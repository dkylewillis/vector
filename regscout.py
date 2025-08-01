#!/usr/bin/env python3
"""
RegScout CLI - Complete command-line interface for document processing and querying
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List

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
    
    def init_components(self, collection_name: str = "regscout_documents"):
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
            
            # Setup collection
            vector_size = self.research_agent.setup_collection()
            
            print(f"✓ Ready (embedding dimension: {vector_size})")
            
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
            

    
# ...existing code...
    def process_files(self, file_paths: List[str]):
        """Process files and add them to the knowledge base"""
        self.init_components()
        self.file_processor = FileProcessor()
        
        documents = []
        metadata = []
        
        print(f"📁 Processing {len(file_paths)} file(s)...")
        
        for file_path in file_paths:
            path = Path(file_path)
            
            if not path.exists():
                print(f"⚠️  File not found: {file_path}")
                continue
            
            print(f"  📄 {path.name}")
            
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
                                
                                # Add each chunk as a separate document
                                documents.append(chunk_text)
                                metadata.append({
                                    'filename': path.name,
                                    'file_type': 'docx',
                                    'source_path': str(path),
                                    'chunk_index': i,
                                    'total_chunks': len(chunks)
                                })
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
    
    def search_documents(self, question: str, top_k: int = 5):
        """Search the knowledge base"""
        self.init_components()
        
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
    
    def ask_ai(self, question: str):
        """Ask AI a question with document context"""
        self.init_components()
        
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
        
        try:
            print("🤔 Thinking...")
            # Use the research agent's ask function directly
            response = self.research_agent.ask(question, use_context=True)
            print(f"\n💡 AI Answer:\n{response}\n")
            
            # Get the context that was used for reference
            context_results = self.research_agent.search(question, top_k=3)
            if context_results:
                print("📖 Sources used:")
                for i, result in enumerate(context_results, 1):
                    filename = result['metadata'].get('filename', 'Unknown')
                    print(f"  {i}. {filename} (relevance: {result['score']:.3f})")
            else:
                print("📖 No relevant documents found for context")
                
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
    
    def show_info(self):
        """Show knowledge base information"""
        self.init_components()
        
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
    
    def clear_knowledge_base(self):
        """Clear the knowledge base"""
        self.init_components()
        
        # Get current info
        info = self.research_agent.get_knowledge_base_info()
        collection_info = info.get('collection_info', {})
        doc_count = collection_info.get('points_count', 0)
        
        if doc_count == 0:
            print("📭 Knowledge base is already empty")
            return
        
        print(f"⚠️  This will delete {doc_count} document(s) from the knowledge base")
        response = input("Continue? (y/N): ")
        
        if response.lower() == 'y':
            self.vector_db.clear_documents()
            print("✅ Knowledge base cleared")
        else:
            print("❌ Operation cancelled")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="RegScout CLI - Document processing and regulatory querying tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s process ordinance.pdf rules.txt          # Add documents to knowledge base
  %(prog)s search "setback requirements"            # Search for relevant content
  %(prog)s ask "What are the parking rules?"       # Get AI-powered answers
  %(prog)s info                                     # Show knowledge base status
  %(prog)s clear                                    # Clear all documents

The tool uses local file storage and works offline (except for AI features).
        """
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
        help='Files to process (supports .txt, .md, .pdf, .docx)'
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
    
    try:
        if args.command == 'process':
            cli.process_files(args.files)
        elif args.command == 'search':
            cli.search_documents(args.question, args.top_k)
        elif args.command == 'ask':
            cli.ask_ai(args.question)
        elif args.command == 'info':
            cli.show_info()
        elif args.command == 'clear':
            cli.clear_knowledge_base()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
