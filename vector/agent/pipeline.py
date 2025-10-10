"""Simple, pluggable retrieval pipeline."""

from typing import List, Dict, Any
from abc import ABC, abstractmethod
from .models import ChatSession, RetrievalResult, UsageMetrics


class RetrievalContext:
    """Shared state passed through pipeline steps."""
    
    def __init__(
        self,
        session: ChatSession,
        user_message: str,
        query: str,
        results: List[RetrievalResult] = None,
        metadata: Dict[str, Any] = None,
        usage_metrics: List[UsageMetrics] = None
    ):
        """Initialize retrieval context.
        
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


class PipelineStep(ABC):
    """Abstract base class for retrieval pipeline steps."""
    
    @abstractmethod
    def __call__(self, context: RetrievalContext) -> RetrievalContext:
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


class Pipeline:
    """Executes a sequence of retrieval steps."""
    
    def __init__(self, steps: List[PipelineStep] = None):
        """Initialize pipeline with steps.
        
        Args:
            steps: List of pipeline steps to execute in order
        """
        self.steps = steps or []
    
    def add_step(self, step: PipelineStep) -> 'Pipeline':
        """Add a step to the pipeline (builder pattern).
        
        Args:
            step: Pipeline step to add
            
        Returns:
            Self for method chaining
        """
        self.steps.append(step)
        return self
    
    def run(self, context: RetrievalContext) -> RetrievalContext:
        """Execute all steps in sequence.
        
        Args:
            context: Initial retrieval context
            
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
