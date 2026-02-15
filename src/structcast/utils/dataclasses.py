"""Dataclass utilities."""

from dataclasses import dataclass as std_dataclass, field
from sys import version_info
from typing import Any, Callable, Literal, Optional, TypeVar, Union, overload

from typing_extensions import dataclass_transform

T = TypeVar("T")


@overload
def dataclass(cls: Literal[None] = None, **kwargs: Any) -> Callable[..., type[T]]: ...


@overload
def dataclass(cls: type[T], **kwargs: Any) -> type[T]: ...


@dataclass_transform(field_specifiers=(field,))
def dataclass(cls: Optional[type[T]] = None, **kwargs: Any) -> Union[Callable[..., type[T]], type[T]]:
    """A wrapper around dataclasses.dataclass that adds kw_only and slots parameters for Python 3.10+."""
    other_kw = {"kw_only": True, "slots": True} if version_info >= (3, 10) else {}
    return std_dataclass(cls, **{**other_kw, **kwargs})
