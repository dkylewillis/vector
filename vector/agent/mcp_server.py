"""Model Context Protocol (MCP) server for Vector agent capabilities.

This module exposes Vector's agent tools as an MCP server, allowing
integration with MCP-compatible clients like Claude Desktop, IDEs, and
other AI applications.

To run the MCP server:
    python -m vector.agent.mcp_server

Or configure in Claude Desktop's config:
    {
      "mcpServers": {
        "vector": {
          "command": "python",
          "args": ["-m", "vector.agent.mcp_server"],
          "env": {
            "OPENAI_API_KEY": "your-key-here"
          }
        }
      }
    }
"""

import asyncio
import sys
from typing import Optional, List

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("Warning: MCP not available. Install with: pip install mcp", file=sys.stderr)

from ..config import Config
from ..embedders.sentence_transformer import SentenceTransformerEmbedder
from ..stores.factory import create_store
from vector.search.service import SearchService
from ..ai.factory import AIModelFactory

from .deps import AgentDeps
from .models import ChatSession
from .tools import (
    retrieve_chunks,
    expand_query,
    search_documents,
    get_chunk_window,
    get_document_metadata,
    list_available_documents
)


class VectorMCPServer:
    """MCP server for Vector agent tools."""
    
    def __init__(self, config: Optional[Config] = None, chunks_collection: str = "chunks"):
        """Initialize MCP server.
        
        Args:
            config: Configuration object
            chunks_collection: Name of chunks collection
        """
        self.config = config or Config()
        self.chunks_collection = chunks_collection
        
        # Initialize dependencies
        self._init_deps()
        
        # Create MCP server
        if MCP_AVAILABLE:
            self.server = Server("vector-agent")
            self._register_tools()
        else:
            self.server = None
    
    def _init_deps(self):
        """Initialize agent dependencies."""
        # Initialize search service
        embedder = SentenceTransformerEmbedder()
        store = create_store("qdrant", db_path=self.config.vector_db_path)
        search_service = SearchService(
            embedder,
            store,
            self.chunks_collection
        )
        
        # Initialize AI models
        try:
            search_model = AIModelFactory.create_model(self.config, 'search')
            answer_model = AIModelFactory.create_model(self.config, 'answer')
        except Exception as e:
            print(f"Warning: Could not initialize AI models: {e}", file=sys.stderr)
            search_model = None
            answer_model = None
        
        # Create dependencies container
        self.deps = AgentDeps(
            search_service=search_service,
            config=self.config,
            search_model=search_model,
            answer_model=answer_model,
            chunks_collection=self.chunks_collection
        )
    
    def _register_tools(self):
        """Register tools with MCP server."""
        if not self.server:
            return
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="search_documents",
                    description=(
                        "Search municipal documents using semantic similarity. "
                        "Returns relevant chunks from ordinances, codes, and regulations."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results (1-50)",
                                "default": 12
                            },
                            "window": {
                                "type": "integer",
                                "description": "Surrounding chunk window (0-5)",
                                "default": 0
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="expand_query",
                    description=(
                        "Expand a user query into search keyphrases using AI. "
                        "Useful for improving search results."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_message": {
                                "type": "string",
                                "description": "User query to expand"
                            }
                        },
                        "required": ["user_message"]
                    }
                ),
                Tool(
                    name="get_chunk_window",
                    description=(
                        "Get surrounding chunks for context around a specific chunk. "
                        "Provides additional context for search results."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chunk_id": {
                                "type": "string",
                                "description": "Chunk ID"
                            },
                            "window": {
                                "type": "integer",
                                "description": "Number of chunks before and after (1-5)",
                                "default": 2
                            }
                        },
                        "required": ["chunk_id"]
                    }
                ),
                Tool(
                    name="get_document_metadata",
                    description="Get metadata for a specific document by ID.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Document ID"
                            }
                        },
                        "required": ["document_id"]
                    }
                ),
                Tool(
                    name="list_documents",
                    description="List all available documents in the collection.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum documents to return (1-500)",
                                "default": 100
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            """Execute a tool."""
            # Create a minimal run context
            from pydantic_ai import RunContext
            ctx = RunContext(deps=self.deps, retry=0, messages=[])
            
            # Create a temporary session for tools that need it
            from uuid import uuid4
            temp_session = ChatSession(
                id=str(uuid4()),
                system_prompt="",
                messages=[]
            )
            
            try:
                if name == "search_documents":
                    results = await search_documents(
                        ctx=ctx,
                        query=arguments["query"],
                        top_k=arguments.get("top_k", 12),
                        window=arguments.get("window", 0)
                    )
                    return [TextContent(
                        type="text",
                        text=f"Found {len(results)} results:\n\n" + 
                             "\n\n".join([
                                 f"[{i+1}] {r.filename} (Score: {r.score:.3f})\n{r.text}"
                                 for i, r in enumerate(results)
                             ])
                    )]
                
                elif name == "expand_query":
                    result = await expand_query(
                        ctx=ctx,
                        session=temp_session,
                        user_message=arguments["user_message"]
                    )
                    return [TextContent(
                        type="text",
                        text=f"Expanded Query: {result['expanded_query']}\n\n"
                             f"Keyphrases: {', '.join(result['keyphrases'])}"
                    )]
                
                elif name == "get_chunk_window":
                    result = await get_chunk_window(
                        ctx=ctx,
                        chunk_id=arguments["chunk_id"],
                        window=arguments.get("window", 2)
                    )
                    if result["success"]:
                        return [TextContent(
                            type="text",
                            text=f"Chunk window for {arguments['chunk_id']}:\n\n" +
                                 "\n\n".join(result["chunks"])
                        )]
                    else:
                        return [TextContent(
                            type="text",
                            text=f"Error: {result.get('error', 'Unknown error')}"
                        )]
                
                elif name == "get_document_metadata":
                    result = await get_document_metadata(
                        ctx=ctx,
                        document_id=arguments["document_id"]
                    )
                    if result["success"]:
                        return [TextContent(
                            type="text",
                            text=f"Document: {result['filename']}\n"
                                 f"Type: {result['type']}\n"
                                 f"Metadata: {result['metadata']}"
                        )]
                    else:
                        return [TextContent(
                            type="text",
                            text=f"Error: {result.get('error', 'Unknown error')}"
                        )]
                
                elif name == "list_documents":
                    result = await list_available_documents(
                        ctx=ctx,
                        limit=arguments.get("limit", 100)
                    )
                    if result["success"]:
                        doc_list = "\n".join([
                            f"- {doc['filename']} ({doc['type']}) [ID: {doc['id']}]"
                            for doc in result["documents"]
                        ])
                        return [TextContent(
                            type="text",
                            text=f"Available Documents ({result['count']}):\n\n{doc_list}"
                        )]
                    else:
                        return [TextContent(
                            type="text",
                            text=f"Error: {result.get('error', 'Unknown error')}"
                        )]
                
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
            
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Tool execution error: {str(e)}"
                )]
    
    async def run(self):
        """Run the MCP server."""
        if not self.server:
            print("Error: MCP server not available", file=sys.stderr)
            return
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def create_mcp_server(config: Optional[Config] = None) -> Optional[VectorMCPServer]:
    """Create and return an MCP server instance.
    
    Args:
        config: Optional configuration object
        
    Returns:
        VectorMCPServer instance or None if MCP not available
    """
    if not MCP_AVAILABLE:
        return None
    
    return VectorMCPServer(config=config)


async def main():
    """Main entry point for MCP server."""
    if not MCP_AVAILABLE:
        print("Error: MCP not installed. Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)
    
    server = create_mcp_server()
    if server:
        print("Starting Vector MCP server...", file=sys.stderr)
        await server.run()


if __name__ == "__main__":
    asyncio.run(main())
