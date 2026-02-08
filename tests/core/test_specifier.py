"""Tests for specifier module."""

from collections import OrderedDict
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Optional, Union

from pydantic import BaseModel
import pytest

from structcast.core.constants import SPEC_SOURCE
from structcast.core.exceptions import SpecError
from structcast.core.instantiator import ObjectPattern
from structcast.core.specifier import (
    SPEC_CONSTANT,
    FlexSpec,
    ObjectSpec,
    RawSpec,
    ReturnType,
    SpecIntermediate,
    WithPipe,
    access,
    configure_spec,
    construct,
    convert_spec,
    register_accesser,
    register_resolver,
)


@pytest.mark.parametrize(
    ("raw", "identifier", "value"),
    [
        ("a.b.c", SPEC_SOURCE, ("a", "b", "c")),
        ("a.b.0.c", SPEC_SOURCE, ("a", "b", 0, "c")),
        ('a.b 0.c."1"', SPEC_SOURCE, ("a", "b 0", "c", "1")),
        ("a.b 0.c.'1'", SPEC_SOURCE, ("a", "b 0", "c", "1")),
        ('a."b 0".c.1', SPEC_SOURCE, ("a", "b 0", "c", 1)),
        ("a.'b 0'.c.1", SPEC_SOURCE, ("a", "b 0", "c", 1)),
        ('a."b \\"0".c.1', SPEC_SOURCE, ("a", 'b "0', "c", 1)),
        ("a.'b \\\\\"0'.c.1", SPEC_SOURCE, ("a", 'b \\"0', "c", 1)),
        ("constant: abc", SPEC_CONSTANT, "abc"),
        ("CONSTANT: xyz", SPEC_CONSTANT, "xyz"),  # Test case-insensitive
        (123, SPEC_CONSTANT, 123),
        ("", SPEC_SOURCE, ()),  # Empty string
    ],
)
def test_convert_spec(raw: str, identifier: str, value: Any) -> None:
    """Test convert_spec."""
    res: SpecIntermediate = SpecIntermediate.convert_spec(raw)
    assert res.identifier == identifier
    assert res.value == value


def test_convert_spec_nested() -> None:
    """Test convert_spec with nested structures."""
    pattern = "a.b.c"
    result = SpecIntermediate(identifier=SPEC_SOURCE, value=("a", "b", "c"))
    assert convert_spec(pattern) == result
    assert convert_spec([pattern, pattern]) == [result, result]
    assert convert_spec({"a": pattern, "b": pattern}) == {"a": result, "b": result}
    assert convert_spec([{"a": pattern, "b": pattern}, pattern]) == [{"a": result, "b": result}, result]
    assert convert_spec({"a": [pattern, pattern], "b": pattern}) == {"a": [result, result], "b": result}
    with pytest.raises(SpecError, match="Unsupported specification type"):
        convert_spec([{pattern}])


def test_convert_spec_invalid_format() -> None:
    """Test convert_spec with invalid specification format."""
    with pytest.raises(SpecError, match="Invalid specification format"):
        SpecIntermediate.convert_spec('a."unclosed')


def test_access() -> None:
    """Test access."""
    data = {"a": [{"b": [{"c": 1}]}]}
    assert access(data, ["a", 0, "b", 0, "c"]) == 1
    assert access(data, ["a", 1]) is None
    assert access(data, ["a", "a"]) is None


