"""Main entry point for RegScout CLI when run as python -m regscout."""

import sys
from .cli.main import main

if __name__ == "__main__":
    sys.exit(main())
