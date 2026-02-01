"""Dataclass utilities."""

import dataclasses
import sys
from typing import Any, Callable, Literal, Optional, TypeVar, Union, overload

T = TypeVar("T")


@overload
def dataclass(cls: type[T], **kwargs: Any) -> type[T]: ...


@overload
def dataclass(cls: Literal[None] = None, **kwargs: Any) -> Callable[..., type[T]]: ...


def dataclass(cls: Optional[type[T]] = None, **kwargs: Any) -> Union[Callable[..., type[T]], type[T]]:
    """A wrapper around dataclasses.dataclass that adds kw_only and slots parameters for Python 3.10+."""
    other_kw = {"kw_only": True, "slots": True} if sys.version_info >= (3, 10) else {}
    return dataclasses.dataclass(cls, **{**other_kw, **kwargs})
