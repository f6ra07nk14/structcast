"""Tests for security features in import_from_address."""

import math
from pathlib import Path

import pytest

from structcast.utils.base import SecurityError, import_from_address
from structcast.utils.constants import DEFAULT_BLOCKED_MODULES
from tests.utils import configure_security_context


class TestSecurityBlocking:
    """Test that dangerous imports are blocked by default."""

    def test_block_os_module(self) -> None:
        """Test that os module is blocked."""
        with configure_security_context(allowed_modules={None}):
            with pytest.raises(SecurityError, match="os.system"):
                import_from_address("os.system")

    def test_block_subprocess_module(self) -> None:
        """Test that subprocess module is blocked."""
        with configure_security_context(allowed_modules={None}):
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
        with configure_security_context(allowed_modules={None}, blocked_modules={"json"}):
            with pytest.raises(SecurityError, match="json.loads"):
                import_from_address("json.loads")

    def test_custom_blocked_builtins(self) -> None:
        """Test custom blocked builtins."""
        with configure_security_context(allowed_builtins=set()):
            with pytest.raises(SecurityError, match="int"):
                import_from_address("int")

    def test_allowlist_mode(self) -> None:
        """Test allowlist mode."""
        with configure_security_context(allowed_modules={"math", "builtins"}):
            assert import_from_address("math.sqrt") is math.sqrt

            with pytest.raises(SecurityError, match="json.loads"):
                import_from_address("json.loads")

    def test_security_check_parameter(self) -> None:
        """Test security_check parameter."""
        assert import_from_address("eval", security_check=False) is eval


class TestSecurityEdgeCases:
    """Test edge cases in security checks."""

    def test_nested_module_blocking(self) -> None:
        """Test that nested modules are blocked if base is blocked."""
        with pytest.raises(SecurityError, match="os"):
            import_from_address("os.path.join")

    def test_error_message_includes_blocked_module(self) -> None:
        """Test that error message is informative."""
        with configure_security_context(allowed_modules={None}):
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
        with configure_security_context(allowed_modules={"test_module"}):
            assert import_from_address("value", module_file=py_file, working_dir_check=False) == 42
