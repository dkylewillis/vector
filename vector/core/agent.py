"""Simplified Research Agent for Vector."""

import warnings
from typing import List, Dict, Any, Optional

from ..config import Config
from ..exceptions import VectorError, AIServiceError, DatabaseError
from ..interfaces import SearchResult
from .embedder import Embedder
from .database import VectorDatabase
from .processor import DocumentProcessor
from ..ai.factory import AIModelFactory
from ..utils.formatting import CLIFormatter

warnings.filterwarnings("ignore", category=FutureWarning, module="torch.nn.modules.module")


class ResearchAgent:
    """
    Simplified research agent that handles search, AI interactions, and document processing.
    """

    def __init__(self, config: Config, collection_name: str):
        """Initialize the research agent.

        Args:
            config: Configuration object
            collection_name: Name of the vector collection
        """
        self.config = config
        self.collection_name = collection_name
        
        # Initialize components
        self.embedder = Embedder(config)
        self.vector_db = VectorDatabase(collection_name, config)
        self.processor = DocumentProcessor(config)
        
        # Initialize AI models using factory
        self.search_ai_model = AIModelFactory.create_model(config, 'search')
        self.answer_ai_model = AIModelFactory.create_model(config, 'answer')
        
        self.formatter = CLIFormatter()

    def setup_collection(self) -> int:
        """Setup the vector database collection with appropriate dimensions."""
        vector_size = self.embedder.get_embedding_dimension()
        self.vector_db.create_collection(vector_size=vector_size)
        
        # Ensure all metadata indexes exist
        self.vector_db.ensure_indexes()
        
        return vector_size

    def search(self, query: str, top_k: int = 5, metadata_filter: Optional[Dict] = None) -> str:
        """Search for relevant documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            metadata_filter: Optional metadata filter
            
        Returns:
            Formatted search results
        """
        try:
            if not query.strip():
                raise VectorError("Search query cannot be empty")
            
            # Embed the query
            query_vector = self.embedder.embed_text(query)
            
            # Search the vector database
            results = self.vector_db.search(query_vector, top_k, metadata_filter)
            
            # Format and return results
            return self.formatter.format_search_results(results)
            
        except Exception as e:
            raise VectorError(f"Search failed: {e}")

    def ask(self, question: str, response_length: str = 'medium', 
            metadata_filter: Optional[Dict] = None) -> str:
        """Ask AI a question about the documents.
        
        Args:
            question: Question to ask
            response_length: Response length (short/medium/long)
            metadata_filter: Optional metadata filter
            
        Returns:
            AI response
        """
        try:
            if not question.strip():
                raise VectorError("Question cannot be empty")
            
            # First search for relevant context

            # Generate context search prompt using search model
            preprocess_prompt = (
                "Given a user question, rephrase or expand it into a list of concise key terms, phrases,"
                "and related concepts that are likely to appear in regulatory or ordinance text."
                "• Include synonyms, common legal/regulatory wording, and technical terminology."
                "• Focus on the underlying intent of the question, not just the exact words used."
                "• Avoid filler words and unrelated concepts."
                "• Output as a comma-separated list, in order of relevance."
            )

            context_search_prompt = self.search_ai_model.generate_response(
                question, preprocess_prompt, max_tokens=self.config.ai_search_max_tokens)
            
            query_vector = self.embedder.embed_text(context_search_prompt)
            search_results = self.vector_db.search(query_vector, 40, metadata_filter)

            if not search_results:
                return "No relevant documents found to answer your question."
            
            # Build context from search results
            context = self._build_context(search_results)
            
            # Get response length settings
            max_tokens = self.config.response_lengths.get(response_length, 1000)
            
            # Generate AI response using answer model
            system_prompt = self._get_system_prompt()
            user_prompt = f"Question: {question}\n\nContext:\n{context}"
            
            response = self.answer_ai_model.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens
            )
            
            return response
            
        except AIServiceError:
            raise  # Re-raise AI service errors
        except Exception as e:
            raise VectorError(f"AI query failed: {e}")

    def process_files(self, files: List[str], force: bool = False, 
                     source: Optional[str] = None) -> str:
        """Process and index documents.
        
        Args:
            files: List of file or directory paths to process
            force: Force reprocessing of existing documents
            source: Source type for documents
            
        Returns:
            Processing status message
        """
        try:
            # Ensure collection exists
            if not self.vector_db.collection_exists():
                self.setup_collection()
            
            # Process each file or directory
            total_processed = 0
            processed_paths = 0
            
            for path in files:
                try:
                    chunks = self.processor.process_path(path, source, force, self.vector_db)
                    if chunks:
                        # Process in batches to avoid timeouts
                        batch_size = 100  # Process 100 chunks at a time
                        for i in range(0, len(chunks), batch_size):
                            batch_chunks = chunks[i:i + batch_size]
                            
                            # Embed batch
                            texts = [chunk['text'] for chunk in batch_chunks]
                            vectors = self.embedder.embed_texts(texts)
                            metadata = [chunk['metadata'] for chunk in batch_chunks]
                            
                            # Add to vector database
                            self.vector_db.add_documents(texts, vectors, metadata)
                            total_processed += len(batch_chunks)
                            
                            print(f"📦 Processed batch: {len(batch_chunks)} chunks (Total: {total_processed})")
                        
                        processed_paths += 1
                except Exception as e:
                    print(f"⚠️  Error processing {path}: {e}")
                    continue
            
            return f"✅ Processed {total_processed} chunks from {processed_paths} path(s)"
            
        except Exception as e:
            raise VectorError(f"File processing failed: {e}")

    def get_info(self) -> str:
        """Get collection information."""
        try:
            info = self.vector_db.get_collection_info()
            return self.formatter.format_info(info)
        except Exception as e:
            raise VectorError(f"Failed to get collection info: {e}")

    def get_metadata_summary(self) -> str:
        """Get metadata summary."""
        try:
            summary = self.vector_db.get_metadata_summary()
            return self.formatter.format_metadata_summary(summary)
        except Exception as e:
            raise VectorError(f"Failed to get metadata summary: {e}")

    def delete_documents(self, metadata_filter: Dict[str, Any]) -> str:
        """Delete documents from the collection based on metadata filter.
        
        Args:
            metadata_filter: Metadata filter to identify documents to delete
            
        Returns:
            Deletion status message
        """
        try:
            if not metadata_filter:
                raise VectorError("Metadata filter cannot be empty for safety")
            
            # Delete documents
            result = self.vector_db.delete_documents(metadata_filter)
            
            # Format filter for display
            filter_display = ", ".join([f"{k}={v}" for k, v in metadata_filter.items()])
            
            return f"✅ Deleted documents matching filter: {filter_display}"
            
        except Exception as e:
            raise VectorError(f"Failed to delete documents: {e}")

    def clear_collection(self) -> str:
        """Clear the collection."""
        try:
            self.vector_db.clear_collection()
            return f"✅ Collection '{self.collection_name}' cleared successfully"
        except Exception as e:
            raise VectorError(f"Failed to clear collection: {e}")

    def get_model_info(self) -> str:
        """Get information about configured models."""
        try:
            search_info = self.search_ai_model.get_model_info()
            answer_info = self.answer_ai_model.get_model_info()
            
            if self.search_ai_model == self.answer_ai_model:
                return f"🤖 Single Model: {search_info['model_name']} ({search_info.get('provider', 'unknown')})"
            
            return (
                f"🔍 Search Model: {search_info['model_name']} ({search_info.get('provider', 'unknown')})\n"
                f"   Max Tokens: {search_info['configured_max_tokens']}\n"
                f"   Temperature: {search_info['configured_temperature']}\n\n"
                f"💬 Answer Model: {answer_info['model_name']} ({answer_info.get('provider', 'unknown')})\n"
                f"   Max Tokens: {answer_info['configured_max_tokens']}\n"
                f"   Temperature: {answer_info['configured_temperature']}\n\n"
                f"📋 Available Providers: {', '.join(AIModelFactory.get_available_providers())}"
            )
        except Exception as e:
            return f"⚠️  Error getting model info: {e}"

    def _build_context(self, search_results: List[SearchResult]) -> str:
        """Build context string from search results."""
        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(
                f"Document {i} (Score: {result.score:.3f}):\n"
                f"Source: {result.filename}\n"
                f"Content: {result.text}\n"
            )
        return "\n".join(context_parts)

    def _get_system_prompt(self) -> str:
        """Get system prompt for AI interactions."""
        return (
            "You are a professional assistant specialized in analyzing municipal "
            "documents, ordinances, and regulations. Your job is to provide accurate, "
            "relevant information based on the given context.\n\n"
            "Instructions:\n"
            "• Answer based only on the provided context\n"
            "• Include specific details, requirements, and references\n"
            "• If the context doesn't contain enough information, say so\n"
            "• Be concise but thorough\n"
            "• Use professional terminology appropriate for municipal regulations"
        )
