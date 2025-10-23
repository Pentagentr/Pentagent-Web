"""
Configuration Management
Centralized configuration for the Pentagent system
"""

import os
from typing import Optional
from pathlib import Path

class Config:
    """Application configuration"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        
        # API Configuration (Gemini deprecated - using Groq now)
        # self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')  # DEPRECATED
        
        # Security Research API Keys
        self.VIRUSTOTAL_API_KEY = os.getenv('VIRUSTOTAL_API_KEY', 'a3613c70e43afc77772f75985a4f7ba228baadd31cceefd6a79902effdaf41c0')
        self.SHODAN_API_KEY = os.getenv('SHODAN_API_KEY', 'Qs2JRfQuCade7ANke71Rj5iVnL0ddvoM')
        self.CENSYS_API_TOKEN = os.getenv('CENSYS_API_TOKEN', '6t5uQ4Xx')
        self.GITHUB_API_TOKEN = os.getenv('GITHUB_API_TOKEN', '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')
        
        # Server Configuration
        self.SERVER_HOST = os.getenv('SERVER_HOST', 'localhost')
        self.SERVER_PORT = int(os.getenv('SERVER_PORT', '8000'))
        self.DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
        
        # Database Configuration
        self.DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./pentagent.db')
        
        # Paths
        self.TOOLS_DIR = self.project_root / 'tools'
        self.REPORTS_DIR = self.project_root / 'reports'
        self.LOGS_DIR = self.project_root / 'logs'
        self.EVIDENCE_DIR = self.project_root / 'evidence'
        
        # Create directories if they don't exist
        for directory in [self.REPORTS_DIR, self.LOGS_DIR, self.EVIDENCE_DIR]:
            directory.mkdir(exist_ok=True)
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = self.LOGS_DIR / 'pentagent.log'
        
        # Tool Configuration
        self.MAX_CONCURRENT_TOOLS = int(os.getenv('MAX_CONCURRENT_TOOLS', '5'))
        self.TOOL_TIMEOUT = int(os.getenv('TOOL_TIMEOUT', '300'))  # 5 minutes
        
        # LLM Provider Configuration
        # MODEL_PROVIDER: "groq" (default) or "huggingface"
        self.MODEL_PROVIDER = os.getenv('MODEL_PROVIDER', 'groq').lower()
        # Groq
        self.GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
        # Default Groq model (fast and strong)
        self.GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
        # Optional alias override (e.g., openai/gpt-oss-120b)
        self.GROQ_MODEL_ALIAS = os.getenv('GROQ_MODEL_ALIAS', '')
        # HuggingFace (optional)
        self.HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN', '')
        self.HF_MODEL_URL = os.getenv('HF_MODEL_URL', 'https://router.huggingface.co/hf-inference/models/meta-llama/Llama-3.2-3B-Instruct')
        
        # Reranker Configuration - mixedbread-ai/mxbai-rerank-base-v1 (DAHA İYİ)
        self.USE_RERANKER = os.getenv('USE_RERANKER', 'true').lower() == 'true'
        # BAAI/bge-reranker-base yerine mixedbread-ai/mxbai-rerank-base-v1 kullanıyoruz (daha iyi)
        self.RERANKER_MODEL = os.getenv('RERANKER_MODEL', 'mixedbread-ai/mxbai-rerank-base-v1')
        self.RERANKER_API_URL = f'https://router.huggingface.co/hf-inference/models/{self.RERANKER_MODEL}'
        self.RERANKER_TOP_K = int(os.getenv('RERANKER_TOP_K', '5'))  # Rerank için kaç sonuç alınacak

# Global configuration instance
config = Config()
