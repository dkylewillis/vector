"""Vector custom exceptions."""


class VectorError(Exception):
    """Base exception for Vector."""
    pass


class ConfigurationError(VectorError):
    """Raised when there's a configuration issue."""
    pass


class ValidationError(VectorError):
    """Raised when input validation fails."""
    pass


class AIServiceError(VectorError):
    """Raised when AI service encounters an error."""
    pass


class DatabaseError(VectorError):
    """Raised when vector database operations fail."""
    pass


class ProcessingError(VectorError):
    """Raised when document processing fails."""
    pass
