"""Tests for base utility functions."""

import json
from pathlib import Path
import uuid

from structcast.utils.base import (
    check_elements,
    dump_yaml,
    dump_yaml_to_string,
    import_from_address,
    load_yaml,
    load_yaml_from_string,
)


class TestCheckElements:
    """Test check_elements function."""

    def test_none_returns_empty_list(self) -> None:
        """Test that None returns an empty list."""
        assert check_elements(None) == []

    def test_single_string_returns_list(self) -> None:
        """Test that a single string returns a list with that string."""
        assert check_elements("abc") == ["abc"]

    def test_tuple_returns_list(self) -> None:
        """Test that a tuple returns a list."""
        assert check_elements(("abc", "def")) == ["abc", "def"]

    def test_set_returns_list(self) -> None:
        """Test that a set returns a list."""
        result = check_elements({"abc", "def"})
        assert isinstance(result, list)
        assert len(result) == 2
        assert "abc" in result
        assert "def" in result

    def test_list_returns_same_list(self) -> None:
        """Test that a list returns the same list."""
        elements = ["abc", "def"]
        assert check_elements(elements) == elements

    def test_single_element_returns_list(self) -> None:
        """Test that a single element returns a list with that element."""
        assert check_elements(42) == [42]


class TestImportFromAddress:
    """Test import_from_address function."""

    def test_import_builtin_class(self) -> None:
        """Test importing a built-in class."""
        assert import_from_address("dict") is dict

    def test_import_from_module(self) -> None:
        """Test importing from a module."""
        assert import_from_address("json.dumps") is json.dumps


class TestLoadYaml:
    """Test load_yaml function."""

    def test_load_yaml_from_file(self) -> None:
        """Test loading yaml from a file."""
        # Use a file in the current directory (allowed by security settings)
        test_file = Path(f"test_temp_{uuid.uuid4()}.yml")
        try:
            test_file.write_text("key: value\nlist:\n  - item1\n  - item2\n")
            result = load_yaml(test_file)
            assert result == {"key": "value", "list": ["item1", "item2"]}
        finally:
            if test_file.exists():
                test_file.unlink()


class TestLoadYamlFromString:
    """Test load_yaml_from_string function."""

    def test_load_yaml_from_string(self) -> None:
        """Test loading yaml from a string."""
        result = load_yaml_from_string("key: value\nlist:\n  - item1\n  - item2\n")
        assert result == {"key": "value", "list": ["item1", "item2"]}

    def test_load_empty_yaml_string(self) -> None:
        """Test loading an empty yaml string."""
        assert load_yaml_from_string("") is None


class TestDumpYaml:
    """Test dump_yaml function."""

    def test_dump_yaml_to_file(self) -> None:
        """Test dumping yaml to a file."""
        data = {"key": "value", "list": ["item1", "item2"]}
        test_file = Path(f"test_dump_temp_{uuid.uuid4()}.yml")
        try:
            # Create the file first so security check can resolve it
            test_file.touch()
            dump_yaml(data, test_file)
            result = load_yaml(test_file)
            assert result == data
        finally:
            if test_file.exists():
                test_file.unlink()


class TestDumpYamlToString:
    """Test dump_yaml_to_string function."""

    def test_dump_yaml_to_string(self) -> None:
        """Test dumping yaml to a string."""
        data = {"key": "value", "list": ["item1", "item2"]}
        result = dump_yaml_to_string(data)
        assert isinstance(result, str)
        assert "key: value" in result
        assert "list:" in result
        assert "item1" in result
        assert "item2" in result

    def test_dump_empty_dict_to_string(self) -> None:
        """Test dumping an empty dict to a string."""
        result = dump_yaml_to_string({})
        assert isinstance(result, str)
        assert result.strip() == "{}"

    def test_dump_simple_value_to_string(self) -> None:
        """Test dumping a simple value to a string."""
        result = dump_yaml_to_string("simple_value")
        assert isinstance(result, str)
        assert "simple_value" in result
