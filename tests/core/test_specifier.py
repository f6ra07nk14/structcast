"""Tests for specifier module."""

from typing import Any

import pytest

from structcast.core.constants import SPEC_SOURCE
from structcast.core.exceptions import SpecError
from structcast.core.specifier import SPEC_CONSTANT, SpecIntermediate, access, convert_spec


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
