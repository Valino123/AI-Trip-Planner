import os
from typing import List
from langchain_openai import ChatOpenAI, AzureOpenAIEmbeddings
from config import config

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