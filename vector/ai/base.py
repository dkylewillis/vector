"""AI model implementations for RegScout."""

from abc import ABC, abstractmethod
from typing import Optional


class BaseAIModel(ABC):
    """Base class for AI model implementations."""

    def __init__(self, model_name: str, **kwargs):
        """Initialize the AI model.
        
        Args:
            model_name: Name of the model
            **kwargs: Additional configuration parameters
        """
        self.model_name = model_name
        self.config = kwargs

    @abstractmethod
    def generate_response(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        """Generate a response from the AI model.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            **kwargs: Additional parameters
            
        Returns:
            Generated response text
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the model is available and configured.
        
        Returns:
            True if model is available, False otherwise
        """
        pass
