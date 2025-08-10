"""Text processing utilities for Vector."""

import re
from typing import List, Optional


def clean_text(text: str) -> str:
    """Clean and normalize text.
    
    Args:
        text: Raw text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep punctuation
    text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)]', '', text)
    
    return text.strip()


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rstrip() + suffix


def extract_headings(text: str) -> List[str]:
    """Extract potential headings from text.
    
    Args:
        text: Text to analyze
        
    Returns:
        List of potential headings
    """
    headings = []
    
    # Look for lines that might be headings (all caps, short, etc.)
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Simple heuristics for headings
        if (line.isupper() and 3 <= len(line) <= 50) or \
           (line.startswith('CHAPTER') or line.startswith('SECTION')):
            headings.append(line)
    
    return headings[:10]  # Limit to first 10 headings


def count_words(text: str) -> int:
    """Count words in text.
    
    Args:
        text: Text to count
        
    Returns:
        Number of words
    """
    if not text:
        return 0
    return len(text.split())


def split_sentences(text: str) -> List[str]:
    """Split text into sentences.
    
    Args:
        text: Text to split
        
    Returns:
        List of sentences
    """
    # Simple sentence splitting
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]
