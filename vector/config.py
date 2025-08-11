"""Unified configuration management for RegScout."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Simplified configuration manager."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to config file. Defaults to 'config.yaml' in project root.
        """
        self.config_path = config_path or self._find_config_file()
        self._config_data = self._load_config()
    
    def _find_config_file(self) -> str:
        """Find the config file in the project."""
        # Look for config.yaml in current directory and parent directories
        current = Path.cwd()
        for path in [current] + list(current.parents):
            config_file = path / "config.yaml"
            if config_file.exists():
                return str(config_file)
        
        raise FileNotFoundError("No config.yaml file found")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file) or {}
        except FileNotFoundError:
            print(f"Warning: Config file {self.config_path} not found. Using defaults.")
            return {}
        except yaml.YAMLError as e:
            print(f"Warning: Error parsing config file: {e}. Using defaults.")
            return {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation support.
        
        Args:
            key: Configuration key (supports dot notation like 'ai_model.name')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    @property
    def embedder_model(self) -> str:
        """Get embedder model name."""
        return self.get('embedder.model_name', 'sentence-transformers/all-MiniLM-L6-v2')
    
    # AI Model properties - Multi-model support only
    @property
    def ai_search_model_name(self) -> str:
        """Get search model name."""
        return self.get('ai_models.search.name', 'gpt-4o-mini')
    
    @property
    def ai_search_max_tokens(self) -> int:
        """Get search model max tokens."""
        return self.get('ai_models.search.max_tokens', 1000)
    
    @property
    def ai_search_temperature(self) -> float:
        """Get search model temperature."""
        return self.get('ai_models.search.temperature', 0.3)
    
    @property
    def ai_search_provider(self) -> str:
        """Get search model provider."""
        return self.get('ai_models.search.provider', 'openai')
    
    @property
    def ai_answer_model_name(self) -> str:
        """Get answer model name."""
        return self.get('ai_models.answer.name', 'gpt-4o-mini')
    
    @property
    def ai_answer_max_tokens(self) -> int:
        """Get answer model max tokens."""
        return self.get('ai_models.answer.max_tokens', 4000)
    
    @property
    def ai_answer_temperature(self) -> float:
        """Get answer model temperature."""
        return self.get('ai_models.answer.temperature', 0.3)
    
    @property
    def ai_answer_provider(self) -> str:
        """Get answer model provider."""
        return self.get('ai_models.answer.provider', 'openai')
    
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from environment or config."""
        # First try environment variable
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            return api_key
        
        # Then try config file
        return self.get('ai_model.api_key')
    
    @property
    def vector_db_path(self) -> Optional[str]:
        """Get vector database local path (deprecated)."""
        path = self.get('vector_database.local_path')
        if path:
            return path
        return './qdrant_db'
    
    @property
    def vector_db_url(self) -> Optional[str]:
        """Get vector database URL for cloud instance."""
        return self.get('vector_database.url')
    
    @property
    def vector_db_api_key(self) -> Optional[str]:
        """Get vector database API key from environment or config."""
        # First try environment variable
        api_key = os.getenv('QDRANT_API_KEY')
        if api_key:
            return api_key
        
        # Then try config file
        return self.get('vector_database.api_key')
    
    @property
    def use_cloud_qdrant(self) -> bool:
        """Check if cloud Qdrant should be used."""
        return self.vector_db_url is not None
    
    @property
    def default_collection(self) -> str:
        """Get default collection name."""
        return self.get('vector_database.collection_name', 'regscout_documents')
    
    @property
    def response_lengths(self) -> Dict[str, int]:
        """Get response length presets."""
        return self.get('response_lengths', {
            'short': 4000,
            'medium': 8000, 
            'long': 15000
        })
    
    def __getitem__(self, key: str) -> Any:
        """Support dict-like access for backward compatibility."""
        return self.get(key)
    
    def __contains__(self, key: str) -> bool:
        """Support 'in' operator."""
        return self.get(key) is not None
