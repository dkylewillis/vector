# Vector Web Interface - Placeholder Mode

⚠️ **This web interface is currently in placeholder mode during core refactoring.**

## Current Status

All web functionality has been temporarily disabled while the core modules are being refactored. The interface will still launch and display the UI components, but all operations will return placeholder messages.

## What's Available

- ✅ UI components (all tabs and forms)
- ✅ Basic Gradio interface structure  
- ❌ Search functionality
- ❌ AI question answering
- ❌ Document upload/processing
- ❌ Collection management
- ❌ Document management

## Running the Placeholder

```bash
# Option 1: Run as module
python -m vector.web

# Option 2: Import and run
python -c "from vector.web import main; main()"
```

## When Will It Be Restored?

The web interface will be restored once the core refactoring is complete. The placeholder maintains the same component structure and API interfaces, so it can be quickly re-enabled by:

1. Replacing the placeholder service implementations
2. Re-enabling the event handlers
3. Restoring the proper Config imports

## Files in Placeholder Mode

- `components.py` - UI components (disabled interactions)
- `handlers.py` - Event handlers (return placeholder messages)
- `service.py` - Web service layer (all methods return placeholders)
- `main.py` - Main app (removed core dependencies)
- `__init__.py` - Module exports (simplified)
- `__main__.py` - Entry point (with warning message)

The original implementations have been completely replaced to avoid any dependency on the core modules during refactoring.