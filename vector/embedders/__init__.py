"""Embedders module - text embedding implementations.

This module provides various text embedding implementations that conform
to the Embedder protocol defined in vector.ports.
"""

from .sentence_transformer import SentenceTransformerEmbedder

__all__ = [
    "SentenceTransformerEmbedder",
]
