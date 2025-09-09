"""Document converter utilities for Vector."""

import os
from pathlib import Path
from typing import Optional

from docling.document_converter import DocumentConverter as DoclingConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, VlmPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc.document import DoclingDocument
from docling.pipeline.vlm_pipeline import VlmPipeline
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions, ResponseFormat
from ..exceptions import ProcessingError
from docling_core.types.doc.page import SegmentedPage
from docling_core.types.doc import ImageRefMode
from .models import DocumentResult


# Forward declarations for type hints
class PipelineType:
    """Forward declaration for PipelineType enum."""
    pass


class ArtifactProcessor:
    """Forward declaration for ArtifactProcessor."""
    pass


class DocumentConverter:
    """Handles document conversion using Docling."""

    def __init__(self, generate_artifacts: bool = True, use_vlm_pipeline: bool = True):
        """Initialize the document converter with configurable artifact generation.

        Args:
            generate_artifacts: Whether to generate picture and table artifacts
            use_vlm_pipeline: Whether to use VLM Pipeline (True) or PDF Pipeline (False)
        """
        self.generate_artifacts = generate_artifacts
        self.use_vlm_pipeline = use_vlm_pipeline

        # Configure pipeline options based on pipeline type
        if use_vlm_pipeline:
            pipeline_options = VlmPipelineOptions()
            pipeline_cls = VlmPipeline
        else:
            pipeline_options = PdfPipelineOptions()
            pipeline_cls = None

        # Configure artifact generation
        if hasattr(pipeline_options, 'images_scale'):
            if generate_artifacts:
                pipeline_options.images_scale = 2.0
                pipeline_options.generate_picture_images = True
                if hasattr(pipeline_options, 'generate_table_images'):
                    pipeline_options.generate_table_images = True
            else:
                pipeline_options.images_scale = 1.0
                pipeline_options.generate_picture_images = False

        # Create converter with PDF format options (supports most formats)
        format_options = {
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }

        if use_vlm_pipeline:
            format_options[InputFormat.PDF].pipeline_cls = pipeline_cls

        self.converter = DoclingConverter(format_options=format_options)

    def _get_file_type(self, file_path: Path) -> str:
        """Get file type for logging purposes."""
        suffix = file_path.suffix.lower()
        type_mapping = {
            '.pdf': 'PDF',
            '.docx': 'DOCX', '.doc': 'DOC',
            '.png': 'IMAGE', '.jpg': 'IMAGE', '.jpeg': 'IMAGE', '.gif': 'IMAGE',
            '.html': 'HTML', '.htm': 'HTML',
            '.txt': 'TEXT', '.md': 'TEXT'
        }
        return type_mapping.get(suffix, 'PDF')

    @classmethod
    def create_for_pipeline(cls, pipeline_type: 'PipelineType', include_artifacts: bool) -> 'DocumentConverter':
        """Factory method to create converter for specific pipeline type.

        Args:
            pipeline_type: PipelineType enum (VLM or PDF)
            include_artifacts: Whether to generate artifacts

        Returns:
            Configured DocumentConverter instance
        """
        use_vlm = (pipeline_type == 'VLM')
        return cls(generate_artifacts=include_artifacts, use_vlm_pipeline=use_vlm)

    def convert_document(self, file_path: Path) -> DoclingDocument:
        """Convert a document file to DoclingDocument.

        Args:
            file_path: Path to the file to convert

        Returns:
            DoclingDocument object

        Raises:
            ProcessingError: If conversion fails
        """
        file_type = self._get_file_type(file_path)
        pipeline_type = "VLM" if self.use_vlm_pipeline else "PDF"
        print(f"Converting: {file_path} (type: {file_type}, pipeline: {pipeline_type}, artifacts: {'enabled' if self.generate_artifacts else 'disabled'})")

        # Convert document using Docling - it auto-detects format
        doc = self.converter.convert(str(file_path)).document
        if not doc:
            raise ProcessingError(f"Failed to convert {file_path}")

        return doc

    def convert_to_document_result(self, file_path: Path, source: Optional[str] = None,
                                 artifact_processor: Optional['ArtifactProcessor'] = None,
                                 run_async: bool = True) -> DocumentResult:
        """Convert file to DocumentResult with metadata and optional artifact processing.

        Args:
            file_path: Path to the file to convert
            source: Source category for the document
            artifact_processor: Optional artifact processor for indexing artifacts
            run_async: Whether to run async operations (default True)

        Returns:
            DocumentResult object with converted document and metadata
        """
        # Convert document using Docling
        doc = self.convert_document(file_path)

        # Calculate metadata
        file_hash = self._calculate_file_hash(file_path)
        source_category = self._determine_source(file_path, source)

        doc_result = DocumentResult(
            document=doc,
            file_path=file_path,
            source_category=source_category,
            file_hash=file_hash
        )

        # Index artifacts if requested and processor provided
        if self.generate_artifacts and artifact_processor:
            if run_async:
                import asyncio
                asyncio.run(artifact_processor.index_artifacts(doc_result))
            else:
                # For synchronous execution, we'll skip async artifact processing
                # The caller should handle this separately
                pass

        return doc_result

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate hash of file content for duplicate detection.

        Args:
            file_path: Path to the file

        Returns:
            SHA256 hash of file content
        """
        import hashlib
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            raise ProcessingError(f"Failed to calculate hash for {file_path}: {e}")

    def _determine_source(self, file_path: Path, source: Optional[str]) -> str:
        """Determine source category from file path or explicit source.

        Args:
            file_path: Path to the file
            source: Explicit source category

        Returns:
            Source category string
        """
        if source:
            return source

        # Try to determine from folder name
        folder_name = file_path.parent.name.lower()
        default_categories = ['ordinances', 'manuals', 'checklists']
        if folder_name in default_categories:
            return folder_name

        return 'other'

    def save_document(self, doc: DoclingDocument, output_path: Path) -> None:
        """Save the converted document to a file.

        Args:
            doc: The DoclingDocument to save
            output_path: The path to the output file
        """
        doc.save_as_markdown(str(output_path), image_mode=ImageRefMode.REFERENCED)