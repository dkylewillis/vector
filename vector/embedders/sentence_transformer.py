"""SentenceTransformer-based text embedder.

This module provides a text embedder using the sentence-transformers library.
It implements the Embedder protocol from vector.ports.
"""

from sentence_transformers import SentenceTransformer
from typing import List


class SentenceTransformerEmbedder:
    """Text embedder using sentence transformers.
    
    This implementation uses the sentence-transformers library to generate
    embeddings. It automatically implements the Embedder protocol through
    structural typing (duck typing).
    
    Example:
        >>> embedder = SentenceTransformerEmbedder()
        >>> embedding = embedder.embed_text("Hello, world!")
        >>> print(len(embedding))
        384
        >>> 
        >>> # Batch processing
        >>> texts = ["First text", "Second text", "Third text"]
        >>> embeddings = embedder.embed_texts(texts)
        >>> print(len(embeddings))
        3
    """
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the embedder with a specific model.
        
        Args:
            model_name: Name of the sentence-transformers model to use.
                       Default is "sentence-transformers/all-MiniLM-L6-v2" (384 dims)
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            List of float values representing the embedding
        """
        embedding = self.model.encode([text], show_progress_bar=False)[0]
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batch processing).
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embeddings, each as a list of float values
        """
        if not texts:
            return []
        
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return [embedding.tolist() for embedding in embeddings]
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings produced by this model.
        
        Returns:
            Integer dimension of embeddings (e.g., 384 for all-MiniLM-L6-v2)
        """
        return self.model.get_sentence_embedding_dimension()
