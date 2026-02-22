"""Core instantiator logic for StructCast."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import field
from functools import cached_property, partial
from logging import getLogger
from pathlib import Path
from time import time
from typing import Any, Optional, Union, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FilePath,
    SerializerFunctionWrapHandler,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_serializer,
    model_validator,
)
from typing_extensions import Self

from structcast.core.constants import MAX_RECURSION_DEPTH, MAX_RECURSION_TIME
from structcast.core.exceptions import InstantiationError, SpecError
from structcast.utils.base import import_from_address, unroll_call
from structcast.utils.dataclasses import dataclass
from structcast.utils.security import get_default_dir, split_attribute, validate_attribute

logger = getLogger(__name__)


@dataclass(frozen=True)
class PatternResult:
    """Result of pattern matching."""

    patterns: list["BasePattern"] = field(default_factory=list)
    """The list of patterns applied."""

    runs: list[Any] = field(default_factory=list)
    """The list of instantiated objects."""

    depth: int = 0
    """Current recursion depth for security checks."""

    start: float = field(default_factory=time)
    """Start time of instantiation for timeout checks."""


class BasePattern(BaseModel, ABC):
    """Base class for pattern matching."""

    model_config = ConfigDict(frozen=True, validate_default=True, extra="forbid", serialize_by_alias=True)

    @abstractmethod
    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the objects from the pattern.

        Args:
            result (PatternResult | None): The current pattern result.

        Returns:
            PatternResult: The updated pattern result.
        """


_patterns: list[BasePattern] = []


def register_pattern(ptn: BasePattern) -> None:
    """Register a pattern for instantiation."""
    _patterns.append(ptn)


def validate_pattern_result(
    res: Optional[PatternResult],
) -> tuple[type[PatternResult], list[BasePattern], list[Any], int, float]:
    """Validate pattern result and extract components.

    Returns:
        Tuple of (result_type, patterns, runs, depth, start)
    """
    if res is None:
        return PatternResult, [], [], 0, time()
    # Security check: enforce depth limit
    if res.depth >= MAX_RECURSION_DEPTH:
        raise InstantiationError(f"Maximum recursion depth exceeded: {MAX_RECURSION_DEPTH}")
    # Security check: enforce timeout
    if (time() - res.start) > MAX_RECURSION_TIME:
        raise InstantiationError(f"Maximum recursion time exceeded: {MAX_RECURSION_TIME} seconds")
    return type(res), res.patterns, res.runs, res.depth, res.start


class AddressPattern(BasePattern):
    """Pattern for matching addresses."""

    address: str = Field(alias="_addr_", min_length=1)
    """The address to import."""

    file: Optional[FilePath] = Field(None, alias="_file_")
    """Optional path to the module file."""

    @model_validator(mode="before")
    @classmethod
    def _validate_raw(cls, raw: Any) -> Any:
        """Validate the object data."""
        if isinstance(raw, AddressPattern):
            return raw
        if isinstance(raw, (list, tuple)) and raw and raw[0] == "_addr_":
            try:
                if len(raw) == 2:
                    return {"_addr_": TypeAdapter(str).validate_python(raw[1])}
                args = TypeAdapter(tuple[str, Optional[FilePath]]).validate_python(raw[1:])
                return {"_addr_": args[0], "_file_": args[1]}
            except ValidationError as err:
                raise SpecError(f"Invalid AddressPattern format: {err.errors()}") from err
        return raw

    @model_serializer()
    def _serialize_model(self) -> Any:
        """Serialize the model."""
        return ["_addr_", self.address, self.file] if self.file else ["_addr_", self.address]

    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the objects from the pattern."""
        res_t, ptns, runs, depth, start = validate_pattern_result(result)
        run = import_from_address(self.address, module_file=self.file)
        return res_t(patterns=ptns + [self], runs=runs + [run], depth=depth, start=start)


class AttributePattern(BasePattern):
    """Pattern for accessing attributes."""

    attribute: str = Field(alias="_attr_", min_length=1)
    """The attribute to access."""

    @field_validator("attribute", mode="after")
    @classmethod
    def _validate_attribute(cls, attribute: str) -> str:
        """Validate the attribute name."""
        validate_attribute(attribute)
        return attribute

    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the objects from the pattern."""
        res_t, ptns, runs, depth, start = validate_pattern_result(result)
        if not runs:
            raise InstantiationError("No object to access attribute from.")
        runs, last = runs[:-1], runs[-1]
        obj = last
        for attr in cast(list[str], split_attribute(self.attribute)):
            if hasattr(obj, attr):
                obj = getattr(obj, attr)
            else:
                if last == obj:
                    raise InstantiationError(
                        f'Attribute "{attr}" not found in object of type {type(obj).__name__} '
                        f"built from previous patterns: {ptns}"
                    )
                raise InstantiationError(
                    f'Attribute "{attr}" not found in intermediate object of type {type(obj).__name__} '
                    f'while accessing "{self.attribute}" on object of type {type(last).__name__} '
                    f"built from previous patterns: {ptns}"
                )
        return res_t(patterns=ptns + [self], runs=runs + [obj], depth=depth, start=start)


