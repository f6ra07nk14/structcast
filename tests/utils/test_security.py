"""Tests for security features in import_from_address."""

from collections.abc import Iterable
import json
import math
from typing import List

import pytest

from structcast.utils.base import (
    SecurityError,
    configure_security,
    import_from_address,
)
from structcast.utils.constants import DEFAULT_BLOCKED_BUILTINS, DEFAULT_BLOCKED_MODULES


class TestSecurityBlocking:
    """Test that dangerous imports are blocked by default."""

    def test_block_os_module(self) -> None:
        """Test that os module is blocked."""
        with pytest.raises(SecurityError, match="os.*blocked"):
            import_from_address("os.system")

    def test_block_subprocess_module(self) -> None:
        """Test that subprocess module is blocked."""
        with pytest.raises(SecurityError, match="subprocess.*blocked"):
            import_from_address("subprocess.run")

    def test_block_eval_builtin(self) -> None:
        """Test that eval builtin is blocked."""
        with pytest.raises(SecurityError, match="eval.*blocked"):
            import_from_address("eval")

    def test_block_exec_builtin(self) -> None:
        """Test that exec builtin is blocked."""
        with pytest.raises(SecurityError, match="exec.*blocked"):
            import_from_address("exec")

    def test_block_compile_builtin(self) -> None:
        """Test that compile builtin is blocked."""
        with pytest.raises(SecurityError, match="compile.*blocked"):
            import_from_address("compile")

    def test_block_open_builtin(self) -> None:
        """Test that open builtin is blocked."""
        with pytest.raises(SecurityError, match="open.*blocked"):
            import_from_address("open")

    def test_block_import_builtin(self) -> None:
        """Test that __import__ builtin is blocked."""
        with pytest.raises(SecurityError, match="__import__.*blocked"):
            import_from_address("__import__")


class TestSecurityAllowedImports:
    """Test that safe imports still work."""

    def test_allow_safe_builtins(self) -> None:
        """Test that safe builtins like int, str, list are allowed."""
        assert import_from_address("int") is int
        assert import_from_address("str") is str
        assert import_from_address("list") is list
        assert import_from_address("dict") is dict

    def test_allow_safe_modules(self) -> None:
        """Test that safe modules like math, json are allowed."""
        assert import_from_address("math.sqrt") is math.sqrt
        assert import_from_address("json.loads") is json.loads

    def test_allow_typing_module(self) -> None:
        """Test that typing module is allowed."""
        assert import_from_address("typing.List") is List


class TestSecurityConfiguration:
    """Test security configuration options."""

    def test_custom_blocked_modules(self) -> None:
        """Test custom blocked modules."""
        # Block json module
        configure_security(blocked_modules={"json"})
        try:
            with pytest.raises(SecurityError, match="json.*blocked"):
                import_from_address("json.loads")
        finally:
            # Restore defaults
            configure_security(blocked_modules=DEFAULT_BLOCKED_MODULES.copy())

    def test_custom_blocked_builtins(self) -> None:
        """Test custom blocked builtins."""
        # Block int builtin
        configure_security(blocked_builtins={"int"})
        try:
            with pytest.raises(SecurityError, match="int.*blocked"):
                import_from_address("int")
        finally:
            # Restore defaults
            configure_security(blocked_builtins=DEFAULT_BLOCKED_BUILTINS.copy())

    def test_allowlist_mode(self) -> None:
        """Test allowlist mode."""
        # Only allow math module
        configure_security(allowed_modules={"math", "builtins"})
        try:
            assert import_from_address("math.sqrt") is math.sqrt

            # json should be blocked
            with pytest.raises(SecurityError, match="blocked"):
                import_from_address("json.loads")
        finally:
            # Restore to blocklist mode
            configure_security(allowed_modules=None)

    def test_security_check_parameter(self) -> None:
        """Test security_check parameter."""
        # Should allow dangerous import when explicitly skipped
        result = import_from_address("eval", security_check=False)
        assert result is eval


class TestSecurityEdgeCases:
    """Test edge cases in security checks."""

    def test_nested_module_blocking(self) -> None:
        """Test that nested modules are blocked if base is blocked."""
        with pytest.raises(SecurityError, match="os"):
            import_from_address("os.path.join")

    def test_safe_nested_modules(self) -> None:
        """Test that nested safe modules work."""
        assert import_from_address("collections.abc.Iterable") is Iterable

    def test_error_message_includes_blocked_module(self) -> None:
        """Test that error message is informative."""
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

    def test_default_blocked_builtins_not_empty(self) -> None:
        """Test that default blocked builtins is not empty."""
        assert len(DEFAULT_BLOCKED_BUILTINS) > 0
        assert "eval" in DEFAULT_BLOCKED_BUILTINS
        assert "exec" in DEFAULT_BLOCKED_BUILTINS
