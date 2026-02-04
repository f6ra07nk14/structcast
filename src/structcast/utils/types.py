"""Type definitions for StructCast utilities."""

from os import PathLike as _PathLike
from pathlib import Path
from typing import Union

from typing_extensions import TypeAlias

PathLike: TypeAlias = Union[str, _PathLike[str], Path]
"""Path-like object."""
