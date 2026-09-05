"""
Ensure the project root is on sys.path so that `from src.xxx import yyy`
works when running pytest from the project root.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
