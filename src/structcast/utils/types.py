"""Type definitions for StructCast utilities."""

from os import PathLike as _PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Union

from typing_extensions import TypeAlias

PathLike: TypeAlias = Union[str, _PathLike[str], Path]
"""Path-like object."""

__all__ = ["PathLike"]


if not TYPE_CHECKING:
    import sys

    from structcast.utils.lazy_import import LazySelectedImporter

    sys.modules[__name__] = LazySelectedImporter(__name__, globals())
