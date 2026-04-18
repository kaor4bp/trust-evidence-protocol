from __future__ import annotations

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent.parent

tests_dir_str = str(TESTS_DIR)
if tests_dir_str not in sys.path:
    sys.path.insert(0, tests_dir_str)
