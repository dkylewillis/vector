"""
Quick Start Guide: Chat Functionality
=====================================

This guide shows you how to use the new chat functionality in your Vector agent.
"""

from vector.agent import ResearchAgent
from vector.config import Config

# Initialize the agent
config = Config()
agent = ResearchAgent(config=config)

print("=" * 70)
print("CHAT FUNCTIONALITY DEMO")
print("=" * 70)

# 1. Start a chat session
print("\n1. Starting a new chat session...")
session_id = agent.start_chat()
print(f"   ✅ Session created: {session_id}")

# 2. Send first message
print("\n2. Sending first message...")
print("   User: 'What are R-1 residential setback requirements?'")
result1 = agent.chat(
    session_id=session_id,
    user_message="What are R-1 residential setback requirements?",
    response_length="medium",
    search_type="both",
    top_k=10
)
print(f"\n   Assistant response:")
print(f"   {result1['assistant'][:200]}...")
print(f"   Message count: {result1['message_count']}")
print(f"   Results found: {len(result1['results'])}")

# 3. Send follow-up question (context-aware)
print("\n3. Sending follow-up question (context-aware)...")
print("   User: 'How about for corner lots?'")
result2 = agent.chat(
    session_id=session_id,
    user_message="How about for corner lots?",
    response_length="short"
)
print(f"\n   Assistant response:")
print(f"   {result2['assistant'][:200]}...")
print(f"   Message count: {result2['message_count']}")

# 4. Another follow-up
print("\n4. Another follow-up question...")
print("   User: 'What about parking requirements?'")
result3 = agent.chat(
    session_id=session_id,
    user_message="What about parking requirements?"
)
print(f"\n   Assistant response:")
print(f"   {result3['assistant'][:200]}...")
print(f"   Message count: {result3['message_count']}")

# 5. Get session info
print("\n5. Retrieving session information...")
session = agent.get_session(session_id)
print(f"   Session ID: {session.id}")
print(f"   Total messages: {len(session.messages)}")
print(f"   Created: {session.created_at}")
print(f"   Last updated: {session.last_updated}")
print(f"   Has summary: {session.summary is not None}")

# 6. End the session
print("\n6. Ending the chat session...")
ended = agent.end_chat(session_id)
print(f"   ✅ Session ended: {ended}")

# Verify session is gone
session_check = agent.get_session(session_id)
print(f"   Session still exists: {session_check is not None}")

print("\n" + "=" * 70)
print("CHAT FEATURES DEMONSTRATED")
print("=" * 70)
print("""
✅ Multi-turn conversation with context awareness
✅ Follow-up questions understood in context
✅ Configurable response lengths and search types
✅ Session state management (start, get, end)
✅ Message history tracking
✅ Timestamp management

TRY IT YOURSELF:
----------------
from vector.agent import ResearchAgent

agent = ResearchAgent()
session_id = agent.start_chat()

# Ask your questions
result = agent.chat(
    session_id=session_id,
    user_message="Your question here",
    response_length="medium",  # short, medium, or long
    search_type="both",        # chunks, artifacts, or both
    top_k=12                   # number of search results
)

print(result['assistant'])

# Don't forget to clean up
agent.end_chat(session_id)
""")

print("\n" + "=" * 70)
