"""Tests for instantiation functionalities - Fixed version."""

from collections import Counter
from collections.abc import Generator
import math
from pathlib import Path
import time
from typing import Any, Callable
from unittest.mock import patch

from pydantic import ValidationError
import pytest

from structcast.core.constants import MAX_INSTANTIATION_DEPTH
from structcast.core.instantiator import (
    AddressPattern,
    AttributePattern,
    BindPattern,
    CallPattern,
    InstantiationError,
    ObjectPattern,
    PatternResult,
    instantiate,
)
from structcast.utils.base import SecurityError
from tests.utils import configure_security_context, temporary_registered_dir

# ============================================================================
# Test 1: Basic Pattern Schema and Validation
# ============================================================================


class TestPatternSchemas:
    """Test schema validation for all Pattern types."""

    def test_address_pattern_valid(self) -> None:
        """Test AddressPattern with valid address using model_validate."""
        pattern = AddressPattern.model_validate({"_addr_": "list"})
        assert pattern.address == "list"
        assert pattern.file is None

    def test_address_pattern_empty_address(self) -> None:
        """Test AddressPattern rejects empty address."""
        with pytest.raises(ValidationError):
            AddressPattern.model_validate({"_addr_": ""})

    def test_address_pattern_with_file(self, tmp_path: Path) -> None:
        """Test AddressPattern with file path."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")
        assert AddressPattern.model_validate({"_addr_": "foo", "_file_": test_file}).file == test_file

    def test_attribute_pattern_valid(self) -> None:
        """Test AttributePattern with valid attribute."""
        assert AttributePattern.model_validate({"_attr_": "append"}).attribute == "append"

    def test_attribute_pattern_empty_attribute(self) -> None:
        """Test AttributePattern rejects empty attribute."""
        with pytest.raises(ValidationError):
            AttributePattern.model_validate({"_attr_": ""})

    def test_attribute_pattern_invalid_identifier(self) -> None:
        """Test AttributePattern rejects invalid identifier."""
        with pytest.raises(SecurityError):
            AttributePattern.model_validate({"_attr_": "123invalid"})

    def test_attribute_pattern_private_member(self) -> None:
        """Test AttributePattern rejects private members."""
        # Validation during model_validate raises SecurityError wrapped in ValidationError context
        with pytest.raises((ValidationError, SecurityError)):
            AttributePattern.model_validate({"_attr_": "__private"})

    def test_attribute_pattern_protected_member(self) -> None:
        """Test AttributePattern rejects protected members."""
        # Validation during model_validate raises SecurityError wrapped in ValidationError context
        with pytest.raises((ValidationError, SecurityError)):
            AttributePattern.model_validate({"_attr_": "_protected"})

    def test_call_pattern_valid(self) -> None:
        """Test CallPattern with valid call."""
        assert CallPattern.model_validate({"_call_": {"a": 1, "b": 2}}).call == {"a": 1, "b": 2}

    def test_call_pattern_empty_call(self) -> None:
        """Test CallPattern with empty call."""
        assert CallPattern.model_validate("_call_").call == {}

    def test_call_pattern_invalid_string(self) -> None:
        """Test CallPattern rejects invalid string."""
        with pytest.raises(ValidationError):
            CallPattern.model_validate("invalid")

    def test_bind_pattern_valid(self) -> None:
        """Test BindPattern with valid bind."""
        assert BindPattern.model_validate({"_bind_": {"a": 1}}).bind == {"a": 1}

    def test_bind_pattern_empty_bind(self) -> None:
        """Test BindPattern rejects empty bind."""
        with pytest.raises(ValidationError):
            BindPattern.model_validate({"_bind_": {}})

    def test_object_pattern_valid(self) -> None:
        """Test ObjectPattern with valid object."""
        assert len(ObjectPattern.model_validate({"_obj_": [{"_addr_": "list"}]}).object) == 1

    def test_object_pattern_tuple_format(self) -> None:
        """Test ObjectPattern with tuple format."""
        assert len(ObjectPattern.model_validate(["_obj_", {"_addr_": "list"}]).object) == 1

    def test_object_pattern_empty_object(self) -> None:
        """Test ObjectPattern rejects empty object."""
        with pytest.raises(ValidationError):
            ObjectPattern.model_validate({"_obj_": []})

    def test_pattern_frozen(self) -> None:
        """Test that patterns are frozen (immutable)."""
        with pytest.raises(ValidationError):
            AddressPattern.model_validate({"_addr_": "list"}).address = "dict"  # type: ignore

    def test_pattern_extra_forbid(self) -> None:
        """Test that patterns forbid extra fields."""
        with pytest.raises(ValidationError):
            AddressPattern.model_validate({"_addr_": "list", "extra": "field"})


# ============================================================================
# Test 2: Pattern Build Functions
# ============================================================================


class TestPatternBuild:
    """Test build methods for all Pattern types."""

    def test_address_pattern_build_builtin(self) -> None:
        """Test AddressPattern.build with builtin."""
        result = AddressPattern.model_validate({"_addr_": "list"}).build()
        assert len(result.runs) == 1
        assert result.runs[0] is list
        assert len(result.patterns) == 1

    def test_address_pattern_build_module(self) -> None:
        """Test AddressPattern.build with module import."""
        result = AddressPattern.model_validate({"_addr_": "collections.Counter"}).build()
        assert len(result.runs) == 1
        assert result.runs[0] is Counter

    def test_address_pattern_build_with_file(self, tmp_path: Path) -> None:
        """Test AddressPattern.build with file path."""
        test_file = tmp_path / "mymodule.py"
        test_file.write_text("def my_func(): return 42")
        # Need to allow the custom module temporarily
        with temporary_registered_dir(tmp_path), configure_security_context(allowed_modules={"mymodule"}):
            result = AddressPattern.model_validate({"_addr_": "my_func", "_file_": test_file}).build()
            assert len(result.runs) == 1
            assert callable(result.runs[0])
            assert result.runs[0]() == 42

    def test_attribute_pattern_build_success(self) -> None:
        """Test AttributePattern.build with valid attribute."""
        result = AttributePattern.model_validate({"_attr_": "append"}).build(PatternResult(runs=[list]))
        assert len(result.runs) == 1
        assert result.runs[0] is list.append

    def test_attribute_pattern_build_no_object(self) -> None:
        """Test AttributePattern.build fails with no object."""
        with pytest.raises(InstantiationError, match="No object to access attribute"):
            AttributePattern.model_validate({"_attr_": "append"}).build()

    def test_attribute_pattern_build_missing_attribute(self) -> None:
        """Test AttributePattern.build fails with missing attribute."""
        with pytest.raises(InstantiationError, match="Attribute .* not found"):
            AttributePattern.model_validate({"_attr_": "nonexistent"}).build(PatternResult(runs=[list]))

    def test_call_pattern_build_success(self) -> None:
        """Test CallPattern.build with callable."""

        def add(a: Any, b: Any) -> Any:
            return a + b

        result = CallPattern.model_validate({"_call_": {"a": 1, "b": 2}}).build(PatternResult(runs=[add]))
        assert len(result.runs) == 1
        assert result.runs[0] == 3

    def test_call_pattern_build_no_args(self) -> None:
        """Test CallPattern.build with no arguments."""
        result = CallPattern.model_validate({"_call_": {}}).build(PatternResult(runs=[list]))
        assert len(result.runs) == 1
        assert result.runs[0] == []

        result = CallPattern.model_validate("_call_").build(PatternResult(runs=[list]))
        assert len(result.runs) == 1
        assert result.runs[0] == []

    def test_call_pattern_build_no_object(self) -> None:
        """Test CallPattern.build fails with no object."""
        with pytest.raises(InstantiationError, match="No object to call"):
            CallPattern.model_validate({"_call_": {}}).build()

    def test_call_pattern_build_not_callable(self) -> None:
        """Test CallPattern.build fails with non-callable."""
        with pytest.raises(InstantiationError, match="not callable"):
            CallPattern.model_validate("_call_").build(PatternResult(runs=[42]))

    def test_bind_pattern_build_success(self) -> None:
        """Test BindPattern.build with callable."""

        def add(a: Any, b: Any) -> Any:
            return a + b

        result = BindPattern.model_validate({"_bind_": {"a": 10}}).build(PatternResult(runs=[add]))
        assert len(result.runs) == 1
        assert callable(result.runs[0])
        assert result.runs[0](b=5) == 15

    def test_bind_pattern_build_no_object(self) -> None:
        """Test BindPattern.build fails with no object."""
        with pytest.raises(InstantiationError, match="No object to bind"):
            BindPattern.model_validate({"_bind_": {"a": 1}}).build()

    def test_bind_pattern_build_not_callable(self) -> None:
        """Test BindPattern.build fails with non-callable."""
        with pytest.raises(InstantiationError, match="not callable"):
            BindPattern.model_validate({"_bind_": {"a": 1}}).build(PatternResult(runs=["string"]))

    def test_object_pattern_build_simple(self) -> None:
        """Test ObjectPattern.build with simple pattern."""
        result = ObjectPattern.model_validate({"_obj_": [{"_addr_": "list"}]}).build()
        assert len(result.runs) == 1
        assert result.runs[0] is list

        result = ObjectPattern.model_validate(["_obj_", {"_addr_": "list"}]).build()
        assert len(result.runs) == 1
        assert result.runs[0] is list

    def test_object_pattern_build_chain(self) -> None:
        """Test ObjectPattern.build with chained patterns."""
        result = ObjectPattern.model_validate({"_obj_": [{"_addr_": "list"}, "_call_"]}).build()
        assert len(result.runs) == 1
        assert result.runs[0] == []

        result = ObjectPattern.model_validate(["_obj_", {"_addr_": "list"}, "_call_"]).build()
        assert len(result.runs) == 1
        assert result.runs[0] == []

    def test_object_pattern_build_nested(self) -> None:
        """Test ObjectPattern.build with nested patterns."""
        result = ObjectPattern.model_validate({"_obj_": [["_obj_", {"_addr_": "dict"}], "_call_"]}).build()
        assert len(result.runs) == 1
        assert result.runs[0] == {}

        result = ObjectPattern.model_validate(["_obj_", ["_obj_", {"_addr_": "dict"}], "_call_"]).build()
        assert len(result.runs) == 1
        assert result.runs[0] == {}

    def test_object_pattern_build_invalid_content(self) -> None:
        """Test ObjectPattern.build fails with invalid content."""
        with pytest.raises(InstantiationError, match="Failed to validate"):
            ObjectPattern.model_validate({"_obj_": [{"invalid": "pattern"}]}).build()

    def test_pattern_result_immutability(self) -> None:
        """Test that PatternResult preserves previous state."""
        initial = PatternResult(runs=[list])
        pattern = AddressPattern.model_validate({"_addr_": "dict"})
        result = pattern.build(initial)
        # Original should be unchanged
        assert len(initial.runs) == 1
        assert initial.runs[0] is list
        # New result should have both
        assert len(result.runs) == 2
        assert result.runs[0] is list
        assert result.runs[1] is dict


# ============================================================================
# Test 3: Instantiate Function Integration
# ============================================================================


class TestInstantiateFunction:
    """Test the main instantiate function."""

    @pytest.mark.parametrize(
        "value",
        [42, 3.14, True, False, None, b"bytes", Path("/tmp/test"), "hello", {"a": 1, "b": 2}, [1, 2, 3], (1, 2, 3)],
        ids=["integer", "float", "true", "false", "none", "bytes", "path", "string", "dict", "list", "tuple"],
    )
    def test_instantiate_value(self, value: Any) -> None:
        """Test instantiate with various primitive values."""
        assert instantiate(value) == value

    def test_instantiate_nested_structures(self) -> None:
        """Test instantiate with nested structures."""
        config = {"a": [1, 2, {"b": 3}], "c": {"d": [4, 5]}}
        result = instantiate(config)
        assert result == config

    def test_instantiate_simple_address(self) -> None:
        """Test instantiate with simple address pattern."""
        assert instantiate(["_obj_", {"_addr_": "list"}]) is list

    def test_instantiate_call_pattern(self) -> None:
        """Test instantiate with call pattern."""
        assert instantiate(["_obj_", {"_addr_": "list"}, {"_call_": {}}]) == []

    def test_instantiate_dict_creation(self) -> None:
        """Test instantiate creating dict with items."""
        assert instantiate(["_obj_", {"_addr_": "dict"}, {"_call_": {"a": 1, "b": 2}}]) == {"a": 1, "b": 2}

    def test_instantiate_bind_pattern(self) -> None:
        """Test instantiate with bind pattern."""
        result = instantiate(["_obj_", {"_addr_": "int"}, {"_bind_": {"base": 16}}])
        assert callable(result)
        assert result("FF") == 255

    def test_instantiate_nested_objects(self) -> None:
        """Test instantiate with nested object patterns."""
        result = instantiate(
            {
                "list_class": ["_obj_", {"_addr_": "list"}],
                "empty_list": ["_obj_", {"_addr_": "list"}, {"_call_": {}}],
                "dict_with_items": ["_obj_", {"_addr_": "dict"}, {"_call_": {"x": 10, "y": 20}}],
            }
        )
        assert result["list_class"] is list
        assert result["empty_list"] == []
        assert result["dict_with_items"] == {"x": 10, "y": 20}

    def test_instantiate_complex_nested_config(self) -> None:
        """Test instantiate with complex nested configuration."""
        config = {
            "name": "test",
            "count": 42,
            "factory": ["_obj_", {"_addr_": "list"}],
            "items": [
                ["_obj_", {"_addr_": "dict"}, {"_call_": {"a": 1}}],
                ["_obj_", {"_addr_": "dict"}, {"_call_": {"b": 2}}],
            ],
        }
        result = instantiate(config)
        assert result["name"] == "test"
        assert result["count"] == 42
        assert result["factory"] is list
        assert result["items"][0] == {"a": 1}
        assert result["items"][1] == {"b": 2}

    def test_instantiate_invalid_pattern(self) -> None:
        """Test instantiate with invalid pattern."""
        assert instantiate(["_pattern_", {"random": "data"}]) == ["_pattern_", {"random": "data"}]

    def test_instantiate_partial_application(self) -> None:
        """Test instantiate creating partial function."""
        result = instantiate(["_obj_", {"_addr_": "pow"}, {"_bind_": {"exp": 2}}])
        assert callable(result)
        assert result(base=5) == 25


# ============================================================================
# Test 4: Security and Injection Attack Tests
# ============================================================================


class TestSecurityAndInjectionAttacks:
    """Test security features and attempt injection attacks."""

    def test_blocked_os_module(self) -> None:
        """Test that os module is blocked by allowlist."""
        with pytest.raises(SecurityError, match="os.system"):
            instantiate(["_obj_", {"_addr_": "os.system"}])

    def test_blocked_subprocess_module(self) -> None:
        """Test that subprocess module is blocked."""
        with pytest.raises(SecurityError, match="subprocess.run"):
            instantiate(["_obj_", {"_addr_": "subprocess.run"}])

    def test_blocked_eval_builtin(self) -> None:
        """Test that eval builtin is blocked."""
        with pytest.raises(SecurityError, match="eval"):
            instantiate(["_obj_", {"_addr_": "eval"}])

    def test_blocked_exec_builtin(self) -> None:
        """Test that exec builtin is blocked."""
        with pytest.raises(SecurityError, match="exec"):
            instantiate(["_obj_", {"_addr_": "exec"}])

    def test_blocked_compile_builtin(self) -> None:
        """Test that compile builtin is blocked."""
        with pytest.raises(SecurityError, match="compile"):
            instantiate(["_obj_", {"_addr_": "compile"}])

    def test_blocked_open_builtin(self) -> None:
        """Test that open builtin is blocked."""
        with pytest.raises(SecurityError, match="open"):
            instantiate(["_obj_", {"_addr_": "open"}])

    def test_blocked_getattr(self) -> None:
        """Test that getattr builtin is blocked."""
        with pytest.raises(SecurityError, match="getattr"):
            instantiate(["_obj_", {"_addr_": "getattr"}])

    def test_blocked_setattr(self) -> None:
        """Test that setattr builtin is blocked."""
        with pytest.raises(SecurityError, match="setattr"):
            instantiate(["_obj_", {"_addr_": "setattr"}])

    def test_blocked_globals(self) -> None:
        """Test that globals builtin is blocked."""
        with pytest.raises(SecurityError, match="globals"):
            instantiate(["_obj_", {"_addr_": "globals"}])

    def test_private_member_access(self) -> None:
        """Test that private members cannot be accessed."""
        # This raises SecurityError during validation, which is caught and wrapped
        with pytest.raises((ValidationError, SecurityError)):
            instantiate(["_obj_", {"_addr_": "list"}, {"_attr_": "__class__"}])

    def test_protected_member_access(self) -> None:
        """Test that protected members cannot be accessed."""
        with pytest.raises((ValidationError, SecurityError)):
            instantiate(["_obj_", {"_addr_": "list"}, {"_attr_": "_abc_impl"}])

    def test_safe_builtin_access_allowed(self) -> None:
        """Test that safe builtins are allowed."""
        assert instantiate(["_obj_", {"_addr_": "len"}]) is len

    def test_math_module_allowed(self) -> None:
        """Test that math module is allowed by default."""
        assert instantiate(["_obj_", {"_addr_": "math.sqrt"}]) is math.sqrt

    def test_injection_attempt_via_import(self) -> None:
        """Test that __import__ is blocked."""
        with pytest.raises(SecurityError, match="__import__"):
            instantiate(["_obj_", {"_addr_": "__import__"}])

    def test_injection_attempt_type_blocked(self) -> None:
        """Test that type builtin is blocked."""
        with pytest.raises(SecurityError, match="type"):
            instantiate(["_obj_", {"_addr_": "type"}])


# ============================================================================
# Test 5: Security Bypass Attempts with configure_security (allowed_modules only)
# ============================================================================


class TestSecurityBypassWithConfigureSecurity:
    """Test attempts to bypass security using only allowed_modules parameter."""

    @pytest.fixture(autouse=True)
    def wrap_context(self) -> Generator[None, Any, None]:
        """Automatically wrap each test in a security context allowing all modules."""
        with configure_security_context(allowed_modules={None}):
            yield

    @pytest.mark.parametrize("builtin", ["eval", "exec", "compile", "__import__", "getattr", "setattr", "globals"])
    def test_allowed_modules_does_not_bypass_blocked_builtins(self, builtin: str) -> None:
        """Verify that allowed_modules cannot bypass blocked_builtins."""
        # Dangerous builtins still blocked
        with pytest.raises(SecurityError, match=builtin):
            instantiate(["_obj_", {"_addr_": builtin}])

    @pytest.mark.parametrize(
        "addr",
        ["os.system", "subprocess.run", "sys.exit", "importlib.import_module", "pickle.loads", "marshal.loads"],
    )
    def test_allowed_modules_does_not_bypass_blocked_modules(self, addr: str) -> None:
        """Verify that allowed_modules cannot bypass blocked_modules."""
        # Dangerous modules should still be blocked
        with pytest.raises(SecurityError, match=addr):
            instantiate(["_obj_", {"_addr_": addr}])

    def test_conclusion_security_is_layered(self) -> None:
        """Demonstrate that security is properly layered."""
        # Private member protection
        with pytest.raises((ValidationError, SecurityError)):
            instantiate(["_obj_", {"_addr_": "list"}, {"_attr_": "__class__"}])


class TestRecursionDepthProtection:
    """Test protection against deep recursion attacks."""

    def test_deep_nesting_blocked(self) -> None:
        """Test that deeply nested configurations are blocked."""
        # Create a deeply nested configuration
        config: dict[str, Any] = {"_obj_": ["int"]}
        for _ in range(MAX_INSTANTIATION_DEPTH):  # Exceed MAX_INSTANTIATION_DEPTH (100)
            config = {"_obj_": [{"_addr_": "dict"}, {"_call_": {"value": config}}]}
        with pytest.raises(InstantiationError, match="Maximum instantiation depth.*exceeded"):
            instantiate(config)

    def test_recursive_dict_structure(self) -> None:
        """Test protection against recursive dictionary structures."""
        # Create nested dicts with object patterns
        config: dict[str, Any] = {"_obj_": [{"_addr_": "dict"}, {"_call_": {"value": "test"}}]}
        for i in range(MAX_INSTANTIATION_DEPTH):
            config = {"_obj_": [{"_addr_": "dict"}, {"_call_": {f"level_{i}": config}}]}
        # This should trigger depth protection
        with pytest.raises(InstantiationError, match="Maximum instantiation depth.*exceeded"):
            instantiate(config)

    def test_recursive_list_structure(self) -> None:
        """Test protection against recursive list structures."""
        config: list[Any] = [1, 2, 3]
        for _ in range(MAX_INSTANTIATION_DEPTH):
            config = [config]
        with pytest.raises(InstantiationError, match="Maximum instantiation depth.*exceeded"):
            instantiate(config)


class TestAttributeValidationImprovements:
    """Test improved attribute validation."""

    @pytest.mark.parametrize(
        "dunder",
        [
            "__subclasses__",
            "__bases__",
            "__globals__",
            "__code__",
            "__dict__",
            "__class__",
            "__mro__",
            "__init__",
            "__import__",
        ],
    )
    def test_block_dangerous_dunders(self, dunder: str) -> None:
        """Test that dangerous dunder methods are blocked."""
        with pytest.raises(SecurityError, match=dunder):
            instantiate({"_obj_": [{"_addr_": "int"}, {"_attr_": dunder}]})

    def test_block_non_ascii_attributes(self) -> None:
        """Test that non-ASCII attribute names are blocked."""
        # Try to use Unicode lookalikes
        with pytest.raises(SecurityError, match="Non-ASCII"):
            instantiate({"_obj_": [{"_addr_": "int"}, {"_attr_": "ｒｅａｌ"}]})  # Full-width characters

        with pytest.raises(SecurityError, match="Non-ASCII"):
            instantiate({"_obj_": [{"_addr_": "int"}, {"_attr_": "реаl"}]})  # Cyrillic characters

    def test_block_whitespace_in_attributes(self) -> None:
        """Test that attributes with whitespace are blocked."""
        with pytest.raises(SecurityError, match="Invalid attribute"):
            instantiate({"_obj_": [{"_addr_": "int"}, {"_attr_": " real"}]})

        with pytest.raises(SecurityError, match="Invalid attribute"):
            instantiate({"_obj_": [{"_addr_": "int"}, {"_attr_": "real "}]})

        with pytest.raises(SecurityError, match="Invalid attribute"):
            instantiate({"_obj_": [{"_addr_": "int"}, {"_attr_": "re al"}]})

    def test_normal_attributes_allowed(self) -> None:
        """Test that normal attributes still work."""
        result = instantiate({"_obj_": [{"_addr_": "int"}, {"_attr_": "real"}]})
        assert result == int.real


class MockTime:
    """Mock time.time to simulate elapsed time."""

    def __init__(self, times: int, original_time: Callable[[], float]) -> None:
        """Initialize the mock time."""
        self.calls = 0
        self.times = times
        self.original_time = original_time

    def __call__(self) -> float:
        """Return simulated time."""
        self.calls += 1
        if self.calls < self.times:
            return self.original_time()
        else:
            return self.original_time() + 31  # Exceed MAX_INSTANTIATION_TIME (30s)


class TestTimeoutProtection:
    """Test timeout protection for instantiation."""

    def test_instantiate_respects_timeout(self) -> None:
        """Test that instantiate enforces timeout limit."""
        # Create a configuration that will take longer than allowed by mocking time to simulate elapsed time
        with patch("structcast.core.instantiator.time", side_effect=MockTime(2, time.time)):
            with pytest.raises(InstantiationError, match="Maximum instantiation time exceeded"):
                instantiate({"a": 1, "b": 2, "c": 3})

    def test_instantiate_timeout_propagates_through_nested_calls(self) -> None:
        """Test that timeout is checked in nested instantiation."""
        with patch("structcast.core.instantiator.time", side_effect=MockTime(3, time.time)):
            with pytest.raises(InstantiationError, match="Maximum instantiation time exceeded"):
                instantiate({"outer": {"inner": {"deep": {"value": 42}}}})


class TestErrorMessageSanitization:
    """Test that error messages don't leak sensitive information."""

    def test_attribute_error_doesnt_expose_object_repr(self) -> None:
        """Test that attribute errors don't expose object representation."""
        cfg = {"_obj_": [{"_addr_": "int"}, {"_attr_": "nonexistent"}]}
        with pytest.raises(InstantiationError) as exc_info:
            instantiate(cfg)
        # Should mention type but not repr of object
        assert "type" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)
        # Should not contain actual repr like "<class 'int'>"
        assert "<class" not in str(exc_info.value)

    def test_call_error_doesnt_expose_object_repr(self) -> None:
        """Test that call errors don't expose object representation."""
        # int() is callable so this won't fail - use str instead which returns an instance
        cfg = {"_obj_": [{"_addr_": "str"}, {"_call_": {}}, {"_call_": {}}]}
        with pytest.raises(InstantiationError) as exc_info:
            instantiate(cfg)
        # Should mention it's not callable without exposing internals
        assert "not callable" in str(exc_info.value)
        assert "str" in str(exc_info.value)
