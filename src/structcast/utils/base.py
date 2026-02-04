"""Base utility functions for StructCast."""

from collections.abc import Sequence
from types import ModuleType
from typing import Any, Optional, TypeVar, Union, cast, overload

from structcast.utils.security import import_from_address as __import_from_address, load_yaml as __load_yaml
from structcast.utils.types import PathLike

T = TypeVar("T")


@overload
def check_elements(elements: Optional[Union[Sequence[str], str]]) -> list[str]: ...


@overload
def check_elements(elements: Optional[set[T]]) -> list[T]: ...


@overload
def check_elements(elements: Optional[list[T]]) -> list[T]: ...


@overload
def check_elements(elements: Optional[tuple[T, ...]]) -> list[T]: ...


@overload
def check_elements(elements: Optional[Union[Sequence[T], T]]) -> list[T]: ...


def check_elements(elements: Optional[Union[Sequence[T], set[T], T]]) -> list[T]:
    """Check the elements.

    Ensure that the elements are in the list format.

    Examples:

    .. code-block:: python

    >>> check_elements(None)
    []
    >>> check_elements("abc")
    ['abc']
    >>> check_elements(("abc", "def"))
    ['abc', 'def']
    >>> check_elements(["abc", "def"])
    ['abc', 'def']

    Args:
        elements (Optional[Union[Elements[T], T]]): The elements to check.

    Returns:
        The checked elements.
    """
    if elements is None:
        return []
    if isinstance(elements, (tuple, set)):
        return list(elements)
    if isinstance(elements, list):
        return elements
    return [cast(T, elements)]


def import_from_address(
    address: str,
    *,
    default_module: Optional[ModuleType] = None,
    module_file: Optional[PathLike] = None,
) -> Any:
    """Import target from address.

    Args:
        address (str): The address of the class or function to import, in the form of "module.class" or "class".
        default_module (Optional[ModuleType]): The default module to use if the module is not specified in the address.
            Default is None, which means the built-in module will be used.
        module_file (Optional[PathLike]): Optional path to a module file to load the module from.

    Returns:
        Any: The imported target.

    Raises:
        SecurityError: If the import is blocked by security settings.
        ImportError: If the target cannot be imported.
    """
    return __import_from_address(address, default_module=default_module, module_file=module_file)


def load_yaml(yaml_file: PathLike) -> Any:
    """Load a yaml file.

    Args:
        yaml_file (PathLike): Path to the yaml file.

    Returns:
        Loaded yaml file.
    """
    return __load_yaml(yaml_file)
