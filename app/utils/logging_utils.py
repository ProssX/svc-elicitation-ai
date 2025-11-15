"""
Logging Utilities

Provides utilities for safe logging that prevents exposure of sensitive data.
"""
import re
from typing import Any, Dict, Optional


# Sensitive field patterns to redact
SENSITIVE_FIELDS = {
    "auth_token",
    "authorization",
    "password",
    "secret",
    "api_key",
    "access_token",
    "refresh_token",
    "jwt",
    "bearer",
    "credentials",
    "private_key",
    "session_id",
    "cookie"
}


def sanitize_log_data(data: Any, redact_text: str = "[REDACTED]") -> Any:
    """
    Sanitize data for logging by redacting sensitive fields.
    
    Recursively processes dictionaries and lists to remove sensitive information
    before logging. This prevents accidental exposure of tokens, passwords, and
    other sensitive data in log files.
    
    Args:
        data: Data to sanitize (dict, list, or primitive)
        redact_text: Text to use for redacted values
        
    Returns:
        Sanitized copy of the data with sensitive fields redacted
        
    Example:
        >>> data = {"user": "john", "auth_token": "secret123"}
        >>> sanitize_log_data(data)
        {"user": "john", "auth_token": "[REDACTED]"}
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Check if key is sensitive (case-insensitive)
            if key.lower() in SENSITIVE_FIELDS or _is_sensitive_key(key):
                sanitized[key] = redact_text
            else:
                # Recursively sanitize nested structures
                sanitized[key] = sanitize_log_data(value, redact_text)
        return sanitized
    
    elif isinstance(data, list):
        return [sanitize_log_data(item, redact_text) for item in data]
    
    elif isinstance(data, tuple):
        return tuple(sanitize_log_data(item, redact_text) for item in data)
    
    else:
        # Primitive types (str, int, bool, etc.) are returned as-is
        return data


def _is_sensitive_key(key: str) -> bool:
    """
    Check if a key name suggests it contains sensitive data.
    
    Uses pattern matching to identify keys that likely contain sensitive
    information even if they're not in the explicit SENSITIVE_FIELDS set.
    
    Args:
        key: Dictionary key to check
        
    Returns:
        True if key appears to be sensitive, False otherwise
    """
    key_lower = key.lower()
    
    # Check for common sensitive patterns
    sensitive_patterns = [
        r".*token.*",
        r".*password.*",
        r".*secret.*",
        r".*key.*",
        r".*auth.*",
        r".*credential.*",
        r".*bearer.*",
        r".*session.*"
    ]
    
    for pattern in sensitive_patterns:
        if re.match(pattern, key_lower):
            return True
    
    return False


def truncate_for_logging(text: str, max_length: int = 100) -> str:
    """
    Truncate long text for logging to prevent log bloat.
    
    Useful for logging user responses or process descriptions without
    filling logs with excessive content.
    
    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        
    Returns:
        Truncated text with ellipsis if needed
        
    Example:
        >>> truncate_for_logging("A very long text...", max_length=10)
        "A very lo..."
    """
    if not text:
        return text
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."


def create_safe_log_context(
    employee_id: Optional[str] = None,
    interview_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a safe logging context dictionary with common fields.
    
    Provides a standardized way to create logging context that includes
    common identifiers while automatically sanitizing any sensitive data
    passed in kwargs.
    
    Args:
        employee_id: Employee UUID (optional)
        interview_id: Interview UUID (optional)
        organization_id: Organization ID (optional)
        **kwargs: Additional context fields (will be sanitized)
        
    Returns:
        Dictionary safe for logging with structured context
        
    Example:
        >>> context = create_safe_log_context(
        ...     employee_id="123",
        ...     auth_token="secret"
        ... )
        >>> context
        {"employee_id": "123", "auth_token": "[REDACTED]"}
    """
    context = {}
    
    # Add standard identifiers
    if employee_id:
        context["employee_id"] = str(employee_id)
    if interview_id:
        context["interview_id"] = str(interview_id)
    if organization_id:
        context["organization_id"] = str(organization_id)
    
    # Add and sanitize additional fields
    sanitized_kwargs = sanitize_log_data(kwargs)
    context.update(sanitized_kwargs)
    
    return context


def mask_pii(text: str) -> str:
    """
    Mask potential PII (Personally Identifiable Information) in text.
    
    Uses pattern matching to identify and mask common PII patterns like
    email addresses, phone numbers, etc.
    
    Args:
        text: Text that may contain PII
        
    Returns:
        Text with PII patterns masked
        
    Example:
        >>> mask_pii("Contact john@example.com or 555-1234")
        "Contact [EMAIL] or [PHONE]"
    """
    if not text:
        return text
    
    # Mask email addresses
    text = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL]',
        text
    )
    
    # Mask phone numbers (various formats)
    text = re.sub(
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        '[PHONE]',
        text
    )
    
    # Mask credit card numbers (basic pattern)
    text = re.sub(
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        '[CARD]',
        text
    )
    
    # Mask SSN-like patterns
    text = re.sub(
        r'\b\d{3}-\d{2}-\d{4}\b',
        '[SSN]',
        text
    )
    
    return text
