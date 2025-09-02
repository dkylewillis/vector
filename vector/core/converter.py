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
        use_vlm_pipeline = None
        if use_vlm_pipeline:
            pipeline_options = VlmPipelineOptions()
            
            #Configure VLM options if available
            
            # pipeline_options.enable_remote_services = True
            # pipeline_options.vlm_options = ApiVlmOptions(
            #     url="https://api.openai.com/v1/chat/completions",  # OpenAI-compatible
            #     params={"model": "gpt-5"},  # <= GPT-5 here
            #     prompt="OCR full page to markdown.",
            #     timeout=300,
            #     response_format=ResponseFormat.MARKDOWN,
            #     headers={
            #         "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
            #     },
            #     temperature=1,
            # )
            pipeline_cls = VlmPipeline
        else:
            pipeline_options = PdfPipelineOptions()
            pipeline_cls = None  # Default pipeline for PDF
        
        if generate_artifacts:
            pipeline_options.images_scale = 2.0
            pipeline_options.generate_picture_images = True
            pipeline_options.generate_table_images = True
        else:
            # Disable artifact generation for faster processing
            pipeline_options.images_scale = 1.0
            pipeline_options.generate_picture_images = False
            #pipeline_options.generate_table_images = False

        # Create converter with appropriate pipeline
        format_options = {
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,          
            )
        }
        
        # Only add pipeline_cls if using VLM pipeline
        if use_vlm_pipeline:
            format_options[InputFormat.PDF].pipeline_cls = pipeline_cls

        self.converter = DoclingConverter(format_options=format_options)

    def convert_document(self, file_path: Path) -> DoclingDocument:
        """Convert a document file to DoclingDocument.
        
        Args:
            file_path: Path to the file to convert
            
        Returns:
            DoclingDocument object
            
        Raises:
            ProcessingError: If conversion fails
        """
        pipeline_type = "VLM" if self.use_vlm_pipeline else "PDF"
        print(f"Converting: {file_path} (pipeline: {pipeline_type}, artifacts: {'enabled' if self.generate_artifacts else 'disabled'})")
        
        # Convert document using Docling
        doc = self.converter.convert(str(file_path)).document
        if not doc:
            raise ProcessingError(f"Failed to convert {file_path}")
            
        return doc

    def save_document(self, doc: DoclingDocument, output_path: Path) -> None:
        """Save the converted document to a file.

        Args:
            doc: The DoclingDocument to save
            output_path: The path to the output file
        """
        doc.save_as_markdown(str(output_path), image_mode=ImageRefMode.REFERENCED)