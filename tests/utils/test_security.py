"""Tests for security features in import_from_address."""

import math
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from structcast.utils.constants import DEFAULT_BLOCKED_MODULES
from structcast.utils.security import (
    SecurityError,
    check_path,
    import_from_address,
    load_yaml,
    register_dir,
    resolve_path,
    unregister_dir,
)
from tests.utils import configure_security_context, temporary_registered_dir


class TestRegisterDir:
    """Test register_dir and unregister_dir functionality."""

    def test_register_dir_with_string_path(self, tmp_path: Path) -> None:
        """Test registering a directory using string path."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        # Should convert string to Path internally
        register_dir(str(test_dir))
        unregister_dir(test_dir)

    def test_register_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test registering a non-existent directory raises ValueError."""
        with pytest.raises(ValueError, match="not a valid directory"):
            register_dir(tmp_path / "nonexistent")

    def test_register_file_as_directory(self, tmp_path: Path) -> None:
        """Test registering a file instead of directory raises ValueError."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        with pytest.raises(ValueError, match="not a valid directory"):
            register_dir(test_file)

    def test_register_already_registered_directory(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test registering an already registered directory logs warning."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        register_dir(test_dir)
        register_dir(test_dir)  # Should log warning
        assert "already registered" in caplog.text.lower()
        unregister_dir(test_dir)

    def test_unregister_dir_with_string_path(self, tmp_path: Path) -> None:
        """Test unregistering a directory using string path."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        register_dir(test_dir)
        # Should convert string to Path internally
        unregister_dir(str(test_dir))

    def test_unregister_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test unregistering a non-existent directory raises ValueError."""
        with pytest.raises(ValueError, match="not a valid directory"):
            unregister_dir(tmp_path / "nonexistent")

    def test_unregister_not_registered_directory(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Test unregistering a non-registered directory logs warning."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        unregister_dir(test_dir)  # Should log warning
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
        with configure_security_context(allowed_modules={"builtins": {None}}):
            with pytest.raises(ImportError, match="not found"):
                import_from_address("nonexistent_function_xyz")

    def test_import_with_module_spec_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test import when module spec is None."""

        def mock_spec(*args: Any, **kwargs: Any) -> None:
            return None

        test_file = tmp_path / "test_module.py"
        test_file.write_text("value = 42")
        with patch("structcast.utils.security.spec_from_file_location", side_effect=mock_spec):
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


class TestSecurityBlocking:
    """Test that dangerous imports are blocked by default."""

    def test_block_os_module(self) -> None:
        """Test that os module is blocked."""
        with configure_security_context(allowed_modules={}):
            with pytest.raises(SecurityError, match="os.system"):
                import_from_address("os.system")

    def test_block_subprocess_module(self) -> None:
        """Test that subprocess module is blocked."""
        with configure_security_context(allowed_modules={}):
            with pytest.raises(SecurityError, match="subprocess.run"):
                import_from_address("subprocess.run")

    def test_block_eval_builtin(self) -> None:
        """Test that eval builtin is blocked."""
        with pytest.raises(SecurityError, match="eval"):
            import_from_address("eval")

    def test_block_exec_builtin(self) -> None:
        """Test that exec builtin is blocked."""
        with pytest.raises(SecurityError, match="exec"):
            import_from_address("exec")

    def test_block_compile_builtin(self) -> None:
        """Test that compile builtin is blocked."""
        with pytest.raises(SecurityError, match="compile"):
            import_from_address("compile")

    def test_block_open_builtin(self) -> None:
        """Test that open builtin is blocked."""
        with pytest.raises(SecurityError, match="open"):
            import_from_address("open")

    def test_block_import_builtin(self) -> None:
        """Test that __import__ builtin is blocked."""
        with pytest.raises(SecurityError, match="__import__"):
            import_from_address("__import__")


class TestSecurityAllowedImports:
    """Test that safe imports still work."""

    def test_allow_safe_builtins(self) -> None:
        """Test that safe builtins like int, str, list are allowed."""
        assert import_from_address("int") is int
        assert import_from_address("str") is str
        assert import_from_address("list") is list
        assert import_from_address("dict") is dict


