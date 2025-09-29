# Vector System

A comprehensive AI-powered document processing and search system with multiple interfaces for different use cases. The system provides three main components:

- **Vector Core CLI** (`vector-core`): Low-level vector database operations
- **Vector Agent CLI** (`vector-agent`): High-level AI-powered search and document management  
- **Vector Web Interface** (`vector-web`): Gradio-based web UI for document upload, search, and management

## Overview

The Vector System provides three specialized interfaces:

### Vector Core CLI
For **low-level vector database operations**:
- **Collection Management**: Create, delete, list, and inspect vector collections
- **Point Operations**: Insert, search, and manage vector points
- **Document Operations**: List and delete documents within collections
- **Database Configuration**: Support for both local and remote Qdrant instances

### Vector Agent CLI  
For **high-level AI-powered operations**:
- **Intelligent Search**: AI-powered semantic search across documents
- **Question Answering**: Natural language questions with context-aware responses
- **Document Management**: Complete document lifecycle with cleanup
- **Multi-Collection Operations**: Search across chunks and artifacts simultaneously

### Vector Web Interface
For **user-friendly web-based operations**:
- **Document Upload**: Drag-and-drop file upload with automatic processing
- **Interactive Search**: Real-time search with filtering by documents and tags
- **AI Chat Interface**: Natural language questions with context-aware responses
- **Document Management**: View, tag, and delete documents through the web UI
- **Collection Monitoring**: Real-time collection statistics and system information

## Vector Web Interface

The Vector Web Interface provides a user-friendly Gradio-based web application for document processing, search, and management.

### Starting the Web Interface

The web interface is available after installing the package:

```bash
# Install the package in development mode
pip install -e .

# Start the web interface (Method 1 - using entry point)
vector-web

# Start the web interface (Method 2 - using module)
python -m vector.web

# Start the web interface (Method 3 - using standalone script)
python vector_web.py
```

### Web Interface Features

#### Document Upload & Processing
- **Drag & Drop Upload**: Upload PDF, DOCX, and other document formats
- **Automatic Processing**: Documents are automatically converted and embedded
- **Real-time Feedback**: Progress indicators and status updates
- **Batch Processing**: Upload multiple files simultaneously

#### Interactive Search
- **Semantic Search**: Find relevant content using natural language queries
- **Document Filtering**: Select specific documents to search within
- **Tag-based Filtering**: Filter by document tags for focused searches
- **Result Ranking**: Results sorted by relevance with confidence scores

#### AI-Powered Q&A
- **Natural Language Questions**: Ask questions in plain English
- **Context-Aware Responses**: AI provides detailed answers with source citations
- **Response Length Control**: Choose short, medium, or long responses
- **Source Tracking**: See which documents provided the context

#### Document Management
- **Document Library**: View all processed documents with metadata
- **Tagging System**: Add and manage tags for better organization
- **Document Deletion**: Remove documents and associated data
- **Collection Statistics**: Monitor vector database usage and performance

### Web Interface Usage

#### Getting Started
1. **Start the Interface**: Run `vector-web` to launch at http://127.0.0.1:7860
2. **Upload Documents**: Use the "Upload Documents" tab to add your files
3. **Wait for Processing**: Documents are automatically processed and indexed
4. **Search or Ask**: Use the "Search" tab for finding content or "AI Chat" for questions

#### Document Upload Workflow
```bash
# 1. Start the web interface
vector-web

# 2. Navigate to http://127.0.0.1:7860
# 3. Go to "Upload Documents" tab
# 4. Drag and drop your documents
# 5. Add tags if desired
# 6. Click "Process Documents"
# 7. Wait for processing to complete
```

#### Search and Q&A Workflow
```bash
# 1. Use "Search" tab for finding relevant documents
#    - Enter your search query
#    - Select documents to search (optional)
#    - Filter by tags (optional)
#    - Review search results

# 2. Use "AI Chat" tab for questions
#    - Ask questions in natural language
#    - Select response length
#    - Choose document scope
#    - Get detailed answers with sources
```

## Vector Agent CLI

The Vector Agent CLI provides high-level, AI-powered operations for document management and intelligent search.

