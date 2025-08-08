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

def create_regscout_app():
    """Create the main Gradio application."""
    
    # Initialize RegScout commands with config
    config = Config()
    regscout = RegScoutCommands(config)
    
    # Modern AI agent styling with Inter font
    custom_css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .gradio-container {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
    }
    
    .gr-block label {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
        font-weight: 500 !important;
    }
    
    .gr-button {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
        font-weight: 500 !important;
    }
    
    .gr-textbox input, .gr-textbox textarea {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
    }
    
    .gr-markdown {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
    }
    """
    
    with gr.Blocks(title="RegScout - Document AI Assistant", theme=gr.themes.Monochrome(), css=custom_css) as app:
        
        gr.HTML("""
        <div style="text-align: center; padding: 20px;">
            <h1>🔍 RegScout</h1>
            <p>AI-Powered Document Processing & Search</p>
        </div>
        """)
        
        # Collection selector (shared state)
        with gr.Row():
            collection_name = gr.Textbox(
                value="regscout_chunks",
                label="Collection Name",
                placeholder="Enter collection name...",
                scale=3
            )
            refresh_btn = gr.Button("🔄 Refresh", size="sm", scale=1)
        
        with gr.Tabs():
            
            # Tab 1: Search & Ask
            with gr.TabItem("🔍 Search & Ask"):
                
                # Search section
                gr.Markdown("### Search Documents")
                with gr.Row():
                    search_query = gr.Textbox(
                        label="Search Query",
                        placeholder="Enter search terms...",
                        scale=3
                    )
                    search_btn = gr.Button("Search", variant="primary", scale=1)
                
                with gr.Row():
                    filename_filter = gr.Textbox(
                        label="Filter by Filename (optional)",
                        placeholder="e.g., ordinance.pdf",
                        scale=2
                    )
                    num_results = gr.Slider(
                        minimum=1, maximum=20, value=5, step=1,
                        label="Results", scale=1
                    )
                
                search_results = gr.Textbox(
                    label="Search Results",
                    lines=10,
                    interactive=False
                )
                
                # Ask AI section
                gr.Markdown("### Ask AI")
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
            
            # Tab 2: Upload Documents
            with gr.TabItem("📁 Upload Documents"):
                
                file_upload = gr.Files(
                    label="Select Documents (.pdf, .docx)",
                    file_types=[".pdf", ".docx"],
                    file_count="multiple"
                )
                
                with gr.Row():
                    force_reprocess = gr.Checkbox(
                        label="Force Reprocess",
                        value=False
                    )
                    process_btn = gr.Button("📚 Process Documents", variant="primary")
                
                processing_output = gr.Textbox(
                    label="Processing Log",
                    lines=15,
                    interactive=False
                )
            
            # Tab 3: Collection Info
            with gr.TabItem("📊 Collection Info"):
                
                info_btn = gr.Button("📊 Get Collection Info", variant="primary")
                
                collection_info = gr.Textbox(
                    label="Collection Information",
                    lines=12,
                    interactive=False
                )
        
        # Event handlers
        def perform_search(query, filename, top_k, collection):
            try:
                regscout.init_components(collection_name=collection, setup_collection=False)
                
                metadata_filter = {"filename": filename} if filename.strip() else None
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
                        filename = result['metadata'].get('filename', 'Unknown')
                        
                        output.append(f"📄 Result {i} (Score: {score:.3f})")
                        output.append(f"📁 Source: {filename}")
                        output.append(f"📝 Content: {text}")
                        output.append("-" * 50)
                    
                    return "\n".join(output)
                else:
                    return "No results found."
            except Exception as e:
                return f"Search error: {e}"
        
        def ask_ai(question, length, collection, filename):
            try:
                regscout.init_components(collection_name=collection, setup_collection=False)
                
                response_lengths = {"short": 200, "medium": 500, "long": 1000}
                max_tokens = response_lengths.get(length, 500)
                
                metadata_filter = {"filename": filename} if filename.strip() else None
                
                response = regscout.research_agent.ask(
                    question,
                    use_context=True,
                    max_tokens=max_tokens,
                    metadata_filter=metadata_filter
                )
                return response
            except Exception as e:
                return f"AI error: {e}"
        
        def process_files(files, collection, force):
            if not files:
                return "No files selected."
            
            try:
                regscout.init_components(collection_name=collection, setup_collection=True)
                
                # Capture output
                old_stdout = sys.stdout
                sys.stdout = captured = io.StringIO()
                
                try:
                    # Process each file
                    for file in files:
                        file_path = file.name
                        regscout.process([file_path], force=force, collection_name=collection)
                    
                    output = captured.getvalue()
                    return output or "✅ Processing completed successfully!"
                
                finally:
                    sys.stdout = old_stdout
                    
            except Exception as e:
                return f"❌ Processing error: {e}"
        
        def get_info(collection):
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
        
        # Connect events
        search_btn.click(
            fn=perform_search,
            inputs=[search_query, filename_filter, num_results, collection_name],
            outputs=search_results
        )
        
        ask_btn.click(
            fn=ask_ai,
            inputs=[ask_query, response_length, collection_name, filename_filter],
            outputs=ai_response
        )
        
        process_btn.click(
            fn=process_files,
            inputs=[file_upload, collection_name, force_reprocess],
            outputs=processing_output
        )
        
        info_btn.click(
            fn=get_info,
            inputs=[collection_name],
            outputs=collection_info
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
