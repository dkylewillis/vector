#!/usr/bin/env python3
"""Standalone CLI runner for vector core operations."""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vector.cli.main import cli

if __name__ == '__main__':
    cli()