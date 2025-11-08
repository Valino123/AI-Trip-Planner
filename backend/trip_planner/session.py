from __future__ import annotations
import os, json, time, uuid
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Literal, Optional

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from .llm import init_llm
from .orchestrate import make_app
from .tools import TOOLS, meta
from .role import role_template
from .context import trim_context
from .memory import create_memory_manager


@dataclass
class MessageRecord:
    mem_index: int
    owner: Literal["user", "agent"]
    content: str
    gen_by_engine: bool = False
    context_size: int = 0
    use_ltm: bool = False
    memory_injected: List[int] = field(default_factory=list)
    use_tools: List[str] = field(default_factory=list)


class Session:
    """Evaluation Session (simple version)"""

    def __init__(self, background_info: Optional[str] = None,
                 session_id: Optional[str] = None,
                 root: str = "./eval_runs",
                 verbose=False,
                 user_id: str = "local_user"):

        self.background_info = background_info
        self.root = root
        self.user_id = user_id
        os.makedirs(os.path.join(root, "sessions"), exist_ok=True)

        if session_id:
            # Load existing session
            self.session_id = session_id
        else:
            self.session_id = f"s_{uuid.uuid4().hex[:8]}"

        self.sdir = os.path.join(root, "sessions", self.session_id)
        os.makedirs(self.sdir, exist_ok=True)
        self.history_path = os.path.join(self.sdir, "history.jsonl")

        # --- load or initialize history ---
        self.history: List[MessageRecord] = []
        if os.path.exists(self.history_path):
            with open(self.history_path, "r", encoding="utf-8") as f:
                for line in f:
                    self.history.append(MessageRecord(**json.loads(line)))

        # --- Production memory system (Redis + MongoDB + Qdrant) ---
        self.memory = create_memory_manager()

        # --- initialize LLM + app ---
        self.llm = init_llm(TOOLS, verbose=verbose)
        self.app = make_app(self.llm, TOOLS)

        # --- If creating a new session with background info ---
        if background_info and not os.path.exists(self.history_path):
            # Seed background as a system message into intra-session memory for this session
            try:
                self.memory.save_message_to_session(
                    self.session_id,
                    {
                        "type": "system",
                        "content": background_info,
                        "created_at": time.time(),
                    },
                )
            except Exception:
                pass

    # ------------------------------------------------------------------

    def _append_record(self, rec: MessageRecord):
        with open(self.history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        self.history.append(rec)

    def _remember_qa_pair(self, q_text: str, a_text: str, a_mem_index: int) -> None:
        """(No-op) Legacy local LTM removed; production memory finalizes per session."""
        return None

    def append_message(self, content: str, owner: Literal["user", "agent"]) -> None:
        """
        Append a message verbatim (no model call).
        If this creates a (user -> agent) pair, auto-save a compact QA to LTM.
        """
        rec = MessageRecord(
            mem_index=len(self.history),
            owner=owner,
            content=content,
            gen_by_engine=False,
        )
        self._append_record(rec)

        # Save to intra-session memory (Redis)
        try:
            self.memory.save_message_to_session(
                self.session_id,
                {
                    "type": owner,
                    "content": content,
                    "created_at": time.time(),
                },
            )
        except Exception:
            pass

        # Immediately archive to LTM: if a Q&A pair is formed, save the pair
        # Only when current is agent and the previous is user
        if owner == "agent" and len(self.history) >= 2:
            prev = self.history[-2]
            if prev.owner == "user":
                # Save (prev.user -> current.agent) as a Q&A pair into LTM
                self._remember_qa_pair(prev.content, rec.content, rec.mem_index)

    def get_history(self) -> List[Dict[str, Any]]:
        return [asdict(r) for r in self.history]

    # ------------------------------------------------------------------

    def empty_session(self, use_ltm: bool = True) -> None:
        """
        Clears the current session's history (RAM and disk).
        Optionally resets the long-term memory (LTM).

        Params:
            use_ltm (bool):
            - True (default): Keeps the LTM. Clears chat history only.
            - False: Resets the LTM. Clears both chat history and LTM,
                     then re-initializes the LTM with the background_info.
        """
        # 1. Clear chat history (in-RAM)
        self.history = []
        
        # 2. Clear chat history (on-disk)
        try:
            if os.path.exists(self.history_path):
                os.remove(self.history_path)
        except OSError as e:
            print(f"[WARN] Could not remove history file {self.history_path}: {e}")

        # 3. Clear intra-session memory (Redis)
        try:
            self.memory.intra_session.clear_session(self.session_id)
        except Exception:
            pass

    # ------------------------------------------------------------------

    def chat(self, user_request: str, context_size: int = 6,
         use_ltm: bool = True, store_to_cache: bool = False,
             verbose: bool = False) -> str:
        """
        One chat turn. If store_to_cache=False, this call is SIDE-EFFECT FREE:
        Params:
            user_request: the new user message for this turn
            context_size: max context turns used by the model (trim_context handles details)
            use_ltm: whether to retrieve from session-scoped long-term memory
            store_to_cache:
            - False => dry-run, no side effects
                * Do NOT append the user/agent messages to session history
                * Do NOT write Q&A summary to long-term memory
            - True => persist to history and LTM
                * Append both user and agent messages to history
                * Optionally write a compact Q&A summary to long-term memory
            verbose: whether to print the retrieve logs
        """
        # --- 1) Build a temporary message list for this inference only ---
        msgs = [SystemMessage(content=role_template)]
        for r in self.history:
            if r.owner == "user":
                msgs.append(HumanMessage(content=r.content))
            else:
                msgs.append(AIMessage(content=r.content))

        # LTM retrieval (read-only)
        mem_injected = []
        if use_ltm:
            try:
                # Retrieve inter-session memories for this user
                memories = self.memory.retrieve_relevant_memories(
                    self.user_id, user_request, verbose=verbose
                )
                if memories:
                    mem_txt = self.memory.format_memories_for_context(memories)
                    if mem_txt:
                        msgs.insert(1, SystemMessage(content=mem_txt))
            except Exception:
                pass

        # Temporarily add this turn's user message (used only for inference; persistence depends on store_to_cache)
        msgs.append(HumanMessage(content=user_request))

        # --- 2) Trim and run the graph ---
        msgs_trim = trim_context(msgs, context_size)
        n0 = len(msgs_trim)  # the message count before calling, used to slice out new outputs

        original_verbose_state = meta['verbose']
        meta['verbose'] = verbose
        state = self.app({"messages": msgs_trim})
        meta['verbose'] = original_verbose_state
        
        new_msgs = state["messages"][n0:] if len(state["messages"]) >= n0 else state["messages"]

        # --- 3) Parse outputs for this turn (tools + final AI) ---
        use_tools: List[str] = []
        last_ai: Optional[AIMessage] = None

        for m in new_msgs:
            if isinstance(m, ToolMessage):
                # ToolMessage includes name and content
                if getattr(m, "name", None):
                    use_tools.append({"name": m.name, "output": m.content})
            elif isinstance(m, AIMessage):
                last_ai = m  # the last AIMessage is the final reply

        resp_text = last_ai.content if last_ai else "[No response]"

        arec = MessageRecord(
            mem_index=len(self.history),
            owner="agent",
            content=resp_text,
            gen_by_engine=True,
            context_size=context_size,
            use_ltm=use_ltm,
            memory_injected=mem_injected,
            use_tools=use_tools,
        )
        
        # --- 4) Side effects only when store_to_cache=True ---
        if store_to_cache:
            # First write this turn's user record
            urec = MessageRecord(
                mem_index=len(self.history),
                owner="user",
                content=user_request
            )
            self._append_record(urec)
            try:
                self.memory.save_message_to_session(
                    self.session_id,
                    {
                        "type": "user",
                        "content": user_request,
                        "created_at": time.time(),
                    },
                )
            except Exception:
                pass

            # Then write this turn's agent record
            self._append_record(arec)
            try:
                self.memory.save_message_to_session(
                    self.session_id,
                    {
                        "type": "agent",
                        "content": resp_text,
                        "created_at": time.time(),
                    },
                )
            except Exception:
                pass

        return asdict(arec)

    # ------------------------------------------------------------------

    def finalize(self) -> bool:
        """Finalize this session into inter-session memory and clear intra-session state."""
        try:
            return self.memory.finalize_session(self.user_id, self.session_id)
        except Exception:
            return False

    def close(self) -> None:
        """Close resources (finalize session is caller's responsibility)."""
        try:
            self.memory.close()
        except Exception:
            pass
