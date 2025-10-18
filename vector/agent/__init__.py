"""Vector Agent - Search and Q&A functionality with PydanticAI integration.

This module provides high-level agent capabilities for conversational search
and question answering over document collections.

Core Components:
- ChatService: Multi-turn conversation management with retrieval
- PydanticAI Agents: SearchAgent, AnswerAgent, ResearchAgent
- Agent Tools: retrieve_chunks, search_documents, etc.
- Memory Management: SummarizerPolicy for conversation history

Note: For context building orchestration, import from vector.context instead:
    from vector.context import ContextOrchestrator, ContextPipeline, ContextStep
"""

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

# Memory management
from .memory import SummarizerPolicy, NoSummarizerPolicy

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


def __getattr__(name):
    """Lazy imports for backward compatibility.
    
    Provides backward compatibility for code that imports retrieval
    components from vector.agent. New code should import directly from
    vector.context instead.
    
    Supported for backward compatibility:
    - Retriever (alias for ContextOrchestrator)
    - RetrievalOrchestrator (alias for ContextOrchestrator)
    - Pipeline, PipelineStep, RetrievalContext
    - QueryExpansionStep, SearchStep, ScoreFilter, DiagnosticsStep
    """
    if name in ('Retriever', 'RetrievalOrchestrator'):
        from vector.context import ContextOrchestrator
        return ContextOrchestrator
    elif name in ('Pipeline', 'PipelineStep', 'RetrievalContext'):
        from vector.context import Pipeline, PipelineStep, RetrievalContext
        return {'Pipeline': Pipeline, 'PipelineStep': PipelineStep, 'RetrievalContext': RetrievalContext}[name]
    elif name in ('QueryExpansionStep', 'SearchStep', 'ScoreFilter', 'DiagnosticsStep'):
        from vector.context import QueryExpansionStep, SearchStep, ScoreFilter, DiagnosticsStep
        return {'QueryExpansionStep': QueryExpansionStep, 'SearchStep': SearchStep, 
                'ScoreFilter': ScoreFilter, 'DiagnosticsStep': DiagnosticsStep}[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


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
    
    # Memory management
    'SummarizerPolicy',
    'NoSummarizerPolicy',
    
    # PydanticAI components
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
    
    # Backward compatibility (lazy loaded via __getattr__)
    # These are provided for backward compatibility only
    # New code should import from vector.context
    'Retriever',
    'RetrievalOrchestrator',
    'Pipeline',
    'PipelineStep',
    'RetrievalContext',
    'QueryExpansionStep',
    'SearchStep',
    'ScoreFilter',
    'DiagnosticsStep',
]
