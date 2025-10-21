import os 
from dotenv import load_dotenv 
from typing import List

load_dotenv()

class Config:
    
    def __init__(self):
        # Server Config
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", "8080"))
        # Chat backbone
        self.DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
        self.BASE_URL = os.getenv("BASE_URL")
        self.QWEN_MODEL = os.getenv("QWEN_MODEL") 
        self.QWEN_TEMPERATURE = os.getenv("QWEN_TEMPERATURE") 
        self.QWEN_MAX_TOKENS = os.getenv("QWEN_MAX_TOKENS") 
        # Embedding
        self.EMBEDDING_DEPLOYMENT = os.getenv("EMBEDDING_DEPLOYMENT") 
        self.EMBEDDING_MODE = os.getenv("EMBEDDING_MODE") 
        self.EMBEDDING_AZURE_ENDPOINT = os.getenv("EMBEDDING_AZURE_ENDPOINT")
        self.EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY") 
        self.EMBEDDING_API_VERSION = os.getenv("EMBEDDING_API_VERSION")
        # Chat config
        self.USE_LTM = os.getenv("USE_LTM", "True").lower() == "true"
        self.DATA_ROOT = os.getenv("DATA_ROOT", "./data")
        self.VERBOSE = os.getenv("VERBOSE", "True").lower() == "true"
        self.MAX_TURNS = int(os.getenv("MAX_TURNS", "16"))
        self.KEEP_SYSTEM = int(os.getenv("KEEP_SYSTEM", "2"))
        self.MAX_TURNS_IN_CONTEXT = int(os.getenv("MAX_TURNS_IN_CONTEXT", "5"))
config = Config()