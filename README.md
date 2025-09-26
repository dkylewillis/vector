# Vector CLI System

A comprehensive command-line interface system for managing vector databases and AI-powered document operations. The system provides two complementary CLIs:

- **Vector Core CLI** (`vector-core`): Low-level vector database operations
- **Vector Agent CLI** (`vector-agent`): High-level AI-powered search and document management

## Overview

The Vector CLI System provides two specialized interfaces:

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

## Vector Agent CLI

The Vector Agent CLI provides high-level, AI-powered operations for document management and intelligent search.

### Installation

The agent CLI is available after installing the package:

```bash
# Install the package in development mode
pip install -e .

# Use the agent CLI
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

### Option 1: Package Installation
```bash
# Install the package in development mode
pip install -e .

# Use the installed command
vector-core [command] [options]
```

### Option 2: Direct Script Execution
```bash
# Use the standalone runner script
python vector_cli.py [command] [options]
```

### Dependencies
The CLI uses only Python standard library modules:
- `argparse` - Command-line argument parsing
- `json` - JSON data handling
- `sys` - System interface
- Plus the existing vector core modules

### Configuration

### Global Options

Available for all commands:

- `--db-path`: Path to Qdrant database directory (default: `./qdrant_db`)
- `--url`: URL for remote Qdrant instance
- `--api-key`: API key for remote Qdrant instance

### Usage Patterns

**Local Database:**
```bash
python vector_cli.py [command] --db-path ./my_qdrant_db
```

**Remote Database:**
```bash
python vector_cli.py [command] --url https://my-qdrant.example.com --api-key your_api_key
```

## Commands Reference

### Collection Management

#### Create Collection
Create a new vector collection with specified parameters.

```bash
python vector_cli.py create-collection <name> [options]
```

**Options:**
- `--vector-size`: Vector dimension size (default: 384)
- `--distance`: Distance metric - `cosine`, `euclid`, or `dot` (default: cosine)

**Examples:**
```bash
# Basic collection with default settings
python vector_cli.py create-collection my_documents

# Custom vector size and distance metric
python vector_cli.py create-collection embeddings_768 --vector-size 768 --distance cosine

# Collection for sentence transformers
python vector_cli.py create-collection sentence_embeddings --vector-size 384 --distance cosine

# Collection for OpenAI embeddings
python vector_cli.py create-collection openai_embeddings --vector-size 1536 --distance cosine
```

#### Delete Collection
Remove a collection and all its data.

```bash
python vector_cli.py delete-collection <name> [--force]
```

**Options:**
- `--force`: Skip confirmation prompt

**Examples:**
```bash
# Interactive deletion with confirmation
python vector_cli.py delete-collection old_collection

# Force deletion without confirmation
python vector_cli.py delete-collection temp_collection --force
```

#### List Collections
Display all available collections in the database.

```bash
python vector_cli.py list-collections
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
python vector_cli.py collection-info <collection_name>
```

**Example:**
```bash
python vector_cli.py collection-info document_chunks
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
python vector_cli.py insert-point <collection> <point_id> <vector> [--payload JSON]
```

**Parameters:**
- `collection`: Target collection name
- `point_id`: Unique identifier for the point
- `vector`: JSON array of floats representing the vector
- `--payload`: Optional JSON payload with metadata

**Examples:**
```bash
# Basic point insertion
python vector_cli.py insert-point my_collection point_1 '[0.1, 0.2, 0.3, 0.4]'

# Point with metadata payload
python vector_cli.py insert-point documents doc_123 '[0.15, 0.25, 0.35, 0.45]' --payload '{"title": "Sample Document", "type": "article", "author": "John Doe"}'

# Document chunk with rich metadata
python vector_cli.py insert-point chunks chunk_456 '[0.2, 0.3, 0.4, 0.5]' --payload '{"document_id": "doc_123", "chunk_number": 1, "text": "This is a sample text chunk", "page": 1}'

