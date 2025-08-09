"""
Simple RegScout Web Interface using Gradio
"""

import gradio as gr
import sys
from pathlib import Path
import tempfile
import io
import os

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.cli.commands import RegScoutCommands
from config import Config

theme = gr.themes.Default().set(
    checkbox_background_color='*checkbox_background_color_selected',
    checkbox_background_color_dark='*checkbox_label_text_color',
    checkbox_label_gap='*spacing_xxs',
    checkbox_label_padding='*spacing_sm',
    checkbox_label_text_size='*text_xxs'
)


def create_regscout_app():
    """Create the main Gradio application."""
    
    # Initialize RegScout commands with config
    config = Config()
    regscout = RegScoutCommands(config)
    
    # Load CSS from external file
    def load_css():
        css_path = Path(__file__).parent / "styles.css"
        if css_path.exists():
            return css_path.read_text(encoding='utf-8')
        return ""
    
    custom_css = load_css()
    
    with gr.Blocks(title="RegScout - Document AI Assistant", theme=theme, css=custom_css) as app:
        
        gr.HTML("""
        <div style="text-align: center; padding: 20px;">
            <h1>🔍 RegScout</h1>
            <p>AI-Powered Document Processing & Search</p>
        </div>
        """)
        
        # Collection selector (shared state)
        def get_collections():
            """Get all available collections."""
            try:
                # Create a temporary VectorDatabase instance to get collections
                from src.data_pipeline.vector_database import VectorDatabase
                temp_db = VectorDatabase()
                collections = temp_db.get_all_collections()
                return collections if collections else ["regscout_chunks"]
            except Exception:
                return ["regscout_chunks"]
        
        with gr.Row():
            available_collections = get_collections()
            default_collection = available_collections[0] if available_collections else "regscout_chunks"
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
                regscout.init_components(collection_name=collection, setup_collection=False)
                summary = regscout.research_agent.vector_db.get_metadata_summary()
                
                if "error" in summary:
                    return [], [], []
                
                filenames = summary.get('filenames', [])
                sources = summary.get('sources', [])
                # Note: headings are extracted from 'headings' field in metadata
                headings = summary.get('headings', [])
                
                return filenames, sources, headings
            except Exception:
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
                # Convert to list of strings
                filters['heading'] = [str(h) for h in selected_headings]
            
            return filters
        
        def perform_search(query, top_k, collection, selected_filenames, selected_sources, selected_headings):
            try:
                regscout.init_components(collection_name=collection, setup_collection=False)
                
                metadata_filter = build_metadata_filter(selected_filenames, selected_sources, selected_headings)
                results = regscout.research_agent.search(
                    query, 
                    top_k=int(top_k),
                    metadata_filter=metadata_filter
                )
                
                if results:
                    output = []
                    for i, result in enumerate(results, 1):
                        score = result['score']
                        text = result['text'][:200] + "..." if len(result['text']) > 200 else result['text']
                        metadata = result['metadata']
                        filename = metadata.get('filename', 'Unknown')
                        source = metadata.get('source', 'Unknown')
                        heading = metadata.get('heading', 'None')
                        
                        output.append(f"📄 Result {i} (Score: {score:.3f})")
                        output.append(f"📁 File: {filename}")
                        output.append(f"📂 Source: {source}")
                        output.append(f"📋 Heading: {heading}")
                        output.append(f"📝 Content: {text}")
                        output.append("-" * 50)
                    
                    return "\n".join(output)
                else:
                    return "No results found."
            except Exception as e:
                return f"Search error: {e}"
        
        def ask_ai(question, length, collection, selected_filenames, selected_sources, selected_headings):
            print(f"DEBUG: ask_ai called with collection='{collection}'")  # Debug line
            try:
                regscout.init_components(collection_name=collection, setup_collection=False)
                
                response_lengths = {"short": 200, "medium": 500, "long": 1000}
                max_tokens = response_lengths.get(length, 500)
                
                metadata_filter = build_metadata_filter(selected_filenames, selected_sources, selected_headings)
                
                response = regscout.research_agent.ask(
                    question,
                    use_context=True,
                    max_tokens=max_tokens,
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
                    if 'heading' in metadata_filter:
                        count = len(metadata_filter['heading']) if isinstance(metadata_filter['heading'], list) else 1
                        filter_parts.append(f"Headings: {count}")
                    filter_info = f" [Filters: {', '.join(filter_parts)}]"
                
                return f"[Collection: {collection}]{filter_info}\n\n{response}"
            except Exception as e:
                return f"AI error: {e}"
        
        def process_files(files, collection, source, force):
            if not files:
                return "No files selected."
            
            try:
                regscout.init_components(collection_name=collection, setup_collection=True)
                
                # Convert source selection
                source_value = None if source == "auto" else source
                
                # Capture output
                old_stdout = sys.stdout
                sys.stdout = captured = io.StringIO()
                
                try:
                    # Process each file
                    for file in files:
                        file_path = file.name
                        regscout.process([file_path], force=force, collection_name=collection, source=source_value)
                    
                    output = captured.getvalue()
                    return output or "✅ Processing completed successfully!"
                
                finally:
                    sys.stdout = old_stdout
                    
            except Exception as e:
                return f"❌ Processing error: {e}"
        
        def get_info(collection):
            print(f"DEBUG: get_info called with collection='{collection}'")  # Debug line
            try:
                regscout.init_components(collection_name=collection, setup_collection=False)
                info = regscout.research_agent.vector_db.get_collection_info()
                
                output = []
                output.append(f"Collection: {collection}")
                output.append(f"Points Count: {info.get('points_count', 'Unknown')}")
                output.append(f"Storage Mode: {info.get('storage_mode', 'Unknown')}")
                output.append(f"Vector Size: {info.get('vector_size', 'Unknown')}")
                
                return "\n".join(output)
            except Exception as e:
                return f"Error getting info: {e}"
        
        def get_metadata_summary(collection):
            print(f"DEBUG: get_metadata_summary called with collection='{collection}'")  # Debug line
            try:
                regscout.init_components(collection_name=collection, setup_collection=False)
                summary = regscout.research_agent.vector_db.get_metadata_summary()
                
                if "error" in summary:
                    return f"❌ {summary['error']}"
                
                output = []
                output.append(f"📊 Collection: {collection}")
                output.append(f"📈 Total chunks: {summary['total_chunks']}")
                
                output.append(f"\n📁 Files ({len(summary['filenames'])}):")
                for filename in summary['filenames']:
                    output.append(f"  • {filename}")
                
                output.append(f"\n📂 Sources ({len(summary['sources'])}):")
                for source in summary['sources']:
                    output.append(f"  • {source}")
                
                if summary['headings']:
                    output.append(f"\n📋 Headings (showing first 10):")
                    for heading in summary['headings'][:10]:
                        output.append(f"  • {heading}")
                    if len(summary['headings']) > 10:
                        output.append(f"  ... and {len(summary['headings']) - 10} more")
                
                return "\n".join(output)
                
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
        
        # Connect events
        def refresh_collections():
            """Refresh the collections dropdown."""
            return gr.Dropdown(choices=get_collections())
        
        refresh_btn.click(
            fn=refresh_collections,
            outputs=collection_dropdown
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
            inputs=[file_upload, collection_dropdown, source_dropdown, force_reprocess],
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

if __name__ == "__main__":
    app = create_regscout_app()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        debug=True
    )
