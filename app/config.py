"""
Application Configuration
Manages environment variables and application settings
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator, ValidationError
from typing import Literal, Optional, Union
import sys


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_env: str = "development"
    app_port: int = 8002
    app_host: str = "0.0.0.0"
    log_level: str = "INFO"
    
    # Database
    database_url: str
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600
    
    # CORS
    frontend_url: str = "http://localhost:5173"
    
    # Backend PHP Service
    backend_php_url: str = "http://localhost:8000/api/v1"
    
    # Authentication
    auth_service_url: str
    jwt_issuer: str = "https://api.example.com"
    jwt_audience: str = "https://api.example.com"
    jwks_cache_ttl: int = 3600  # 1 hour in seconds
    
    # Model Provider
    model_provider: Literal["local", "openai"] = "local"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    
    # Ollama
    # Default uses Docker service name, override with OLLAMA_BASE_URL env var
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:3b"
    
    # Interview Configuration
    min_questions: int = 7
    max_questions: int = 20
    default_completeness_threshold: float = 0.8
    
    @field_validator('auth_service_url')
    @classmethod
    def validate_auth_service_url(cls, v: str) -> str:
        """Validate that AUTH_SERVICE_URL is a valid HTTP/HTTPS URL"""
        if not v:
            raise ValueError("AUTH_SERVICE_URL must be configured")
        
        v = v.strip()
        
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError(
                f"AUTH_SERVICE_URL must be a valid HTTP or HTTPS URL, got: {v}"
            )
        
        # Remove trailing slash for consistency
        return v.rstrip('/')
    
    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate that DATABASE_URL is properly formatted for PostgreSQL"""
        if not v:
            raise ValueError("DATABASE_URL must be configured")
        
        v = v.strip()
        
        # Check for asyncpg driver (required for async SQLAlchemy)
        if not v.startswith('postgresql+asyncpg://'):
            raise ValueError(
                f"DATABASE_URL must use postgresql+asyncpg:// driver for async support, got: {v}"
            )
        
        return v
    
    @property
    def jwks_url(self) -> str:
        """Construct JWKS endpoint URL from auth service URL"""
        return f"{self.auth_service_url}/api/v1/auth/jwks"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance with startup validation
try:
    settings = Settings()
except ValidationError as e:
    print("=" * 60)
    print("CONFIGURATION ERROR - Application cannot start")
    print("=" * 60)
    for error in e.errors():
        field = error['loc'][0] if error['loc'] else 'unknown'
        message = error['msg']
        print(f"\n❌ {field.upper()}: {message}")
    print("\n" + "=" * 60)
    print("Please check your .env file and ensure all required")
    print("environment variables are properly configured.")
    print("=" * 60)
    sys.exit(1)


