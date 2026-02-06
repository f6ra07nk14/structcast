"""Tests for specifier module."""

from typing import Any

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
    access,
    convert_spec,
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
        (123, SPEC_CONSTANT, 123),
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


def test_access() -> None:
    """Test access."""
    data = {"a": [{"b": [{"c": 1}]}]}
    assert access(data, ["a", 0, "b", 0, "c"]) == 1
    assert access(data, ["a", 1]) is None
    assert access(data, ["a", "a"]) is None


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
        assert RawSpec.model_validate(RawSpec.model_validate("a.b.c")).raw == "a.b.c"

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
        assert spec2.pattern == spec1.pattern

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
        spec = FlexSpec.model_validate({"_obj_": [{"_addr_": "list"}]})
        assert isinstance(spec.structure, ObjectSpec)

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
        spec = FlexSpec(**{"_spec_": "a.b.c"})
        assert isinstance(spec.structure, RawSpec)

    def test_flexspec_construct_rawspec(self) -> None:
        """Test FlexSpec construction with RawSpec."""
        data = {"a": {"b": {"c": 123}}}
        spec = FlexSpec.model_validate("a.b.c")
        result = spec(data)
        assert result == 123

    def test_flexspec_construct_objectspec(self) -> None:
        """Test FlexSpec construction with ObjectSpec."""
        spec = FlexSpec.model_validate({"_obj_": [{"_addr_": "list"}]})
        result = spec({})
        assert result is list

    def test_flexspec_construct_dict(self) -> None:
        """Test FlexSpec construction with dict structure."""
        data = {"a": {"b": 1}, "x": {"y": 2}}
        spec = FlexSpec.model_validate({"first": "a.b", "second": "x.y"})
        result = spec(data)
        assert result == {"first": 1, "second": 2}

    def test_flexspec_construct_list(self) -> None:
        """Test FlexSpec construction with list structure."""
        data = {"a": 1, "b": 2, "c": 3}
        spec = FlexSpec.model_validate(["a", "b", "c"])
        result = spec(data)
        assert result == [1, 2, 3]

    def test_flexspec_construct_nested_dict(self) -> None:
        """Test FlexSpec construction with nested dict structure."""
        data = {"a": {"b": 1}, "x": {"y": 2}, "z": 3}
        spec = FlexSpec.model_validate({"nested": {"first": "a.b", "second": "x.y"}, "direct": "z"})
        result = spec(data)
        assert result == {"nested": {"first": 1, "second": 2}, "direct": 3}

    def test_flexspec_construct_nested_list(self) -> None:
        """Test FlexSpec construction with nested list structure."""
        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        spec = FlexSpec.model_validate([["a", "b"], ["c", "d"]])
        result = spec(data)
        assert result == [[1, 2], [3, 4]]

    def test_flexspec_construct_mixed(self) -> None:
        """Test FlexSpec construction with mixed dict and list."""
        data = {"a": 1, "b": 2, "c": 3}
        spec = FlexSpec.model_validate({"values": ["a", "b", "c"]})
        result = spec(data)
        assert result == {"values": [1, 2, 3]}

    def test_flexspec_construct_with_constant(self) -> None:
        """Test FlexSpec construction with constant values."""
        data = {"a": 1}
        spec = FlexSpec.model_validate({"dynamic": "a", "static": "constant: fixed"})
        result = spec(data)
        assert result == {"dynamic": 1, "static": "fixed"}

    def test_flexspec_construct_objectspec_in_dict(self) -> None:
        """Test FlexSpec construction with ObjectSpec inside dict."""
        spec = FlexSpec.model_validate({"cls": {"_obj_": [{"_addr_": "list"}]}})
        result = spec({})
        assert result == {"cls": list}

    def test_flexspec_spec_property_rawspec(self) -> None:
        """Test FlexSpec spec property with RawSpec."""
        spec = FlexSpec.model_validate("a.b.c")
        assert isinstance(spec.spec, SpecIntermediate)

    def test_flexspec_spec_property_dict(self) -> None:
        """Test FlexSpec spec property with dict."""
        spec = FlexSpec.model_validate({"a": "x.y", "b": "p.q"})
        assert isinstance(spec.spec, dict)
        print(spec.spec)
        assert all(isinstance(v, SpecIntermediate) for v in spec.spec.values())

    def test_flexspec_spec_property_list(self) -> None:
        """Test FlexSpec spec property with list."""
        spec = FlexSpec.model_validate(["a.b", "x.y"])
        assert isinstance(spec.spec, list)
        assert all(isinstance(v, SpecIntermediate) for v in spec.spec)

    def test_flexspec_serialization_rawspec(self) -> None:
        """Test FlexSpec serialization with RawSpec."""
        spec = FlexSpec.model_validate("a.b.c")
        serialized = spec.model_dump()
        assert serialized == "a.b.c"

    def test_flexspec_serialization_objectspec(self) -> None:
        """Test FlexSpec serialization with ObjectSpec."""
        spec = FlexSpec.model_validate({"_obj_": [{"_addr_": "list"}]})
        serialized = spec.model_dump()
        assert serialized == ["_obj_", ["_addr_", "list"]]

    def test_flexspec_serialization_dict(self) -> None:
        """Test FlexSpec serialization with dict."""
        spec = FlexSpec.model_validate({"a": "x.y", "b": "p.q"})
        serialized = spec.model_dump()
        assert serialized == {"a": "x.y", "b": "p.q"}

    def test_flexspec_serialization_list(self) -> None:
        """Test FlexSpec serialization with list."""
        spec = FlexSpec.model_validate(["a.b", "x.y"])
        serialized = spec.model_dump()
        assert serialized == ["a.b", "x.y"]

    def test_flexspec_validation_from_flexspec(self) -> None:
        """Test FlexSpec validation from another FlexSpec instance."""
        spec1 = FlexSpec.model_validate("a.b.c")
        spec2 = FlexSpec.model_validate(spec1)
        assert isinstance(spec2.structure, RawSpec)
        assert spec2.structure.raw == "a.b.c"

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

    def test_flexspec_empty_dict(self) -> None:
        """Test FlexSpec with empty dict."""
        spec = FlexSpec.model_validate({})
        result = spec({"a": 1})
        assert result == {}

    def test_flexspec_empty_list(self) -> None:
        """Test FlexSpec with empty list."""
        spec = FlexSpec.model_validate([])
        result = spec({"a": 1})
        assert result == []

    def test_flexspec_deeply_nested(self) -> None:
        """Test FlexSpec with deeply nested structure."""
        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        spec = FlexSpec.model_validate({"level1": {"level2": {"level3": ["a", "b"]}, "other": ["c", "d"]}})
        result = spec(data)
        assert result == {"level1": {"level2": {"level3": [1, 2]}, "other": [3, 4]}}

    def test_flexspec_construct_idempotent(self) -> None:
        """Test FlexSpec construction is consistent."""
        data = {"a": 1}
        spec = FlexSpec.model_validate("a")
        result1 = spec(data)
        result2 = spec(data)
        assert result1 == result2
        assert result1 == 1
