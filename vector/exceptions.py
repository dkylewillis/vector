"""Vector system exceptions."""


class VectorError(Exception):
    """Base exception for Vector system errors."""
    pass


class AIServiceError(VectorError):
    """Exception for AI service related errors."""
    pass


class DatabaseError(VectorError):
    """Exception for database related errors."""
    pass


class ConfigurationError(VectorError):
    """Exception for configuration related errors."""
    pass