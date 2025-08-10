"""Vector - AI-Powered Document Processing & Search."""

__version__ = "2.0.0"
__author__ = "Vector Team"
__description__ = "AI-Powered Document Processing & Search"

# Main API exports
from .config import Config
from .core.agent import ResearchAgent
from .exceptions import VectorError

__all__ = [
    "Config",
    "ResearchAgent", 
    "VectorError",
]
