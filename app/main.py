"""
FastAPI Application
Main entry point for the elicitation AI microservice
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError
from app.config import settings
from app.routers import health, interviews
from app.database import validate_database_connection, close_database_connection
from app.exceptions import (
    InterviewNotFoundError,
    InterviewAccessDeniedError,
    DatabaseConnectionError
)
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting up application...")
    db_connected = await validate_database_connection()
    if not db_connected:
        logger.warning("⚠️  Database connection failed - application will start but database operations will fail")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_database_connection()

# Create FastAPI app
app = FastAPI(
    title="Elicitation AI Service",
    description="Microservicio de entrevistas con IA para elicitación de requerimientos",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check endpoints - **No authentication required**"
        },
        {
            "name": "interviews",
            "description": """Interview management endpoints - **Authentication required** (Bearer token)
            
## Permission System

All interview endpoints require specific permissions in addition to authentication. Permissions follow the `resource:action` pattern and are included in the JWT token.

### Available Permissions

- **`interviews:create`** - Create new interviews and continue existing ones
- **`interviews:read`** - Read own interviews only
- **`interviews:read_all`** - Read all interviews in the organization (admin/manager)
- **`interviews:update`** - Update interview status (own interviews only)
- **`interviews:export`** - Export interviews to documents (own interviews only)
- **`interviews:delete`** - Delete own interviews (future implementation)

### Permission Scopes

**Own vs Organization Access:**
- Users with only `interviews:read` can only see their own interviews
- Users with `interviews:read_all` can see all interviews in their organization
- The `interviews:read_all` permission grants admin/manager level access

### Common Error Responses

**403 Forbidden - Insufficient Permissions:**
```json
{
  "status": "error",
  "code": 403,
  "message": "Insufficient permissions",
  "errors": [
    {
      "field": "permissions",
      "error": "Required permission: interviews:create",
      "user_permissions": []
    }
  ]
}
```

