def _generate_thumbnail_bytes(self, image_data: bytes) -> Optional[bytes]:
    """Generate thumbnail bytes from image data."""
    try:
        image = PILImage.open(io.BytesIO(image_data))
        image.thumbnail(self.thumbnail_size, PILImage.Resampling.LANCZOS)
        
        # Convert to bytes
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=85)
        return output.getvalue()
    except Exception as e:
        self._debug_print(f"Error generating thumbnail: {e}")
        return None

def _get_context_text(self, items: List[Tuple], current_idx: int, direction: str, max_chars: int = 200) -> Optional[str]:
    """Extract context text before or after the current item."""
    context_parts = []
    chars_collected = 0
    
    if direction == "before":
        for i in range(current_idx - 1, -1, -1):
            item, level = items[i]
            if isinstance(item, TextItem):
                text = item.text.strip()
                if text:
                    context_parts.insert(0, text)
                    chars_collected += len(text)
                    if chars_collected >= max_chars:
                        break
    else:  # direction == "after"
        for i in range(current_idx + 1, len(items)):
            item, level = items[i]
            if isinstance(item, TextItem):
                text = item.text.strip()
                if text:
                    context_parts.append(text)
                    chars_collected += len(text)
                    if chars_collected >= max_chars:
                        break
    
    if context_parts:
        full_context = " ".join(context_parts)
        return full_context[:max_chars] if len(full_context) > max_chars else full_context
    return None

def _update_heading_stack(self, heading_stack: List[Dict], item: SectionHeaderItem, level: int) -> List[Dict]:
    """Update heading stack with new section header."""
    heading_info = {
        "text": item.text.strip() if hasattr(item, 'text') else "",
        "level": level,
        "ref": item.self_ref
    }
    
    # Remove headings at the same or deeper level
    heading_stack = [h for h in heading_stack if h['level'] < level]
    heading_stack.append(heading_info)
    
    return heading_stack

def _get_heading_context(self, heading_stack: List[Dict]) -> List[str]:
    """Get hierarchical heading context."""
    return [heading["text"] for heading in heading_stack if heading["text"]]



def _extract_table_text(self, doc: DoclingDocument, item: TableItem) -> str:
    """Extract table text content."""
    try:
        if hasattr(item, 'text') and item.text:
            return item.text.strip()
        else:
            return item.export_to_markdown(doc=doc)
    except Exception as e:
        self._debug_print(f"Error extracting table text: {e}")
        return ""
    
def _extract_image_data(self, item, doc: DoclingDocument) -> Optional[bytes]:
    """Extract raw image data from any artifact item.
    
    Args:
        item: Artifact item (PictureItem or TableItem)
        doc: Docling document
        
    Returns:
        Raw image bytes or None if not available
    """
    try:
        # Try nested image object
        if hasattr(item, 'image') and item.image:
            
            try:
                pil_img = getattr(item.image, 'pil_image', None)
            except Exception as e:
                pil_img = None
                
            # Verify it's actually a PIL Image
            if isinstance(pil_img, PILImage.Image):
                # Convert PIL Image to bytes    
                buffer = io.BytesIO()
                pil_img.save(buffer, format='PNG')
                return buffer.getvalue()
            
            # Check for URI
            if hasattr(item.image, 'uri'):
                uri = item.image.uri
                
                if isinstance(uri, Path):
                    artifacts_dir = Path(self.config.artifacts_dir)
                    image_path = artifacts_dir / uri
                    try:
                        with open(image_path, 'rb') as f:
                            return f.read()
                    except Exception as e:
                        self._debug_print(f"Error loading image from {image_path}: {e}")
        return None
        
    except Exception as e:
        self._debug_print(f"Error extracting image data for {item.self_ref}: {e}")
        return None