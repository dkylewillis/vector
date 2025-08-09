"""RegScout custom exceptions."""


class RegScoutError(Exception):
    """Base exception for RegScout."""
    pass


class ConfigurationError(RegScoutError):
    """Raised when there's a configuration issue."""
    pass


class ValidationError(RegScoutError):
    """Raised when input validation fails."""
    pass


class AIServiceError(RegScoutError):
    """Raised when AI service encounters an error."""
    pass


class DatabaseError(RegScoutError):
    """Raised when vector database operations fail."""
    pass


class ProcessingError(RegScoutError):
    """Raised when document processing fails."""
    pass