**403 Forbidden - Access Denied to Resource:**
```json
{
  "status": "error",
  "code": 403,
  "message": "Access denied",
  "errors": [
    {
      "field": "interview_id",
      "error": "You don't have permission to access this interview"
    }
  ]
}
```
            """
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
    
    # Add security requirement and 403 responses to all interview endpoints
    # EXCEPT public endpoints like /permissions
    for path, path_item in openapi_schema["paths"].items():
        if path.startswith("/api/v1/interviews"):
            # Skip public endpoints
            if path == "/api/v1/interviews/permissions":
                continue
                
            for method_name, method in path_item.items():
                if isinstance(method, dict) and "operationId" in method:
                    # Add security requirement
                    method["security"] = [{"BearerAuth": []}]
                    
                    # Add 403 response for permission errors
                    if "responses" not in method:
                        method["responses"] = {}
                    
                    method["responses"]["403"] = {
                        "description": "Forbidden - Insufficient permissions or access denied",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "oneOf": [
                                        {"$ref": "#/components/schemas/InsufficientPermissionsError"},
                                        {"$ref": "#/components/schemas/AccessDeniedError"}
                                    ]
                                },
                                "examples": {
                                    "insufficient_permissions": {
                                        "summary": "Missing required permission",
                                        "value": {
                                            "status": "error",
                                            "code": 403,
                                            "message": "Insufficient permissions",
                                            "errors": [
                                                {
                                                    "field": "permissions",
                                                    "error": "Required permission: interviews:create",
                                                    "user_permissions": []
                                                }
                                            ]
                                        }
                                    },
                                    "access_denied": {
                                        "summary": "Access denied to resource",
                                        "value": {
                                            "status": "error",
                                            "code": 403,
                                            "message": "Access denied",
                                            "errors": [
                                                {
                                                    "field": "interview_id",
                                                    "error": "You don't have permission to access this interview"
                                                }
                                            ]
                                        }
                                    }
                                }
                            }
                        }
                    }
    
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
    
    # Add permission-related error schemas
    openapi_schema["components"]["schemas"]["InsufficientPermissionsError"] = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "example": "error"},
            "code": {"type": "integer", "example": 403},
            "message": {"type": "string", "example": "Insufficient permissions"},
            "errors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string", "example": "permissions"},
                        "error": {"type": "string", "example": "Required permission: interviews:create"},
                        "user_permissions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": []
                        }
                    }
                }
            }
        }
    }
    
    openapi_schema["components"]["schemas"]["AccessDeniedError"] = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "example": "error"},
            "code": {"type": "integer", "example": 403},
            "message": {"type": "string", "example": "Access denied"},
            "errors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string", "example": "interview_id"},
                        "error": {"type": "string", "example": "You don't have permission to access this interview"}
                    }
                }
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


# Exception handlers
@app.exception_handler(InterviewNotFoundError)
async def interview_not_found_handler(request: Request, exc: InterviewNotFoundError):
    """Handle InterviewNotFoundError with 404 status"""
    return JSONResponse(
        status_code=404,
        content={
            "status": "error",
            "code": 404,
            "message": "Interview not found",
            "errors": [
                {
                    "field": "interview_id",
                    "error": exc.message
                }
            ]
        }
    )


@app.exception_handler(InterviewAccessDeniedError)
async def interview_access_denied_handler(request: Request, exc: InterviewAccessDeniedError):
    """Handle InterviewAccessDeniedError with 403 status"""
    return JSONResponse(
        status_code=403,
        content={
            "status": "error",
            "code": 403,
            "message": "Access denied",
            "errors": [
                {
                    "field": "interview_access",
                    "error": exc.message
                }
            ]
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTPException with proper ProssX standard formatting.
    
    Special handling for 403 errors to ensure permission information is properly
    formatted and no sensitive information is exposed.
    
    Args:
        request: FastAPI request object
        exc: HTTPException raised by the application
        
    Returns:
        JSONResponse with ProssX standard error format
    """
    # If it's a 403 error with detail as dict (from permission dependencies)
    if exc.status_code == 403 and isinstance(exc.detail, dict):
        # Validate that the detail follows ProssX standard format
        if "status" in exc.detail and "code" in exc.detail and "message" in exc.detail:
            # Log the permission denial for audit purposes
            logger.warning(
                f"403 Forbidden: {exc.detail.get('message')} - "
                f"Path: {request.url.path} - "
                f"Method: {request.method}"
            )
            return JSONResponse(
                status_code=403,
                content=exc.detail
            )
    
    # For 403 errors with string detail (fallback)
    if exc.status_code == 403:
        logger.warning(
            f"403 Forbidden: {exc.detail} - "
            f"Path: {request.url.path} - "
            f"Method: {request.method}"
        )
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "code": 403,
                "message": "Access denied",
                "errors": [
                    {
                        "field": "authorization",
                        "error": exc.detail if isinstance(exc.detail, str) else "Insufficient permissions"
                    }
                ]
            }
        )
    
    # For other HTTP exceptions, use standard format
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": exc.status_code,
            "message": exc.detail if isinstance(exc.detail, str) else "Request failed",
            "errors": [
                {
                    "field": "general",
                    "error": exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                }
            ]
        }
    )


@app.exception_handler(DatabaseConnectionError)
async def database_connection_error_handler(request: Request, exc: DatabaseConnectionError):
    """Handle DatabaseConnectionError with 500 status"""
    logger.error(f"Database connection error: {exc.message}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": 500,
            "message": "Database connection error",
            "errors": [
                {
                    "field": "database",
                    "error": "Unable to connect to database"
                }
            ]
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Handle generic SQLAlchemy errors with 500 status"""
    logger.error(f"Database error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": 500,
            "message": "Database operation failed",
            "errors": [
                {
                    "field": "database",
                    "error": "An error occurred while processing the database operation"
                }
            ]
        }
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


