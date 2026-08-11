"""Constants for StructCast utilities."""

from typing import TYPE_CHECKING

from structcast.utils.lazy_import import DEFAULT_ALLOWED_DUNDERS

DEFAULT_DANGEROUS_DUNDERS: set[str] = {
    *{"__subclasses__", "__bases__", "__globals__", "__code__", "__dict__"},
    *{"__class__", "__mro__", "__init__", "__import__"},
}
"""Default dangerous dunder attributes to block during instantiation."""

__all__ = [
    "DEFAULT_ALLOWED_DUNDERS",
    "DEFAULT_DANGEROUS_DUNDERS",
]

if not TYPE_CHECKING:
    import sys

    from structcast.utils.lazy_import import LazySelectedImporter

    sys.modules[__name__] = LazySelectedImporter(__name__, globals())
