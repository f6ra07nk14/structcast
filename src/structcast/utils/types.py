"""Type definitions for COMIC2."""

import os
from pathlib import Path

PathLike = str | os.PathLike[str] | Path
"""Path-like object."""
