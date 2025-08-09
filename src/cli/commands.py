"""CLI command implementations for RegScout."""

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

from ..agents.research_agent import ResearchAgent
from ..data_pipeline.file_processing import FileProcessor
from config import Config


class RegScoutCommands:
    """All RegScout CLI command implementations."""
    
    def __init__(self, config: Config):
        self.config = config
        self.research_agent = None
        self.vector_db = None
        self.embedder = None
        self.file_processor = None

    def init_components(self, collection_name: str = "regscout_chunks",
                        setup_collection: bool = True):
        """Initialize research agent and components."""
        # Check if we need to reinitialize with a different collection
        if (self.research_agent is not None and 
            hasattr(self.research_agent, 'collection_name') and
            self.research_agent.collection_name == collection_name):
            return  # Same collection, no need to reinitialize

        print(f"🔧 Initializing RegScout with collection '{collection_name}'...")
        self.research_agent = ResearchAgent(
            config=self.config,
            collection_name=collection_name
        )
        self.embedder = self.research_agent.embedder
        self.vector_db = self.research_agent.vector_db

        if setup_collection:
            if not self.vector_db.collection_exists():
                print(f"📦 Collection '{collection_name}' does not exist.")
                response = input(
                    f"Create new collection '{collection_name}'? (y/N): "
                )
                if response.lower() != 'y':
                    print("❌ Operation cancelled - collection creation "
                          "required for processing")
                    sys.exit(0)
            
            vector_size = self.research_agent.setup_collection()
            print(f"✓ Ready (embedding dimension: {vector_size})")
        else:
            print("✓ Ready (read-only mode)")

    def process(self, file_paths: List[str], force: bool = False, 
                collection_name: str = "regscout_chunks", source: str = None):
        """Process files and add to knowledge base."""
        self.init_components(collection_name=collection_name, 
                           setup_collection=True)
        self.file_processor = FileProcessor()
        
        # Expand directories to file lists
        expanded_files = self._expand_file_paths(file_paths)
        if not expanded_files:
            print("❌ No supported files found")
            return
            
        # Filter already processed files
        files_to_process = self._filter_processed_files(expanded_files, force)
        if not files_to_process:
            print("✅ All files already processed! Use --force to reprocess.")
            return
            
        # Process and add files
        self._process_and_add_files(files_to_process, source)

    def search(self, question: str, top_k: int = 5, 
               collection_name: str = "regscout_chunks",
               filename: str = None):
        """Search the knowledge base."""
        self.init_components(collection_name=collection_name, 
                           setup_collection=False)
        
        # Build metadata filter
        metadata_filter = {}
        if filename:
            metadata_filter["filename"] = filename
        
        filter_dict = metadata_filter if metadata_filter else None
        
        print(f"🔍 Searching: '{question}'" + 
              (f" (filtered by {metadata_filter})" if filter_dict else ""))
        results = self.research_agent.search(question, top_k=top_k, metadata_filter=filter_dict)
        
        if not results:
            print("❌ No results found")
            return
            
        self._display_search_results(results)

    def ask(self, question: str, response_length: str = "medium",
            collection_name: str = "regscout_chunks",
            filename: str = None):
        """Ask AI with chunk context."""
        self.init_components(collection_name=collection_name, 
                           setup_collection=False)
        
        if not os.getenv('OPENAI_API_KEY'):
            self._show_api_key_help()
            return
            
        # Build metadata filter
        metadata_filter = {}
        if filename:
            metadata_filter["filename"] = filename
        
        filter_dict = metadata_filter if metadata_filter else None
        
        print(f"🤖 AI Question: '{question}'" + 
              (f" (context filtered by {metadata_filter})" if filter_dict else ""))
        
        # Get max_tokens from config
        response_lengths = self.research_agent.config.get(
            'ai_model.response_lengths', {})
        max_tokens = response_lengths.get(
            response_length, response_lengths.get('short', 256))
        
        print(f"📏 Response length: {response_length} ({max_tokens} tokens)")
        
        try:
            print("🤔 Thinking...")
            response = self.research_agent.ask(
                question, use_context=True, max_tokens=max_tokens, metadata_filter=filter_dict)
            print(f"\n💡 AI Answer:\n{response}\n")
        except Exception as e:
            print(f"❌ AI service error: {e}")
            self._show_fallback_results(question)



    def info(self, collection_name: str = "regscout_chunks"):
        """Show knowledge base information."""
        if collection_name == "all":
            self._list_all_collections()
            return
            
        self.init_components(collection_name=collection_name, 
                           setup_collection=False)
        info = self.research_agent.get_knowledge_base_info()
        self._display_info(info)

    def clear(self, collection_name: str = "regscout_chunks"):
        """Clear knowledge base."""
        self.init_components(collection_name=collection_name, 
                           setup_collection=False)
        
        info = self.research_agent.get_knowledge_base_info()
        collection_info = info.get('collection_info', {})
        doc_count = collection_info.get('points_count', 0)
        collection_display = collection_name or info['collection_name']
        
        if doc_count == 0:
            print(f"📭 Collection '{collection_display}' is already empty")
            return
            
        print(f"⚠️  This will delete {doc_count} chunk(s) from "
              f"collection '{collection_display}'")
        if input("Continue? (y/N): ").lower() == 'y':
            self.vector_db.clear_chunks()
            print(f"✅ Collection '{collection_display}' cleared")
        else:
            print("❌ Operation cancelled")

    # Helper methods
    def _expand_file_paths(self, file_paths: List[str]) -> List[Path]:
        """Expand directories to file lists."""
        expanded_files = []
        supported_extensions = {'.txt', '.md', '.pdf', '.docx'}

        for file_path in file_paths:
            path = Path(file_path)

            if path.is_dir():
                print(f"📁 Scanning directory: {path}")
                for ext in supported_extensions:
                    found_files = list(path.rglob(f"*{ext}"))
                    expanded_files.extend(found_files)
                    if found_files:
                        print(f"   Found {len(found_files)} {ext} file(s)")
            elif path.exists():
                expanded_files.append(path)
            else:
                print(f"⚠️  File/directory not found: {file_path}")

        return sorted(set(expanded_files))
        
    def _filter_processed_files(self, files: List[Path], 
                              force: bool) -> List[Path]:
        """Filter out already processed files."""
        if force:
            return files
            
        files_to_process = []
        skipped_files = []
        
        print(f"🔍 Checking {len(files)} file(s) for duplicates...")
        for file_path in files:
            if self._is_file_already_processed(file_path):
                skipped_files.append(file_path)
            else:
                files_to_process.append(file_path)
        
        if skipped_files:
            print(f"⏭️  Skipping {len(skipped_files)} already processed file(s)")
            if len(skipped_files) <= 5:
                for file_path in skipped_files:
                    print(f"   📄 {file_path.name}")
            else:
                print(f"   📄 {skipped_files[0].name} ... and "
                      f"{len(skipped_files) - 1} more")
        
        return files_to_process
        
    def _is_file_already_processed(self, file_path: Path) -> bool:
        """Check if file already processed."""
        try:
            results = self.research_agent.search(
                f"filename:{file_path.name}",
                top_k=5,
                score_threshold=0.1
            )
            
            for result in results:
                if (result.get('metadata', {}).get('filename') == 
                        file_path.name):
                    return True
            return False
        except Exception:
            return False
        
    def _process_and_add_files(self, files: List[Path], source: str = None):
        """Process files and add to database."""
        print(f"📁 Processing {len(files)} new file(s)...")
        if source:
            print(f"🏷️  Using source category: {source}")
        
        chunks = []
        metadata = []

        for path in files:
            rel_path = (path.relative_to(Path.cwd()) 
                       if path.is_relative_to(Path.cwd()) else path)
            print(f"  📄 {rel_path}")

            try:
                content, file_metadata = self._process_single_file(path, source)
                if content:
                    if isinstance(content, list):
                        # Multiple chunks from DOCX
                        chunks.extend(content)
                        metadata.extend(file_metadata)
                    else:
                        # Single chunk
                        chunks.append(content)
                        metadata.append(file_metadata)
            except Exception as e:
                print(f"    ❌ Error processing {path.name}: {e}")

        if chunks:
            print(f"📚 Adding {len(chunks)} chunks to knowledge base...")
            embeddings = self.embedder.embed_chunks(chunks)
            chunk_ids = self.vector_db.add_chunks(
                chunks, embeddings, metadata)
            print(f"✅ Successfully added {len(chunk_ids)} chunk(s)")
        else:
            print("⚠️  No chunks were processed")
            
    def _process_single_file(self, path: Path, source: str = None):
        """Process a single file and return content and metadata."""
        if path.suffix.lower() == '.pdf' and self.file_processor:
            try:
                chunks = self.file_processor.process_pdf(path, source)
                if chunks and len(chunks) > 0:
                    print(f"    ✓ Extracted {len(chunks)} chunks")
                    documents = []
                    metadatas = []
                    
                    for i, chunk in enumerate(chunks):
                        chunk_text = self._extract_chunk_text(chunk)
                        chunk_meta = self._extract_chunk_meta(chunk)
                        
                        # Use source from file processor (which handles the logic)
                        processed_source = chunk_meta.get('source', 'other')
                        
                        documents.append(chunk_text)
                        metadatas.append({
                            'filename': path.name,
                            'file_type': 'pdf',
                            'source_path': str(path),
                            'source': processed_source,
                            'chunk_index': i,
                            'total_chunks': len(chunks),
                            'headings': chunk_meta.get('headings', []),
                        })
                    
                    return documents, metadatas
                else:
                    content = f"PDF Document: {path.name}\n[No content extracted]"
            except Exception as e:
                print(f"    ⚠️  PDF processing failed: {e}")
                content = f"PDF Document: {path.name}\n[PDF processing failed: {e}]"
            
            # Extract source for fallback case
            if source:
                fallback_source = source
            else:
                folder_name = path.parent.name
                fallback_source = folder_name if folder_name in ['ordinances', 'manuals', 'checklists'] else 'other'
            
            return content, {
                'filename': path.name,
                'file_type': 'pdf',
                'source_path': str(path),
                'source': fallback_source,
            }
            
        elif path.suffix.lower() == '.docx' and self.file_processor:
            try:
                chunks = self.file_processor.process_docx(path, source)
                if chunks and len(chunks) > 0:
                    print(f"    ✓ Extracted {len(chunks)} chunks")
                    documents = []
                    metadatas = []
                    
                    for i, chunk in enumerate(chunks):
                        chunk_text = self._extract_chunk_text(chunk)
                        chunk_meta = self._extract_chunk_meta(chunk)
                        
                        # Use source from file processor (which handles the logic)
                        processed_source = chunk_meta.get('source', 'other')
                        
                        documents.append(chunk_text)
                        metadatas.append({
                            'filename': path.name,
                            'file_type': 'docx',
                            'source_path': str(path),
                            'source': processed_source,
                            'chunk_index': i,
                            'total_chunks': len(chunks),
                            'headings': chunk_meta.get('headings', []),
                        })
                    
                    return documents, metadatas
                else:
                    content = f"DOCX Document: {path.name}\n[No content extracted]"
            except Exception as e:
                print(f"    ⚠️  DOCX processing failed: {e}")
                content = f"DOCX Document: {path.name}\n[DOCX processing failed: {e}]"
            
            # Extract source for fallback case
            if source:
                fallback_source = source
            else:
                folder_name = path.parent.name
                fallback_source = folder_name if folder_name in ['ordinances', 'manuals', 'checklists'] else 'other'
            
            return content, {
                'filename': path.name,
                'file_type': 'docx',
                'source_path': str(path),
                'source': fallback_source,
            }
        else:
            # Text files or fallback
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                content = f"Document: {path.name}\n[Could not read file content]"
            
            # Extract source for fallback case
            if source:
                fallback_source = source
            else:
                folder_name = path.parent.name
                fallback_source = folder_name if folder_name in ['ordinances', 'manuals', 'checklists'] else 'other'
            
            return content, {
                'filename': path.name,
                'file_type': path.suffix.lower().lstrip('.'),
                'source_path': str(path),
                'source': fallback_source,
            }
    
    def _extract_chunk_text(self, chunk):
        """Extract text from chunk object."""
        if hasattr(chunk, 'text'):
            return chunk.text
        elif isinstance(chunk, dict):
            return chunk.get('text', chunk.get('content', str(chunk)))
        else:
            return str(chunk)
    
    def _extract_chunk_meta(self, chunk):
        """Extract metadata from chunk object."""
        if hasattr(chunk, 'meta'):
            return chunk.meta
        elif isinstance(chunk, dict):
            return chunk.get('meta', {})
        else:
            return {}
        
    def _display_search_results(self, results: List[Dict]):
        """Display formatted search results."""
        print(f"\n📋 Found {len(results)} result(s):\n")
        print("=" * 80)

        for i, result in enumerate(results, 1):
            score = result['score']
            filename = result['metadata'].get('filename', 'Unknown')
            text = result['text']
            chunk_info = ""

            if 'chunk_index' in result['metadata']:
                chunk_idx = result['metadata']['chunk_index']
                total_chunks = result['metadata'].get('total_chunks', '?')
                chunk_info = f" (chunk {chunk_idx + 1}/{total_chunks})"

            print(f"\n📄 Result {i}")
            print(f"📊 Relevance Score: {score:.4f}")
            print(f"📁 Source: {filename}{chunk_info}")
            print("-" * 60)

            # Format text with proper line wrapping
            if len(text) > 500:
                truncated = text[:500]
                last_space = truncated.rfind(' ')
                if last_space > 400:
                    truncated = truncated[:last_space]
                text_display = truncated + "..."
            else:
                text_display = text

            text_display = text_display.strip()
            text_display = re.sub(r'\s+', ' ', text_display)

            print(f"📝 Content:")
            if len(text_display) > 200:
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
        
    def _display_info(self, info: Dict):
        """Display knowledge base info."""
        print("\n📊 Knowledge Base Information:")
        print(f"   📦 Collection: {info['collection_name']}")
        print(f"   🧠 Embedding Model: {info['embedding_model']}")
        print(f"   📏 Vector Dimensions: {info['embedding_dimension']}")

        collection_info = info.get('collection_info', {})
        if collection_info:
            doc_count = collection_info.get('points_count', 0)
            print(f"   📚 Documents Stored: {doc_count}")

        print(f"   💾 Storage: {info['storage_mode']}")
        print()
        
    def _list_all_collections(self):
        """List all available collections."""
        try:
            # Use existing client if available, otherwise create one using config
            if hasattr(self, 'vector_db') and self.vector_db:
                client = self.vector_db.client
            else:
                # Create client using same config as main app
                from ..data_pipeline.vector_database import VectorDatabase
                temp_db = VectorDatabase("temp")
                client = temp_db.client
            
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
        
    def _save_research_report(self, topic: str, results: Dict):
        """Save research report to markdown file."""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(
            c for c in topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"due_diligence_report_{safe_topic.replace(' ', '_')}_{timestamp}.md"

        # Save the markdown report
        markdown_content = results.get('markdown_report', '')
        if markdown_content:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"💾 Due diligence report saved to: {filename}")
        else:
            print("❌ No markdown report found to save")
            
        # Also save a summary file with metadata
        summary_filename = f"due_diligence_summary_{safe_topic.replace(' ', '_')}_{timestamp}.txt"
        with open(summary_filename, 'w', encoding='utf-8') as f:
            f.write(f"DUE DILIGENCE REPORT SUMMARY\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Focus Topic: {topic}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write("TOPICS RESEARCHED:\n")
            for i, researched_topic in enumerate(results.get('topics_researched', []), 1):
                f.write(f"{i}. {researched_topic.replace('_', ' ').title()}\n")
            
            f.write(f"\nTOTAL ITEMS PROCESSED: {results.get('total_items', 0)}\n")
            f.write(f"REPORT TYPE: {results.get('report_type', 'Unknown')}\n")
            
            f.write(f"\nFILES GENERATED:\n")
            f.write(f"- Main Report: {filename}\n")
            f.write(f"- Summary: {summary_filename}\n")

        print(f"� Summary saved to: {summary_filename}")
        
    def _show_api_key_help(self):
        """Show API key setup instructions."""
        print("❌ OpenAI API key not found!")
        print("   Please set your API key using one of these methods:")
        print("   1. Create a .env file with: OPENAI_API_KEY=your_key_here")
        print("   2. Set environment variable: set OPENAI_API_KEY=your_key_here")
        print("   3. Add api_key to config/settings.yaml")
        print("   Get your API key from: https://platform.openai.com/api-keys")
        
    def _show_fallback_results(self, question: str):
        """Show fallback search results when AI fails."""
        context_results = self.research_agent.search(question, top_k=3)
        if context_results:
            print("\n📚 Here are the relevant documents I found:")
            for result in context_results:
                filename = result['metadata'].get('filename', 'Unknown')
                text = (result['text'][:150] + "..." 
                       if len(result['text']) > 150 else result['text'])
                print(f"  📁 {filename}: {text}")
        else:
            print("❌ No relevant documents found")

    def metadata_summary(self, collection_name: str = "regscout_chunks"):
        """Show metadata summary for a collection."""
        self.init_components(collection_name=collection_name, setup_collection=False)
        
        print(f"📊 Getting metadata summary for '{collection_name}'...")
        summary = self.research_agent.vector_db.get_metadata_summary()
        
        if "error" in summary:
            print(f"❌ {summary['error']}")
            return
        
        print(f"\n📈 Total chunks: {summary['total_chunks']}")
        
        print(f"\n📁 Files ({len(summary['filenames'])}):")
        for filename in summary['filenames']:
            print(f"  • {filename}")
        
        print(f"\n📂 Sources ({len(summary['sources'])}):")
        for source in summary['sources']:
            print(f"  • {source}")
        
        if summary['headings']:
            print(f"\n📋 Headings (first 10):")
            for heading in summary['headings'][:10]:
                print(f"  • {heading}")
            if len(summary['headings']) > 10:
                print(f"  ... and {len(summary['headings']) - 10} more")
