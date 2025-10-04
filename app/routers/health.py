"""
Health Check Router
"""
from fastapi import APIRouter
from app.models.responses import success_response
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns service status and configuration info
    """
    data = {
        "service": "svc-elicitation-ai",
        "version": "1.0.0",
        "status": "healthy",
        "model_provider": settings.model_provider,
        "model": settings.ollama_model if settings.model_provider == "local" else settings.openai_model,
        "environment": settings.app_env
    }
    
    return success_response(
        data=data,
        message="Service is healthy"
    )

