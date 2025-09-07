"""Simplified text embedder for Vector."""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union, Tuple

from ..config import Config


# Forward declaration for type hints
class Chunk:
    """Forward declaration for Chunk class."""
    pass


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

    def embed_chunks(self, chunks: List['Chunk']) -> List[tuple]:
        """Generate embeddings for chunks and return with chunk objects.
        
        Args:
            chunks: List of Chunk objects to embed
            
        Returns:
            List of tuples (chunk, embedding_vector)
        """
        if not chunks:
            return []
        
        # Extract texts from chunks
        texts = [chunk.text for chunk in chunks]
        
        # Generate embeddings in batch
        embeddings = self.embed_texts(texts)
        
        # Return tuples of (chunk, embedding)
        return list(zip(chunks, embeddings))

    def embed_chunks_batch(self, chunks: List['Chunk'], batch_size: int = 32) -> List[tuple]:
        """Generate embeddings for chunks in batches and return with chunk objects.
        
        Args:
            chunks: List of Chunk objects to embed
            batch_size: Number of chunks to process in each batch
            
        Returns:
            List of tuples (chunk, embedding_vector)
        """
        if not chunks:
            return []
        
        chunks_with_embeddings = []
        
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_texts = [chunk.text for chunk in batch_chunks]
            
            # Generate embeddings for this batch
            batch_embeddings = self.embed_texts(batch_texts)
            
            # Combine chunks with their embeddings
            for chunk, embedding in zip(batch_chunks, batch_embeddings):
                chunks_with_embeddings.append((chunk, embedding))
        
        return chunks_with_embeddings
