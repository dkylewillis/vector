"""Storage backend factory."""

from typing import Optional
from .base import StorageBackend
from .filesystem import FileSystemBackend
from ...config import Config


class StorageFactory:
    """Factory for creating storage backends."""
    
    @staticmethod
    async def create_backend(config: Config, backend_type: Optional[str] = None) -> StorageBackend:
        """Create and initialize storage backend.
        
        Args:
            config: Configuration instance
            backend_type: Override backend type ('filesystem', 'postgresql')
            
        Returns:
            Initialized storage backend
        """
        backend_type = backend_type or getattr(config, 'storage_backend', 'filesystem')
        
        if backend_type == 'filesystem':
            backend = FileSystemBackend(config)
        elif backend_type == 'postgresql':
            # Future implementation
            raise NotImplementedError("PostgreSQL backend not yet implemented")
        else:
            raise ValueError(f"Unknown storage backend: {backend_type}")
        
        await backend.initialize()
        return backend
