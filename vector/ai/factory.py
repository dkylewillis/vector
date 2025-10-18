"""AI Model Factory for creating different AI providers."""

from typing import Dict, Any, Type, List
from ..settings import Settings, settings
from ..exceptions import AIServiceError
from .base import BaseAIModel
from .openai import OpenAIModel


class AIModelFactory:
    """Factory for creating AI models from different providers."""
    
    # Registry of available providers
    _providers: Dict[str, Type[BaseAIModel]] = {
        "openai": OpenAIModel,
        # Future providers will be added here
        # "anthropic": AnthropicModel,
        # "google": GoogleModel,
        # "azure": AzureOpenAIModel,
    }
    
    @classmethod
    def register_provider(cls, name: str, model_class: Type[BaseAIModel]):
        """Register a new AI provider.
        
        Args:
            name: Provider name (e.g., 'anthropic', 'google')
            model_class: Model class implementing BaseAIModel
        """
        cls._providers[name] = model_class
    
    @classmethod
    def create_model(cls, config_or_settings: Settings, model_type: str) -> BaseAIModel:
        """Create an AI model instance.
        
        Args:
            config_or_settings: Settings object (Config deprecated but accepted for compat)
            model_type: Type of model ('search' or 'answer')
            
        Returns:
            AI model instance
            
        Raises:
            AIServiceError: If provider is not supported or model_type is invalid
        """
        if model_type not in ['search', 'answer']:
            raise AIServiceError(f"Invalid model type: {model_type}. Must be 'search' or 'answer'")
        
        # Get model configuration based on type
        model_config = cls._get_model_config(config_or_settings, model_type)
        provider = model_config.get('provider', 'openai').lower()
        
        if provider not in cls._providers:
            raise AIServiceError(f"Unsupported AI provider: {provider}")
        
        # Create model-specific settings wrapper
        temp_settings = cls._create_temp_settings(config_or_settings, model_config)
        
        # Create and return the model
        model_class = cls._providers[provider]
        return model_class(temp_settings)
    
    @classmethod
    def _get_model_config(cls, config_or_settings: Settings, model_type: str) -> Dict[str, Any]:
        """Get configuration for specific model type.
        
        Args:
            config_or_settings: Settings object
            model_type: Type of model ('search' or 'answer')
            
        Returns:
            Model configuration dictionary
        """
        # Handle both Settings and old Config for backward compat
        if isinstance(config_or_settings, Settings):
            cfg = config_or_settings
        else:
            # Fall back to global settings if old Config passed
            cfg = settings
            
        if model_type == 'search':
            return {
                'name': cfg.ai_search_model_name,
                'max_tokens': cfg.ai_search_max_tokens,
                'temperature': cfg.ai_search_temperature,
                'provider': cfg.ai_search_provider
            }
        elif model_type == 'answer':
            return {
                'name': cfg.ai_answer_model_name,
                'max_tokens': cfg.ai_answer_max_tokens,
                'temperature': cfg.ai_answer_temperature,
                'provider': cfg.ai_answer_provider
            }
        else:
            raise AIServiceError(f"Unknown model type: {model_type}")
    
    @classmethod
    def _create_temp_settings(cls, base_settings: Settings, model_config: Dict[str, Any]) -> Settings:
        """Create a temporary settings wrapper with specific model settings.
        
        Args:
            base_settings: Base settings object
            model_config: Model-specific configuration
            
        Returns:
            Settings object with overridden model config
        """
        # Create a simple object to mock the necessary attributes for OpenAI model
        class TempSettings:
            def __init__(self, model_cfg: Dict[str, Any], base: Settings):
                self.openai_api_key = base.openai_api_key
                self.ai_search_model_name = model_cfg['name']
                self.ai_search_max_tokens = model_cfg['max_tokens']
                self.ai_search_temperature = model_cfg['temperature']
                self.ai_answer_model_name = model_cfg['name']
                self.ai_answer_max_tokens = model_cfg['max_tokens']
                self.ai_answer_temperature = model_cfg['temperature']
        
        return TempSettings(model_config, settings)
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available providers.
        
        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
