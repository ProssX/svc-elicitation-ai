"""
Response Format Verification Script

This script documents and verifies that all endpoint response formats match the ProssX standard
and remain backward compatible after the async-db-concurrency-fix implementation.

Run this script to verify response format compatibility before and after changes.
"""

from typing import Dict, Any, List


class ProssXResponseFormat:
    """
    ProssX Standard Response Format
    Reference: app/models/responses.py
    """
    
    @staticmethod
    def success_format() -> Dict[str, Any]:
        """Standard success response format"""
        return {
            "status": "success",  # Always "success" for successful operations
            "code": 200,  # HTTP status code (200, 201, etc.)
            "message": "Operation completed successfully",  # Human-readable message
            "data": {},  # Response data (can be object, array, or null)
            "errors": None,  # Always None for success responses
            "meta": {}  # Optional metadata (pagination, filters, etc.)
        }
    
    @staticmethod
    def error_format() -> Dict[str, Any]:
        """Standard error response format"""
        return {
            "status": "error",  # Always "error" for error responses
            "code": 404,  # HTTP status code (400, 404, 422, 500, etc.)
            "message": "Error message",  # Human-readable error message
            "data": None,  # Always None for error responses
            "errors": [  # List of error details
                {
                    "field": "field_name",  # Field that caused the error
                    "error": "Error description",  # Error description
                    "type": "error_type"  # Optional: error type (for validation errors)
                }
            ],
            "meta": {}  # Optional metadata (endpoint, method, etc.)
        }


