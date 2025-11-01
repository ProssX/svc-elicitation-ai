"""
Custom exceptions for the elicitation AI service
"""
from uuid import UUID


class InterviewError(Exception):
    """Base exception for interview operations"""
    pass


class InterviewNotFoundError(InterviewError):
    """Raised when an interview is not found"""
    def __init__(self, interview_id: UUID, message: str = None):
        self.interview_id = interview_id
        self.message = message or f"Interview with ID {interview_id} not found"
        super().__init__(self.message)


class InterviewAccessDeniedError(InterviewError):
    """Raised when access to an interview is denied"""
    def __init__(self, interview_id: UUID, employee_id: UUID, message: str = None):
        self.interview_id = interview_id
        self.employee_id = employee_id
        self.message = message or f"Access denied to interview {interview_id} for employee {employee_id}"
        super().__init__(self.message)


class DatabaseConnectionError(Exception):
    """Raised when database connection fails"""
    def __init__(self, message: str = None):
        self.message = message or "Database connection failed"
        super().__init__(self.message)