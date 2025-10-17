"""PydanticAI tool definitions for agent capabilities."""

from typing import List, Optional
from pydantic import Field
from pydantic_ai import RunContext

from .deps import AgentDeps
from .models import ChatSession, RetrievalBundle, RetrievalResult
from .prompting import build_expansion_prompt, render_recent_messages


async def retrieve_chunks(
    ctx: RunContext[AgentDeps],
    session: ChatSession,
    user_message: str = Field(..., description="User query to search for"),
    top_k: int = Field(12, ge=1, le=50, description="Number of results to retrieve"),
    document_ids: Optional[List[str]] = Field(None, description="Optional list of document IDs to filter"),
    window: int = Field(0, ge=0, le=5, description="Number of surrounding chunks to include"),
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum relevance score threshold"),
) -> RetrievalBundle:
    """Retrieve document chunks using the full retrieval pipeline.
    
    This tool orchestrates query expansion and vector search to find relevant
    document chunks. It's the primary tool for retrieving information from the
    document collection.
    
    Args:
        ctx: PydanticAI run context with dependencies
        session: Current chat session with conversation history
        user_message: The user's query to search for
        top_k: Number of results to retrieve (1-50)
        document_ids: Optional filter to specific documents
        window: Number of surrounding chunks to include for context (0-5)
        min_score: Optional minimum relevance score (0.0-1.0)
        
    Returns:
        RetrievalBundle with results and diagnostics
    """
    # Import retriever (avoid circular imports)
    from .retrieval import Retriever
    
    # Create retriever with dependencies
    retriever = Retriever(
        ctx.deps.search_model,
        ctx.deps.search_service
    )
    
    # Perform retrieval using existing pipeline
    bundle, _metrics = retriever.retrieve(
        session=session,
        user_message=user_message,
        top_k=top_k,
        document_ids=document_ids,
        window=window,
        min_score=min_score
    )
    
    return bundle


async def expand_query(
    ctx: RunContext[AgentDeps],
    session: ChatSession,
    user_message: str = Field(..., description="Original user query to expand"),
) -> dict:
    """Expand a user query into search keyphrases using conversation context.
    
    This tool uses the AI model to generate focused keyphrases for better
    document retrieval, considering the conversation history.
    
    Args:
        ctx: PydanticAI run context with dependencies
        session: Current chat session for context
        user_message: The user's original query
        
    Returns:
        Dict with expanded_query and keyphrases list
    """
    if not ctx.deps.search_model:
        return {
            "expanded_query": user_message,
            "keyphrases": [],
            "expanded": False
        }
    
    # Build expansion context from recent history
    history = render_recent_messages(session, limit=6)
    prompt = build_expansion_prompt(history, user_message)
    
    try:
        response_text, metrics_dict = ctx.deps.search_model.generate_response(
            prompt=prompt,
            system_prompt="You output only comma-separated keyphrases for document retrieval. No explanations.",
            max_tokens=96,
            operation="search"
        )
        
        # Parse keyphrases
        keyphrases = [kp.strip() for kp in response_text.split(",") if kp.strip()]
        expanded_query = ", ".join(keyphrases) if keyphrases else user_message
        
        return {
            "expanded_query": expanded_query,
            "keyphrases": keyphrases,
            "expanded": True,
            "metrics": metrics_dict
        }
    except Exception as e:
        return {
            "expanded_query": user_message,
            "keyphrases": [],
            "expanded": False,
            "error": str(e)
        }


async def search_documents(
    ctx: RunContext[AgentDeps],
    query: str = Field(..., description="Search query string"),
    top_k: int = Field(12, ge=1, le=50, description="Number of results"),
    document_ids: Optional[List[str]] = Field(None, description="Optional document ID filter"),
    window: int = Field(0, ge=0, le=5, description="Surrounding chunk window size"),
) -> List[RetrievalResult]:
    """Perform direct vector search without query expansion.
    
    This is a lower-level tool for direct semantic search when you already
    have a well-formed query and don't need conversation-aware expansion.
    
    Args:
        ctx: PydanticAI run context with dependencies
        query: The search query string
        top_k: Number of results to retrieve (1-50)
        document_ids: Optional filter to specific documents
        window: Number of surrounding chunks for context (0-5)
        
    Returns:
        List of RetrievalResult objects
    """
    # Perform search directly through search service
    search_results = ctx.deps.search_service.search(
        query=query,
        top_k=top_k,
        document_ids=document_ids,
        window=window
    )
    
    # Convert to RetrievalResult format
    results = []
    for sr in search_results:
        results.append(RetrievalResult(
            filename=sr.filename,
            doc_id=sr.id,
            type=sr.type,
            score=sr.score,
            text=sr.text,
            collection="chunks",
            chunk=sr.chunk,
            artifact=sr.artifact
        ))
    
    return results


async def get_chunk_window(
    ctx: RunContext[AgentDeps],
    chunk_id: str = Field(..., description="ID of the chunk to get context for"),
    window: int = Field(2, ge=1, le=5, description="Number of chunks before and after"),
) -> dict:
    """Get surrounding chunks for context around a specific chunk.
    
    This tool retrieves the chunks immediately before and after a given chunk
    to provide additional context. Useful when you need more information about
    a specific search result.
    
    Args:
        ctx: PydanticAI run context with dependencies
        chunk_id: The ID of the central chunk
        window: Number of chunks to get before and after (1-5)
        
    Returns:
        Dict with before, target, and after chunk texts
    """
    try:
        # Use search service's window functionality
        # This is a simplified version - you may need to implement this method
        # in SearchService if it doesn't exist
        window_chunks = ctx.deps.search_service.get_chunk_window(chunk_id, window)
        
        return {
            "chunk_id": chunk_id,
            "window_size": window,
            "chunks": window_chunks,
            "success": True
        }
    except Exception as e:
        return {
            "chunk_id": chunk_id,
            "window_size": window,
            "chunks": [],
            "success": False,
            "error": str(e)
        }


async def get_document_metadata(
    ctx: RunContext[AgentDeps],
    document_id: str = Field(..., description="Document ID to get metadata for"),
) -> dict:
    """Get metadata for a specific document.
    
    Retrieves document-level information like title, type, page count, etc.
    
    Args:
        ctx: PydanticAI run context with dependencies
        document_id: The ID of the document
        
    Returns:
        Dict with document metadata
    """
    try:
        # Get document from search service
        doc = ctx.deps.search_service.get_document_by_id(document_id)
        
        if doc:
            return {
                "document_id": document_id,
                "filename": doc.filename,
                "type": doc.type,
                "metadata": doc.metadata,
                "success": True
            }
        else:
            return {
                "document_id": document_id,
                "success": False,
                "error": "Document not found"
            }
    except Exception as e:
        return {
            "document_id": document_id,
            "success": False,
            "error": str(e)
        }


async def list_available_documents(
    ctx: RunContext[AgentDeps],
    limit: int = Field(100, ge=1, le=500, description="Maximum documents to return"),
) -> dict:
    """List all available documents in the collection.
    
    Retrieves a list of all documents that can be searched. Useful for
    understanding what information is available.
    
    Args:
        ctx: PydanticAI run context with dependencies
        limit: Maximum number of documents to return (1-500)
        
    Returns:
        Dict with document list and count
    """
    try:
        # Get all documents from search service
        documents = ctx.deps.search_service.list_documents(limit=limit)
        
        return {
            "count": len(documents),
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "type": doc.type
                }
                for doc in documents
            ],
            "success": True
        }
    except Exception as e:
        return {
            "count": 0,
            "documents": [],
            "success": False,
            "error": str(e)
        }
