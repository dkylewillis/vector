#!/usr/bin/env python3
"""
RegScout CLI - Complete command-line interface for document processing and querying
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

from src.data_pipeline.file_processing import FileProcessor
from src.agents.research_agent import ResearchAgent
# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()


def setup_imports():
    """Setup import paths"""
    project_root = os.path.dirname(__file__)
    sys.path.append(os.path.join(project_root, 'src'))
    sys.path.append(project_root)


class RegScoutCLI:
    """Complete CLI for RegScout functionality"""
    
    def __init__(self):
        setup_imports()
        self.research_agent = None
        self.vector_db = None
        self.embedder = None
    
    def init_components(self, collection_name: str = "regscout_documents", setup_collection: bool = True):
        """Initialize research agent"""
        if self.research_agent is not None:
            return
            
        try:
            from agents.research_agent import ResearchAgent
            from data_pipeline.vector_database import VectorDatabase
            from data_pipeline.embedder import Embedder
            
            print("🔧 Initializing RegScout...")
            
            # Initialize research agent
            self.research_agent = ResearchAgent(collection_name=collection_name)
            
            # Get embedder and vector_db from research agent to avoid duplication
            self.embedder = self.research_agent.embedder
            self.vector_db = self.research_agent.vector_db
            
            # Only setup collection if needed
            if setup_collection:
                # Check if collection exists before prompting
                if not self.vector_db.collection_exists():
                    print(f"📦 Collection '{collection_name}' does not exist.")
                    response = input(f"Create new collection '{collection_name}'? (y/N): ")
                    if response.lower() != 'y':
                        print("❌ Operation cancelled - collection creation required for processing")
                        sys.exit(0)
                
                vector_size = self.research_agent.setup_collection()
                print(f"✓ Ready (embedding dimension: {vector_size})")
            else:
                print(f"✓ Ready (read-only mode)")
            
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            sys.exit(1)
    
    def _chunk_text(self, text: str, max_chunk_size: int = 1000) -> List[str]:
        """
        Split text into chunks for better retrieval.
        
        Args:
            text: Text to chunk
            max_chunk_size: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        # First try to split by double newlines (paragraphs)
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed max size, save current chunk
            if len(current_chunk) + len(paragraph) > max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # If no good paragraph breaks, fall back to simple splitting
        if len(chunks) == 1 and len(chunks[0]) > max_chunk_size:
            text = chunks[0]
            chunks = []
            words = text.split()
            current_chunk = ""
            
            for word in words:
                if len(current_chunk) + len(word) + 1 > max_chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = word
                else:
                    if current_chunk:
                        current_chunk += " " + word
                    else:
                        current_chunk = word
            
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]  # Return original text if chunking fails
    
    def _is_file_already_processed(self, file_path: Path) -> bool:
        """
        Check if a file has already been processed by searching for it in the knowledge base.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file is already in knowledge base, False otherwise
        """
        try:
            # Simple approach: search for the filename in documents
            # This is not perfect but works for basic duplicate detection
            results = self.research_agent.search(
                f"filename:{file_path.name}", 
                top_k=5, 
                score_threshold=0.1
            )
            
            # Check if any results have matching filename in metadata
            for result in results:
                if result.get('metadata', {}).get('filename') == file_path.name:
                    return True
            
            return False
            
        except Exception:
            # If we can't check, assume it's not processed to be safe
            return False

    def process_files(self, file_paths: List[str], force: bool = False, collection_name: str = "regscout_documents"):
        """Process files and add them to the knowledge base"""
        self.init_components(collection_name=collection_name, setup_collection=True)  # Only process creates collections
        self.file_processor = FileProcessor()
        
        # Expand directories to individual files
        expanded_files = []
        supported_extensions = {'.txt', '.md', '.pdf', '.docx'}
        
        for file_path in file_paths:
            path = Path(file_path)
            
            if path.is_dir():
                print(f"📁 Scanning directory: {path}")
                # Find all supported files in directory (recursive)
                for ext in supported_extensions:
                    found_files = list(path.rglob(f"*{ext}"))
                    expanded_files.extend(found_files)
                    if found_files:
                        print(f"   Found {len(found_files)} {ext} file(s)")
            elif path.exists():
                expanded_files.append(path)
            else:
                print(f"⚠️  File/directory not found: {file_path}")
        
        if not expanded_files:
            print("❌ No supported files found")
            return
        
        # Remove duplicates and sort
        expanded_files = sorted(set(expanded_files))
        
        # Filter out already processed files unless force is True
        files_to_process = []
        skipped_files = []
        
        if not force:
            print(f"🔍 Checking {len(expanded_files)} file(s) for duplicates...")
            for file_path in expanded_files:
                if self._is_file_already_processed(file_path):
                    skipped_files.append(file_path)
                else:
                    files_to_process.append(file_path)
        else:
            files_to_process = expanded_files
        
        # Report what we're doing
        if skipped_files:
            print(f"⏭️  Skipping {len(skipped_files)} already processed file(s)")
            if len(skipped_files) <= 5:  # Show filenames if not too many
                for file_path in skipped_files:
                    print(f"   📄 {file_path.name}")
            else:
                print(f"   📄 {skipped_files[0].name} ... and {len(skipped_files)-1} more")
        
        if not files_to_process:
            print("✅ All files already processed! Use --force to reprocess.")
            return
            
        print(f"📁 Processing {len(files_to_process)} new file(s)...")
        
        documents = []
        metadata = []
        
        for path in files_to_process:
            rel_path = path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path
            print(f"  📄 {rel_path}")
            
            try:
                # Read file content using appropriate processor
                if path.suffix.lower() in ['.txt', '.md']:
                    with open(path, 'r', encoding='utf-8') as f:
                        full_content = f.read()
                    
                    # Chunk text files by paragraphs or sections for better retrieval
                    chunks = self._chunk_text(full_content)
                    print(f"    ✓ Split into {len(chunks)} chunks")
                    
                    for i, chunk_text in enumerate(chunks):
                        documents.append(chunk_text)
                        metadata.append({
                            'filename': path.name,
                            'file_type': path.suffix.lower().lstrip('.'),
                            'source_path': str(path),
                            'chunk_index': i,
                            'total_chunks': len(chunks)
                        })
                    continue  # Skip the main document addition
                        
                elif path.suffix.lower() == '.pdf' and self.file_processor:
                    # Use real PDF processing
                    try:
                        result = self.file_processor.process_pdf(path)
                        # Extract text from processing result
                        if isinstance(result, dict) and 'content' in result:
                            content = result['content']
                        else:
                            content = str(result)
                    except Exception as e:
                        print(f"    ⚠️  PDF processing failed: {e}")
                        content = f"PDF Document: {path.name}\n[PDF processing failed: {e}]"
                        
                elif path.suffix.lower() == '.docx' and self.file_processor:
                    # Use real DOCX processing - store each chunk separately
                    try:
                        chunks = self.file_processor.process_docx(path)
                        if chunks and len(chunks) > 0:
                            print(f"    ✓ Extracted {len(chunks)} chunks")
                            for i, chunk in enumerate(chunks):
                                if hasattr(chunk, 'text'):
                                    chunk_text = chunk.text
                                elif isinstance(chunk, dict):
                                    chunk_text = chunk.get('text', chunk.get('content', str(chunk)))
                                else:
                                    chunk_text = str(chunk)

                                # Extract meta if available
                                if hasattr(chunk, 'meta'):
                                    chunk_meta = chunk.meta
                                elif isinstance(chunk, dict):
                                    chunk_meta = chunk.get('meta', {})
                                else:
                                    chunk_meta = {}

                                # Add each chunk as a separate document
                                documents.append(chunk_text)
                                # Merge chunk_meta with default metadata
                                merged_meta = {
                                    'filename': path.name,
                                    'file_type': 'docx',
                                    'source_path': str(path),
                                    'chunk_index': i,
                                    'total_chunks': len(chunks),
                                    'headings': chunk_meta.get('headings', []),  # Preserve headings if available
                            
                                }
                                metadata.append(merged_meta)
                        else:
                            # Fallback if no chunks extracted
                            content = f"DOCX Document: {path.name}\n[No content extracted]"
                            documents.append(content)
                            metadata.append({
                                'filename': path.name,
                                'file_type': 'docx',
                                'source_path': str(path)
                            })
                        continue  # Skip the main document addition since we added chunks
                    except Exception as e:
                        print(f"    ⚠️  DOCX processing failed: {e}")
                        content = f"DOCX Document: {path.name}\n[DOCX processing failed: {e}]"
                        
                else:
                    # Fallback for unsupported types or missing processor
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    except:
                        content = f"Document: {path.name}\n[Could not read file content]"
                
                documents.append(content)
                metadata.append({
                    'filename': path.name,
                    'file_type': path.suffix.lower().lstrip('.'),
                    'source_path': str(path)
                })
                
            except Exception as e:
                print(f"    ❌ Error processing {path.name}: {e}")
        
        if documents:
            print(f"📚 Adding {len(documents)} documents to knowledge base...")
            
            # Generate embeddings
            embeddings = self.embedder.embed_documents(documents)
            
            # Add to vector database directly
            doc_ids = self.vector_db.add_documents(documents, embeddings, metadata)
            print(f"✅ Successfully added {len(doc_ids)} document(s)")
        else:
            print("⚠️  No documents were processed")
    
    def search_documents(self, question: str, top_k: int = 5, collection_name: str = "regscout_documents"):
        """Search the knowledge base"""
        self.init_components(collection_name=collection_name, setup_collection=False)  # Read-only mode
        
        print(f"🔍 Searching: '{question}'")
        results = self.research_agent.search(question, top_k=top_k)
        
        if not results:
            print("❌ No results found")
            return
        
        print(f"\n📋 Found {len(results)} result(s):\n")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            score = result['score']
            filename = result['metadata'].get('filename', 'Unknown')
            text = result['text']
            chunk_info = ""
            
            # Add chunk information if available
            if 'chunk_index' in result['metadata']:
                chunk_idx = result['metadata']['chunk_index']
                total_chunks = result['metadata'].get('total_chunks', '?')
                chunk_info = f" (chunk {chunk_idx + 1}/{total_chunks})"
            
            # Header with result number and score
            print(f"\n📄 Result {i}")
            print(f"📊 Relevance Score: {score:.4f}")
            print(f"📁 Source: {filename}{chunk_info}")
            print("-" * 60)
            
            # Format text with proper line wrapping
            if len(text) > 500:
                # Show first 500 characters with proper word boundary
                truncated = text[:500]
                last_space = truncated.rfind(' ')
                if last_space > 400:  # Only truncate at word boundary if reasonable
                    truncated = truncated[:last_space]
                text_display = truncated + "..."
            else:
                text_display = text
            
            # Clean up text formatting
            text_display = text_display.strip()
            # Replace multiple whitespace/newlines with single spaces for readability
            import re
            text_display = re.sub(r'\s+', ' ', text_display)
            
            print(f"📝 Content:")
            
            # Split long text into paragraphs for better readability
            if len(text_display) > 200:
                # Try to break into logical paragraphs
                paragraphs = text_display.split('. ')
                formatted_text = ""
                current_line = ""
                
                for sentence in paragraphs:
                    if len(current_line + sentence) > 80:
                        if current_line:
                            formatted_text += f"   {current_line.strip()}\n"
                            current_line = sentence + ". "
                        else:
                            formatted_text += f"   {sentence}.\n"
                    else:
                        current_line += sentence + ". "
                
                if current_line:
                    formatted_text += f"   {current_line.strip()}"
                
                print(formatted_text)
            else:
                print(f"   {text_display}")
            
            if i < len(results):
                print("\n" + "=" * 80)
        
        print(f"\n✨ Search completed - showing top {len(results)} results")
    
    def ask_ai(self, question: str, response_length: str = "medium", collection_name: str = "regscout_documents"):
        """Ask AI a question with document context"""
        self.init_components(collection_name=collection_name, setup_collection=False)  # Read-only mode
        
        print(f"🤖 AI Question: '{question}'")
        
        # Check if OpenAI API key is available
        if not os.getenv('OPENAI_API_KEY'):
            print("❌ OpenAI API key not found!")
            print("   Please set your API key using one of these methods:")
            print("   1. Create a .env file with: OPENAI_API_KEY=your_key_here")
            print("   2. Set environment variable: set OPENAI_API_KEY=your_key_here")
            print("   3. Add api_key to config/settings.yaml")
            print("   Get your API key from: https://platform.openai.com/api-keys")
            return
        
        # Get max_tokens from config based on response length
        response_lengths = self.research_agent.config.get('ai_model.response_lengths', {})
        max_tokens = response_lengths.get(response_length, response_lengths.get('short', 256))
        
        print(f"📏 Response length: {response_length} ({max_tokens} tokens)")
        
        try:
            print("🤔 Thinking...")
            # Use the research agent's ask function directly
            response = self.research_agent.ask(question, use_context=True, max_tokens=max_tokens)
            print(f"\n💡 AI Answer:\n{response}\n")
                
        except Exception as e:
            print(f"❌ AI service error: {e}")
            # Fallback: show relevant documents if AI fails
            context_results = self.research_agent.search(question, top_k=3)
            if context_results:
                print("\n📚 Here are the relevant documents I found:")
                for result in context_results:
                    filename = result['metadata'].get('filename', 'Unknown')
                    text = result['text'][:150] + "..." if len(result['text']) > 150 else result['text']
                    print(f"  📁 {filename}: {text}")
            else:
                print("❌ No relevant documents found")

    def research_topic(self, topic: str, depth: str = "medium", additional_questions: List[str] = None, save_report: bool = False, collection_name: str = "regscout_documents"):
        """Conduct comprehensive research on a topic"""
        self.init_components(collection_name=collection_name, setup_collection=False)  # Read-only mode
        
        print(f"🔬 Researching: '{topic}' (depth: {depth})")
        print("=" * 80)
        
        try:
            research_results = self.research_agent.research(
                topic, 
                depth=depth, 
                additional_questions=additional_questions
            )
            
            # Display research summary
            print(f"\n✅ Research Complete!")
            print(f"📊 Questions researched: {len(research_results['research_questions'])}")
            print(f"📁 Source documents: {research_results['source_documents']}")
            print(f"📄 Key sources: {', '.join(research_results['key_sources'])}")
            
            print(f"\n📋 RESEARCH REPORT")
            print("=" * 80)
            print(research_results['report'])
            
            # Optionally save detailed report
            if save_report:
                self._save_research_report(topic, research_results)
                
            return research_results
            
        except Exception as e:
            print(f"❌ Research failed: {e}")
            return None

    def _save_research_report(self, topic: str, research_results: Dict[str, Any]):
        """Save detailed research report to file"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"research_report_{safe_topic.replace(' ', '_')}_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"RESEARCH REPORT: {topic}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Research Depth: {research_results.get('depth', 'medium')}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("EXECUTIVE SUMMARY\n")
            f.write("-" * 40 + "\n")
            f.write(research_results['report'] + "\n\n")
            
            f.write("DETAILED FINDINGS\n")
            f.write("-" * 40 + "\n")
            for i, question in enumerate(research_results['research_questions'], 1):
                answer = research_results['findings'].get(question, "No answer found")
                f.write(f"\nQ{i}: {question}\n")
                f.write(f"A{i}: {answer}\n")
                f.write("-" * 60 + "\n")
            
            f.write(f"\nSOURCE DOCUMENTS\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total documents consulted: {research_results['source_documents']}\n")
            f.write(f"Key sources: {', '.join(research_results['key_sources'])}\n")
        
        print(f"💾 Detailed report saved to: {filename}")
    
    def show_info(self, collection_name: str = "regscout_documents"):
        """Show knowledge base information"""
        if collection_name == "all":
            self.list_all_collections()
            return
            
        self.init_components(collection_name=collection_name, setup_collection=False)  # Read-only mode
        
        info = self.research_agent.get_knowledge_base_info()
        
        print("\n📊 Knowledge Base Information:")
        print(f"   📦 Collection: {info['collection_name']}")
        print(f"   🧠 Embedding Model: {info['embedding_model']}")
        print(f"   📏 Vector Dimensions: {info['embedding_dimension']}")
        
        collection_info = info.get('collection_info', {})
        if collection_info:
            doc_count = collection_info.get('points_count', 0)
            print(f"   📚 Documents Stored: {doc_count}")
        
        print(f"   💾 Storage: Local file-based")
        print()
    
    def list_all_collections(self):
        """List all available collections"""
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(path="qdrant_db")
            collections = client.get_collections()
            
            print("\n📁 Available Collections:")
            if not collections.collections:
                print("   No collections found")
            else:
                for collection in collections.collections:
                    try:
                        count = client.count(collection.name)
                        print(f"   • {collection.name} ({count.count} documents)")
                    except Exception:
                        print(f"   • {collection.name} (unable to get count)")
        except Exception as e:
            print(f"❌ Error listing collections: {e}")
    
    def clear_knowledge_base(self, collection_name: str = "regscout_documents"):
        """Clear the knowledge base"""
        self.init_components(collection_name=collection_name, setup_collection=False)  # Read-only mode
        
        # Get current info
        info = self.research_agent.get_knowledge_base_info()
        collection_info = info.get('collection_info', {})
        doc_count = collection_info.get('points_count', 0)
        
        collection_display = collection_name or info['collection_name']
        
        if doc_count == 0:
            print(f"📭 Collection '{collection_display}' is already empty")
            return
        
        print(f"⚠️  This will delete {doc_count} document(s) from collection '{collection_display}'")
        response = input("Continue? (y/N): ")
        
        if response.lower() == 'y':
            self.vector_db.clear_documents()
            print(f"✅ Collection '{collection_display}' cleared")
        else:
            print("❌ Operation cancelled")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="RegScout CLI - Document processing and regulatory querying tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s process ordinance.pdf rules.txt          # Process specific files
  %(prog)s --collection zoning process data/        # Process to specific collection
  %(prog)s -c utilities process utilities/          # Process to utilities collection
  %(prog)s process data/                             # Process all files in directory (skip duplicates)
  %(prog)s process data/ --force                     # Process directory, including already processed files
  %(prog)s process data/ more_docs/                  # Process multiple directories
  %(prog)s search "setback requirements"            # Search for relevant content
  %(prog)s --collection zoning search "setbacks"   # Search in specific collection
  %(prog)s ask "What are the parking rules?"       # Get AI-powered answers (medium length)
  %(prog)s ask --short "What is setback?"          # Get brief answer
  %(prog)s ask --long "Explain zoning rules"       # Get comprehensive answer
  %(prog)s -c drainage ask "What are pipe requirements?" # Ask using specific collection
  %(prog)s research "stormwater management"        # Comprehensive research with report
  %(prog)s research "parking" --depth shallow      # Quick research (3 questions)
  %(prog)s research "drainage" --save               # Save detailed report to file
  %(prog)s --collection zoning research "parking"  # Research in specific collection
  %(prog)s research "setbacks" --questions "What are corner lot requirements?" "How are setbacks measured?"  # Add custom questions
  %(prog)s info                                     # Show knowledge base status
  %(prog)s --collection all info                   # Show info for all collections
  %(prog)s clear                                    # Clear all documents
  %(prog)s --collection temp clear                 # Clear specific collection

The tool uses local file storage and works offline (except for AI features).
        """
    )
    
    # Global collection argument
    parser.add_argument(
        '--collection', '-c',
        type=str,
        default=None,
        help='Specify collection name (default: regscout_documents)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process command
    process_parser = subparsers.add_parser(
        'process', 
        help='Process documents and add to knowledge base'
    )
    process_parser.add_argument(
        'files', 
        nargs='+', 
        help='Files or directories to process (supports .txt, .md, .pdf, .docx). Directories are processed recursively.'
    )
    process_parser.add_argument(
        '--force', 
        action='store_true',
        help='Force reprocessing of files even if already in knowledge base'
    )
    
    # Search command
    search_parser = subparsers.add_parser(
        'search', 
        help='Search the knowledge base'
    )
    search_parser.add_argument('question', help='Search query')
    search_parser.add_argument(
        '-k', '--top-k', 
        type=int, 
        default=5, 
        help='Number of results to return (default: 5)'
    )
    
    # Ask command
    ask_parser = subparsers.add_parser(
        'ask', 
        help='Ask AI a question with document context'
    )
    ask_parser.add_argument('question', help='Question for AI')
    
    # Response length group - mutually exclusive
    length_group = ask_parser.add_mutually_exclusive_group()
    length_group.add_argument(
        '--short', 
        action='store_const', 
        const='short', 
        dest='response_length',
        help='Short, concise answer (150 tokens)'
    )
    length_group.add_argument(
        '--medium', 
        action='store_const', 
        const='medium', 
        dest='response_length',
        help='Balanced detail level (500 tokens) [default]'
    )
    length_group.add_argument(
        '--long', 
        action='store_const', 
        const='long', 
        dest='response_length',
        help='Comprehensive answer (1500 tokens)'
    )
    
    # Set default response length
    ask_parser.set_defaults(response_length='medium')
    
    # Research command
    research_parser = subparsers.add_parser(
        'research', 
        help='Conduct comprehensive research on a topic'
    )
    research_parser.add_argument('topic', help='Topic to research')
    research_parser.add_argument(
        '--depth', 
        choices=['shallow', 'medium', 'comprehensive'],
        default='medium',
        help='Research depth (default: medium)'
    )
    research_parser.add_argument(
        '--questions', 
        nargs='*',
        help='Additional research questions to include'
    )
    research_parser.add_argument(
        '--save', 
        action='store_true',
        help='Save detailed report to file'
    )
    
    # Info command
    subparsers.add_parser(
        'info', 
        help='Show knowledge base information'
    )
    
    # Clear command
    subparsers.add_parser(
        'clear', 
        help='Clear the knowledge base'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI
    cli = RegScoutCLI()
    
    # Determine collection name
    collection_name = args.collection or "regscout_documents"
    
    # Remove the global init_components call - let each method handle it
    
    try:
        if args.command == 'process':
            cli.process_files(args.files, force=args.force, collection_name=collection_name)
        elif args.command == 'search':
            cli.search_documents(args.question, args.top_k, collection_name=collection_name)
        elif args.command == 'ask':
            cli.ask_ai(args.question, args.response_length, collection_name=collection_name)
        elif args.command == 'research':
            cli.research_topic(args.topic, depth=args.depth, additional_questions=args.questions, save_report=args.save, collection_name=collection_name)
        elif args.command == 'info':
            cli.show_info(collection_name)
        elif args.command == 'clear':
            cli.clear_knowledge_base(collection_name)
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
