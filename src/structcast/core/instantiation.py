"""Core instantiation logic for StructCast."""

import abc
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import partial
import logging
from pathlib import Path
import sys
import time
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

from structcast.core.constants import MAX_INSTANTIATION_DEPTH, MAX_INSTANTIATION_TIME
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

    depth: int = 0
    """Current recursion depth for security checks."""

    start_time: float = field(default_factory=time.time)
    """Start time of instantiation for timeout checks."""


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


def _validate_pattern_result(
    res: Optional[PatternResult],
) -> tuple[type[PatternResult], list[BasePattern], list[Any], int, float]:
    """Validate pattern result and extract components.

    Returns:
        Tuple of (result_type, patterns, runs, depth, start_time)
    """
    if res is None:
        return PatternResult, [], [], 0, time.time()
    # Security check: enforce depth limit
    if res.depth >= MAX_INSTANTIATION_DEPTH:
        raise InstantiationError(f"Maximum instantiation depth exceeded: {MAX_INSTANTIATION_DEPTH}")
    # Security check: enforce timeout
    elapsed = time.time() - res.start_time
    if elapsed > MAX_INSTANTIATION_TIME:
        raise InstantiationError(f"Maximum instantiation time exceeded: {MAX_INSTANTIATION_TIME} seconds")
    return type(res), res.patterns, res.runs, res.depth, res.start_time


class AddressPattern(BasePattern):
    """Pattern for matching addresses."""

    address: str = Field(alias="_addr_", min_length=1)
    """The address to import."""

    file: Optional[FilePath] = Field(None, alias="_file_")
    """Optional path to the module file."""

    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the objects from the pattern."""
        res_t, ptns, runs, depth, start_time = _validate_pattern_result(result)
        run = import_from_address(self.address, module_file=self.file)
        return res_t(patterns=ptns + [self], runs=runs + [run], depth=depth, start_time=start_time)


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
        res_t, ptns, runs, depth, start_time = _validate_pattern_result(result)
        if not runs:
            raise InstantiationError("No object to access attribute from.")
        runs, last = runs[:-1], runs[-1]
        if hasattr(last, self.attribute):
            run = getattr(last, self.attribute)
            return res_t(patterns=ptns + [self], runs=runs + [run], depth=depth, start_time=start_time)
        typ_n = type(last).__name__
        msg = f'Attribute "{self.attribute}" not found in object of type {typ_n} built from previous patterns: {ptns}'
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
        res_t, ptns, runs, depth, start_time = _validate_pattern_result(result)
        if not runs:
            raise InstantiationError("No object to call.")
        runs, last = runs[:-1], runs[-1]
        if callable(last):
            run = last(**instantiate(self.call, __depth__=depth + 1, __start_time__=start_time))
            return res_t(patterns=ptns + [self], runs=runs + [run], depth=depth, start_time=start_time)
        msg = f"Object of type {type(last).__name__} built from previous patterns is not callable: {ptns}"
        raise InstantiationError(msg)


class BindPattern(BasePattern):
    """Pattern for partially calling callables."""

    bind: Mapping[str, Any] = Field(alias="_bind_", min_length=1)
    """The binding arguments."""

    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the objects from the pattern."""
        res_t, ptns, runs, depth, start_time = _validate_pattern_result(result)
        if not runs:
            raise InstantiationError("No object to bind.")
        runs, last = runs[:-1], runs[-1]
        if callable(last):
            run = partial(last, **instantiate(self.bind, __depth__=depth + 1, __start_time__=start_time))
            return res_t(patterns=ptns + [self], runs=runs + [run], depth=depth, start_time=start_time)
        msg = f"Object of type {type(last).__name__} built from previous patterns is not callable: {ptns}"
        raise InstantiationError(msg)


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
        res_t, ptns, runs, depth, start_time = _validate_pattern_result(result)
        new = res_t(depth=depth + 1, start_time=start_time)
        try:
            for ptn in TypeAdapter(list[PatternLike]).validate_python(self.object):
                new = ptn.build(new)
        except ValidationError as err:
            raise InstantiationError(f"Failed to validate ObjectPattern contents: {err.errors()}") from err
        if len(new.runs) == 1:
            return res_t(patterns=ptns + [self], runs=runs + new.runs, depth=depth, start_time=start_time)
        raise InstantiationError(f"ObjectPattern did not result in a single object (got {new.runs}): {new.patterns}")


PatternLike: TypeAlias = Union[AddressPattern, AttributePattern, CallPattern, BindPattern, ObjectPattern]


def instantiate(cfg: Any, *, __depth__: int = 0, __start_time__: Optional[float] = None) -> Any:
    """Instantiate an object from a configuration.

    Args:
        cfg (Any): The configuration to instantiate from.
        __depth__ (int): Internal recursion depth counter. DO NOT set manually.
        __start_time__ (Optional[float]): Internal start time for timeout. DO NOT set manually.

    Returns:
        Any: The instantiated object.

    Raises:
        InstantiationError: If maximum recursion depth is exceeded or instantiation fails.
    """
    # Initialize start time on first call
    if __start_time__ is None:
        __start_time__ = time.time()
    # Security check: recursion depth
    if __depth__ >= MAX_INSTANTIATION_DEPTH:
        raise InstantiationError(f"Maximum instantiation depth exceeded: {MAX_INSTANTIATION_DEPTH}")
    # Security check: timeout
    elapsed = time.time() - __start_time__
    if elapsed > MAX_INSTANTIATION_TIME:
        raise InstantiationError(f"Maximum instantiation time exceeded: {MAX_INSTANTIATION_TIME} seconds")
    # Security check: primitive types that are safe to return as-is
    if isinstance(cfg, (int, float, bool, bytes, Path, type(None))):
        return cfg
    # Try to validate as pattern
    try:
        res = ObjectPattern.model_validate(cfg).build(PatternResult(depth=__depth__, start_time=__start_time__))
        if len(res.runs) == 1:
            return res.runs[0]
        raise InstantiationError(f"Instantiation did not result in a single object (got {res.runs}): {res.patterns}")
    except ValidationError:
        pass
    # Pass through strings and BaseModel instances
    if isinstance(cfg, (str, BaseModel)):
        return cfg
    # Security check: Validate dict/Mapping types explicitly
    nest_kw: dict[str, Any] = {"__depth__": __depth__ + 1, "__start_time__": __start_time__}
    if isinstance(cfg, dict):
        return {k: instantiate(v, **nest_kw) for k, v in cfg.items()}
    if isinstance(cfg, Mapping):
        # Use type() to preserve custom Mapping subclasses
        return type(cfg)(**{k: instantiate(v, **nest_kw) for k, v in cfg.items()})
    # Security check: Validate list/tuple types explicitly
    if isinstance(cfg, list):
        return [instantiate(v, **nest_kw) for v in cfg]
    if isinstance(cfg, tuple):
        return tuple(instantiate(v, **nest_kw) for v in cfg)
    # Log warning for unrecognized types
    __logger.warning(f"Unrecognized configuration type ({type(cfg).__name__}). Returning as is.")
    return cfg
