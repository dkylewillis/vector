"""Web interface main entry point for Vector."""

import gradio as gr
from pathlib import Path
import logging

logging.basicConfig()
logging.getLogger('docling').setLevel(logging.WARNING)
logging.getLogger('docling_core').setLevel(logging.WARNING)
logging.getLogger('docling.document_converter').setLevel(logging.WARNING)
logging.getLogger('docling.backend').setLevel(logging.WARNING)

from ..config import Config
from .service import VectorWebService
from .components import (
    create_header, create_collection_selector,
    create_search_tab, create_upload_tab, create_info_tab,
    create_delete_tab,
    create_document_management_tab
)
from .handlers import connect_events


def create_vector_app() -> gr.Blocks:
    """Create the main Gradio application."""
    
    # Initialize Vector web service with config
    config = Config()
    web_service = VectorWebService(config=config)
    
    # Get initial documents from registry
    initial_documents = web_service.get_registry_documents()
    
    # Get all available tags
    initial_tags = web_service.get_all_tags()
    
    with gr.Blocks(title="Vector - Document Search & AI") as app:
        
        # Header
        create_header()
        
        # Main interface without collection selector
        with gr.Row():
            with gr.Column(scale=1):
                # Tag filter
                gr.Markdown("**Filter by Tags**")
                tag_filter_dropdown = gr.Dropdown(
                    label="Select Tags",
                    choices=initial_tags,
                    value=None,
                    multiselect=True,
                    interactive=True,
                    info="Filter documents by tags (leave empty for all documents)"
                )
                
                # Documents list
                gr.Markdown("**Documents**")
                documents_checkboxgroup = gr.CheckboxGroup(
                    label="Select Documents",
                    choices=initial_documents,
                    value=[],
                    interactive=True
                )
                refresh_docs_btn = gr.Button("Refresh Documents", interactive=True)
                
            with gr.Column(scale=3):
                # Main tabs
                with gr.Tabs():
                    # Create all tabs
                    search_components = create_search_tab()
                    upload_components = create_upload_tab()
                    info_components = create_info_tab()
                    document_management_components = create_document_management_tab()
                    delete_components = create_delete_tab()
                
                # Connect event handlers
                connect_events(
                    web_service, None, refresh_docs_btn,
                    search_components, upload_components, info_components,
                    document_management_components, 
                    delete_components,
                    documents_checkboxgroup, tag_filter_dropdown
                )
    
    return app


def main():
    """Main entry point for web interface."""
    print("🚀 Starting Vector Web Interface...")
    print("📍 Navigate to: http://127.0.0.1:7860")
    
    app = create_vector_app()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        debug=True
    )