### Installation

The agent CLI is available after installing the package:

```bash
# Install the package in development mode
pip install -e .

# Use the agent CLI
vector-agent [command] [options]
# OR
python -m vector.agent [command] [options]
```

### Agent Commands Reference

#### Ask Questions
Get AI-powered answers with relevant context from your document collections.

```bash
python -m vector.agent ask "your question" [options]
```

**Options:**
- `--chunks-collection`: Chunks collection name (default: "chunks")
- `--artifacts-collection`: Artifacts collection name (default: "artifacts") 
- `--type`: Search type - `chunks`, `artifacts`, or `both` (default: "both")
- `--length`: Response length - `short`, `medium`, or `long` (default: "medium")
- `--top-k`: Number of context results (default: 20)
- `--verbose`: Enable detailed output

**Examples:**
```bash
# Basic question with default settings
python -m vector.agent ask "What are the parking requirements for commercial buildings?"

# Focused search on chunks only
python -m vector.agent ask "zoning regulations" --type chunks --length short

# Detailed search with verbose output
python -m vector.agent ask "building permits" --type both --length long --top-k 30 --verbose
```

#### Search Documents
Perform semantic search across document collections without AI processing.

```bash
python -m vector.agent search "search query" [options]
```

**Options:**
- `--chunks-collection`: Chunks collection name (default: "chunks")
- `--artifacts-collection`: Artifacts collection name (default: "artifacts")
- `--type`: Search type - `chunks`, `artifacts`, or `both` (default: "both")
- `--top-k`: Number of results to return (default: 5)
- `--verbose`: Enable detailed output

**Examples:**
```bash
# Search both chunks and artifacts
python -m vector.agent search "drainage requirements" --top-k 10

# Search only document chunks
python -m vector.agent search "setback requirements" --type chunks

# Search with verbose output
python -m vector.agent search "parking standards" --type both --verbose
```

#### Delete Documents
**NEW FEATURE** - Delete documents and all associated data (vectors, files, registry entries).

```bash
python -m vector.agent delete [options]
```

**Options (mutually exclusive):**
- `--document-id`: Document ID to delete
- `--name`: Document display name to delete

**Additional Options:**
- `--no-cleanup`: Don't delete saved files, only remove vector data
- `--force`: Skip confirmation prompt

**Examples:**
```bash
# Delete by document ID with confirmation
python -m vector.agent delete --document-id abc123

# Delete by document name without confirmation
python -m vector.agent delete --name "Planning Ordinance 2024" --force

# Delete only vector data, preserve saved files
python -m vector.agent delete --document-id xyz789 --no-cleanup

# Interactive deletion with name matching
python -m vector.agent delete --name "Zoning Code"
```

**What Gets Deleted:**
- All vector embeddings (chunks and artifacts) from collections
- Document registry entry
- Saved document files and artifacts (unless `--no-cleanup` is used)
- Generated thumbnails and converted documents

**Safety Features:**
- Confirmation prompt (unless `--force` is used)
- Validation that document exists before deletion
- Clear error messages for ambiguous names
- Complete transaction - either all data is deleted or operation fails

#### Collection Information
View details about your vector collections.

```bash
python -m vector.agent collection-info [options]
```

**Options:**
- `--chunks-collection`: Chunks collection name (default: "chunks")
- `--artifacts-collection`: Artifacts collection name (default: "artifacts")

**Example:**
```bash
python -m vector.agent collection-info
```

#### Model Information
Display AI model configuration and settings.

```bash
python -m vector.agent model-info [options]
```

**Options:**
- `--chunks-collection`: Chunks collection name (default: "chunks")
- `--artifacts-collection`: Artifacts collection name (default: "artifacts")

**Example:**
```bash
python -m vector.agent model-info
```

### Agent Usage Patterns

#### Document Management Workflow

```bash
# 1. Process documents (using pipeline)
python -m vector.core pipeline process document.pdf

# 2. Verify document was processed
python -m vector.agent collection-info

# 3. Search the processed content
python -m vector.agent search "specific topic" --verbose

# 4. Ask questions about the content
python -m vector.agent ask "What does the document say about X?"

# 5. Clean up when no longer needed
python -m vector.agent delete --name "document" --force
```

