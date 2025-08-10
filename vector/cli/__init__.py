"""CLI package for Vector."""

from .main import main, VectorCLI
from .parser import create_parser

__all__ = ['main', 'VectorCLI', 'create_parser']
