import hashlib
from typing import Optional
from PIL import Image as PILImage

def extract_ref_id(ref_item: str) -> int:
    """Extract the numeric ID from a ref_item string.

    Args:
        ref_item: Reference item string like "#/tables/0" or "#/images/5"

    Returns:
        The numeric ID as int, or -1 if no pattern match

    Examples:
        >>> extract_ref_id("#/tables/0")
        0
        >>> extract_ref_id("#/images/5") 
        5
        >>> extract_ref_id("simple_string")
        -1
    """
    try:
        # Get the last part after the final "/"
        last_part = ref_item.split('/')[-1]
        return int(last_part)
    except (ValueError, AttributeError, IndexError):
        return -1
    
def image_to_hexhash(img: Optional[PILImage.Image]) -> Optional[str]:
    """Hexash from the image."""
    if img is not None:
        # Convert the image to raw bytes
        image_bytes = img.tobytes()

        # Create a hash object (e.g., SHA-256)
        hasher = hashlib.sha256(usedforsecurity=False)

        # Feed the image bytes into the hash object
        hasher.update(image_bytes)

        # Get the hexadecimal representation of the hash
        return hasher.hexdigest()

    return None