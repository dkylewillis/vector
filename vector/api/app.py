"""FastAPI application entry point.

Main application with:
- Lifespan management
- CORS configuration
- Router registration
- Gradio UI mounted at /ui
- Health check endpoint
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr

from vector.api.deps import get_deps
from vector.api.routers import vectorstore, ingestion, retrieval

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.
    
    Handles startup and shutdown:
    - Startup: Initialize dependencies (embedder, vector store, etc.)
    - Shutdown: Clean up resources if needed
    """
    logger.info("🚀 Starting Vector API server...")
    
    # Initialize dependencies on startup
    deps = get_deps()
    logger.info(f"✓ Initialized with {len(deps.store.list_collections())} collections")
    
    yield
    
    # Cleanup on shutdown (if needed)
    logger.info("🛑 Shutting down Vector API server...")


# Create FastAPI application
app = FastAPI(
    title="Vector API",
    version="2.0.0",
    description="RAG Pipeline, Vector Store, and Context Retrieval API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(vectorstore.router)
app.include_router(ingestion.router)
app.include_router(retrieval.router)

# Mount Gradio UI at /ui
try:
    from vector.ui.app import create_gradio_app
    
    gradio_app = create_gradio_app()
    app = gr.mount_gradio_app(app, gradio_app, path="/ui")
    logger.info("✓ Gradio UI mounted at /ui")
except ImportError as e:
    logger.warning(f"⚠ Gradio UI not available: {e}")
except Exception as e:
    logger.error(f"⚠ Failed to mount Gradio UI: {e}")


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "Vector API",
        "version": "2.0.0",
        "description": "RAG Pipeline, Vector Store, and Context Retrieval",
        "ui": "/ui",
        "docs": "/docs",
        "endpoints": {
            "vectorstore": "/vectorstore",
            "ingestion": "/ingestion",
            "retrieval": "/retrieval"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    try:
        deps = get_deps()
        collections = deps.store.list_collections()
        
        return {
            "status": "healthy",
            "collections": len(collections),
            "embedder": "initialized",
            "store": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def main():
    """CLI entry point to run the server."""
    import uvicorn
    
    logger.info("Starting Vector API server via CLI...")
    uvicorn.run(
        "vector.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