class CallPattern(BasePattern):
    """Pattern for calling callables."""

    call: Any = Field(alias="_call_")
    """The call arguments."""

    @model_validator(mode="before")
    @classmethod
    def _validate_raw(cls, raw: Any) -> Any:
        """Validate the call data."""
        if isinstance(raw, (list, tuple)) and raw and raw[0] == "_call_":
            return {"_call_": raw[1:]}
        if isinstance(raw, str):
            if raw == "_call_":
                return {"_call_": {}}
            raise SpecError(f"Invalid call pattern: {raw}")
        return raw

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler: SerializerFunctionWrapHandler) -> Any:
        """Serialize the model."""
        res = handler(self)
        if isinstance(self.call, (dict, Mapping)):
            return res if self.call else "_call_"
        if isinstance(self.call, (list, tuple)):
            return ["_call_", *res["_call_"]] if self.call else "_call_"
        return res

    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the objects from the pattern."""
        res_t, ptns, runs, depth, start = validate_pattern_result(result)
        if not runs:
            raise InstantiationError("No object to call.")
        runs, last = runs[:-1], runs[-1]
        if callable(last):
            run = unroll_call(instantiate(self.call, __depth__=depth + 1, __start__=start), call=last)
            return res_t(patterns=ptns + [self], runs=runs + [run], depth=depth, start=start)
        msg = f"Object of type {type(last).__name__} built from previous patterns is not callable: {ptns}"
        raise InstantiationError(msg)


class BindPattern(BasePattern):
    """Pattern for partially calling callables."""

    bind: Any = Field(alias="_bind_", min_length=1)
    """The binding arguments."""

    @model_validator(mode="before")
    @classmethod
    def _validate_raw(cls, raw: Any) -> Any:
        """Validate the call data."""
        if isinstance(raw, (list, tuple)) and raw and raw[0] == "_bind_":
            return {"_bind_": raw[1:]}
        return raw

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler: SerializerFunctionWrapHandler) -> Any:
        """Serialize the model."""
        res = handler(self)
        if isinstance(self.bind, (list, tuple)):
            return ["_bind_", *res["_bind_"]]
        return res

    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the objects from the pattern."""
        res_t, ptns, runs, depth, start = validate_pattern_result(result)
        if not runs:
            raise InstantiationError("No object to bind.")
        runs, last = runs[:-1], runs[-1]
        if callable(last):
            param = instantiate(self.bind, __depth__=depth + 1, __start__=start)
            if isinstance(param, (dict, Mapping)):
                run = partial(last, **param)
            elif isinstance(param, (list, tuple)):
                run = partial(last, *param)
            else:
                run = partial(last, param)
            return res_t(patterns=ptns + [self], runs=runs + [run], depth=depth, start=start)
        msg = f"Object of type {type(last).__name__} built from previous patterns is not callable: {ptns}"
        raise InstantiationError(msg)


