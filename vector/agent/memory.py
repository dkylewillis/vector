"""Conversation memory and summarization policies."""

from .models import ChatSession, ChatMessage


class SummarizerPolicy:
    """Policy for managing conversation memory through summarization."""
    
    def __init__(self, ai_model, trigger_messages: int = 18, keep_recent: int = 6):
        """Initialize the summarizer policy.
        
        Args:
            ai_model: AI model to use for summarization
            trigger_messages: Number of messages before triggering summarization
            keep_recent: Number of recent messages to keep after summarization
        """
        self.ai_model = ai_model
        self.trigger_messages = trigger_messages
        self.keep_recent = keep_recent
    
    def should_compact(self, session: ChatSession) -> bool:
        """Check if session should be compacted.
        
        Args:
            session: Chat session to check
            
        Returns:
            True if compaction should occur
        """
        return len(session.messages) >= self.trigger_messages
    
    def compact(self, session: ChatSession) -> None:
        """Compact session history by summarizing old messages.
        
        Args:
            session: Chat session to compact
        """
        if not self.should_compact(session):
            return
        
        # Get messages to summarize (exclude system and recent messages)
        non_system = [m for m in session.messages if m.role != 'system']
        if len(non_system) <= self.keep_recent:
            return
        
        messages_to_summarize = non_system[:-self.keep_recent]
        if not messages_to_summarize:
            return
        
        # Build text to summarize
        text = "\n".join(f"{m.role}: {m.content}" for m in messages_to_summarize)
        
        # Generate summary
        try:
            summary, _ = self.ai_model.generate_response(
                prompt=f"Summarize these municipal regulation Q&A turns into a compact factual session memory:\n{text}",
                system_prompt="You compress conversation history; preserve obligations, constraints, definitions, and key entities.",
                max_tokens=300,
                operation="summarization"
            )
            
            session.summary = summary
            
            # Reconstruct messages: system + summary marker + recent messages
            system_msg = session.messages[0]  # Original system message
            recent_msgs = non_system[-self.keep_recent:]
            
            session.messages = [
                system_msg,
                ChatMessage(role='system', content=f"[CONVERSATION HISTORY SUMMARY]\n{summary}")
            ] + recent_msgs
            
        except Exception as e:
            # If summarization fails, continue without it
            print(f"Warning: Summarization failed: {e}")
            pass


class NoSummarizerPolicy:
    """Policy that performs no summarization - keeps all messages."""
    
    def should_compact(self, session: ChatSession) -> bool:
        """Always returns False - no compaction needed.
        
        Args:
            session: Chat session (unused)
            
        Returns:
            False
        """
        return False
    
    def compact(self, session: ChatSession) -> None:
        """No-op compaction.
        
        Args:
            session: Chat session (unused)
        """
        pass
