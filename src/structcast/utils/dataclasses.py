"""Dataclass utilities."""

from dataclasses import dataclass as std_dataclass, field
from sys import version_info
from typing import Any, Callable, Union

from typing_extensions import dataclass_transform


@dataclass_transform(field_specifiers=(field,))
def dataclass(cls: Any = None, **kwargs: Any) -> Union[Callable[..., Any], Any]:
    """A wrapper around dataclasses.dataclass that adds kw_only and slots parameters for Python 3.10+."""
    other_kw = {"kw_only": True, "slots": True} if version_info >= (3, 10) else {}
    return std_dataclass(cls, **{**other_kw, **kwargs})
