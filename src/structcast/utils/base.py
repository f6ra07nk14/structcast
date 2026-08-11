"""Base utilities for StructCast: security settings, attribute validation, imports, path resolution and YAML I/O."""

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import field
from datetime import date, datetime
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
from logging import getLogger
from pathlib import Path
from re import findall as re_findall, match as re_match
from types import ModuleType
from typing import IO, TYPE_CHECKING, Any, Callable, Optional, TypeVar, Union, cast, overload

from ruamel.yaml import YAML
from ruamel.yaml.constructor import SafeConstructor

from structcast.utils.dataclasses import dataclass
from structcast.utils.lazy_import import get_default_dir
from structcast.utils.types import PathLike

logger = getLogger(__name__)

T = TypeVar("T")


class SecurityError(Exception):
    """Exception raised when a security check fails."""


def resolve_path(path: Path) -> Optional[Path]:
    """Resolve a path safely, returning None if it cannot be resolved.

    Args:
        path (Path): The path to resolve.

    Returns:
        Optional[Path]: The resolved path, or None if it cannot be resolved.
    """
    try:
        resolved_path = path.resolve(strict=True)
        if resolved_path.exists():
            return resolved_path
    except (OSError, RuntimeError) as e:
        logger.warning(f"Failed to resolve path {path}: {e}")
    return None


DEFAULT_DANGEROUS_DUNDERS: set[str] = {
    *{"__subclasses__", "__bases__", "__globals__", "__code__", "__dict__"},
    *{"__class__", "__mro__", "__init__", "__import__"},
}
"""Default dangerous dunder attributes to block during instantiation."""


@dataclass
class SecuritySettings:
    """Settings for security-related restrictions."""

    dangerous_dunders: set[str] = field(default_factory=lambda: deepcopy(DEFAULT_DANGEROUS_DUNDERS))
    """Set of dangerous dunder method names to block."""

    ascii_check: bool = True
    """Whether to block non-ASCII attribute names."""

    protected_member_check: bool = True
    """Whether to block protected member access."""

    private_member_check: bool = True
    """Whether to block private member access."""


def _construct_from_address(constructor: Any, tag_suffix: str, node: Any) -> Any:
    """Construct an object for a "!<address>" tag by importing the address on demand.

    Args:
        constructor (Any): The YAML constructor calling this function.
        tag_suffix (str): The tag without its leading "!", used as the address of the class.
        node (Any): The YAML node to construct from.

    Returns:
        Any: The constructed object.
    """
    cls = import_from_address(tag_suffix)
    cls_from_yaml = getattr(cls, "from_yaml", None)
    if cls_from_yaml is None:
        return constructor.construct_yaml_object(node, cls)
    return cls_from_yaml(constructor, node)


class _AddressConstructor(SafeConstructor):
    """Safe constructor owning the "!<address>" registration.

    ``add_multi_constructor`` is a classmethod, so registering on ``SafeConstructor`` itself would make every
    ``YAML(typ="safe")`` instance in the process resolve ``!<address>`` tags through structcast. Owning a
    subclass keeps the registration inside structcast.
    """


def _new_yaml() -> YAML:
    """Create the safe YAML instance structcast loads and dumps with."""
    instance = YAML(typ="safe", pure=True)  # YAML 1.2 support
    instance.Constructor = _AddressConstructor
    return instance


@dataclass
class _YamlManager:
    """Manager for YAML constructor and representer reloading."""

    instance: YAML = field(default_factory=_new_yaml)
    """YAML loader instance."""

    def reset(self) -> None:
        """Reset the YAML instance to default safe settings."""
        self.instance = _new_yaml()

    def add_representer(self, tag: str, cls: type, to_yaml_fn: Optional[Callable[[Any, Any], Any]]) -> None:
        """Add a YAML representer for a class."""
        if to_yaml_fn is None:

            def to_yaml_fn(representer: Any, data: Any) -> Any:
                return representer.represent_yaml_object(tag, data, cls, flow_style=representer.default_flow_style)

        self.instance.representer.add_representer(cls, to_yaml_fn)

    def load_representer(self, instance: Optional[YAML], addresses: set[Union[str, type]]) -> "_YamlManager":
        """Reload the YAML representer if not already reloaded."""
        self_ = self if instance is None else _YamlManager(instance=instance)
        for addr in addresses:
            if isinstance(addr, str):
                tag: str = f"!{addr}"
                cls = import_from_address(addr)
                to_yaml_fn = getattr(cls, "to_yaml", None)
            else:
                cls = addr
                module_name, target = addr.__module__, addr.__name__
                tag = getattr(addr, "yaml_tag", f"!{module_name}.{target}")
                to_yaml_fn = getattr(addr, "to_yaml", None)
            self_.add_representer(tag, cls, to_yaml_fn)
        return self_

    def load_constructor(self, instance: Optional[YAML]) -> "_YamlManager":
        """Register the constructor resolving "!<address>" tags on demand."""
        self_ = self if instance is None else _YamlManager(instance=instance)
        self_.instance.constructor.add_multi_constructor("!", _construct_from_address)
        return self_


