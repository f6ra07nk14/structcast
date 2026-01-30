"""Type definitions for StructCast utilities."""

import os
from pathlib import Path
from typing import Union

PathLike = Union[str, os.PathLike[str], Path]
"""Path-like object."""
