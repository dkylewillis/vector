"""Retrieval orchestration with query expansion."""

import time
from typing import Optional, List, Tuple, Dict, Any
from ..core.services.search import SearchService, SearchResult
from .models import ChatSession, RetrievalResult, RetrievalBundle, UsageMetrics
from .prompting import build_expansion_prompt, render_recent_messages


class Retriever:
    """Orchestrates retrieval with optional query expansion."""
    
    def __init__(self, search_model, search_service: SearchService):
        """Initialize the retriever.
        
        Args:
            search_model: Optional AI model for query expansion (or None)
            search_service: SearchService instance for document retrieval
        """
        self.search_model = search_model
        self.search_service = search_service
    
    def expand_query(self, history: str, user_message: str) -> Tuple[str, List[str], UsageMetrics]:
        """Expand query using conversation context.
        
        Args:
            history: Recent conversation history
            user_message: Current user message
            
        Returns:
            Tuple of (expanded_query, keyphrases_list, usage_metrics)
        """
        if not self.search_model:
            return user_message, [], UsageMetrics()
        
        prompt = build_expansion_prompt(history, user_message)
        
        try:
            response_text, metrics_dict = self.search_model.generate_response(
                prompt=prompt,
                system_prompt="You output only comma-separated keyphrases for document retrieval. No explanations.",
                max_tokens=96,
                operation="search"  # Mark this as search operation
            )
            
            # Convert dict to UsageMetrics
            usage_metrics = UsageMetrics(**metrics_dict)
            
            # Parse keyphrases
            keyphrases = [kp.strip() for kp in response_text.split(",") if kp.strip()]
            
            # Merge keyphrases into query
            if keyphrases:
                expanded_query = ", ".join(keyphrases)
            else:
                expanded_query = user_message
            
            return expanded_query, keyphrases, usage_metrics
            
        except Exception as e:
            # Fallback to original query on error
            print(f"Warning: Query expansion failed: {e}")
            return user_message, [], UsageMetrics()
    
    def retrieve(
        self,
        session: ChatSession,
        user_message: str,
        top_k: int = 12,
        search_type: str = "both",
        document_ids: Optional[List[str]] = None
    ) -> Tuple[RetrievalBundle, UsageMetrics]:
        """Perform retrieval with query expansion.
        
        Args:
            session: Current chat session
            user_message: User's current message
            top_k: Number of results to retrieve
            search_type: Type of search ('chunks', 'artifacts', or 'both')
            document_ids: Optional list of document IDs to filter
            
        Returns:
            Tuple of (retrieval_bundle, expansion_usage_metrics)
        """
        # Build expansion context from recent history
        history = render_recent_messages(session, limit=6)
        
        # Expand query
        expanded_query, keyphrases, expansion_metrics = self.expand_query(history, user_message)
        
        # Perform search with timing
        start_time = time.time()
        search_results = self.search_service.search(
            query=expanded_query,
            top_k=top_k,
            search_type=search_type,
            document_ids=document_ids
        )
        
        # Convert SearchResult to RetrievalResult
        results = [self._convert_result(r) for r in search_results]
        latency_ms = (time.time() - start_time) * 1000
        
        # Build diagnostics
        diagnostics = {
            "latency_ms": round(latency_ms, 2),
            "result_count": len(results),
            "query_expanded": len(keyphrases) > 0,
            "keyphrase_count": len(keyphrases)
        }
        
        # Add result breakdown by type
        if results:
            type_counts = {}
            for r in results:
                type_counts[r.type] = type_counts.get(r.type, 0) + 1
            diagnostics["results_by_type"] = type_counts
        
        retrieval_bundle = RetrievalBundle(
            original_query=user_message,
            expanded_query=expanded_query,
            keyphrases=keyphrases,
            results=results,
            diagnostics=diagnostics
        )
        
        return retrieval_bundle, expansion_metrics
    
    def _convert_result(self, search_result: SearchResult) -> RetrievalResult:
        """Convert SearchResult to RetrievalResult.
        
        Args:
            search_result: Original SearchResult from SearchService
            
        Returns:
            Converted RetrievalResult
        """
        collection = "artifacts" if search_result.type == "artifact" else "chunks"
        
        return RetrievalResult(
            filename=search_result.filename,
            doc_id=search_result.id,
            type=search_result.type,
            score=search_result.score,
            text=search_result.text,
            collection=collection,
            chunk=search_result.chunk,
            artifact=search_result.artifact
        )
