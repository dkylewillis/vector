# Chat Feature - Visual Layout

## Tab Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  🔍 Search & Ask Tab                                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┬─────────────┬───────────────────┐                 │
│  │ 💬 Chat │ 🤖 Ask AI   │ 🔍 Search Docs    │                 │
│  └─────────┴─────────────┴───────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

## Chat Tab Layout (NEW!)

```
┌─────────────────────────────────────────────────────────────────┐
│  💬 Chat                                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Multi-turn Conversation                                        │
│  Have a back-and-forth conversation with AI...                  │
│                                                                  │
│  ┌──────────────────────────────────────┬───────────────────┐  │
│  │ Session ID: abc-123-def-456-789      │ [🆕 Start Chat] │  │
│  │                                      │ [🛑 End Chat]   │  │
│  └──────────────────────────────────────┴───────────────────┘  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Conversation                                            │  │
│  │                                                          │  │
│  │  ┌──────────────────────────────────────────┐          │  │
│  │  │ What are setback requirements?           │  👤      │  │
│  │  └──────────────────────────────────────────┘          │  │
│  │                                                          │  │
│  │       ┌──────────────────────────────────────┐         │  │
│  │  🤖   │ R-1 residential setbacks require...  │         │  │
│  │       └──────────────────────────────────────┘         │  │
│  │                                                          │  │
│  │  ┌──────────────────────────────────────────┐          │  │
│  │  │ How about corner lots?                   │  👤      │  │
│  │  └──────────────────────────────────────────┘          │  │
│  │                                                          │  │
│  │       ┌──────────────────────────────────────┐         │  │
│  │  🤖   │ For corner lots, the setbacks are... │         │  │
│  │       └──────────────────────────────────────┘         │  │
│  │                                                          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────┬───────────────────┐  │
│  │ Your Message:                        │                   │  │
│  │ [Type your question here...]         │  [📤 Send]       │  │
│  └──────────────────────────────────────┴───────────────────┘  │
│                                                                  │
│  ▼ ⚙️ Chat Settings                                            │
│  ├─ Response Length:  ○ short  ● medium  ○ long              │
│  ├─ Search Type:      ○ chunks ○ artifacts ● both            │
│  └─ Results per Turn: [====|====] 12                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Related Document Pages (Last Response)                  │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                   │  │
│  │  │ Page │ │ Page │ │ Page │ │ Page │                   │  │
│  │  │  1   │ │  2   │ │  3   │ │  4   │                   │  │
│  │  └──────┘ └──────┘ └──────┘ └──────┘                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ▼ 📊 Session Info                                             │
│  │  Messages: 5 | Results used: 8                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Comparison: Chat vs Ask AI

### Chat Tab (Multi-turn)
```
┌────────────────────────────────────────┐
│  💬 CHAT                               │
├────────────────────────────────────────┤
│  Session: abc-123                      │
│  ┌─────────────────────────────────┐  │
│  │ 👤: Question 1                  │  │
│  │ 🤖: Answer 1                    │  │
│  │ 👤: Follow-up (context aware)   │  │
│  │ 🤖: Answer 2 (knows history)    │  │
│  │ 👤: Another follow-up           │  │
│  │ 🤖: Answer 3 (full context)     │  │
│  └─────────────────────────────────┘  │
│  [Type next message...]                │
│  ✅ Remembers conversation             │
│  ✅ Natural follow-ups                 │
│  ✅ Session management                 │
└────────────────────────────────────────┘
```

### Ask AI Tab (Single-turn)
```
┌────────────────────────────────────────┐
│  🤖 ASK AI                             │
├────────────────────────────────────────┤
│  [Type your question...]               │
│  [Ask AI]                              │
│                                        │
│  Response:                             │
│  [AI answer appears here]              │
│                                        │
│  ❌ No memory between questions        │
│  ❌ Must repeat context each time      │
│  ✅ Good for single queries            │
└────────────────────────────────────────┘
```

## User Flow Diagram

```
START
  │
  ├─> Click "🆕 Start New Chat"
  │     │
  │     └─> Session ID appears
  │     └─> Chat history cleared
  │     └─> Ready to chat
  │
  ├─> Type message
  │     │
  │     └─> Click "📤 Send" or press Enter
  │     └─> Message appears in chat
  │     └─> AI searches documents
  │     └─> AI generates context-aware response
  │     └─> Response appears in chat
  │     └─> Thumbnails update
  │     └─> Message input clears
  │
  ├─> Type follow-up question
  │     │
  │     └─> Repeats above flow
  │     └─> AI remembers previous messages
  │     └─> Response is contextually aware
  │
  ├─> (Optional) Adjust Settings
  │     │
  │     └─> Change response length
  │     └─> Change search type
  │     └─> Adjust top-k results
  │
  ├─> Continue conversation...
  │
  └─> Click "🛑 End Chat"
        │
        └─> Session cleared
        └─> Chat history cleared
        └─> Ready for new session
