"""OpenAI model implementation for Vector."""

import os
from openai import OpenAI
from typing import Optional, Dict, Any

from .base import BaseAIModel
from ..config import Config
from ..exceptions import AIServiceError


class ModelConfig:
    """Configuration for different OpenAI models."""
    
    # Model parameter mappings
    MODEL_CONFIGS = {
        # GPT-4 models
        "gpt-4": {
            "max_tokens_param": "max_tokens",
            "supports_temperature": True,
            "supports_system_prompt": True,
            "default_max_tokens": 4000
        },
        "gpt-4-turbo": {
            "max_tokens_param": "max_tokens", 
            "supports_temperature": True,
            "supports_system_prompt": True,
            "default_max_tokens": 4000
        },
        "gpt-4o": {
            "max_tokens_param": "max_tokens",
            "supports_temperature": True,
            "supports_system_prompt": True,
            "default_max_tokens": 4000
        },
        "gpt-4o-mini": {
            "max_tokens_param": "max_tokens",
            "supports_temperature": True,
            "supports_system_prompt": True,
            "default_max_tokens": 4000
        },
        
        # GPT-5 models (new parameter structure)
        "gpt-5": {
            "max_tokens_param": "max_completion_tokens",
            "supports_temperature": False,
            "supports_system_prompt": True,
            "default_max_tokens": 100000
        },
        "gpt-5-mini": {
            "max_tokens_param": "max_completion_tokens",
            "supports_temperature": False,
            "supports_system_prompt": True,
            "default_max_tokens": 100000
        },
        "gpt-5-nano": {
            "max_tokens_param": "max_completion_tokens",
            "supports_temperature": False,
            "supports_system_prompt": True,
            "default_max_tokens": 100000
        },
        
        # GPT-3.5 models
        "gpt-3.5-turbo": {
            "max_tokens_param": "max_tokens",
            "supports_temperature": True,
            "supports_system_prompt": True,
            "default_max_tokens": 4000
        },
        
        # Legacy models (if needed)
        "text-davinci-003": {
            "max_tokens_param": "max_tokens",
            "supports_temperature": True,
            "supports_system_prompt": False,
            "default_max_tokens": 4000
        }
    }
    
    @classmethod
    def get_config(cls, model_name: str) -> Dict[str, Any]:
        """Get configuration for a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Configuration dictionary for the model
        """
        # Try exact match first
        if model_name in cls.MODEL_CONFIGS:
            return cls.MODEL_CONFIGS[model_name]
        
        # Try partial matches for model variants
        for config_model, config in cls.MODEL_CONFIGS.items():
            if model_name.startswith(config_model):
                return config
        
        # Default configuration for unknown models
        return {
            "max_tokens_param": "max_tokens",
            "supports_temperature": True,
            "supports_system_prompt": True,
            "default_max_tokens": 4000
        }


class OpenAIModel(BaseAIModel):
    """OpenAI GPT model implementation with multi-model support."""

    def __init__(self, config: Config):
        """Initialize OpenAI model.
        
        Args:
            config: Configuration object
        """
        # Try to get model name from either search or answer config
        model_name = (config.ai_search_model_name if hasattr(config, 'ai_search_model_name') 
                     else config.ai_answer_model_name)
        super().__init__(model_name)
        
        self.config = config
        self.api_key = config.openai_api_key
        
        # Use search model config as default, fall back to answer config
        try:
            self.max_tokens = config.ai_search_max_tokens
            self.temperature = config.ai_search_temperature
        except:
            self.max_tokens = config.ai_answer_max_tokens
            self.temperature = config.ai_answer_temperature
            
        self.provider = "openai"
        
        # Get model-specific configuration
        self.model_config = ModelConfig.get_config(model_name)
        
        if not self.api_key:
            raise AIServiceError("OpenAI API key not found")
        
        try:
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            raise AIServiceError(f"Failed to initialize OpenAI client: {e}")

    def _build_api_params(self, max_tokens: Optional[int] = None, 
                         temperature: Optional[float] = None) -> Dict[str, Any]:
        """Build API parameters based on model configuration.
        
        Args:
            max_tokens: Maximum tokens to generate
            temperature: Temperature for response generation
            
        Returns:
            Dictionary of API parameters
        """
        params = {
            "model": self.model_name
        }
        
        # Handle max_tokens parameter based on model
        if max_tokens:
            max_tokens_param = self.model_config["max_tokens_param"]
            params[max_tokens_param] = max_tokens
        
        # Handle temperature parameter
        if temperature is not None and self.model_config["supports_temperature"]:
            params["temperature"] = temperature
            
        return params

    def generate_response(self, prompt: str, system_prompt: str = "", 
                         max_tokens: Optional[int] = None, **kwargs) -> str:
        """Generate response using OpenAI API.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Generated response text
        """
        if not self.is_available():
            raise AIServiceError("OpenAI API not available")

        max_tokens = max_tokens or self.max_tokens
        temperature = kwargs.get('temperature', self.temperature)

        try:
            # Build messages based on model capabilities
            messages = []
            if system_prompt and self.model_config["supports_system_prompt"]:
                messages.append({"role": "system", "content": system_prompt})
            elif system_prompt and not self.model_config["supports_system_prompt"]:
                # For models that don't support system prompts, prepend to user message
                prompt = f"{system_prompt}\n\n{prompt}"
            
            messages.append({"role": "user", "content": prompt})

            # Build API parameters based on model configuration
            api_params = self._build_api_params(max_tokens, temperature)
            api_params["messages"] = messages

            response = self.client.chat.completions.create(**api_params)
            
            return response.choices[0].message.content.strip()

        except Exception as e:
            raise AIServiceError(f"OpenAI API error: {e}")

    def is_available(self) -> bool:
        """Check if OpenAI API is configured and available.
        
        Returns:
            True if API is available, False otherwise
        """
        return self.api_key is not None and self.client is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model configuration.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "provider": self.provider,
            "max_tokens_param": self.model_config["max_tokens_param"],
            "supports_temperature": self.model_config["supports_temperature"],
            "supports_system_prompt": self.model_config["supports_system_prompt"],
            "default_max_tokens": self.model_config["default_max_tokens"],
            "configured_max_tokens": self.max_tokens,
            "configured_temperature": self.temperature
        }

    def get_available_models(self):
        """Get a list of available models from OpenAI API.
        
        Returns:
            List of model names/IDs
        """
        try:
            models_response = self.client.models.list()
            # Handle the response format properly
            if hasattr(models_response, 'data'):
                return [model.id for model in models_response.data]
            else:
                # Fallback for different response format
                return [model.id for model in models_response]
        except Exception as e:
            raise AIServiceError(f"Failed to fetch available models: {e}")
