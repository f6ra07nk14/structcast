"""Module for specification conversion and resolver registration."""

from collections.abc import Mapping
from dataclasses import field
from functools import cached_property
from logging import getLogger
from re import findall as re_findall, match as re_match
from typing import Any, Callable, Optional, Union, cast

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, TypeAdapter, field_validator, model_validator
from typing_extensions import Self

from structcast.core.constants import SPEC_CONSTANT, SPEC_FORMAT, SPEC_SOURCE
from structcast.core.instantiator import ObjectPattern
from structcast.utils.base import check_elements
from structcast.utils.dataclasses import dataclass
from structcast.utils.security import SecurityError, validate_attribute

logger = getLogger(__name__)


class SpecConversionError(Exception):
    """Exception raised for errors in the specification conversion process."""


class AccessError(Exception):
    """Exception raised for errors in the access process."""


@dataclass
class __SpecSettings:
    """Settings for specification conversion and accessors."""

    resolvers: dict[str, tuple[str, Callable[[str], Any]]] = field(default_factory=dict)
    castings: dict[str, Callable[[Any], Any]] = field(default_factory=dict)
    accessers: list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]] = field(default_factory=list)
    support_basemodel: bool = True
    support_attribute: bool = True
    raise_error: bool = False

    def register_resolver(self, name: str, resolver: Callable[[str], Any], casting: Callable[[Any], Any]) -> None:
        """Register a resolver for specification conversion.

        Args:
            name (str): The name of the resolver.
            resolver (Callable[[str], Any]): The resolver function that takes a string and returns a resolved value.
            casting (Callable[[Any], Any]): The casting function that takes a resolved value and returns a casted value.

        Raises:
            ValueError: If the resolver name is already registered.
        """
        if name in self.resolvers:
            raise ValueError(f"Resolver '{name}' is already registered.")
        spec_id = SPEC_FORMAT.format(resolver=name)
        self.resolvers[name] = spec_id, resolver
        self.castings[spec_id] = casting


SPEC_SETTINGS = __SpecSettings()
"""Global specification settings instance."""


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


def convert_spec(raw: Optional[Union[str, int, float, bool, bytes]]) -> tuple[Any, ...]:
    """Convert a raw specification into a structured format.

    Args:
        raw (Optional[Union[str, int, float, bool, bytes]]): The raw specification input.

    Returns:
        tuple[Any, ...]: A tuple containing the specification identifier and parameters.
    """
    if not isinstance(raw, str):
        return SPEC_CONSTANT, raw
    if not raw:
        return (SPEC_SOURCE,)
    for spec_name, (spec_id, resolver) in SPEC_SETTINGS.resolvers.items():
        prefix = f"{spec_name}:"
        if raw.lower().startswith(prefix):
            return spec_id, resolver(raw[len(prefix) :].strip())
    if re_match(__FORMAT_PATTERN, raw):
        res = [_to(p) for p in re_findall(__GROUP_FIELD, raw)]
        return SPEC_SOURCE, *res
    raise SpecConversionError(f"Invalid specification format: {raw}")


SPEC_SETTINGS.resolvers["constant"] = (SPEC_CONSTANT, lambda x: x)


def _convert_structured_spec(raw: Any) -> Any:
    if isinstance(raw, dict):
        return {k: _convert_structured_spec(v) for k, v in raw.items()}
    if isinstance(raw, Mapping):
        return type(raw)(**{k: _convert_structured_spec(v) for k, v in raw.items()})
    if isinstance(raw, (list, tuple)):
        return type(raw)(_convert_structured_spec(v) for v in raw)
    if isinstance(raw, (str, int, float, bool)) or raw is None:
        return convert_spec(raw)
    raise SpecConversionError(f"Unsupported specification type: {type(raw)}")


def convert_structured_spec(raw: Any) -> Any:
    """Convert a structured specification into a resolved format.

    Args:
        raw (Any): The structured specification input.

    Returns:
        Any: The resolved specification.

    Raises:
        SpecConversionError: If the specification format is invalid.
    """
    return _convert_structured_spec(raw)


def _str_index(index: Union[int, str]) -> str:
    if isinstance(index, int):
        return str(index)
    if not index.isidentifier():
        index = index.replace('"', '\\"')
        return f'"{index}"'
    return index


