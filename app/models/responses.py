"""
Standard Response Models
Follows ProssX Confluence documentation standards
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class StandardResponse(BaseModel):
    """
    Standard response format according to Confluence documentation
    
    Reference: Estándar de Respuesta para Microservicios
    """
    status: str = Field(description="success or error")
    code: int = Field(description="HTTP status code")
    message: str = Field(description="Human-readable message")
    data: Optional[Any] = Field(default=None, description="Response data")
    errors: Optional[List[Dict[str, str]]] = Field(default=None, description="Error details")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "code": 200,
                "message": "Operation completed successfully",
                "data": {"key": "value"},
                "errors": None,
                "meta": {"timestamp": "2025-10-03T00:00:00Z"}
            }
        }


def success_response(
    data: Any,
    message: str = "Operation completed successfully",
    code: int = 200,
    meta: Optional[Dict[str, Any]] = None
) -> StandardResponse:
    """Helper function to create success responses"""
    return StandardResponse(
        status="success",
        code=code,
        message=message,
        data=data,
        errors=None,
        meta=meta
    )


def error_response(
    message: str,
    code: int = 400,
    errors: Optional[List[Dict[str, str]]] = None,
    meta: Optional[Dict[str, Any]] = None
) -> StandardResponse:
    """Helper function to create error responses"""
    return StandardResponse(
        status="error",
        code=code,
        message=message,
        data=None,
        errors=errors,
        meta=meta
    )


