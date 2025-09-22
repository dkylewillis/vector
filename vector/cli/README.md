# Vector Core CLI

A command-line interface for managing vector stores and performing CRUD operations on collections and documents.

## Installation

The CLI is part of the vector core module. To use it:

1. Install the package in development mode:
```bash
pip install -e .
```

2. Or use the standalone runner:
```bash
python vector_cli.py [command] [options]
```

## Usage

### Global Options

- `--db-path`: Path to Qdrant database directory (default: `./qdrant_db`)
- `--url`: URL for remote Qdrant instance
- `--api-key`: API key for remote Qdrant instance

### Commands

#### Collection Management

**Create a new collection:**
```bash
python vector_cli.py create-collection <name> [--vector-size SIZE] [--distance METRIC]
```
- `--vector-size`: Vector dimension size (default: 384)
- `--distance`: Distance metric: cosine, euclid, or dot (default: cosine)

Example:
```bash
python vector_cli.py create-collection my_collection --vector-size 768 --distance cosine
```

**Delete a collection:**
```bash
python vector_cli.py delete-collection <name> [--force]
```
- `--force`: Skip confirmation prompt

**List all collections:**
```bash
python vector_cli.py list-collections
```

**Get collection information:**
```bash
python vector_cli.py collection-info <collection_name>
```

#### Point Operations

**Insert a point:**
```bash
python vector_cli.py insert-point <collection> <point_id> <vector> [--payload JSON]
```
- `vector`: JSON array of floats, e.g., `'[0.1, 0.2, 0.3]'`
- `--payload`: JSON payload for the point

Example:
```bash
python vector_cli.py insert-point my_collection point_1 '[0.1, 0.2, 0.3, 0.4]' --payload '{"type": "example"}'
```

**Search for similar vectors:**
```bash
python vector_cli.py search <collection> <query_vector> [--top-k K] [--document-ids JSON_ARRAY]
```
- `--top-k`: Number of results to return (default: 5)
- `--document-ids`: JSON array of document IDs to filter by

Example:
```bash
python vector_cli.py search my_collection '[0.1, 0.2, 0.3, 0.4]' --top-k 10
```

#### Document Operations

**List documents in a collection:**
```bash
python vector_cli.py list-documents <collection>
```

**Delete a document:**
```bash
python vector_cli.py delete-document <collection> <document_id> [--force]
```
- `--force`: Skip confirmation prompt

## Examples

### Basic Workflow

1. **Create a collection:**
```bash
python vector_cli.py create-collection test_collection --vector-size 128
```

2. **Check collection info:**
```bash
python vector_cli.py collection-info test_collection
```

3. **Insert some points:**
```bash
python vector_cli.py insert-point test_collection 1 '[0.1, 0.2, 0.3, ...]' --payload '{"type": "test"}'
python vector_cli.py insert-point test_collection 2 '[0.4, 0.5, 0.6, ...]' --payload '{"type": "test2"}'
```

4. **Search for similar vectors:**
```bash
python vector_cli.py search test_collection '[0.15, 0.25, 0.35, ...]' --top-k 5
```

5. **Clean up:**
```bash
python vector_cli.py delete-collection test_collection --force
```

### Working with Documents

1. **List existing collections:**
```bash
python vector_cli.py list-collections
```

2. **List documents in a collection:**
```bash
python vector_cli.py list-documents my_existing_collection
```

3. **Search within specific documents:**
```bash
python vector_cli.py search my_collection '[0.1, 0.2, 0.3]' --document-ids '["doc1", "doc2"]'
```

4. **Delete a specific document:**
```bash
python vector_cli.py delete-document my_collection doc_id_to_delete
```

## Notes

- Vector dimensions must match the collection's configured vector size
- Point IDs can be strings or integers
- JSON arguments should be properly quoted for your shell
- Use `--force` flag to skip confirmation prompts in scripts
- The CLI supports both local Qdrant instances (via `--db-path`) and remote instances (via `--url` and `--api-key`)

## Error Handling

The CLI provides clear error messages for common issues:
- Invalid JSON format in vectors or payloads
- Collection not found
- Vector dimension mismatches
- Connection issues

Exit codes:
- 0: Success
- 1: Error occurred