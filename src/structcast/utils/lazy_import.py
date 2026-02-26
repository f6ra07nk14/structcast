"""Utilities to import modules and classes.

The implementation is based on the following:
    - [lazy-imports](https://github.com/telekom/lazy-imports/tree/main).
    - [optuna](https://github.com/optuna/optuna/tree/master)
"""

from importlib import import_module
from types import ModuleType, TracebackType
from typing import TYPE_CHECKING, Any, Optional

DEFAULT_ALLOWED_DUNDERS: set[str] = {
    "__annotations__",
    "__doc__",
    "__name__",
    "__file__",
    "__path__",
    "__version__",
    "__all__",
    "__spec__",
    "__loader__",
    "__package__",
}
"""Default dunder attributes to allow during instantiation."""


def get_default_dir(module_globals: dict[str, Any]) -> list[str]:
    """Get the default allowed members for a module based on its globals."""
    res = [n for n in DEFAULT_ALLOWED_DUNDERS if n in module_globals]
    if "__all__" in module_globals:
        res += [n for n in module_globals["__all__"] if n not in res]
    return res


class LazySelectedImporter(ModuleType):
    """Do lazy imports."""

    # Very heavily inspired by optuna.integration._IntegrationModule
    # https://github.com/optuna/optuna/blob/master/optuna/integration/__init__.py
    def __init__(
        self,
        module_name: str,
        module_globals: dict[str, Any],
        imported_structure: Optional[dict[str, list[str]]] = None,
    ) -> None:
        """Initialize a lazy selected importer.

        Args:
            module_name (str): Name of the module.
            module_globals (dict[str, Any]): The global variables of the module.
            imported_structure (dict[str, list[str]] | None): The structure of the imports.
        """
        super().__init__(module_name)
        self._extra = {k: module_globals.get(k) for k in get_default_dir(module_globals)}
        if imported_structure is None:
            imported_structure = {}
        self._class_to_module = {v: k for k, values in imported_structure.items() for v in values}
        self._imported_structure = imported_structure

    def _get_module(self, module_name: str) -> ModuleType:
        """Get a module.

        Args:
            module_name: Name of the module.

        Returns:
            The module.
        """
        return import_module(f".{module_name}", self.__name__)

    def __dir__(self) -> tuple[str, ...]:
        """Return the directory.

        Returns:
            The directory.
        """
        return tuple(self._extra)

    def __getattribute__(self, item: str) -> Any:
        """Get an attribute."""
        if item in (
            "_class_to_module",
            "_imported_structure",
            "_extra",
            "_get_module",
            "__spec__",
            "__firstlineno__",
            "__reduce__",
            "__dir__",
            "__getattribute__",
            # "__dict__",
        ):
            return super().__getattribute__(item)
        if item in (_extra := super().__getattribute__("_extra")):
            return super().__getattribute__(item)
        if item == "__dict__":
            return _extra
        raise AttributeError(f'Module "{super().__getattribute__("__name__")}" has no attribute "{item}".')

    def __getattr__(self, item: str) -> Any:
        """Get an attribute."""
        if item not in self._extra:
            raise AttributeError(f'Module "{self.__name__}" has no attribute "{item}".')
        if item in self._class_to_module:
            value = getattr(self._get_module(self._class_to_module[item]), item)
        elif item in self._imported_structure:
            value = self._get_module(item)
        else:
            return self._extra[item]
        setattr(self, item, value)
        return value

    def __reduce__(self) -> tuple[type["LazySelectedImporter"], tuple[str, Optional[str], dict[str, list[str]]]]:
        """Return the reduced form for pickling."""
        return self.__class__, (self.__name__, self.__file__, self._imported_structure)


class LazyModuleImporter(ModuleType):
    """Module wrapper for lazy import.

    This class wraps the specified modules and lazily imports them only when accessed.
    Otherwise, `import optuna` is slowed down by importing all submodules and
    dependencies even if not required.
    Within this project's usage, importlib override this module's attribute on the first
    access and the imported submodule is directly accessed from the second access.
    """

    def __init__(self, module_name: str) -> None:
        """Initialize a lazy module importer."""
        super().__init__(module_name)
        self._module: Optional[ModuleType] = None

    def _load(self) -> ModuleType:
        """Load the module.

        Returns:
            The module.
        """
        if self._module is None:
            self._module = import_module(self.__name__)
            self.__dict__.update(self._module.__dict__)
        return self._module

    def __getattr__(self, item: str) -> Any:
        """Get an attribute.

        Args:
            item: Name of the attribute.

        Returns:
            The attribute.
        """
        return getattr(self._load(), item)


class _DeferredImportExceptionContextManager:
    """Context manager to defer exceptions from imports.

    Catches :exc:`ImportError` and :exc:`SyntaxError`.
    If any exception is caught, this class raises an :exc:`ImportError` when being checked.

    """

    def __init__(self) -> None:
        """Initialize a deferred import exception context manager."""
        self._deferred: Optional[tuple[Exception, str]] = None

    def __enter__(self) -> "_DeferredImportExceptionContextManager":
        """Enter the context manager.

        Returns:
            Itself.
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[type[Exception]],
        exc_value: Optional[Exception],
        traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        """Exit the context manager."""
        if isinstance(exc_value, ImportError):
            message = (
                f"Tried to import '{exc_value.name}' but failed. Please make sure that the package is "
                f"installed correctly to use this feature. Actual error: {exc_value}."
            )
        elif isinstance(exc_value, SyntaxError):
            message = (
                f"Tried to import a package but failed due to a syntax error in {exc_value.filename}. "
                f"Please make sure that the Python version is correct to use this feature. "
                f"Actual error: {exc_value}."
            )
        else:
            return None
        self._deferred = (exc_value, message)
        return True

    @property
    def is_successful(self) -> bool:
        """Return whether the context manager has caught any exceptions.

        Returns:
            :obj:`True` if no exceptions are caught, :obj:`False` otherwise.

        """
        return self._deferred is None

    def check(self) -> None:
        """Check whether the context manger has caught any exceptions.

        Raises:
            ImportError: If any exceptions are caught.
        """
        if self._deferred is not None:
            exc_value, message = self._deferred
            raise ImportError(message) from exc_value


def try_import() -> _DeferredImportExceptionContextManager:
    """Create a context manager that can wrap imports of optional packages to defer exceptions.

    Returns:
        Deferred import context manager.
    """
    return _DeferredImportExceptionContextManager()


__all__ = ["DEFAULT_ALLOWED_DUNDERS", "LazyModuleImporter", "LazySelectedImporter", "get_default_dir", "try_import"]


if not TYPE_CHECKING:
    import sys

    sys.modules[__name__] = LazySelectedImporter(__name__, globals())
