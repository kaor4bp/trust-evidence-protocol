from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationError:
    path: Path
    message: str

