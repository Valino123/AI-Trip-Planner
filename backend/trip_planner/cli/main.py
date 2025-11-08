import os
import uuid
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ..tools import TOOLS
from ..orchestrate import make_app
from ..cli.user import CLI
from ..llm import init_llm
from ..role import role_template
from ..memory import create_memory_manager
from config import config


def _get_cli_ids() -> tuple[str, str]:
    user_id = os.getenv("CLI_USER_ID") or "cli_user"
    session_id = os.getenv("CLI_SESSION_ID") or f"s_{uuid.uuid4().hex[:8]}"
    return user_id, session_id


def main():

    print("\n=== LangGraph Agent — CLI (Redis/Mongo/Qdrant memory) ===")

    # LLM
    llm_invoker = init_llm(TOOLS)

    # Memory Manager (production)
    mem = create_memory_manager()
    user_id, session_id = _get_cli_ids()

    # Short-term in-process state for the graph
    state = {"messages": [SystemMessage(content=role_template)]}

    USE_LTM = config.USE_LTM
    MAX_CONTEXT_SCALE = config.MAX_TURNS_IN_CONTEXT
    print(f"Memory: Short{'+Long' if USE_LTM else ''} | Max context scale: {MAX_CONTEXT_SCALE}")

    # Orchestrate
    app = make_app(llm_invoker, TOOLS, MAX_CONTEXT_SCALE)

    print("\nType 'exit' to quit. Try: 'Plan a 2-day trip to San Diego, browse the internet for nice places and check the weather'.\n")
    usr = CLI()

    try:
        while True:
            try:
                user_inp = usr.get_input()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if user_inp.lower() in {"exit", "quit", ":q"}:
                break
            if not user_inp:
                continue

            # Persist to intra-session (Redis) — best-effort
            mem.save_message_to_session(session_id, {"type": "human", "content": user_inp})

            # Write the current user input to in-process state
            state["messages"].append(HumanMessage(content=user_inp))

            # Optional: long-term retrieval (Mongo/Qdrant)
            if USE_LTM:
                try:
                    snips = mem.retrieve_relevant_memories(user_id, user_inp, k=4, min_similarity=0.55, verbose=config.VERBOSE)
                    mem_text = mem.format_memories_for_context(snips)
                    if mem_text:
                        insert_at = 1 if state["messages"] and isinstance(state["messages"][0], SystemMessage) else 0
                        state["messages"].insert(insert_at, SystemMessage(content=mem_text))
                except Exception:
                    pass

            # Run the agent graph
            new_state = app({"messages": state["messages"]})
            last_ai = next((m for m in reversed(new_state["messages"]) if isinstance(m, AIMessage)), None)

            if last_ai:
                # Append to in-process state and persist to intra-session
                state["messages"].append(last_ai)
                mem.save_message_to_session(session_id, {"type": "ai", "content": last_ai.content})
                usr.send_response(last_ai.content)
            else:
                usr.send_response("[No response]")

    finally:
        # Finalize: move session to MongoDB and queue embedding
        try:
            mem.finalize_session(user_id, session_id)
        except Exception:
            pass


if __name__ == "__main__":
    main()


