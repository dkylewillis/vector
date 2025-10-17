"""Simple, pluggable retrieval pipeline.

DEPRECATED: This module has been moved to vector.retrieval for better separation of concerns.
Imports are re-exported here for backward compatibility.

Please update your imports:
    from vector.agent.pipeline import Pipeline  # Old
    from vector.retrieval import Pipeline       # New
"""

# Re-export from vector.retrieval for backward compatibility
from vector.retrieval.pipeline import (
    RetrievalContext,
    PipelineStep,
    Pipeline
)

__all__ = ["RetrievalContext", "PipelineStep", "Pipeline"]
