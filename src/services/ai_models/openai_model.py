import os
from openai import OpenAI
from .base import BaseAIModel
from typing import List, Dict, Any, Optional

class OpenAIModel(BaseAIModel):
    """OpenAI GPT model implementation."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", api_key: Optional[str] = None, **kwargs):
        super().__init__(model_name, **kwargs)
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.max_tokens = kwargs.get('max_tokens', 512)
        self.temperature = kwargs.get('temperature', 0.1)
    
    def generate_response(self, user_prompt: str, system_prompt: str) -> str:
        """Generate response using OpenAI API."""
        if not self.is_available():
            return "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system", 
                        "content": system_prompt if system_prompt else "You are a helpful assistant."
                    },
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def is_available(self) -> bool:
        """Check if OpenAI API is configured."""
        return self.api_key is not None and self.client is not None
