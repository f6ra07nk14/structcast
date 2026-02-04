"""Security-related utilities and settings for structcast."""

from copy import deepcopy
from dataclasses import field
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from logging import getLogger
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

from ruamel.yaml import YAML

from structcast.utils.constants import DEFAULT_ALLOWED_MODULES, DEFAULT_BLOCKED_MODULES, DEFAULT_DANGEROUS_DUNDERS
from structcast.utils.dataclasses import dataclass
from structcast.utils.types import PathLike

logger = getLogger(__name__)


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


@dataclass
class SecuritySettings:
    """Settings for security-related restrictions."""

    blocked_modules: set[str] = field(default_factory=lambda: deepcopy(DEFAULT_BLOCKED_MODULES))
    """Set of module names to block."""

    allowed_modules: dict[str, Optional[set[Optional[str]]]] = field(
        default_factory=lambda: deepcopy(DEFAULT_ALLOWED_MODULES)
    )
    """Allowlist of module names and their allowed members.

    If the value is None, switch off allowlist checking for that module.
    If the value is a set, only the specified members are allowed.
    If the set contains None, all members are allowed.
    """

    dangerous_dunders: set[str] = field(default_factory=lambda: deepcopy(DEFAULT_DANGEROUS_DUNDERS))
    """Set of dangerous dunder method names to block."""

    ascii_check: bool = True
    """Whether to block non-ASCII attribute names."""

    protected_member_check: bool = True
    """Whether to block protected member access."""

    private_member_check: bool = True
    """Whether to block private member access."""

    hidden_check: bool = True
    """Whether to block paths with hidden directories."""

    working_dir_check: bool = True
    """Whether to ensure relative paths resolve within allowed directories."""


__allowed_directories: list[Path] = []
__security_settings = SecuritySettings()
"""Global security settings instance."""


def configure_security(
    settings: Optional[SecuritySettings] = None,
    *,
    blocked_modules: Optional[set[str]] = None,
    allowed_modules: Optional[dict[str, Optional[set[Optional[str]]]]] = None,
    dangerous_dunders: Optional[set[str]] = None,
    ascii_check: Optional[bool] = None,
    protected_member_check: Optional[bool] = None,
    private_member_check: Optional[bool] = None,
    hidden_check: Optional[bool] = None,
    working_dir_check: Optional[bool] = None,
) -> None:
    """Configure security settings for import_from_address.

    Args:
        settings (Optional[SecuritySettings]): A SecuritySettings instance to use.
            If None, individual parameters are used.
        blocked_modules (Optional[set[str]]): Set of module names to block. If None, use default blocked modules.
        allowed_modules (Optional[dict[str, Optional[set[Optional[str]]]]]):
            Allowlist of module names and their allowed members. If None, use default allowed modules.
        dangerous_dunders (Optional[set[str]]): Set of dangerous dunder method names to block. If None, use default.
        ascii_check (Optional[bool]): Whether to block non-ASCII attribute names. If None, use default.
        protected_member_check (Optional[bool]): Whether to block protected member access. If None, use default.
        private_member_check (Optional[bool]): Whether to block private member access. If None, use default.
        hidden_check (Optional[bool]): Whether to block paths with hidden directories. If None, use default.
        working_dir_check (Optional[bool]): Whether to ensure relative paths resolve within allowed directories.
            If None, use default.
    """
    if settings is None:
        kwargs: dict[str, Any] = {}
        if blocked_modules is not None:
            kwargs["blocked_modules"] = blocked_modules
        if allowed_modules is not None:
            kwargs["allowed_modules"] = allowed_modules
        if dangerous_dunders is not None:
            kwargs["dangerous_dunders"] = dangerous_dunders
        if ascii_check is not None:
            kwargs["ascii_check"] = ascii_check
        if protected_member_check is not None:
            kwargs["protected_member_check"] = protected_member_check
        if private_member_check is not None:
            kwargs["private_member_check"] = private_member_check
        if hidden_check is not None:
            kwargs["hidden_check"] = hidden_check
        if working_dir_check is not None:
            kwargs["working_dir_check"] = working_dir_check
        settings = SecuritySettings(**kwargs)
    __security_settings.blocked_modules = settings.blocked_modules
    __security_settings.allowed_modules = settings.allowed_modules
    __security_settings.dangerous_dunders = settings.dangerous_dunders
    __security_settings.ascii_check = settings.ascii_check
    __security_settings.protected_member_check = settings.protected_member_check
    __security_settings.private_member_check = settings.private_member_check
    __security_settings.hidden_check = settings.hidden_check
    __security_settings.working_dir_check = settings.working_dir_check


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
    if resolved_path in __allowed_directories:
        logger.warning(f"Directory is already registered. Skip registering: {path}")
    else:
        __allowed_directories.append(resolved_path)


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
        __allowed_directories.remove(resolved_path)
    except ValueError:
        logger.warning(f"Directory was not registered. Skip unregistering: {path}")