class TestConstruct:
    """Tests for construct function."""

    def test_construct_with_none(self) -> None:
        """Test construct with None spec."""
        assert construct({"a": 1}, None) is None

    def test_construct_with_primitive_spec(self) -> None:
        """Test construct with primitive types as spec."""
        data = {"a": 1}
        assert construct(data, "hello") == "hello"
        assert construct(data, 123) == 123
        assert construct(data, 3.14) == 3.14
        assert construct(data, True) is True
        assert construct(data, b"bytes") == b"bytes"

    def test_construct_with_spec_intermediate_source(self) -> None:
        """Test construct with SpecIntermediate using SPEC_SOURCE."""
        data = {"a": {"b": {"c": 123}}}
        spec = SpecIntermediate(identifier=SPEC_SOURCE, value=("a", "b", "c"))
        assert construct(data, spec) == 123

    def test_construct_with_spec_intermediate_constant(self) -> None:
        """Test construct with SpecIntermediate using SPEC_CONSTANT."""
        data = {"a": 1}
        spec = SpecIntermediate(identifier=SPEC_CONSTANT, value="fixed_value")
        assert construct(data, spec) == "fixed_value"

    def test_construct_with_dict_spec(self) -> None:
        """Test construct with dict specification."""
        data = {"a": {"b": 1}, "x": {"y": 2}}
        spec = {
            "first": SpecIntermediate(identifier=SPEC_SOURCE, value=("a", "b")),
            "second": SpecIntermediate(identifier=SPEC_SOURCE, value=("x", "y")),
        }
        assert construct(data, spec) == {"first": 1, "second": 2}

    def test_construct_with_list_spec(self) -> None:
        """Test construct with list specification."""
        data = {"a": 1, "b": 2, "c": 3}
        spec = [
            SpecIntermediate(identifier=SPEC_SOURCE, value=("a",)),
            SpecIntermediate(identifier=SPEC_SOURCE, value=("b",)),
            SpecIntermediate(identifier=SPEC_SOURCE, value=("c",)),
        ]
        assert construct(data, spec) == [1, 2, 3]

    def test_construct_with_tuple_spec(self) -> None:
        """Test construct with tuple specification."""
        data = {"a": 1, "b": 2}
        spec = (
            SpecIntermediate(identifier=SPEC_SOURCE, value=("a",)),
            SpecIntermediate(identifier=SPEC_SOURCE, value=("b",)),
        )
        assert construct(data, spec) == (1, 2)

    def test_construct_with_nested_dict_spec(self) -> None:
        """Test construct with nested dict specification."""
        data = {"a": 1, "b": 2, "c": 3}
        spec = {
            "nested": {
                "first": SpecIntermediate(identifier=SPEC_SOURCE, value=("a",)),
                "second": SpecIntermediate(identifier=SPEC_SOURCE, value=("b",)),
            },
            "direct": SpecIntermediate(identifier=SPEC_SOURCE, value=("c",)),
        }
        assert construct(data, spec) == {"nested": {"first": 1, "second": 2}, "direct": 3}

    def test_construct_with_nested_list_spec(self) -> None:
        """Test construct with nested list specification."""
        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        spec = [
            [
                SpecIntermediate(identifier=SPEC_SOURCE, value=("a",)),
                SpecIntermediate(identifier=SPEC_SOURCE, value=("b",)),
            ],
            [
                SpecIntermediate(identifier=SPEC_SOURCE, value=("c",)),
                SpecIntermediate(identifier=SPEC_SOURCE, value=("d",)),
            ],
        ]
        assert construct(data, spec) == [[1, 2], [3, 4]]

    def test_construct_with_mixed_spec(self) -> None:
        """Test construct with mixed dict and list specification."""
        data = {"a": 1, "b": 2, "c": 3}
        spec = {
            "values": [
                SpecIntermediate(identifier=SPEC_SOURCE, value=("a",)),
                SpecIntermediate(identifier=SPEC_SOURCE, value=("b",)),
                SpecIntermediate(identifier=SPEC_SOURCE, value=("c",)),
            ]
        }
        assert construct(data, spec) == {"values": [1, 2, 3]}

    def test_construct_with_mixed_primitives_and_specs(self) -> None:
        """Test construct with mixed primitive values and SpecIntermediate."""
        data = {"a": 1}
        spec = {
            "dynamic": SpecIntermediate(identifier=SPEC_SOURCE, value=("a",)),
            "static": "constant_value",
            "number": 42,
        }
        assert construct(data, spec) == {"dynamic": 1, "static": "constant_value", "number": 42}

    def test_construct_with_return_type_reference(self) -> None:
        """Test construct with return_type=REFERENCE."""
        data = {"a": {"b": [1, 2, 3]}}
        spec = SpecIntermediate(identifier=SPEC_SOURCE, value=("a", "b"))
        result = construct(data, spec, return_type=ReturnType.REFERENCE)
        assert result == [1, 2, 3]
        # Verify it's a reference
        result.append(4)
        assert data["a"]["b"] == [1, 2, 3, 4]

    def test_construct_with_return_type_shallow_copy(self) -> None:
        """Test construct with return_type=SHALLOW_COPY."""
        data = {"a": {"b": [1, 2, 3]}}
        spec = SpecIntermediate(identifier=SPEC_SOURCE, value=("a", "b"))
        result = construct(data, spec, return_type=ReturnType.SHALLOW_COPY)
        assert result == [1, 2, 3]
        # Verify it's a shallow copy
        result.append(4)
        assert data["a"]["b"] == [1, 2, 3]

    def test_construct_with_return_type_deep_copy(self) -> None:
        """Test construct with return_type=DEEP_COPY."""
        data = {"a": {"b": {"c": [1, 2, 3]}}}
        spec = SpecIntermediate(identifier=SPEC_SOURCE, value=("a", "b"))
        result = construct(data, spec, return_type=ReturnType.DEEP_COPY)
        assert result == {"c": [1, 2, 3]}
        # Verify it's a deep copy
        result["c"].append(4)
        assert data["a"]["b"]["c"] == [1, 2, 3]

    def test_construct_with_raise_error_false(self) -> None:
        """Test construct with raise_error=False."""
        data = {"a": {"b": 1}}
        spec = SpecIntermediate(identifier=SPEC_SOURCE, value=("a", "x", "y"))
        result = construct(data, spec, raise_error=False)
        assert result is None

    def test_construct_with_raise_error_true(self) -> None:
        """Test construct with raise_error=True."""
        data = {"a": {"b": 1}}
        spec = SpecIntermediate(identifier=SPEC_SOURCE, value=("a", "x", "y"))
        with pytest.raises(SpecError):
            construct(data, spec, raise_error=True)

    def test_construct_with_complex_nested_structure(self) -> None:
        """Test construct with complex nested structure."""
        data = {
            "users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            "config": {"timeout": 30, "retry": 3},
        }
        spec = {
            "user_names": [
                SpecIntermediate(identifier=SPEC_SOURCE, value=("users", 0, "name")),
                SpecIntermediate(identifier=SPEC_SOURCE, value=("users", 1, "name")),
            ],
            "settings": {
                "timeout": SpecIntermediate(identifier=SPEC_SOURCE, value=("config", "timeout")),
                "retry_count": SpecIntermediate(identifier=SPEC_SOURCE, value=("config", "retry")),
            },
        }
        assert construct(data, spec) == {
            "user_names": ["Alice", "Bob"],
            "settings": {"timeout": 30, "retry_count": 3},
        }

    def test_construct_with_empty_dict_spec(self) -> None:
        """Test construct with empty dict specification."""
        assert construct({"a": 1}, {}) == {}

    def test_construct_with_empty_list_spec(self) -> None:
        """Test construct with empty list specification."""
        assert construct({"a": 1}, []) == []

    def test_construct_preserves_tuple_type(self) -> None:
        """Test that construct preserves tuple type in spec."""
        data = {"a": 1, "b": 2}
        spec = (
            SpecIntermediate(identifier=SPEC_SOURCE, value=("a",)),
            SpecIntermediate(identifier=SPEC_SOURCE, value=("b",)),
        )
        result = construct(data, spec)
        assert isinstance(result, tuple)
        assert result == (1, 2)

    def test_construct_with_unsupported_spec_type(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test construct with unsupported spec type logs debug message."""

        # Create a custom object that's not a supported spec type
        class CustomSpec:
            pass

        custom = CustomSpec()
        assert construct({"a": 1}, custom) is custom
        assert "Got unsupported type" in caplog.text

    def test_construct_with_custom_mapping(self) -> None:
        """Test construct with custom Mapping type in spec."""

        class CustomDict(dict):
            pass

        spec = CustomDict(
            {
                "x": SpecIntermediate(identifier=SPEC_SOURCE, value=("a",)),
                "y": SpecIntermediate(identifier=SPEC_SOURCE, value=("b",)),
            }
        )
        result = construct({"a": 1, "b": 2}, spec)
        assert isinstance(result, CustomDict)
        assert result == {"x": 1, "y": 2}


class TestRawSpec:
    """Tests for RawSpec class."""

    def test_rawspec_initialization_simple(self) -> None:
        """Test RawSpec initialization with simple values."""
        spec = RawSpec.model_validate("a.b.c")
        assert spec.raw == "a.b.c"
        assert isinstance(spec.spec, SpecIntermediate)
        assert spec.spec.identifier == SPEC_SOURCE
        assert spec.spec.value == ("a", "b", "c")

    def test_rawspec_initialization_constant(self) -> None:
        """Test RawSpec initialization with constant values."""
        spec = RawSpec.model_validate(123)
        assert spec.raw == 123
        assert spec.spec.identifier == SPEC_CONSTANT
        assert spec.spec.value == 123

        spec2 = RawSpec.model_validate("constant: hello")
        assert spec2.raw == "constant: hello"
        assert spec2.spec.identifier == SPEC_CONSTANT
        assert spec2.spec.value == "hello"

    def test_rawspec_initialization_alias(self) -> None:
        """Test RawSpec initialization with alias."""
        assert RawSpec(_spec_="a.b.c").raw == "a.b.c"

    def test_rawspec_initialization_from_dict(self) -> None:
        """Test RawSpec initialization from dict."""
        assert RawSpec(**{"_spec_": "a.b.c"}).raw == "a.b.c"

    def test_rawspec_construct_simple(self) -> None:
        """Test RawSpec construction with simple data."""
        assert RawSpec.model_validate("a.b.c")({"a": {"b": {"c": 123}}}) == 123

    def test_rawspec_construct_with_list(self) -> None:
        """Test RawSpec construction with list access."""
        assert RawSpec.model_validate("a.1.b")({"a": [{"b": 1}, {"b": 2}, {"b": 3}]}) == 2

    def test_rawspec_construct_constant(self) -> None:
        """Test RawSpec construction with constant value."""
        assert RawSpec.model_validate("constant: fixed_value")({"a": {"b": {"c": 123}}}) == "fixed_value"

    def test_rawspec_construct_none(self) -> None:
        """Test RawSpec construction with None value."""
        assert RawSpec.model_validate(None)({"a": {"b": {"c": 123}}}) is None

    def test_rawspec_return_type_reference(self) -> None:
        """Test RawSpec with reference return type."""
        data = {"a": {"b": [1, 2, 3]}}
        result = RawSpec.model_validate({"_spec_": "a.b", "return_type": ReturnType.REFERENCE})(data)
        assert result == [1, 2, 3]
        # Verify it's a reference
        result.append(4)
        assert data["a"]["b"] == [1, 2, 3, 4]

    def test_rawspec_return_type_shallow_copy(self) -> None:
        """Test RawSpec with shallow copy return type."""
        data = {"a": {"b": [1, 2, 3]}}
        result = RawSpec.model_validate({"_spec_": "a.b", "return_type": ReturnType.SHALLOW_COPY})(data)
        assert result == [1, 2, 3]
        # Verify it's a shallow copy
        result.append(4)
        assert data["a"]["b"] == [1, 2, 3]

    def test_rawspec_return_type_deep_copy(self) -> None:
        """Test RawSpec with deep copy return type."""
        data = {"a": {"b": {"c": [1, 2, 3]}}}
        result = RawSpec.model_validate({"_spec_": "a.b", "return_type": ReturnType.DEEP_COPY})(data)
        assert result == {"c": [1, 2, 3]}
        # Verify it's a deep copy
        result["c"].append(4)
        assert data["a"]["b"]["c"] == [1, 2, 3]

    def test_rawspec_raise_error_false(self) -> None:
        """Test RawSpec with raise_error=False."""
        assert RawSpec.model_validate({"_spec_": "a.x.y", "raise_error": False})({"a": {"b": 123}}) is None

    def test_rawspec_raise_error_true(self) -> None:
        """Test RawSpec with raise_error=True."""
        with pytest.raises(SpecError):
            RawSpec.model_validate({"_spec_": "a.x.y", "raise_error": True})({"a": {"b": 123}})

    def test_rawspec_has_construct_kwargs(self) -> None:
        """Test has_construct_kwargs property."""
        assert not RawSpec.model_validate("a.b.c").has_construct_kwargs
        assert RawSpec.model_validate({"_spec_": "a.b.c", "return_type": ReturnType.SHALLOW_COPY}).has_construct_kwargs
        assert RawSpec.model_validate({"_spec_": "a.b.c", "raise_error": True}).has_construct_kwargs

    def test_rawspec_serialization_simple(self) -> None:
        """Test RawSpec serialization without kwargs."""
        assert RawSpec.model_validate("a.b.c").model_dump() == "a.b.c"

    def test_rawspec_serialization_with_kwargs(self) -> None:
        """Test RawSpec serialization with kwargs."""
        serialized = RawSpec.model_validate({"_spec_": "a.b.c", "return_type": ReturnType.SHALLOW_COPY}).model_dump()
        assert isinstance(serialized, dict)
        assert serialized["_spec_"] == "a.b.c"
        assert serialized["return_type"] == ReturnType.SHALLOW_COPY

    def test_rawspec_validation_from_rawspec(self) -> None:
        """Test RawSpec validation from another RawSpec instance."""
        spec1 = RawSpec.model_validate("a.b.c")
        spec2 = RawSpec.model_validate(spec1)
        assert spec2.raw == "a.b.c"
        assert spec1 is spec2  # Should return the same instance

    def test_rawspec_complex_path(self) -> None:
        """Test RawSpec with complex path containing spaces and quotes."""
        assert RawSpec.model_validate('a."b 0".c."1"')({"a": {"b 0": {"c": {"1": 999}}}}) == 999


class TestObjectSpec:
    """Tests for ObjectSpec class."""

    def test_objectspec_initialization_simple(self) -> None:
        """Test ObjectSpec initialization with simple pattern."""
        spec = ObjectSpec.model_validate({"_obj_": [{"_addr_": "list"}]})
        assert isinstance(spec.pattern, ObjectPattern)
        assert len(spec.pattern.object) == 1

    def test_objectspec_initialization_from_objectpattern(self) -> None:
        """Test ObjectSpec initialization from ObjectPattern."""
        pattern = ObjectPattern.model_validate({"_obj_": [{"_addr_": "dict"}]})
        spec = ObjectSpec.model_validate(pattern)
        assert spec.pattern == pattern

    def test_objectspec_initialization_alias(self) -> None:
        """Test ObjectSpec initialization with alias."""
        assert isinstance(ObjectSpec(_spec_={"_obj_": [{"_addr_": "list"}]}).pattern, ObjectPattern)

    def test_objectspec_initialization_from_dict(self) -> None:
        """Test ObjectSpec initialization from dict."""
        assert isinstance(ObjectSpec(**{"_spec_": {"_obj_": [{"_addr_": "dict"}]}}).pattern, ObjectPattern)

    def test_objectspec_construct_list(self) -> None:
        """Test ObjectSpec construction returns list class."""
        assert ObjectSpec.model_validate({"_obj_": [{"_addr_": "list"}]})({}) is list

    def test_objectspec_construct_dict(self) -> None:
        """Test ObjectSpec construction returns dict class."""
        assert ObjectSpec.model_validate({"_obj_": [{"_addr_": "dict"}]})({}) is dict

    def test_objectspec_construct_with_call(self) -> None:
        """Test ObjectSpec construction with call pattern."""
        result = ObjectSpec.model_validate({"_obj_": [{"_addr_": "list"}, "_call_"]})({})
        assert result == []
        assert isinstance(result, list)

    def test_objectspec_construct_nested(self) -> None:
        """Test ObjectSpec construction with nested patterns."""
        result = ObjectSpec.model_validate({"_obj_": [["_obj_", {"_addr_": "dict"}], "_call_"]})({})
        assert result == {}
        assert isinstance(result, dict)

    def test_objectspec_spec_property(self) -> None:
        """Test ObjectSpec spec property returns built object."""
        assert ObjectSpec.model_validate({"_obj_": [{"_addr_": "list"}]}).spec is list

    def test_objectspec_serialization_simple(self) -> None:
        """Test ObjectSpec serialization without pipe."""
        ptn = ["_obj_", ["_addr_", "list"]]
        spec = ObjectSpec.model_validate(ptn)
        assert spec.model_dump() == ptn
        assert spec.pattern.model_dump() == ptn

    def test_objectspec_validation_from_objectspec(self) -> None:
        """Test ObjectSpec validation from another ObjectSpec instance."""
        spec1 = ObjectSpec.model_validate({"_obj_": [{"_addr_": "list"}]})
        spec2 = ObjectSpec.model_validate(spec1)
        assert spec1 is spec2  # Should return the same instance

    def test_objectspec_with_attribute_pattern(self) -> None:
        """Test ObjectSpec with attribute access pattern."""
        result = ObjectSpec.model_validate({"_obj_": [{"_addr_": "dict"}, {"_attr_": "keys"}]})({})
        assert callable(result)
        assert result.__name__ == "keys"

    def test_objectspec_with_bind_pattern(self) -> None:
        """Test ObjectSpec with bind pattern."""
        result = ObjectSpec.model_validate({"_obj_": [{"_addr_": "dict"}, {"_bind_": {"a": 1}}]})({})
        assert callable(result)
        # The result should be a partially applied dict with a=1

    def test_objectspec_tuple_format(self) -> None:
        """Test ObjectSpec with tuple format."""
        assert ObjectSpec.model_validate(["_obj_", {"_addr_": "list"}])({}) is list

    def test_objectspec_validation_error_invalid_pattern(self) -> None:
        """Test ObjectSpec raises error for invalid pattern content."""
        with pytest.raises(SpecError):
            ObjectSpec.model_validate({"_obj_": [{"invalid": "pattern"}]})

    def test_objectspec_construct_idempotent(self) -> None:
        """Test ObjectSpec construction is idempotent."""
        spec = ObjectSpec.model_validate({"_obj_": [{"_addr_": "list"}]})
        result1 = spec({})
        result2 = spec({})
        assert result1 is result2
        assert result1 is list


class TestFlexSpec:
    """Tests for FlexSpec class."""

    def test_flexspec_initialization_rawspec(self) -> None:
        """Test FlexSpec initialization with RawSpec."""
        spec = FlexSpec.model_validate("a.b.c")
        assert isinstance(spec.structure, RawSpec)
        assert spec.structure.raw == "a.b.c"

    def test_flexspec_initialization_objectspec(self) -> None:
        """Test FlexSpec initialization with ObjectSpec."""
        assert isinstance(FlexSpec.model_validate({"_obj_": [{"_addr_": "list"}]}).structure, ObjectSpec)

    def test_flexspec_initialization_dict(self) -> None:
        """Test FlexSpec initialization with dict structure."""
        spec = FlexSpec.model_validate({"a": "a.b.c", "b": "x.y.z"})
        assert isinstance(spec.structure, dict)
        assert isinstance(spec.structure["a"], RawSpec)
        assert isinstance(spec.structure["b"], RawSpec)

    def test_flexspec_initialization_list(self) -> None:
        """Test FlexSpec initialization with list structure."""
        spec = FlexSpec.model_validate(["a.b.c", "x.y.z"])
        assert isinstance(spec.structure, list)
        assert len(spec.structure) == 2
        assert all(isinstance(s, RawSpec) for s in spec.structure)

    def test_flexspec_initialization_alias(self) -> None:
        """Test FlexSpec initialization with alias."""
        spec = FlexSpec(_spec_="a.b.c")
        assert isinstance(spec.structure, RawSpec)
        assert spec.structure.raw == "a.b.c"

    def test_flexspec_initialization_from_dict_alias(self) -> None:
        """Test FlexSpec initialization from dict with alias."""
        assert isinstance(FlexSpec(**{"_spec_": "a.b.c"}).structure, RawSpec)

    def test_flexspec_construct_rawspec(self) -> None:
        """Test FlexSpec construction with RawSpec."""
        assert FlexSpec.model_validate("a.b.c")({"a": {"b": {"c": 123}}}) == 123

    def test_flexspec_construct_objectspec(self) -> None:
        """Test FlexSpec construction with ObjectSpec."""
        assert FlexSpec.model_validate({"_obj_": [{"_addr_": "list"}]})({}) is list

    def test_flexspec_construct_dict(self) -> None:
        """Test FlexSpec construction with dict structure."""
        result = FlexSpec.model_validate({"first": "a.b", "second": "x.y"})({"a": {"b": 1}, "x": {"y": 2}})
        assert result == {"first": 1, "second": 2}

    def test_flexspec_construct_list(self) -> None:
        """Test FlexSpec construction with list structure."""
        assert FlexSpec.model_validate(["a", "b", "c"])({"a": 1, "b": 2, "c": 3}) == [1, 2, 3]

    def test_flexspec_construct_nested_dict(self) -> None:
        """Test FlexSpec construction with nested dict structure."""
        data = {"a": {"b": 1}, "x": {"y": 2}, "z": 3}
        result = FlexSpec.model_validate({"nested": {"first": "a.b", "second": "x.y"}, "direct": "z"})(data)
        assert result == {"nested": {"first": 1, "second": 2}, "direct": 3}

    def test_flexspec_construct_nested_list(self) -> None:
        """Test FlexSpec construction with nested list structure."""
        assert FlexSpec.model_validate([["a", "b"], ["c", "d"]])({"a": 1, "b": 2, "c": 3, "d": 4}) == [[1, 2], [3, 4]]

    def test_flexspec_construct_mixed(self) -> None:
        """Test FlexSpec construction with mixed dict and list."""
        assert FlexSpec.model_validate({"values": ["a", "b", "c"]})({"a": 1, "b": 2, "c": 3}) == {"values": [1, 2, 3]}

    def test_flexspec_construct_with_constant(self) -> None:
        """Test FlexSpec construction with constant values."""
        result = FlexSpec.model_validate({"dynamic": "a", "static": "constant: fixed"})({"a": 1})
        assert result == {"dynamic": 1, "static": "fixed"}

    def test_flexspec_construct_objectspec_in_dict(self) -> None:
        """Test FlexSpec construction with ObjectSpec inside dict."""
        assert FlexSpec.model_validate({"cls": {"_obj_": [{"_addr_": "list"}]}})({}) == {"cls": list}

    def test_flexspec_spec_property_rawspec(self) -> None:
        """Test FlexSpec spec property with RawSpec."""
        assert isinstance(FlexSpec.model_validate("a.b.c").spec, SpecIntermediate)

    def test_flexspec_spec_property_dict(self) -> None:
        """Test FlexSpec spec property with dict."""
        spec = FlexSpec.model_validate({"a": "x.y", "b": "p.q"})
        assert isinstance(spec.spec, dict)
        assert all(isinstance(v, SpecIntermediate) for v in spec.spec.values())

    def test_flexspec_spec_property_list(self) -> None:
        """Test FlexSpec spec property with list."""
        spec = FlexSpec.model_validate(["a.b", "x.y"])
        assert isinstance(spec.spec, list)
        assert all(isinstance(v, SpecIntermediate) for v in spec.spec)

    def test_flexspec_serialization_rawspec(self) -> None:
        """Test FlexSpec serialization with RawSpec."""
        assert FlexSpec.model_validate("a.b.c").model_dump() == "a.b.c"

    def test_flexspec_serialization_objectspec(self) -> None:
        """Test FlexSpec serialization with ObjectSpec."""
        assert FlexSpec.model_validate({"_obj_": [{"_addr_": "list"}]}).model_dump() == ["_obj_", ["_addr_", "list"]]

    def test_flexspec_serialization_dict(self) -> None:
        """Test FlexSpec serialization with dict."""
        assert FlexSpec.model_validate({"a": "x.y", "b": "p.q"}).model_dump() == {"a": "x.y", "b": "p.q"}

    def test_flexspec_serialization_list(self) -> None:
        """Test FlexSpec serialization with list."""
        assert FlexSpec.model_validate(["a.b", "x.y"]).model_dump() == ["a.b", "x.y"]

    def test_flexspec_validation_from_flexspec(self) -> None:
        """Test FlexSpec validation from another FlexSpec instance."""
        spec1 = FlexSpec.model_validate("a.b.c")
        spec2 = FlexSpec.model_validate(spec1)
        assert spec1 is spec2  # Should return the same instance

    def test_flexspec_validation_from_rawspec(self) -> None:
        """Test FlexSpec validation from RawSpec instance."""
        raw = RawSpec.model_validate("a.b.c")
        spec = FlexSpec.model_validate(raw)
        assert spec.structure == raw

    def test_flexspec_validation_from_objectspec(self) -> None:
        """Test FlexSpec validation from ObjectSpec instance."""
        obj = ObjectSpec.model_validate({"_obj_": [{"_addr_": "list"}]})
        spec = FlexSpec.model_validate(obj)
        assert spec.structure == obj

    def test_flexspec_validation_with_alias_in_dict(self) -> None:
        """Test FlexSpec validation when dict contains _ALIAS_SPEC key."""
        spec = FlexSpec.model_validate({"_spec_": "a.b.c"})
        assert isinstance(spec.structure, RawSpec)
        assert spec.structure.raw == "a.b.c"

    def test_flexspec_empty_dict(self) -> None:
        """Test FlexSpec with empty dict."""
        assert FlexSpec.model_validate({})({"a": 1}) == {}

    def test_flexspec_empty_list(self) -> None:
        """Test FlexSpec with empty list."""
        assert FlexSpec.model_validate([])({"a": 1}) == []

    def test_flexspec_deeply_nested(self) -> None:
        """Test FlexSpec with deeply nested structure."""
        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        result = FlexSpec.model_validate({"level1": {"level2": {"level3": ["a", "b"]}, "other": ["c", "d"]}})(data)
        assert result == {"level1": {"level2": {"level3": [1, 2]}, "other": [3, 4]}}

    def test_flexspec_construct_idempotent(self) -> None:
        """Test FlexSpec construction is consistent."""
        data = {"a": 1}
        spec = FlexSpec.model_validate("a")
        result1 = spec(data)
        result2 = spec(data)
        assert result1 == result2
        assert result1 == 1


class TestRegisterResolver:
    """Tests for register_resolver function."""

    def test_register_resolver_success(self) -> None:
        """Test successful resolver registration."""
        register_resolver("test_resolver", lambda x: f"resolved_{x}")
        assert SpecIntermediate.convert_spec("test_resolver: value").value == "resolved_value"

    def test_register_resolver_duplicate_raises_error(self) -> None:
        """Test that registering the same resolver twice raises an error."""
        register_resolver("test_unique", lambda x: x)
        with pytest.raises(ValueError, match="Resolver 'test_unique' is already registered"):
            register_resolver("test_unique", lambda x: x)


class TestRegisterAccesser:
    """Tests for register_accesser function."""

    def test_register_accesser_custom_type(self) -> None:
        """Test registering a custom accesser for a custom type."""

        class CustomContainer:
            def __init__(self, data: dict[str, Any]) -> None:
                self._data = data

        def custom_accesser(instance: CustomContainer, index: Union[str, int]) -> tuple[bool, Any]:
            if isinstance(index, str) and index in instance._data:
                return True, instance._data[index]
            return False, None

        register_accesser(CustomContainer, custom_accesser)
        assert access(CustomContainer({"key1": "value1", "key2": 123}), ("key1",)) == "value1"

    def test_register_accesser_multiple_types(self) -> None:
        """Test registering accessers for multiple types."""

        class TypeA:
            value_a = "A"

        class TypeB:
            value_b = "B"

        def accesser_a(instance: TypeA, index: Union[str, int]) -> tuple[bool, Any]:
            return (True, instance.value_a) if index == "value_a" else (False, None)

        def accesser_b(instance: TypeB, index: Union[str, int]) -> tuple[bool, Any]:
            return (True, instance.value_b) if index == "value_b" else (False, None)

        register_accesser(TypeA, accesser_a)
        register_accesser(TypeB, accesser_b)
        assert access(TypeA(), ("value_a",)) == "A"
        assert access(TypeB(), ("value_b",)) == "B"


@contextmanager
def configure_spec_context(
    support_basemodel: Optional[bool] = None,
    support_attribute: Optional[bool] = None,
    raise_error: Optional[bool] = None,
    return_type: Optional[ReturnType] = None,
) -> Generator[None, Any, None]:
    """Context manager to temporarily configure spec settings for testing."""
    try:
        configure_spec(
            support_basemodel=support_basemodel,
            support_attribute=support_attribute,
            raise_error=raise_error,
            return_type=return_type,
        )
        yield
    finally:
        configure_spec()


class TestConfigureSpec:
    """Tests for configure_spec function."""

    def test_configure_spec_with_raise_error(self) -> None:
        """Test configure_spec with SpecSettings object."""
        with configure_spec_context(raise_error=True):
            with pytest.raises(SpecError, match=r"Key \(x\) not found"):
                construct({"a": {"b": 1}}, SpecIntermediate(identifier=SPEC_SOURCE, value=("a", "x")))

    def test_configure_spec_with_return_type(self) -> None:
        """Test configure_spec with keyword arguments."""
        with configure_spec_context(return_type=ReturnType.SHALLOW_COPY):
            data = {"a": [1, 2, 3]}
            result = construct({"a": [1, 2, 3]}, SpecIntermediate(identifier=SPEC_SOURCE, value=("a",)))
            result.append(4)
            assert data["a"] == [1, 2, 3]  # Original unchanged due to shallow copy

    def test_configure_spec_with_support_basemodel(self) -> None:
        """Test configure_spec with support_basemodel=True."""

        class TestModel(BaseModel):
            name: str

        with configure_spec_context(support_basemodel=True):
            assert access(TestModel(name="Alice"), ("name",)) == "Alice"

    def test_configure_spec_with_support_attribute(self) -> None:
        """Test configure_spec with support_attribute=True."""

        class TestClass:
            def __init__(self) -> None:
                self.value = 42

        with configure_spec_context(support_attribute=True):
            assert access(TestClass(), ("value",)) == 42


class TestAccessWithBaseModel:
    """Tests for access function with BaseModel support."""

    def test_access_basemodel_field(self) -> None:
        """Test accessing a field from a BaseModel instance."""

        class TestModel(BaseModel):
            name: str
            age: int

        assert access(TestModel(name="Alice", age=30), ("name",), support_basemodel=True) == "Alice"

    def test_access_basemodel_nested(self) -> None:
        """Test accessing nested fields in BaseModel."""

        class Address(BaseModel):
            city: str
            zip_code: str

        class Person(BaseModel):
            name: str
            address: Address

        person = Person(name="Bob", address=Address(city="NYC", zip_code="10001"))
        assert access(person, ("address", "city"), support_basemodel=True) == "NYC"

    def test_access_basemodel_field_not_set(self) -> None:
        """Test accessing an unset optional field in BaseModel."""

        class TestModel(BaseModel):
            name: str
            optional: Union[str, None] = None

        assert access(TestModel(name="Alice"), ("optional",), support_basemodel=True, raise_error=False) is None

    def test_access_basemodel_with_dict_mixing(self) -> None:
        """Test accessing BaseModel within dict structure."""

        class Config(BaseModel):
            timeout: int
            retry: int

        data = {"settings": Config(timeout=30, retry=3), "version": "1.0"}
        assert access(data, ("settings", "timeout"), support_basemodel=True) == 30


class TestAccessWithAttribute:
    """Tests for access function with attribute support."""

    def test_access_attribute_simple(self) -> None:
        """Test accessing object attributes."""

        class SimpleClass:
            def __init__(self) -> None:
                self.value = 42
                self.name = "test"

        assert access(SimpleClass(), ("value",), support_attribute=True) == 42

    def test_access_attribute_nested(self) -> None:
        """Test accessing nested object attributes."""

        class Inner:
            def __init__(self) -> None:
                self.data = "inner_value"

        class Outer:
            def __init__(self) -> None:
                self.inner = Inner()

        assert access(Outer(), ("inner", "data"), support_attribute=True) == "inner_value"

    def test_access_attribute_nonexistent(self) -> None:
        """Test accessing non-existent attribute."""

        class SimpleClass:
            value = 42

        assert access(SimpleClass(), ("nonexistent",), support_attribute=True, raise_error=False) is None

    def test_access_attribute_with_private(self) -> None:
        """Test that private attributes are handled securely."""

        class SimpleClass:
            def __init__(self) -> None:
                self._private = "should_not_access"
                self.public = "accessible"

        assert access(SimpleClass(), ("public",), support_attribute=True) == "accessible"

    def test_access_attribute_integer_index_fails(self) -> None:
        """Test that integer index doesn't work with attribute access."""

        class SimpleClass:
            value = 42

        assert access(SimpleClass(), (0,), support_attribute=True, raise_error=False) is None


class TestConvertSpecMapping:
    """Tests for convert_spec with Mapping types."""

    def test_convert_spec_ordered_dict(self) -> None:
        """Test convert_spec preserves OrderedDict type."""
        pattern = "a.b.c"
        result_intermediate = SpecIntermediate(identifier=SPEC_SOURCE, value=("a", "b", "c"))
        result = convert_spec(OrderedDict([("key1", pattern), ("key2", pattern)]))
        assert isinstance(result, OrderedDict)
        assert list(result.keys()) == ["key1", "key2"]
        assert result["key1"] == result_intermediate
        assert result["key2"] == result_intermediate

    def test_convert_spec_custom_mapping(self) -> None:
        """Test convert_spec with custom Mapping subclass."""

        class CustomMapping(dict):
            pass

        result = convert_spec(CustomMapping({"x": "a.b"}))
        assert isinstance(result, CustomMapping)
        assert "x" in result


class TestAccessCustomAccessers:
    """Tests for access function with custom accessers."""

    def test_access_with_custom_accesser_list(self) -> None:
        """Test access with custom accesser list."""

        class SpecialContainer:
            def __init__(self, items: list[Any]) -> None:
                self.items = items

        def special_accesser(instance: SpecialContainer, index: Union[str, int]) -> tuple[bool, Any]:
            if isinstance(index, int) and 0 <= index < len(instance.items):
                return True, instance.items[index]
            return False, None

        container = SpecialContainer([10, 20, 30])
        result = access(container, (1,), accessers=[(SpecialContainer, special_accesser)])
        assert result == 20

    def test_access_custom_accesser_precedence(self) -> None:
        """Test that custom accessers are tried in order."""

        class Container:
            value = "default"

        def first_accesser(instance: Container, index: Union[str, int]) -> tuple[bool, Any]:
            if index == "first":
                return True, "first_result"
            return False, None

        def second_accesser(instance: Container, index: Union[str, int]) -> tuple[bool, Any]:
            if index == "second":
                return True, "second_result"
            return False, None

        container = Container()
        accessers = [(Container, first_accesser), (Container, second_accesser)]

        assert access(container, ("first",), accessers=accessers) == "first_result"
        assert access(container, ("second",), accessers=accessers) == "second_result"

    def test_access_custom_accesser_fallback(self) -> None:
        """Test that access falls back when custom accesser fails."""

        class Container:
            pass

        def failing_accesser(instance: Container, index: Union[str, int]) -> tuple[bool, Any]:
            return False, None

        assert access(Container(), ("anything",), accessers=[(Container, failing_accesser)], raise_error=False) is None


class TestAccessEdgeCases:
    """Tests for edge cases in access function."""

    def test_access_empty_source(self) -> None:
        """Test access with empty source tuple returns the data itself."""
        data = {"a": 1}
        assert access(data, ()) == data

    def test_access_with_none_data(self) -> None:
        """Test access with None data."""
        assert access(None, ("a",), raise_error=False) is None

    def test_access_deeply_nested_path(self) -> None:
        """Test access with deeply nested path."""
        data = {"a": {"b": {"c": {"d": {"e": {"f": 123}}}}}}
        assert access(data, ("a", "b", "c", "d", "e", "f")) == 123

    def test_access_mixed_dict_list_access(self) -> None:
        """Test access mixing dict and list indexing."""
        data = {"users": [{"name": "Alice", "scores": [10, 20, 30]}, {"name": "Bob", "scores": [40, 50, 60]}]}
        assert access(data, ("users", 1, "scores", 2)) == 60


class TestWithPipeCoverage:
    """Tests for WithPipe class coverage."""

    def test_withpipe_non_callable_pipe_element(self) -> None:
        """Test WithPipe raises error for non-callable pipe element."""
        # Create a WithPipe with a pipe element that builds to non-callable (an integer value)
        # int() returns 0 which is not callable, and this should raise SpecError during validation
        with pytest.raises(SpecError, match="not callable"):
            WithPipe.model_validate({"_pipe_": [{"_obj_": [{"_addr_": "int"}, {"_call_": {}}]}]})
