"""Type definitions for StructCast utilities."""

import os
from pathlib import Path
from typing import Union

from typing_extensions import TypeAlias

PathLike: TypeAlias = Union[str, os.PathLike[str], Path]
"""Path-like object."""
