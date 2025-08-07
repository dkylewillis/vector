from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union


class Embedder:
    """
    A simple text embedder using sentence transformers.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedder with a pre-trained sentence transformer model.

        Args:
            model_name: Name of the sentence transformer model to use.
                       Default is 'all-MiniLM-L6-v2' which is lightweight and fast.
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_text(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for text(s).

        Args:
            text: Single text string or list of text strings to embed

        Returns:
            numpy array of embeddings. Shape: (1, embedding_dim) for single text,
            (n, embedding_dim) for list of texts
        """
        if isinstance(text, str):
            text = [text]

        embeddings = self.model.encode(text)
        return embeddings

    def embed_chunks(self, chunks: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of text chunks.

        Args:
            chunks: List of chunk texts to embed

        Returns:
            numpy array of shape (n_chunks, embedding_dim)
        """
        return self.embed_text(chunks)

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embeddings produced by this model.

        Returns:
            Integer dimension of embeddings
        """
        return self.model.get_sentence_embedding_dimension()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """
        Generate embeddings for a batch of texts with specified batch size.

        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process in each batch (default: 32)

        Returns:
            List of numpy arrays, where each array is an individual embedding
        """
        if not texts:
            return []

        # Process texts in batches
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(batch)
            # Convert to list of individual embeddings
            all_embeddings.extend(batch_embeddings.tolist())

        # Convert back to list of numpy arrays
        return [np.array(embedding) for embedding in all_embeddings]