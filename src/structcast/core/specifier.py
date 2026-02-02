"""Module for specification conversion and resolver registration."""

from re import findall as re_findall, match as re_match
from typing import Any, Callable, Union

from structcast.core.constants import SPEC_CONSTANT, SPEC_FORMAT, SPEC_SOURCE


class SpecConversionError(Exception):
    """Exception raised for errors in the specification conversion process."""


__resolvers: dict[str, tuple[str, Callable[[str], Any]]] = {}


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
