"""UI components for the Vector Gradio interface."""

import gradio as gr
from typing import List


def create_header():
    """Create the main header."""
    return gr.HTML("""
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet">
        <div style="text-align: center; padding: 20px;">
            <h1>
            <span style="color:#3b82f6; font-size:50px; position:relative; top:4px;">●</span>
            Vector
            </h1>
            <p>AI-Powered Document Processing & Search</p>
        </div>
        """)


def create_collection_selector(collections: List[str], default_collection: str, initial_documents: List[str] = None):
    """Create collection selector with document list."""
    if initial_documents is None:
        initial_documents = []
        
    with gr.Column(elem_id="dropdown_column"):
        with gr.Row(elem_id="collection_selector_top"):
            gr.Markdown("**Collection**", elem_id="bottom_md")
            refresh_btn = gr.Button("Refresh Collections", size="sm", scale=1, 
                                  elem_classes="icon-btn", elem_id="refresh_btn")
        with gr.Row():
            collection_dropdown = gr.Dropdown(
                choices=collections,
                value=default_collection,
                show_label=False,
                scale=3
            )
        
        # Documents section
        with gr.Row():
            with gr.Column():
                gr.Markdown("**Documents in Collection**", elem_classes="filter_label")
                documents_checkboxgroup = gr.CheckboxGroup(
                    choices=initial_documents,
                    label="",
                    show_label=False,
                    interactive=True,
                    elem_classes="vector-checkbox-group"
                )
    
    return collection_dropdown, refresh_btn, documents_checkboxgroup


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
                        label="Response Length"
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
            components['source_dropdown'] = gr.Dropdown(
                choices=["auto", "ordinances", "manuals", "checklists", "other"],
                value="auto",
                label="Source Category",
                info="Choose source or 'auto' to detect from folder name",
                scale=2
            )
            components['force_reprocess'] = gr.Checkbox(
                label="Force Reprocess",
                value=False,
                scale=1
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
        
        components['collection_info'] = gr.Textbox(
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


def create_management_tab():
    """Create the Collection Management tab."""
    components = {}
    
    with gr.TabItem("📚 Collection Management"):
        with gr.Tabs():
            # Sub-tab: List Collections
            with gr.TabItem("📋 List Collections"):
                with gr.Row():
                    components['list_collections_btn'] = gr.Button("📋 List All Collections", variant="primary")
                
                components['collections_list'] = gr.Textbox(
                    label="Collections",
                    lines=12,
                    interactive=False,
                    placeholder="Click 'List All Collections' to see available collections..."
                )
            
            # Sub-tab: Create Collection
            with gr.TabItem("➕ Create Collection"):
                gr.Markdown("### Create New Collection")
                
                components['create_display_name'] = gr.Textbox(
                    label="Display Name",
                    placeholder="Enter a friendly name for the collection...",
                )
                
                components['create_description'] = gr.Textbox(
                    label="Description (Optional)",
                    placeholder="Enter a description for the collection...",
                    lines=2
                )
                
                with gr.Row():
                    components['create_collection_btn'] = gr.Button("➕ Create Collection", variant="primary")
                
                components['create_output'] = gr.Textbox(
                    label="Creation Result",
                    lines=4,
                    interactive=False,
                    placeholder="Collection creation results will appear here..."
                )
            
            # Sub-tab: Rename Collection
            with gr.TabItem("✏️ Rename Collection"):
                gr.Markdown("### Rename Collection Display Name")
                
                with gr.Row():
                    components['rename_old_name'] = gr.Textbox(
                        label="Current Display Name",
                        placeholder="Enter current display name...",
                        scale=1
                    )
                    components['rename_new_name'] = gr.Textbox(
                        label="New Display Name",
                        placeholder="Enter new display name...",
                        scale=1
                    )
                
                with gr.Row():
                    components['rename_collection_btn'] = gr.Button("✏️ Rename Collection", variant="primary")
                
                components['rename_output'] = gr.Textbox(
                    label="Rename Result",
                    lines=4,
                    interactive=False,
                    placeholder="Collection rename results will appear here..."
                )
            
            # Sub-tab: Delete Collection
            with gr.TabItem("🗑️ Delete Collection"):
                gr.Markdown("### ⚠️ Delete Collection")
                gr.Markdown("**Warning:** This will permanently delete the collection and all its data!")
                
                components['delete_collection_name'] = gr.Textbox(
                    label="Collection Display Name",
                    placeholder="Enter display name of collection to delete...",
                    info="Type the exact display name of the collection you want to delete"
                )
                
                components['delete_force_checkbox'] = gr.Checkbox(
                    label="I understand this action cannot be undone",
                    value=False,
                    info="Check this box to confirm deletion"
                )
                
                with gr.Row():
                    components['delete_collection_btn'] = gr.Button("🗑️ Delete Collection", variant="stop")
                
                components['delete_collection_output'] = gr.Textbox(
                    label="Deletion Result",
                    lines=4,
                    interactive=False,
                    placeholder="Collection deletion results will appear here..."
                )
    
    return components


def create_delete_tab():
    """Create the Delete Documents tab."""
    components = {}
    
    with gr.TabItem("🗑️ Delete Documents"):
        gr.Markdown("### ⚠️ Delete Documents")
        gr.Markdown("**Warning:** This action cannot be undone. Please select files carefully.")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("**Select Files to Delete**")
                components['delete_filename_dropdown'] = gr.Dropdown(
                    choices=[],
                    multiselect=True,
                    show_label=False,
                    interactive=True,
                    elem_classes="vector-dropdown",
                    info="Select one or more files to delete from the collection"
                )
            
            with gr.Column(scale=1):
                gr.Markdown("**Actions**")
                with gr.Row():
                    components['refresh_delete_btn'] = gr.Button("🔄 Refresh Files", variant="secondary", size="sm")
                with gr.Row():
                    components['delete_btn'] = gr.Button("🗑️ Delete Selected Files", variant="stop", scale=1)
        
        components['delete_output'] = gr.Textbox(
            label="Deletion Log",
            lines=8,
            interactive=False,
            placeholder="Deletion results will appear here..."
        )
    
    return components