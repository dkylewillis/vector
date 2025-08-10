"""Main entry point for Vector CLI when run as python -m vector."""

import sys
from .cli.main import main

if __name__ == "__main__":
    sys.exit(main())