#### Research and Analysis Workflow

```bash
# 1. Search for relevant information
python -m vector.agent search "building codes" --type both --top-k 20

# 2. Ask specific questions
python -m vector.agent ask "What are the height restrictions?" --length long

# 3. Get detailed context with sources
python -m vector.agent ask "parking requirements" --verbose

# 4. Search within specific document types
python -m vector.agent search "zoning" --type artifacts --top-k 10
```

#### Data Maintenance Workflow

```bash
# 1. Check current collections
python -m vector.agent collection-info

# 2. Review model configuration
python -m vector.agent model-info

# 3. Clean up old documents
python -m vector.agent delete --name "outdated document" --force

# 4. Verify cleanup
python -m vector.agent collection-info
```

## Vector Core CLI

The Vector Core CLI handles low-level vector database operations and direct collection management.

### Installation

```bash
# Install the package in development mode
pip install -e .

# Use the installed command
vector-core [command] [options]
# OR
python -m vector.core [command] [options]
```

### Configuration

#### Global Options

Available for all commands:

- `--db-path`: Path to Qdrant database directory (default: `./qdrant_db`)
- `--url`: URL for remote Qdrant instance
- `--api-key`: API key for remote Qdrant instance

### Usage Patterns

**Local Database:**
```bash
vector-core [command] --db-path ./my_qdrant_db
```

**Remote Database:**
```bash
vector-core [command] --url https://my-qdrant.example.com --api-key your_api_key
```

## Commands Reference

### Collection Management

#### Create Collection
Create a new vector collection with specified parameters.

```bash
vector-core create-collection <name> [options]
```

**Options:**
- `--vector-size`: Vector dimension size (default: 384)
- `--distance`: Distance metric - `cosine`, `euclid`, or `dot` (default: cosine)

**Examples:**
```bash
# Basic collection with default settings
vector-core create-collection my_documents

# Custom vector size and distance metric
vector-core create-collection embeddings_768 --vector-size 768 --distance cosine

# Collection for sentence transformers
vector-core create-collection sentence_embeddings --vector-size 384 --distance cosine

# Collection for OpenAI embeddings
vector-core create-collection openai_embeddings --vector-size 1536 --distance cosine
```

#### Delete Collection
Remove a collection and all its data.

```bash
vector-core delete-collection <name> [--force]
```

**Options:**
- `--force`: Skip confirmation prompt

**Examples:**
```bash
# Interactive deletion with confirmation
vector-core delete-collection old_collection

# Force deletion without confirmation
vector-core delete-collection temp_collection --force
```

#### List Collections
Display all available collections in the database.

```bash
vector-core list-collections
```

**Example Output:**
```
Collections:
  * document_chunks
  * document_artifacts
  * user_queries
  * embeddings_test
```

#### Collection Information
Get detailed information about a specific collection.

```bash
vector-core collection-info <collection_name>
```

**Example:**
```bash
vector-core collection-info document_chunks
```

**Example Output:**
```
Collection 'document_chunks' information:
  * Status: green
  * Vector size: 384
  * Distance: Cosine
  * Points count: 1,247
```

### Point Operations

#### Insert Point
Add a vector point to a collection with optional payload data.

```bash
vector-core insert-point <collection> <point_id> <vector> [--payload JSON]
```

**Parameters:**
- `collection`: Target collection name
- `point_id`: Unique identifier for the point
- `vector`: JSON array of floats representing the vector
- `--payload`: Optional JSON payload with metadata

**Examples:**
```bash
# Basic point insertion
vector-core insert-point my_collection point_1 '[0.1, 0.2, 0.3, 0.4]'

# Point with metadata payload
vector-core insert-point documents doc_123 '[0.15, 0.25, 0.35, 0.45]' --payload '{"title": "Sample Document", "type": "article", "author": "John Doe"}'

# Document chunk with rich metadata
vector-core insert-point chunks chunk_456 '[0.2, 0.3, 0.4, 0.5]' --payload '{"document_id": "doc_123", "chunk_number": 1, "text": "This is a sample text chunk", "page": 1}'

# Image embedding with visual metadata
vector-core insert-point images img_789 '[0.1, 0.4, 0.2, 0.6]' --payload '{"document_id": "doc_123", "type": "diagram", "caption": "System Architecture", "page": 5}'
```

