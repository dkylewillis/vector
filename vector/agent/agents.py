"""PydanticAI-based agent implementations."""

from typing import Optional, List, Dict, Any
from pydantic_ai import Agent
from pydantic import BaseModel, Field

from .deps import AgentDeps
from .tools import (
    retrieve_chunks,
    expand_query,
    search_documents,
    get_chunk_window,
    get_document_metadata,
    list_available_documents
)
from .models import ChatSession, ChatMessage
from .prompting import build_system_prompt


class QueryExpansionResult(BaseModel):
    """Result from query expansion."""
    expanded_query: str = Field(..., description="Expanded search query")
    keyphrases: List[str] = Field(default_factory=list, description="Extracted keyphrases")
    original_query: str = Field(..., description="Original user query")


class SearchResult(BaseModel):
    """Result from search operation."""
    query: str = Field(..., description="Query used for search")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Search results")
    result_count: int = Field(0, description="Number of results returned")


class AnswerResult(BaseModel):
    """Result from answer generation."""
    answer: str = Field(..., description="Generated answer")
    sources: List[str] = Field(default_factory=list, description="Source citations")
    confidence: Optional[str] = Field(None, description="Confidence level")


class SearchAgent:
    """Specialized agent for search query optimization and expansion.
    
    This agent focuses on understanding user queries and expanding them
    into effective search terms for document retrieval.
    """
    
    def __init__(self, deps: AgentDeps):
        """Initialize search agent.
        
        Args:
            deps: Agent dependencies container
        """
        self.deps = deps
        
        # Create PydanticAI agent for query expansion
        self.agent = Agent(
            model=f"openai:{deps.config.ai_search_model_name}",
            deps_type=AgentDeps,
            system_prompt=(
                "You are a query expansion specialist for municipal document search. "
                "Your job is to transform user queries into effective search keyphrases "
                "that will retrieve relevant regulatory documents, ordinances, and codes."
            )
        )
    
    async def expand_query_with_context(
        self,
        session: ChatSession,
        user_message: str
    ) -> QueryExpansionResult:
        """Expand user query using conversation context.
        
        Args:
            session: Current chat session
            user_message: User's query to expand
            
        Returns:
            QueryExpansionResult with expanded query and keyphrases
        """
        # Use the expand_query tool
        result = await expand_query(
            self.agent._get_context(self.deps),
            session=session,
            user_message=user_message
        )
        
        return QueryExpansionResult(
            expanded_query=result.get("expanded_query", user_message),
            keyphrases=result.get("keyphrases", []),
            original_query=user_message
        )


class AnswerAgent:
    """Specialized agent for generating answers from retrieved context.
    
    This agent takes search results and generates comprehensive, well-cited
    answers to user questions.
    """
    
    def __init__(self, deps: AgentDeps):
        """Initialize answer agent.
        
        Args:
            deps: Agent dependencies container
        """
        self.deps = deps
        
        # Create PydanticAI agent for answer generation
        self.agent = Agent(
            model=f"openai:{deps.config.ai_answer_model_name}",
            deps_type=AgentDeps,
            system_prompt=build_system_prompt(),
            tools=[retrieve_chunks, search_documents, get_chunk_window]
        )
    
    async def generate_answer(
        self,
        session: ChatSession,
        user_message: str,
        max_tokens: int = 800
    ) -> AnswerResult:
        """Generate an answer to the user's question.
        
        This method can use tools to retrieve information as needed.
        
        Args:
            session: Current chat session
            user_message: User's question
            max_tokens: Maximum tokens for the response
            
        Returns:
            AnswerResult with generated answer and sources
        """
        # Build message history for context
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages
            if msg.role != "system"
        ]
        
        # Run agent with tool access
        result = await self.agent.run(
            user_message,
            message_history=messages,
            deps=self.deps,
            model_settings={"max_tokens": max_tokens}
        )
        
        return result.data


