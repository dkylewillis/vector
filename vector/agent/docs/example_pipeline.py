"""Example demonstrating pipeline usage."""

from vector.agent import (
    Pipeline, 
    PipelineStep, 
    RetrievalContext,
    QueryExpansionStep,
    SearchStep,
    ScoreFilter,
    DiagnosticsStep,
    ChatSession
)


def example_custom_step():
    """Example of creating a custom pipeline step."""
    
    class TypeBalancer(PipelineStep):
        """Ensures minimum representation of each result type."""
        
        def __init__(self, min_per_type: int = 2):
            self.min_per_type = min_per_type
        
        def __call__(self, context: RetrievalContext) -> RetrievalContext:
            """Balance result types."""
            if len(context.results) <= self.min_per_type:
                return context
            
            # Group by type
            by_type = {}
            for result in context.results:
                by_type.setdefault(result.type, []).append(result)
            
            # Take top min_per_type from each type
            balanced = []
            for type_results in by_type.values():
                balanced.extend(type_results[:self.min_per_type])
            
            # Add remaining results by score
            remaining = [r for r in context.results if r not in balanced]
            remaining.sort(key=lambda r: r.score, reverse=True)
            balanced.extend(remaining)
            
            context.results = balanced
            context.add_metadata("type_balanced", True)
            
            return context
    
    return TypeBalancer


def example_pipeline_usage():
    """Example of using a custom pipeline."""
    
    # Assume we have these initialized
    search_model = None  # Your AI model
    search_service = None  # Your SearchService
    
    # Create custom step
    TypeBalancer = example_custom_step()
    
    # Build custom pipeline
    pipeline = (
        Pipeline()
        .add_step(QueryExpansionStep(search_model))
        .add_step(SearchStep(search_service, top_k=20))
        .add_step(ScoreFilter(min_score=0.4))
        .add_step(TypeBalancer(min_per_type=3))
        .add_step(DiagnosticsStep())
    )
    
    # Create context
    session = ChatSession(id="test", system_prompt="You are a helpful assistant.")
    context = RetrievalContext(
        session=session,
        user_message="What is machine learning?",
        query="What is machine learning?"
    )
    
    # Run pipeline
    context = pipeline.run(context)
    
    # Access results
    print(f"Found {len(context.results)} results")
    print(f"Metadata: {context.metadata}")
    
    return context


if __name__ == "__main__":
    print("Pipeline Examples")
    print("=" * 50)
    
    print("\n1. Creating a custom step:")
    TypeBalancer = example_custom_step()
    print(f"   Created: {TypeBalancer.__name__}")
    
    print("\n2. Using a custom pipeline:")
    print("   See example_pipeline_usage() function")
    
    print("\n3. Benefits:")
    print("   ✓ Easy to add new steps")
    print("   ✓ Easy to remove steps")
    print("   ✓ Easy to reorder steps")
    print("   ✓ Easy to test steps independently")
    print("   ✓ Clear, understandable code")