#### Search Vectors
Find similar vectors in a collection using cosine similarity or other distance metrics.

```bash
vector-core search <collection> <query_vector> [options]
```

**Options:**
- `--top-k`: Number of results to return (default: 5)
- `--document-ids`: JSON array of document IDs to filter results

**Examples:**
```bash
# Basic similarity search
vector-core search documents '[0.1, 0.2, 0.3, 0.4]'

# Search with more results
vector-core search documents '[0.1, 0.2, 0.3, 0.4]' --top-k 10

# Search within specific documents
vector-core search chunks '[0.15, 0.25, 0.35, 0.45]' --document-ids '["doc_123", "doc_456", "doc_789"]'

# Find similar chunks with detailed results
vector-core search document_chunks '[0.2, 0.3, 0.4, 0.5]' --top-k 3
```

**Example Output:**
```
Search results for collection 'documents':
  1. ID: doc_456, Score: 0.8945
     Payload: {
       "title": "Related Article",
       "type": "article",
       "relevance": "high"
     }
  2. ID: doc_789, Score: 0.8123
     Payload: {
       "title": "Another Document",
       "type": "manual"
     }
```

### Document Operations

#### List Documents
Show all unique documents in a collection.

```bash
vector-core list-documents <collection>
```

**Examples:**
```bash
# List all documents in a collection
vector-core list-documents document_chunks

# Check documents in artifacts collection
vector-core list-documents document_artifacts
```

**Example Output:**
```
Documents in collection 'document_chunks':
  * doc_123
  * doc_456
  * doc_789
  * user_manual_001
  * technical_spec_v2

Total: 5 documents
```

#### Delete Document
Remove all points associated with a specific document ID.

```bash
vector-core delete-document <collection> <document_id> [--force]
```

**Options:**
- `--force`: Skip confirmation prompt

**Examples:**
```bash
# Interactive document deletion
vector-core delete-document chunks doc_123

# Force deletion without confirmation
vector-core delete-document artifacts old_doc_456 --force
```

## Complete Workflow Examples

### Document Processing Pipeline

```bash
# 1. Create collections for a new document set
vector-core create-collection legal_docs_chunks --vector-size 384
vector-core create-collection legal_docs_artifacts --vector-size 384

# 2. Verify collections were created
vector-core list-collections

# 3. Check collection details
vector-core collection-info legal_docs_chunks

# 4. Process and insert document chunks (example with sample data)
vector-core insert-point legal_docs_chunks chunk_001 '[0.1, 0.2, ...]' --payload '{"document_id": "ordinance_123", "page": 1, "section": "Zoning Requirements"}'

# 5. Insert document artifacts (tables, images)
vector-core insert-point legal_docs_artifacts artifact_001 '[0.3, 0.4, ...]' --payload '{"document_id": "ordinance_123", "type": "table", "caption": "Setback Requirements"}'

# 6. Search for relevant content
vector-core search legal_docs_chunks '[0.15, 0.25, ...]' --top-k 5

# 7. List all processed documents
vector-core list-documents legal_docs_chunks

# 8. Clean up if needed
vector-core delete-document legal_docs_chunks old_ordinance_456 --force
```

### Multi-Collection Search Workflow

```bash
# Search across different collection types
vector-core search document_chunks '[0.1, 0.2, 0.3, 0.4]' --top-k 3
vector-core search document_artifacts '[0.1, 0.2, 0.3, 0.4]' --top-k 3

# Filter search by specific documents
vector-core search all_documents '[0.2, 0.3, 0.4, 0.5]' --document-ids '["important_doc", "reference_manual"]'
```

### Database Maintenance

```bash
# 1. List all collections to see current state
vector-core list-collections

# 2. Get information about each collection
vector-core collection-info collection_name

# 3. Check document counts
vector-core list-documents collection_name

# 4. Clean up old collections
vector-core delete-collection temp_collection --force

# 5. Verify cleanup
vector-core list-collections
```

