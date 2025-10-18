"""Context building pipeline - pluggable RAG orchestration.

This module provides a simple, composable pipeline for building context
that will be used for chat responses. Steps can include:
- Query expansion (AI-powered)
- Vector search (pure retrieval)
- Result filtering
- Context window expansion
- Diagnostics

Context building can include both AI-powered operations (agents) and 
pure retrieval operations.
"""

from typing import List, Dict, Any
from abc import ABC, abstractmethod

# Import models from agent for now (backward compatibility)
# TODO: Consider moving these models to vector.models in future
from vector.agent.models import ChatSession, RetrievalResult, UsageMetrics


class ContextBuildResult:
    """Shared state passed through context building pipeline steps.
    
    Attributes:
        session: Chat session with conversation history
        user_message: Original user message
        query: Current query (may be modified by steps)
        results: Retrieved results (populated by steps)
        metadata: Additional metadata from steps
        usage_metrics: Usage metrics from AI operations
    """
    
    def __init__(
        self,
        session: ChatSession,
        user_message: str,
        query: str,
        results: List[RetrievalResult] = None,
        metadata: Dict[str, Any] = None,
        usage_metrics: List[UsageMetrics] = None
    ):
        """Initialize context build result.
        
        Args:
            session: Chat session with conversation history
            user_message: Original user message
            query: Current query (may be modified by steps)
            results: Retrieved results (populated by steps)
            metadata: Additional metadata from steps
            usage_metrics: Usage metrics from AI operations
        """
        self.session = session
        self.user_message = user_message
        self.query = query
        self.results = results or []
        self.metadata = metadata or {}
        self.usage_metrics = usage_metrics or []
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata from a pipeline step.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def add_usage(self, metrics: UsageMetrics) -> None:
        """Track usage metrics from a pipeline step.
        
        Args:
            metrics: Usage metrics to track
        """
        if metrics and metrics.total_tokens > 0:
            self.usage_metrics.append(metrics)


class ContextStep(ABC):
    """Abstract base class for context building pipeline steps.
    
    Each step processes the context and returns a modified context.
    Steps can:
    - Modify the query (e.g., query expansion using AI)
    - Add/filter results (e.g., vector search, filtering)
    - Enrich metadata
    - Track usage metrics
    """
    
    @abstractmethod
    def __call__(self, context: ContextBuildResult) -> ContextBuildResult:
        """Process the context and return modified context.
        
        Args:
            context: Current pipeline context
            
        Returns:
            Modified context (can be same object or new one)
        """
        pass
    
    @property
    def name(self) -> str:
        """Step name for logging/debugging."""
        return self.__class__.__name__


class ContextPipeline:
    """Executes a sequence of context building steps.
    
    Example:
        >>> from vector.context import ContextPipeline, SearchStep, ScoreFilter
        >>> 
        >>> pipeline = ContextPipeline()
        >>> pipeline.add_step(SearchStep(search_service, top_k=12))
        >>> pipeline.add_step(ScoreFilter(min_score=0.5))
        >>> 
        >>> context = ContextBuildResult(session, message, query)
        >>> result = pipeline.run(context)
    """
    
    def __init__(self, steps: List[ContextStep] = None):
        """Initialize pipeline with steps.
        
        Args:
            steps: List of pipeline steps to execute in order
        """
        self.steps = steps or []
    
    def add_step(self, step: ContextStep) -> 'ContextPipeline':
        """Add a step to the pipeline (builder pattern).
        
        Args:
            step: Pipeline step to add
            
        Returns:
            Self for method chaining
        """
        self.steps.append(step)
        return self
    
    def run(self, context: ContextBuildResult) -> ContextBuildResult:
        """Execute all steps in sequence.
        
        Args:
            context: Initial context
            
        Returns:
            Final context after all steps
        """
        for step in self.steps:
            try:
                context = step(context)
            except Exception as e:
                print(f"Warning: Pipeline step {step.name} failed: {e}")
                context.add_metadata(f"{step.name}_error", str(e))
        
        return context
