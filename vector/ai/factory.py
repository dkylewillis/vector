"""AI Model Factory for creating different AI providers."""

from typing import Dict, Any, Type, List
from ..config import Config
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
    def create_model(cls, config: Config, model_type: str) -> BaseAIModel:
        """Create an AI model instance.
        
        Args:
            config: Configuration object
            model_type: Type of model ('search' or 'answer')
            
        Returns:
            AI model instance
            
        Raises:
            AIServiceError: If provider is not supported or model_type is invalid
        """
        if model_type not in ['search', 'answer']:
            raise AIServiceError(f"Invalid model type: {model_type}. Must be 'search' or 'answer'")
        
        # Get model configuration based on type
        model_config = cls._get_model_config(config, model_type)
        provider = model_config.get('provider', 'openai').lower()
        
        if provider not in cls._providers:
            raise AIServiceError(f"Unsupported AI provider: {provider}")
        
        # Create a temporary config object with the specific model settings
        temp_config = cls._create_temp_config(config, model_config)
        
        # Create and return the model
        model_class = cls._providers[provider]
        return model_class(temp_config)
    
    @classmethod
    def _get_model_config(cls, config: Config, model_type: str) -> Dict[str, Any]:
        """Get configuration for specific model type.
        
        Args:
            config: Main configuration object
            model_type: Type of model ('search' or 'answer')
            
        Returns:
            Model configuration dictionary
        """
        if model_type == 'search':
            return {
                'name': config.ai_search_model_name,
                'max_tokens': config.ai_search_max_tokens,
                'temperature': config.ai_search_temperature,
                'provider': config.ai_search_provider
            }
        elif model_type == 'answer':
            return {
                'name': config.ai_answer_model_name,
                'max_tokens': config.ai_answer_max_tokens,
                'temperature': config.ai_answer_temperature,
                'provider': config.ai_answer_provider
            }
        else:
            raise AIServiceError(f"Unknown model type: {model_type}")
    
    @classmethod
    def _create_temp_config(cls, base_config: Config, model_config: Dict[str, Any]) -> Config:
        """Create a temporary config object with specific model settings.
        
        Args:
            base_config: Base configuration object
            model_config: Model-specific configuration
            
        Returns:
            Temporary configuration object
        """
        # Create a copy of the base config
        temp_config = Config(base_config.config_path)
        
        # Override ai_models section with specific model settings for OpenAI compatibility
        temp_config._config_data['ai_models'] = {
            'search': {
                'name': model_config['name'],
                'max_tokens': model_config['max_tokens'],
                'temperature': model_config['temperature'],
                'provider': model_config['provider']
            },
            'answer': {
                'name': model_config['name'],
                'max_tokens': model_config['max_tokens'],
                'temperature': model_config['temperature'],
                'provider': model_config['provider']
            }
        }
        
        return temp_config
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available providers.
        
        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
