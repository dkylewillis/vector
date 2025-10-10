# Metrics Display Fix

## Problem

After implementing the pipeline pattern for retrieval, metrics were no longer showing in the web interface. The chat would display "No metrics available" instead of the detailed token usage breakdown.

## Root Cause

The issue was in `retrieval.py` where we were converting `AggregatedUsageMetrics` (which contains the detailed breakdown by operation) into a simple `UsageMetrics` object, losing all the breakdown information.

**Before (broken):**
```python
# retrieval.py
aggregated = AggregatedUsageMetrics.from_operations(context.usage_metrics)
usage = UsageMetrics(  # ❌ Lost the breakdown!
    prompt_tokens=aggregated.total_prompt_tokens,
    completion_tokens=aggregated.total_completion_tokens,
    total_tokens=aggregated.total_tokens,
    latency_ms=aggregated.total_latency_ms
)
return retrieval_bundle, usage
```

This simplified `UsageMetrics` object didn't have the `operations` field needed for the breakdown display in the web UI.

## Solution

Return `AggregatedUsageMetrics` directly from `retrieval.retrieve()` instead of converting it to a simple `UsageMetrics` object.

### Changes Made

#### 1. `retrieval.py` - Return Type Fix
```python
# Return type changed from Tuple[RetrievalBundle, UsageMetrics] to:
def retrieve(...) -> Tuple[RetrievalBundle, AggregatedUsageMetrics]:
    # ...
    if context.usage_metrics:
        aggregated = AggregatedUsageMetrics.from_operations(context.usage_metrics)
        return retrieval_bundle, aggregated  # ✅ Preserve breakdown
    else:
        return retrieval_bundle, AggregatedUsageMetrics()
```

#### 2. `agent.py` - Handle AggregatedUsageMetrics

**No results case:**
```python
# expansion_metrics is already AggregatedUsageMetrics
return {
    "session_id": session_id,
    "assistant": assistant_response,
    "usage_metrics": expansion_metrics.model_dump()  # ✅ Direct use
}
```

**With results case:**
```python
# Combine expansion metrics with answer metrics
all_operations = list(expansion_metrics.operations) + [answer_metrics]
aggregated = AggregatedUsageMetrics.from_operations(all_operations)
return {
    "usage_metrics": aggregated.model_dump()  # ✅ Full breakdown
}
```

## How It Works Now

1. **Pipeline Steps** (in `steps.py`) add `UsageMetrics` to context with `operation` field set:
   ```python
   context.add_usage(UsageMetrics(
       prompt_tokens=100,
       completion_tokens=50,
       total_tokens=150,
       operation="search"  # ✅ Operation tagged
   ))
   ```

2. **Retriever** (in `retrieval.py`) aggregates and returns `AggregatedUsageMetrics`:
   ```python
   aggregated = AggregatedUsageMetrics.from_operations(context.usage_metrics)
   # aggregated.operations = [UsageMetrics(operation="search", ...)]
   return retrieval_bundle, aggregated
   ```

3. **Agent** (in `agent.py`) combines with answer metrics:
   ```python
   all_operations = list(expansion_metrics.operations) + [answer_metrics]
   # all_operations = [
   #   UsageMetrics(operation="search", ...),
   #   UsageMetrics(operation="answer", ...)
   # ]
   aggregated = AggregatedUsageMetrics.from_operations(all_operations)
   ```

4. **Web UI** (in `components.py`) displays the breakdown:
   ```python
   breakdown = usage_metrics.get('breakdown', [])
   for op_metrics in breakdown:
       operation = op_metrics.get('operation', 'unknown')
       # Display: 🔍 Query Expansion, 💬 Answer Generation
   ```

## Result

The web interface now correctly displays:

```
📊 Token Usage Metrics

Total Usage:
• Prompt tokens: 1,234
• Completion tokens: 567
• Total tokens: 1,801
• Models: gpt-4o-mini
• Total latency: 2,345.67ms (2.35s)

---
Breakdown by Operation:

🔍 Query Expansion:
• Model: gpt-4o-mini
• Prompt tokens: 234
• Completion tokens: 67
• Total: 301
• Latency: 345.67ms

💬 Answer Generation:
• Model: gpt-4o-mini
• Prompt tokens: 1,000
• Completion tokens: 500
• Total: 1,500
• Latency: 2,000.00ms
```

## Benefits

✅ **Full transparency** - Users can see exactly how tokens are used  
✅ **Cost tracking** - Breakdown shows search vs answer costs  
✅ **Performance insights** - Latency per operation  
✅ **Model visibility** - Which models are being used  
✅ **Pipeline compatible** - Works with the new pipeline architecture  

## Testing

To verify the fix works:

1. Start the web interface: `python -m vector.web`
2. Navigate to the Chat tab
3. Send a message
4. Check the "Usage Metrics & Model Breakdown" accordion
5. You should see detailed breakdown with operation types
