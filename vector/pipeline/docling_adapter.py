"""Docling adapter for converting documents to VectorDocument format.

This adapter bridges Docling's document representation to our parser-agnostic
VectorDocument format. It handles both fresh document parsing and loading
pre-converted Docling JSON files.
"""

from pathlib import Path
from typing import Optional, List
import uuid

from docling_core.types.doc.document import (
    DoclingDocument,
    TextItem,
    TableItem,
    PictureItem,
    SectionHeaderItem,
)

from vector.models import (
    VectorDocument,
    DocumentSection,
    TableElement,
    ImageElement,
    HeaderElement,
)
from vector.ports import DocumentConverter


class DoclingAdapter:
    """Adapter for Docling parser - handles both fresh parsing and loading pre-converted documents.
    
    This adapter implements the DocumentConverter protocol and provides the bridge
    between Docling's document representation and our standardized VectorDocument format.
    
    Usage:
        # Fresh conversion
        adapter = DoclingAdapter()
        vector_doc = adapter.convert_document(Path("report.pdf"))
        
        # Load pre-converted JSON
        vector_doc = adapter.load_from_json(Path("data/converted_documents/report.json"))
    """
    
    def convert_document(self, file_path: Path) -> VectorDocument:
        """Convert a document file to VectorDocument format.
        
        Parses the document using Docling and converts the result to our
        standardized VectorDocument representation.
        
        Args:
            file_path: Path to document (PDF, DOCX, PPTX, HTML, etc.)
            
        Returns:
            VectorDocument representation with extracted structure
            
        Raises:
            FileNotFoundError: If file_path doesn't exist
            Exception: If Docling parsing fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        # Import here to avoid loading Docling until needed
        from docling.document_converter import DocumentConverter as DoclingConverter
        
        # Parse with Docling
        converter = DoclingConverter()
        result = converter.convert(file_path)
        docling_doc = result.document
        
        # Convert to VectorDocument
        return self._adapt_docling_to_vector(
            docling_doc=docling_doc,
            source_path=str(file_path)
        )
    
    def load_from_json(self, json_path: Path) -> VectorDocument:
        """Load a pre-converted Docling JSON file and convert to VectorDocument.
        
        This is useful when you have already-converted documents stored in
        data/converted_documents/ or similar locations. It loads the Docling
        JSON format and converts it to VectorDocument.
        
        Args:
            json_path: Path to Docling JSON file
            
        Returns:
            VectorDocument representation
            
        Raises:
            FileNotFoundError: If json_path doesn't exist
            Exception: If JSON loading or conversion fails
        """
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        # Load DoclingDocument from JSON
        docling_doc = DoclingDocument.load_from_json(json_path)
        
        # Convert to VectorDocument
        return self._adapt_docling_to_vector(
            docling_doc=docling_doc,
            source_path=str(json_path)
        )
    
    def save_to_json(self, doc: VectorDocument, json_path: Path) -> None:
        """Save VectorDocument to JSON.
        
        Note: This saves in VectorDocument format (our standardized format),
        not Docling format. The saved JSON can be loaded back using standard
        Pydantic model loading.
        
        Args:
            doc: VectorDocument to save
            json_path: Output path for JSON file
        """
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(doc.model_dump_json(indent=2))
    
    def _adapt_docling_to_vector(
        self,
        docling_doc: DoclingDocument,
        source_path: str,
        document_id: Optional[str] = None
    ) -> VectorDocument:
        """Internal: Convert DoclingDocument to VectorDocument format.
        
        This is the core adaptation logic that extracts structure from Docling's
        representation into our standardized format. It handles:
        - Text sections with hierarchy
        - Tables with structured data
        - Images with captions
        - Headers/headings
        - Metadata and provenance
        
        Args:
            docling_doc: Docling's document representation
            source_path: Original file path (for metadata)
            document_id: Optional document ID (generated if not provided)
            
        Returns:
            VectorDocument with extracted structure
        """
        doc_id = document_id or str(uuid.uuid4())
        sections = []
        tables = []
        images = []
        headers = []
        
        # Iterate through Docling's structured items
        for item, level in docling_doc.iterate_items():
            # Extract page number from provenance if available
            page_no = self._extract_page_number(item)
            
            if isinstance(item, TextItem):
                # Regular text becomes a section
                if item.text and item.text.strip():
                    sections.append(DocumentSection(
                        section_id=f"section_{len(sections)}",
                        text=item.text.strip(),
                        page_number=page_no,
                        level=level
                    ))
            
            elif isinstance(item, SectionHeaderItem):
                # Headers are tracked separately for document structure
                if hasattr(item, 'text') and item.text:
                    headers.append(HeaderElement(
                        header_id=item.self_ref or f"header_{len(headers)}",
                        text=item.text.strip(),
                        level=level,
                        page_number=page_no
                    ))
            
            elif isinstance(item, TableItem):
                # Extract table data as 2D array
                table_data = self._extract_table_data(item, docling_doc)
                caption = None
                if hasattr(item, 'caption_text'):
                    try:
                        caption = item.caption_text(doc=docling_doc)
                    except:
                        pass
                
                tables.append(TableElement(
                    table_id=item.self_ref or f"table_{len(tables)}",
                    caption=caption,
                    data=table_data,
                    page_number=page_no
                ))
            
            elif isinstance(item, PictureItem):
                # Extract image metadata
                caption = None
                if hasattr(item, 'caption_text'):
                    try:
                        caption = item.caption_text(doc=docling_doc)
                    except:
                        pass
                
                # Extract bounding box if available
                bbox = self._extract_bbox(item)
                
                images.append(ImageElement(
                    image_id=item.self_ref or f"image_{len(images)}",
                    caption=caption,
                    image_path="",  # Will be set when artifacts are saved
                    page_number=page_no,
                    bbox=bbox
                ))
        
        # Get full text export
        full_text = docling_doc.export_to_text()
        
        # Determine source format from file extension
        source_format = None
        if source_path:
            source_format = Path(source_path).suffix.lower().lstrip('.')
        
        # Extract page count
        page_count = None
        if hasattr(docling_doc, 'pages'):
            page_count = len(docling_doc.pages)
        
        return VectorDocument(
            document_id=doc_id,
            text=full_text,
            sections=sections,
            tables=tables,
            images=images,
            headers=headers,
            source_path=source_path,
            source_format=source_format,
            page_count=page_count,
            metadata={
                "parser": "docling",
                "docling_version": getattr(docling_doc, 'version', 'unknown'),
                "item_count": len(list(docling_doc.iterate_items()))
            }
        )
    
    def _extract_page_number(self, item) -> Optional[int]:
        """Extract page number from item provenance.
        
        Args:
            item: Docling document item
            
        Returns:
            Page number if available, None otherwise
        """
        if hasattr(item, 'prov') and item.prov:
            try:
                return item.prov[0].page_no
            except (IndexError, AttributeError):
                pass
        return None
    
    def _extract_bbox(self, item) -> Optional[List[float]]:
        """Extract bounding box from item provenance.
        
        Args:
            item: Docling document item
            
        Returns:
            Bounding box as [x0, y0, x1, y1] if available, None otherwise
        """
        if hasattr(item, 'prov') and item.prov:
            try:
                prov = item.prov[0]
                if hasattr(prov, 'bbox'):
                    bbox = prov.bbox
                    # Convert to list format [x0, y0, x1, y1]
                    if hasattr(bbox, 'l') and hasattr(bbox, 't') and hasattr(bbox, 'r') and hasattr(bbox, 'b'):
                        return [bbox.l, bbox.t, bbox.r, bbox.b]
                    elif isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                        return list(bbox)
            except (IndexError, AttributeError):
                pass
        return None
    
    def _extract_table_data(self, item: TableItem, doc: DoclingDocument) -> List[List[str]]:
        """Extract table as 2D array of strings.
        
        Attempts multiple strategies to extract table data:
        1. Use structured data.grid if available
        2. Parse from markdown export
        3. Fallback to empty table
        
        Args:
            item: Docling TableItem
            doc: Parent DoclingDocument
            
        Returns:
            2D list of cell values (rows and columns)
        """
        try:
            # Strategy 1: Try to get structured table data if available
            if hasattr(item, 'data') and item.data:
                if hasattr(item.data, 'grid'):
                    # Docling has structured grid data
                    return [[str(cell) for cell in row] for row in item.data.grid]
                elif hasattr(item.data, 'table'):
                    # Alternative structure
                    table = item.data.table
                    if hasattr(table, 'data'):
                        return [[str(cell) for cell in row] for row in table.data]
            
            # Strategy 2: Parse from markdown export
            if hasattr(item, 'export_to_markdown'):
                markdown = item.export_to_markdown(doc=doc)
                rows = []
                for line in markdown.split('\n'):
                    line = line.strip()
                    if line and '|' in line:
                        # Parse markdown table row: | cell1 | cell2 | cell3 |
                        cells = [cell.strip() for cell in line.split('|')[1:-1]]
                        # Skip separator rows (|---|---|---|)
                        if cells and not all(c.replace('-', '').strip() == '' for c in cells):
                            rows.append(cells)
                
                if rows:
                    return rows
            
            # Strategy 3: Try to get text representation
            if hasattr(item, 'text') and item.text:
                # Split by lines and create simple 1-column table
                lines = [line.strip() for line in item.text.split('\n') if line.strip()]
                if lines:
                    return [[line] for line in lines]
            
        except Exception as e:
            # Log error but don't fail - return empty table
            print(f"Warning: Failed to extract table data: {e}")
        
        # Last resort: return minimal empty table
        return [[]]
    
    def get_chunk_size(self) -> int:
        """Get the recommended chunk size for documents processed by this adapter.
        
        Returns:
            Recommended chunk size in characters
        """
        # This is a reasonable default for most documents
        # Can be overridden by specific chunker implementations
        return 1000
