import os
from pathlib import Path
from typing import Optional, Union
import json

from docling.document_converter import DocumentConverter as DoclingConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, VlmPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc.document import DoclingDocument
from docling.pipeline.vlm_pipeline import VlmPipeline
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions, ResponseFormat
from docling_core.types.doc.page import SegmentedPage
from docling_core.types.doc import ImageRefMode
from pydantic import ValidationError

from .models import ConvertedDocument


class DocumentConverter:
    """Handles document conversion using Docling."""

    def __init__(self, generate_artifacts: bool = True, use_vlm_pipeline: bool = False):
        """Initialize the document converter with configurable artifact generation.

        Args:
            generate_artifacts: Whether to generate picture and table artifacts
            use_vlm_pipeline: Whether to use VLM Pipeline (True) or PDF Pipeline (False)
        """
        self.generate_artifacts = generate_artifacts
        self.use_vlm_pipeline = use_vlm_pipeline

        if use_vlm_pipeline:
            pdf_pipeline_options = VlmPipelineOptions()
            pipeline_cls = VlmPipeline
        else:
            pdf_pipeline_options = PdfPipelineOptions()
            pipeline_cls = None

        if generate_artifacts:
            pdf_pipeline_options.images_scale = 2.0
            pdf_pipeline_options.generate_picture_images = True
            pdf_pipeline_options.generate_table_images = True
        else:
            pdf_pipeline_options.images_scale = 1.0
            pdf_pipeline_options.generate_picture_images = False

        # Fix: Create PdfFormatOption with pipeline_options (not a dict)
        pdf_format_option = PdfFormatOption(pipeline_options=pdf_pipeline_options)
        
        if use_vlm_pipeline:
            pdf_format_option.pipeline_cls = pipeline_cls

        self.converter = DoclingConverter(
            allowed_formats=[
                InputFormat.PDF,
                InputFormat.IMAGE,
                InputFormat.DOCX,
                InputFormat.HTML,
                InputFormat.PPTX,
                InputFormat.ASCIIDOC,
                InputFormat.CSV,
                InputFormat.MD,
                InputFormat.JSON_DOCLING,
            ],
            format_options={
                InputFormat.PDF: pdf_format_option  # Fix: Use the correct format option
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
        print(f"Converting: {file_path} (type: {file_type}, artifacts: {'enabled' if self.generate_artifacts else 'disabled'})")

        # Convert document using Docling - it auto-detects format
        doc = self.converter.convert(str(file_path)).document
        if not doc:
            raise Exception(f"Failed to convert {file_path}")

        return doc
    
    @staticmethod
    def is_valid_docling_json(json_path: Path) -> bool:
        """Check if a JSON file contains a valid DoclingDocument.

        Args:
            json_path: Path to the JSON file to validate

        Returns:
            True if the JSON is a valid DoclingDocument, False otherwise
        """
        try:
            if not json_path.exists():
                return False
            
            with open(json_path, 'r', encoding='utf-8') as f:
                json_content = f.read()
            
            # Try to validate the JSON against DoclingDocument schema
            DoclingDocument.model_validate_json(json_content)
            return True
        except (json.JSONDecodeError, ValidationError, Exception):
            return False
    
    def load_from_json(self, json_path: Path) -> DoclingDocument:
        """Load a DoclingDocument from a JSON file.

        Args:
            json_path: Path to the JSON file containing the DoclingDocument

        Returns:
            DoclingDocument object

        Raises:
            FileNotFoundError: If the JSON file doesn't exist
            ValueError: If the JSON is invalid or not a DoclingDocument
        """
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        print(f"Loading DoclingDocument from: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            json_content = f.read()
        
        try:
            doc = DoclingDocument.model_validate_json(json_content)
            return doc
        except ValidationError as e:
            raise ValueError(f"Invalid DoclingDocument JSON: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
    
    @staticmethod
    def save_to_json(doc: DoclingDocument, json_path: Path, image_mode: ImageRefMode = ImageRefMode.EMBEDDED) -> None:
        """Save a DoclingDocument to a JSON file.

        Args:
            doc: The DoclingDocument to save
            json_path: Path where to save the JSON file
            image_mode: How to handle images in the export
        """
        print(f"Saving DoclingDocument to: {json_path}")
        
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        doc.save_as_json(json_path, image_mode=image_mode)
    
    def _get_file_type(self, file_path: Path) -> str:
        """Get file type for logging purposes."""
        suffix = file_path.suffix.lower()
        type_mapping = {
            '.pdf': 'PDF',
            '.docx': 'DOCX', '.doc': 'DOC',
            '.png': 'IMAGE', '.jpg': 'IMAGE', '.jpeg': 'IMAGE', '.gif': 'IMAGE',
            '.html': 'HTML', '.htm': 'HTML',
            '.txt': 'TEXT', '.md': 'TEXT',
            '.json': 'JSON_DOCLING'
        }
        return type_mapping.get(suffix, 'PDF')