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
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check endpoints - **No authentication required**"
        },
        {
            "name": "interviews",
            "description": "Interview management endpoints - **Authentication required** (Bearer token)"
        }
    ],
    servers=[
        {
            "url": "http://localhost:8002",
            "description": "Development server"
        },
        {
            "url": "https://api.example.com",
            "description": "Production server"
        }
    ]
)

# Add security scheme for OpenAPI documentation
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        servers=app.servers
    )
    
    # Add security scheme definition
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from the Auth Service (svc-users-python) at `/api/v1/auth/login`"
        }
    }
    
    # Add security requirement to all interview endpoints
    for path, path_item in openapi_schema["paths"].items():
        if path.startswith("/api/v1/interviews"):
            for method in path_item.values():
                if isinstance(method, dict) and "operationId" in method:
                    method["security"] = [{"BearerAuth": []}]
    
    # Add common error responses to schema
    openapi_schema["components"]["schemas"]["AuthenticationError"] = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "example": "error"},
            "code": {"type": "integer", "example": 401},
            "message": {"type": "string", "example": "Authentication required"},
            "errors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string", "example": "authorization"},
                        "error": {"type": "string", "example": "Missing or invalid authorization header"}
                    }
                }
            }
        }
    }
    
    openapi_schema["components"]["schemas"]["TokenExpiredError"] = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "example": "error"},
            "code": {"type": "integer", "example": 401},
            "message": {"type": "string", "example": "Token expired"},
            "errors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string", "example": "token"},
                        "error": {"type": "string", "example": "JWT token has expired"}
                    }
                }
            }
        }
    }
    
    openapi_schema["components"]["schemas"]["TokenInvalidError"] = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "example": "error"},
            "code": {"type": "integer", "example": 401},
            "message": {"type": "string", "example": "Invalid token"},
            "errors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string", "example": "token"},
                        "error": {"type": "string", "example": "Token signature verification failed"}
                    }
                }
            }
        }
    }
    
    openapi_schema["components"]["schemas"]["ServiceUnavailableError"] = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "example": "error"},
            "code": {"type": "integer", "example": 503},
            "message": {"type": "string", "example": "Authentication service unavailable"},
            "errors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string", "example": "service"},
                        "error": {"type": "string", "example": "Unable to validate token"}
                    }
                }
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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


