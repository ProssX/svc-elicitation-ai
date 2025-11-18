"""
Unit tests for error handlers in main.py
"""
import pytest
import json
from unittest.mock import Mock
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from app.main import validation_exception_handler


class TestValidationErrorHandler:
    """Test suite for RequestValidationError handler"""
    
    @pytest.mark.asyncio
    async def test_validation_error_handler_returns_prossx_format(self):
        """Test that RequestValidationError returns correct ProssX format"""
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/v1/interviews/continue"
        request.method = "POST"
        
        # Create validation error with single field error
        exc = RequestValidationError([
            {
                "loc": ("body", "user_response"),
                "msg": "String should have at least 1 character",
                "type": "string_too_short"
            }
        ])
        
        # Call handler
        response = await validation_exception_handler(request, exc)
        
        # Assert response structure
        assert response.status_code == 422
        
        # Parse response body
        content = json.loads(response.body)
        
        # Assert ProssX standard format
        assert content["status"] == "error"
        assert content["code"] == 422
        assert content["message"] == "Validation error"
        assert "errors" in content
        assert isinstance(content["errors"], list)
        assert len(content["errors"]) == 1
        
        # Assert error details
        error = content["errors"][0]
        assert error["field"] == "user_response"
        assert error["error"] == "String should have at least 1 character"
        assert error["type"] == "string_too_short"
        
        # Assert meta information
        assert "meta" in content
        assert content["meta"]["endpoint"] == "/api/v1/interviews/continue"
        assert content["meta"]["method"] == "POST"
    
    @pytest.mark.asyncio
    async def test_validation_error_handler_multiple_errors(self):
        """Test multiple validation errors are included in errors array"""
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/v1/interviews/continue"
        request.method = "POST"
        
        # Create validation error with multiple field errors
        exc = RequestValidationError([
            {
                "loc": ("body", "user_response"),
                "msg": "String should have at least 1 character",
                "type": "string_too_short"
            },
            {
                "loc": ("body", "language"),
                "msg": "String should match pattern '^(es|en|pt)$'",
                "type": "string_pattern_mismatch"
            },
            {
                "loc": ("body", "interview_id"),
                "msg": "Input should be a valid UUID",
                "type": "uuid_parsing"
            }
        ])
        
        # Call handler
        response = await validation_exception_handler(request, exc)
        
        # Parse response body
        content = json.loads(response.body)
        
        # Assert all errors are included
        assert len(content["errors"]) == 3
        
        # Verify each error
        fields = [error["field"] for error in content["errors"]]
        assert "user_response" in fields
        assert "language" in fields
        assert "interview_id" in fields
    
    @pytest.mark.asyncio
    async def test_validation_error_handler_field_name_extraction(self):
        """Test field names are extracted correctly from error location"""
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/v1/test"
        request.method = "POST"
        
        # Test different location formats
        test_cases = [
            # Simple field
            {
                "loc": ("body", "field_name"),
                "expected_field": "field_name"
            },
            # Nested field
            {
                "loc": ("body", "nested", "field"),
                "expected_field": "nested -> field"
            },
            # Query parameter
            {
                "loc": ("query", "param"),
                "expected_field": "param"
            },
            # Path parameter
            {
                "loc": ("path", "id"),
                "expected_field": "id"
            }
        ]
        
        for test_case in test_cases:
            exc = RequestValidationError([
                {
                    "loc": test_case["loc"],
                    "msg": "Test error",
                    "type": "test_error"
                }
            ])
            
            response = await validation_exception_handler(request, exc)
            content = json.loads(response.body)
            
            assert content["errors"][0]["field"] == test_case["expected_field"]
    
    @pytest.mark.asyncio
    async def test_validation_error_handler_human_readable_messages(self):
        """Test error messages are human-readable"""
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/v1/interviews/continue"
        request.method = "POST"
        
        # Test various Pydantic error types
        test_errors = [
            {
                "loc": ("body", "field1"),
                "msg": "Field required",
                "type": "missing"
            },
            {
                "loc": ("body", "field2"),
                "msg": "Input should be a valid string",
                "type": "string_type"
            },
            {
                "loc": ("body", "field3"),
                "msg": "String should have at most 100 characters",
                "type": "string_too_long"
            }
        ]
        
        exc = RequestValidationError(test_errors)
        response = await validation_exception_handler(request, exc)
        content = json.loads(response.body)
        
        # Verify all messages are present and readable
        for i, error in enumerate(content["errors"]):
            assert error["error"] == test_errors[i]["msg"]
            assert len(error["error"]) > 0
            assert error["error"] != ""
    
    @pytest.mark.asyncio
    async def test_validation_error_handler_logging(self, caplog):
        """Test logging includes endpoint and method information"""
        import logging
        
        # Set up logging capture
        with caplog.at_level(logging.WARNING):
            # Create mock request
            request = Mock(spec=Request)
            request.url.path = "/api/v1/interviews/continue"
            request.method = "POST"
            
            # Create validation error
            exc = RequestValidationError([
                {
                    "loc": ("body", "user_response"),
                    "msg": "String should have at least 1 character",
                    "type": "string_too_short"
                },
                {
                    "loc": ("body", "language"),
                    "msg": "String should match pattern",
                    "type": "string_pattern_mismatch"
                }
            ])
            
            # Call handler
            await validation_exception_handler(request, exc)
            
            # Verify logging
            assert len(caplog.records) == 1
            log_record = caplog.records[0]
            
            # Check log level
            assert log_record.levelname == "WARNING"
            
            # Check log message contains endpoint and method
            assert "POST" in log_record.message
            assert "/api/v1/interviews/continue" in log_record.message
            assert "2 field(s) failed validation" in log_record.message
    
    @pytest.mark.asyncio
    async def test_validation_error_handler_empty_location(self):
        """Test handler gracefully handles errors with empty location"""
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/v1/test"
        request.method = "GET"
        
        # Create validation error with minimal location
        exc = RequestValidationError([
            {
                "loc": ("body",),  # Only 'body', no field name
                "msg": "Invalid request body",
                "type": "value_error"
            }
        ])
        
        # Call handler
        response = await validation_exception_handler(request, exc)
        content = json.loads(response.body)
        
        # Should use "request" as fallback field name
        assert content["errors"][0]["field"] == "request"
        assert content["errors"][0]["error"] == "Invalid request body"
    
    @pytest.mark.asyncio
    async def test_validation_error_handler_missing_error_type(self):
        """Test handler handles missing error type gracefully"""
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/v1/test"
        request.method = "POST"
        
        # Create validation error without type field
        exc = RequestValidationError([
            {
                "loc": ("body", "field"),
                "msg": "Error message"
                # No "type" field
            }
        ])
        
        # Call handler
        response = await validation_exception_handler(request, exc)
        content = json.loads(response.body)
        
        # Should use default type
        assert content["errors"][0]["type"] == "validation_error"
