"""UI components for the Vector Gradio interface."""

import gradio as gr
from typing import List


def create_header():
    """Create the main header."""
    return gr.HTML("""
        <div style="text-align: center; padding: 20px;">
            <h1>Vector - Document Search & AI</h1>
            <p>Search documents and ask questions using AI-powered analysis</p>
        </div>
        """)


def create_search_tab():
    """Create the Search & Ask tab."""
    components = {}
    
    with gr.TabItem("🔍 Search & Ask"):
        # Sub-tabs for Ask AI, Chat, and Search
        with gr.Tabs():
            # Chat Tab (Multi-turn conversation)
            with gr.TabItem("💬 Chat"):
                
                # Chat interface
                components['chat_history'] = gr.Chatbot(
                    label="Chatbot",
                    height=450,
                    show_label=True,
                    bubble_full_width=False,
                    type='messages'
                )
                
                # Message input and settings button row
                with gr.Row():
                    components['chat_message'] = gr.Textbox(
                        label="Your Message",
                        placeholder="Ask me anything about your documents...",
                        lines=1,
                        show_label=False,
                        submit_btn=True,
                        stop_btn=True,
                        scale=20
                    )
                    components['chat_settings_btn'] = gr.Button(
                        value="⚙️",
                        variant="secondary",
                        scale=1,
                        min_width=50,
                        elem_classes="settings-button"
                    )
                
                # Chat Settings Dialog (hidden by default)
                with gr.Group(visible=False) as components['chat_settings_dialog']:
                    gr.Markdown("### ⚙️ Chat Settings")
                    with gr.Row():
                        components['chat_response_length'] = gr.Radio(
                            choices=["short", "medium", "long"],
                            value="medium",
                            label="Response Length",
                            scale=1
                        )
                        components['chat_search_type'] = gr.Radio(
                            choices=["chunks", "artifacts", "both"],
                            value="chunks",
                            label="Search Type",
                            info="chunks: text content, artifacts: images/tables, both: combined",
                            scale=1
                        )
                        components['chat_top_k'] = gr.Slider(
                            minimum=5,
                            maximum=30,
                            value=12,
                            step=1,
                            label="Search Results per Turn",
                            scale=1
                        )
                    with gr.Row():
                        components['chat_settings_close_btn'] = gr.Button("Close", variant="primary")
                
                # Chat thumbnails
                components['chat_thumbnails'] = gr.Gallery(
                    label="Related Document Pages (Last Response)",
                    show_label=True,
                    elem_id="chat_thumbnails",
                    columns=4,
                    rows=2,
                    height="auto",
                    allow_preview=True,
                    show_share_button=False,
                    interactive=False
                )
                
                # Session info
                with gr.Accordion("📊 Session Info", open=False):
                    components['chat_session_info'] = gr.Textbox(
                        label="Session Details",
                        lines=3,
                        interactive=False,
                        placeholder="Start a chat session to see session ID and details..."
                    )
            
            # Ask AI Tab (Single-turn Q&A)
            with gr.TabItem("🤖 Ask AI"):
                with gr.Row():
                    components['ask_query'] = gr.Textbox(
                        label="Question",
                        placeholder="Ask a question about your documents...",
                        scale=3
                    )
                    components['ask_btn'] = gr.Button("Ask AI", variant="primary", scale=1, 
                                      elem_classes="vector-button-1")

                with gr.Row():
                    components['response_length'] = gr.Radio(
                        choices=["short", "medium", "long"],
                        value="medium",
                        label="Response Length",
                        scale=1
                    )
                    components['ask_search_type'] = gr.Radio(
                        choices=["chunks", "artifacts", "both"],
                        value="chunks",
                        label="Search Type",
                        info="chunks: text content, artifacts: images/tables, both: combined",
                        scale=1
                    )
                
                components['ai_response'] = gr.Textbox(
                    label="AI Response",
                    lines=8,
                    interactive=False
                )
                
                # Add thumbnail gallery under AI response
                components['ai_thumbnails'] = gr.Gallery(
                    label="Related Document Pages",
                    show_label=True,
                    elem_id="ai_thumbnails",
                    columns=4,
                    rows=2,
                    height="auto",
                    allow_preview=True,
                    show_share_button=False,
                    interactive=False
                )
            
            # Search Documents Tab
            with gr.TabItem("🔍 Search Documents"):
                components['search_query'] = gr.Textbox(
                    label="Search Query",
                    placeholder="Enter search terms...",
                    submit_btn=True
                )
                
                with gr.Row():
                    components['num_results'] = gr.Slider(
                        minimum=1, maximum=20, value=5, step=1,
                        label="Number of Results", scale=1
                    )
                    components['search_search_type'] = gr.Radio(
                        choices=["chunks", "artifacts", "both"],
                        value="both",
                        label="Search Type",
                        info="chunks: text content, artifacts: images/tables, both: combined",
                        scale=1
                    )
                
                components['search_results'] = gr.Textbox(
                    label="Search Results",
                    lines=10,
                    interactive=False
                )
                
                # Add thumbnail gallery under search results
                components['search_thumbnails'] = gr.Gallery(
                    label="Related Document Pages",
                    show_label=True,
                    elem_id="search_thumbnails",
                    columns=4,
                    rows=2,
                    height="auto",
                    allow_preview=True,
                    show_share_button=False,
                    interactive=False
                )
    
    return components