def _str_source(source: tuple[Union[int, str], ...]) -> str:
    return ".".join(_str_index(i) for i in source)


def _access_default(
    data: Any,
    source: tuple[Union[int, str], ...],
    accessers: list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]],
    raise_error: bool,
    __data__: Any,
    __source__: Optional[str],
) -> Any:
    if not source:
        return data
    index, source = source[0], source[1:]
    kwargs = {"accessers": accessers, "raise_error": raise_error, "__data__": __data__, "__source__": __source__}
    if isinstance(data, (dict, Mapping)):
        if index in data:
            return _access_default(data[index], source, **kwargs)
        else:
            msg = f"Key ({_str_index(index)}) not found in mapping at source ({__source__}): {__data__}"
    elif isinstance(data, (list, tuple)):
        if isinstance(index, int):
            if 0 <= index < len(data):
                return _access_default(data[index], source, **kwargs)
            else:
                msg = f"Index ({index}) out of range in sequence at source ({__source__}): {__data__}"
        else:
            msg = f"Non-integer index ({_str_index(index)}) used for sequence at source ({__source__}): {__data__}"
    else:
        for data_type, accesser in accessers:
            if isinstance(data, data_type):
                success, value = accesser(data, index)
                if success:
                    return _access_default(value, source, **kwargs)
                else:
                    logger.info(
                        f"Accesser for type ({data_type.__name__}) failed to access index ({_str_index(index)}) "
                        f"at source ({__source__})."
                    )
        msg = f"Cannot index into type ({type(data).__name__}) at source ({__source__}): {__data__}"
    if raise_error:
        raise AccessError(msg)
    logger.warning(msg)
    return None


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
    support_basemodel: Optional[bool] = None,
    support_attribute: Optional[bool] = None,
    accessers: Optional[list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]]] = None,
    raise_error: Optional[bool] = None,
) -> Any:
    """Access a value from data based on the provided source path.

    Args:
        data (Any): The data to access.
        source (tuple[Union[int, str], ...]): The path to access within the data.
        support_basemodel (Optional[bool], optional): Whether to support BaseModel access.
            Default is taken from global settings.
        support_attribute (Optional[bool], optional): Whether to support attribute access on objects.
            Default is taken from global settings.
        accessers (Optional[list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]]], optional):
            A custom list of type-accesser pairs to use for accessing data.
            Each accesser is a callable that takes an instance and an index,
            and returns a tuple of success (bool) and value (Any). Default is taken from global settings.
        raise_error (Optional[bool], optional): Whether to raise an error when access fails.
            Default is taken from global settings.

    Returns:
        Any: The accessed value.

    Raises:
        AccessError: If access fails and raise_error is True.
    """
    accessers = SPEC_SETTINGS.accessers if accessers is None else accessers
    support_attribute = SPEC_SETTINGS.support_attribute if support_attribute is None else support_attribute
    support_basemodel = SPEC_SETTINGS.support_basemodel if support_basemodel is None else support_basemodel
    if support_attribute:
        accessers = [(object, _access_attribute)] + accessers
    if support_basemodel:
        accessers = [(BaseModel, _access_basemodel)] + accessers
    raise_error = SPEC_SETTINGS.raise_error if raise_error is None else raise_error
    return _access_default(data, source, accessers, raise_error, data, _str_source(source))


