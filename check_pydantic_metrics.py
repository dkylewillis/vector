"""Check PydanticAI metrics capabilities."""

from pydantic_ai import Agent

# Create a simple agent
agent = Agent('openai:gpt-4')

print("PydanticAI Agent Capabilities")
print("=" * 60)

# Check for usage/metrics methods
print("\nUsage-related attributes:")
usage_attrs = [attr for attr in dir(agent) if 'usage' in attr.lower() or 'metric' in attr.lower()]
for attr in usage_attrs:
    print(f"  - {attr}")

print("\nResult attributes (after run):")
print("  When you call agent.run(), the result has:")
print("  - result.usage() -> Usage object with token counts")
print("  - result.all_messages() -> Full conversation trace")
print("  - result.data -> The actual response")
print("  - result.timestamp() -> When the run completed")

print("\nUsage object contains:")
print("  - request_tokens (prompt tokens)")
print("  - response_tokens (completion tokens)")
print("  - total_tokens")
print("  - details (provider-specific details)")

print("\nExample usage:")
print("""
async def chat_example():
    result = await agent.run("hello")
    usage = result.usage()
    
    print(f"Prompt tokens: {usage.request_tokens}")
    print(f"Response tokens: {usage.response_tokens}")
    print(f"Total tokens: {usage.total_tokens}")
    
    # Get all messages including tool calls
    messages = result.all_messages()
    for msg in messages:
        print(msg)
""")
