"""Type definitions for StructCast utilities."""

from os import PathLike as _PathLike
from pathlib import Path
from typing import Union

from typing_extensions import TypeAlias

import structcast.utils.security

PathLike: TypeAlias = Union[str, _PathLike[str], Path]
"""Path-like object."""

__all__ = ["PathLike"]


def __dir__() -> list[str]:
    return structcast.utils.security.get_default_dir(globals())
