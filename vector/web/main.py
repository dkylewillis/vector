"""Web interface main entry point for Vector (placeholder during core refactoring)."""

import gradio as gr
from pathlib import Path

from .service import VectorWebService
from .components import (
    create_header, create_collection_selector,
    create_search_tab, create_upload_tab, create_info_tab,
    create_management_tab, create_delete_tab,
    create_document_management_tab, create_collection_documents_tab
)
from .handlers import connect_events


def create_vector_app() -> gr.Blocks:
    """Create the main Gradio application (placeholder)."""
    
    # Initialize Vector web service (placeholder mode)
    web_service = VectorWebService(config=None)
    
    with gr.Blocks(title="Vector - Placeholder Mode") as app:
        
        # Header
        create_header()
        
        # Collection selector
        with gr.Row():
            with gr.Column(scale=1):
                collection_dropdown, refresh_btn, documents_checkboxgroup = create_collection_selector(
                    ["placeholder"], "placeholder", []
                )
            with gr.Column(scale=3):
                # Main tabs
                with gr.Tabs():
                    # Create all tabs (all disabled/placeholder)
                    search_components = create_search_tab()
                    upload_components = create_upload_tab()
                    info_components = create_info_tab()
                    management_components = create_management_tab()
                    document_management_components = create_document_management_tab()
                    collection_documents_components = create_collection_documents_tab()
                    delete_components = create_delete_tab()
                
                # Connect event handlers (placeholder - no actual connections)
                connect_events(
                    web_service, collection_dropdown, refresh_btn,
                    search_components, upload_components, info_components,
                    management_components, document_management_components, 
                    collection_documents_components, delete_components,
                    documents_checkboxgroup
                )
    
    return app


def main():
    """Main entry point for web interface (placeholder)."""
    print("🚀 Starting Vector Web Interface in Placeholder Mode...")
    print("⚠️  All functionality disabled during core refactoring")
    print("📍 Navigate to: http://127.0.0.1:7860")
    
    app = create_vector_app()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        debug=True
    )