```

## Example Screen States

### State 1: Initial (No Session)
```
┌──────────────────────────────────────┐
│ Session ID: [Click Start New Chat]  │
│ [🆕 Start] [🛑 End]                 │
├──────────────────────────────────────┤
│                                      │
│  (Empty chat area)                   │
│                                      │
└──────────────────────────────────────┘
```

### State 2: Session Active, No Messages
```
┌──────────────────────────────────────┐
│ Session ID: abc-123-def-456          │
│ [🆕 Start] [🛑 End]                 │
├──────────────────────────────────────┤
│  Chat ready - ask your first         │
│  question below!                     │
│                                      │
└──────────────────────────────────────┘
```

### State 3: Active Conversation
```
┌──────────────────────────────────────┐
│ Session ID: abc-123-def-456          │
│ [🆕 Start] [🛑 End]                 │
├──────────────────────────────────────┤
│  👤: What are setbacks?              │
│  🤖: R-1 residential setbacks...     │
│  👤: Corner lots?                    │
│  🤖: For corner lots...              │
└──────────────────────────────────────┘
│ [Type message...] [📤]               │
│ Session: Messages: 5 | Results: 8   │
└──────────────────────────────────────┘
```

## Component Hierarchy

```
create_search_tab()
  └── TabItem: "🔍 Search & Ask"
      └── Tabs()
          ├── TabItem: "💬 Chat" ← NEW!
          │   ├── Markdown (instructions)
          │   ├── Row (session management)
          │   │   ├── Textbox (session_id)
          │   │   └── Column
          │   │       ├── Button (start_chat_btn)
          │   │       └── Button (end_chat_btn)
          │   ├── Chatbot (chat_history)
          │   ├── Row (message input)
          │   │   ├── Textbox (chat_message)
          │   │   └── Button (send_chat_btn)
          │   ├── Accordion ("Chat Settings")
          │   │   └── Row
          │   │       ├── Radio (response_length)
          │   │       ├── Radio (search_type)
          │   │       └── Slider (top_k)
          │   ├── Gallery (thumbnails)
          │   └── Accordion ("Session Info")
          │       └── Textbox (session_info)
          │
          ├── TabItem: "🤖 Ask AI" (existing)
          └── TabItem: "🔍 Search Documents" (existing)
```

## Event Wiring

```
start_chat_btn.click
  → start_chat_session()
    → Returns: session_id, [], [], "Session started"
    → Updates: all chat components

send_chat_btn.click / chat_message.submit
  → send_chat_message()
    → Inputs: session_id, message, history, settings, docs
    → Returns: updated_history, thumbnails, session_info
    → Then: clears message input

end_chat_btn.click
  → end_chat_session()
    → Returns: "", [], [], "Session ended"
    → Clears: all chat components
```

---

This visual guide shows the exact layout and flow of the new chat feature!
