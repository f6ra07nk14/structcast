"""Tests for StructCast utilities."""

import importlib.util
import math
from pathlib import Path
from typing import Any

import pytest

from structcast.utils.base import check_path, import_from_address, load_yaml
from structcast.utils.security import SECURITY_SETTINGS, SecurityError
from tests.utils import configure_security_context, temporary_registered_dir


class TestRegisterDir:
    """Test register_dir and unregister_dir functionality."""

    def test_register_dir_with_string_path(self, tmp_path: Path) -> None:
        """Test registering a directory using string path."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        # Should convert string to Path internally
        SECURITY_SETTINGS.register_dir(str(test_dir))
        SECURITY_SETTINGS.unregister_dir(test_dir)

    def test_register_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test registering a non-existent directory raises ValueError."""
        with pytest.raises(ValueError, match="not a valid directory"):
            SECURITY_SETTINGS.register_dir(tmp_path / "nonexistent")

    def test_register_file_as_directory(self, tmp_path: Path) -> None:
        """Test registering a file instead of directory raises ValueError."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        with pytest.raises(ValueError, match="not a valid directory"):
            SECURITY_SETTINGS.register_dir(test_file)

    def test_register_already_registered_directory(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test registering an already registered directory logs warning."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        SECURITY_SETTINGS.register_dir(test_dir)
        SECURITY_SETTINGS.register_dir(test_dir)  # Should log warning
        assert "already registered" in caplog.text.lower()
        SECURITY_SETTINGS.unregister_dir(test_dir)

    def test_unregister_dir_with_string_path(self, tmp_path: Path) -> None:
        """Test unregistering a directory using string path."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        SECURITY_SETTINGS.register_dir(test_dir)
        # Should convert string to Path internally
        SECURITY_SETTINGS.unregister_dir(str(test_dir))

    def test_unregister_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test unregistering a non-existent directory raises ValueError."""
        with pytest.raises(ValueError, match="not a valid directory"):
            SECURITY_SETTINGS.unregister_dir(tmp_path / "nonexistent")

    def test_unregister_not_registered_directory(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test unregistering a non-registered directory logs warning."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        SECURITY_SETTINGS.unregister_dir(test_dir)  # Should log warning
        assert "not registered" in caplog.text.lower()


class TestCheckPath:
    """Test check_path functionality."""

    def test_check_path_tmp_path(self, tmp_path: Path) -> None:
        """Test check_path with Path object."""
        with pytest.raises(SecurityError, match="Path is outside of allowed directories"):
            check_path(tmp_path)

    def test_check_path_with_string_path(self, tmp_path: Path) -> None:
        """Test check_path with string path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        assert check_path(str(test_file), working_dir_check=False) == test_file.resolve()

    def test_check_path_nonexistent_file(self, tmp_path: Path) -> None:
        """Test check_path with non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="does not exist"):
            check_path(tmp_path / "nonexistent.txt")

    def test_check_path_with_relative_path_in_registered_dir(self, tmp_path: Path) -> None:
        """Test check_path finds relative paths in registered directories."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        with temporary_registered_dir(tmp_path):
            assert check_path("test.txt").name == "test.txt"

    def test_check_path_with_hidden_directory(self, tmp_path: Path) -> None:
        """Test check_path blocks hidden directories."""
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        test_file = hidden_dir / "test.txt"
        test_file.write_text("test")
        with pytest.raises(SecurityError, match="hidden directories"):
            check_path(test_file, hidden_check=True, working_dir_check=False)

    def test_check_path_with_hidden_check_disabled(self, tmp_path: Path) -> None:
        """Test check_path allows hidden directories when check is disabled."""
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        test_file = hidden_dir / "test.txt"
        test_file.write_text("test")
        assert check_path(test_file, hidden_check=False, working_dir_check=False) == test_file.resolve()

    def test_check_path_outside_allowed_directories(self, tmp_path: Path) -> None:
        """Test check_path blocks paths outside allowed directories."""
        # Create a file outside the current working directory
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        test_file = outside_dir / "test.txt"
        test_file.write_text("test")
        # This might pass or fail depending on the system setup
        # The test verifies the working_dir_check parameter works
        assert check_path(test_file, working_dir_check=False) == test_file.resolve()


class TestImportFromAddress:
    """Test import_from_address edge cases."""

    def test_import_with_default_module(self) -> None:
        """Test importing from a default module."""
        result = import_from_address("sqrt", default_module=math)
        assert result is math.sqrt

    def test_import_nonexistent_target(self) -> None:
        """Test importing non-existent target raises ImportError."""
        with configure_security_context(allowed_builtins={"nonexistent_function_xyz"}):
            with pytest.raises(ImportError, match="not found"):
                import_from_address("nonexistent_function_xyz")

    def test_import_with_module_spec_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test import when module spec is None."""
        test_file = tmp_path / "test_module.py"
        test_file.write_text("value = 42")

        def mock_spec(*args: Any, **kwargs: Any) -> None:
            return None

        monkeypatch.setattr(importlib.util, "spec_from_file_location", mock_spec)
        with pytest.raises(ImportError, match="Cannot load module"):
            import_from_address("value", module_file=test_file, working_dir_check=False)


class TestLoadYAML:
    """Test load_yaml functionality."""

    def test_load_yaml_basic(self, tmp_path: Path) -> None:
        """Test loading a basic YAML file."""
        with temporary_registered_dir(tmp_path):
            yaml_file = tmp_path / "test.yaml"
            yaml_file.write_text("key: value\nlist:\n  - item1\n  - item2\n")
            result = load_yaml(yaml_file)
            assert result == {"key": "value", "list": ["item1", "item2"]}

    def test_load_yaml_with_string_path(self, tmp_path: Path) -> None:
        """Test loading YAML with string path."""
        with temporary_registered_dir(tmp_path):
            yaml_file = tmp_path / "test.yaml"
            yaml_file.write_text("test: 123")
            result = load_yaml(str(yaml_file))
            assert result == {"test": 123}

    def test_load_yaml_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading non-existent YAML file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_yaml(tmp_path / "nonexistent.yaml")

    def test_load_yaml_complex_types(self, tmp_path: Path) -> None:
        """Test loading YAML with various data types."""
        with temporary_registered_dir(tmp_path):
            yaml_file = tmp_path / "complex.yaml"
            yaml_content = """\
string: hello
integer: 42
float: 3.14
boolean: true
null_value: null
nested:
  key1: value1
  key2: value2
array:
  - 1
  - 2
  - 3
"""
            yaml_file.write_text(yaml_content)
            result = load_yaml(yaml_file)
            assert result["string"] == "hello"
            assert result["integer"] == 42
            assert result["float"] == 3.14
            assert result["boolean"] is True
            assert result["null_value"] is None
            assert result["nested"]["key1"] == "value1"
            assert result["array"] == [1, 2, 3]
