"""OpenAI model implementation for RegScout."""

import os
from openai import OpenAI
from typing import Optional

from .base import BaseAIModel
from ..config import Config
from ..exceptions import AIServiceError


class OpenAIModel(BaseAIModel):
    """OpenAI GPT model implementation."""

    def __init__(self, config: Config):
        """Initialize OpenAI model.
        
        Args:
            config: Configuration object
        """
        model_name = config.ai_model_name
        super().__init__(model_name)
        
        self.config = config
        self.api_key = config.openai_api_key
        self.max_tokens = config.ai_max_tokens
        self.temperature = config.ai_temperature
        
        if not self.api_key:
            raise AIServiceError("OpenAI API key not found")
        
        try:
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            raise AIServiceError(f"Failed to initialize OpenAI client: {e}")

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
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content.strip()

        except Exception as e:
            raise AIServiceError(f"OpenAI API error: {e}")

    def is_available(self) -> bool:
        """Check if OpenAI API is configured and available.
        
        Returns:
            True if API is available, False otherwise
        """
        return self.api_key is not None and self.client is not None
