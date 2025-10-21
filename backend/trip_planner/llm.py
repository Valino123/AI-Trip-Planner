import os
from typing import List
from langchain_openai import ChatOpenAI, AzureOpenAIEmbeddings
from config import config

# # ===== Runtime knobs (merged with LLM) =====
# MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
# TEMPERATURE = float(os.environ.get("TEMPERATURE", "0"))
# API_KEY_PATH = os.environ.get("API_KEY_PATH", "API_KEY")


# def _get_api_key() -> str:
#     # Prefer env var, fallback to file (OPENAI_API_KEY)
#     key = os.environ.get("OPENAI_API_KEY", "").strip()
    
#     if not key and os.path.exists(API_KEY_PATH):
#         with open(API_KEY_PATH, "r") as f:
#             key = f.read().strip()
#             if key:
#                 return key
#     if not key:
#         raise RuntimeError(
#             "OpenAI API key not found. Provide file 'API_KEY' or set OPENAI_API_KEY."
#         )
#     return key


# def init_llm(tools: List, verbose=True):
#     """Factory returning an LLM bound with the provided tools."""
#     llm = ChatOpenAI(model=MODEL, temperature=TEMPERATURE, api_key=_get_api_key())
#     if verbose:
#         print(f"Model: {MODEL} | Temp: {TEMPERATURE}")
#         print(f"Tools: {' | '.join(t.name for t in tools)}")
#     return llm.bind_tools(tools).invoke

def init_llm(tools: List, verbose=True):
    llm = ChatOpenAI(
        model=config.QWEN_MODEL,
        temperature=float(config.QWEN_TEMPERATURE or "0.7"),
        max_tokens=int(config.QWEN_MAX_TOKENS or "1000"),
        api_key=config.DASHSCOPE_API_KEY,
        base_url=config.BASE_URL,
    )

    if verbose:
        print(f"Model: {config.QWEN_MODEL} | Temperature: {config.QWEN_TEMPERATURE} | Max Tokens: {config.QWEN_MAX_TOKENS}")
        print(f"Tools: {' | '.join(t.name for t in tools)}")

    return llm.bind_tools(tools).invoke\


def init_embedder():
    return AzureOpenAIEmbeddings(
        azure_deployment=config.EMBEDDING_DEPLOYMENT,
        azure_endpoint=config.EMBEDDING_AZURE_ENDPOINT,
        api_key=config.EMBEDDING_API_KEY,
        api_version=config.EMBEDDING_API_VERSION,
        model=config.EMBEDDING_MODE,
    )