from typing import Dict, Type, Any
from .base import BaseAIModel
from .openai_model import OpenAIModel

class AIModelFactory:
    """Factory for creating AI model instances."""
    
    _models: Dict[str, Type[BaseAIModel]] = {
        'openai': OpenAIModel,
        'gpt': OpenAIModel,  # Alias
        # Future models can be added here:
        # 'anthropic': AnthropicModel,
        # 'local': LocalModel,
    }
    
    @classmethod
    def create_model(cls, model_type: str, **kwargs) -> BaseAIModel:
        """
        Create an AI model instance.
        
        Args:
            model_type: Type of model ('openai', 'anthropic', etc.)
            **kwargs: Configuration parameters for the model
            
        Returns:
            Configured AI model instance
        """
        model_type = model_type.lower()
        
        if model_type not in cls._models:
            available = ', '.join(cls._models.keys())
            raise ValueError(f"Unknown model type '{model_type}'. Available: {available}")
        
        model_class = cls._models[model_type]
        return model_class(**kwargs)
    
    @classmethod
    def register_model(cls, model_type: str, model_class: Type[BaseAIModel]):
        """Register a new model type."""
        cls._models[model_type.lower()] = model_class
    
    @classmethod
    def available_models(cls) -> list:
        """Get list of available model types."""
        return list(cls._models.keys())
