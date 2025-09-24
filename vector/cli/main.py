#!/usr/bin/env python3
"""Main CLI entry point for vector core operations."""

from .commands import main


def cli():
    """Vector Core CLI - Manage vector stores and low-level operations."""
    main()


if __name__ == '__main__':
    cli()