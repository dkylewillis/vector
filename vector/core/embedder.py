"""Simplified text embedder for Vector."""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union

from ..config import Config


class Embedder:
    """Text embedder using sentence transformers."""

    def __init__(self, config: Config):
        """Initialize the embedder.

        Args:
            config: Configuration object
        """
        self.config = config
        self.model_name = config.embedder_model
        self.model = SentenceTransformer(self.model_name)

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            List of float values representing the embedding
        """
        embedding = self.model.encode([text])[0]
        return embedding.tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embeddings, each as a list of float values
        """
        if not texts:
            return []
        
        embeddings = self.model.encode(texts)
        return [embedding.tolist() for embedding in embeddings]

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings.

        Returns:
            Integer dimension of embeddings
        """
        return self.model.get_sentence_embedding_dimension()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for texts in batches.

        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process in each batch

        Returns:
            List of embeddings, each as a list of float values
        """
        if not texts:
            return []

        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(batch)
            all_embeddings.extend([embedding.tolist() for embedding in batch_embeddings])

        return all_embeddings