def validate_import(module_name: str, target: str) -> None:
    """Validate that an import is safe.

    Args:
        module_name (str): The module name to import from.
        target (str): The target name to import.

    Raises:
        SecurityError: If the import is blocked by security settings.
    """
    allowed_members = __security_settings.allowed_modules.get(module_name, set())
    if allowed_members is not None:
        if None in allowed_members or target in allowed_members:
            return
        raise SecurityError(f"Blocked import attempt (not in allowlist): {module_name}.{target}")
    if any(n and (module_name == n or module_name.startswith(f"{n}.")) for n in __security_settings.blocked_modules):
        raise SecurityError(f"Blocked import attempt (blocklisted): {module_name}.{target}")


def _validate_attribute(
    target: str,
    *,
    protected_member_check: Optional[bool] = None,
    private_member_check: Optional[bool] = None,
    ascii_check: Optional[bool] = None,
) -> None:
    ascii_check = __security_settings.ascii_check if ascii_check is None else ascii_check
    protected_member_check = (
        __security_settings.protected_member_check if protected_member_check is None else protected_member_check
    )
    private_member_check = (
        __security_settings.private_member_check if private_member_check is None else private_member_check
    )
    if not target.isidentifier() or target != target.strip():
        raise SecurityError(f"Invalid attribute access attempt: {repr(target)}")
    if ascii_check and not target.isascii():
        raise SecurityError(f"Non-ASCII attribute access attempt: {repr(target)}")
    if target in __security_settings.dangerous_dunders:
        raise SecurityError(f"Dangerous dunder access attempt: {repr(target)}")
    is_private = target.startswith("__")
    is_protected = target.startswith("_") and not is_private
    if private_member_check and is_private:
        raise SecurityError(f"Private member access attempt: {repr(target)}")
    elif protected_member_check and is_protected:
        raise SecurityError(f"Protected member access attempt: {repr(target)}")


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
        protected_member_check (Optional[bool]): Whether to block access to protected members (starting with '_').
            Default is taken from global settings.
        private_member_check (Optional[bool]): Whether to block access to private members (starting with '__').
            Default is taken from global settings.
        ascii_check (Optional[bool]): Whether to block access to non-ASCII attribute names.
            Default is taken from global settings.

    Raises:
        SecurityError: If the attribute access is blocked by security settings.
    """
    attrs = target.split(".")
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


def check_path(
    path: PathLike,
    *,
    hidden_check: Optional[bool] = None,
    working_dir_check: Optional[bool] = None,
) -> Path:
    """Check if a path exists, searching in registered directories if necessary.

    Args:
        path (PathLike): The path to check.
        hidden_check (Optional[bool]): Whether to block paths with hidden directories (starting with '.').
            Default is taken from global settings.
        working_dir_check (Optional[bool]): Whether to ensure that relative paths resolve within allowed directories.
            Default is taken from global settings.

    Returns:
        Path: The resolved path.

    Raises:
        FileNotFoundError: If the path does not exist.
        SecurityError: If the path is blocked by security settings.
    """
    hidden_check = __security_settings.hidden_check if hidden_check is None else hidden_check
    working_dir_check = __security_settings.working_dir_check if working_dir_check is None else working_dir_check
    if not isinstance(path, Path):
        path = Path(path)
    candidate: Optional[Path] = resolve_path(path)
    if not path.is_absolute():
        allowed_directories = __allowed_directories.copy()
        while candidate is None and allowed_directories:
            candidate = resolve_path(allowed_directories.pop(0) / path)
    if candidate is None:
        raise FileNotFoundError(f"Path does not exist: {path}")
    if working_dir_check and not (
        (candidate.is_relative_to(Path.home()) and candidate.is_relative_to(Path.cwd()))
        or any(candidate.is_relative_to(d) for d in __allowed_directories)
    ):
        raise SecurityError(f"Path is outside of allowed directories: {path}")
    if hidden_check and any(p.startswith(".") for p in candidate.parts):
        raise SecurityError(f"Path contains hidden directories which are not allowed: {path}")
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


def import_from_address(
    address: str,
    *,
    default_module: Optional[ModuleType] = None,
    module_file: Optional[PathLike] = None,
    hidden_check: Optional[bool] = None,
    working_dir_check: Optional[bool] = None,
    protected_member_check: Optional[bool] = None,
    private_member_check: Optional[bool] = None,
    ascii_check: Optional[bool] = None,
) -> Any:
    """Import target from address.

    This function imports a class or function from a module specified by the `address` string.
    The `address` can be in the form of "module.class" or just "class". If the module is not specified,
    it defaults to the `default_module` provided. If `module_file` is provided,
    the module will be loaded from the specified file.

    Security: By default, this function blocks importing from dangerous modules (os, subprocess, etc.)
    and dangerous builtins (eval, exec, etc.) to prevent injection attacks. Use configure_security()
    to customize the security settings.

    Args:
        address (str): The address of the class or function to import, in the form of "module.class" or "class".
        default_module (Optional[ModuleType]): The default module to use if the module is not specified in the address.
            Default is None, which means the built-in module will be used.
        module_file (Optional[PathLike]): Optional path to a module file to load the module from.
        hidden_check (Optional[bool]): Whether to block paths with hidden directories (starting with '.').
            Default is taken from global settings.
        working_dir_check (Optional[bool]): Whether to ensure that relative paths resolve within allowed directories.
            Default is taken from global settings.
        protected_member_check (Optional[bool]): Whether to block access to protected members (starting with '_').
            Default is taken from global settings.
        private_member_check (Optional[bool]): Whether to block access to private members (starting with '__').
            Default is taken from global settings.
        ascii_check (Optional[bool]): Whether to block access to non-ASCII attribute names.
            Default is taken from global settings.

    Returns:
        Any: The imported target.

    Raises:
        SecurityError: If the import is blocked by security settings.
        ImportError: If the target cannot be imported.
    """
    if "." in address:
        index = address.rindex(".")
        module_name, target = address[:index], address[index + 1 :]
    else:
        module_name, target = None, address
    if module_file is not None:
        module_file = check_path(module_file, hidden_check=hidden_check, working_dir_check=working_dir_check)
        module_name = module_name or module_file.stem
        module = __load_module(module_name, module_file)
    elif module_name is not None:
        module = import_module(module_name)
    elif default_module is None:
        module, module_name = import_module("builtins"), "builtins"
    else:
        module, module_name = default_module, default_module.__name__
    validate_import(module_name, target)
    validate_attribute(
        f"{module_name}.{target}",
        protected_member_check=protected_member_check,
        private_member_check=private_member_check,
        ascii_check=ascii_check,
    )
    if hasattr(module, target):
        return getattr(module, target)
    raise ImportError(f'Target "{target}" not found in module "{module_name}".')


def load_yaml(
    yaml_file: PathLike,
    *,
    hidden_check: Optional[bool] = None,
    working_dir_check: Optional[bool] = None,
) -> Any:
    """Load a yaml file.

    Args:
        yaml_file (PathLike): Path to the yaml file.
        hidden_check (Optional[bool]): Whether to block paths with hidden directories (starting with '.').
            Default is taken from global settings.
        working_dir_check (Optional[bool]): Whether to ensure that relative paths resolve within allowed directories.
            Default is taken from global settings.

    Returns:
        Loaded yaml file.
    """
    yaml_file = check_path(yaml_file, hidden_check=hidden_check, working_dir_check=working_dir_check)
    with open(yaml_file, encoding="utf-8") as fin:
        return YAML(typ="safe", pure=True).load(fin)  # YAML 1.2 support
