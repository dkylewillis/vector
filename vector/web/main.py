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
    theme = gr.themes.Base().set(
        background_fill_primary='*primary_50',
        block_background_fill_dark='*body_background_fill',
        block_border_color='*background_fill_primary',
        block_border_color_dark='*background_fill_primary',
    )
    
    with gr.Blocks(title="Vector - Document AI Assistant", 
                   theme=theme, 
                   css=custom_css
                   ) as app:
        
        gr.HTML("""
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet">
        <div style="text-align: center; padding: 20px;">
            <h1>
            <span style="color:#3b82f6; font-size:50px; position:relative; top:4px;">●</span>
            Vector
            </h1>
            <p>AI-Powered Document Processing & Search</p>
        </div>
        """)
        
        # Collection selector
        def get_collections():
            """Get all available collections with display names."""
            try:
                collections_result = vector.execute_command('collections')
                collections = []
                if "Collections:" in collections_result:
                    lines = collections_result.split('\n')
                    for line in lines:
                        if line.strip().startswith('•'):
                            # Extract display name from the line
                            display_name = line.strip()[2:].strip()
                            collections.append(display_name)
                return collections if collections else [config.default_collection]
            except Exception as e:
                print(f"Error getting collections: {e}")
                return [config.default_collection]
        
        with gr.Column(elem_id="dropdown_column"):
            with gr.Row(elem_id="collection_selector_top"):
                gr.Markdown("**Collection**", elem_id="bottom_md")
                with gr.Column(scale=3):
                    pass  # empty column acts as spacer
                refresh_btn = gr.Button("Refresh Collections", size="sm", scale=1, elem_classes="icon-btn", elem_id="refresh_btn")
            with gr.Row():
                available_collections = get_collections()
                default_collection = available_collections[0] if available_collections else config.default_collection
                collection_dropdown = gr.Dropdown(
                    choices=available_collections,
                    value=default_collection,
                    show_label=False,
                    scale=3
                )
        
        # Add function to get metadata for filters
        def get_metadata_options(collection):
            """Get available metadata options for filters."""
            try:
                # Get metadata summary from CLI command (which now uses agent properly)
                metadata_result = vector.execute_command('metadata', collection_name=collection)
                
                # Parse the formatted output to extract lists
                filenames = []
                sources = []
                headings = []
                
                lines = metadata_result.split('\n')
                current_section = None
                
                for line in lines:
                    line = line.strip()
                    if '📁 Files:' in line:
                        current_section = 'files'
                        continue
                    elif '📋 Sources:' in line:
                        current_section = 'sources'
                        continue
                    elif '🏷️ Headings:' in line:
                        current_section = 'headings'
                        continue
                    elif '📊 Total:' in line or not line:
                        current_section = None
                        continue
                    
                    # Parse items (remove bullet points and clean up)
                    if current_section and line.startswith('•'):
                        item = line[1:].strip()
                        if current_section == 'files':
                            filenames.append(item)
                        elif current_section == 'sources':
                            sources.append(item)
                        elif current_section == 'headings':
                            headings.append(item)
                
                return filenames, sources, headings
            except Exception as e:
                print(f"Error getting metadata options: {e}")
                return [], [], []

        with gr.Tabs(elem_id="search_ask_tabs"): # Search and Ask

            # Tab 1: Search & Ask
            with gr.TabItem("🔍 Search & Ask"):
                
                # Metadata Filters Section (shared by both Search and Ask)
                with gr.Row():
                    with gr.Column(scale=0):
                        with gr.Row():
                            gr.Markdown("### <span class='material-symbols-outlined' " \
                            "style='font-size:20px; margin-top:4px; position:relative; top:4px;'>menu</span> " \
                            "Filters")
                            update_filters_btn = gr.Button("Update Filters", variant="secondary", size="sm", elem_classes="icon-btn", elem_id="update_btn")

                with gr.Row():
                    with gr.Column(scale=1, min_width=50, elem_classes="dropdown_column"):
                        gr.Markdown("**Files**", elem_classes="filter_label")
                        filename_filter_dropdown = gr.Dropdown(
                            choices=[],
                            multiselect=True,
                            show_label=False,
                            interactive=True,
                            elem_classes="vector-dropdown"
                        )
                    
                    with gr.Column(scale=1, min_width=50, elem_classes="dropdown_column"):
                        gr.Markdown("**Sources**", elem_classes="filter_label")
                        source_filter_dropdown = gr.Dropdown(
                            choices=[],
                            multiselect=True,
                            show_label=False,
                            interactive=True,
                            elem_classes="vector-dropdown"
                        )
                    
                    with gr.Column(scale=1, min_width=50, elem_classes="dropdown_column"):
                        gr.Markdown("**Headings**", elem_classes="filter_label")
                        heading_filter_dropdown = gr.Dropdown( 
                            choices=[],
                            multiselect=True,
                            show_label=False,
                            interactive=True,
                            elem_classes="vector-dropdown"
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
                            ask_btn = gr.Button("Ask AI", variant="primary", scale=1, elem_classes="vector-button-1")

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
                            search_btn = gr.Button("Search", variant="primary", scale=1, elem_classes="vector-button-1")
                        
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
            
            # Tab 4: Collection Management
            with gr.TabItem("📚 Collection Management"):
                
                with gr.Tabs():
                    
                    # Sub-tab: List Collections
                    with gr.TabItem("📋 List Collections"):
                        with gr.Row():
                            list_collections_btn = gr.Button("📋 List All Collections", variant="primary")
                        
                        collections_list = gr.Textbox(
                            label="Collections",
                            lines=12,
                            interactive=False,
                            placeholder="Click 'List All Collections' to see available collections..."
                        )
                    
                    # Sub-tab: Create Collection
                    with gr.TabItem("➕ Create Collection"):
                        gr.Markdown("### Create New Collection")
                        
                        with gr.Row():
                            create_display_name = gr.Textbox(
                                label="Display Name",
                                placeholder="Enter a friendly name for the collection...",
                                scale=2
                            )
                            create_modality = gr.Dropdown(
                                choices=["chunks", "artifacts"],
                                value="chunks",
                                label="Modality",
                                info="Type of data to store",
                                scale=1
                            )
                        
                        create_description = gr.Textbox(
                            label="Description (Optional)",
                            placeholder="Enter a description for the collection...",
                            lines=2
                        )
                        
                        with gr.Row():
                            create_collection_btn = gr.Button("➕ Create Collection", variant="primary")
                        
                        create_output = gr.Textbox(
                            label="Creation Result",
                            lines=4,
                            interactive=False,
                            placeholder="Collection creation results will appear here..."
                        )
                    
                    # Sub-tab: Rename Collection
                    with gr.TabItem("✏️ Rename Collection"):
                        gr.Markdown("### Rename Collection Display Name")
                        
                        with gr.Row():
                            rename_old_name = gr.Textbox(
                                label="Current Display Name",
                                placeholder="Enter current display name...",
                                scale=1
                            )
                            rename_new_name = gr.Textbox(
                                label="New Display Name",
                                placeholder="Enter new display name...",
                                scale=1
                            )
                        
                        with gr.Row():
                            rename_collection_btn = gr.Button("✏️ Rename Collection", variant="primary")
                        
                        rename_output = gr.Textbox(
                            label="Rename Result",
                            lines=4,
                            interactive=False,
                            placeholder="Collection rename results will appear here..."
                        )
                    
                    # Sub-tab: Delete Collection
                    with gr.TabItem("🗑️ Delete Collection"):
                        gr.Markdown("### ⚠️ Delete Collection")
                        gr.Markdown("**Warning:** This will permanently delete the collection and all its data!")
                        
                        delete_collection_name = gr.Textbox(
                            label="Collection Display Name",
                            placeholder="Enter display name of collection to delete...",
                            info="Type the exact display name of the collection you want to delete"
                        )
                        
                        delete_force_checkbox = gr.Checkbox(
                            label="I understand this action cannot be undone",
                            value=False,
                            info="Check this box to confirm deletion"
                        )
                        
                        with gr.Row():
                            delete_collection_btn = gr.Button("🗑️ Delete Collection", variant="stop")
                        
                        delete_collection_output = gr.Textbox(
                            label="Deletion Result",
                            lines=4,
                            interactive=False,
                            placeholder="Collection deletion results will appear here..."
                        )
            
            # Tab 5: Delete Documents
            with gr.TabItem("🗑️ Delete Documents"):
                
                gr.Markdown("### ⚠️ Delete Documents")
                gr.Markdown("**Warning:** This action cannot be undone. Please select files carefully.")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("**Select Files to Delete**")
                        delete_filename_dropdown = gr.Dropdown(
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
                            refresh_delete_btn = gr.Button("🔄 Refresh Files", variant="secondary", size="sm")
                        with gr.Row():
                            delete_btn = gr.Button("🗑️ Delete Selected Files", variant="stop", scale=1)
                
                delete_output = gr.Textbox(
                    label="Deletion Log",
                    lines=8,
                    interactive=False,
                    placeholder="Deletion results will appear here..."
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
        
        def process_files(files, collection_mode, current_collection, new_collection, source, force):
            if not files:
                return "No files selected."
            
            # Determine which collection to use
            if collection_mode == "new":
                if not new_collection or not new_collection.strip():
                    return "❌ Please enter a name for the new collection."
                
                collection_name = new_collection.strip()
                
                # Try to create the collection first
                try:
                    create_result = vector.execute_command(
                        'create-collection',
                        display_name=collection_name,
                        modality="chunks",  # Default to chunks for document processing
                        description=f"Auto-created collection for uploaded documents"
                    )
                    
                    if "❌" in create_result:
                        # Collection creation failed, might already exist
                        if "already exists" not in create_result:
                            return f"❌ Failed to create collection: {create_result}"
                        # If it already exists, continue with processing
                    
                except Exception as e:
                    return f"❌ Error creating collection: {e}"
                    
            else:
                collection_name = current_collection
            
            try:
                source_value = None if source == "auto" else source
                
                # Capture output
                old_stdout = sys.stdout
                sys.stdout = captured = io.StringIO()
                
                try:
                    # If creating a new collection, show a message
                    if collection_mode == "new":
                        print(f"🆕 Using collection: {collection_name}")
                    
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
                        success_msg = f"✅ Documents processed successfully in collection '{collection_name}'!"
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
        
        def delete_documents(selected_files, collection):
            """Delete selected documents from the collection."""
            if not selected_files:
                return "❌ No files selected for deletion."
            
            try:
                deleted_count = 0
                results = []
                
                for filename in selected_files:
                    try:
                        result = vector.execute_command(
                            'delete',
                            collection_name=collection,
                            key='filename',
                            value=filename
                        )
                        results.append(f"✅ {filename}: {result}")
                        deleted_count += 1
                    except Exception as e:
                        results.append(f"❌ {filename}: Error - {e}")
                
                summary = f"📊 Summary: {deleted_count}/{len(selected_files)} files deleted successfully\n\n"
                return summary + "\n".join(results)
                
            except Exception as e:
                return f"❌ Deletion error: {e}"
        
        def refresh_delete_files(collection):
            """Refresh the files list for deletion dropdown."""
            filenames, _, _ = get_metadata_options(collection)
            return gr.Dropdown(choices=filenames, value=[])
        
        def update_metadata_filters(collection):
            """Update the filter options based on selected collection."""
            filenames, sources, headings = get_metadata_options(collection)
            
            return (
                gr.Dropdown(choices=filenames, value=[]),  # filename_filter_dropdown
                gr.Dropdown(choices=sources, value=[]),    # source_filter_dropdown  
                gr.Dropdown(choices=headings, value=[]),   # heading_filter_dropdown
                gr.Dropdown(choices=filenames, value=[])   # delete_filename_dropdown
            )
        
        def toggle_collection_mode(mode):
            """Toggle visibility of collection inputs based on mode."""
            if mode == "new":
                return gr.Textbox(visible=True)     # new_collection_name
            else:
                return gr.Textbox(visible=False)    # new_collection_name
        
        def refresh_collections():
            """Refresh the collections dropdown."""
            return gr.Dropdown(choices=get_collections())
        
        def list_all_collections():
            """List all collections with their metadata."""
            try:
                return vector.execute_command('collections')
            except Exception as e:
                return f"❌ Error listing collections: {e}"
        
        def create_new_collection(display_name, modality, description):
            """Create a new collection."""
            try:
                if not display_name or not display_name.strip():
                    return "❌ Display name is required"
                
                if not modality:
                    return "❌ Modality is required"
                
                result = vector.execute_command(
                    'create-collection',
                    display_name=display_name.strip(),
                    modality=modality,
                    description=description.strip() if description else ""
                )
                return result
            except Exception as e:
                return f"❌ Error creating collection: {e}"
        
        def rename_collection(old_name, new_name):
            """Rename a collection's display name."""
            try:
                if not old_name or not old_name.strip():
                    return "❌ Current display name is required"
                
                if not new_name or not new_name.strip():
                    return "❌ New display name is required"
                
                result = vector.execute_command(
                    'rename-collection',
                    old_name=old_name.strip(),
                    new_name=new_name.strip()
                )
                return result
            except Exception as e:
                return f"❌ Error renaming collection: {e}"
        
        def delete_collection(collection_name, force_confirmed):
            """Delete a collection."""
            try:
                if not collection_name or not collection_name.strip():
                    return "❌ Collection display name is required"
                
                if not force_confirmed:
                    return "❌ Please confirm deletion by checking the checkbox"
                
                result = vector.execute_command(
                    'delete-collection',
                    display_name=collection_name.strip(),
                    force=True
                )
                return result
            except Exception as e:
                return f"❌ Error deleting collection: {e}"
        
        # Connect events
        refresh_btn.click(
            fn=refresh_collections,
            outputs=collection_dropdown
        )
        
        # Toggle collection mode visibility
        collection_mode.change(
            fn=toggle_collection_mode,
            inputs=[collection_mode],
            outputs=[new_collection_name]
        )
        
        # Update filters when collection changes or when update button is clicked
        collection_dropdown.change(
            fn=update_metadata_filters,
            inputs=[collection_dropdown],
            outputs=[filename_filter_dropdown, source_filter_dropdown, heading_filter_dropdown, delete_filename_dropdown]
        )
        
        update_filters_btn.click(
            fn=update_metadata_filters,
            inputs=[collection_dropdown],
            outputs=[filename_filter_dropdown, source_filter_dropdown, heading_filter_dropdown, delete_filename_dropdown]
        )
        
        search_btn.click(
            fn=perform_search,
            inputs=[search_query, num_results, collection_dropdown, filename_filter_dropdown, source_filter_dropdown, heading_filter_dropdown],
            outputs=search_results
        )
        
        ask_btn.click(
            fn=ask_ai,
            inputs=[ask_query, response_length, collection_dropdown, filename_filter_dropdown, source_filter_dropdown, heading_filter_dropdown],
            outputs=ai_response
        )
        
        process_btn.click(
            fn=process_files,
            inputs=[file_upload, collection_mode, collection_dropdown, new_collection_name, source_dropdown, force_reprocess],
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
        
        # Delete documents handlers
        delete_btn.click(
            fn=delete_documents,
            inputs=[delete_filename_dropdown, collection_dropdown],
            outputs=delete_output
        )
        
        refresh_delete_btn.click(
            fn=refresh_delete_files,
            inputs=[collection_dropdown],
            outputs=delete_filename_dropdown
        )
        
        # Collection management handlers
        list_collections_btn.click(
            fn=list_all_collections,
            outputs=collections_list
        )
        
        create_collection_btn.click(
            fn=create_new_collection,
            inputs=[create_display_name, create_modality, create_description],
            outputs=create_output
        )
        
        rename_collection_btn.click(
            fn=rename_collection,
            inputs=[rename_old_name, rename_new_name],
            outputs=rename_output
        )
        
        delete_collection_btn.click(
            fn=delete_collection,
            inputs=[delete_collection_name, delete_force_checkbox],
            outputs=delete_collection_output
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
