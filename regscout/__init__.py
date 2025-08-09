"""RegScout - AI-Powered Document Processing & Search."""

__version__ = "2.0.0"
__author__ = "RegScout Team"
__description__ = "AI-Powered Document Processing & Search for Municipal Documents"

# Main API exports
from .config import Config
from .core.agent import ResearchAgent
from .exceptions import RegScoutError

__all__ = [
    "Config",
    "ResearchAgent", 
    "RegScoutError",
]
