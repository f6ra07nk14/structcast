"""Core instantiation logic for StructCast."""

import abc
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import partial
import logging
from pathlib import Path
import sys
from typing import Any, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FilePath,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)
from typing_extensions import TypeAlias

from structcast.utils.base import import_from_address, validate_attribute

__logger = logging.getLogger(__name__)

# check python version to support kw_only and slots in dataclass
__dataclass_kw = {"kw_only": True, "slots": True} if sys.version_info >= (3, 10) else {}


@dataclass(**__dataclass_kw, frozen=True)
class PatternResult:
    """Result of pattern matching."""

    patterns: list["BasePattern"] = field(default_factory=list)
    """The list of patterns applied."""

    runs: list[Any] = field(default_factory=list)
    """The list of instantiated objects."""


class InstantiationError(Exception):
    """Exception raised for errors during instantiation."""


class BasePattern(BaseModel, abc.ABC):
    """Base class for pattern matching."""

    model_config = ConfigDict(frozen=True, validate_default=True, extra="forbid", serialize_by_alias=True)

    @abc.abstractmethod
    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the objects from the pattern.

        Args:
            result (Optional[PatternResult]): The current pattern result.

        Returns:
            PatternResult: The updated pattern result.
        """


def _validate_pattern_result(res: Optional[PatternResult]) -> tuple[type[PatternResult], list[BasePattern], list[Any]]:
    return (PatternResult, [], []) if res is None else (type(res), res.patterns, res.runs)


class AddressPattern(BasePattern):
    """Pattern for matching addresses."""

    address: str = Field(alias="_addr_", min_length=1)
    """The address to import."""

    file: Optional[FilePath] = Field(None, alias="_file_")
    """Optional path to the module file."""

    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the objects from the pattern."""
        res_t, ptns, runs = _validate_pattern_result(result)
        return res_t(patterns=ptns + [self], runs=runs + [import_from_address(self.address, module_file=self.file)])


class AttributePattern(BasePattern):
    """Pattern for accessing attributes."""

    attribute: str = Field(alias="_attr_", min_length=1)
    """The attribute to access."""

    @field_validator("attribute", mode="after")
    @classmethod
    def validate_attribute(cls, attribute: str) -> str:
        """Validate the attribute name."""
        validate_attribute(attribute)
        return attribute

    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the objects from the pattern."""
        res_t, ptns, runs = _validate_pattern_result(result)
        if not runs:
            raise InstantiationError("No object to access attribute from.")
        runs, last = runs[:-1], runs[-1]
        if hasattr(last, self.attribute):
            return res_t(patterns=ptns + [self], runs=runs + [getattr(last, self.attribute)])
        msg = f'Attribute "{self.attribute}" not found in object ({last}) with previous patterns: {ptns}'
        raise InstantiationError(msg)


class CallPattern(BasePattern):
    """Pattern for calling callables."""

    call: Mapping[str, Any] = Field(alias="_call_")
    """The call arguments."""

    @model_validator(mode="before")
    @classmethod
    def validate_raw(cls, data: Any) -> Any:
        """Validate the call data."""
        if isinstance(data, str):
            if data == "_call_":
                return {"_call_": {}}
            raise ValueError(f"Invalid call pattern: {data}")
        return data

    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the objects from the pattern."""
        res_t, ptns, runs = _validate_pattern_result(result)
        if not runs:
            raise InstantiationError("No object to call.")
        runs, last = runs[:-1], runs[-1]
        if callable(last):
            return res_t(patterns=ptns + [self], runs=runs + [last(**instantiate(self.call))])
        raise InstantiationError(f"Object ({last}) is not callable with previous patterns: {ptns}")


class BindPattern(BasePattern):
    """Pattern for partially calling callables."""

    bind: Mapping[str, Any] = Field(alias="_bind_", min_length=1)
    """The binding arguments."""

    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the objects from the pattern."""
        res_t, ptns, runs = _validate_pattern_result(result)
        if not runs:
            raise InstantiationError("No object to bind.")
        runs, last = runs[:-1], runs[-1]
        if callable(last):
            return res_t(patterns=ptns + [self], runs=runs + [partial(last, **instantiate(self.bind))])
        raise InstantiationError(f"Object ({last}) is not callable with previous patterns: {ptns}")


class ObjectPattern(BasePattern):
    """Pattern for creating objects."""

    object: list[Any] = Field(alias="_obj_", min_length=1)
    """The list of patterns to create the object."""

    @model_validator(mode="before")
    @classmethod
    def validate_raw(cls, data: Any) -> Any:
        """Validate the object data."""
        if isinstance(data, (list, tuple)) and data and data[0] == "_obj_":
            return {"_obj_": data[1:]}
        return data

    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the runnable from the pattern."""
        res_t, ptns, runs = _validate_pattern_result(result)
        new = res_t()
        try:
            for ptn in TypeAdapter(list[PatternLike]).validate_python(self.object):
                new = ptn.build(new)
        except ValidationError as err:
            raise InstantiationError(f"Failed to validate ObjectPattern contents: {err.errors()}") from err
        if len(new.runs) != 1:
            msg = f"ObjectPattern did not result in a single object (got {new.runs}): {new.patterns}"
            raise InstantiationError(msg)
        return res_t(patterns=ptns + [self], runs=runs + new.runs)


PatternLike: TypeAlias = Union[AddressPattern, AttributePattern, CallPattern, BindPattern, ObjectPattern]


def instantiate(cfg: Any) -> Any:
    """Instantiate an object from a configuration.

    Args:
        cfg (Any): The configuration to instantiate from.

    Returns:
        Any: The instantiated object.
    """
    if isinstance(cfg, (int, float, bool, bytes, Path, type(None))):
        return cfg
    try:
        res = ObjectPattern.model_validate(cfg).build(PatternResult())
        if len(res.runs) != 1:
            msg = f"ObjectPattern did not result in a single object (got {res.runs}): {res.patterns}"
            raise InstantiationError(msg)
        return res.runs[0]
    except ValidationError:
        pass
    if isinstance(cfg, (str, BaseModel)):
        return cfg
    if isinstance(cfg, (dict, Mapping)):
        return type(cfg)(**{k: instantiate(v) for k, v in cfg.items()})
    if isinstance(cfg, (list, tuple)):
        return type(cfg)(instantiate(v) for v in cfg)
    __logger.warning(f"Unrecognized configuration type ({type(cfg)}). Returning as is.")
    return cfg