_allowed_directories: list[Path] = []
"""List of registered directories for module searching."""

_security_settings = SecuritySettings()
"""Security settings instance."""

_yaml_manager = _YamlManager()
"""YAML manager instance."""


def get_security_settings() -> SecuritySettings:
    """Get a copy of the current security settings."""
    return SecuritySettings(
        dangerous_dunders=deepcopy(_security_settings.dangerous_dunders),
        ascii_check=_security_settings.ascii_check,
        protected_member_check=_security_settings.protected_member_check,
        private_member_check=_security_settings.private_member_check,
    )


def configure_security(
    settings: Optional[SecuritySettings] = None,
    *,
    dangerous_dunders: Optional[set[str]] = None,
    ascii_check: Optional[bool] = None,
    protected_member_check: Optional[bool] = None,
    private_member_check: Optional[bool] = None,
) -> None:
    """Configure security settings for import_from_address.

    Args:
        settings (SecuritySettings | None): A SecuritySettings instance to use.
            If None, individual parameters are used.
        dangerous_dunders (set[str] | None): Set of dangerous dunder method names to block. If None, use default.
        ascii_check (bool | None): Whether to block non-ASCII attribute names. If None, use default.
        protected_member_check (bool | None): Whether to block protected member access. If None, use default.
        private_member_check (bool | None): Whether to block private member access. If None, use default.
    """
    if settings is None:
        kwargs: dict[str, Any] = {}
        if dangerous_dunders is not None:
            kwargs["dangerous_dunders"] = dangerous_dunders
        if ascii_check is not None:
            kwargs["ascii_check"] = ascii_check
        if protected_member_check is not None:
            kwargs["protected_member_check"] = protected_member_check
        if private_member_check is not None:
            kwargs["private_member_check"] = private_member_check
        settings = SecuritySettings(**kwargs)
    _security_settings.dangerous_dunders = settings.dangerous_dunders
    _security_settings.ascii_check = settings.ascii_check
    _security_settings.protected_member_check = settings.protected_member_check
    _security_settings.private_member_check = settings.private_member_check
    _yaml_manager.reset()


def register_dir(path: PathLike) -> None:
    """Register a directory to search for modules.

    Args:
        path (PathLike): The path to the directory to register.
    """
    if not isinstance(path, Path):
        path = Path(path)
    resolved_path = resolve_path(path)
    if resolved_path is None or not resolved_path.is_dir():
        raise ValueError(f"Path is not a valid directory: {path}")
    if resolved_path in _allowed_directories:
        logger.warning(f"Directory is already registered. Skip registering: {path}")
    else:
        _allowed_directories.append(resolved_path)


def unregister_dir(path: PathLike) -> None:
    """Unregister a previously registered directory.

    Args:
        path (PathLike): The path to the directory to unregister.
    """
    if not isinstance(path, Path):
        path = Path(path)
    resolved_path = resolve_path(path)
    if resolved_path is None or not resolved_path.is_dir():
        raise ValueError(f"Path is not a valid directory: {path}")
    try:
        _allowed_directories.remove(resolved_path)
    except ValueError:
        logger.warning(f"Directory was not registered. Skip unregistering: {path}")


