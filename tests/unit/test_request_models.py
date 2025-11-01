"""
Unit tests for request model validation
"""
import pytest
from pydantic import ValidationError
from app.models.interview import ContinueInterviewRequest, ConversationMessage


class TestContinueInterviewRequestValidation:
    """Test suite for ContinueInterviewRequest model validation"""
    
    def test_valid_minimal_request_passes_validation(self):
        """Test valid minimal request passes validation"""
        # Create minimal valid request
        request = ContinueInterviewRequest(
            interview_id="018e5f8b-1234-7890-abcd-123456789abc",
            user_response="Soy responsable del proceso de compras",
            language="es"
        )
        
        # Assert all required fields are set
        assert str(request.interview_id) == "018e5f8b-1234-7890-abcd-123456789abc"
        assert request.user_response == "Soy responsable del proceso de compras"
        assert request.language == "es"
        
        # Assert optional fields default to None
        assert request.session_id is None
        assert request.conversation_history is None
    
    def test_empty_user_response_fails_validation(self):
        """Test empty user_response fails validation"""
        with pytest.raises(ValidationError) as exc_info:
            ContinueInterviewRequest(
                interview_id="018e5f8b-1234-7890-abcd-123456789abc",
                user_response="",  # Empty string
                language="es"
            )
        
        # Verify error is for user_response field
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("user_response",)
        assert errors[0]["type"] == "string_too_short"
    
    def test_user_response_exceeding_max_length_fails_validation(self):
        """Test user_response exceeding max_length fails validation"""
        # Create a response longer than 5000 characters
        long_response = "a" * 5001
        
        with pytest.raises(ValidationError) as exc_info:
            ContinueInterviewRequest(
                interview_id="018e5f8b-1234-7890-abcd-123456789abc",
                user_response=long_response,
                language="es"
            )
        
        # Verify error is for user_response field
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("user_response",)
        assert errors[0]["type"] == "string_too_long"
    
    def test_invalid_language_pattern_fails_validation(self):
        """Test invalid language pattern fails validation"""
        with pytest.raises(ValidationError) as exc_info:
            ContinueInterviewRequest(
                interview_id="018e5f8b-1234-7890-abcd-123456789abc",
                user_response="Mi respuesta",
                language="fr"  # French not supported
            )
        
        # Verify error is for language field
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("language",)
        assert errors[0]["type"] == "string_pattern_mismatch"
    
    def test_legacy_fields_are_optional(self):
        """Test legacy fields (session_id, conversation_history) are optional"""
        # Create request without legacy fields
        request = ContinueInterviewRequest(
            interview_id="018e5f8b-1234-7890-abcd-123456789abc",
            user_response="Mi respuesta",
            language="es"
        )
        
        # Verify legacy fields are None
        assert request.session_id is None
        assert request.conversation_history is None
    
    def test_request_with_legacy_fields_validates_successfully(self):
        """Test request with legacy fields still validates successfully"""
        # Create request with legacy fields
        request = ContinueInterviewRequest(
            interview_id="018e5f8b-1234-7890-abcd-123456789abc",
            session_id="550e8400-e29b-41d4-a716-446655440000",
            user_response="Mi respuesta",
            conversation_history=[
                ConversationMessage(
                    role="assistant",
                    content="¿Cuál es tu rol?",
                    timestamp=None
                ),
                ConversationMessage(
                    role="user",
                    content="Soy gerente",
                    timestamp=None
                )
            ],
            language="es"
        )
        
        # Verify all fields are set correctly
        assert str(request.interview_id) == "018e5f8b-1234-7890-abcd-123456789abc"
        assert request.session_id == "550e8400-e29b-41d4-a716-446655440000"
        assert request.user_response == "Mi respuesta"
        assert request.language == "es"
        assert request.conversation_history is not None
        assert len(request.conversation_history) == 2
    
    def test_valid_language_codes(self):
        """Test all valid language codes pass validation"""
        valid_languages = ["es", "en", "pt"]
        
        for lang in valid_languages:
            request = ContinueInterviewRequest(
                interview_id="018e5f8b-1234-7890-abcd-123456789abc",
                user_response="Test response",
                language=lang
            )
            assert request.language == lang
    
    def test_user_response_at_min_length_boundary(self):
        """Test user_response with exactly 1 character passes validation"""
        request = ContinueInterviewRequest(
            interview_id="018e5f8b-1234-7890-abcd-123456789abc",
            user_response="a",  # Exactly 1 character
            language="es"
        )
        assert request.user_response == "a"
    
    def test_user_response_at_max_length_boundary(self):
        """Test user_response with exactly 5000 characters passes validation"""
        max_response = "a" * 5000  # Exactly 5000 characters
        
        request = ContinueInterviewRequest(
            interview_id="018e5f8b-1234-7890-abcd-123456789abc",
            user_response=max_response,
            language="es"
        )
        assert len(request.user_response) == 5000
    
    def test_default_language_is_spanish(self):
        """Test default language is 'es' when not provided"""
        request = ContinueInterviewRequest(
            interview_id="018e5f8b-1234-7890-abcd-123456789abc",
            user_response="Mi respuesta"
            # language not provided
        )
        assert request.language == "es"
    
    def test_multiple_validation_errors(self):
        """Test multiple validation errors are reported together"""
        with pytest.raises(ValidationError) as exc_info:
            ContinueInterviewRequest(
                interview_id="018e5f8b-1234-7890-abcd-123456789abc",
                user_response="",  # Empty (invalid)
                language="fr"  # Invalid language
            )
        
        # Verify both errors are reported
        errors = exc_info.value.errors()
        assert len(errors) == 2
        
        error_fields = [error["loc"][0] for error in errors]
        assert "user_response" in error_fields
        assert "language" in error_fields
