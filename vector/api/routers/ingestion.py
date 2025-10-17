"""Document ingestion endpoints.

Provides REST API for:
- File upload and ingestion
- Batch document processing
"""

from pathlib import Path
import tempfile
import logging
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form

from vector.api.deps import get_deps, AppDeps
from vector.api.schemas import IngestionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/ingest", response_model=IngestionResponse)
async def ingest_file(
    file: UploadFile = File(..., description="Document file to ingest"),
    document_id: Optional[str] = Form(None, description="Optional document ID (defaults to filename)"),
    deps: AppDeps = Depends(get_deps)
):
    """Ingest a document file into the vector store.
    
    Supports PDF, DOCX, TXT, and other document formats.
    The pipeline will:
    1. Convert document to structured format (using Docling)
    2. Extract text chunks
    3. Generate embeddings
    4. Store chunks in vector database
    
    Args:
        file: Document file to upload
        document_id: Optional custom document ID
        
    Returns:
        IngestionResponse with ingestion statistics and any errors
        
    Raises:
        HTTPException: If ingestion fails completely
    """
    logger.info(f"Received file upload: {file.filename}")
    
    try:
        # Create temporary file to store upload
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / file.filename
            
            # Write uploaded content to temp file
            content = await file.read()
            temp_path.write_bytes(content)
            
            logger.info(f"Saved upload to temporary file: {temp_path}")
            
            # Run ingestion pipeline
            result = deps.ingestion.ingest_file(
                file_path=temp_path,
                document_id=document_id
            )
            
            # Convert IngestionResult to IngestionResponse
            response = IngestionResponse(
                success=result.success,
                document_id=result.document_id,
                chunks_created=result.chunks_created,
                chunks_indexed=result.chunks_indexed,
                artifacts_generated=result.artifacts_generated,
                duration_seconds=result.duration_seconds,
                errors=result.errors
            )
            
            if response.success:
                logger.info(
                    f"✓ Ingestion successful: {response.chunks_indexed} chunks indexed "
                    f"in {response.duration_seconds:.2f}s"
                )
            else:
                logger.warning(
                    f"⚠ Ingestion completed with errors: {response.errors}"
                )
            
            return response
            
    except Exception as e:
        error_msg = f"Ingestion failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)