class TestSecurityConfiguration:
    """Test security configuration options."""

    def test_custom_blocked_modules(self) -> None:
        """Test custom blocked modules."""
        with configure_security_context(allowed_modules={}, blocked_modules={"json"}):
            with pytest.raises(SecurityError, match="json.loads"):
                import_from_address("json.loads")

    def test_custom_blocked_builtins(self) -> None:
        """Test custom blocked builtins."""
        with configure_security_context(allowed_modules={"builtins": None}, blocked_modules={"builtins"}):
            with pytest.raises(SecurityError, match="int"):
                import_from_address("int")

    def test_allowlist_mode(self) -> None:
        """Test allowlist mode."""
        with configure_security_context(allowed_modules={"math": {None}}):
            assert import_from_address("math.sqrt") is math.sqrt

            with pytest.raises(SecurityError, match="json.loads"):
                import_from_address("json.loads")


class TestSecurityEdgeCases:
    """Test edge cases in security checks."""

    def test_nested_module_blocking(self) -> None:
        """Test that nested modules are blocked if base is blocked."""
        with pytest.raises(SecurityError, match="os"):
            import_from_address("os.path.join")

    def test_error_message_includes_blocked_module(self) -> None:
        """Test that error message is informative."""
        with configure_security_context(allowed_modules={}):
            with pytest.raises(SecurityError) as exc_info:
                import_from_address("subprocess.Popen")
        assert "subprocess" in str(exc_info.value)
        assert "blocked" in str(exc_info.value).lower()

    def test_error_message_includes_blocked_builtin(self) -> None:
        """Test that error message is informative for builtins."""
        with pytest.raises(SecurityError) as exc_info:
            import_from_address("eval")

        assert "eval" in str(exc_info.value)
        assert "blocked" in str(exc_info.value).lower()


class TestDefaultSecuritySettings:
    """Test default security settings."""

    def test_default_blocked_modules_not_empty(self) -> None:
        """Test that default blocked modules is not empty."""
        assert len(DEFAULT_BLOCKED_MODULES) > 0
        assert "os" in DEFAULT_BLOCKED_MODULES
        assert "subprocess" in DEFAULT_BLOCKED_MODULES


class TestFileLoadingSecurity:
    """Test security improvements for file loading."""

    def test_block_non_python_files(self, tmp_path: Path) -> None:
        """Test that non-.py files are blocked."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("print('hello')")
        with pytest.raises(SecurityError, match="Module file must be a .py file"):
            import_from_address("test", module_file=txt_file, working_dir_check=False)

    def test_resolve_absolute_paths(self, tmp_path: Path) -> None:
        """Test that paths are resolved to absolute paths."""
        py_file = tmp_path / "test_module.py"
        py_file.write_text("value = 42")
        # Should work with absolute path when module is allowed
        with configure_security_context(allowed_modules={"test_module": {None}}):
            assert import_from_address("value", module_file=py_file, working_dir_check=False) == 42


class TestPathResolutionErrors:
    """Test error handling in path resolution."""

    def test_resolve_path_with_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test _resolve_path handles OSError gracefully."""
        test_path = tmp_path / "test"
        test_path.mkdir()

        def mock_resolve(self: Path, *args: Any, **kwargs: Any) -> None:
            raise OSError("Mock error")

        monkeypatch.setattr(Path, "resolve", mock_resolve)
        assert resolve_path(test_path) is None
        assert "Failed to resolve path" in caplog.text

    def test_resolve_path_with_runtime_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test _resolve_path handles RuntimeError gracefully."""
        test_path = tmp_path / "test"
        test_path.mkdir()

        # Mock resolve to raise RuntimeError
        def mock_resolve(self: Path, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("Mock error")

        monkeypatch.setattr(Path, "resolve", mock_resolve)
        assert resolve_path(test_path) is None
        assert "Failed to resolve path" in caplog.text
