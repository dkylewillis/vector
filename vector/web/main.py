"""Web interface main entry point for Vector."""

import gradio as gr
from pathlib import Path

from ..config import Config
from .service import VectorWebService
from .components import (
    create_header, create_collection_selector,
    create_search_tab, create_upload_tab, create_info_tab,
    create_management_tab, create_delete_tab,
    create_document_management_tab, create_collection_documents_tab
)
from .handlers import connect_events


def create_vector_app() -> gr.Blocks:
    """Create the main Gradio application."""
    
    # Initialize Vector web service
    config = Config()
    web_service = VectorWebService(config)
    
    # Load CSS
    css_path = Path(__file__).parent / "styles.css"
    custom_css = ""
    if css_path.exists():
        custom_css = css_path.read_text(encoding='utf-8')
    custom_css = ""

    # Create Gradio theme
    theme = gr.themes.Base().set(
        background_fill_primary='*primary_50',
        block_background_fill_dark='*body_background_fill',
        block_border_color='*background_fill_primary',
        block_border_color_dark='*background_fill_primary',
    )
    
    with gr.Blocks(title="Vector - Document AI Assistant", 
                   theme=theme, css=custom_css) as app:
        
        # Header
        create_header()
        
        # Collection selector
        with gr.Row():
            with gr.Column(scale=1):
                available_collections = web_service.get_collections()
                default_collection = available_collections[0] if available_collections else config.default_collection
                
                # Get initial documents for the default collection
                initial_documents = web_service.get_collection_documents(default_collection) if default_collection else []
                
                collection_dropdown, refresh_btn, documents_checkboxgroup = create_collection_selector(
                    available_collections, default_collection, initial_documents
                )
            with gr.Column(scale=3):
                # Main tabs
                with gr.Tabs(elem_id="search_ask_tabs"):
                    # Create all tabs
                    search_components = create_search_tab()
                    upload_components = create_upload_tab()
                    info_components = create_info_tab()
                    management_components = create_management_tab()
                    document_management_components = create_document_management_tab()
                    collection_documents_components = create_collection_documents_tab()
                    delete_components = create_delete_tab()  # Keep for backward compatibility
                
                # Connect all event handlers
                connect_events(
                    web_service, collection_dropdown, refresh_btn,
                    search_components, upload_components, info_components,
                    management_components, document_management_components, 
                    collection_documents_components, delete_components,
                    documents_checkboxgroup
                )
                
                # Auto-populate document management lists on interface load
                def initialize_document_lists():
                    """Initialize document lists when interface loads."""
                    try:
                        documents = web_service.get_all_documents()
                        return (
                            gr.CheckboxGroup(choices=documents, value=[]),  # all_documents_list
                            gr.CheckboxGroup(choices=documents, value=[])   # documents_to_delete
                        )
                    except Exception as e:
                        print(f"Warning: Could not initialize document lists: {e}")
                        return (
                            gr.CheckboxGroup(choices=[], value=[]),
                            gr.CheckboxGroup(choices=[], value=[])
                        )
                
                # Set up interface load event to populate document lists
                app.load(
                    fn=initialize_document_lists,
                    outputs=[
                        document_management_components['all_documents_list'],
                        document_management_components['documents_to_delete']
                    ]
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
