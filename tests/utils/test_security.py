"""Tests for security features in import_from_address."""

import collections
from concurrent.futures import Future
from dataclasses import dataclass
from datetime import date, datetime
from io import StringIO
import math
import os
from pathlib import Path
from typing import Any, ClassVar

import pytest
from ruamel.yaml import YAML
from ruamel.yaml.constructor import ConstructorError

import structcast.utils.security as security_module
from structcast.utils.security import (
    SecurityError,
    check_path,
    configure_security,
    dump_yaml,
    get_security_settings,
    import_from_address,
    load_yaml,
    load_yaml_from_stream,
    register_dir,
    resolve_path,
    unregister_dir,
    validate_attribute,
)
from tests.utils import configure_security_context, temporary_registered_dir


@dataclass
class YAMLTestClass:
    """Test class for YAML constructor testing."""

    name: str
    value: int

    @classmethod
    def from_yaml(cls, constructor: Any, node: Any) -> "YAMLTestClass":
        """Construct from YAML node."""
        mapping = constructor.construct_mapping(node, deep=True)
        return cls(name=mapping["name"], value=mapping["value"])


@dataclass
class YAMLDumpDefaultTagClass:
    """Test class dumped with default YAML tag behavior."""

    value: str


@dataclass
class YAMLDumpCustomTagClass:
    """Test class dumped with custom yaml_tag behavior."""

    value: str
    yaml_tag: ClassVar[str] = "!custom.yaml.tag"


@dataclass
class YAMLDumpCustomToYamlClass:
    """Test class dumped with custom to_yaml representer."""

    value: str

    @staticmethod
    def to_yaml(representer: Any, data: Any) -> Any:
        """Serialize object to custom scalar."""
        return representer.represent_scalar("!custom.scalar", data.value)


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
        assert check_path(tmp_path) == tmp_path.resolve()

    def test_check_path_with_string_path(self, tmp_path: Path) -> None:
        """Test check_path with string path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        assert check_path(str(test_file)) == test_file.resolve()

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
        """Test check_path resolves paths inside hidden directories."""
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        test_file = hidden_dir / "test.txt"
        test_file.write_text("test")
        assert check_path(test_file) == test_file.resolve()

    def test_check_path_outside_working_directory(self, tmp_path: Path) -> None:
        """Test check_path resolves paths outside the working directory."""
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        test_file = outside_dir / "test.txt"
        test_file.write_text("test")
        assert check_path(test_file) == test_file.resolve()


class TestImportFromAddress:
    """Test import_from_address edge cases."""

    def test_import_with_default_module(self) -> None:
        """Test importing from a default module."""
        result = import_from_address("sqrt", default_module=math)
        assert result is math.sqrt

    def test_import_nonexistent_target(self) -> None:
        """Test importing non-existent target raises ImportError."""
        with pytest.raises(ImportError, match="not found"):
            import_from_address("nonexistent_function_xyz")

    def test_import_with_module_spec_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test import when module spec is None."""

        def mock_spec(*args: Any, **kwargs: Any) -> None:
            return None

        test_file = tmp_path / "test_module.py"
        test_file.write_text("value = 42")
        monkeypatch.setitem(import_from_address.__globals__, "spec_from_file_location", mock_spec)
        with pytest.raises(ImportError, match="Cannot load module"):
            import_from_address("value", module_file=test_file)


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
    """Test that dangerous dunder targets are blocked by default."""

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


