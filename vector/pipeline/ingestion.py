"""Document ingestion pipeline for processing and indexing documents."""

from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import logging
import uuid

from pydantic import BaseModel, Field

from vector.models import ConvertedDocument
from vector.ports import Embedder, VectorStore
from .converter import DocumentConverter

logger = logging.getLogger(__name__)


class IngestionConfig(BaseModel):
    """Configuration for ingestion pipeline."""
    
    batch_size: int = Field(default=32, description="Batch size for embedding generation")
    collection_name: str = Field(default="chunks", description="Target collection name")
    generate_artifacts: bool = Field(default=True, description="Whether to generate image artifacts")
    use_vlm_pipeline: bool = Field(default=False, description="Use VLM pipeline for PDFs")


class IngestionResult(BaseModel):
    """Result of an ingestion operation."""
    
    document_id: str
    chunks_created: int
    chunks_indexed: int
    artifacts_generated: int = 0
    duration_seconds: float
    errors: List[str] = Field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """Check if ingestion was successful."""
        return len(self.errors) == 0 and self.chunks_indexed > 0


class IngestionPipeline:
    """Pipeline for ingesting documents into the vector store.
    
    Handles the complete document processing flow:
    1. Convert document to structured format (using Docling)
    2. Extract chunks and artifacts
    3. Generate embeddings for chunks
    4. Store chunks with embeddings in vector store
    
    Example:
        >>> from vector.pipeline import IngestionPipeline, IngestionConfig
        >>> from vector.stores import create_store
        >>> from vector.embedders import SentenceTransformerEmbedder
        >>> 
        >>> embedder = SentenceTransformerEmbedder()
        >>> store = create_store("qdrant", db_path="./qdrant_db")
        >>> config = IngestionConfig(collection_name="chunks")
        >>> 
        >>> pipeline = IngestionPipeline(embedder, store, config)
        >>> result = pipeline.ingest_file(Path("document.pdf"))
        >>> print(f"Indexed {result.chunks_indexed} chunks")
    """
    
    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        config: IngestionConfig
    ):
        """Initialize the ingestion pipeline.
        
        Args:
            embedder: Text embedder for generating chunk embeddings
            store: Vector store for persisting chunks
            config: Pipeline configuration
        """
        self.embedder = embedder
        self.store = store
        self.config = config
        self.converter = DocumentConverter(
            generate_artifacts=config.generate_artifacts,
            use_vlm_pipeline=config.use_vlm_pipeline
        )
    
    def ingest_file(
        self,
        file_path: Path,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionResult:
        """Ingest a document file into the vector store.
        
        Args:
            file_path: Path to the document file
            document_id: Optional document ID (defaults to filename stem)
            metadata: Optional metadata to attach to chunks
            
        Returns:
            IngestionResult with details about the operation
        """
        start_time = datetime.now()
        errors = []
        
        file_path = Path(file_path)
        if not file_path.exists():
            return IngestionResult(
                document_id=document_id or str(file_path),
                chunks_created=0,
                chunks_indexed=0,
                duration_seconds=0.0,
                errors=[f"File not found: {file_path}"]
            )
        
        # Use filename as document_id if not provided
        if document_id is None:
            document_id = file_path.stem
        
        logger.info(f"Starting ingestion of {file_path}")
        
        try:
            # Step 1: Convert document
            if file_path.suffix.lower() == '.json' and self.converter.is_valid_docling_json(file_path):
                logger.info(f"Loading pre-converted DoclingDocument from JSON")
                docling_doc = self.converter.load_from_json(file_path)
            else:
                logger.info(f"Converting document: {file_path}")
                docling_doc = self.converter.convert_document(file_path)
            
            converted_doc = ConvertedDocument(doc=docling_doc)
            
            # Step 2: Extract chunks and artifacts
            logger.info("Extracting chunks from document")
            chunks = converted_doc.get_chunks()
            
            if not chunks:
                errors.append("No chunks extracted from document")
                return IngestionResult(
                    document_id=document_id,
                    chunks_created=0,
                    chunks_indexed=0,
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                    errors=errors
                )
            
            logger.info(f"Extracted {len(chunks)} chunks")
            
            # Extract artifacts
            artifacts = converted_doc.get_artifacts()
            logger.info(f"Extracted {len(artifacts)} artifacts")
            
            # Step 3: Generate embeddings in batches
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = self._embed_in_batches(chunk_texts)
            
            # Step 4: Store chunks with embeddings
            logger.info(f"Storing chunks in collection '{self.config.collection_name}'")
            indexed_count = 0
            
            # Add file metadata to all chunks
            file_metadata = {
                **(metadata or {}),
                "source_file": str(file_path),
                "filename": file_path.name,
                "document_id": document_id
            }
            
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                try:
                    point_id = str(uuid.uuid4())
                    
                    payload = {
                        "chunk": chunk.model_dump_json(),
                        "document_id": document_id,
                        "chunk_index": chunk.chunk_index,  # Use chunk's own index
                        "registered_date": datetime.now().isoformat(),
                        **file_metadata
                    }
                    
                    self.store.upsert(
                        collection_name=self.config.collection_name,
                        point_id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                    indexed_count += 1
                    
                except Exception as e:
                    error_msg = f"Failed to index chunk {idx}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Ingestion complete: {indexed_count}/{len(chunks)} chunks indexed "
                f"in {duration:.2f}s"
            )
            
            return IngestionResult(
                document_id=document_id,
                chunks_created=len(chunks),
                chunks_indexed=indexed_count,
                artifacts_generated=len(artifacts),
                duration_seconds=duration,
                errors=errors
            )
            
        except Exception as e:
            error_msg = f"Ingestion failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
            
            return IngestionResult(
                document_id=document_id,
                chunks_created=0,
                chunks_indexed=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                errors=errors
            )
    
    def ingest_batch(
        self,
        file_paths: List[Path],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[IngestionResult]:
        """Ingest multiple documents in batch.
        
        Args:
            file_paths: List of document file paths
            metadata: Optional metadata to attach to all documents
            
        Returns:
            List of IngestionResult objects
        """
        results = []
        
        for file_path in file_paths:
            result = self.ingest_file(file_path, metadata=metadata)
            results.append(result)
        
        return results
    
    def _embed_in_batches(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batches to avoid memory issues.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            batch_embeddings = self.embedder.embed_texts(batch)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
