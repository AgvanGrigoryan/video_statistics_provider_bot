
class ServiceError(Exception):
    """Base exception for all service-level errors.
    
    Provides consistent interface:
    - message: Technical message for logs
    - user_message: User-friendly message for UI
    """
    
    def __init__(self, message: str, user_message: str | None = None):
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message


class LLMServiceError(ServiceError):
    """LLM provider errors (network, auth, rate limits)."""
    pass

class NLPParseError(ServiceError):
    """NLP parsing/validation errors."""
    pass


class QueryBuildError(ServiceError):
    """SQL generation errors."""
    pass


class DatabaseError(ServiceError):
    """Database execution errors."""
    pass
