"""Module for specification conversion and resolver registration."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from copy import copy, deepcopy
from enum import Enum
from functools import cached_property
from logging import getLogger
from typing import Any, Callable, Optional, Union

from pydantic import (
    BaseModel,
    Field,
    SerializerFunctionWrapHandler,
    TypeAdapter,
    ValidationError,
    model_serializer,
    model_validator,
)
from typing_extensions import Self

from structcast.core.constants import SPEC_FORMAT, SPEC_SOURCE
from structcast.core.instantiator import ObjectPattern, WithPipe
from structcast.utils.dataclasses import dataclass
from structcast.utils.security import SecurityError, split_attribute, validate_attribute

logger = getLogger(__name__)


class SpecError(Exception):
    """Exception raised for specification errors."""


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


__spec_settings = SpecSettings()
"""Global specification settings instance."""

__resolvers: dict[str, tuple[str, Callable[[str], Any]]] = {}
"""Registered resolvers for specification conversion."""

__accessers: list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]] = []
"""Registered accessers for data access."""


def register_resolver(name: str, resolver: Callable[[str], Any]) -> None:
    """Register a resolver for specification conversion.

    Args:
        name (str): The name of the resolver.
        resolver (Callable[[str], Any]): The resolver function that takes a string and returns a resolved value.

    Raises:
        ValueError: If the resolver name is already registered.
    """
    if name in __resolvers:
        raise ValueError(f"Resolver '{name}' is already registered.")
    __resolvers[name] = SPEC_FORMAT.format(resolver=name), resolver


register_resolver("constant", lambda x: x)

SPEC_CONSTANT = __resolvers["constant"][0]


def register_accesser(data_type: type, accesser: Callable[[Any, Union[str, int]], tuple[bool, Any]]) -> None:
    """Register an accesser for data access.

    Args:
        data_type (type): The type of data the accesser can handle.
        accesser (Callable[[Any, Union[str, int]], tuple[bool, Any]]): The accesser function that takes an instance
            and an index, and returns a tuple of success (bool) and value (Any).
    """
    __accessers.append((data_type, accesser))


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
    __spec_settings.support_basemodel = settings.support_basemodel
    __spec_settings.support_attribute = settings.support_attribute
    __spec_settings.raise_error = settings.raise_error
    __spec_settings.return_type = settings.return_type


__FIELD_PATTERN1 = r'(?:[^\f\n\r\t\v."\']+)'
__FIELD_PATTERN2 = r'(?:"(?:\\"|\\\\|[^\f\n\r\t\v"\\])+")'
__FIELD_PATTERN3 = r"(?:\'(?:\\\\|\\\'|[^\f\n\r\t\v\'\\])+\')"
__FIELD_PATTERN = rf"(?:{__FIELD_PATTERN1}|{__FIELD_PATTERN2}|{__FIELD_PATTERN3})"
__GROUP_FIELD = rf"({__FIELD_PATTERN1}|{__FIELD_PATTERN2}|{__FIELD_PATTERN3})"
__FORMAT_PATTERN = rf"^{__FIELD_PATTERN}(?:\.{__FIELD_PATTERN})*$"


def _to(value: str) -> Union[str, int]:
    """Convert a string value to an int or unescaped string."""
    try:
        return int(value)
    except ValueError:
        if value[0] == '"':
            return value.strip('"').replace('\\"', '"').replace("\\\\", "\\")
        if value[0] == "'":
            return value.strip("'").replace("\\'", "'").replace("\\\\", "\\")
    return value


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
        for spec_name, (spec_id, resolver) in __resolvers.items():
            prefix = f"{spec_name}:"
            if raw.lower().startswith(prefix):
                return cls(identifier=spec_id, value=resolver(raw[len(prefix) :].strip()))
        try:
            return cls(identifier=SPEC_SOURCE, value=split_attribute(raw))
        except ValueError as e:
            raise SpecError(f"Invalid specification format: {raw}") from e


def convert_spec(raw: Any) -> Any:
    """Convert a structured specification input into a resolved format.

    Args:
        raw (Any): The structured specification input.

    Returns:
        Any: The resolved specification.

    Raises:
        SpecError: If the specification type is unsupported.
    """
    if isinstance(raw, (str, int, float, bool, bytes)) or raw is None:
        return SpecIntermediate.convert_spec(raw)
    if isinstance(raw, dict):
        return {k: convert_spec(v) for k, v in raw.items()}
    if isinstance(raw, Mapping):
        return type(raw)(**{k: convert_spec(v) for k, v in raw.items()})
    if isinstance(raw, (list, tuple)):
        return type(raw)(convert_spec(v) for v in raw)
    raise SpecError(f"Unsupported specification type: {type(raw)}")


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
    return_type = __spec_settings.return_type if return_type is None else return_type
    accessers = __accessers if accessers is None else accessers
    support_attribute = __spec_settings.support_attribute if support_attribute is None else support_attribute
    support_basemodel = __spec_settings.support_basemodel if support_basemodel is None else support_basemodel
    if support_attribute:
        accessers = [(object, _access_attribute)] + accessers
    if support_basemodel:
        accessers = [(BaseModel, _access_basemodel)] + accessers
    raise_error = __spec_settings.raise_error if raise_error is None else raise_error
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
        if isinstance(sim, dict):
            return {k: _construct(raw, v) for k, v in sim.items()}
        if isinstance(sim, Mapping):
            return type(sim)(**{k: _construct(raw, v) for k, v in sim.items()})
        if isinstance(sim, (list, tuple)):
            return type(sim)(_construct(raw, v) for v in sim)
        logger.debug(f"Got unsupported type ({type(sim)}) in specification construction: {sim}")
        return sim

    return _construct(data, spec)


_ALIAS_SPEC = "_spec_"


class _Constructor(WithPipe, ABC):
    @model_validator(mode="after")
    def _validate_constructor(self) -> Self:
        """Validate the constructor."""
        _ = self.spec  # Ensure spec are initialized and cached
        return self

    @abstractmethod
    def _get_spec(self) -> Any:
        """Get the specification for construction."""

    @cached_property
    def spec(self) -> Any:
        return self._get_spec()

    @abstractmethod
    def _construct(self, data: Any) -> Any:
        """Construct the value from data based on the specification.

        Args:
            data (Any): The data to construct from.

        Returns:
            Any: The constructed value before casting.
        """

    def __call__(self, data: Any) -> Any:
        """Construct the value from data based on the specification.

        Args:
            data (Any): The data to construct from.

        Returns:
            Any: The constructed and casted value.
        """
        return self.casting(self._construct(data))


class RawSpec(_Constructor):
    """Raw specification model for constructing values from data."""

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
        if isinstance(raw, BaseModel):
            raw = raw.model_dump()
        return raw if isinstance(raw, (dict, Mapping)) and _ALIAS_SPEC in raw else {_ALIAS_SPEC: raw}

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler: SerializerFunctionWrapHandler) -> Any:
        """Serialize the model."""
        return handler(self) if self.has_construct_kwargs else self.raw

    def _get_spec(self) -> Any:
        return SpecIntermediate.convert_spec(self.raw)

    @cached_property
    def has_construct_kwargs(self) -> bool:
        """Check if any construction keyword arguments are set."""
        return (
            self.return_type is not None
            or self.support_basemodel is not None
            or self.support_attribute is not None
            or self.raise_error is not None
            or bool(self.pipe)
        )

    @cached_property
    def construct_kwargs(self) -> dict[str, Any]:
        """Get the construction keyword arguments."""
        return {
            "return_type": self.return_type,
            "support_basemodel": self.support_basemodel,
            "support_attribute": self.support_attribute,
            "raise_error": self.raise_error,
        }

    def _construct(self, data: Any) -> Any:
        """Construct the value from data based on the specification."""
        return construct(data, self.spec, **self.construct_kwargs)


class ObjectSpec(_Constructor):
    """Object specification model for constructing values from data."""

    pattern: ObjectPattern = Field(default_factory=ObjectPattern, alias=_ALIAS_SPEC)
    """The object pattern specification."""

    @model_validator(mode="before")
    @classmethod
    def _validate_pattern(cls, raw: Any) -> Any:
        """Validate the pattern field."""
        if isinstance(raw, ObjectSpec):
            return raw
        if isinstance(raw, ObjectPattern):
            return {_ALIAS_SPEC: raw}
        if isinstance(raw, BaseModel):
            raw = raw.model_dump()
        try:
            return {_ALIAS_SPEC: ObjectPattern.model_validate(raw)}
        except ValidationError:
            pass
        return raw if isinstance(raw, (dict, Mapping)) and _ALIAS_SPEC in raw else {_ALIAS_SPEC: raw}

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler: SerializerFunctionWrapHandler) -> Any:
        """Serialize the model."""
        return handler(self) if self.pipe else handler(self.pattern)

    def _get_spec(self) -> Any:
        return self.pattern.build().runs[0]

    def _construct(self, data: Any) -> Any:
        """Construct the value from data based on the specification."""
        return self.spec


class FlexSpec(_Constructor):
    """Flexible specification model for constructing values from data."""

    structure: Union[ObjectSpec, dict[str, "FlexSpec"], list["FlexSpec"], RawSpec] = Field(
        default_factory=RawSpec, alias=_ALIAS_SPEC
    )
    """The specification structure."""

    @model_validator(mode="before")
    @classmethod
    def _validate_structure(cls, raw: Any) -> Any:
        """Validate the data."""
        if isinstance(raw, FlexSpec):
            return raw
        if isinstance(raw, (ObjectSpec, RawSpec)):
            return {_ALIAS_SPEC: raw}
        if isinstance(raw, BaseModel):
            raw = raw.model_dump()
        try:
            return {_ALIAS_SPEC: TypeAdapter(Union[ObjectSpec, RawSpec]).validate_python(raw)}
        except ValidationError:
            pass
        if isinstance(raw, (dict, Mapping)):
            if _ALIAS_SPEC in raw:
                return raw
            return {_ALIAS_SPEC: {k: cls.model_validate(v) for k, v in raw.items()}}
        if isinstance(raw, (list, tuple)):
            return {_ALIAS_SPEC: [cls.model_validate(v) for v in raw]}
        return {_ALIAS_SPEC: raw}

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler: SerializerFunctionWrapHandler) -> Any:
        """Serialize the model."""
        return handler(self) if self.pipe else handler(self.structure)

    def _get_spec(self) -> Any:
        def _get(structure: Any) -> Any:
            if isinstance(structure, dict):
                return {k: _get(v) for k, v in structure.items()}
            if isinstance(structure, list):
                return [_get(v) for v in structure]
            if isinstance(structure, (RawSpec, ObjectSpec)):
                return structure.spec
            logger.debug(f"Got unsupported type ({type(structure)}) in specification structure: {structure}")
            return structure

        return _get(self.structure)

    def _construct(self, data: Any) -> Any:
        if isinstance(self.structure, dict):
            return {k: v(data) for k, v in self.structure.items()}
        if isinstance(self.structure, list):
            return [v(data) for v in self.structure]
        return self.structure(data)