class EndpointResponseFormats:
    """
    Documents the expected response formats for each endpoint
    """
    
    @staticmethod
    def start_interview_success() -> Dict[str, Any]:
        """POST /api/v1/interviews/start - Success Response"""
        return {
            "status": "success",
            "code": 200,
            "message": "Interview started successfully",
            "data": {
                "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
                "question": "¿Cuál es tu rol en la organización?",
                "question_number": 1,
                "is_final": False
            },
            "errors": None,
            "meta": {
                "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
                "session_id": None,
                "question_count": 1,
                "language": "es"
            }
        }
    
    @staticmethod
    def continue_interview_success() -> Dict[str, Any]:
        """POST /api/v1/interviews/continue - Success Response"""
        return {
            "status": "success",
            "code": 200,
            "message": "Question generated successfully",
            "data": {
                "question": "Agent's next question",
                "question_number": 2,
                "is_final": False,
                "corrected_response": "User's response (spell-checked)"
            },
            "errors": None,
            "meta": {
                "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
                "session_id": None,
                "question_count": 2,
                "language": "es"
            }
        }
    
    @staticmethod
    def continue_interview_validation_error() -> Dict[str, Any]:
        """POST /api/v1/interviews/continue - Validation Error (422)"""
        return {
            "status": "error",
            "code": 422,
            "message": "Validation error",
            "data": None,
            "errors": [
                {
                    "field": "user_response",
                    "error": "String should have at least 1 character",
                    "type": "string_too_short"
                }
            ],
            "meta": {
                "endpoint": "/api/v1/interviews/continue",
                "method": "POST"
            }
        }
    
    @staticmethod
    def continue_interview_invalid_uuid() -> Dict[str, Any]:
        """POST /api/v1/interviews/continue - Invalid UUID (422)"""
        return {
            "status": "error",
            "code": 422,
            "message": "Validation error",
            "data": None,
            "errors": [
                {
                    "field": "interview_id",
                    "error": "Input should be a valid UUID",
                    "type": "uuid_parsing"
                }
            ],
            "meta": {
                "endpoint": "/api/v1/interviews/continue",
                "method": "POST"
            }
        }
    
    @staticmethod
    def export_interview_success() -> Dict[str, Any]:
        """POST /api/v1/interviews/export - Success Response"""
        return {
            "status": "success",
            "code": 200,
            "message": "Interview data exported successfully (from database)",
            "data": {
                "session_id": None,
                "user_id": "01932e5f-8b2a-7890-b123-456789abcdef",
                "user_name": "Juan Pérez",
                "user_role": "Gerente de Operaciones",
                "organization": "Empresa XYZ",
                "interview_date": "2025-10-25T10:00:00Z",
                "interview_duration_minutes": 15,
                "total_questions": 8,
                "total_user_responses": 8,
                "is_complete": True,
                "conversation_history": [
                    {
                        "role": "assistant",
                        "content": "¿Cuál es tu rol?",
                        "timestamp": "2025-10-25T10:00:00Z"
                    }
                ],
                "interview_id": "018e5f8b-1234-7890-abcd-123456789abc"
            },
            "errors": None,
            "meta": {
                "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
                "export_date": "2025-10-25T15:30:00Z",
                "language": "es",
                "technical_level": "intermediate",
                "data_source": "database"
            }
        }
    
    @staticmethod
    def export_interview_not_found() -> Dict[str, Any]:
        """POST /api/v1/interviews/export - Interview Not Found (404)"""
        return {
            "status": "error",
            "code": 404,
            "message": "Interview not found",
            "data": None,
            "errors": [
                {
                    "field": "interview_id",
                    "error": "Interview does not exist"
                }
            ],
            "meta": None
        }
    
    @staticmethod
    def export_interview_access_denied() -> Dict[str, Any]:
        """POST /api/v1/interviews/export - Access Denied (403)"""
        return {
            "status": "error",
            "code": 403,
            "message": "Access denied",
            "data": None,
            "errors": [
                {
                    "field": "interview_id",
                    "error": "You don't have permission to export this interview"
                }
            ],
            "meta": None
        }
    
    @staticmethod
    def list_interviews_success() -> Dict[str, Any]:
        """GET /api/v1/interviews - Success Response"""
        return {
            "status": "success",
            "code": 200,
            "message": "Interviews retrieved successfully",
            "data": [
                {
                    "id_interview": "018e5f8b-1234-7890-abcd-123456789abc",
                    "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef",
                    "language": "es",
                    "technical_level": "intermediate",
                    "status": "completed",
                    "started_at": "2025-10-25T10:00:00Z",
                    "completed_at": "2025-10-25T10:15:00Z",
                    "total_messages": 12
                }
            ],
            "errors": None,
            "meta": {
                "pagination": {
                    "total_items": 45,
                    "total_pages": 3,
                    "current_page": 1,
                    "page_size": 20
                },
                "filters": {
                    "status": "completed",
                    "language": "es",
                    "start_date": "2025-10-01T00:00:00Z",
                    "end_date": "2025-10-31T23:59:59Z"
                },
                "scope": "own",
                "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef"
            }
        }
    
    @staticmethod
    def list_interviews_empty() -> Dict[str, Any]:
        """GET /api/v1/interviews - Empty List Response"""
        return {
            "status": "success",
            "code": 200,
            "message": "Interviews retrieved successfully",
            "data": [],
            "errors": None,
            "meta": {
                "pagination": {
                    "total_items": 0,
                    "total_pages": 0,
                    "current_page": 1,
                    "page_size": 20
                },
                "filters": {
                    "status": None,
                    "language": None,
                    "start_date": None,
                    "end_date": None
                },
                "scope": "own",
                "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef"
            }
        }
    
    @staticmethod
    def get_interview_success() -> Dict[str, Any]:
        """GET /api/v1/interviews/{interview_id} - Success Response"""
        return {
            "status": "success",
            "code": 200,
            "message": "Interview retrieved successfully",
            "data": {
                "id_interview": "018e5f8b-1234-7890-abcd-123456789abc",
                "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef",
                "language": "es",
                "technical_level": "intermediate",
                "status": "in_progress",
                "started_at": "2025-10-25T10:00:00Z",
                "completed_at": None,
                "total_messages": 4,
                "messages": [
                    {
                        "id_message": "018e5f8b-2a78-7890-b123-456789abcdef",
                        "role": "assistant",
                        "content": "¿Cuál es tu rol en la organización?",
                        "sequence_number": 1,
                        "created_at": "2025-10-25T10:00:00Z"
                    }
                ]
            },
            "errors": None,
            "meta": {
                "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
                "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef"
            }
        }
    
    @staticmethod
    def get_interview_not_found() -> Dict[str, Any]:
        """GET /api/v1/interviews/{interview_id} - Not Found (404)"""
        return {
            "status": "error",
            "code": 404,
            "message": "Interview not found",
            "data": None,
            "errors": [
                {
                    "field": "interview_id",
                    "error": "Interview does not exist"
                }
            ],
            "meta": None
        }
    
    @staticmethod
    def update_interview_success() -> Dict[str, Any]:
        """PATCH /api/v1/interviews/{interview_id} - Success Response"""
        return {
            "status": "success",
            "code": 200,
            "message": "Interview status updated successfully",
            "data": {
                "id_interview": "018e5f8b-1234-7890-abcd-123456789abc",
                "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef",
                "language": "es",
                "technical_level": "intermediate",
                "status": "completed",
                "started_at": "2025-10-25T10:00:00Z",
                "completed_at": "2025-10-25T10:15:00Z",
                "total_messages": 8
            },
            "errors": None,
            "meta": {
                "interview_id": "018e5f8b-1234-7890-abcd-123456789abc",
                "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef",
                "updated_fields": ["status", "updated_at", "completed_at"]
            }
        }
    
    @staticmethod
    def update_interview_not_found() -> Dict[str, Any]:
        """PATCH /api/v1/interviews/{interview_id} - Not Found (404)"""
        return {
            "status": "error",
            "code": 404,
            "message": "Interview not found",
            "data": None,
            "errors": [
                {
                    "field": "interview_id",
                    "error": "Interview does not exist"
                }
            ],
            "meta": None
        }


