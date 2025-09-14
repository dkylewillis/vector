"""Thumbnail path utilities for web interface."""

from typing import Optional, List, Dict, Any, Union
from pathlib import Path

from ..core.models import SearchResultType, ArtifactSearchResult, BaseArtifactMetadata
from ..config import Config


class ThumbnailPathResolver:
    """Utility for resolving thumbnail file paths from search results."""
    
    def __init__(self, config: Config):
        """Initialize with configuration for base paths."""
        # The artifacts are actually stored in converted_documents subdirectory
        self.artifacts_dir = Path(config.artifacts_dir) / "converted_documents"
        self.base_url = getattr(config, 'web_base_url', '/static/artifacts')
    
    def get_thumbnail_file_path(self, metadata: Union[Dict[str, Any], BaseArtifactMetadata]) -> Optional[Path]:
        """Get the actual file system path to a thumbnail.
        
        Args:
            metadata: Artifact metadata (dict or Pydantic model)
            
        Returns:
            Path to thumbnail file if it exists, None otherwise
        """
        # Extract values from metadata (handle both dict and Pydantic models)
        if isinstance(metadata, BaseArtifactMetadata):
            file_hash = metadata.file_hash
            ref_item = metadata.ref_item
        else:
            file_hash = metadata.get('file_hash')
            ref_item = metadata.get('ref_item')
        
        if not file_hash or not ref_item:
            return None
        
        # Clean ref_item to get just the ID (e.g., "#/images/5" -> "5")
        ref_id = ref_item.split('/')[-1] if '/' in ref_item else ref_item
        
        # Construct path: artifacts_dir/file_hash/images/
        images_dir = self.artifacts_dir / file_hash / "images"
        
        if not images_dir.exists():
            return None
        
        # Look for thumbnail files with the pattern: thumbnail_XXXXXX_<hash>_thumb.png
        # where XXXXXX is the ref_id padded to 6 digits with zeros
        try:
            ref_num = int(ref_id)
            ref_padded = f"{ref_num:06d}"  # Pad to 6 digits with zeros
            
            # Pattern: thumbnail_000000_*_thumb.png
            thumbnail_pattern = f"thumbnail_{ref_padded}_*_thumb.png"
            matching_files = list(images_dir.glob(thumbnail_pattern))
            
            if matching_files:
                return matching_files[0]  # Return first match
                
        except ValueError:
            # If ref_id is not a number, skip this approach
            pass
        
        # Fallback patterns
        fallback_patterns = [
            f"thumbnail_{ref_id}_*.png",
            f"{ref_id}.png",
            f"{ref_id}.jpg"
        ]
        
        for pattern in fallback_patterns:
            matching_files = list(images_dir.glob(pattern))
            if matching_files:
                return matching_files[0]
        
        return None
    
    def get_thumbnail_web_url(self, metadata: Union[Dict[str, Any], BaseArtifactMetadata]) -> Optional[str]:
        """Get the web URL for a thumbnail.
        
        Args:
            metadata: Artifact metadata (dict or Pydantic model)
            
        Returns:
            Web URL string if thumbnail exists, None otherwise
        """
        thumbnail_path = self.get_thumbnail_file_path(metadata)
        if not thumbnail_path:
            return None
        
        # Convert file path to web URL
        # e.g., artifacts/abc123/thumbnails/5.jpg -> /static/artifacts/abc123/thumbnails/5.jpg
        relative_path = thumbnail_path.relative_to(self.artifacts_dir)
        return f"{self.base_url}/{relative_path.as_posix()}"
    
    def extract_thumbnails_from_search_results(self, search_results: List[SearchResultType]) -> List[str]:
        """Extract thumbnail file paths from search results.
        
        Args:
            search_results: List of search results from agent
            
        Returns:
            List of valid thumbnail file paths (filters out None values for Gradio compatibility)
        """
        thumbnails = []
        
        for result in search_results:
            if isinstance(result, ArtifactSearchResult):
                # Try to get thumbnail file path (not web URL)
                thumbnail_path = self.get_thumbnail_file_path(result.metadata)
                if thumbnail_path and thumbnail_path.exists():
                    thumbnails.append(str(thumbnail_path))
                # Skip None values - don't append anything if thumbnail doesn't exist
            # Skip non-artifact results - don't append anything for chunk results
        
        return thumbnails


def create_thumbnail_resolver(config: Config) -> ThumbnailPathResolver:
    """Factory function to create a thumbnail resolver."""
    return ThumbnailPathResolver(config)