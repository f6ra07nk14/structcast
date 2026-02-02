"""Utility functions for StructCast."""

from types import ModuleType
from typing import Any, Optional

from structcast.utils.base import import_from_address as __import_from_address, load_yaml as __load_yaml
from structcast.utils.types import PathLike


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


def load_yaml(yaml_file: PathLike) -> dict[str, Any]:
    """Load a yaml file.

    Args:
        yaml_file (PathLike): Path to the yaml file.

    Returns:
        Loaded yaml file.
    """
    return __load_yaml(yaml_file)


__all__ = ["PathLike", "import_from_address", "load_yaml"]