def create_upload_tab():
    """Create the Upload Documents tab."""
    components = {}
    
    with gr.TabItem("📁 Upload Documents"):
        components['file_upload'] = gr.Files(
            label="Select Documents (.pdf, .docx, .json)",
            file_types=[".pdf", ".docx", ".json"],
            file_count="multiple"
        )
        
        gr.Markdown("### ⚙️ Processing Options")
        with gr.Row():
            components['upload_tags_input'] = gr.Textbox(
                label="Add Tags",
                placeholder="Enter tags separated by commas (e.g., important, manual, checklist)",
                info="Tags will be added to uploaded documents",
                scale=2
            )
        
        with gr.Row():
            components['process_btn'] = gr.Button("📚 Process Documents", variant="primary")
        
        components['processing_output'] = gr.Textbox(
            label="Processing Log",
            lines=15,
            interactive=False
        )
    
    return components


def create_info_tab():
    """Create the Collection Info tab."""
    components = {}
    
    with gr.TabItem("📊 Collection Info"):
        with gr.Row():
            components['info_btn'] = gr.Button("📊 Get Collection Info", variant="primary")
        
        components['info_output'] = gr.Textbox(
            label="Collection Information",
            lines=12,
            interactive=False
        )
        
    
    return components


def create_document_management_tab():
    """Create the Document Management tab."""
    components = {}
    
    with gr.TabItem("📄 Document Management"):
        with gr.Tabs():
            # Sub-tab: Document Details
            with gr.TabItem("📋 Document Details"):
                gr.Markdown("### Document Details")
                gr.Markdown("Select documents from the main document list on the left, then click 'View Details' to see information.")
                
                components['view_details_btn'] = gr.Button("🔍 View Details", variant="primary")
                
                components['document_details_output'] = gr.Textbox(
                    label="Document Details",
                    lines=10,
                    interactive=False,
                    placeholder="Select documents from the left panel and click 'View Details' to see information..."
                )
            
            # Sub-tab: Rename Document
            with gr.TabItem("✏️ Rename Document"):
                gr.Markdown("### Rename Document")
                gr.Markdown("""
                **Instructions:**
                1. Select a single document from the main document list on the left
                2. Enter a new name below (without extension)
                3. Click 'Rename Document'
                
                **Note:** The system will automatically ensure the new name is unique by adding a counter if needed.
                """)
                
                with gr.Row():
                    components['rename_new_name'] = gr.Textbox(
                        label="New Document Name",
                        placeholder="Enter new name (e.g., 'Updated Report')",
                        scale=3
                    )
                    components['rename_btn'] = gr.Button("✏️ Rename", variant="primary", scale=1)
                
                components['rename_output'] = gr.Textbox(
                    label="Rename Status",
                    lines=4,
                    interactive=False,
                    placeholder="Select a single document and enter a new name above..."
                )
            
            # Sub-tab: Manage Tags
            with gr.TabItem("🏷️ Manage Tags"):
                gr.Markdown("### Document Tag Management")
                gr.Markdown("Select documents from the left panel, then add or remove tags below.")
                
                with gr.Row():
                    with gr.Column(scale=2):
                        components['add_tags_input'] = gr.Textbox(
                            label="Add Tags",
                            placeholder="Enter tags separated by commas (e.g., important, manual, checklist)",
                            info="Tags will be added to all selected documents"
                        )
                    with gr.Column(scale=1):
                        components['add_tags_btn'] = gr.Button("➕ Add Tags", variant="primary")
                
                with gr.Row():
                    with gr.Column(scale=2):
                        components['remove_tags_input'] = gr.Textbox(
                            label="Remove Tags",
                            placeholder="Enter tags to remove, separated by commas",
                            info="Tags will be removed from all selected documents"
                        )
                    with gr.Column(scale=1):
                        components['remove_tags_btn'] = gr.Button("➖ Remove Tags", variant="secondary")
                
                components['tag_management_output'] = gr.Textbox(
                    label="Tag Management Log",
                    lines=8,
                    interactive=False,
                    placeholder="Select documents and add/remove tags above to see results..."
                )
                
                # Show current tags for selected documents
                components['current_tags_display'] = gr.Textbox(
                    label="Current Tags for Selected Documents",
                    lines=3,
                    interactive=False,
                    placeholder="Select documents to view their current tags..."
                )
            
            # Sub-tab: Delete Documents
            with gr.TabItem("🗑️ Delete Documents"):
                gr.Markdown("### Delete Documents")
                gr.Markdown("""
                **⚠️ Warning:** This will permanently delete documents from the system and all collections.
                
                **Instructions:**
                1. Select documents from the main document list on the left
                2. Check the confirmation box below
                3. Click 'Delete Selected Documents'
                """)
                
                components['confirm_delete_checkbox'] = gr.Checkbox(
                    label="I understand this action cannot be undone",
                    value=False,
                    interactive=True
                )
                
                components['delete_selected_btn'] = gr.Button("Delete Selected Documents", variant="primary")
                components['delete_output'] = gr.Textbox(
                    label="Delete Status",
                    lines=6,
                    interactive=False,
                    placeholder="Select documents from the left panel, confirm deletion, and click the delete button..."
                )

    
    return components