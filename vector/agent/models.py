"""Data models for the research agent."""

from __future__ import annotations
import time
from typing import List, Optional, Dict, Any, Literal, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from vector.models import Chunk, Artifact


class ChatMessage(BaseModel):
    """Chat message with role and content."""
    role: Literal['system', 'user', 'assistant'] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    created_at: float = Field(default_factory=time.time, description="Message creation timestamp")


class ChatSession(BaseModel):
    """Chat session with message history."""
    id: str = Field(..., description="Session identifier")
    system_prompt: str = Field(..., description="System prompt for this session")
    messages: List[ChatMessage] = Field(default_factory=list, description="Message history")
    summary: Optional[str] = Field(None, description="Compressed history summary")
    created_at: float = Field(default_factory=time.time, description="Session creation timestamp")
    last_updated: float = Field(default_factory=time.time, description="Last update timestamp")

    def add(self, role: str, content: str) -> None:
        """Add a message to the session.
        
        Args:
            role: Message role (user/assistant/system)
            content: Message content
        """
        self.messages.append(ChatMessage(role=role, content=content))
        self.last_updated = time.time()


class RetrievalResult(BaseModel):
    """A single retrieval result with provenance information."""
    filename: str = Field(..., description="Source filename")
    doc_id: str = Field(..., description="Document identifier")
    type: str = Field(..., description="Result type (chunk/artifact)")
    score: float = Field(..., description="Similarity score")
    text: str = Field(..., description="Retrieved text content")
    collection: str = Field(..., description="Collection name")
    # Optional: preserve original chunk/artifact objects for web interface
    chunk: Optional[Any] = Field(None, description="Original chunk object if available")
    artifact: Optional[Any] = Field(None, description="Original artifact object if available")


class UsageMetrics(BaseModel):
    """Token usage and performance metrics from AI model calls."""
    prompt_tokens: int = Field(0, description="Number of tokens in the prompt")
    completion_tokens: int = Field(0, description="Number of tokens in the completion")
    total_tokens: int = Field(0, description="Total tokens used")
    model_name: Optional[str] = Field(None, description="Name of the model used")
    latency_ms: Optional[float] = Field(None, description="Latency in milliseconds")
    operation: Optional[str] = Field(None, description="Operation type (e.g., 'search', 'answer', 'summarization')")


class AggregatedUsageMetrics(BaseModel):
    """Aggregated usage metrics with breakdown by operation."""
    total_prompt_tokens: int = Field(0, description="Total prompt tokens across all operations")
    total_completion_tokens: int = Field(0, description="Total completion tokens across all operations")
    total_tokens: int = Field(0, description="Total tokens across all operations")
    total_latency_ms: float = Field(0, description="Total latency across all operations")
    operations: List[UsageMetrics] = Field(default_factory=list, description="Individual operation metrics")
    
    @classmethod
    def from_operations(cls, operations: List[UsageMetrics]) -> 'AggregatedUsageMetrics':
        """Create aggregated metrics from a list of operation metrics.
        
        Args:
            operations: List of UsageMetrics for individual operations
            
        Returns:
            AggregatedUsageMetrics with totals and breakdown
        """
        return cls(
            total_prompt_tokens=sum(op.prompt_tokens for op in operations),
            total_completion_tokens=sum(op.completion_tokens for op in operations),
            total_tokens=sum(op.total_tokens for op in operations),
            total_latency_ms=sum(op.latency_ms or 0 for op in operations),
            operations=operations
        )
    
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to include backward compatibility fields."""
        result = super().model_dump(**kwargs)
        
        # Add backward compatibility fields
        result['prompt_tokens'] = self.total_prompt_tokens
        result['completion_tokens'] = self.total_completion_tokens
        result['latency_ms'] = self.total_latency_ms
        
        # Add model names summary
        model_names = [op.model_name for op in self.operations if op.model_name]
        if model_names:
            unique_models = list(dict.fromkeys(model_names))  # Preserve order, remove duplicates
            result['model_name'] = ' + '.join(unique_models) if len(unique_models) > 1 else unique_models[0]
        
        # Convert operations to dicts with clearer names
        if self.operations:
            result['breakdown'] = [op.model_dump() for op in self.operations]
            
            # Also provide named breakdowns for easier access
            for op in self.operations:
                if op.operation == 'search':
                    result['search_metrics'] = op.model_dump()
                elif op.operation == 'answer':
                    result['answer_metrics'] = op.model_dump()
                elif op.operation == 'summarization':
                    result['summarization_metrics'] = op.model_dump()
        
        return result


class RetrievalBundle(BaseModel):
    """Complete retrieval operation result with diagnostics."""
    original_query: str = Field(..., description="Original user query")
    expanded_query: str = Field(..., description="Expanded search query")
    keyphrases: List[str] = Field(default_factory=list, description="Extracted keyphrases")
    results: List[RetrievalResult] = Field(default_factory=list, description="Search results")
    diagnostics: Dict[str, Any] = Field(default_factory=dict, description="Performance and debug info")
