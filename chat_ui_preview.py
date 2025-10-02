"""
Visual test of the chat UI to verify layout and components
Run this to see what the chat tab looks like
"""

import gradio as gr

def mock_start_chat():
    return "abc-123-def-456", [], [], "Session started - 1 message"

def mock_send_message(session_id, message, history, *args):
    if not session_id:
        return history, [], "Error: No active session"
    if not message:
        return history, [], "Error: Empty message"
    
    # Simulate AI response
    response = f"This is a mock response to: '{message}'. In a real chat, the AI would search your documents and provide context-aware answers."
    history.append((message, response))
    return history, [], f"Messages: {len(history) * 2 + 1} | Results: 5"

def mock_end_chat(session_id):
    return "", [], [], "Session ended"

# Create the chat UI for preview
with gr.Blocks(title="Vector Chat Preview") as demo:
    gr.Markdown("# Chat Tab Preview\nThis is how the chat tab will look in the Vector web app")
    
    # Session management
    with gr.Row():
        session_id = gr.Textbox(
            label="Session ID",
            placeholder="Click 'Start New Chat' to begin...",
            interactive=False,
            scale=3
        )
        with gr.Column(scale=1):
            start_btn = gr.Button("🆕 Start New Chat", variant="primary")
            end_btn = gr.Button("🛑 End Chat", variant="secondary")
    
    # Chat interface
    chatbot = gr.Chatbot(
        label="Conversation",
        height=400,
        show_label=True,
        bubble_full_width=False
    )
    
    with gr.Row():
        message = gr.Textbox(
            label="Your Message",
            placeholder="Ask a question or continue the conversation...",
            scale=4,
            lines=2
        )
        send_btn = gr.Button("📤 Send", variant="primary", scale=1)
    
    with gr.Accordion("⚙️ Chat Settings", open=False):
        with gr.Row():
            response_length = gr.Radio(
                choices=["short", "medium", "long"],
                value="medium",
                label="Response Length",
                scale=1
            )
            search_type = gr.Radio(
                choices=["chunks", "artifacts", "both"],
                value="both",
                label="Search Type",
                info="chunks: text content, artifacts: images/tables, both: combined",
                scale=1
            )
            top_k = gr.Slider(
                minimum=5,
                maximum=30,
                value=12,
                step=1,
                label="Search Results per Turn",
                scale=1
            )
    
    # Thumbnails
    thumbnails = gr.Gallery(
        label="Related Document Pages (Last Response)",
        show_label=True,
        columns=4,
        rows=2,
        height="auto",
        allow_preview=True,
        show_share_button=False,
        interactive=False
    )
    
    # Session info
    with gr.Accordion("📊 Session Info", open=False):
        session_info = gr.Textbox(
            label="Session Details",
            lines=3,
            interactive=False,
            placeholder="Start a chat session to see details..."
        )
    
    # Connect events
    start_btn.click(
        fn=mock_start_chat,
        outputs=[session_id, chatbot, thumbnails, session_info]
    )
    
    send_btn.click(
        fn=lambda sid, msg, hist, rlen, stype, topk: mock_send_message(sid, msg, hist, rlen, stype, topk),
        inputs=[session_id, message, chatbot, response_length, search_type, top_k],
        outputs=[chatbot, thumbnails, session_info]
    ).then(
        lambda: "",
        outputs=message
    )
    
    message.submit(
        fn=lambda sid, msg, hist, rlen, stype, topk: mock_send_message(sid, msg, hist, rlen, stype, topk),
        inputs=[session_id, message, chatbot, response_length, search_type, top_k],
        outputs=[chatbot, thumbnails, session_info]
    ).then(
        lambda: "",
        outputs=message
    )
    
    end_btn.click(
        fn=mock_end_chat,
        inputs=session_id,
        outputs=[session_id, chatbot, thumbnails, session_info]
    )
    
    # Instructions
    gr.Markdown("""
    ## How to Use
    
    1. **Click "Start New Chat"** - A session ID will appear
    2. **Type a message** in the input box
    3. **Click "Send"** or press Enter
    4. **Ask follow-up questions** - The AI remembers the context
    5. **Adjust settings** in the accordion if needed
    6. **Click "End Chat"** when finished
    
    ## Try These Example Conversations
    
    ### Example 1: Research Query
    ```
    You: What are R-1 residential setback requirements?
    AI: [Provides detailed information about R-1 setbacks]
    You: How about for corner lots?
    AI: [Gives corner lot specific information, understanding context]
    You: What if there's a detached garage?
    AI: [Continues with garage-specific details]
    ```
    
    ### Example 2: Document Exploration
    ```
    You: Summarize the fire safety requirements
    AI: [Provides summary]
    You: Tell me more about sprinkler systems
    AI: [Detailed sprinkler info]
    You: Are there exceptions for existing buildings?
    AI: [Exception details, maintaining context]
    ```
    
    ## Features Demonstrated
    
    ✅ Multi-turn conversation with context awareness  
    ✅ Clean chat bubble interface  
    ✅ Session management (start/end)  
    ✅ Configurable settings  
    ✅ Auto-clear message after sending  
    ✅ Enter key support  
    ✅ Session info display  
    """)

if __name__ == "__main__":
    demo.launch(share=False)