# Image embedding with visual metadata
python vector_cli.py insert-point images img_789 '[0.1, 0.4, 0.2, 0.6]' --payload '{"document_id": "doc_123", "type": "diagram", "caption": "System Architecture", "page": 5}'
```

#### Search Vectors
Find similar vectors in a collection using cosine similarity or other distance metrics.

```bash
python vector_cli.py search <collection> <query_vector> [options]
```

**Options:**
- `--top-k`: Number of results to return (default: 5)
- `--document-ids`: JSON array of document IDs to filter results

**Examples:**
```bash
# Basic similarity search
python vector_cli.py search documents '[0.1, 0.2, 0.3, 0.4]'

# Search with more results
python vector_cli.py search documents '[0.1, 0.2, 0.3, 0.4]' --top-k 10

# Search within specific documents
python vector_cli.py search chunks '[0.15, 0.25, 0.35, 0.45]' --document-ids '["doc_123", "doc_456", "doc_789"]'

# Find similar chunks with detailed results
python vector_cli.py search document_chunks '[0.2, 0.3, 0.4, 0.5]' --top-k 3
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
python vector_cli.py list-documents <collection>
```

**Examples:**
```bash
# List all documents in a collection
python vector_cli.py list-documents document_chunks

# Check documents in artifacts collection
python vector_cli.py list-documents document_artifacts
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
python vector_cli.py delete-document <collection> <document_id> [--force]
```

**Options:**
- `--force`: Skip confirmation prompt

**Examples:**
```bash
# Interactive document deletion
python vector_cli.py delete-document chunks doc_123

# Force deletion without confirmation
python vector_cli.py delete-document artifacts old_doc_456 --force
```

## Complete Workflow Examples

### Document Processing Pipeline

```bash
# 1. Create collections for a new document set
python vector_cli.py create-collection legal_docs_chunks --vector-size 384
python vector_cli.py create-collection legal_docs_artifacts --vector-size 384

# 2. Verify collections were created
python vector_cli.py list-collections

# 3. Check collection details
python vector_cli.py collection-info legal_docs_chunks

# 4. Process and insert document chunks (example with sample data)
python vector_cli.py insert-point legal_docs_chunks chunk_001 '[0.1, 0.2, ...]' --payload '{"document_id": "ordinance_123", "page": 1, "section": "Zoning Requirements"}'

# 5. Insert document artifacts (tables, images)
python vector_cli.py insert-point legal_docs_artifacts artifact_001 '[0.3, 0.4, ...]' --payload '{"document_id": "ordinance_123", "type": "table", "caption": "Setback Requirements"}'

# 6. Search for relevant content
python vector_cli.py search legal_docs_chunks '[0.15, 0.25, ...]' --top-k 5

# 7. List all processed documents
python vector_cli.py list-documents legal_docs_chunks

# 8. Clean up if needed
python vector_cli.py delete-document legal_docs_chunks old_ordinance_456 --force
```

### Multi-Collection Search Workflow

```bash
# Search across different collection types
python vector_cli.py search document_chunks '[0.1, 0.2, 0.3, 0.4]' --top-k 3
python vector_cli.py search document_artifacts '[0.1, 0.2, 0.3, 0.4]' --top-k 3

# Filter search by specific documents
python vector_cli.py search all_documents '[0.2, 0.3, 0.4, 0.5]' --document-ids '["important_doc", "reference_manual"]'
```

### Database Maintenance

```bash
# 1. List all collections to see current state
python vector_cli.py list-collections

# 2. Get information about each collection
python vector_cli.py collection-info collection_name

# 3. Check document counts
python vector_cli.py list-documents collection_name

# 4. Clean up old collections
python vector_cli.py delete-collection temp_collection --force

# 5. Verify cleanup
python vector_cli.py list-collections
```

## Advanced Usage Patterns

### Batch Operations

For batch operations, you can create shell scripts:

**Windows PowerShell:**
```powershell
# create_test_collections.ps1
$collections = @("docs_v1", "docs_v2", "docs_v3")
foreach ($collection in $collections) {
    python vector_cli.py create-collection $collection --vector-size 768
}
```

**Unix/Linux Bash:**
```bash
#!/bin/bash
# create_test_collections.sh
collections=("docs_v1" "docs_v2" "docs_v3")
for collection in "${collections[@]}"; do
    python vector_cli.py create-collection "$collection" --vector-size 768
