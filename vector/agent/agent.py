"""Simplified Research Agent for Vector."""

import warnings
import time
from typing import List, Dict, Any, Optional, Union, Literal
from uuid import uuid4
from pydantic import BaseModel, Field

from vector.core.models import Chunk, Artifact

from ..config import Config
from ..exceptions import VectorError, AIServiceError
from ..ai.factory import AIModelFactory
from ..core.embedder import Embedder
from ..core.vector_store import VectorStore

warnings.filterwarnings("ignore", category=FutureWarning, module="torch.nn.modules.module")


class SearchResult(BaseModel):
    """Search result container with validation."""
    id: str = Field(..., description="Unique identifier")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    text: str = Field(..., description="Result content")
    filename: str = Field(..., description="Source filename")
    type: str = Field(..., description="Result type (chunk/artifact)")
    chunk: Optional[Chunk] = None
    artifact: Optional[Artifact] = None


class ChatMessage(BaseModel):
    """Chat message with role and content."""
    role: Literal['system', 'user', 'assistant'] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")


class ChatSession(BaseModel):
    """Chat session with message history."""
    id: str = Field(..., description="Session identifier")
    messages: List[ChatMessage] = Field(default_factory=list, description="Message history")
    summary: Optional[str] = Field(None, description="Compressed history summary")
    created_at: float = Field(..., description="Session creation timestamp")
    last_updated: float = Field(..., description="Last update timestamp")
    system_prompt: Optional[str] = Field(None, description="System prompt for this session")

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
        
        # Chat session management
        self._sessions: Dict[str, ChatSession] = {}
        self.max_history_messages = self.config.chat_max_history_messages
        self.summary_trigger_messages = self.config.chat_summary_trigger_messages

    def search_chunks(self, query: str, top_k: int = 5, document_ids: Optional[List[str]] = None) -> List[SearchResult]:
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
        results = self.store.search_documents(query_vector, self.chunks_collection, top_k, document_ids)
        
        # Convert to SearchResult objects
        search_results = []
        for result in results:

            try:
                # Convert string to dictionary first, then validate
                import json
                chunk_data = result.payload.get('chunk', {})
                
                # If chunk_data is a string, parse it as JSON
                if isinstance(chunk_data, str):
                    chunk_data = json.loads(chunk_data)
                
                # Now validate with Pydantic
                chunk = Chunk.model_validate(chunk_data)
                
            except Exception as e:
                print(f"Warning: Could not validate chunk: {e}")

            search_results.append(SearchResult(
                id=str(result.id),
                score=result.score,
                text=chunk.text,
                filename=result.payload.get("document_id", "Unknown"),
                type="chunk",
                chunk=chunk
            ))
        
        return search_results

    def search_artifacts(self, query: str, top_k: int = 5, document_ids: Optional[List[str]] = None) -> List[SearchResult]:
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
        results = self.store.search_documents(query_vector, self.artifacts_collection, top_k, document_ids)

        # Convert to SearchResult objects
        search_results = []
        for result in results:

            try:
                # Convert string to dictionary first, then validate
                import json
                artifact_data = result.payload.get('artifact', {})
                
                # If artifact_data is a string, parse it as JSON
                if isinstance(artifact_data, str):
                    artifact_data = json.loads(artifact_data)
                
                # Now validate with Pydantic
                artifact = Artifact.model_validate(artifact_data)
               
            except Exception as e:
                print(f"Warning: Could not validate artifact: {e}")

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
                artifact=artifact
            ))
        
        return search_results

    def search(self, query: str, top_k: int = 5, search_type: str = 'both', document_ids: Optional[List[str]] = None) -> List[SearchResult]:
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
            chunk_results = self.search_chunks(query, top_k, document_ids)
            results.extend(chunk_results)
        
        if search_type in ['artifacts', 'both']:
            artifact_results = self.search_artifacts(query, top_k, document_ids)
            results.extend(artifact_results)
        
        # Sort combined results by score if searching both
        if search_type == 'both':
            results.sort(key=lambda x: x.score, reverse=True)
            results = results[:top_k * 2]  # Return up to top_k*2 results when searching both
        
        return results
    
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

    # Chat Methods

    def start_chat(self, system_prompt: Optional[str] = None) -> str:
        """Start a new chat session.
        
        Args:
            system_prompt: Optional custom system prompt. Uses default if None.
            
        Returns:
            Session ID for the new chat
        """
        session_id = str(uuid4())
        base_prompt = system_prompt or self._get_system_prompt()
        session = ChatSession(
            id=session_id,
            messages=[ChatMessage(role='system', content=base_prompt)],
            created_at=time.time(),
            last_updated=time.time()
        )
        # Store the system prompt explicitly for easier access
        session.system_prompt = base_prompt
        self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ChatSession if found, None otherwise
        """
        return self._sessions.get(session_id)

    def end_chat(self, session_id: str) -> bool:
        """End a chat session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was found and removed, False otherwise
        """
        return self._sessions.pop(session_id, None) is not None

    def chat(
        self,
        session_id: str,
        user_message: str,
        response_length: str = 'medium',
        search_type: str = 'both',
        top_k: int = 12,
        document_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Process a chat message in a multi-turn conversation.
        
        Args:
            session_id: Session identifier
            user_message: User's message
            response_length: Response length (short/medium/long)
            search_type: 'chunks', 'artifacts', or 'both'
            top_k: Number of results to retrieve
            document_ids: Optional list of document IDs to filter
            
        Returns:
            Dict with assistant response, results, and metadata
        """
        if not user_message.strip():
            raise ValueError("User message cannot be empty")
        
        if session_id not in self._sessions:
            raise ValueError(f"Unknown chat session: {session_id}")
        
        # Check if AI models are available
        if not self.search_ai_model or not self.answer_ai_model:
            raise AIServiceError(
                "AI models are not available. Please configure API keys and ensure models are properly initialized."
            )
        
        session = self._sessions[session_id]
        session.messages.append(ChatMessage(role='user', content=user_message))
        
        # Build retrieval query from conversation context
        retrieval_query = self._build_retrieval_query(session, user_message)
        
        # Search for relevant context
        results = self.search(
            query=retrieval_query,
            top_k=top_k,
            search_type=search_type,
            document_ids=document_ids
        )
        
        if not results:
            assistant_response = "I couldn't find relevant information in the documents to answer your question."
            session.messages.append(ChatMessage(role='assistant', content=assistant_response))
            session.last_updated = time.time()
            return {
                "session_id": session_id,
                "assistant": assistant_response,
                "results": [],
                "message_count": len(session.messages)
            }
        
        # Build context from search results
        context_str = self._build_context(results[:40])
        max_tokens = self.config.response_lengths.get(response_length, 1000)
        
        # Construct conversational prompt
        conversation_snippet = self._render_recent_messages(session)
        user_prompt = (
            f"Conversation so far:\n{conversation_snippet}\n\n"
            f"New user message: {user_message}\n\n"
            f"Retrieved Context:\n{context_str}\n\n"
            "Compose the assistant reply grounded ONLY in the retrieved context and prior turns. "
            "If insufficient context, state that clearly."
        )
        
        # Generate AI response
        try:
            assistant_response = self.answer_ai_model.generate_response(
                prompt=user_prompt,
                system_prompt=session.system_prompt or session.messages[0].content,
                max_tokens=max_tokens
            )
        except Exception as e:
            raise AIServiceError(f"Failed to generate AI response: {e}")
        
        # Add assistant response to session
        session.messages.append(ChatMessage(role='assistant', content=assistant_response))
        session.last_updated = time.time()
        
        # Summarize if conversation is getting long
        self._maybe_summarize_session(session)
        
        return {
            "session_id": session_id,
            "assistant": assistant_response,
            "results": results,
            "message_count": len(session.messages)
        }

    def _render_recent_messages(self, session: ChatSession, limit: int = 10) -> str:
        """Render recent messages for context.
        
        Args:
            session: Chat session
            limit: Maximum number of messages to include
            
        Returns:
            Formatted conversation snippet
        """
        relevant = [m for m in session.messages if m.role != 'system'][-limit:]
        return "\n".join(f"{m.role.upper()}: {m.content}" for m in relevant)

    def _build_retrieval_query(self, session: ChatSession, user_message: str) -> str:
        """Build retrieval query from conversation context.
        
        Args:
            session: Chat session
            user_message: Current user message
            
        Returns:
            Enhanced search query
        """
        if not self.search_ai_model:
            return user_message
        
        recent = self._render_recent_messages(session, limit=6)
        expand_prompt = (
            "Given the ongoing municipal regulations conversation and NEW user message, "
            "produce a comma-separated list of focused retrieval keyphrases. "
            "Avoid generic fluff. Prior conversation:\n"
            f"{recent}\n\nUser message:\n{user_message}"
        )
        
        try:
            return self.search_ai_model.generate_response(
                user_message,
                expand_prompt,
                max_tokens=self.config.ai_search_max_tokens
            )
        except Exception:
            return user_message

    def _maybe_summarize_session(self, session: ChatSession) -> None:
        """Summarize session history if it's getting too long.
        
        Args:
            session: Chat session to potentially summarize
        """
        if len(session.messages) < self.summary_trigger_messages:
            return
        
        if not self.answer_ai_model:
            return
        
        # Summarize all but last few message pairs
        core_messages = session.messages[1:-4]  # exclude system and last 4
        if not core_messages:
            return
        
        text = "\n".join(f"{m.role}: {m.content}" for m in core_messages)
        
        try:
            summary = self.answer_ai_model.generate_response(
                prompt=f"Summarize these municipal regulation Q&A turns into a compact factual session memory:\n{text}",
                system_prompt="You compress conversation history; preserve obligations, constraints, and definitions.",
                max_tokens=300
            )
            session.summary = summary
            # Replace old messages with summary placeholder
            session.messages = [
                session.messages[0],
                ChatMessage(role='system', content=f"[HISTORY SUMMARY]: {summary}")
            ] + session.messages[-4:]
        except Exception:
            # If summarization fails, just continue without it
            pass
    
