"""Vector Agent - Search and Q&A functionality with PydanticAI integration."""

# Primary API
from .chat_service import ChatService

# Data models
from .models import ChatSession, ChatMessage, RetrievalResult, RetrievalBundle

# Prompting
from .prompting import (
    build_system_prompt,
    build_expansion_prompt,
    build_answer_prompt
)

# Memory and retrieval
from .memory import SummarizerPolicy, NoSummarizerPolicy
from .retrieval import Retriever

# Pipeline (classic mode)
from .pipeline import Pipeline, PipelineStep, RetrievalContext
from .steps import QueryExpansionStep, SearchStep, ScoreFilter, DiagnosticsStep

# PydanticAI components
from .deps import AgentDeps
from .agents import (
    SearchAgent,
    AnswerAgent,
    ResearchAgent
)
from .tools import (
    retrieve_chunks,
    expand_query,
    search_documents,
    get_chunk_window,
    get_document_metadata,
    list_available_documents
)

# MCP server
try:
    from .mcp_server import VectorMCPServer, create_mcp_server
    MCP_AVAILABLE = True
except ImportError:
    VectorMCPServer = None
    create_mcp_server = None
    MCP_AVAILABLE = False

__all__ = [
    # Primary API
    'ChatService',
    
    # Data models
    'ChatSession',
    'ChatMessage',
    'RetrievalResult',
    'RetrievalBundle',
    
    # Prompting
    'build_system_prompt',
    'build_expansion_prompt',
    'build_answer_prompt',
    
    # Memory and retrieval
    'SummarizerPolicy',
    'NoSummarizerPolicy',
    'Retriever',
    
    # Pipeline (classic mode)
    'Pipeline',
    'PipelineStep',
    'RetrievalContext',
    'QueryExpansionStep',
    'SearchStep',
    'ScoreFilter',
    'DiagnosticsStep',
    
    # PydanticAI agents
    'AgentDeps',
    'SearchAgent',
    'AnswerAgent',
    'ResearchAgent',
    
    # Tools
    'retrieve_chunks',
    'expand_query',
    'search_documents',
    'get_chunk_window',
    'get_document_metadata',
    'list_available_documents',
    
    # MCP server
    'VectorMCPServer',
    'create_mcp_server',
    'MCP_AVAILABLE',
]

