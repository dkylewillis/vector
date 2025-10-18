"""Gradio application factory for Vector web interface."""

import gradio as gr
import logging

logging.basicConfig()
logging.getLogger('docling').setLevel(logging.WARNING)
logging.getLogger('docling_core').setLevel(logging.WARNING)
logging.getLogger('docling.document_converter').setLevel(logging.WARNING)
logging.getLogger('docling.backend').setLevel(logging.WARNING)

from .service import VectorWebService
from .components import (
    create_header, create_search_tab, create_document_management_tab, 
    create_upload_tab, create_info_tab,
)
from .handlers import connect_events


def create_gradio_app() -> gr.Blocks:
    """Create the Gradio application.
    
    This function creates a Gradio Blocks app that can be:
    - Launched standalone
    - Mounted in FastAPI at /ui
    
    Returns:
        gr.Blocks: Configured Gradio application
    """
    
    # Initialize Vector web service (uses global settings)
    web_service = VectorWebService()
    
    # Get initial documents from registry
    initial_documents = web_service.get_registry_documents()
    
    # Get all available tags
    initial_tags = web_service.get_all_tags()
    
    # Custom CSS for the interface
    custom_css = """
    .settings-button {
        min-width: 50px !important;
        padding: 8px !important;
        font-size: 18px !important;
    }
    """
    
    with gr.Blocks(title="Vector - Document Search & AI", css=custom_css) as app:
        
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
                
            with gr.Column(scale=3):
                # Main tabs
                with gr.Tabs():
                    # Create all tabs
                    search_components = create_search_tab()
                    document_management_components = create_document_management_tab()
                    upload_components = create_upload_tab()
                    info_components = create_info_tab()
                
                # Connect event handlers
                connect_events(
                    web_service,
                    search_components, upload_components, info_components,
                    document_management_components,
                    documents_checkboxgroup, tag_filter_dropdown
                )
    
    return app


def main():
    """Main entry point for standalone Gradio server.
    
    This is used when running: python -m apps.gradio
    """
    print("🚀 Starting Vector Gradio Interface...")
    print("📍 Navigate to: http://127.0.0.1:7860")
    
    app = create_gradio_app()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        debug=True
    )


if __name__ == "__main__":
    main()