## Advanced Usage Patterns

### Batch Operations

For batch operations, you can create shell scripts:

**Windows PowerShell:**
```powershell
# create_test_collections.ps1
$collections = @("docs_v1", "docs_v2", "docs_v3")
foreach ($collection in $collections) {
    vector-core create-collection $collection --vector-size 768
}
```

**Unix/Linux Bash:**
```bash
#!/bin/bash
# create_test_collections.sh
collections=("docs_v1" "docs_v2" "docs_v3")
for collection in "${collections[@]}"; do
    vector-core create-collection "$collection" --vector-size 768
done
```

### Integration with Data Processing

```python
# Example Python script integrating CLI operations
import subprocess
import json

def run_cli_command(args):
    """Execute a CLI command and return results."""
    cmd = ["vector-core"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr

# Create a collection
success, output, error = run_cli_command([
    "create-collection", "processed_docs", "--vector-size", "384"
])

if success:
    print("Collection created successfully")
    
    # Insert processed embeddings
    for doc_id, embedding, metadata in processed_documents:
        run_cli_command([
            "insert-point", "processed_docs", doc_id, 
            json.dumps(embedding), "--payload", json.dumps(metadata)
        ])
```

## Error Handling

The CLI provides comprehensive error handling with clear messages:

### Common Error Scenarios

**Invalid JSON:**
```bash
vector-core insert-point test invalid_id '[0.1, 0.2, invalid]'
# Output: [ERROR] JSON parsing error: Expecting value: line 1 column 15 (char 14)
```

**Collection Not Found:**
```bash
vector-core search nonexistent_collection '[0.1, 0.2]'
# Output: [ERROR] Collection 'nonexistent_collection' does not exist
```

**Vector Dimension Mismatch:**
```bash
# Collection expects 384 dimensions, but vector has 3
vector-core insert-point my_collection point1 '[0.1, 0.2, 0.3]'
# Output: [ERROR] Error inserting point: Vector dimension mismatch
```

**Database Connection Issues:**
```bash
vector-core list-collections --url http://invalid-url
# Output: [ERROR] Connection failed: Unable to connect to database
```

### Exit Codes

- `0`: Success
- `1`: Error occurred (invalid arguments, database errors, etc.)

## Performance Considerations

### Vector Sizes and Performance

- **Small vectors (≤ 384 dimensions)**: Fast insertion and search
- **Medium vectors (384-768 dimensions)**: Good balance of performance and accuracy
- **Large vectors (≥ 1536 dimensions)**: Higher accuracy but slower operations

### Database Size Guidelines

- **Local development**: Up to 100K points per collection
- **Production usage**: Millions of points with proper indexing
- **Memory usage**: ~4 bytes per dimension per point

### Optimization Tips

1. **Use appropriate vector sizes** for your use case
2. **Batch insert operations** when possible
3. **Use filters** to limit search scope
4. **Monitor collection sizes** with `collection-info`
5. **Clean up unused documents** regularly

## Troubleshooting

### Common Issues

**Command not recognized:**
```bash
# Ensure the package is installed correctly
pip install -e .
vector-core --help
```

**Import errors:**
```bash
# Check Python path and dependencies
python -c "import vector.core.vector_store"
pip install -e .
```

**Permission errors:**
```bash
# Check database directory permissions
ls -la ./qdrant_db/
# Ensure write access to database directory
```

**Memory issues with large vectors:**
```bash
# Use smaller batch sizes
# Monitor system memory usage
# Consider using remote Qdrant instance
```

## System Integration and Workflows

The Vector System's three components work together to provide a complete document management solution:

### Complete Document Lifecycle

```bash
# 1. Set up collections (Core CLI)
vector-core create-collection documents_chunks --vector-size 384
vector-core create-collection documents_artifacts --vector-size 384

# 2. Verify setup (Core CLI)
vector-core list-collections
vector-core collection-info documents_chunks

# 3. Process documents (Web Interface - preferred) 
# OR use Pipeline programmatically
vector-web  # Upload documents via web interface

# 4. Search and analyze (Agent CLI)
vector-agent search "building codes" --type both --verbose
vector-agent ask "What are the parking requirements?" --length medium

# 5. Document cleanup (Agent CLI)
vector-agent delete --name "outdated document" --force

# 6. Verify cleanup (Agent CLI)
vector-agent collection-info
```