class TestFileLoadingSecurity:
    """Test security improvements for file loading."""

    def test_block_non_python_files(self, tmp_path: Path) -> None:
        """Test that non-.py files are blocked."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("print('hello')")
        with pytest.raises(SecurityError, match="Module file must be a .py file"):
            import_from_address("test", module_file=txt_file)

    def test_resolve_absolute_paths(self, tmp_path: Path) -> None:
        """Test that paths are resolved to absolute paths."""
        py_file = tmp_path / "test_module.py"
        py_file.write_text("value = 42")
        assert import_from_address("value", module_file=py_file) == 42


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


def test_configure_security_with_settings_object() -> None:
    """Test configure_security with SecuritySettings object."""
    configure_security(
        dangerous_dunders={"__custom_dunder__"},
        ascii_check=False,
        protected_member_check=False,
        private_member_check=False,
    )
    res = get_security_settings()
    assert res.dangerous_dunders == {"__custom_dunder__"}
    assert not res.ascii_check
    assert not res.protected_member_check
    assert not res.private_member_check
    configure_security()


class TestDumpYaml:
    """Test dump_yaml functionality."""

    def test_dump_yaml_to_file(self, tmp_path: Path) -> None:
        """Test dumping YAML to a file."""
        yaml_file = tmp_path / "output.yaml"
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        with temporary_registered_dir(tmp_path):
            # Create file first
            yaml_file.touch()
            dump_yaml(data, yaml_file)
            assert load_yaml(yaml_file) == data

    def test_dump_yaml_to_stream(self) -> None:
        """Test dumping YAML to a stream."""
        stream = StringIO()
        dump_yaml({"test": "data"}, stream)
        content = stream.getvalue()
        assert "test" in content
        assert "data" in content

    def test_dump_yaml_with_nested_structures(self, tmp_path: Path) -> None:
        """Test dumping YAML with nested data structures."""
        yaml_file = tmp_path / "nested.yaml"
        data = {"nested": {"deep": {"value": 123}}, "list_of_dicts": [{"a": 1}, {"b": 2}]}
        with temporary_registered_dir(tmp_path):
            # Create file first
            yaml_file.touch()
            dump_yaml(data, yaml_file)
            assert load_yaml(yaml_file) == data

    def test_dump_yaml_with_various_types(self, tmp_path: Path) -> None:
        """Test dumping YAML with various data types."""
        yaml_file = tmp_path / "types.yaml"
        data = {
            "string": "hello",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "bytes": b"bytes",
            "date": date(2024, 1, 1),
            "datetime": datetime(2024, 1, 1, 12, 0, 0),
        }
        with temporary_registered_dir(tmp_path):
            # Create file first
            yaml_file.touch()
            dump_yaml(data, yaml_file)
            loaded = load_yaml(yaml_file)
            # Basic types should match
            assert loaded["string"] == data["string"]
            assert loaded["int"] == data["int"]
            assert loaded["bool"] == data["bool"]

    def test_dump_yaml_custom_object_uses_default_tag(self) -> None:
        """Test dump_yaml uses default module/class YAML tag for object types."""
        test_module = "tests.utils.test_security"
        stream = StringIO()
        dump_yaml({"obj": YAMLDumpDefaultTagClass("value")}, stream)
        assert f"!{test_module}.YAMLDumpDefaultTagClass" in stream.getvalue()

    def test_dump_yaml_custom_object_uses_yaml_tag_attribute(self) -> None:
        """Test dump_yaml uses yaml_tag when class defines it."""
        stream = StringIO()
        dump_yaml({"obj": YAMLDumpCustomTagClass("value")}, stream)
        assert "!custom.yaml.tag" in stream.getvalue()

    def test_dump_yaml_custom_object_uses_to_yaml_method(self) -> None:
        """Test dump_yaml uses class to_yaml method when provided."""
        stream = StringIO()
        dump_yaml({"obj": YAMLDumpCustomToYamlClass("serialized")}, stream)
        content = stream.getvalue()
        assert "!custom.scalar" in content
        assert "serialized" in content


def test_yaml_manager_load_representer_with_string_address() -> None:
    """Test load_representer string-address path builds the expected tag."""
    address = "tests.utils.test_security.YAMLDumpDefaultTagClass"
    manager = security_module.dump_yaml.__globals__["_YamlManager"]()
    manager.load_representer(None, {address})
    stream = StringIO()
    manager.instance.dump(YAMLDumpDefaultTagClass("value"), stream)
    assert f"!{address}" in stream.getvalue()


class TestValidateAttributeEdgeCases:
    """Test _validate_attribute internal function edge cases."""

    def test_validate_attribute_with_non_identifier_after_strip(self) -> None:
        """Test attribute that looks valid but isn't an identifier."""
        with pytest.raises(SecurityError, match="Numeric index access"):
            validate_attribute("123")  # Starts with digit - interpreted as numeric index

    def test_validate_attribute_with_non_ascii_when_disabled(self) -> None:
        """Test non-ASCII attributes when check is disabled."""
        # Should not raise when ascii_check is False
        validate_attribute("café", ascii_check=False)

    def test_validate_attribute_protected_when_disabled(self) -> None:
        """Test protected member access when check is disabled."""
        # Should not raise when protected_member_check is False
        validate_attribute("_protected", protected_member_check=False)

    def test_validate_attribute_private_when_disabled(self) -> None:
        """Test private member access when check is disabled."""
        # Should not raise when private_member_check is False
        validate_attribute("__private", private_member_check=False)


