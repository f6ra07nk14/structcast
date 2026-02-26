"""Tests for lazy import utilities."""

import importlib
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from structcast.utils.lazy_import import (
    LazyModuleImporter,
    LazySelectedImporter,
    get_default_dir,
    try_import,
)


class TestGetDefaultDir:
    """Tests for get_default_dir."""

    def test_returns_allowed_dunders_and_all_members(self) -> None:
        """It collects existing dunders and exports from __all__."""
        result = get_default_dir({"__name__": "sample", "__doc__": "module doc", "__all__": ["A", "B", "A"]})
        assert "__name__" in result
        assert "__doc__" in result
        assert "A" in result
        assert "B" in result
        assert result.count("A") == 2

    def test_ignores_missing_dunders(self) -> None:
        """It does not add dunders that are not present in globals."""
        assert get_default_dir({"__all__": []}) == ["__all__"]


class TestLazyModuleImporter:
    """Tests for LazyModuleImporter."""

    def test_loads_module_on_first_attribute_access(self) -> None:
        """It imports wrapped module only when attribute is requested."""
        importer = LazyModuleImporter("math")
        assert importer._module is None
        assert importer.sqrt(16) == 4
        assert importer._module is not None
        assert importer.__dict__["__name__"] == "math"


class TestLazySelectedImporter:
    """Tests for LazySelectedImporter."""

    def test_accesses_extra_attributes_and_dict(self) -> None:
        """It returns values from extra globals and custom __dict__."""
        module_globals = {
            "__name__": "fake_pkg",
            "__file__": "/tmp/fake_pkg/__init__.py",
            "__all__": ["CONST"],
            "CONST": 42,
        }
        importer = LazySelectedImporter("fake_pkg", module_globals)
        assert importer.CONST == 42
        assert importer.__dict__["CONST"] == 42

    def test_raises_for_missing_attribute(self) -> None:
        """It raises AttributeError for unknown names."""
        with pytest.raises(AttributeError, match='has no attribute "missing"'):
            _ = LazySelectedImporter("fake_pkg", {"__name__": "fake_pkg", "__all__": []}).missing

    def test_lazy_loads_submodule_and_symbol(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """It loads a configured submodule and symbol on demand."""
        package_dir = tmp_path / "lazy_pkg"
        package_dir.mkdir()
        (package_dir / "__init__.py").write_text("__all__ = ['lazy_mod', 'Foo']\n")
        (package_dir / "lazy_mod.py").write_text("class Foo:\n    value = 7\n\nSENTINEL = 99\n")
        monkeypatch.syspath_prepend(str(tmp_path))
        imported_pkg = importlib.import_module("lazy_pkg")
        assert isinstance(imported_pkg, ModuleType)
        module_globals: dict[str, Any] = {
            "__name__": "lazy_pkg",
            "__all__": ["lazy_mod", "Foo"],
            "__file__": str(package_dir / "__init__.py"),
        }
        importer = LazySelectedImporter("lazy_pkg", module_globals, imported_structure={"lazy_mod": ["Foo"]})
        loaded_module = importer.lazy_mod
        loaded_class = importer.Foo
        assert isinstance(loaded_module, ModuleType)
        assert loaded_module.SENTINEL == 99
        assert loaded_class.value == 7

    def test_dir_and_reduce_raises_due_to_class_lookup(self) -> None:
        """It exposes directory entries and currently raises on reduce."""
        module_globals = {"__name__": "fake_pkg", "__file__": "/tmp/fake_pkg/__init__.py", "__all__": ["Foo"]}
        importer = LazySelectedImporter("fake_pkg", module_globals, imported_structure={"sub": ["Foo"]})
        assert "Foo" in importer.__dir__()
        with pytest.raises(AttributeError, match='has no attribute "__class__"'):
            LazySelectedImporter.__reduce__(importer)


class TestTryImport:
    """Tests for try_import context manager."""

    def test_successful_context(self) -> None:
        """It is successful and check does not raise when no errors happen."""
        with try_import() as deferred:
            _ = 1 + 1
        assert deferred.is_successful
        deferred.check()

    def test_defers_import_error(self) -> None:
        """It captures ImportError and raises a deferred ImportError on check."""
        with try_import() as deferred:
            raise ImportError("boom", name="missing_pkg")
        assert not deferred.is_successful
        with pytest.raises(ImportError, match="missing_pkg"):
            deferred.check()

    def test_defers_syntax_error(self) -> None:
        """It captures SyntaxError and raises a deferred ImportError on check."""
        with try_import() as deferred:
            raise SyntaxError("invalid syntax", ("bad_file.py", 1, 1, "x"))
        assert not deferred.is_successful
        with pytest.raises(ImportError, match="syntax error"):
            deferred.check()

    def test_does_not_swallow_other_exceptions(self) -> None:
        """It should propagate non-import related exceptions."""
        with pytest.raises(ValueError, match="other failure"):
            with try_import():
                raise ValueError("other failure")