class ObjectPattern(BasePattern):
    """Pattern for creating objects."""

    object: list[Any] = Field(alias="_obj_", min_length=1)
    """The list of patterns to create the object."""

    @model_validator(mode="before")
    @classmethod
    def _validate_raw(cls, raw: Any) -> Any:
        """Validate the object data."""
        if isinstance(raw, ObjectPattern):
            return raw
        if isinstance(raw, (list, tuple)) and raw and raw[0] == "_obj_":
            return {"_obj_": raw[1:]}
        return raw

    @model_validator(mode="after")
    def _validate_patterns(self) -> Self:
        """Validate the patterns."""
        _ = self.patterns
        return self

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler: SerializerFunctionWrapHandler) -> list[Any]:
        """Serialize the model."""
        return ["_obj_"] + handler(self.patterns)

    @cached_property
    def patterns(self) -> list[BasePattern]:
        """Get the list of patterns."""
        try:
            default_ptns = [AddressPattern, AttributePattern, CallPattern, BindPattern, ObjectPattern]
            return TypeAdapter(list[Union[tuple(_patterns + default_ptns)]]).validate_python(self.object)  # type: ignore[misc]
        except ValidationError as err:
            raise SpecError(f"Failed to validate ObjectPattern contents: {err.errors()}") from err

    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        """Build the runnable from the pattern."""
        res_t, ptns, runs, depth, start = validate_pattern_result(result)
        new = res_t(depth=depth + 1, start=start)
        for ptn in self.patterns:
            new = ptn.build(new)
        if len(new.runs) == 1:
            return res_t(patterns=ptns + [self], runs=runs + new.runs, depth=depth, start=start)
        raise InstantiationError(f"ObjectPattern did not result in a single object (got {new.runs}): {new.patterns}")


def instantiate(cfg: Any, *, __depth__: int = 0, __start__: Optional[float] = None) -> Any:
    """Instantiate an object from a configuration.

    Args:
        cfg (Any): The configuration to instantiate from.
        __depth__ (int): Internal recursion depth counter. DO NOT set manually.
        __start__ (float | None): Internal start time for timeout. DO NOT set manually.

    Returns:
        Any: The instantiated object.

    Raises:
        InstantiationError: If maximum recursion depth is exceeded or instantiation fails.
    """
    # Initialize start time on first call
    if __start__ is None:
        __start__ = time()

    def _instantiate(raw: Any, dep: int) -> Any:
        # Security check: recursion depth
        if dep >= MAX_RECURSION_DEPTH:
            raise InstantiationError(f"Maximum recursion depth exceeded: {MAX_RECURSION_DEPTH}")
        # Security check: timeout
        if (time() - __start__) > MAX_RECURSION_TIME:
            raise InstantiationError(f"Maximum recursion time exceeded: {MAX_RECURSION_TIME} seconds")
        # Security check: primitive types that are safe to return as-is
        if isinstance(raw, (int, float, bool, bytes, Path, type(None))):
            return raw
        # Try to validate as pattern
        try:
            return ObjectPattern.model_validate(raw).build(PatternResult(depth=dep, start=__start__)).runs[0]
        except ValidationError:
            pass
        # Pass through strings and BaseModel instances
        if isinstance(raw, (str, BaseModel)):
            return raw
        # Security check: Validate dict/Mapping types explicitly
        dep += 1
        if type(raw) is dict:
            return {k: _instantiate(v, dep) for k, v in raw.items()}
        if isinstance(raw, Mapping):
            # Use type() to preserve custom Mapping subclasses
            return type(raw)(**{k: _instantiate(v, dep) for k, v in raw.items()})
        # Security check: Validate list/tuple types explicitly
        if isinstance(raw, (list, tuple)):
            return type(raw)(_instantiate(v, dep) for v in raw)
        # Log warning for unrecognized types
        logger.warning(f"Unrecognized configuration type ({type(raw).__name__}). Returning as is.")
        return raw

    return _instantiate(cfg, __depth__)


__all__ = [
    "AddressPattern",
    "AttributePattern",
    "BasePattern",
    "BindPattern",
    "CallPattern",
    "ObjectPattern",
    "PatternResult",
    "instantiate",
    "register_pattern",
    "validate_pattern_result",
]


def __dir__() -> list[str]:
    return get_default_dir(globals())
