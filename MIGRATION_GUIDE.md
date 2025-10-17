# Quick Migration Guide: ResearchAgent → ChatService

## TL;DR

```python
# Before
from vector.agent import ResearchAgent
agent = ResearchAgent()

# After  
from vector.agent import ChatService
service = ChatService()
```

That's it! The API is identical.

## Why Migrate?

1. **Clear naming** - `ChatService` is what it actually does (not an "agent")
2. **Better architecture** - Separates orchestration from agent logic
3. **Future-proof** - `ResearchAgent` will be removed eventually

## Migration Checklist

### Step 1: Update Import

```python
# Old
from vector.agent import ResearchAgent

# New
from vector.agent import ChatService
```

### Step 2: Rename Variable (Optional)

```python
# Old
agent = ResearchAgent()
session_id = agent.start_chat()
response = agent.chat(session_id, "question")

# New
service = ChatService()
session_id = service.start_chat()
response = service.chat(session_id, "question")
```

### Step 3: Test

Everything should work exactly the same. If not, report an issue!

## Same API, New Name

All methods are identical:

| Method | Works the Same |
|--------|---------------|
| `start_chat()` | ✅ |
| `get_session()` | ✅ |
| `end_chat()` | ✅ |
| `chat()` | ✅ |
| `get_model_info()` | ✅ |
| `get_collection_info()` | ✅ |

## Example Migrations

### Example 1: Simple Chat

**Before:**
```python
from vector.agent import ResearchAgent

agent = ResearchAgent()
session_id = agent.start_chat()
response = agent.chat(session_id, "What are parking rules?")
print(response['assistant'])
agent.end_chat(session_id)
```

**After:**
```python
from vector.agent import ChatService

service = ChatService()
session_id = service.start_chat()
response = service.chat(session_id, "What are parking rules?")
print(response['assistant'])
service.end_chat(session_id)
```

### Example 2: With Configuration

**Before:**
```python
from vector.agent import ResearchAgent
from vector.config import Config

config = Config()
agent = ResearchAgent(
    config=config,
    chunks_collection="my_chunks",
    use_pydantic_ai=True
)
```

**After:**
```python
from vector.agent import ChatService
from vector.config import Config

config = Config()
service = ChatService(
    config=config,
    chunks_collection="my_chunks",
    use_pydantic_ai=True
)
```

### Example 3: Using Tools

**Before:**
```python
agent = ResearchAgent(use_pydantic_ai=True)
response = agent.chat(
    session_id=session_id,
    user_message="question",
    use_tools=True  # Enable PydanticAI agents
)
```

**After:**
```python
service = ChatService(use_pydantic_ai=True)
response = service.chat(
    session_id=session_id,
    user_message="question",
    use_tools=True  # Enable PydanticAI agents
)
```

## Common Questions

### Q: Do I have to migrate now?

**A:** No, but you should. `ResearchAgent` will show a deprecation warning and will be removed in a future version.

### Q: Will my code break?

**A:** No! Full backward compatibility is maintained.

### Q: What if I want to use PydanticAI agents directly?

**A:** You can!

```python
from vector.agent import PydanticResearchAgent
from vector.agent.deps import AgentDeps

# Setup deps...
agent = PydanticResearchAgent(deps)
```

### Q: Can I still use the classic pipeline?

**A:** Yes! Set `use_tools=False` in the `chat()` method (it's the default).

### Q: What about tests?

**A:** Same migration - just update imports:

```python
# Old
from vector.agent import ResearchAgent

# New  
from vector.agent import ChatService
```

## Search and Replace

If you have many files to update:

**VS Code:**
1. Press `Ctrl+Shift+H` (Find and Replace in Files)
2. Find: `from vector.agent import ResearchAgent`
3. Replace: `from vector.agent import ChatService`
4. Find: `ResearchAgent(`
5. Replace: `ChatService(`

**Command Line:**
```bash
# macOS/Linux
grep -rl "ResearchAgent" . | xargs sed -i '' 's/ResearchAgent/ChatService/g'

# Windows (PowerShell)
Get-ChildItem -Recurse -File | ForEach-Object {
    (Get-Content $_.FullName) -replace 'ResearchAgent', 'ChatService' | Set-Content $_.FullName
}
```

## Need Help?

- Check `CHAT_SERVICE_REFACTOR.md` for detailed architecture explanation
- See `vector/agent/docs/PYDANTIC_AI_MIGRATION.md` for PydanticAI details
- Open an issue if something doesn't work

## Timeline

- **Now**: `ResearchAgent` deprecated but functional (with warning)
- **Next Major Release**: `ResearchAgent` will be removed
- **Recommendation**: Migrate as soon as convenient

---

**Bottom Line:** Change the import and variable name. Everything else stays the same. Easy! 🎉