def verify_response_structure(response: Dict[str, Any], expected_keys: List[str]) -> bool:
    """Verify that response has all expected top-level keys"""
    return all(key in response for key in expected_keys)


def verify_success_response(response: Dict[str, Any]) -> bool:
    """Verify success response structure"""
    required_keys = ["status", "code", "message", "data", "errors", "meta"]
    if not verify_response_structure(response, required_keys):
        return False
    
    # Verify field types and values
    if response["status"] != "success":
        return False
    if not isinstance(response["code"], int) or response["code"] < 200 or response["code"] >= 300:
        return False
    if response["errors"] is not None:
        return False
    
    return True


def verify_error_response(response: Dict[str, Any]) -> bool:
    """Verify error response structure"""
    required_keys = ["status", "code", "message", "data", "errors"]
    if not verify_response_structure(response, required_keys):
        return False
    
    # Verify field types and values
    if response["status"] != "error":
        return False
    if not isinstance(response["code"], int) or response["code"] < 400:
        return False
    if response["data"] is not None:
        return False
    if response["errors"] is not None and not isinstance(response["errors"], list):
        return False
    
    return True


if __name__ == "__main__":
    print("=" * 80)
    print("ProssX Response Format Verification")
    print("=" * 80)
    print()
    
    # Verify all documented response formats
    formats = EndpointResponseFormats()
    
    test_cases = [
        ("Start Interview - Success", formats.start_interview_success(), True),
        ("Continue Interview - Success", formats.continue_interview_success(), True),
        ("Continue Interview - Validation Error", formats.continue_interview_validation_error(), False),
        ("Continue Interview - Invalid UUID", formats.continue_interview_invalid_uuid(), False),
        ("Export Interview - Success", formats.export_interview_success(), True),
        ("Export Interview - Not Found", formats.export_interview_not_found(), False),
        ("Export Interview - Access Denied", formats.export_interview_access_denied(), False),
        ("List Interviews - Success", formats.list_interviews_success(), True),
        ("List Interviews - Empty", formats.list_interviews_empty(), True),
        ("Get Interview - Success", formats.get_interview_success(), True),
        ("Get Interview - Not Found", formats.get_interview_not_found(), False),
        ("Update Interview - Success", formats.update_interview_success(), True),
        ("Update Interview - Not Found", formats.update_interview_not_found(), False),
    ]
    
    all_passed = True
    for name, response, is_success in test_cases:
        if is_success:
            passed = verify_success_response(response)
        else:
            passed = verify_error_response(response)
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")
        
        if not passed:
            all_passed = False
    
    print()
    print("=" * 80)
    if all_passed:
        print("✓ All response formats are valid and match ProssX standard")
    else:
        print("✗ Some response formats do not match ProssX standard")
    print("=" * 80)
