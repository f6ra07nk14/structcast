"""Module for specification conversion and resolver registration."""

from collections.abc import Mapping
from logging import getLogger
from re import findall as re_findall, match as re_match
from typing import Any, Callable, Optional, Union

from pydantic import BaseModel

from structcast.core.constants import SPEC_CONSTANT, SPEC_FORMAT, SPEC_SOURCE
from structcast.utils.security import SecurityError, validate_attribute

logger = getLogger(__name__)


class SpecConversionError(Exception):
    """Exception raised for errors in the specification conversion process."""


class ConstructionError(Exception):
    """Exception raised for errors during construction."""


__resolvers: dict[str, tuple[str, Callable[[str], Any]]] = {}
__accessers: list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]] = []


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


def register_accesser(data_type: type, accesser: Callable[[Any, Union[str, int]], tuple[bool, Any]]) -> None:
    """Register an accesser for a specific data type.

    Args:
        data_type (type): The data type for which the accesser is registered.
        accesser (Callable[[Any, Union[str, int]], tuple[bool, Any]]):
            The accesser function that takes an instance of the data type and an index,
            returning a tuple of success flag and the accessed value.
    """
    __accessers.append((data_type, accesser))


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


def convert_spec(raw: Union[str, int, float, bool, None]) -> tuple[Any, ...]:
    """Convert a raw specification into a structured format.

    Args:
        raw (Union[str, int, float, bool, None]): The raw specification input.

    Returns:
        tuple[Any, ...]: A tuple containing the specification identifier and parameters.
    """
    if not isinstance(raw, str):
        return SPEC_CONSTANT, raw
    for spec_name, (spec_id, resolver) in __resolvers.items():
        prefix = f"{spec_name}:"
        if raw.lower().startswith(prefix):
            return spec_id, resolver(raw[len(prefix) :].strip())
    if re_match(__FORMAT_PATTERN, raw):
        res = [_to(p) for p in re_findall(__GROUP_FIELD, raw)]
        return SPEC_SOURCE, *res
    raise SpecConversionError(f"Invalid specification format: {raw}")


__resolvers["constant"] = (SPEC_CONSTANT, lambda x: x)
__resolvers["source"] = (SPEC_SOURCE, convert_spec)


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


def _construct(
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
            return _construct(data[index], source, **kwargs)
        else:
            msg = f"Key ({_str_index(index)}) not found in mapping at source ({__source__}): {__data__}"
    elif isinstance(data, (list, tuple)):
        if isinstance(index, int):
            if 0 <= index < len(data):
                return _construct(data[index], source, **kwargs)
            else:
                msg = f"Index ({index}) out of range in sequence at source ({__source__}): {__data__}"
        else:
            msg = f"Non-integer index ({_str_index(index)}) used for sequence at source ({__source__}): {__data__}"
    else:
        for data_type, accesser in accessers:
            if isinstance(data, data_type):
                success, value = accesser(data, index)
                if success:
                    return _construct(value, source, **kwargs)
                else:
                    logger.info(
                        f"Accesser for type ({data_type.__name__}) failed to access index ({_str_index(index)}) "
                        f"at source ({__source__})."
                    )
        msg = f"Cannot index into type ({type(data).__name__}) at source ({__source__}): {__data__}"
    if raise_error:
        raise ConstructionError(msg)
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


def construct(
    data: Any,
    source: tuple[Union[int, str], ...],
    *,
    support_basemodel: bool = False,
    support_attribute: bool = False,
    accessers: Optional[list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]]] = None,
    raise_error: bool = False,
) -> Any:
    """Construct a value from data based on the provided source path.

    Args:
        data (Any): The data to construct the value from.
        source (tuple[Union[int, str], ...]): The path to the desired value in the data.
        support_basemodel (bool, optional): Whether to support Pydantic BaseModel access. Defaults to False.
        support_attribute (bool, optional): Whether to support attribute access on objects. Defaults to False.
        accessers (Optional[list[tuple[type, Callable[[Any, Union[str, int]], tuple[bool, Any]]]]], optional):
            A list of accessers for custom data types. Each accesser is a tuple of data type and accesser function,
            which takes an instance of the data type and an index,
            returning a tuple of success flag and the accessed value.
        raise_error (bool, optional): Whether to raise an error if construction fails. Defaults to False.

    Returns:
        Any: The constructed value or None if not found and raise_error is False.

    Raises:
        ConstructionError: If the construction fails and raise_error is True.
    """
    accessers = __accessers if accessers is None else accessers
    if support_attribute:
        accessers = [(object, _access_attribute)] + accessers
    if support_basemodel:
        accessers = [(BaseModel, _access_basemodel)] + accessers
    return _construct(data, source, accessers, raise_error, data, _str_source(source))
