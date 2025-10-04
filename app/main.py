"""
FastAPI Application
Main entry point for the elicitation AI microservice
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import health, interviews

# Create FastAPI app
app = FastAPI(
    title="Elicitation AI Service",
    description="Microservicio de entrevistas con IA para elicitación de requerimientos",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(interviews.router, prefix="/api/v1", tags=["interviews"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "svc-elicitation-ai",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=(settings.app_env == "development")
    )


