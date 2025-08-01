import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Configuration loader for RegScout settings."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_path: Path to the configuration file. If None, uses default location.
        """
        if config_path is None:
            # Default to config/settings.yaml relative to project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "settings.yaml"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                return config or {}
        except FileNotFoundError:
            print(f"Configuration file not found: {self.config_path}")
            return {}
        except yaml.YAMLError as e:
            print(f"Error parsing YAML configuration: {e}")
            return {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., 'embedder.model_name')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.
        
        Args:
            section: Section name (e.g., 'embedder', 'vector_database')
            
        Returns:
            Dictionary containing section configuration
        """
        return self._config.get(section, {})
    
    def update(self, key: str, value: Any) -> None:
        """
        Update a configuration value.
        
        Args:
            key: Configuration key using dot notation
            value: New value to set
        """
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the final value
        config[keys[-1]] = value
    
    def save(self) -> None:
        """Save current configuration back to file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(self._config, file, default_flow_style=False, indent=2)
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    @property
    def embedder(self) -> Dict[str, Any]:
        """Get embedder configuration."""
        return self.get_section('embedder')
    
    @property
    def ai_model(self) -> Dict[str, Any]:
        """Get AI model configuration."""
        return self.get_section('ai_model')
    
    @property
    def question_answering(self) -> Dict[str, Any]:
        """Get question answering configuration."""
        return self.get_section('question_answering')
    
    @property
    def vector_database(self) -> Dict[str, Any]:
        """Get vector database configuration."""
        return self.get_section('vector_database')
    
    @property
    def file_processing(self) -> Dict[str, Any]:
        """Get file processing configuration."""
        return self.get_section('file_processing')
    
    @property
    def data_paths(self) -> Dict[str, Any]:
        """Get data paths configuration."""
        return self.get_section('data')
    
    @property
    def search(self) -> Dict[str, Any]:
        """Get search configuration."""
        return self.get_section('search')


# Global configuration instance
config = Config()


# Example usage functions
def get_embedder_config() -> Dict[str, Any]:
    """Get embedder configuration settings."""
    return config.embedder

def get_ai_model_config() -> Dict[str, Any]:
    """Get AI model configuration settings."""
    return config.ai_model

def get_question_answering_config() -> Dict[str, Any]:
    """Get question answering configuration settings."""
    return config.question_answering

def get_vector_db_config() -> Dict[str, Any]:
    """Get vector database configuration settings."""
    return config.vector_database

def get_file_processing_config() -> Dict[str, Any]:
    """Get file processing configuration settings."""
    return config.file_processing


if __name__ == "__main__":
    # Example usage
    cfg = Config()
    
    print("Embedder model:", cfg.get('embedder.model_name'))
    print("AI model:", cfg.get('ai_model.name'))
    print("Vector DB host:", cfg.get('vector_database.host'))
    print("Default batch size:", cfg.get('embedder.batch_size'))
    print("PDF OCR enabled:", cfg.get('file_processing.pdf.do_ocr'))
    print("QA max tokens:", cfg.get('question_answering.max_tokens'))
    
    print("\nEmbedder section:")
    print(cfg.embedder)
    
    print("\nAI Model section:")
    print(cfg.ai_model)
    
    print("\nQuestion Answering section:")
    print(cfg.question_answering)
    
    print("\nVector database section:")
    print(cfg.vector_database)
