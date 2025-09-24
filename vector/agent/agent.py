"""Simplified Research Agent for Vector."""

import warnings
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

from ..config import Config
from ..exceptions import VectorError, AIServiceError
from ..ai.factory import AIModelFactory
from ..core.embedder import Embedder
from ..core.vector_store import VectorStore

warnings.filterwarnings("ignore", category=FutureWarning, module="torch.nn.modules.module")


@dataclass
class SearchResult:
    """Simple search result container."""
    id: str
    score: float
    text: str
    filename: str
    type: str
    metadata: Dict[str, Any]


class ResearchAgent:
    """
    Simplified research agent that handles search operations only.
    Document processing is handled separately.
    """

    def __init__(self, config: Optional[Config] = None, chunks_collection: str = "chunks", artifacts_collection: str = "artifacts"):
        """Initialize the research agent.

        Args:
            config: Configuration object. If None, loads default config.
            chunks_collection: Name of the chunks collection
            artifacts_collection: Name of the artifacts collection
        """
        self.config = config or Config()
        self.chunks_collection = chunks_collection
        self.artifacts_collection = artifacts_collection
        
        # Initialize components
        self.embedder = Embedder()
        self.store = VectorStore()
        
        # Initialize AI models using factory
        try:
            self.search_ai_model = AIModelFactory.create_model(self.config, 'search')
            self.answer_ai_model = AIModelFactory.create_model(self.config, 'answer')
        except Exception as e:
            print(f"Warning: Could not initialize AI models: {e}")
            self.search_ai_model = None
            self.answer_ai_model = None

    def search_chunks(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Search for relevant document chunks.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of search results
        """
        if not query.strip():
            raise ValueError("Search query cannot be empty")
        
        # Embed the query
        query_vector = self.embedder.embed_text(query)
        
        # Search the chunks database
        results = self.store.search(query_vector, self.chunks_collection, top_k)
        
        # Convert to SearchResult objects
        search_results = []
        for result in results:
            search_results.append(SearchResult(
                id=str(result.id),
                score=result.score,
                text=result.payload.get("text", ""),
                filename=result.payload.get("document_id", "Unknown"),
                type="chunk",
                metadata=result.payload
            ))

        for result in search_results:
            pictures = result.metadata.get('pictures')
            if pictures:
                print(f"Picture URL: {pictures[0]}")
        
        return search_results

    def search_artifacts(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Search for relevant artifacts.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of search results
        """
        if not query.strip():
            raise ValueError("Search query cannot be empty")
        
        # Embed the query
        query_vector = self.embedder.embed_text(query)
        
        # Search the artifacts database
        results = self.store.search(query_vector, self.artifacts_collection, top_k)
        
        # Convert to SearchResult objects
        search_results = []
        for result in results:
            # Build text from artifact fields
            text_parts = []
            if result.payload.get("caption"):
                text_parts.append(f"Caption: {result.payload['caption']}")
            if result.payload.get("before_text"):
                text_parts.append(f"Context: {result.payload['before_text']}")
            if result.payload.get("after_text"):
                text_parts.append(f"Context: {result.payload['after_text']}")
            if result.payload.get("headings"):
                text_parts.append(f"Headings: {', '.join(result.payload['headings'])}")
            
            search_results.append(SearchResult(
                id=str(result.id),
                score=result.score,
                text=" | ".join(text_parts) if text_parts else "Artifact",
                filename=result.payload.get("document_id", "Unknown"),
                type=result.payload.get("type", "artifact"),
                metadata=result.payload
            ))
        
        return search_results

    def search(self, query: str, top_k: int = 5, search_type: str = 'both') -> List[SearchResult]:
        """Search for relevant documents across chunks and/or artifacts.
        
        Args:
            query: Search query
            top_k: Number of results to return per type
            search_type: 'chunks', 'artifacts', or 'both'
            
        Returns:
            List of search results
        """
        if not query.strip():
            raise ValueError("Search query cannot be empty")
        
        results = []
        
        if search_type in ['chunks', 'both']:
            chunk_results = self.search_chunks(query, top_k)
            results.extend(chunk_results)
        
        if search_type in ['artifacts', 'both']:
            artifact_results = self.search_artifacts(query, top_k)
            results.extend(artifact_results)
        
        # Sort combined results by score if searching both
        if search_type == 'both':
            results.sort(key=lambda x: x.score, reverse=True)
            results = results[:top_k * 2]  # Return up to top_k*2 results when searching both
        
        return results

    def ask(self, question: str, response_length: str = 'medium', search_type: str = 'both', top_k: int = 20) -> tuple[str, List[SearchResult]]:
        """Ask a question about the documents and get relevant context.
        
        Args:
            question: Question to ask
            response_length: Response length (short/medium/long)
            search_type: 'chunks', 'artifacts', or 'both' for context search
            top_k: Number of results to return for context
            
        Returns:
            Tuple of (AI response, search results used for context)
        """
        if not question.strip():
            raise ValueError("Question cannot be empty")
        
        # Check if AI models are available
        if not self.search_ai_model or not self.answer_ai_model:
            raise AIServiceError("AI models are not available. Please configure API keys and ensure models are properly initialized.")
        
        # Use AI to enhance search
        try:
            # Generate context search prompt using search model
            preprocess_prompt = (
                "Given a user question, rephrase or expand it into a list of concise key terms, phrases, "
                "and related concepts that are likely to appear in regulatory or ordinance text. "
                "• Include synonyms, common legal/regulatory wording, and technical terminology. "
                "• Focus on the underlying intent of the question, not just the exact words used. "
                "• Avoid filler words and unrelated concepts. "
                "• Output as a comma-separated list, in order of relevance."
            )
            
            search_query = self.search_ai_model.generate_response(
                question, preprocess_prompt, max_tokens=self.config.ai_search_max_tokens)
        except Exception as e:
            # Fall back to original question if search enhancement fails
            print(f"Warning: Could not enhance search with AI: {e}")
            search_query = question
        
        # Search for context based on search_type
        results = self.search(query=search_query, top_k=top_k, search_type=search_type)
        
        if not results:
            return ("No relevant documents found to answer your question.", [])
        
        # Generate AI response
        try:
            # Build context from search results
            context = self._build_context(results[:40])  # Limit to top 40 results
            
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
        except Exception as e:
            raise AIServiceError(f"Failed to generate AI response: {e}")
        
        # Debug output
        chunk_count = len([r for r in results if r.type == 'chunk'])
        artifact_count = len([r for r in results if r.type in ['table', 'picture', 'artifact']])
        print(f"Chunk Results Count: {chunk_count}")
        print(f"Artifact Results Count: {artifact_count}")
        print(f"Total Results Used: {len(results)}")
        print()
        
        return (response, results)
    
    def _build_context(self, search_results: List[SearchResult]) -> str:
        """Build context string from search results for AI."""
        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(
                f"Document {i} (Score: {result.score:.3f}, Type: {result.type}):\n"
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

    def get_model_info(self) -> str:
        """Get information about configured models."""
        if not self.search_ai_model or not self.answer_ai_model:
            return "⚠️  AI models not available"
        
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

    def format_results(self, results: List[SearchResult]) -> str:
        """Format search results for display.
        
        Args:
            results: List of search results
            
        Returns:
            Formatted string
        """
        if not results:
            return "No results found."
        
        formatted_parts = []
        for i, result in enumerate(results, 1):
            formatted_parts.append(
                f"Result {i} (Score: {result.score:.3f}, Type: {result.type}):\n"
                f"Source: {result.filename}\n"
                f"Content: {result.text}\n"
            )
        
        return "\n".join(formatted_parts)

    def get_collection_info(self) -> str:
        """Get information about the collections being searched."""
        collections = self.store.list_collections()
        info_parts = [
            f"Available collections: {', '.join(collections)}",
            f"Chunks collection: {self.chunks_collection}",
            f"Artifacts collection: {self.artifacts_collection}"
        ]
        return "\n".join(info_parts)