done
```

### Integration with Data Processing

```python
# Example Python script integrating CLI operations
import subprocess
import json

def run_cli_command(args):
    """Execute a CLI command and return results."""
    cmd = ["python", "vector_cli.py"] + args
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
python vector_cli.py insert-point test invalid_id '[0.1, 0.2, invalid]'
# Output: [ERROR] JSON parsing error: Expecting value: line 1 column 15 (char 14)
```

**Collection Not Found:**
```bash
python vector_cli.py search nonexistent_collection '[0.1, 0.2]'
# Output: [ERROR] Collection 'nonexistent_collection' does not exist
```

**Vector Dimension Mismatch:**
```bash
# Collection expects 384 dimensions, but vector has 3
python vector_cli.py insert-point my_collection point1 '[0.1, 0.2, 0.3]'
# Output: [ERROR] Error inserting point: Vector dimension mismatch
```

**Database Connection Issues:**
```bash
python vector_cli.py list-collections --url http://invalid-url
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
# Ensure you're in the correct directory
cd /path/to/vector/project
python vector_cli.py --help
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

## CLI Integration and Workflows

The Vector Core CLI and Vector Agent CLI work together to provide a complete document management solution:

### Complete Document Lifecycle

```bash
# 1. Set up collections (Core CLI)
python vector_cli.py create-collection documents_chunks --vector-size 384
python vector_cli.py create-collection documents_artifacts --vector-size 384

# 2. Verify setup (Core CLI)
python vector_cli.py list-collections
python vector_cli.py collection-info documents_chunks

# 3. Process documents (Pipeline - not CLI, but part of workflow)
# Documents get processed and stored in collections

# 4. Search and analyze (Agent CLI)
python -m vector.agent search "building codes" --type both --verbose
python -m vector.agent ask "What are the parking requirements?" --length medium

# 5. Document cleanup (Agent CLI) - NEW DELETE FUNCTIONALITY
python -m vector.agent delete --name "outdated document" --force

# 6. Verify cleanup (Agent CLI)
python -m vector.agent collection-info
```

### Mixed Operations Example

```bash
# Use Core CLI for collection management
python vector_cli.py create-collection legal_docs --vector-size 1536

# Use Agent CLI for intelligent operations  
python -m vector.agent ask "zoning requirements" --chunks-collection legal_docs

# Use Core CLI for low-level inspection
python vector_cli.py list-documents legal_docs
python vector_cli.py collection-info legal_docs

# Use Agent CLI for complete document removal (NEW)
python -m vector.agent delete --document-id doc123 --no-cleanup
```

### When to Use Each CLI

**Use Vector Core CLI (`vector-core` or `vector_cli.py`) for:**
- Creating and configuring collections
- Low-level vector operations
- Direct point insertion and search
- Database administration
- Debugging vector operations

**Use Vector Agent CLI (`python -m vector.agent`) for:**
- Intelligent document search
- Natural language questions
- Complete document management (including NEW delete functionality)
- AI-powered analysis
- High-level document operations

## Contributing

When extending the CLI system:

**For Vector Core CLI:**
1. Add new commands to `vector/cli/commands.py`
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
- Consider both interactive and scripted usage

## Support

For issues and questions:
- Check the error messages for guidance
- Verify database connectivity with `list-collections`
- Use `--help` for command-specific information
- Test with simple operations first

## Recent Updates

### Document Delete Functionality (NEW)
The Vector Agent CLI now includes comprehensive document deletion capabilities:

- **Delete by ID**: `python -m vector.agent delete --document-id abc123`
- **Delete by Name**: `python -m vector.agent delete --name "Document Name"`
- **Safety Features**: Confirmation prompts and `--force` option
- **Flexible Cleanup**: `--no-cleanup` to preserve files while removing vectors
- **Complete Removal**: Deletes vectors, registry entries, and saved files
- **Error Handling**: Clear messages for missing or ambiguous documents

This feature provides a complete document lifecycle management solution when combined with the existing pipeline processing capabilities.

## Examples Repository

The `test_cli.py` script provides comprehensive examples of all CLI functionality and can serve as a reference for integration patterns.