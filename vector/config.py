"""Configuration management for Vector."""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from .exceptions import ConfigurationError

# Try to import dotenv to load .env files
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if it exists
except ImportError:
    # dotenv not available, continue without it
    pass


class Config:
    """Configuration manager for Vector system."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to configuration file. Defaults to 'config.yaml'
        """
        self.config_path = config_path or "config.yaml"
        self._config_data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            # Create default config if none exists
            default_config = self._get_default_config()
            with open(config_file, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False)
            return default_config
        
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigurationError(f"Failed to load config from {config_file}: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'ai_models': {
                'search': {
                    'name': 'gpt-3.5-turbo',
                    'max_tokens': 4000,
                    'temperature': 0.7,
                    'provider': 'openai'
                },
                'answer': {
                    'name': 'gpt-4',
                    'max_tokens': 15000,
                    'temperature': 0.7,
                    'provider': 'openai'
                }
            },
            'response_lengths': {
                'short': 500,
                'medium': 1000,
                'long': 2000
            },
            'vector_db': {
                'path': './qdrant_db'
            }
        }
    
    # AI Model Properties - Search
    @property
    def ai_search_model_name(self) -> str:
        return self._config_data.get('ai_models', {}).get('search', {}).get('name', 'gpt-3.5-turbo')
    
    @property
    def ai_search_max_tokens(self) -> int:
        return self._config_data.get('ai_models', {}).get('search', {}).get('max_tokens', 4000)
    
    @property
    def ai_search_temperature(self) -> float:
        return self._config_data.get('ai_models', {}).get('search', {}).get('temperature', 0.7)
    
    @property
    def ai_search_provider(self) -> str:
        return self._config_data.get('ai_models', {}).get('search', {}).get('provider', 'openai')
    
    # AI Model Properties - Answer
    @property
    def ai_answer_model_name(self) -> str:
        return self._config_data.get('ai_models', {}).get('answer', {}).get('name', 'gpt-4')
    
    @property
    def ai_answer_max_tokens(self) -> int:
        return self._config_data.get('ai_models', {}).get('answer', {}).get('max_tokens', 15000)
    
    @property
    def ai_answer_temperature(self) -> float:
        return self._config_data.get('ai_models', {}).get('answer', {}).get('temperature', 0.7)
    
    @property
    def ai_answer_provider(self) -> str:
        return self._config_data.get('ai_models', {}).get('answer', {}).get('provider', 'openai')
    
    # Response lengths
    @property
    def response_lengths(self) -> Dict[str, int]:
        return self._config_data.get('response_lengths', {
            'short': 500,
            'medium': 1000,
            'long': 2000
        })
    
    # Chat configuration
    @property
    def chat_max_history_messages(self) -> int:
        return self._config_data.get('chat', {}).get('max_history_messages', 40)
    
    @property
    def chat_summary_trigger_messages(self) -> int:
        return self._config_data.get('chat', {}).get('summary_trigger_messages', 14)
    
    @property
    def chat_max_context_results(self) -> int:
        return self._config_data.get('chat', {}).get('max_context_results', 40)
    
    @property
    def chat_default_top_k(self) -> int:
        return self._config_data.get('chat', {}).get('default_top_k', 12)
    
    # Vector database
    @property
    def vector_db_path(self) -> str:
        return self._config_data.get('vector_db', {}).get('path', './qdrant_db')
    
    # OpenAI API key
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from environment or config."""
        # First check environment variable
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            return api_key
        
        # Fall back to config file
        return self._config_data.get('openai', {}).get('api_key')
    
    # Storage configuration
    @property
    def storage_converted_documents_dir(self) -> str:
        """Get converted documents directory from config."""
        return self._config_data.get('storage', {}).get('converted_documents_dir', './data/converted_documents')
    
    @property 
    def storage_registry_dir(self) -> str:
        """Get registry directory from config."""
        return self._config_data.get('storage', {}).get('registry_dir', './vector_registry')