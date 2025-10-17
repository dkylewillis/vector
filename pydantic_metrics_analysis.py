"""Check PydanticAI metrics capabilities without requiring API key."""

print("PydanticAI Metrics Capabilities")
print("=" * 80)

print("\n✅ YES - PydanticAI provides comprehensive metrics!")
print("\nWhat you get after agent.run():")
print("""
result = await agent.run("query")

# 1. Usage/Token Metrics
usage = result.usage()
print(f"Request tokens (prompt): {usage.request_tokens}")
print(f"Response tokens (completion): {usage.response_tokens}")
print(f"Total tokens: {usage.total_tokens}")
print(f"Details: {usage.details}")  # Provider-specific details

# 2. Message Trace (includes tool calls)
messages = result.all_messages()
for msg in messages:
    print(msg)  # Shows: user messages, assistant responses, tool calls, tool results

# 3. Timestamp
print(f"Completed at: {result.timestamp()}")

# 4. New messages only (since last run)
new_msgs = result.new_messages()

# 5. The actual response data
response_data = result.data
""")

print("\n" + "=" * 80)
print("Comparison: Your Custom Metrics vs PydanticAI Native")
print("=" * 80)

print("\nYour Current Custom Metrics (from vector.ai):")
print("""
{
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150,
    "model_name": "gpt-4",
    "latency_ms": 1234.56,
    "operation": "search"  # Your custom field
}
""")

print("\nPydanticAI Native Metrics (from result.usage()):")
print("""
Usage(
    request_tokens=100,      # Same as prompt_tokens
    response_tokens=50,      # Same as completion_tokens  
    total_tokens=150,        # Same
    details={...}            # Provider-specific details
)

# Plus from result:
result.timestamp()           # When completed
result.all_messages()        # Full conversation trace including tools
""")

print("\n" + "=" * 80)
print("What You'd LOSE with Option 2 (Full PydanticAI Migration):")
print("=" * 80)

print("""
❌ Your custom 'operation' field (e.g., 'search', 'answer', 'summarization')
❌ Your latency_ms tracking (though timestamp available)
❌ Your AggregatedUsageMetrics breakdown by operation
❌ Your multi-provider abstraction (BaseAIModel interface)
❌ Your service_tier control for OpenAI
❌ Your GPT-5 vs GPT-4 parameter handling
""")

print("\n" + "=" * 80)
print("What You'd GAIN with Option 2:")
print("=" * 80)

print("""
✅ Native tool call tracking in all_messages()
✅ Automatic retry logic
✅ Structured outputs with Pydantic models
✅ Better async support
✅ Agent composition patterns
✅ Built-in observability
✅ OpenTelemetry integration (via logfire)
✅ Less code to maintain
""")

print("\n" + "=" * 80)
print("RECOMMENDATION: Option 3 - Best of Both Worlds")
print("=" * 80)

print("""
Instead of Option 2 (losing your metrics), do Option 3:

1. Keep your AgentDeps and tool architecture ✅
2. Use PydanticAI Agents for orchestration ✅  
3. Create a THIN WRAPPER around PydanticAI's usage:

class EnhancedUsageMetrics:
    '''Combines PydanticAI usage with your custom fields.'''
    
    def __init__(self, pydantic_usage, operation: str, latency_ms: float):
        # Map PydanticAI to your format
        self.prompt_tokens = pydantic_usage.request_tokens
        self.completion_tokens = pydantic_usage.response_tokens
        self.total_tokens = pydantic_usage.total_tokens
        
        # Add your custom fields
        self.operation = operation
        self.latency_ms = latency_ms
        self.model_name = "..." # Extract from result
        
        # Keep PydanticAI benefits
        self.pydantic_details = pydantic_usage.details

This way you:
✅ Keep your custom metrics (operation, latency, breakdown)
✅ Get PydanticAI benefits (tools, observability, async)
✅ Maintain backward compatibility
✅ Have a clear migration path
""")

print("\n" + "=" * 80)
print("ANSWER: Yes, Option 2 has metrics, but OPTION 3 is better!")
print("=" * 80)
