"""Vector Agent - Search and Q&A functionality."""

from .agent import ResearchAgent
from .models import ChatSession, ChatMessage, RetrievalResult, RetrievalBundle
from .prompting import (
    build_system_prompt,
    build_expansion_prompt,
    build_answer_prompt
)
from .memory import SummarizerPolicy, NoSummarizerPolicy
from .retrieval import Retriever
from .pipeline import Pipeline, PipelineStep, RetrievalContext
from .steps import QueryExpansionStep, SearchStep, ScoreFilter, DiagnosticsStep

__all__ = [
    'ResearchAgent',
    'ChatSession',
    'ChatMessage',
    'RetrievalResult',
    'RetrievalBundle',
    'build_system_prompt',
    'build_expansion_prompt',
    'build_answer_prompt',
    'SummarizerPolicy',
    'NoSummarizerPolicy',
    'Retriever',
    'Pipeline',
    'PipelineStep',
    'RetrievalContext',
    'QueryExpansionStep',
    'SearchStep',
    'ScoreFilter',
    'DiagnosticsStep'
]

