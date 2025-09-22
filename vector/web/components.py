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


def create_upload_tab():
    """Create upload tab components."""
    with gr.TabItem("📤 Upload", elem_id="upload_tab"):
        gr.Markdown("### File Upload (Not Yet Implemented)")
        
        file_upload = gr.File(
            label="Select Files",
            file_count="multiple",
            interactive=False
        )
        
        source_textbox = gr.Textbox(
            label="Source",
            placeholder="File upload not yet implemented in refactored version",
            interactive=False
        )
        
        force_checkbox = gr.Checkbox(
            label="Force Reprocess",
            interactive=False
        )
        
        upload_btn = gr.Button("Upload (Not Implemented)", interactive=False)
        upload_output = gr.Textbox(
            label="Upload Status",
            value="Upload functionality not yet implemented in refactored version",
            interactive=False
        )
    
    return {
        'file_upload': file_upload,
        'source_textbox': source_textbox,
        'force_checkbox': force_checkbox,
        'upload_btn': upload_btn,
        'upload_output': upload_output
    }


def create_info_tab():
    """Create info tab components."""
    with gr.TabItem("ℹ️ Info", elem_id="info_tab"):
        gr.Markdown("### Collection Information")
        
        info_btn = gr.Button("Get Info", interactive=True)
        info_output = gr.Textbox(
            label="Collection Info",
            value="",
            interactive=False
        )
        
        metadata_btn = gr.Button("Get Metadata", interactive=False)
        metadata_output = gr.Textbox(
            label="Metadata Summary",
            value="Metadata functionality not yet implemented in refactored version",
            interactive=False
        )
    
    return {
        'info_btn': info_btn,
        'info_output': info_output,
        'metadata_btn': metadata_btn,
        'metadata_output': metadata_output
    }


def create_collection_documents_tab():
    """Create collection documents tab components."""
    with gr.TabItem("📋 Collection Docs", elem_id="collection_documents_tab"):
        gr.Markdown("### Collection Documents")
        
        available_docs_list = gr.CheckboxGroup(
            label="Available Documents",
            choices=[],
            interactive=False
        )
        
        add_to_collection_btn = gr.Button("Add to Collection (Disabled)", interactive=False)
        remove_from_collection_btn = gr.Button("Remove from Collection (Disabled)", interactive=False)
        
        collection_docs_output = gr.Textbox(
            label="Collection Documents Status",
            value="Collection document management not yet implemented in refactored version",
            interactive=False
        )
    
    return {
        'available_docs_list': available_docs_list,
        'add_to_collection_btn': add_to_collection_btn,
        'remove_from_collection_btn': remove_from_collection_btn,
        'collection_docs_output': collection_docs_output
    }


def create_delete_tab():
    """Create delete tab components."""
    with gr.TabItem("🗑️ Delete", elem_id="delete_tab"):
        gr.Markdown("### Delete Operations")
        
        delete_collection_dropdown = gr.Dropdown(
            label="Collection",
            choices=["placeholder"],
            interactive=False
        )
        
        delete_documents_list = gr.CheckboxGroup(
            label="Documents to Delete",
            choices=[],
            interactive=False
        )
        
        confirm_delete_checkbox = gr.Checkbox(
            label="Confirm Deletion",
            interactive=False
        )
        
        delete_selected_btn = gr.Button("Delete Selected (Disabled)", interactive=False)
        delete_output = gr.Textbox(
            label="Delete Status",
            value="Delete functionality not yet implemented in refactored version",
            interactive=False
        )
    
    return {
        'delete_collection_dropdown': delete_collection_dropdown,
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
                        value="both",
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
                
                components['new_name_input'] = gr.Textbox(
                    label="Display Name",
                    placeholder="Enter a friendly name for the collection...",
                )
                
                components['new_desc_input'] = gr.Textbox(
                    label="Description (Optional)",
                    placeholder="Enter a description for the collection...",
                    lines=2
                )
                
                with gr.Row():
                    components['create_btn'] = gr.Button("➕ Create Collection", variant="primary")
                
                components['management_output'] = gr.Textbox(
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
            
            # Sub-tab: Delete Documents
            with gr.TabItem("🗑️ Delete Documents"):
                gr.Markdown("### ⚠️ Permanently Delete Documents")
                gr.Markdown("**Warning:** This will delete the converted documents from disk and remove them from ALL collections!")
                
                components['documents_to_delete'] = gr.CheckboxGroup(
                    label="Select Documents to Delete",
                    choices=[],
                    interactive=True,
                    info="These documents will be permanently removed from the system"
                )
                
                components['confirm_delete_checkbox'] = gr.Checkbox(
                    label="I understand this action cannot be undone",
                    value=False,
                    info="Check this box to confirm deletion"
                )
                
                with gr.Row():
                    components['delete_documents_btn'] = gr.Button("🗑️ Delete Selected Documents", variant="stop")
                
                components['delete_documents_output'] = gr.Textbox(
                    label="Deletion Log",
                    lines=8,
                    interactive=False,
                    placeholder="Select documents and confirm to delete..."
                )
    
    return components


def create_collection_documents_tab():
    """Create the Collection Documents tab (replaces current Delete Documents tab)."""
    components = {}
    
    with gr.TabItem("📚 Collection Documents"):
        with gr.Tabs():
            # Sub-tab: Add Documents
            with gr.TabItem("➕ Add to Collection"):
                gr.Markdown("### Add Documents to Current Collection")
                
                components['available_documents'] = gr.CheckboxGroup(
                    label="Available Documents (not in current collection)",
                    choices=[],
                    interactive=True,
                    info="Select documents to add to the current collection"
                )
                
                with gr.Row():
                    components['add_to_collection_btn'] = gr.Button("➕ Add to Collection", variant="primary")
                
                components['add_to_collection_output'] = gr.Textbox(
                    label="Add Documents Log",
                    lines=6,
                    interactive=False,
                    placeholder="Select documents and click 'Add to Collection'..."
                )
            
            # Sub-tab: Remove from Collection
            with gr.TabItem("➖ Remove from Collection"):
                gr.Markdown("### Remove Documents from Current Collection")
                gr.Markdown("**Note:** This only removes documents from the collection, not from the system.")
                
                with gr.Row():
                    components['remove_from_collection_btn'] = gr.Button("➖ Remove Selected Documents", variant="secondary", scale=1)
                
                components['remove_from_collection_output'] = gr.Textbox(
                    label="Remove Documents Log",
                    lines=6,
                    interactive=False,
                    placeholder="Select documents from the left panel, then click 'Remove Selected Documents'..."
                )
    
    return components


def create_delete_tab():
    """Create the Delete Documents tab (DEPRECATED - Use create_collection_documents_tab instead)."""
    components = {}
    
    with gr.TabItem("🗑️ Delete Documents"):
        gr.Markdown("### ⚠️ Delete Documents")
        gr.Markdown("**Warning:** This action cannot be undone. Please select files carefully.")
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("""
                **Instructions:**
                1. Select documents from the **"Documents in Collection"** section on the left
                2. Click the delete button below
                3. The selected documents will be permanently removed from the collection
                """)
                
                with gr.Row():
                    components['delete_btn'] = gr.Button("🗑️ Delete Selected Documents", variant="stop", scale=1)
        
        components['delete_output'] = gr.Textbox(
            label="Deletion Log",
            lines=8,
            interactive=False,
            placeholder="Select documents from the left panel, then click 'Delete Selected Documents'..."
        )
    
    return components