def _validate_attribute(
    target: str,
    *,
    protected_member_check: Optional[bool] = None,
    private_member_check: Optional[bool] = None,
    ascii_check: Optional[bool] = None,
) -> None:
    ascii_check = _security_settings.ascii_check if ascii_check is None else ascii_check
    protected_member_check = (
        _security_settings.protected_member_check if protected_member_check is None else protected_member_check
    )
    private_member_check = (
        _security_settings.private_member_check if private_member_check is None else private_member_check
    )
    if not target.isidentifier() or target != target.strip():
        raise SecurityError(f"Invalid attribute access attempt: {repr(target)}")
    if ascii_check and not target.isascii():
        raise SecurityError(f"Non-ASCII attribute access attempt: {repr(target)}")
    if target in _security_settings.dangerous_dunders:
        raise SecurityError(f"Dangerous dunder access attempt: {repr(target)}")
    is_private = target.startswith("__")
    is_protected = target.startswith("_") and not is_private
    if private_member_check and is_private:
        raise SecurityError(f"Private member access attempt: {repr(target)}")
    elif protected_member_check and is_protected:
        raise SecurityError(f"Protected member access attempt: {repr(target)}")


__FIELD_PATTERN1 = r'(?:[^\f\n\r\t\v."\']+)'
__FIELD_PATTERN2 = r'(?:"(?:\\"|\\\\|[^\f\n\r\t\v"\\])+")'
__FIELD_PATTERN3 = r"(?:\'(?:\\\\|\\\'|[^\f\n\r\t\v\'\\])+\')"
__FIELD_PATTERN = rf"(?:{__FIELD_PATTERN1}|{__FIELD_PATTERN2}|{__FIELD_PATTERN3})"
__GROUP_FIELD = rf"({__FIELD_PATTERN1}|{__FIELD_PATTERN2}|{__FIELD_PATTERN3})"
__FORMAT_PATTERN = rf"^{__FIELD_PATTERN}(?:\.{__FIELD_PATTERN})*$"


def _to_index(value: str) -> Union[str, int]:
    """Convert a string value to an int or unescaped string."""
    try:
        return int(value)
    except ValueError:
        if value[0] == '"':
            return value.strip('"').replace('\\"', '"').replace("\\\\", "\\")
        if value[0] == "'":
            return value.strip("'").replace("\\'", "'").replace("\\\\", "\\")
    return value


def convert_part_to_string(part: Union[str, int]) -> str:
    """Convert a part to a string.

    If the part is an integer, it will be converted to a string.
    If the part is a string that is not a valid identifier, it will be quoted.

    Args:
        part (str | int): The part to convert.

    Returns:
        str: The converted part.
    """
    if isinstance(part, int):
        return str(part)
    if not part.isidentifier():
        return repr(part)
    return part


def convert_parts_to_string(parts: Sequence[Union[str, int]]) -> str:
    """Convert parts to a string.

    Args:
        parts (Sequence[str | int]): The parts to convert.

    Returns:
        str: The converted string.
    """
    return ".".join(convert_part_to_string(i) for i in parts)


def split_attribute(path: str) -> tuple[Union[str, int], ...]:
    """Split an attribute path into its components.

    Args:
        path (str): The attribute path to split.

    Returns:
        tuple[Union[str, int], ...]: A tuple of the components of the attribute path.
    """
    if re_match(__FORMAT_PATTERN, path):
        return tuple(_to_index(p) for p in re_findall(__GROUP_FIELD, path))
    raise ValueError(f"Invalid attribute path format: {path}")


def validate_attribute(
    target: str,
    *,
    protected_member_check: Optional[bool] = None,
    private_member_check: Optional[bool] = None,
    ascii_check: Optional[bool] = None,
) -> None:
    """Validate that a dotted attribute access is safe.

    Args:
        target (str): The dotted attribute name to access.
        protected_member_check (bool | None): Whether to block access to protected members (starting with '_').
            Default is taken from global settings.
        private_member_check (bool | None): Whether to block access to private members (starting with '__').
            Default is taken from global settings.
        ascii_check (bool | None): Whether to block access to non-ASCII attribute names.
            Default is taken from global settings.

    Raises:
        SecurityError: If the attribute access is blocked by security settings.
    """
    attrs = split_attribute(target)
    if any(isinstance(a, int) for a in attrs):
        raise SecurityError(f"Numeric index access is not allowed in attribute paths: {repr(target)}")
    attrs = cast(tuple[str], attrs)
    for ind, attr in enumerate(attrs):
        try:
            _validate_attribute(
                attr,
                protected_member_check=protected_member_check,
                private_member_check=private_member_check,
                ascii_check=ascii_check,
            )
        except SecurityError as e:
            raise SecurityError(f'Invalid attribute access attempt at "{".".join(attrs[: ind + 1])}": {e}') from e


