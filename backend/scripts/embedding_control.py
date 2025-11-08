#!/usr/bin/env python3
"""
Embedding workers controller.

Modes:
  local  - spawn multiple worker subprocesses on WSL/Linux
  docker - scale workers via docker compose (requires Docker Desktop/Engine)
  aws    - print guidance/commands for ECS (requires AWS CLI; no destructive ops)

At-least-once delivery is guaranteed by Redis Streams consumer groups. This controller
adds safety by:
  - ensuring the consumer group exists,
  - optionally re-assigning stale pending entries (XAUTOCLAIM) to the controller's
    maintenance consumer when they are stuck beyond a threshold.
"""
from __future__ import annotations
import argparse
import os
import signal
import subprocess
import sys
import time
from typing import List, Optional, Tuple

# Ensure backend on sys.path
THIS_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(THIS_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from trip_planner.memory import memory_config, RedisConnectionManager


def ensure_group(redis, stream_key: str, group: str):
    try:
        redis.xgroup_create(name=stream_key, groupname=group, id="0", mkstream=True)
        print(f"[control] Created group '{group}' on stream '{stream_key}'")
    except Exception as e:
        if "BUSYGROUP" in str(e):
            print(f"[control] Group '{group}' already exists.")
        else:
            print(f"[control] xgroup_create warning: {e}")


def autoclaim_stale(redis, stream_key: str, group: str, consumer: str, min_idle_ms: int, count: int = 20):
    """
    Reassign stale pending messages (older than min_idle_ms) to 'consumer'.
    This prevents deadlocks when a worker dies before XACK.
    """
    try:
        # XAUTOCLAIM returns [new_start_id, [[id, fields], ...]]
        start_id = "0-0"
        total = 0
        while True:
            res = redis.xautoclaim(stream_key, group, consumer, min_idle_ms, start_id, count=count)
            if not res or len(res) < 2:
                break
            start_id, messages = res[0], res[1]
            if not messages:
                break
            total += len(messages)
            # We do not process here; workers will get these now-owned by 'consumer' only if they read pending.
            # Most workers only read '>' (new). If desired, one special consumer can read its pending explicitly.
            # Here we simply reassign ownership to make XPENDING manageable; processing remains in workers.
            # Optionally, we could XACK+requeue here, but that changes semantics.
        if total:
            print(f"[control] Auto-claimed {total} stale pending messages to '{consumer}'.")
    except Exception as e:
        print(f"[control] XAUTOCLAIM error: {e}")


def run_local(workers: int, group: str, stream_key: str, stale_ms: int):
    cfg = memory_config
    redis = RedisConnectionManager(cfg).get_client()
    if not redis:
        print("[control] Redis not available.")
        return 1
    ensure_group(redis, stream_key, group)

    procs: List[Tuple[str, subprocess.Popen]] = []
    for i in range(workers):
        name = f"worker-{i+1}"
        cmd = [sys.executable, os.path.join(BACKEND_DIR, "scripts", "embedding_worker.py"),
               "--group", group, "--consumer", name]
        p = subprocess.Popen(cmd)
        procs.append((name, p))
        print(f"[control] Started {name} pid={p.pid}")

    stopping = False

    def _stop(signum, frame):
        nonlocal stopping
        if stopping:
            return
        stopping = True
        print("\n[control] Stopping workers...")
        for name, p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        for name, p in procs:
            try:
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        print("[control] All workers stopped.")
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        while True:
            # Periodic maintenance: auto-claim stale pending entries to this controller (as 'ctl' consumer)
            autoclaim_stale(redis, stream_key, group, consumer="ctl", min_idle_ms=stale_ms, count=50)
            # Restart crashed workers
            for idx, (name, p) in enumerate(list(procs)):
                if p.poll() is not None:
                    print(f"[control] {name} exited with code {p.returncode}, restarting...")
                    new_name = name  # keep name stable
                    cmd = [sys.executable, os.path.join(BACKEND_DIR, "scripts", "embedding_worker.py"),
                           "--group", group, "--consumer", new_name]
                    new_p = subprocess.Popen(cmd)
                    procs[idx] = (new_name, new_p)
                    print(f"[control] Restarted {new_name} pid={new_p.pid}")
            time.sleep(5.0)
    finally:
        _stop(None, None)  # ensure cleanup


def run_docker(compose_files: List[str], service: str, replicas: int):
    """
    Scale workers via docker compose. Example:
      docker compose -f backend/docker-compose.memory.yml -f backend/docker-compose.worker.yml up -d --scale worker=3
    """
    args = ["docker", "compose"]
    for f in compose_files:
        args += ["-f", f]
    args += ["up", "-d", "--scale", f"{service}={replicas}"]
    print("[control] Running:", " ".join(args))
    code = subprocess.call(args)
    return code


def run_aws_help(cluster: str, service: str, count: int):
    """
    Print guidance to scale an ECS service (Fargate) running the worker container image.
    Assumes service already exists pointing to your worker image/command.
    """
    print("\n[control] AWS ECS scaling guidance:")
    print(f"  aws ecs update-service --cluster {cluster} --service {service} --desired-count {count}")
    print("If you need to run ad-hoc tasks instead of a service:")
    print("  aws ecs run-task --cluster <cluster> --launch-type FARGATE \\")
    print("    --task-definition <your-worker-task-def> \\")
    print("    --network-configuration 'awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}'")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)

    ap_local = sub.add_parser("local", help="Run multiple workers locally (WSL/Linux)")
    ap_local.add_argument("--workers", type=int, default=3)
    ap_local.add_argument("--group", default="embedder")
    ap_local.add_argument("--stream", default=None, help="Stream key (default from config)")
    ap_local.add_argument("--stale-ms", type=int, default=120000, help="auto-claim messages idle longer than this")

    ap_docker = sub.add_parser("docker", help="Scale docker compose worker service")
    ap_docker.add_argument("--files", nargs="+", default=[
        os.path.join(BACKEND_DIR, "docker-compose.memory.yml"),
        os.path.join(BACKEND_DIR, "docker-compose.worker.yml"),
    ])
    ap_docker.add_argument("--service", default="worker")
    ap_docker.add_argument("--replicas", type=int, default=3)

    ap_aws = sub.add_parser("aws", help="Print AWS ECS scaling commands")
    ap_aws.add_argument("--cluster", required=True)
    ap_aws.add_argument("--service", required=True)
    ap_aws.add_argument("--count", type=int, default=3)

    args = ap.parse_args()
    cfg = memory_config
    stream_key = args.stream or getattr(cfg, "EMBEDDING_QUEUE", "embedding_queue")

    if args.mode == "local":
        return run_local(args.workers, args.group, stream_key, args.stale_ms)
    if args.mode == "docker":
        return run_docker(args.files, args.service, args.replicas)
    if args.mode == "aws":
        run_aws_help(args.cluster, args.service, args.count)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