def construct(
    data: Any,
    spec: Optional[Union[str, int, float, bool, bytes, dict, list, tuple]],
    *,
    support_basemodel: Optional[bool] = None,
    support_attribute: Optional[bool] = None,
    accessers: Optional[list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]]] = None,
    raise_error: Optional[bool] = None,
) -> Any:
    """Construct a value from data based on the structured specification.

    Args:
        data (Any): The data to construct from.
        spec (Optional[Union[str, int, float, bool, bytes, dict, list, tuple]]): The structured specification.
        support_basemodel (Optional[bool], optional): Whether to support BaseModel access.
            Default is taken from global settings.
        support_attribute (Optional[bool], optional): Whether to support attribute access on objects.
            Default is taken from global settings.
        accessers (Optional[list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]]], optional):
            A custom list of type-accesser pairs to use for accessing data.
            Each accesser is a callable that takes an instance and an index,
            and returns a tuple of success (bool) and value (Any). Default is taken from global settings.
        raise_error (Optional[bool], optional): Whether to raise an error when access fails.
            Default is taken from global settings.

    Returns:
        Any: The constructed value.

    Raises:
        AccessError: If access fails and raise_error is True.
    """
    if isinstance(spec, (str, int, float, bool, bytes)) or spec is None:
        return spec
    if not spec:
        return type(spec)()
    kwargs: dict[str, Any] = {
        "support_basemodel": support_basemodel,
        "support_attribute": support_attribute,
        "accessers": accessers,
        "raise_error": raise_error,
    }
    if isinstance(spec, dict):
        return {k: construct(data, v, **kwargs) for k, v in spec.items()}
    if isinstance(spec, Mapping):
        return type(spec)(**{k: construct(data, v, **kwargs) for k, v in spec.items()})
    if SPEC_SOURCE in spec:
        return access(data, cast(tuple[Union[int, str], ...], spec[1:]), **kwargs)
    if SPEC_CONSTANT in spec:
        return spec[1]
    if spec[0] in SPEC_SETTINGS.castings:
        return SPEC_SETTINGS.castings[spec[0]](spec[1])
    return type(spec)(construct(data, v, **kwargs) for v in spec)


_ALIAS_SPEC = "_spec_"


class Spec(BaseModel):
    """Field for string-like structures."""

    model_config = ConfigDict(frozen=True, validate_default=True, extra="forbid", serialize_by_alias=True)

    raw: Optional[Union[str, int, float, bool, bytes]] = Field("", alias=_ALIAS_SPEC)
    """The raw specification input."""

    support_basemodel: Optional[bool] = None
    """Whether to support BaseModel."""

    support_attribute: Optional[bool] = None
    """Whether to support attribute access on objects."""

    raise_error: Optional[bool] = None
    """Whether to raise an error when picking fails."""

    pipe: list[ObjectPattern] = Field(default_factory=list)
    """List of casting patterns to apply after construction."""

    _spec: tuple[Any, ...] = PrivateAttr()
    _pipe: list[Callable[[Any], Any]] = PrivateAttr(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def validate_raw(cls, raw: Any) -> Any:
        """Validate the raw field."""
        return raw if isinstance(raw, (dict, Mapping)) and _ALIAS_SPEC in raw else {_ALIAS_SPEC: raw}

    @field_validator("pipe", mode="before")
    @classmethod
    def validate_pipe(cls, pipe: Any) -> Any:
        """Validate the pipe field."""
        return check_elements(TypeAdapter(Optional[Union[ObjectPattern, list[ObjectPattern]]]).validate_python(pipe))

    @model_validator(mode="after")
    def validate_structure(self) -> Self:
        """Validate the structure."""
        self._spec = convert_spec(self.raw)
        for ind, ptn in enumerate(self.pipe):
            inst = ptn.build().runs[0]
            if not callable(inst):
                raise SpecConversionError(f"Cast at index {ind} is not callable: {inst}")
            self._pipe.append(inst)
        return self

    @property
    def spec(self) -> tuple[Any, ...]:
        """Get the field specification."""
        return self._spec

    @cached_property
    def casting(self) -> Callable[[Any], Any]:
        """Get the casting function."""

        def _cast(value: Any) -> Any:
            for func in self._pipe:
                value = func(value)
            return value

        return _cast

    def __call__(
        self,
        data: Any,
        *,
        support_basemodel: Optional[bool] = None,
        support_attribute: Optional[bool] = None,
        raise_error: Optional[bool] = None,
    ) -> Any:
        """Construct the value from data based on the specification.

        Args:
            data (Any): The data to construct from.
            support_basemodel (Optional[bool], optional): Whether to support BaseModel access.
                Default is taken from instance settings.
            support_attribute (Optional[bool], optional): Whether to support attribute access on objects.
                Default is taken from instance settings.
            raise_error (Optional[bool], optional): Whether to raise an error when picking fails.
                Default is taken from instance settings.
        """
        value = construct(
            data,
            self._spec,
            support_basemodel=self.support_basemodel if support_basemodel is None else support_basemodel,
            support_attribute=self.support_attribute if support_attribute is None else support_attribute,
            raise_error=self.raise_error if raise_error is None else raise_error,
        )
        return self.casting(value)