class ResearchAgent:
    """Coordinating agent that orchestrates search and answer generation.
    
    This is the main agent that users interact with. It coordinates between
    the SearchAgent and AnswerAgent to provide comprehensive responses.
    """
    
    def __init__(self, deps: AgentDeps):
        """Initialize research agent.
        
        Args:
            deps: Agent dependencies container
        """
        self.deps = deps
        self.search_agent = SearchAgent(deps)
        self.answer_agent = AnswerAgent(deps)
        
        # Create coordinating agent
        self.agent = Agent(
            model=f"openai:{deps.config.ai_answer_model_name}",
            deps_type=AgentDeps,
            system_prompt=(
                "You are a research coordinator for municipal document analysis. "
                "You orchestrate search and answer generation to help users find "
                "information in regulatory documents. Use your tools wisely to "
                "provide accurate, well-cited responses."
            ),
            tools=[
                retrieve_chunks,
                search_documents,
                expand_query,
                get_chunk_window,
                get_document_metadata,
                list_available_documents
            ]
        )
    
    async def chat(
        self,
        session: ChatSession,
        user_message: str,
        max_tokens: int = 800,
        top_k: int = 12,
        document_ids: Optional[List[str]] = None,
        window: int = 0
    ) -> Dict[str, Any]:
        """Process a chat message with full tool access.
        
        This method provides the agent with all available tools and lets it
        decide how best to answer the user's question.
        
        Args:
            session: Current chat session
            user_message: User's message
            max_tokens: Maximum tokens for response
            top_k: Default number of results to retrieve
            document_ids: Optional document filter
            window: Default chunk window size
            
        Returns:
            Dict with answer, tool calls, and usage metrics
        """
        # Build message history
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages
            if msg.role != "system"
        ]
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        # Run agent with full tool access
        result = await self.agent.run(
            user_message,
            message_history=messages,
            deps=self.deps,
            model_settings={"max_tokens": max_tokens}
        )
        
        # Extract result data
        response_text = result.data if isinstance(result.data, str) else str(result.data)
        
        # Get all messages including tool calls
        all_messages = result.all_messages()
        
        # Extract tool calls for transparency
        tool_calls = [
            {
                "tool": msg.get("tool_name"),
                "args": msg.get("tool_args"),
                "result": msg.get("tool_result")
            }
            for msg in all_messages
            if msg.get("kind") == "tool-call"
        ]
        
        # Get usage metrics
        usage = result.usage()
        
        return {
            "assistant": response_text,
            "tool_calls": tool_calls,
            "usage_metrics": {
                "total_tokens": usage.total_tokens if usage else 0,
                "prompt_tokens": usage.request_tokens if usage else 0,
                "completion_tokens": usage.response_tokens if usage else 0,
                "model_name": self.deps.config.ai_answer_model_name
            },
            "message_count": len(all_messages)
        }
    
    async def retrieve_and_answer(
        self,
        session: ChatSession,
        user_message: str,
        max_tokens: int = 800,
        top_k: int = 12,
        document_ids: Optional[List[str]] = None,
        window: int = 0
    ) -> Dict[str, Any]:
        """Structured retrieve-then-answer workflow.
        
        This method performs explicit retrieval followed by answer generation,
        giving more control over the process compared to letting the agent
        decide when to use tools.
        
        Args:
            session: Current chat session
            user_message: User's message
            max_tokens: Maximum tokens for response
            top_k: Number of results to retrieve
            document_ids: Optional document filter
            window: Chunk window size
            
        Returns:
            Dict with answer, retrieval results, and metrics
        """
        # Step 1: Expand query
        expansion = await self.search_agent.expand_query_with_context(
            session=session,
            user_message=user_message
        )
        
        # Step 2: Retrieve chunks using expanded query
        from .retrieval import Retriever
        retriever = Retriever(self.deps.search_model, self.deps.search_service)
        
        retrieval_bundle, retrieval_metrics = retriever.retrieve(
            session=session,
            user_message=user_message,
            top_k=top_k,
            document_ids=document_ids,
            window=window
        )
        
        # Step 3: Generate answer using retrieved context
        if retrieval_bundle.results:
            answer_result = await self.answer_agent.generate_answer(
                session=session,
                user_message=user_message,
                max_tokens=max_tokens
            )
            
            assistant_response = answer_result.answer
        else:
            assistant_response = "I couldn't find relevant information in the documents to answer your question."
        
        return {
            "assistant": assistant_response,
            "results": retrieval_bundle.results,
            "retrieval": retrieval_bundle.model_dump(),
            "expansion": expansion.model_dump(),
            "usage_metrics": retrieval_metrics.model_dump()
        }
