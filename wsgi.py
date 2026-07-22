"""PythonAnywhere WSGI entry point.

On PythonAnywhere's "Web" tab, point the WSGI configuration file at this
module (or copy its contents into the one PythonAnywhere generates) so the
`application` object below is what gets served.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app as application  # noqa: E402
