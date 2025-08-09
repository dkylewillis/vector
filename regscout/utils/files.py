"""File utilities for RegScout."""

import os
from pathlib import Path
from typing import List, Generator


def find_files(directory: str, extensions: List[str]) -> Generator[Path, None, None]:
    """Find files with specific extensions in a directory.
    
    Args:
        directory: Directory to search
        extensions: List of file extensions (e.g., ['.pdf', '.docx'])
        
    Yields:
        Path objects for matching files
    """
    directory = Path(directory)
    if not directory.exists():
        return
    
    for ext in extensions:
        # Ensure extension starts with dot
        if not ext.startswith('.'):
            ext = '.' + ext
        
        # Find files with this extension
        for file_path in directory.rglob(f'*{ext}'):
            if file_path.is_file():
                yield file_path


def ensure_directory(path: str) -> Path:
    """Ensure directory exists, create if needed.
    
    Args:
        path: Directory path
        
    Returns:
        Path object for the directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size(path: str) -> int:
    """Get file size in bytes.
    
    Args:
        path: File path
        
    Returns:
        File size in bytes
    """
    return Path(path).stat().st_size


def is_file_readable(path: str) -> bool:
    """Check if file is readable.
    
    Args:
        path: File path
        
    Returns:
        True if file is readable, False otherwise
    """
    try:
        path = Path(path)
        return path.exists() and path.is_file() and os.access(path, os.R_OK)
    except Exception:
        return False
