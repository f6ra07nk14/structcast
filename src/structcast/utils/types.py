"""Type definitions for StructCast utilities."""

from os import PathLike as OsPathLike
from pathlib import Path
from typing import Union

from typing_extensions import TypeAlias

PathLike: TypeAlias = Union[str, OsPathLike[str], Path]
"""Path-like object."""
