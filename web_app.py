#!/usr/bin/env python3
"""
RegScout Web Interface Entry Point
Launch with: python web_app.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.web.app import create_regscout_app

if __name__ == "__main__":
    print("🚀 Starting RegScout Web Interface...")
    print("📍 Navigate to: http://127.0.0.1:7860")
    
    app = create_regscout_app()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        debug=True
    )
