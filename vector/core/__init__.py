"""Core processing modules for Vector."""

from .embedder import Embedder
from .database import VectorDatabase
from .processor import DocumentProcessor
from .collection_manager import CollectionManager
from .document_manager import DocumentManager

__all__ = ['Embedder', 'VectorDatabase', 'DocumentProcessor', 'CollectionManager', 'DocumentManager']
