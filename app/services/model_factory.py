"""
Model Factory
Creates model instances based on configuration
"""
from app.config import settings


def create_model():
    """
    Factory function to create a model based on configuration
    
    Returns:
        Model instance configured for Ollama or OpenAI
    """
    if settings.model_provider == "local":
        # Local model via Ollama
        from strands.models.ollama import OllamaModel
        
        return OllamaModel(
            host=settings.ollama_base_url,
            model_id=settings.ollama_model,
            temperature=0.7,
        )
    elif settings.model_provider == "openai":
        # OpenAI model
        from strands.models.openai import OpenAIModel
        
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        
        return OpenAIModel(
            api_key=settings.openai_api_key,
            model_id=settings.openai_model,
            temperature=0.7,
        )
    else:
        raise ValueError(f"Unknown model provider: {settings.model_provider}")


def get_model_info() -> dict:
    """
    Get information about the currently configured model
    
    Returns:
        dict: Model provider and model ID
    """
    return {
        "provider": settings.model_provider,
        "model": settings.ollama_model if settings.model_provider == "local" else settings.openai_model
    }