### Mixed Operations Example

```bash
# Use Core CLI for collection management
vector-core create-collection legal_docs --vector-size 1536

# Use Web Interface for document upload and processing
vector-web  # Upload documents via web interface

# Use Agent CLI for intelligent operations  
vector-agent ask "zoning requirements" --chunks-collection legal_docs

# Use Core CLI for low-level inspection
vector-core list-documents legal_docs
vector-core collection-info legal_docs

# Use Agent CLI for complete document removal
vector-agent delete --document-id doc123 --no-cleanup
```

### When to Use Each Interface

**Use Vector Web Interface (`vector-web`) for:**
- Document upload and processing
- Interactive search and exploration
- Natural language questions with immediate feedback
- Document management and organization
- Users who prefer GUI over command line
- Demonstrations and presentations

**Use Vector Core CLI (`vector-core`) for:**
- Creating and configuring collections
- Low-level vector operations
- Direct point insertion and search
- Database administration
- Debugging vector operations
- Automation and scripting

**Use Vector Agent CLI (`vector-agent`) for:**
- Intelligent document search from command line
- Natural language questions in scripts
- Complete document management including deletion
- AI-powered analysis in batch processes
- Integration with other command-line tools

## Contributing

When extending the Vector System:

**For Vector Web Interface:**
1. Add new components to `vector/web/components.py`
2. Update handlers in `vector/web/handlers.py`
3. Modify the main app in `vector/web/main.py`
4. Update web service in `vector/web/service.py`
5. Update this README with new functionality

**For Vector Core CLI:**
1. Add new commands to `vector/core/cli.py`
2. Update argument parser in `setup_parser()`
3. Add command handlers to the `VectorStoreCLI` class
4. Update this README with new command documentation

**For Vector Agent CLI:**
1. Add new commands to `vector/agent/cli.py`
2. Update argument parser in `main()` function
3. Add command handlers in the main command routing
4. Import required modules as needed (prefer lazy imports)
5. Update this README with new command documentation

**General Guidelines:**
- Add tests to verify functionality
- Follow existing error handling patterns
- Use consistent help text formatting
- Consider all three interfaces for feature parity where appropriate
- Update entry points in `pyproject.toml` if adding new CLI commands

## Support

For issues and questions:
- Check the error messages for guidance
- Verify database connectivity with `list-collections`
- Use `--help` for command-specific information
- Test with simple operations first

## Recent Updates

### Vector System Refactor (v2.0.0)
Major refactor with new architecture and features:

- **Three-Interface Architecture**: Web UI, Agent CLI, and Core CLI for different use cases
- **Web Interface**: New Gradio-based web application for document management
- **Improved CLI Structure**: Separate entry points for core and agent operations
- **Enhanced Document Processing**: Better pipeline with automatic processing
- **Tag Management**: Document tagging and filtering capabilities
- **Real-time Updates**: Live collection statistics and document management

### Document Delete Functionality
The Vector Agent CLI includes comprehensive document deletion capabilities:

- **Delete by ID**: `vector-agent delete --document-id abc123`
- **Delete by Name**: `vector-agent delete --name "Document Name"`
- **Safety Features**: Confirmation prompts and `--force` option
- **Flexible Cleanup**: `--no-cleanup` to preserve files while removing vectors
- **Complete Removal**: Deletes vectors, registry entries, and saved files
- **Error Handling**: Clear messages for missing or ambiguous documents

## Examples and Testing

The `tests/` directory contains comprehensive examples of all functionality:

- **CLI Tests**: `test_cli.py` - Examples of both Core and Agent CLI usage
- **Pipeline Tests**: `test_pipeline_run.py` - Document processing workflows
- **Search Tests**: `test_search_handler.py` - Search functionality examples
- **Deletion Tests**: `test_delete_command.py` - Document cleanup examples

These test files serve as reference implementations for integration patterns and can help understand the complete system capabilities.