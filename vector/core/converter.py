import os
from pathlib import Path
from typing import Optional, Union

from docling.document_converter import DocumentConverter as DoclingConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, VlmPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc.document import DoclingDocument
from docling.pipeline.vlm_pipeline import VlmPipeline
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions, ResponseFormat
from docling_core.types.doc.page import SegmentedPage
from docling_core.types.doc import ImageRefMode

from .models import ConvertedDocument


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

        pdf_format_options = PdfFormatOption(
            pipeline_cls=VlmPipeline if use_vlm_pipeline else None,
            pipeline_options=VlmPipelineOptions() if use_vlm_pipeline else PdfPipelineOptions()
        )


        self.converter = DocumentConverter(  # all of the below is optional, has internal defaults.
            allowed_formats=[
                InputFormat.PDF,
                InputFormat.IMAGE,
                InputFormat.DOCX,
                InputFormat.HTML,
                InputFormat.PPTX,
                InputFormat.ASCIIDOC,
                InputFormat.CSV,
                InputFormat.MD,
            ],  # whitelist formats, non-matching files are ignored.
            format_options={
                InputFormat.PDF: pdf_format_options
            },
        )


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
            raise Exception(f"Failed to convert {file_path}")

        return doc
    
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
    
