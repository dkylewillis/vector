"""Simplified Research Agent for Vector."""

import warnings
from typing import List, Dict, Any, Optional
from uuid import uuid4

from ..config import Config
from ..exceptions import AIServiceError
from ..ai.factory import AIModelFactory
from ..core.services.search import SearchService

# Import new modular components
from .models import ChatSession, RetrievalResult, UsageMetrics, AggregatedUsageMetrics
from .prompting import build_system_prompt, build_answer_prompt
from .memory import SummarizerPolicy
from .retrieval import Retriever

warnings.filterwarnings("ignore", category=FutureWarning, module="torch.nn.modules.module")


class ResearchAgent:
    """
    Refactored research agent with modular architecture.
    Handles search operations and conversational AI interactions.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        chunks_collection: str = "chunks",
        artifacts_collection: str = "artifacts"
    ):
        """Initialize the research agent.

        Args:
            config: Configuration object. If None, loads default config.
            chunks_collection: Name of the chunks collection
            artifacts_collection: Name of the artifacts collection
        """
        self.config = config or Config()
        self.chunks_collection = chunks_collection
        self.artifacts_collection = artifacts_collection
        
        # Initialize search service
        from ..core.embedder import Embedder
        from ..core.vector_store import VectorStore
        search_service = SearchService(
            Embedder(),
            VectorStore(),
            chunks_collection,
            artifacts_collection
        )
        
        # Initialize AI models using factory
        try:
            self.search_ai_model = AIModelFactory.create_model(self.config, 'search')
            self.answer_ai_model = AIModelFactory.create_model(self.config, 'answer')
        except Exception as e:
            print(f"Warning: Could not initialize AI models: {e}")
            self.search_ai_model = None
            self.answer_ai_model = None
        
        # Initialize retriever with search service
        self.retriever = Retriever(self.search_ai_model, search_service)
        
        # Initialize summarizer policy
        if self.answer_ai_model:
            self.summarizer = SummarizerPolicy(
                ai_model=self.answer_ai_model,
                trigger_messages=self.config.chat_summary_trigger_messages,
                keep_recent=6
            )
        else:
            self.summarizer = None
        
        # Session management
        self._sessions: Dict[str, ChatSession] = {}
        self.max_answer_tokens = 800

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

    def get_collection_info(self) -> str:
        """Get information about the collections being searched."""
        collections = self.retriever.search_service.store.list_collections()
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
        prompt = system_prompt or build_system_prompt()
        
        session = ChatSession(
            id=session_id,
            system_prompt=prompt,
            messages=[]
        )
        
        # Add system message
        session.add('system', prompt)
        
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
        if not self.answer_ai_model:
            raise AIServiceError(
                "AI models are not available. Please configure API keys and ensure models are properly initialized."
            )
        
        session = self._sessions[session_id]
        
        # Add user message to session
        session.add('user', user_message)
        
        # Perform retrieval with query expansion
        retrieval, expansion_metrics = self.retriever.retrieve(
            session=session,
            user_message=user_message,
            top_k=top_k,
            search_type=search_type,
            document_ids=document_ids
        )
        
        # Handle no results case
        if not retrieval.results:
            assistant_response = "I couldn't find relevant information in the documents to answer your question."
            session.add('assistant', assistant_response)
            
            # Create aggregated metrics from just the expansion
            aggregated = AggregatedUsageMetrics.from_operations([expansion_metrics])
            
            return {
                "session_id": session_id,
                "assistant": assistant_response,
                "results": [],
                "retrieval": retrieval.model_dump(),
                "message_count": len(session.messages),
                "usage_metrics": aggregated.model_dump()
            }
        
        # Build answer prompt with retrieved context
        answer_prompt = build_answer_prompt(session, user_message, retrieval)
        
        # Get max tokens for response length
        max_tokens = self.config.response_lengths.get(response_length, 1000)
        
        # Generate AI response
        try:
            assistant_response, answer_metrics_dict = self.answer_ai_model.generate_response(
                prompt=answer_prompt,
                system_prompt=session.system_prompt,
                max_tokens=max_tokens,
                operation="answer"  # Mark this as answer operation
            )
            
            # Convert to UsageMetrics
            answer_metrics = UsageMetrics(**answer_metrics_dict)
            
            # Create aggregated metrics from both operations
            aggregated = AggregatedUsageMetrics.from_operations([expansion_metrics, answer_metrics])
            
        except Exception as e:
            raise AIServiceError(f"Failed to generate AI response: {e}")
        
        # Add assistant response to session
        session.add('assistant', assistant_response)
        
        # Apply summarization if needed
        if self.summarizer:
            self.summarizer.compact(session)
        
        return {
            "session_id": session_id,
            "assistant": assistant_response,
            "results": retrieval.results,
            "retrieval": retrieval.model_dump(),
            "message_count": len(session.messages),
            "summary_present": session.summary is not None,
            "usage_metrics": aggregated.model_dump()
        }

    
