"""Core processing modules for Vector."""

from .embedder import Embedder
from .database import VectorDatabase
from .processor import DocumentProcessor
from .collection_manager import CollectionManager

__all__ = ['Embedder', 'VectorDatabase', 'DocumentProcessor', 'CollectionManager']
