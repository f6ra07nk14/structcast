"""Dataclass utilities."""

import dataclasses
import sys
from typing import Any, Callable, Union

from typing_extensions import dataclass_transform


@dataclass_transform(field_specifiers=(dataclasses.field,))
def dataclass(cls: Any = None, **kwargs: Any) -> Union[Callable[..., Any], Any]:
    """A wrapper around dataclasses.dataclass that adds kw_only and slots parameters for Python 3.10+."""
    other_kw = {"kw_only": True, "slots": True} if sys.version_info >= (3, 10) else {}
    return dataclasses.dataclass(cls, **{**other_kw, **kwargs})
