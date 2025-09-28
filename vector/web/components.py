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


def create_collection_selector(collections: List[str], default_collection: str, initial_documents: List[str] = None):
    """Create collection selector with document list."""
    if initial_documents is None:
        initial_documents = []
        
    with gr.Column():
        gr.Markdown("**Collection Selector**")
        collection_dropdown = gr.Dropdown(
            choices=collections,
            value=default_collection,
            label="Collection",
            interactive=True
        )
        refresh_btn = gr.Button("Refresh Collections", interactive=True)
        documents_checkboxgroup = gr.CheckboxGroup(
            choices=[],
            label="Documents",
            interactive=False
        )
    
    return collection_dropdown, refresh_btn, documents_checkboxgroup


def create_delete_tab():
    """Create delete tab components."""
    with gr.TabItem("🗑️ Delete", elem_id="delete_tab"):
        gr.Markdown("### Delete Documents")
        gr.Markdown("""
        **⚠️ Warning:** This will permanently delete documents from the system and all collections.
        
        **Instructions:**
        1. Select documents from the main document list on the left
        2. Check the confirmation box below
        3. Click 'Delete Selected Documents'
        """)
        
        delete_documents_list = gr.CheckboxGroup(
            label="Documents to Delete",
            choices=[],
            interactive=False
        )
        
        confirm_delete_checkbox = gr.Checkbox(
            label="I understand this action cannot be undone",
            value=False,
            interactive=True
        )
        
        delete_selected_btn = gr.Button("Delete Selected Documents", interactive=True)
        delete_output = gr.Textbox(
            label="Delete Status",
            value="",
            interactive=False
        )
    
    return {
        'delete_documents_list': delete_documents_list,
        'confirm_delete_checkbox': confirm_delete_checkbox,
        'delete_selected_btn': delete_selected_btn,
        'delete_output': delete_output
    }


def create_search_tab():
    """Create the Search & Ask tab."""
    components = {}
    
    with gr.TabItem("🔍 Search & Ask"):
        # Sub-tabs for Ask AI and Search
        with gr.Tabs():
            # Ask AI Tab
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
                with gr.Row():
                    components['search_query'] = gr.Textbox(
                        label="Search Query",
                        placeholder="Enter search terms...",
                        scale=3
                    )
                    components['search_btn'] = gr.Button("Search", variant="primary", scale=1, 
                                         elem_classes="vector-button-1")
                
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
            label="Select Documents (.pdf, .docx)",
            file_types=[".pdf", ".docx"],
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
            components['metadata_btn'] = gr.Button("📋 Get Metadata Summary", variant="secondary")
        
        components['info_output'] = gr.Textbox(
            label="Collection Information",
            lines=12,
            interactive=False
        )
        
        components['metadata_summary'] = gr.Textbox(
            label="Metadata Summary",
            lines=20,
            interactive=False
        )
    
    return components


def create_document_management_tab():
    """Create the Document Management tab."""
    components = {}
    
    with gr.TabItem("📄 Document Management"):
        with gr.Tabs():
            # Sub-tab: All Documents
            with gr.TabItem("📋 All Documents"):
                with gr.Row():
                    components['refresh_docs_btn'] = gr.Button("🔄 Refresh Documents", variant="secondary")
                    components['view_details_btn'] = gr.Button("🔍 View Details", variant="primary")
                
                components['all_documents_list'] = gr.CheckboxGroup(
                    label="Available Documents",
                    choices=[],
                    interactive=True,
                    elem_classes="document-checkbox-group"
                )
                
                components['document_details_output'] = gr.Textbox(
                    label="Document Details",
                    lines=10,
                    interactive=False,
                    placeholder="Select documents and click 'View Details' to see information..."
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

    
    return components





