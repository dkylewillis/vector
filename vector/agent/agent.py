"""Simplified Research Agent for Vector."""

import warnings
from typing import List, Dict, Any, Optional

from ..config import Config
from ..exceptions import VectorError, AIServiceError, DatabaseError
from ..interfaces import SearchResult
from ..core.embedder import Embedder
from ..core.database import VectorDatabase
from ..core.collection_manager import CollectionManager
from ..ai.factory import AIModelFactory
from ..utils.formatting import CLIFormatter

warnings.filterwarnings("ignore", category=FutureWarning, module="torch.nn.modules.module")


class ResearchAgent:
    """
    Simplified research agent that handles search and AI interactions only.
    Document processing is handled separately.
    """

    def __init__(self, config: Config, collection_name: str, collection_manager: Optional[CollectionManager] = None):
        """Initialize the research agent.

        Args:
            config: Configuration object
            collection_name: Name of the collection (display name)
            collection_manager: Optional collection manager for name resolution
        """
        self.config = config
        self.collection_name = collection_name
        self.collection_manager = collection_manager
        
        # Initialize components
        self.embedder = Embedder(config)
        
        # Resolve collections via CollectionManager when available
        if collection_manager:
            pair = collection_manager.get_pair_by_display_name(collection_name)
            if not pair:
                raise VectorError(f"Collection pair with display name '{collection_name}' not found")
            chunks_collection = pair["chunks_collection"]
            artifacts_collection = pair["artifacts_collection"]
        else:
            # Fallback to legacy naming when no collection manager
            chunks_collection = f"{collection_name}_chunks" if not collection_name.endswith('_chunks') else collection_name
            artifacts_collection = f"{collection_name.replace('_chunks', '')}_artifacts"
        
        self.chunks_db = VectorDatabase(chunks_collection, config, collection_manager)
        self.artifacts_db = VectorDatabase(artifacts_collection, config, collection_manager)
        
        # Initialize AI models using factory
        self.search_ai_model = AIModelFactory.create_model(config, 'search')
        self.answer_ai_model = AIModelFactory.create_model(config, 'answer')
        
        self.formatter = CLIFormatter()

    def search_chunks(self, query: str, top_k: int = 5, metadata_filter: Optional[Dict] = None) -> str:
        """Search for relevant document chunks.
        
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
            
            # Search the chunks database
            results = self.chunks_db.search(query_vector, top_k, metadata_filter)
            
            # Format and return results
            return self.formatter.format_search_results(results)
            
        except Exception as e:
            raise VectorError(f"Chunk search failed: {e}")

    def search_artifacts(self, query: str, top_k: int = 5, metadata_filter: Optional[Dict] = None) -> str:
        """Search for relevant artifacts.
        
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
            
            # Search the artifacts database
            results = self.artifacts_db.search(query_vector, top_k, metadata_filter)
            
            # Format and return results
            return self.formatter.format_search_results(results)
            
        except Exception as e:
            raise VectorError(f"Artifact search failed: {e}")

    def search(self, query: str, top_k: int = 5, metadata_filter: Optional[Dict] = None, 
               search_type: str = 'both') -> str:
        """Search for relevant documents across chunks and/or artifacts.
        
        Args:
            query: Search query
            top_k: Number of results to return per type
            metadata_filter: Optional metadata filter
            search_type: 'chunks', 'artifacts', or 'both'
            
        Returns:
            Formatted search results
        """
        try:
            if not query.strip():
                raise VectorError("Search query cannot be empty")
            
            results = []
            
            if search_type in ['chunks', 'both']:
                chunk_results = self._search_collection(query, self.chunks_db, top_k, metadata_filter)
                results.extend(chunk_results)
            
            if search_type in ['artifacts', 'both']:
                artifact_results = self._search_collection(query, self.artifacts_db, top_k, metadata_filter)
                results.extend(artifact_results)
            
            # Sort combined results by score if searching both
            if search_type == 'both':
                results.sort(key=lambda x: x.score, reverse=True)
                results = results[:top_k * 2]  # Return up to top_k*2 results when searching both
            
            # Format and return results
            return self.formatter.format_search_results(results)
            
        except Exception as e:
            raise VectorError(f"Search failed: {e}")

    def _search_collection(self, query: str, database: VectorDatabase, top_k: int, 
                          metadata_filter: Optional[Dict] = None) -> List[SearchResult]:
        """Helper method to search a specific collection."""
        query_vector = self.embedder.embed_text(query)
        return database.search(query_vector, top_k, metadata_filter)

    def ask(self, question: str, response_length: str = 'medium', 
            metadata_filter: Optional[Dict] = None, search_type: str = 'chunks') -> str:
        """Ask AI a question about the documents.
        
        Args:
            question: Question to ask
            response_length: Response length (short/medium/long)
            metadata_filter: Optional metadata filter
            search_type: 'chunks', 'artifacts', or 'both' for context search
            
        Returns:
            AI response
        """
        try:
            if not question.strip():
                raise VectorError("Question cannot be empty")
            
            # Generate context search prompt using search model
            preprocess_prompt = (
                "Given a user question, rephrase or expand it into a list of concise key terms, phrases, "
                "and related concepts that are likely to appear in regulatory or ordinance text. "
                "• Include synonyms, common legal/regulatory wording, and technical terminology. "
                "• Focus on the underlying intent of the question, not just the exact words used. "
                "• Avoid filler words and unrelated concepts. "
                "• Output as a comma-separated list, in order of relevance."
            )

            context_search_prompt = self.search_ai_model.generate_response(
                question, preprocess_prompt, max_tokens=self.config.ai_search_max_tokens)
            
            # Search for context based on search_type
            chunk_results = []
            artifact_results = []   
            
            if search_type in ['chunks', 'both']:
                chunk_results = self._search_collection(context_search_prompt, self.chunks_db, 20, metadata_filter)
            
            if search_type in ['artifacts', 'both']:
                artifact_results = self._search_collection(context_search_prompt, self.artifacts_db, 20, metadata_filter)
                
            
            # Sort by score and limit results
            
            chunk_results = chunk_results[:40]

            if not chunk_results:
                return "No relevant documents found to answer your question."
            
            # Build context from search results
            context = self._build_context(chunk_results)

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

            print("Artifact Results:\n")

            print(artifact_results)
            print("\n\n")

            return response

        except AIServiceError:
            raise  # Re-raise AI service errors
        except Exception as e:
            raise VectorError(f"AI query failed: {e}")

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
            # Determine result type from metadata or collection info
            result_type = getattr(result, 'result_type', 'content')
            context_parts.append(
                f"Document {i} (Score: {result.score:.3f}, Type: {result_type}):\n"
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
            "• Use professional terminology appropriate for municipal regulations\n"
            "• When referencing context, note whether it comes from document chunks or extracted artifacts"
        )

    def get_collection_info(self) -> str:
        """Get information about the collections being searched."""
        try:
            chunks_info = f"Chunks Collection: {self.chunks_db.collection_name}"
            artifacts_info = f"Artifacts Collection: {self.artifacts_db.collection_name}"
            return f"{chunks_info}\n{artifacts_info}"
        except Exception as e:
            return f"⚠️  Error getting collection info: {e}"