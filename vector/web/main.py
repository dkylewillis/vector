"""Web interface main entry point for Vector."""

import gradio as gr
import sys
import io
from pathlib import Path

from ..config import Config
from ..cli.main import VectorCLI


def create_vector_app() -> gr.Blocks:
    """Create the main Gradio application."""
    
    # Initialize Vector CLI
    config = Config()
    vector = VectorCLI(config)
    
    # Load CSS
    css_path = Path(__file__).parent / "styles.css"
    custom_css = ""
    if css_path.exists():
        custom_css = css_path.read_text(encoding='utf-8')
    
    # Create Gradio theme
    theme = gr.themes.Default().set(
        checkbox_background_color='*checkbox_background_color_selected',
        checkbox_background_color_dark='*checkbox_label_text_color',
        checkbox_label_gap='*spacing_xxs',
        checkbox_label_padding='*spacing_sm',
        checkbox_label_text_size='*text_xxs'
    )
    
    with gr.Blocks(title="Vector - Document AI Assistant", theme=theme, css=custom_css) as app:
        
        gr.HTML("""
        <div style="text-align: center; padding: 20px;">
            <h1>🔍 Vector</h1>
            <p>AI-Powered Document Processing & Search</p>
        </div>
        """)
        
        # Collection selector
        def get_collections():
            """Get all available collections."""
            try:
                collections_result = vector.execute_command('info', collection_name='all')
                collections = []
                if "Available Collections:" in collections_result:
                    lines = collections_result.split('\n')
                    for line in lines:
                        if line.strip().startswith('•'):
                            full_line = line.strip()[2:].strip()
                            if '(' in full_line:
                                collection_name = full_line.split('(')[0].strip()
                            else:
                                collection_name = full_line
                            collections.append(collection_name)
                return collections if collections else [config.default_collection]
            except Exception:
                return [config.default_collection]
        
        with gr.Row():
            available_collections = get_collections()
            default_collection = available_collections[0] if available_collections else config.default_collection
            collection_dropdown = gr.Dropdown(
                choices=available_collections,
                value=default_collection,
                label="Collection",
                scale=3
            )
            refresh_btn = gr.Button("🔄 Refresh Collections", size="sm", scale=1)
        
        # Add function to get metadata for filters
        def get_metadata_options(collection):
            """Get available metadata options for filters."""
            try:
                # Get raw metadata directly from agent instead of formatted CLI output
                agent = vector.get_agent(collection)
                metadata_summary = agent.vector_db.get_metadata_summary()
                
                # Extract the raw lists directly
                filenames = metadata_summary.get('filenames', [])
                sources = metadata_summary.get('sources', [])
                headings = metadata_summary.get('headings', [])
                
                return filenames, sources, headings
            except Exception as e:
                print(f"Error getting metadata options: {e}")
                return [], [], []

        with gr.Tabs():
            
            # Tab 1: Search & Ask
            with gr.TabItem("🔍 Search & Ask"):
                
                # Metadata Filters Section (shared by both Search and Ask)
                gr.Markdown("### 🔧 Filters")
                with gr.Row():
                    update_filters_btn = gr.Button("🔄 Update Filters", variant="secondary", size="sm")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("**📁 Files**")
                        filename_checkboxes = gr.CheckboxGroup(
                            choices=[],
                            label="Select Files",
                            info="Leave empty for all files",
                            interactive=True,
                            elem_id="filename_filters"
                        )
                    
                    with gr.Column(scale=1):
                        gr.Markdown("**📂 Sources**")
                        source_checkboxes = gr.CheckboxGroup(
                            choices=[],
                            label="Select Sources", 
                            info="Leave empty for all sources",
                            interactive=True,
                            elem_id="source_filters"
                        )
                    
                    with gr.Column(scale=1):
                        gr.Markdown("**📋 Headings**")
                        heading_checkboxes = gr.CheckboxGroup(
                            choices=[],
                            label="Select Headings",
                            info="Leave empty for all headings",
                            interactive=True,
                            elem_id="heading_filters"
                        )
                
                # Sub-tabs for Ask AI and Search
                with gr.Tabs():
                    
                    # Ask AI Tab
                    with gr.TabItem("🤖 Ask AI"):
                        with gr.Row():
                            ask_query = gr.Textbox(
                                label="Question",
                                placeholder="Ask a question about your documents...",
                                scale=3
                            )
                            ask_btn = gr.Button("Ask AI", variant="secondary", scale=1)
                        
                        with gr.Row():
                            response_length = gr.Radio(
                                choices=["short", "medium", "long"],
                                value="medium",
                                label="Response Length"
                            )
                        
                        ai_response = gr.Textbox(
                            label="AI Response",
                            lines=8,
                            interactive=False
                        )
                    
                    # Search Documents Tab
                    with gr.TabItem("🔍 Search Documents"):
                        with gr.Row():
                            search_query = gr.Textbox(
                                label="Search Query",
                                placeholder="Enter search terms...",
                                scale=3
                            )
                            search_btn = gr.Button("Search", variant="primary", scale=1)
                        
                        with gr.Row():
                            num_results = gr.Slider(
                                minimum=1, maximum=20, value=5, step=1,
                                label="Number of Results", scale=1
                            )
                        
                        search_results = gr.Textbox(
                            label="Search Results",
                            lines=10,
                            interactive=False
                        )
            
            # Tab 2: Upload Documents
            with gr.TabItem("📁 Upload Documents"):
                
                file_upload = gr.Files(
                    label="Select Documents (.pdf, .docx)",
                    file_types=[".pdf", ".docx"],
                    file_count="multiple"
                )
                
                # Collection selection for upload
                gr.Markdown("### 📚 Collection")
                with gr.Row():
                    collection_mode = gr.Radio(
                        choices=["existing", "new"],
                        value="existing",
                        label="Collection Mode",
                        info="Use existing collection or create a new one",
                        scale=1
                    )
                
                with gr.Row():
                    existing_collection_dropdown = gr.Dropdown(
                        choices=get_collections(),
                        value=default_collection,
                        label="Existing Collection",
                        visible=True,
                        scale=2
                    )
                    new_collection_name = gr.Textbox(
                        label="New Collection Name",
                        placeholder="Enter name for new collection...",
                        visible=False,
                        scale=2
                    )
                
                with gr.Row():
                    source_dropdown = gr.Dropdown(
                        choices=["auto", "ordinances", "manuals", "checklists", "other"],
                        value="auto",
                        label="Source Category",
                        info="Choose source or 'auto' to detect from folder name",
                        scale=2
                    )
                    force_reprocess = gr.Checkbox(
                        label="Force Reprocess",
                        value=False,
                        scale=1
                    )
                
                with gr.Row():
                    process_btn = gr.Button("📚 Process Documents", variant="primary")
                
                processing_output = gr.Textbox(
                    label="Processing Log",
                    lines=15,
                    interactive=False
                )
            
            # Tab 3: Collection Info
            with gr.TabItem("📊 Collection Info"):
                
                with gr.Row():
                    info_btn = gr.Button("📊 Get Collection Info", variant="primary")
                    metadata_btn = gr.Button("📋 Get Metadata Summary", variant="secondary")
                
                collection_info = gr.Textbox(
                    label="Collection Information",
                    lines=12,
                    interactive=False
                )
                
                metadata_summary = gr.Textbox(
                    label="Metadata Summary",
                    lines=20,
                    interactive=False
                )
        
        # Event handlers
        def build_metadata_filter(selected_filenames, selected_sources, selected_headings):
            """Build metadata filter from selected options."""
            # If nothing is selected, return None (no filter)
            if not selected_filenames and not selected_sources and not selected_headings:
                return None
            
            # Build filter with support for multiple values
            filters = {}
            
            if selected_filenames:
                # Convert to list of strings
                filters['filename'] = [str(f) for f in selected_filenames]
            
            if selected_sources:
                # Convert to list of strings
                filters['source'] = [str(s) for s in selected_sources]
            
            if selected_headings:
                # Convert to list of strings - use 'headings' (plural) to match database field
                filters['headings'] = [str(h) for h in selected_headings]
            
            return filters

        def perform_search(query, top_k, collection, selected_filenames, selected_sources, selected_headings):
            try:
                metadata_filter = build_metadata_filter(selected_filenames, selected_sources, selected_headings)
                
                results = vector.execute_command(
                    'search',
                    collection_name=collection,
                    question=query,
                    top_k=int(top_k),
                    metadata_filter=metadata_filter
                )
                return results or "No results found."
            except Exception as e:
                return f"Search error: {e}"
        
        def ask_ai(question, length, collection, selected_filenames, selected_sources, selected_headings):
            try:
                metadata_filter = build_metadata_filter(selected_filenames, selected_sources, selected_headings)
                
                response = vector.execute_command(
                    'ask',
                    collection_name=collection,
                    question=question,
                    response_length=length,
                    metadata_filter=metadata_filter
                )
                
                # Show which filters were applied
                filter_info = ""
                if metadata_filter:
                    filter_parts = []
                    if 'filename' in metadata_filter:
                        count = len(metadata_filter['filename']) if isinstance(metadata_filter['filename'], list) else 1
                        filter_parts.append(f"Files: {count}")
                    if 'source' in metadata_filter:
                        count = len(metadata_filter['source']) if isinstance(metadata_filter['source'], list) else 1
                        filter_parts.append(f"Sources: {count}")
                    if 'headings' in metadata_filter:
                        count = len(metadata_filter['headings']) if isinstance(metadata_filter['headings'], list) else 1
                        filter_parts.append(f"Headings: {count}")
                    filter_info = f" [Filters: {', '.join(filter_parts)}]"
                
                return f"[Collection: {collection}]{filter_info}\n\n{response}"
            except Exception as e:
                return f"AI error: {e}"
        
        def process_files(files, collection_mode, existing_collection, new_collection, source, force):
            if not files:
                return "No files selected."
            
            # Determine which collection to use
            if collection_mode == "new":
                if not new_collection or not new_collection.strip():
                    return "❌ Please enter a name for the new collection."
                collection_name = new_collection.strip().lower()
                # Validate collection name (basic validation)
                if not collection_name.replace('_', '').replace('-', '').isalnum():
                    return "❌ Collection name can only contain letters, numbers, hyphens, and underscores."
            else:
                collection_name = existing_collection
            
            try:
                source_value = None if source == "auto" else source
                
                # Capture output
                old_stdout = sys.stdout
                sys.stdout = captured = io.StringIO()
                
                try:
                    # If creating a new collection, show a message
                    if collection_mode == "new":
                        print(f"🆕 Creating new collection: {collection_name}")
                    
                    for file in files:
                        file_path = file.name
                        result = vector.execute_command(
                            'process',
                            collection_name=collection_name,
                            files=[file_path],
                            force=force,
                            source=source_value
                        )
                        print(result)
                    
                    output = captured.getvalue()
                    
                    # Add success message with collection info
                    if collection_mode == "new":
                        success_msg = f"✅ Documents processed successfully in new collection '{collection_name}'!"
                    else:
                        success_msg = f"✅ Documents processed successfully in collection '{collection_name}'!"
                    
                    return output + "\n" + success_msg if output else success_msg
                
                finally:
                    sys.stdout = old_stdout
                    
            except Exception as e:
                return f"❌ Processing error: {e}"
        
        def get_info(collection):
            try:
                return vector.execute_command('info', collection_name=collection)
            except Exception as e:
                return f"Error getting info: {e}"
        
        def get_metadata_summary(collection):
            try:
                return vector.execute_command('metadata', collection_name=collection)
            except Exception as e:
                return f"❌ Error: {e}"
        
        def update_metadata_filters(collection):
            """Update the filter options based on selected collection."""
            filenames, sources, headings = get_metadata_options(collection)
            
            return (
                gr.CheckboxGroup(choices=filenames, value=[]),
                gr.CheckboxGroup(choices=sources, value=[]),
                gr.CheckboxGroup(choices=headings, value=[])
            )
        
        def toggle_collection_mode(mode):
            """Toggle visibility of collection inputs based on mode."""
            if mode == "new":
                return (
                    gr.Dropdown(visible=False),  # existing_collection_dropdown
                    gr.Textbox(visible=True)     # new_collection_name
                )
            else:
                return (
                    gr.Dropdown(visible=True),   # existing_collection_dropdown
                    gr.Textbox(visible=False)    # new_collection_name
                )
        
        def refresh_collections():
            """Refresh the collections dropdown."""
            return gr.Dropdown(choices=get_collections())
        
        # Connect events
        refresh_btn.click(
            fn=refresh_collections,
            outputs=collection_dropdown
        )
        
        # Toggle collection mode visibility
        collection_mode.change(
            fn=toggle_collection_mode,
            inputs=[collection_mode],
            outputs=[existing_collection_dropdown, new_collection_name]
        )
        
        # Update filters when collection changes or when update button is clicked
        collection_dropdown.change(
            fn=update_metadata_filters,
            inputs=[collection_dropdown],
            outputs=[filename_checkboxes, source_checkboxes, heading_checkboxes]
        )
        
        update_filters_btn.click(
            fn=update_metadata_filters,
            inputs=[collection_dropdown],
            outputs=[filename_checkboxes, source_checkboxes, heading_checkboxes]
        )
        
        search_btn.click(
            fn=perform_search,
            inputs=[search_query, num_results, collection_dropdown, filename_checkboxes, source_checkboxes, heading_checkboxes],
            outputs=search_results
        )
        
        ask_btn.click(
            fn=ask_ai,
            inputs=[ask_query, response_length, collection_dropdown, filename_checkboxes, source_checkboxes, heading_checkboxes],
            outputs=ai_response
        )
        
        process_btn.click(
            fn=process_files,
            inputs=[file_upload, collection_mode, existing_collection_dropdown, new_collection_name, source_dropdown, force_reprocess],
            outputs=processing_output
        )
        
        info_btn.click(
            fn=get_info,
            inputs=[collection_dropdown],
            outputs=collection_info
        )
        
        metadata_btn.click(
            fn=get_metadata_summary,
            inputs=[collection_dropdown],
            outputs=metadata_summary
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
