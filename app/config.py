"""
Application Configuration
Manages environment variables and application settings
"""
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_env: str = "development"
    app_port: int = 8001
    app_host: str = "0.0.0.0"
    log_level: str = "INFO"
    
    # CORS
    frontend_url: str = "http://localhost:5173"
    
    # Backend PHP Service
    backend_php_url: str = "http://localhost:8000/api/v1"
    
    # Model Provider
    model_provider: Literal["local", "openai"] = "local"
    
    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    
    # Interview Configuration
    min_questions: int = 7
    max_questions: int = 20
    default_completeness_threshold: float = 0.8
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


