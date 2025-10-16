"""Stores module - vector store implementations and factory.

This module provides vector store implementations and a factory for
creating store instances. All stores implement the VectorStore protocol
defined in vector.ports.
"""

from .base import BaseVectorStore, DistanceType
from .qdrant import QdrantVectorStore
from .factory import create_store

__all__ = [
    "BaseVectorStore",
    "DistanceType",
    "QdrantVectorStore",
    "create_store",
]
