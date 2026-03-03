#!/usr/bin/env python3
"""
GUI launcher for the Workspace File Indexer application.
"""

import sys
import os
from pathlib import Path

# Add the current directory to the Python path so we can import core modules
sys.path.insert(0, str(Path(__file__).parent))

# Ensure database is initialized before starting the GUI
from core.db import ensure_database_initialized
from gui.main_window import main

if __name__ == "__main__":
    # Initialize database first
    ensure_database_initialized()

    # Launch the GUI application
    main()