class TestYamlAddressConstructor:
    """Test that "!<address>" tags are resolved on demand, without registering the class first."""

    def test_round_trip_uses_from_yaml_without_configuration(self, tmp_path: Path) -> None:
        """Test a dumped object is reconstructed from its address tag with zero configuration."""
        yaml_file = tmp_path / "round_trip.yaml"
        yaml_file.touch()  # dump_yaml resolves the target path, so it has to exist first
        dump_yaml({"obj": YAMLTestClass(name="test_name", value=42)}, yaml_file)
        result = load_yaml(yaml_file)
        assert isinstance(result["obj"], YAMLTestClass)
        assert result["obj"].name == "test_name"
        assert result["obj"].value == 42

    def test_round_trip_without_from_yaml_uses_default_construction(self) -> None:
        """Test a class without from_yaml is reconstructed through the default object constructor."""
        stream = StringIO()
        dump_yaml({"obj": YAMLDumpDefaultTagClass("value")}, stream)
        result = load_yaml_from_stream(stream.getvalue())
        assert result["obj"] == YAMLDumpDefaultTagClass("value")

    def test_unknown_address_raises_import_error(self) -> None:
        """Test a tag whose address cannot be imported fails loudly instead of being ignored."""
        with pytest.raises(ImportError):
            load_yaml_from_stream("obj: !no.such.module.Cls {}\n")

    def test_registration_does_not_leak_into_foreign_yaml_instances(self) -> None:
        """Test address resolution stays inside structcast, since ruamel registers multi-constructors per class."""
        load_yaml_from_stream("obj: 1\n")  # ensure the constructor has been registered
        with pytest.raises(ConstructorError):
            YAML(typ="safe", pure=True).load("obj: !os.system {}\n")


class TestImportTargetValidation:
    """Test that import_from_address validates the target, treating the module path as trusted input."""

    def test_module_path_is_trusted(self) -> None:
        """Test module paths are no longer gated, since configuration is trusted input."""
        assert import_from_address("os.system") is os.system

    def test_module_path_with_underscore_part_is_allowed(self) -> None:
        """Test protected/private checks do not apply to module path parts."""
        assert import_from_address("concurrent.futures._base.Future") is Future

    def test_dangerous_dunder_target_is_blocked(self) -> None:
        """Test dangerous dunders remain blocked, as they escape the imported object."""
        with pytest.raises(SecurityError, match="__import__"):
            import_from_address("builtins.__import__")

    def test_protected_target_is_blocked_by_default(self) -> None:
        """Test the target is an attribute access, so protected members stay blocked unless opted out."""
        with pytest.raises(SecurityError, match="Protected member"):
            import_from_address("collections._count_elements")
        target = import_from_address("collections._count_elements", protected_member_check=False)
        assert target is collections._count_elements

    def test_protected_target_follows_global_settings(self) -> None:
        """Test target validation honours the globally configured checks, not just the keyword arguments."""
        with configure_security_context(protected_member_check=False):
            assert import_from_address("collections._count_elements") is collections._count_elements
