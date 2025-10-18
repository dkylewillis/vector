"""Configuration management for Vector using pydantic-settings.

This module provides type-safe, validated configuration loaded from environment variables.
Environment variables can be set via .env file or system environment.

Nested configuration uses double underscore delimiter:
    AI_MODELS__SEARCH__NAME=gpt-5-nano
    VECTOR_DATABASE__URL=https://...

Example:
    >>> from vector.settings import settings
    >>> settings.ai_models.search.name
    'gpt-5-nano'
    >>> settings.openai_api_key
    'sk-proj-...'
"""

from typing import Optional
from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbedderConfig(BaseModel):
    """Embedding model configuration."""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"


class AIModelConfig(BaseModel):
    """Individual AI model configuration."""
    name: str
    max_tokens: int
    temperature: float
    provider: str


class AIModelsConfig(BaseModel):
    """AI models configuration for search and answer."""
    search: AIModelConfig = AIModelConfig(
        name="gpt-5-nano",
        max_tokens=4000,
        temperature=1.0,
        provider="openai",
    )
    answer: AIModelConfig = AIModelConfig(
        name="gpt-5",
        max_tokens=15000,
        temperature=1.0,
        provider="openai",
    )


class ResponseLengthsConfig(BaseModel):
    """Response length presets."""
    short: int = 4000
    medium: int = 8000
    long: int = 15000


class ChatConfig(BaseModel):
    """Chat configuration."""
    max_history_messages: int = 40
    summary_trigger_messages: int = 14
    max_context_results: int = 40
    default_top_k: int = 12


class VectorDatabaseConfig(BaseModel):
    """Vector database configuration."""
    url: Optional[str] = None
    api_key: Optional[str] = None
    local_path: str = "./qdrant_db"


class StorageConfig(BaseModel):
    """Storage paths configuration."""
    converted_documents_dir: str = "./data/converted_documents"
    registry_dir: str = "./vector_registry"


class Settings(BaseSettings):
    """Main settings class - loads from environment variables and .env file.
    
    Environment variables can override any setting using double underscore for nesting:
        OPENAI_API_KEY=sk-...
        AI_MODELS__SEARCH__NAME=gpt-5-nano
        VECTOR_DATABASE__URL=https://...
    
    Attributes:
        openai_api_key: OpenAI API key (from OPENAI_API_KEY)
        llama_cloud_api_key: Llama Cloud API key (from LLAMA_CLOUD_API_KEY)
        hf_token: HuggingFace token (from HF_TOKEN)
        qdrant_api_key: Qdrant API key (from QDRANT_API_KEY)
        qdrant_api_url: Qdrant API URL (from QDRANT_API_URL)
        runpod_api_key: RunPod API key (from RUNPOD_API_KEY)
        embedder: Embedding model configuration
        ai_models: AI models for search and answer
        response_lengths: Response length presets
        chat: Chat configuration
        vector_database: Vector database configuration
        storage: Storage paths configuration
    """
    
    # Secrets - loaded from environment variables
    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    llama_cloud_api_key: Optional[str] = Field(default=None, validation_alias="LLAMA_CLOUD_API_KEY")
    hf_token: Optional[str] = Field(default=None, validation_alias="HF_TOKEN")
    qdrant_api_key: Optional[str] = Field(default=None, validation_alias="QDRANT_API_KEY")
    qdrant_api_url: Optional[str] = Field(default=None, validation_alias="QDRANT_API_URL")
    runpod_api_key: Optional[str] = Field(default=None, validation_alias="RUNPOD_API_KEY")
    
    # Structured configuration
    embedder: EmbedderConfig = EmbedderConfig()
    ai_models: AIModelsConfig = AIModelsConfig()
    response_lengths: ResponseLengthsConfig = ResponseLengthsConfig()
    chat: ChatConfig = ChatConfig()
    vector_database: VectorDatabaseConfig = VectorDatabaseConfig()
    storage: StorageConfig = StorageConfig()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )
    
    # Convenience properties for backward compatibility
    
    @property
    def ai_search_model_name(self) -> str:
        """Search model name."""
        return self.ai_models.search.name
    
    @property
    def ai_search_max_tokens(self) -> int:
        """Search model max tokens."""
        return self.ai_models.search.max_tokens
    
    @property
    def ai_search_temperature(self) -> float:
        """Search model temperature."""
        return self.ai_models.search.temperature
    
    @property
    def ai_search_provider(self) -> str:
        """Search model provider."""
        return self.ai_models.search.provider
    
    @property
    def ai_answer_model_name(self) -> str:
        """Answer model name."""
        return self.ai_models.answer.name
    
    @property
    def ai_answer_max_tokens(self) -> int:
        """Answer model max tokens."""
        return self.ai_models.answer.max_tokens
    
    @property
    def ai_answer_temperature(self) -> float:
        """Answer model temperature."""
        return self.ai_models.answer.temperature
    
    @property
    def ai_answer_provider(self) -> str:
        """Answer model provider."""
        return self.ai_models.answer.provider
    
    @property
    def response_length_presets(self) -> dict:
        """Response length presets as dict."""
        return {
            "short": self.response_lengths.short,
            "medium": self.response_lengths.medium,
            "long": self.response_lengths.long,
        }
    
    @property
    def max_history_messages(self) -> int:
        """Max history messages for chat."""
        return self.chat.max_history_messages
    
    @property
    def summary_trigger_messages(self) -> int:
        """Trigger summarization after this many messages."""
        return self.chat.summary_trigger_messages
    
    @property
    def max_context_results(self) -> int:
        """Maximum search results to use for context."""
        return self.chat.max_context_results
    
    @property
    def default_top_k(self) -> int:
        """Default number of search results per chat turn."""
        return self.chat.default_top_k
    
    @property
    def embedder_model_name(self) -> str:
        """Embedder model name."""
        return self.embedder.model_name
    
    @property
    def converted_documents_dir(self) -> Path:
        """Converted documents directory path."""
        return Path(self.storage.converted_documents_dir)
    
    @property
    def registry_dir(self) -> Path:
        """Registry directory path."""
        return Path(self.storage.registry_dir)
    
    @property
    def qdrant_url(self) -> Optional[str]:
        """Qdrant URL - prefers qdrant_api_url, falls back to vector_database.url."""
        return self.qdrant_api_url or self.vector_database.url
    
    @property
    def qdrant_key(self) -> Optional[str]:
        """Qdrant API key - prefers qdrant_api_key, falls back to vector_database.api_key."""
        return self.qdrant_api_key or self.vector_database.api_key
    
    @property
    def qdrant_local_path(self) -> str:
        """Qdrant local storage path."""
        return self.vector_database.local_path


# Global settings instance
settings = Settings()