def find_path(path: PathLike) -> Path:
    """Check if a path exists, searching in registered directories if necessary.

    Args:
        path (PathLike): The path to check.

    Returns:
        Path: The resolved path.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    if not isinstance(path, Path):
        path = Path(path)
    candidate: Optional[Path] = resolve_path(path)
    if not path.is_absolute():
        allowed_directories = _allowed_directories.copy()
        while candidate is None and allowed_directories:
            candidate = resolve_path(allowed_directories.pop(0) / path)
    if candidate is None:
        raise FileNotFoundError(f"Path does not exist: {path}")
    return candidate


def __load_module(module_name: str, module_file: Path) -> ModuleType:
    """Load a module from a file.

    Args:
        module_name (str): The name of the module.
        module_file (Path): The path to the module file.

    Returns:
        ModuleType: The loaded module.

    Raises:
        ImportError: If the module cannot be loaded.
        SecurityError: If the module file is not a .py file.
    """
    # Only allow .py files
    if module_file.suffix != ".py":
        raise SecurityError(f"Module file must be a .py file, got: {module_file.suffix}")
    module_spec = spec_from_file_location(module_name, module_file)
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {module_file}")
    module = module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def resolve_address(address: str) -> tuple[Optional[str], str]:
    """Resolve an address into module name and target.

    Args:
        address (str): The address to resolve, in the form of "module.target" or "target".

    Returns:
        tuple[Optional[str], str]: A tuple of (module_name, target). If the module name is not specified, returns None.
    """
    parts = split_attribute(address)
    if len(parts) > 1:
        module, target = parts[:-1], parts[-1]
        if isinstance(target, int):
            raise ValueError(f"Target part of address cannot be a numeric index: {repr(target)}")
        return convert_parts_to_string(module), target
    return None, address


def import_from_address(
    address: str,
    *,
    default_module: Optional[ModuleType] = None,
    module_file: Optional[PathLike] = None,
    protected_member_check: Optional[bool] = None,
    private_member_check: Optional[bool] = None,
    ascii_check: Optional[bool] = None,
) -> Any:
    """Import target from address.

    This function imports a class or function from a module specified by the `address` string.
    The `address` can be in the form of "module.class" or just "class". If the module is not specified,
    it defaults to the `default_module` provided. If `module_file` is provided,
    the module will be loaded from the specified file.

    Security: addresses come from configuration, which is trusted input, so the module path is only checked
    for a valid format and dangerous dunders. The target is an attribute access on the imported module and is
    validated accordingly. Use configure_security() to customize the security settings.

    Args:
        address (str): The address of the class or function to import, in the form of "module.class" or "class".
        default_module (ModuleType | None): The default module to use if the module is not specified in the address.
            Default is None, which means the built-in module will be used.
        module_file (PathLike | None): Optional path to a module file to load the module from.
        protected_member_check (bool | None): Whether to block access to protected targets (starting with '_').
            Default is taken from global settings.
        private_member_check (bool | None): Whether to block access to private targets (starting with '__').
            Default is taken from global settings.
        ascii_check (bool | None): Whether to block access to non-ASCII target names.
            Default is taken from global settings.

    Returns:
        Any: The imported target.

    Raises:
        SecurityError: If the import is blocked by security settings.
        ImportError: If the target cannot be imported.
    """
    module_name, target = resolve_address(address)
    if module_file is not None:
        module_file = find_path(module_file)
        module_name = module_name or module_file.stem
        module = __load_module(module_name, module_file)
    elif module_name is not None:
        module = import_module(module_name)
    elif default_module is None:
        module, module_name = import_module("builtins"), "builtins"
    else:
        module, module_name = default_module, default_module.__name__
    for part in module_name.split("."):
        if not part.isidentifier():
            raise SecurityError(f"Invalid module path: {repr(module_name)}")
        if part in _security_settings.dangerous_dunders:
            raise SecurityError(f"Dangerous dunder in module path: {repr(part)}")
    _validate_attribute(
        target,
        protected_member_check=protected_member_check,
        private_member_check=private_member_check,
        ascii_check=ascii_check,
    )
    if hasattr(module, target):
        return getattr(module, target)
    raise ImportError(f'Target "{target}" not found in module "{module_name}".')


def load_yaml(yaml_file: PathLike, *, instance: Optional[YAML] = None) -> Any:
    """Load a yaml file.

    Args:
        yaml_file (PathLike): Path to the yaml file.
        instance (YAML | None): Optional YAML instance to use for loading.
            If None, a default safe YAML instance is used.

    Returns:
        Any: The loaded data from the yaml file.
    """
    yaml_file = find_path(yaml_file)
    with open(yaml_file, encoding="utf-8") as fin:
        return load_yaml_from_stream(fin, instance=instance)


def load_yaml_from_stream(stream: Union[str, IO], *, instance: Optional[YAML] = None) -> Any:
    """Load a yaml string.

    Args:
        stream (str | IO): The yaml string or file-like object to load.
        instance (YAML | None): Optional YAML instance to use for loading.
            If None, a default safe YAML instance is used.

    Returns:
        Any: The loaded data from the yaml string.
    """
    return _yaml_manager.load_constructor(instance).instance.load(stream)


def dump_yaml(data: Any, stream: Union[PathLike, IO], *, instance: Optional[YAML] = None) -> None:
    """Dump data to a yaml file.

    Args:
        data (Any): The data to dump.
        stream (Path | IO): The file path or file-like object to dump the yaml to.
        instance (YAML | None): Optional YAML instance to use for dumping.
            If None, a default safe YAML instance is used.
    """

    def _find(obj: Any) -> set[Union[str, type]]:
        if obj is None or isinstance(obj, (str, int, float, bool, bytes, date, datetime)):
            return set()
        if isinstance(obj, (dict, Mapping)):
            return {a for v in obj.values() for a in _find(v)}
        if isinstance(obj, (list, tuple, set, Sequence)):
            return {a for v in obj for a in _find(v)}
        return {type(obj)}

    inst = _yaml_manager.load_representer(instance, _find(data))
    if isinstance(stream, (Path, str)):
        stream = find_path(stream)
        with open(stream, "w", encoding="utf-8") as fout:
            inst.instance.dump(data, fout)
    else:
        inst.instance.dump(data, stream)


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
        elements (Sequence[T] | set[T] | T | None): The elements to check.

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


def unroll_call(value: Any, *, call: Callable[..., Any]) -> Any:
    """Unroll the call if the value is a callable.

    If the value is a dict or a mapping, it will be unpacked as keyword arguments.
    If the value is a list or a tuple, it will be unpacked as positional arguments.
    Otherwise, it will be passed as a single argument.

    Args:
        value: The value to unroll.
        call: The callable to call with the unrolled value.

    Returns:
        The result of the call.
    """
    if isinstance(value, (dict, Mapping)):
        return call(**value)
    if isinstance(value, (list, tuple)):
        return call(*value)
    return call(value)


def load_yaml_from_string(yaml_string: str) -> Any:
    """Load a yaml string.

    Args:
        yaml_string (str): The yaml string to load.

    Returns:
        Any: The loaded yaml data.
    """
    try:
        return load_yaml_from_stream(yaml_string)
    except Exception as e:
        raise ValueError(f"RAW STRING:\n{yaml_string}\n\nFailed to load YAML from string: {e}") from e


def dump_yaml_to_string(data: Any) -> str:
    """Dump data to a yaml formatted string."""
    str_io = StringIO()
    dump_yaml(data, str_io)
    value = str_io.getvalue()
    str_io.close()
    return value


__all__ = [
    "DEFAULT_DANGEROUS_DUNDERS",
    "SecurityError",
    "SecuritySettings",
    "check_elements",
    "configure_security",
    "convert_part_to_string",
    "convert_parts_to_string",
    "dump_yaml",
    "dump_yaml_to_string",
    "find_path",
    "get_default_dir",
    "get_security_settings",
    "import_from_address",
    "load_yaml",
    "load_yaml_from_stream",
    "load_yaml_from_string",
    "register_dir",
    "resolve_address",
    "resolve_path",
    "split_attribute",
    "unregister_dir",
    "unroll_call",
    "validate_attribute",
]


if not TYPE_CHECKING:
    import sys

    from structcast.utils.lazy_import import LazySelectedImporter

    sys.modules[__name__] = LazySelectedImporter(__name__, globals())
