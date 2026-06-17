"""
tests/conftest.py
─────────────────
Shared test fixtures and path configuration.
"""

import sys
from pathlib import Path

# Ensure the backend directory is on sys.path so 'from app...' imports work
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
