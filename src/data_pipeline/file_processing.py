import sys
import json
from pathlib import Path
from docling.document_converter import DocumentConverter

from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

from docling.chunking import HybridChunker

from typing import Dict, List, Any


class FileProcessor:
    """Class to handle file processing with Docling."""

    def __init__(
            self,
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            max_tokens=None):
        # If max_tokens is not provided, use the model's max length
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        if max_tokens is None:
            max_tokens = tokenizer.model_max_length

        self.tokenizer = HuggingFaceTokenizer(
            tokenizer=tokenizer,
            max_tokens=max_tokens,
        )

        self.chunker = HybridChunker(
            tokenizer=self.tokenizer,
        )

        self.converter = DocumentConverter()

    def process_docx(self, docx_path) -> list[dict[str, Any]]:
        """Process a single DOCX with Docling and return contextualized chunks."""
        print(f"Processing: {docx_path}")

        # Convert DOCX
        doc = self.converter.convert(str(docx_path)).document
        if not doc:
            print(f"Failed to convert {docx_path}.")
            return None

        chunks = self.chunk_text(doc)
        if not chunks:
            print(f"No chunks created for {docx_path}.")
            return None

        # Process chunks and contextualize them
        processed_chunks = []
        for chunk in chunks:
            contextualized_text = self.chunker.contextualize(chunk=chunk)

            chunk_data = {
                'text': contextualized_text,
                'meta': chunk.meta.export_json_dict() if hasattr(
                    chunk.meta,
                    'export_json_dict') else chunk.meta}
            processed_chunks.append(chunk_data)

        return processed_chunks

    def chunk_text(self, doc):
        chunk_iter = self.chunker.chunk(dl_doc=doc)
        chunks = list(chunk_iter)
        return chunks