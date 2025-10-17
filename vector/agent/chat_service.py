"""Chat service for managing conversation sessions and orchestrating agents."""

import asyncio
from typing import Dict, Any, Optional, List
from uuid import uuid4

from ..config import Config
from ..exceptions import AIServiceError
from ..ai.factory import AIModelFactory
from vector.search.service import SearchService
from vector.embedders.sentence_transformer import SentenceTransformerEmbedder
from vector.stores.factory import create_store

from .models import ChatSession, UsageMetrics, AggregatedUsageMetrics
from .prompting import build_system_prompt, build_answer_prompt
from .memory import SummarizerPolicy
from .retrieval import Retriever
from .deps import AgentDeps
from .agents import ResearchAgent


class ChatService:
    """
    Service for managing multi-turn conversations with document retrieval.
    
    This service orchestrates between classic pipeline-based retrieval
    and modern PydanticAI agent-based approaches.
    
    Features:
    - Session management (start/end/get)
    - Memory management with automatic summarization
    - Dual-mode operation: classic pipeline or PydanticAI agents
    - Async-to-sync bridging for compatibility
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        chunks_collection: str = "chunks",
        use_pydantic_ai: bool = True
    ):
        """Initialize the chat service.

        Args:
            config: Configuration object. If None, loads default config.
            chunks_collection: Name of the chunks collection
            use_pydantic_ai: Whether to use PydanticAI agents (default: True)
        """
        self.config = config or Config()
        self.chunks_collection = chunks_collection
        self.use_pydantic_ai = use_pydantic_ai
        
        # Initialize search service
        embedder = SentenceTransformerEmbedder()
        store = create_store("qdrant", db_path=self.config.vector_db_path)
        self.search_service = SearchService(embedder, store, chunks_collection)
        
        # Initialize AI models
        try:
            self.search_ai_model = AIModelFactory.create_model(self.config, 'search')
            self.answer_ai_model = AIModelFactory.create_model(self.config, 'answer')
        except Exception as e:
            print(f"Warning: Could not initialize AI models: {e}")
            self.search_ai_model = None
            self.answer_ai_model = None
        
        # Initialize retriever (for classic mode)
        self.retriever = Retriever(self.search_ai_model, self.search_service)
        
        # Initialize summarizer policy
        if self.answer_ai_model:
            self.summarizer = SummarizerPolicy(
                ai_model=self.answer_ai_model,
                trigger_messages=self.config.chat_summary_trigger_messages,
                keep_recent=6
            )
        else:
            self.summarizer = None
        
        # Initialize PydanticAI agent if enabled
        if self.use_pydantic_ai and self.search_ai_model and self.answer_ai_model:
            try:
                deps = AgentDeps(
                    search_service=self.search_service,
                    config=self.config,
                    search_model=self.search_ai_model,
                    answer_model=self.answer_ai_model,
                    chunks_collection=chunks_collection
                )
                self.agent = ResearchAgent(deps)
            except Exception as e:
                print(f"Warning: Could not initialize PydanticAI agent: {e}")
                self.agent = None
                self.use_pydantic_ai = False
        else:
            self.agent = None
        
        # Session management
        self._sessions: Dict[str, ChatSession] = {}

    # Session Management Methods

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

    # Main Chat Method

    def chat(
        self,
        session_id: str,
        user_message: str,
        response_length: str = 'medium',
        top_k: int = 12,
        document_ids: Optional[List[str]] = None,
        window: int = 0,
        use_tools: bool = False
    ) -> Dict[str, Any]:
        """Process a chat message in a multi-turn conversation.
        
        Args:
            session_id: Session identifier
            user_message: User's message
            response_length: Response length (short/medium/long)
            top_k: Number of results to retrieve
            document_ids: Optional list of document IDs to filter
            window: Number of surrounding chunks to include
            use_tools: Whether to use PydanticAI tool-based agent
            
        Returns:
            Dict with assistant response, results, and metadata
        """
        if not user_message.strip():
            raise ValueError("User message cannot be empty")
        
        if session_id not in self._sessions:
            raise ValueError(f"Unknown chat session: {session_id}")
        
        if not self.answer_ai_model:
            raise AIServiceError(
                "AI models are not available. Please configure API keys."
            )
        
        session = self._sessions[session_id]
        session.add('user', user_message)
        
        # Choose mode
        if use_tools and self.use_pydantic_ai and self.agent:
            try:
                return self._chat_with_agent(
                    session_id, user_message, response_length,
                    top_k, document_ids, window
                )
            except Exception as e:
                print(f"Warning: PydanticAI agent failed, falling back: {e}")
        
        # Classic mode fallback
        return self._chat_classic(
            session_id, user_message, response_length,
            top_k, document_ids, window
        )
    
    def _chat_with_agent(
        self,
        session_id: str,
        user_message: str,
        response_length: str,
        top_k: int,
        document_ids: Optional[List[str]],
        window: int
    ) -> Dict[str, Any]:
        """Chat using PydanticAI agent."""
        session = self._sessions[session_id]
        max_tokens = self.config.response_lengths.get(response_length, 1000)
        
        # Run async agent
        result = asyncio.run(
            self.agent.retrieve_and_answer(
                session=session,
                user_message=user_message,
                max_tokens=max_tokens,
                top_k=top_k,
                document_ids=document_ids,
                window=window
            )
        )
        
        # Update session
        session.add('assistant', result['assistant'])
        
        if self.summarizer:
            self.summarizer.compact(session)
        
        result.update({
            "session_id": session_id,
            "message_count": len(session.messages),
            "summary_present": session.summary is not None,
            "agent_type": "pydantic_ai"
        })
        
        return result
    
    def _chat_classic(
        self,
        session_id: str,
        user_message: str,
        response_length: str,
        top_k: int,
        document_ids: Optional[List[str]],
        window: int
    ) -> Dict[str, Any]:
        """Chat using classic retrieval pipeline."""
        session = self._sessions[session_id]
        
        # Retrieval
        retrieval, expansion_metrics = self.retriever.retrieve(
            session=session,
            user_message=user_message,
            top_k=top_k,
            document_ids=document_ids,
            window=window
        )
        
        # Handle no results
        if not retrieval.results:
            assistant_response = "I couldn't find relevant information to answer your question."
            session.add('assistant', assistant_response)
            
            return {
                "session_id": session_id,
                "assistant": assistant_response,
                "results": [],
                "retrieval": retrieval.model_dump(),
                "message_count": len(session.messages),
                "usage_metrics": expansion_metrics.model_dump(),
                "agent_type": "classic"
            }
        
        # Generate answer
        answer_prompt = build_answer_prompt(session, user_message, retrieval)
        max_tokens = self.config.response_lengths.get(response_length, 1000)
        
        try:
            assistant_response, answer_metrics_dict = self.answer_ai_model.generate_response(
                prompt=answer_prompt,
                system_prompt=session.system_prompt,
                max_tokens=max_tokens,
                operation="answer"
            )
            
            answer_metrics = UsageMetrics(**answer_metrics_dict)
            all_operations = list(expansion_metrics.operations) + [answer_metrics]
            aggregated = AggregatedUsageMetrics.from_operations(all_operations)
            
        except Exception as e:
            raise AIServiceError(f"Failed to generate AI response: {e}")
        
        # Update session
        session.add('assistant', assistant_response)
        
        if self.summarizer:
            self.summarizer.compact(session)
        
        return {
            "session_id": session_id,
            "assistant": assistant_response,
            "results": retrieval.results,
            "retrieval": retrieval.model_dump(),
            "message_count": len(session.messages),
            "summary_present": session.summary is not None,
            "usage_metrics": aggregated.model_dump(),
            "agent_type": "classic"
        }

    # Info Methods

    def get_model_info(self) -> str:
        """Get information about configured models."""
        if not self.search_ai_model or not self.answer_ai_model:
            return "⚠️  AI models not available"
        
        try:
            search_info = self.search_ai_model.get_model_info()
            answer_info = self.answer_ai_model.get_model_info()
            
            if self.search_ai_model == self.answer_ai_model:
                return f"🤖 Single Model: {search_info['model_name']}"
            
            return (
                f"🔍 Search Model: {search_info['model_name']}\n"
                f"💬 Answer Model: {answer_info['model_name']}"
            )
        except Exception as e:
            return f"⚠️  Error: {e}"

    def get_collection_info(self) -> str:
        """Get information about collections."""
        collections = self.search_service.store.list_collections()
        return f"Collections: {', '.join(collections)}\nChunks: {self.chunks_collection}"
