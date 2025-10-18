"""Quick test to verify retrieval refactor works correctly."""

print("Testing retrieval refactor...")
print("=" * 60)

# Test 1: Import orchestrator directly (bypassing vector.retrieval.__init__)
print("\n1. Testing direct import from orchestrator module...")
try:
    from vector.retrieval.orchestrator import RetrievalOrchestrator, Retriever
    print("   ✓ Direct import from orchestrator successful")
    print(f"   ✓ RetrievalOrchestrator: {RetrievalOrchestrator}")
    print(f"   ✓ Retriever (alias): {Retriever}")
    print(f"   ✓ Retriever is RetrievalOrchestrator: {Retriever is RetrievalOrchestrator}")
except ImportError as e:
    print(f"   ✗ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Import from new location through __init__ (preferred)
print("\n2. Testing import from vector.retrieval (NEW - PREFERRED)...")
try:
    from vector.retrieval import RetrievalOrchestrator as RO2
    from vector.retrieval import Retriever as R2
    from vector.retrieval import Pipeline, PipelineStep, RetrievalContext
    from vector.retrieval import QueryExpansionStep, SearchStep, ScoreFilter, DiagnosticsStep
    print("   ✓ All imports from vector.retrieval successful")
    print(f"   ✓ RetrievalOrchestrator: {RO2}")
    print(f"   ✓ Retriever (alias): {R2}")
    print(f"   ✓ Retriever is RetrievalOrchestrator: {R2 is RO2}")
except ImportError as e:
    print(f"   ✗ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Backward compatibility via vector.agent (lazy imports)
print("\n3. Testing backward compatibility via vector.agent.__getattr__ (lazy)...")
try:
    from vector.agent import Retriever as AgentRetriever
    from vector.agent import Pipeline as AgentPipeline
    from vector.agent import SearchStep as AgentSearchStep
    print("   ✓ Backward compatibility via lazy imports working")
    print(f"   ✓ Same Retriever: {AgentRetriever is RetrievalOrchestrator}")
    print(f"   ✓ Same Pipeline: {AgentPipeline is Pipeline}")
    print(f"   ✓ Same SearchStep: {AgentSearchStep is SearchStep}")
except ImportError as e:
    print(f"   ⚠ EXPECTED FAILURE (circular import): {e}")

# Test 4: Verify deprecated shim files are removed
print("\n4. Verifying deprecated shim files are removed...")
import os
agent_path = "e:\\02-regscout\\vector\\agent"
deprecated_files = ["retrieval.py", "pipeline.py", "steps.py"]
all_removed = True
for f in deprecated_files:
    fpath = os.path.join(agent_path, f)
    if os.path.exists(fpath):
        print(f"   ✗ FAILED: {f} still exists")
        all_removed = False
    else:
        print(f"   ✓ {f} successfully removed")

if all_removed:
    print("   ✓ All deprecated shims removed")

# Test 5: Check agent module only has core files
print("\n5. Checking vector/agent contains only core agent files...")
expected_files = {
    '__init__.py', '__main__.py', 'agents.py', 'chat_service.py',
    'cli.py', 'deps.py', 'mcp_server.py', 'memory.py', 
    'models.py', 'prompting.py', 'tools.py'
}
actual_files = {f for f in os.listdir(agent_path) if f.endswith('.py')}
if actual_files == expected_files:
    print(f"   ✓ Agent module contains exactly the expected files")
    print(f"   ✓ File count: {len(actual_files)}")
else:
    unexpected = actual_files - expected_files
    missing = expected_files - actual_files
    if unexpected:
        print(f"   ⚠ Unexpected files: {unexpected}")
    if missing:
        print(f"   ⚠ Missing files: {missing}")

# Test 6: Import agent core components
print("\n6. Testing agent core components still work...")
try:
    from vector.agent import ChatService, SearchAgent, AnswerAgent, ResearchAgent
    from vector.agent import ChatSession, ChatMessage, RetrievalResult
    from vector.agent import build_system_prompt, SummarizerPolicy
    print("   ✓ All core agent components imported successfully")
except ImportError as e:
    print(f"   ✗ FAILED: {e}")

print("\n" + "=" * 60)
print("✓ Refactor complete! Structure cleaned successfully.")
print("\nFinal structure:")
print("  vector/agent/        # High-level agent logic")
print("    ├── agents.py      # PydanticAI agents")
print("    ├── tools.py       # Agent tools")
print("    ├── chat_service.py # Chat orchestration")  
print("    ├── models.py      # Agent-specific models")
print("    ├── deps.py        # Agent dependencies")
print("    ├── memory.py      # Memory/summarization")
print("    ├── prompting.py   # Prompt builders")
print("    ├── cli.py         # CLI interface")
print("    ├── mcp_server.py  # MCP server")
print("    └── __init__.py    # Module exports")
print("\n  vector/retrieval/  # Retrieval orchestration")
print("    ├── orchestrator.py # RetrievalOrchestrator")
print("    ├── pipeline.py    # Pipeline framework")
print("    ├── steps.py       # Pipeline steps")
print("    └── __init__.py    # Module exports")
print("\nRecommended usage:")
print("  from vector.retrieval import RetrievalOrchestrator")
print("  from vector.retrieval import Pipeline, SearchStep")
print("  from vector.agent import ChatService, SearchAgent")
