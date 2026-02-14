"""Module for specification conversion and resolver registration."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from copy import copy, deepcopy
from enum import Enum
from functools import cached_property, partial
from logging import getLogger
from time import time
from typing import Any, Callable, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    TypeAdapter,
    ValidationError,
    field_serializer,
    field_validator,
    model_serializer,
    model_validator,
)
from typing_extensions import Self

from structcast.core.constants import SPEC_FORMAT, SPEC_SOURCE
from structcast.core.exceptions import SpecError
from structcast.core.instantiator import ObjectPattern
from structcast.utils.base import check_elements, unroll_call
from structcast.utils.dataclasses import dataclass
from structcast.utils.security import SecurityError, split_attribute, validate_attribute

logger = getLogger(__name__)


class ReturnType(Enum):
    """Enumeration of return types for specification access."""

    REFERENCE = "reference"
    """Return a reference to the original data."""

    SHALLOW_COPY = "shallow_copy"
    """Return a shallow copy of the data."""

    DEEP_COPY = "deep_copy"
    """Return a deep copy of the data."""


@dataclass
class SpecSettings:
    """Settings for specification conversion and accessors."""

    support_basemodel: bool = True
    """Whether to support BaseModel access."""

    support_attribute: bool = True
    """Whether to support attribute access on objects."""

    raise_error: bool = False
    """Whether to raise an error when access fails."""

    return_type: ReturnType = ReturnType.REFERENCE
    """The default return type for access operations."""


_spec_settings = SpecSettings()
"""Global specification settings instance."""

_resolvers: dict[str, tuple[str, Callable[[str], Any]]] = {}
"""Registered resolvers for specification conversion."""

_accessers: list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]] = []
"""Registered accessers for data access."""


def register_resolver(name: str, resolver: Callable[[str], Any]) -> str:
    """Register a resolver for specification conversion.

    Args:
        name (str): The name of the resolver.
        resolver (Callable[[str], Any]): The resolver function that takes a string and returns a resolved value.

    Returns:
        str: The specification identifier for the registered resolver.

    Raises:
        ValueError: If the resolver name is already registered.
    """
    if name in _resolvers:
        raise ValueError(f"Resolver '{name}' is already registered.")
    spec_id = SPEC_FORMAT.format(resolver=name)
    _resolvers[name] = spec_id, resolver
    return spec_id


def register_accesser(data_type: type, accesser: Callable[[Any, Union[str, int]], tuple[bool, Any]]) -> None:
    """Register an accesser for data access.

    Args:
        data_type (type): The type of data the accesser can handle.
        accesser (Callable[[Any, Union[str, int]], tuple[bool, Any]]): The accesser function that takes an instance
            and an index, and returns a tuple of success (bool) and value (Any).
    """
    _accessers.append((data_type, accesser))


def configure_spec(
    settings: Optional[SpecSettings] = None,
    *,
    support_basemodel: Optional[bool] = None,
    support_attribute: Optional[bool] = None,
    raise_error: Optional[bool] = None,
    return_type: Optional[ReturnType] = None,
) -> None:
    """Configure global specification settings.

    Args:
        settings (SpecSettings | None): An instance of SpecSettings to use for configuration.
            If provided, individual keyword arguments will be ignored.
            If None, individual keyword arguments will be used for configuration.
        support_basemodel (bool | None, optional): Whether to support BaseModel access.
            If None, the setting is not changed.
        support_attribute (bool | None, optional): Whether to support attribute access on objects.
            If None, the setting is not changed.
        raise_error (bool | None, optional): Whether to raise an error when access fails.
            If None, the setting is not changed.
        return_type (ReturnType | None, optional): The default return type for access operations.
            If None, the setting is not changed.
    """
    if settings is None:
        kwargs: dict[str, Any] = {}
        if support_basemodel is not None:
            kwargs["support_basemodel"] = support_basemodel
        if support_attribute is not None:
            kwargs["support_attribute"] = support_attribute
        if raise_error is not None:
            kwargs["raise_error"] = raise_error
        if return_type is not None:
            kwargs["return_type"] = return_type
        settings = SpecSettings(**kwargs)
    _spec_settings.support_basemodel = settings.support_basemodel
    _spec_settings.support_attribute = settings.support_attribute
    _spec_settings.raise_error = settings.raise_error
    _spec_settings.return_type = settings.return_type


@dataclass(frozen=True)
class SpecIntermediate:
    """Intermediate representation of a specification."""

    identifier: str
    """The specification identifier."""

    value: Any
    """The resolved value."""

    @classmethod
    def convert_spec(cls, raw: Optional[Union[str, int, float, bool, bytes]]) -> Self:
        """Convert a raw specification into a structured format.

        Args:
            raw (str | int | float | bool | bytes | None): The raw specification input.

        Returns:
            SpecIntermediate: A tuple containing the specification identifier and parameters.
        """
        if not isinstance(raw, str):
            return cls(identifier=SPEC_CONSTANT, value=raw)
        if not raw:
            return cls(identifier=SPEC_SOURCE, value=())
        for spec_name, (spec_id, resolver) in _resolvers.items():
            prefix = f"{spec_name}:"
            if raw.lower().startswith(prefix):
                return cls(identifier=spec_id, value=resolver(raw[len(prefix) :].strip()))
        try:
            return cls(identifier=SPEC_SOURCE, value=split_attribute(raw))
        except ValueError as e:
            raise SpecError(f"Invalid specification format: {raw}") from e


SPEC_CONSTANT = register_resolver("constant", lambda x: x)
SPEC_SKIP: str = register_resolver("skip", lambda _: SPEC_SKIP)
SPEC_PLACEHOLDER = register_resolver("placeholder", lambda x: SpecIntermediate.convert_spec(x or "skip:"))


def convert_spec(cfg: Any, *, __depth__: int = 0, __start__: Optional[float] = None) -> Any:
    """Convert a structured specification input into a resolved format.

    Args:
        cfg (Any): The structured specification input.
        __depth__ (int, optional): The current recursion depth. Used internally for recursion control.
        __start__ (float | None, optional): The start time of the conversion process.
            Used internally for recursion control.

    Returns:
        Any: The resolved specification.

    Raises:
        SpecError: If the specification type is unsupported.
    """
    # Initialize start time on first call
    if __start__ is None:
        __start__ = time()

    def _convert(raw: Any, dep: int) -> Any:
        if isinstance(raw, (str, int, float, bool, bytes)) or raw is None:
            return SpecIntermediate.convert_spec(raw)
        dep += 1
        if type(raw) is dict:
            return {k: _convert(v, dep) for k, v in raw.items()}
        if isinstance(raw, Mapping):
            return type(raw)(**{k: _convert(v, dep) for k, v in raw.items()})
        if isinstance(raw, (list, tuple)):
            return type(raw)(_convert(v, dep) for v in raw)
        raise SpecError(f"Unsupported specification type: {type(raw)}")

    return _convert(cfg, __depth__)


def _str_index(index: Union[int, str]) -> str:
    if isinstance(index, int):
        return str(index)
    if not index.isidentifier():
        index = index.replace('"', '\\"')
        return f'"{index}"'
    return index


def _str_source(source: tuple[Union[int, str], ...]) -> str:
    return ".".join(_str_index(i) for i in source)


def _return_ref(data: Any) -> Any:
    return data


def _return_shallow(data: Any) -> Any:
    return data.model_copy(deep=False) if isinstance(data, BaseModel) else copy(data)


def _return_deep(data: Any) -> Any:
    return data.model_copy(deep=True) if isinstance(data, BaseModel) else deepcopy(data)


__return_mapping: dict[ReturnType, Callable[[Any], Any]] = {
    ReturnType.REFERENCE: _return_ref,
    ReturnType.SHALLOW_COPY: _return_shallow,
    ReturnType.DEEP_COPY: _return_deep,
}


def _return_value(data: Any, *, return_type: ReturnType) -> Any:
    return data if data is None else __return_mapping[return_type](data)


def _access_default(
    data: Any,
    source: tuple[Union[int, str], ...],
    return_type: ReturnType,
    accessers: list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]],
    raise_error: bool,
) -> Any:
    def _access(target: Any, indices: tuple[Union[int, str], ...]) -> Any:
        if not indices:
            return target
        index, indices = indices[0], indices[1:]
        if isinstance(target, (dict, Mapping)):
            if index in target:
                return _return_value(_access(target[index], indices), return_type=return_type)
            else:
                i_str, s_str = _str_index(index), _str_source(source)
                msg = f"Key ({i_str}) not found in mapping at source ({s_str}): {data}"
        elif isinstance(target, (list, tuple)):
            if isinstance(index, int):
                if 0 <= index < len(target):
                    return _return_value(_access(target[index], indices), return_type=return_type)
                else:
                    i_str, s_str = _str_index(index), _str_source(source)
                    msg = f"Index ({i_str}) out of range in sequence at source ({s_str}): {data}"
            else:
                i_str, s_str = _str_index(index), _str_source(source)
                msg = f"Non-integer index ({i_str}) used for sequence at source ({s_str}): {data}"
        else:
            i_str, s_str = _str_index(index), _str_source(source)
            for data_type, accesser in accessers:
                if isinstance(target, data_type):
                    success, value = accesser(target, index)
                    if success:
                        return _return_value(_access(value, indices), return_type=return_type)
                    t_str = data_type.__name__
                    logger.debug(f"Accesser for type ({t_str}) failed to access index ({i_str}) at source ({s_str}).")
            msg = f"Cannot index into type ({type(target).__name__}) at source ({s_str}): {data}"
        if raise_error:
            raise SpecError(msg)
        logger.warning(msg)
        return None

    return _access(data, source)


def _access_basemodel(instance: BaseModel, index: Union[str, int]) -> tuple[bool, Any]:
    if index in instance.model_fields_set:
        return True, instance.model_dump(include={index})[index]
    return False, None


def _access_attribute(instance: Any, index: Union[str, int]) -> tuple[bool, Any]:
    if isinstance(index, str):
        try:
            validate_attribute(index)
            if hasattr(instance, index):
                return True, getattr(instance, index)
        except SecurityError:
            pass
    return False, None


def access(
    data: Any,
    source: tuple[Union[int, str], ...],
    *,
    return_type: Optional[ReturnType] = None,
    support_basemodel: Optional[bool] = None,
    support_attribute: Optional[bool] = None,
    accessers: Optional[list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]]] = None,
    raise_error: Optional[bool] = None,
) -> Any:
    """Access a value from data based on the provided source path.

    Args:
        data (Any): The data to access.
        source (tuple[int | str, ...]): The path to access within the data.
        return_type (ReturnType | None, optional): The type of access to use.
            Default is taken from global settings.
        support_basemodel (bool | None, optional): Whether to support BaseModel access.
            Default is taken from global settings.
        support_attribute (bool | None, optional): Whether to support attribute access on objects.
            Default is taken from global settings.
        accessers (list[tuple[type, Callable[[Any, int | str], tuple[bool, Any]]]] | None, optional):
            A custom list of type-accesser pairs to use for accessing data.
            Each accesser is a callable that takes an instance and an index,
            and returns a tuple of success (bool) and value (Any). Default is taken from global settings.
        raise_error (bool | None, optional): Whether to raise an error when access fails.
            Default is taken from global settings.

    Returns:
        Any: The accessed value.

    Raises:
        AccessError: If access fails and raise_error is True.
    """
    return_type = _spec_settings.return_type if return_type is None else return_type
    accessers = _accessers if accessers is None else accessers
    support_attribute = _spec_settings.support_attribute if support_attribute is None else support_attribute
    support_basemodel = _spec_settings.support_basemodel if support_basemodel is None else support_basemodel
    if support_attribute:
        accessers = [(object, _access_attribute)] + accessers
    if support_basemodel:
        accessers = [(BaseModel, _access_basemodel)] + accessers
    raise_error = _spec_settings.raise_error if raise_error is None else raise_error
    return _access_default(data, source, return_type, accessers, raise_error)


def construct(
    data: Any,
    spec: Any,
    *,
    return_type: Optional[ReturnType] = None,
    support_basemodel: Optional[bool] = None,
    support_attribute: Optional[bool] = None,
    accessers: Optional[list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]]] = None,
    raise_error: Optional[bool] = None,
) -> Any:
    """Construct a value from data based on the structured specification.

    Args:
        data (Any): The data to construct from.
        spec (Any): The structured specification.
        return_type (ReturnType | None, optional): The type of access to use.
            Default is taken from global settings.
        support_basemodel (bool | None, optional): Whether to support BaseModel access.
            Default is taken from global settings.
        support_attribute (bool | None, optional): Whether to support attribute access on objects.
            Default is taken from global settings.
        accessers (list[tuple[type, Callable[[Any, int | str], tuple[bool, Any]]]] | None, optional):
            A custom list of type-accesser pairs to use for accessing data.
            Each accesser is a callable that takes an instance and an index,
            and returns a tuple of success (bool) and value (Any). Default is taken from global settings.
        raise_error (bool | None, optional): Whether to raise an error when access fails.
            Default is taken from global settings.

    Returns:
        Any: The constructed value.

    Raises:
        AccessError: If access fails and raise_error is True.
    """
    kwargs: dict[str, Any] = {
        "return_type": return_type,
        "support_basemodel": support_basemodel,
        "support_attribute": support_attribute,
        "accessers": accessers,
        "raise_error": raise_error,
    }

    def _construct(raw: Any, sim: Any) -> Any:
        if sim is None or isinstance(sim, (str, int, float, bool, bytes)):
            return sim
        if isinstance(sim, SpecIntermediate):
            if sim.identifier == SPEC_SOURCE:
                return access(raw, sim.value, **kwargs)
            return sim.value
        if isinstance(sim, (dict, Mapping)):
            res_d = {k: r for k, v in sim.items() if (r := _construct(raw, v)) != SPEC_SKIP}
            return res_d if type(sim) is dict else type(sim)(**res_d)
        if isinstance(sim, (list, tuple)):
            res_l = [r for v in sim if (r := _construct(raw, v)) != SPEC_SKIP]
            return res_l if type(sim) is list else type(sim)(res_l)
        logger.warning(f"Got unsupported type ({type(sim)}) in specification construction: {sim}")
        return sim

    return _construct(data, spec)


_ALIAS_SPEC = "_spec_"
_ALIAS_PIPE = "_pipe_"


def _casting(value: Any, *, pipe: list[Callable[[Any], Any]]) -> Any:
    for call in pipe:
        value = unroll_call(value, call=call)
    return value


class WithPipe(BaseModel):
    """Model wrapper that applies a pipe of casting functions after instantiation."""

    model_config = ConfigDict(frozen=True, validate_default=True, extra="forbid", serialize_by_alias=True)

    pipe: list[ObjectPattern] = Field(default_factory=list, alias=_ALIAS_PIPE)
    """List of casting patterns to apply after construction."""

    @field_validator("pipe", mode="before")
    @classmethod
    def _validate_pipe(cls, pipe: Any) -> list[ObjectPattern]:
        """Validate the pipe field."""
        return check_elements(TypeAdapter(Optional[Union[ObjectPattern, list[ObjectPattern]]]).validate_python(pipe))

    @model_validator(mode="after")
    def _validate_casting(self) -> Self:
        """Validate the constructor."""
        _ = self.casting  # Ensure casting are initialized and cached
        return self

    @field_serializer("pipe", mode="wrap")
    def _serialize_pipe(self, value: list[ObjectPattern], handler: SerializerFunctionWrapHandler) -> list[Any]:
        """Serialize the pipe field."""
        res = handler(value)
        return res[0] if len(res) == 1 else res

    @cached_property
    def casting(self) -> Callable[[Any], Any]:
        """Get the cached casting function that applies the pipe of casting patterns."""
        pipe: list[Callable[[Any], Any]] = []
        for ind, ptn in enumerate(self.pipe):
            inst = ptn.build().runs[0]
            if not callable(inst):
                raise SpecError(f"Invalid pipe at position {ind} is not callable: {inst}")
            pipe.append(inst)
        return partial(_casting, pipe=pipe)


class _Spec(WithPipe, ABC):
    @model_validator(mode="after")
    def _validate_constructor(self) -> Self:
        """Validate the constructor."""
        _ = self.spec  # Ensure spec are initialized and cached
        return self

    @cached_property
    def spec(self) -> Any:
        """Get the cached specification for construction."""
        return self._get_spec()

    @abstractmethod
    def _get_spec(self) -> Any:
        """Get the specification for construction."""

    @cached_property
    def placeholder_depth(self) -> int:
        """Get the cached maximum depth of placeholders in the specification."""
        return self._get_placeholder_depth()

    def _get_placeholder_depth(self) -> int:
        """Get the maximum depth of placeholders in the specification."""
        return 0

    @abstractmethod
    def _constructor(self, total_depth: int) -> Callable[[Any], Any]:
        """Get the constructor function based on the specification and total depth of placeholders."""

    def __call__(self, data: Any) -> Any:
        """Construct the value from data based on the specification.

        Args:
            data (Any): The data to construct from.

        Returns:
            Any: The constructed and casted value.
        """
        return self._constructor(self.placeholder_depth)(data)


@dataclass
class _Constructor:
    spec: Any
    convert_spec: Callable[[Any, Any], Any]
    self_depth: int
    total_depth: int
    casting: Callable[[Any], Any]

    def __call__(self, data: Any) -> Any:
        if self.self_depth >= 0:
            self.spec = self.convert_spec(data, self.spec)
            self.self_depth -= 1
        if self.total_depth == 0:
            return self.casting(self.spec)
        self.total_depth -= 1
        return self


class RawSpec(_Spec):
    """Raw specification for constructing values from data based on a raw specification input."""

    raw: Optional[Union[str, int, float, bool, bytes]] = Field("", alias=_ALIAS_SPEC)
    """The raw specification input."""

    return_type: Optional[ReturnType] = None
    """The type of access to use."""

    support_basemodel: Optional[bool] = None
    """Whether to support BaseModel."""

    support_attribute: Optional[bool] = None
    """Whether to support attribute access on objects."""

    raise_error: Optional[bool] = None
    """Whether to raise an error when picking fails."""

    @model_validator(mode="before")
    @classmethod
    def _validate_raw(cls, raw: Any) -> Any:
        """Validate the raw field."""
        if isinstance(raw, RawSpec):
            return raw
        return raw if isinstance(raw, (dict, Mapping)) and _ALIAS_SPEC in raw else {_ALIAS_SPEC: raw}

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler: SerializerFunctionWrapHandler) -> Any:
        """Serialize the model."""
        res = handler(self)
        if isinstance(res, dict) and _ALIAS_SPEC in res:
            return res if self.has_construct_kwargs else res[_ALIAS_SPEC]
        return res

    def _get_spec(self) -> Any:
        return SpecIntermediate.convert_spec(self.raw)

    def _get_placeholder_depth(self) -> int:
        """Implementation to get the maximum depth of placeholders in the specification."""
        count, spec = 0, self.spec
        while isinstance(spec, SpecIntermediate) and spec.identifier == SPEC_PLACEHOLDER:
            count += 1
            spec = spec.value
        return count

    @cached_property
    def has_construct_kwargs(self) -> bool:
        """Check if any construction keyword arguments are set, which affects serialization behavior."""
        return (
            self.return_type is not None
            or self.support_basemodel is not None
            or self.support_attribute is not None
            or self.raise_error is not None
            or bool(self.pipe)
        )

    @cached_property
    def construct_kwargs(self) -> dict[str, Any]:
        """Get the cached construction keyword arguments."""
        return {
            "return_type": self.return_type,
            "support_basemodel": self.support_basemodel,
            "support_attribute": self.support_attribute,
            "raise_error": self.raise_error,
        }

    def _constructor(self, total_depth: int) -> Callable[[Any], Any]:
        if total_depth == 0:
            return lambda x: self.casting(construct(x, self.spec, **self.construct_kwargs))
        return _Constructor(
            spec=self.spec,
            convert_spec=partial(construct, **self.construct_kwargs),
            self_depth=self.placeholder_depth,
            total_depth=total_depth,
            casting=self.casting,
        )


class ObjectSpec(_Spec):
    """Object specification for constructing values from data based on an object pattern."""

    pattern: ObjectPattern = Field(default_factory=ObjectPattern, alias=_ALIAS_SPEC)
    """The object pattern specification."""

    @model_validator(mode="before")
    @classmethod
    def _validate_pattern(cls, raw: Any) -> Any:
        """Validate the pattern field."""
        if isinstance(raw, ObjectSpec):
            return raw
        try:
            return {_ALIAS_SPEC: ObjectPattern.model_validate(raw)}
        except ValidationError:
            pass
        return raw if isinstance(raw, (dict, Mapping)) and _ALIAS_SPEC in raw else {_ALIAS_SPEC: raw}

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler: SerializerFunctionWrapHandler) -> Any:
        """Serialize the model."""
        res = handler(self)
        if isinstance(res, dict) and _ALIAS_SPEC in res:
            return res if self.pipe else res[_ALIAS_SPEC]
        return res

    def _get_spec(self) -> Any:
        return self.pattern.build().runs[0]

    def _constructor(self, total_depth: int) -> Callable[[Any], Any]:
        if total_depth == 0:
            return lambda _: self.casting(self.spec)
        return _Constructor(
            spec=self.spec,
            total_depth=total_depth,
            casting=self.casting,
            # ObjectSpec itself does not have placeholders, but its spec may contain placeholders,
            # so self_depth is set to -1 to indicate that it should not be decremented for the ObjectSpec level.
            convert_spec=lambda _, s: s,
            self_depth=-1,
        )


class FlexSpec(_Spec):
    """Flexible specification that can handle various specification structures for constructing values from data."""

    structure: Union[
        RawSpec,
        ObjectSpec,
        dict[str, Union[RawSpec, ObjectSpec, "FlexSpec"]],
        list[Union[RawSpec, ObjectSpec, "FlexSpec"]],
    ] = Field(default_factory=RawSpec, alias=_ALIAS_SPEC)
    """The specification structure."""

    @model_validator(mode="before")
    @classmethod
    def _validate_structure(cls, raw: Any) -> Any:
        """Validate the data."""
        if isinstance(raw, FlexSpec):
            return raw
        try:
            return {_ALIAS_SPEC: TypeAdapter(Union[RawSpec, ObjectSpec]).validate_python(raw)}
        except ValidationError:
            pass
        if isinstance(raw, (dict, Mapping)):
            if _ALIAS_SPEC in raw:
                return raw
            raw = {k: TypeAdapter(Union[RawSpec, ObjectSpec, FlexSpec]).validate_python(v) for k, v in raw.items()}
        elif isinstance(raw, (list, tuple)):
            raw = [TypeAdapter(Union[RawSpec, ObjectSpec, FlexSpec]).validate_python(v) for v in raw]
        return {_ALIAS_SPEC: raw}

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler: SerializerFunctionWrapHandler) -> Any:
        """Serialize the model."""
        res = handler(self)
        if isinstance(res, dict) and _ALIAS_SPEC in res:
            return res if self.pipe else res[_ALIAS_SPEC]
        return res

    def _get_spec(self) -> Any:
        def _get(structure: Any) -> Any:
            if isinstance(structure, dict):
                return {k: _get(v) for k, v in structure.items()}
            if isinstance(structure, list):
                return [_get(v) for v in structure]
            if isinstance(structure, (RawSpec, ObjectSpec, FlexSpec)):
                return structure.spec
            logger.debug(f"Got unsupported type ({type(structure)}) in specification structure: {structure}")
            return structure

        return _get(self.structure)

    def _get_placeholder_depth(self) -> int:
        """Implementation to get the maximum depth of placeholders in the specification."""

        def _depth(structure: Any) -> int:
            if isinstance(structure, dict):
                return max((_depth(v) for v in structure.values()), default=0)
            if isinstance(structure, list):
                return max((_depth(v) for v in structure), default=0)
            if isinstance(structure, (RawSpec, ObjectSpec, FlexSpec)):
                return structure.placeholder_depth
            return 0

        return _depth(self.structure)

    def _constructor(self, total_depth: int) -> Callable[[Any], Any]:
        if total_depth == 0:

            def _construct(data: Any) -> Any:
                if isinstance(self.structure, dict):
                    return {k: r for k, v in self.structure.items() if (r := v(data)) != SPEC_SKIP}
                if isinstance(self.structure, list):
                    return [r for v in self.structure if (r := v(data)) != SPEC_SKIP]
                return self.structure(data)

            return _construct
        if isinstance(self.structure, dict):
            return _Constructor(
                spec={k: v._constructor(total_depth) for k, v in self.structure.items()},
                convert_spec=lambda d, s: {k: r for k, v in s.items() if (r := v(d)) != SPEC_SKIP},
                self_depth=self.placeholder_depth,
                total_depth=total_depth,
                casting=self.casting,
            )
        if isinstance(self.structure, list):
            return _Constructor(
                spec=[v._constructor(total_depth) for v in self.structure],
                convert_spec=lambda d, s: [r for v in s if (r := v(d)) != SPEC_SKIP],
                self_depth=self.placeholder_depth,
                total_depth=total_depth,
                casting=self.casting,
            )
        return _Constructor(
            spec=self.structure._constructor(total_depth),
            convert_spec=lambda d, s: s(d),
            self_depth=self.placeholder_depth,
            total_depth=total_depth,
            casting=self.casting,
        )
