from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseAIModel(ABC):
    """Base class for AI model integrations."""

    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.config = kwargs

    @abstractmethod
    def generate_response(
            self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """Generate a response based on prompt and optional context."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the model is available and configured."""
        pass
