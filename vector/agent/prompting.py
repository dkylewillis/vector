"""Pure functions for prompt construction."""

from typing import List
from .models import ChatSession, RetrievalBundle, RetrievalResult


def build_system_prompt() -> str:
    """Build the default system prompt for the research agent.
    
    Returns:
        System prompt string
    """
    return (
        "You are a professional assistant specialized in analyzing municipal "
        "documents, ordinances, and regulations. Your job is to provide accurate, "
        "relevant information based on the given context.\n\n"
        "Instructions:\n"
        "• Answer based only on the provided context\n"
        "• Include specific details, requirements, and references\n"
        "• For each claim, cite the source (e.g., [chunk #3] or [artifact #1])\n"
        "• If the context doesn't contain enough information, explicitly say so\n"
        "• Be concise but thorough\n"
        "• Use professional terminology appropriate for municipal regulations\n"
        "• Note whether information comes from document chunks or extracted artifacts"
    )


def build_expansion_prompt(history_snippet: str, user_message: str) -> str:
    """Build prompt for query expansion.
    
    Args:
        history_snippet: Recent conversation history
        user_message: Current user message
        
    Returns:
        Expansion prompt string
    """
    return (
        "Generate 6-12 focused retrieval keyphrases (comma-separated) for municipal regulation search.\n"
        "Avoid generic words. Be specific to ordinances, zoning, codes, permits, and requirements.\n\n"
        f"Prior conversation:\n{history_snippet}\n\n"
        f"User message:\n{user_message}\n\n"
        "Output only the comma-separated keyphrases, no explanations."
    )


def build_answer_prompt(session: ChatSession, user_message: str, retrieval: RetrievalBundle) -> str:
    """Build the final prompt for answer generation.
    
    Args:
        session: Current chat session
        user_message: User's current message
        retrieval: Retrieval results bundle
        
    Returns:
        Complete answer generation prompt
    """
    # Render recent conversation
    convo = render_recent_messages(session, limit=8)
    
    # Format retrieved context with provenance
    ctx_lines = []
    for i, result in enumerate(retrieval.results, 1):
        ctx_lines.append(
            f"[{i}] (Type: {result.type} | Collection: {result.collection} | "
            f"Score: {result.score:.3f} | File: {result.filename})\n{result.text}"
        )
    context_block = "\n\n".join(ctx_lines)
    
    return (
        f"Conversation so far:\n{convo}\n\n"
        f"New user message: {user_message}\n\n"
        f"Retrieved Context ({len(retrieval.results)} documents):\n{context_block}\n\n"
        "Compose the assistant reply grounded ONLY in the retrieved context and prior conversation turns. "
        "For each claim or fact you mention, cite the source using the [#] notation from above. "
        "If the context is insufficient to fully answer the question, explicitly state that."
    )


def render_recent_messages(session: ChatSession, limit: int = 10) -> str:
    """Render recent non-system messages for context.
    
    Args:
        session: Chat session
        limit: Maximum number of messages to include
        
    Returns:
        Formatted conversation snippet
    """
    non_system = [m for m in session.messages if m.role != 'system']
    relevant = non_system[-limit:] if len(non_system) > limit else non_system
    return "\n".join(f"{m.role.upper()}: {m.content}" for m in relevant)


def format_results_for_display(results: List[RetrievalResult]) -> str:
    """Format search results for user display.
    
    Args:
        results: List of retrieval results
        
    Returns:
        Formatted string for display
    """
    if not results:
        return "No results found."
    
    formatted_parts = []
    for i, result in enumerate(results, 1):
        formatted_parts.append(
            f"Result {i} (Score: {result.score:.3f}, Type: {result.type}):\n"
            f"Source: {result.filename}\n"
            f"Collection: {result.collection}\n"
            f"Content: {result.text}\n"
        )
    
    return "\n".join(formatted_parts)
