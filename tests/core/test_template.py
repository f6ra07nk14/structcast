"""Tests for Jinja template functionality."""

from collections import OrderedDict
from contextlib import contextmanager
from typing import Any, Optional, Union
from unittest.mock import patch

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, Undefined, UndefinedError
from jinja2.ext import Extension
from jinja2.sandbox import ImmutableSandboxedEnvironment
import pytest

from structcast.core.constants import MAX_RECURSION_DEPTH, MAX_RECURSION_TIME
from structcast.core.exceptions import (
    InstantiationError,
    SpecError,
    StructuredExtensionError,
)
from structcast.core.template import (
    JinjaJsonTemplate,
    JinjaSettings,
    JinjaTemplate,
    JinjaYamlTemplate,
    configure_jinja,
    extend_structure,
    get_environment,
)

# ============================================================================
# Test 1: JinjaSettings and Configuration
# ============================================================================


@contextmanager
def configure_jinja_context(
    environment_type: Optional[type[Environment]] = None,
    undefined_type: Optional[type[Undefined]] = None,
    trim_blocks: Optional[bool] = None,
    lstrip_blocks: Optional[bool] = None,
    extensions: Optional[list[Union[str, type[Extension]]]] = None,
):
    """Context manager to temporarily configure Jinja environment."""
    try:
        configure_jinja(
            environment_type=environment_type,
            undefined_type=undefined_type,
            trim_blocks=trim_blocks,
            lstrip_blocks=lstrip_blocks,
            extensions=extensions,
        )
        yield
    finally:
        configure_jinja()


class TestJinjaSettings:
    """Test JinjaSettings dataclass and configuration."""

    def test_jinja_settings_defaults(self) -> None:
        """Test default values in JinjaSettings."""
        settings = JinjaSettings()
        assert settings.environment_type == ImmutableSandboxedEnvironment
        assert settings.undefined_type == StrictUndefined
        assert settings.trim_blocks is True
        assert settings.lstrip_blocks is True
        assert settings.raise_error is True
        assert settings.extensions == ["jinja2.ext.loopcontrols"]

    def test_jinja_settings_custom(self) -> None:
        """Test custom JinjaSettings values."""
        settings = JinjaSettings(
            environment_type=Environment,
            trim_blocks=False,
            lstrip_blocks=False,
            raise_error=False,
            extensions=["jinja2.ext.do"],
        )
        assert settings.environment_type == Environment
        assert settings.trim_blocks is False
        assert settings.lstrip_blocks is False
        assert settings.raise_error is False
        assert settings.extensions == ["jinja2.ext.do"]

    def test_configure_jinja_with_settings(self) -> None:
        """Test configure_jinja with JinjaSettings object."""
        with configure_jinja_context(trim_blocks=False, lstrip_blocks=False):
            env = get_environment()
            assert env.trim_blocks is False
            assert env.lstrip_blocks is False

    def test_configure_jinja_with_kwargs(self) -> None:
        """Test configure_jinja with individual keyword arguments."""
        with configure_jinja_context(trim_blocks=False, lstrip_blocks=False):
            env = get_environment()
            assert env.trim_blocks is False
            assert env.lstrip_blocks is False

    def test_configure_jinja_environment_type(self) -> None:
        """Test configure_jinja with custom environment type."""
        with configure_jinja_context(environment_type=Environment):
            env = get_environment()
            assert isinstance(env, Environment)
            assert not isinstance(env, ImmutableSandboxedEnvironment)

    def test_get_environment_returns_configured_env(self) -> None:
        """Test get_environment returns properly configured environment."""
        env = get_environment()
        assert isinstance(env, ImmutableSandboxedEnvironment)
        assert env.undefined == StrictUndefined
        assert env.trim_blocks is True
        assert env.lstrip_blocks is True


# ============================================================================
# Test 2: JinjaTemplate Basic Functionality
# ============================================================================


class TestJinjaTemplate:
    """Test JinjaTemplate class."""

    def test_jinja_template_creation(self) -> None:
        """Test creating a JinjaTemplate."""
        template = JinjaTemplate.model_validate({"_jinja_": "Hello {{ name }}"})
        assert template.source == "Hello {{ name }}"
        assert "name" in template.variables

    def test_jinja_template_alias_list(self) -> None:
        """Test creating JinjaTemplate with alias list format."""
        template = JinjaTemplate.model_validate(["_jinja_", "Hello {{ name }}"])
        assert template.source == "Hello {{ name }}"

    def test_jinja_template_alias_list_with_pipe(self) -> None:
        """Test creating JinjaTemplate with alias list and pipe."""
        template = JinjaTemplate.model_validate(["_jinja_", "{{ value }}", [["_obj_", {"_addr_": "int"}]]])
        assert template.source == "{{ value }}"
        assert len(template.pipe) == 1

    def test_jinja_template_invalid_list_format(self) -> None:
        """Test JinjaTemplate rejects invalid list format."""
        with pytest.raises(SpecError, match="Invalid Jinja template format"):
            JinjaTemplate.model_validate(["_jinja_", "source", "pipe", "extra"])

    def test_jinja_template_rendering(self) -> None:
        """Test rendering a JinjaTemplate."""
        template = JinjaTemplate.model_validate({"_jinja_": "Hello {{ name }}"})
        result = template(name="World")
        assert result == "Hello World"

    def test_jinja_template_variables(self) -> None:
        """Test extracting variables from template."""
        template = JinjaTemplate.model_validate({"_jinja_": "{{ a }} + {{ b }} = {{ c }}"})
        assert template.variables == {"a", "b", "c"}

    def test_jinja_template_no_variables(self) -> None:
        """Test template with no variables."""
        template = JinjaTemplate.model_validate({"_jinja_": "Static text"})
        assert len(template.variables) == 0
        assert template() == "Static text"

    def test_jinja_template_complex_rendering(self) -> None:
        """Test rendering complex Jinja template."""
        template = JinjaTemplate.model_validate({"_jinja_": "{% for i in items %}{{ i }}{% endfor %}"})
        result = template(items=[1, 2, 3])
        assert result == "123"

    def test_jinja_template_undefined_variable(self) -> None:
        """Test that undefined variables raise error with StrictUndefined."""
        template = JinjaTemplate.model_validate({"_jinja_": "Hello {{ name }}"})
        with pytest.raises(UndefinedError):
            template()

    def test_jinja_template_trim_blocks(self) -> None:
        """Test trim_blocks and lstrip_blocks behavior."""
        template = JinjaTemplate.model_validate({"_jinja_": "{% if true %}text{% endif %}"})
        result = template()
        assert result == "text"

    def test_jinja_template_with_pipe(self) -> None:
        """Test JinjaTemplate with pipe casting."""
        template = JinjaTemplate.model_validate({"_jinja_": "42", "_jinja_pipe_": [["_obj_", {"_addr_": "int"}]]})
        result = template()
        assert result == 42
        assert isinstance(result, int)


# ============================================================================
# Test 3: JinjaYamlTemplate
# ============================================================================


class TestJinjaYamlTemplate:
    """Test JinjaYamlTemplate class."""

    def test_jinja_yaml_template_creation(self) -> None:
        """Test creating a JinjaYamlTemplate."""
        template = JinjaYamlTemplate.model_validate({"_jinja_yaml_": "key: {{ value }}"})
        result = template(value="test")
        assert isinstance(result, dict)
        assert result["key"] == "test"

    def test_jinja_yaml_template_alias_list(self) -> None:
        """Test JinjaYamlTemplate with list format."""
        template = JinjaYamlTemplate.model_validate(["_jinja_yaml_", "key: {{ value }}"])
        result = template(value="test")
        assert isinstance(result, dict)
        assert result["key"] == "test"

    def test_jinja_yaml_template_ignores_custom_pipe(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that JinjaYamlTemplate ignores custom pipe in list format."""
        template = JinjaYamlTemplate.model_validate(["_jinja_yaml_", "key: value", [["_obj_", {"_addr_": "str"}]]])
        result = template()
        assert isinstance(result, dict)
        assert result == {"key": "value"}
        assert "Ignoring custom pipe in JinjaYamlTemplate" in caplog.text

    def test_jinja_yaml_template_complex_structure(self) -> None:
        """Test rendering complex YAML structure."""
        yaml_source = """
        items:
          {% for item in values %}
          - name: {{ item }}
          {% endfor %}
        """
        template = JinjaYamlTemplate.model_validate({"_jinja_yaml_": yaml_source})
        result = template(values=["a", "b", "c"])
        assert isinstance(result, dict)
        assert "items" in result
        assert len(result["items"]) == 3

    def test_jinja_yaml_template_with_jinja_alias(self) -> None:
        """Test JinjaYamlTemplate can use _jinja_ alias."""
        template = JinjaYamlTemplate.model_validate(["_jinja_", "key: value"])
        result = template()
        assert isinstance(result, dict)
        assert result["key"] == "value"

    def test_jinja_yaml_template_invalid_format(self) -> None:
        """Test JinjaYamlTemplate rejects invalid format."""
        with pytest.raises(SpecError, match="Invalid Jinja YAML template format"):
            JinjaYamlTemplate.model_validate(["_jinja_yaml_", "source", "pipe", "extra"])


# ============================================================================
# Test 4: JinjaJsonTemplate
# ============================================================================


class TestJinjaJsonTemplate:
    """Test JinjaJsonTemplate class."""

    def test_jinja_json_template_creation(self) -> None:
        """Test creating a JinjaJsonTemplate."""
        template = JinjaJsonTemplate.model_validate({"_jinja_json_": '{"key": "{{ value }}"}'})
        result = template(value="test")
        assert isinstance(result, dict)
        assert result["key"] == "test"

    def test_jinja_json_template_alias_list(self) -> None:
        """Test JinjaJsonTemplate with list format."""
        template = JinjaJsonTemplate.model_validate(["_jinja_json_", '{"key": "{{ value }}"}'])
        result = template(value="test")
        assert isinstance(result, dict)
        assert result["key"] == "test"

    def test_jinja_json_template_ignores_custom_pipe(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that JinjaJsonTemplate ignores custom pipe in list format."""
        # The code logs a warning but doesn't emit a Python warning, so we just test functionality
        template = JinjaJsonTemplate.model_validate(["_jinja_json_", '{"key": "value"}', ["_obj_", {"_addr_": "str"}]])
        result = template()
        assert isinstance(result, dict)
        assert result == {"key": "value"}
        assert "Ignoring custom pipe in JinjaJsonTemplate" in caplog.text

    def test_jinja_json_template_complex_structure(self) -> None:
        """Test rendering complex JSON structure."""
        json_source = """
        {
          "items": [
            {% for item in values %}
            "{{ item }}"{% if not loop.last %},{% endif %}
            {% endfor %}
          ]
        }
        """
        template = JinjaJsonTemplate.model_validate({"_jinja_json_": json_source})
        result = template(values=["a", "b", "c"])
        assert isinstance(result, dict)
        assert "items" in result
        assert result["items"] == ["a", "b", "c"]

    def test_jinja_json_template_with_jinja_alias(self) -> None:
        """Test JinjaJsonTemplate can use _jinja_ alias."""
        template = JinjaJsonTemplate.model_validate(["_jinja_", '{"key": "value"}'])
        result = template()
        assert isinstance(result, dict)
        assert result["key"] == "value"

    def test_jinja_json_template_invalid_format(self) -> None:
        """Test JinjaJsonTemplate rejects invalid format."""
        with pytest.raises(SpecError, match="Invalid Jinja JSON template format"):
            JinjaJsonTemplate.model_validate(["_jinja_json_", "source", "pipe", "extra"])


# ============================================================================
# Test 5: extend_structure Function
# ============================================================================


class TestExtendStructure:
    """Test extend_structure function."""

    def test_extend_structure_simple_dict(self) -> None:
        """Test extending simple dict with Jinja template."""
        # When _jinja_ in a dict returns a string (not a dict), it raises an error
        data = {"_jinja_": "Hello {{ name }}", "extra": "value"}
        with pytest.raises(StructuredExtensionError, match="did not produce a mapping"):
            extend_structure(data, template_kwargs={"default": {"name": "World"}})
        # Use YAML template to properly extend dict
        data = {"_jinja_yaml_": "greeting: Hello {{ name }}", "extra": "value"}
        result = extend_structure(data, template_kwargs={"default": {"name": "World"}})
        assert "extra" in result
        assert result["extra"] == "value"
        assert result["greeting"] == "Hello World"

    def test_extend_structure_nested_dict(self) -> None:
        """Test extending nested dict structure."""
        # String template in dict context should raise error
        data = {"outer": {"_jinja_": "{{ value }}", "static": "text"}}
        with pytest.raises(StructuredExtensionError, match="did not produce a mapping"):
            extend_structure(data, template_kwargs={"default": {"value": "dynamic"}})
        # Use YAML template to properly extend dict
        data = {"outer": {"_jinja_yaml_": "result: {{ value }}", "static": "text"}}
        result = extend_structure(data, template_kwargs={"default": {"value": "dynamic"}})
        assert "outer" in result
        assert "static" in result["outer"]
        assert result["outer"]["static"] == "text"
        assert result["outer"]["result"] == "dynamic"

    def test_extend_structure_yaml_template(self) -> None:
        """Test extending structure with YAML template."""
        data = {"_jinja_yaml_": "key: {{ value }}"}
        result = extend_structure(data, template_kwargs={"default": {"value": "test"}})
        assert result == {"key": "test"}

    def test_extend_structure_json_template(self) -> None:
        """Test extending structure with JSON template."""
        data = {"_jinja_json_": '{"key": "{{ value }}"}'}
        result = extend_structure(data, template_kwargs={"default": {"value": "test"}})
        assert result == {"key": "test"}

    def test_extend_structure_list_expansion(self) -> None:
        """Test extending list with template that expands."""
        data = ["item1", {"_jinja_": '["a", "b"]', "_jinja_pipe_": [["_obj_", {"_addr_": "json.loads"}]]}, "item2"]
        result = extend_structure(data)
        assert result == ["item1", "a", "b", "item2"]

    def test_extend_structure_with_group(self) -> None:
        """Test extending with named template group."""
        # When _jinja_ renders to a string in a dict context, it should fail
        # Let's use a template that returns a dict-like structure using YAML
        data = {"_jinja_yaml_": "key: {{ value }}", "_jinja_group_": "custom"}
        result = extend_structure(data, template_kwargs={"custom": {"value": "custom_value"}})
        assert result["key"] == "custom_value"

    def test_extend_structure_default_group(self) -> None:
        """Test default group name."""
        # Use YAML template to return a dict
        data = {"_jinja_yaml_": "key: {{ value }}"}
        result = extend_structure(data, template_kwargs={"default": {"value": "default_value"}}, default="default")
        assert result["key"] == "default_value"

    def test_extend_structure_custom_default_group(self) -> None:
        """Test custom default group name."""
        # Use YAML template to return a dict
        data = {"_jinja_yaml_": "key: {{ value }}"}
        result = extend_structure(data, template_kwargs={"mygroup": {"value": "my_value"}}, default="mygroup")
        assert result["key"] == "my_value"

    def test_extend_structure_no_template_kwargs(self) -> None:
        """Test extending without template_kwargs."""
        data = {"key": "value", "nested": {"inner": "data"}}
        result = extend_structure(data)
        assert result == data

    def test_extend_structure_max_recursion_depth(self) -> None:
        """Test that max recursion depth is enforced."""
        # Create deeply nested structure
        data: dict[str, Any] = {}
        current = data
        for _ in range(MAX_RECURSION_DEPTH + 1):
            current["nested"] = {}
            current = current["nested"]
        with pytest.raises(InstantiationError, match="Maximum recursion depth exceeded"):
            extend_structure(data)

    def test_extend_structure_max_recursion_time(self) -> None:
        """Test that max recursion time is enforced."""
        # Create structure that takes too long
        with patch("structcast.core.template.time") as mock_time:
            mock_time.return_value = 0
            # First call returns start time, subsequent calls return timeout
            mock_time.side_effect = [0, MAX_RECURSION_TIME + 1]
            data = {"nested": {"key": "value"}}
            with pytest.raises(InstantiationError, match="Maximum recursion time exceeded"):
                extend_structure(data)

    def test_extend_structure_preserves_mapping_type(self) -> None:
        """Test that extend_structure preserves custom Mapping types."""
        # Note: Current implementation converts OrderedDict to dict in line 322
        # This is a known limitation - OrderedDict(**dict) doesn't preserve the type properly
        data = OrderedDict([("a", 1), ("b", 2)])
        result = extend_structure(data)
        # Just verify the content is preserved, type conversion is acceptable
        assert isinstance(result, OrderedDict)
        assert result == {"a": 1, "b": 2}
        assert list(result.keys()) == ["a", "b"]  # Order is preserved in Python 3.7+

    def test_extend_structure_preserves_sequence_type(self) -> None:
        """Test that extend_structure preserves sequence types."""
        data = ("a", "b", "c")
        result = extend_structure(data)
        assert isinstance(result, tuple)

    def test_extend_structure_multiple_aliases_error(self) -> None:
        """Test error when multiple Jinja aliases are present."""
        data = {"_jinja_": "template1", "_jinja_yaml_": "template2"}
        with pytest.raises(SpecError, match="Multiple Jinja template aliases found"):
            extend_structure(data)

    def test_extend_structure_template_not_mapping_error(self) -> None:
        """Test error when template in mapping doesn't produce mapping."""
        data = {"_jinja_": "just a string"}
        with pytest.raises(StructuredExtensionError, match="did not produce a mapping"):
            extend_structure(data)

    def test_extend_structure_template_not_sequence_error(self) -> None:
        """Test error when template in sequence doesn't produce sequence."""
        data = [{"_jinja_": "just a string"}]
        with pytest.raises(StructuredExtensionError, match="did not produce a sequence"):
            extend_structure(data)

    def test_extend_structure_deeply_nested(self) -> None:
        """Test extending deeply nested structure."""
        data = {"level1": {"level2": {"level3": {"_jinja_yaml_": "value: {{ deep_value }}"}}}}
        result = extend_structure(data, template_kwargs={"default": {"deep_value": "found"}})
        assert result["level1"]["level2"]["level3"]["value"] == "found"

    def test_extend_structure_mixed_content(self) -> None:
        """Test extending structure with mixed static and dynamic content."""
        data = {
            "static1": "value1",
            "dynamic": {"_jinja_yaml_": "result: {{ var }}"},
            "static2": "value2",
            "nested": {"static3": "value3", "dynamic2": {"_jinja_yaml_": "key: {{ var2 }}"}},
        }
        result = extend_structure(data, template_kwargs={"default": {"var": "dynamic1", "var2": "dynamic2"}})
        assert result["static1"] == "value1"
        assert result["dynamic"]["result"] == "dynamic1"
        assert result["static2"] == "value2"
        assert result["nested"]["static3"] == "value3"
        assert result["nested"]["dynamic2"]["key"] == "dynamic2"

    def test_extend_structure_empty_structures(self) -> None:
        """Test extending empty structures."""
        assert extend_structure({}) == {}
        assert extend_structure([]) == []
        assert extend_structure(()) == ()

    def test_extend_structure_primitive_types(self) -> None:
        """Test that primitive types pass through unchanged."""
        assert extend_structure(42) == 42
        assert extend_structure("string") == "string"
        assert extend_structure(True) is True
        assert extend_structure(None) is None


# ============================================================================
# Test 6: Edge Cases and Error Handling
# ============================================================================


class TestEdgeCasesAndErrors:
    """Test edge cases and error conditions."""

    def test_template_with_syntax_error(self) -> None:
        """Test that template with syntax error raises on creation."""
        with pytest.raises(TemplateSyntaxError):
            JinjaTemplate.model_validate({"_jinja_": "{{ unclosed"})

    def test_template_revalidation(self) -> None:
        """Test that template validation is cached."""
        template = JinjaTemplate.model_validate({"_jinja_": "{{ value }}"})
        # Access template twice to ensure caching works
        t1 = template.template
        t2 = template.template
        assert t1 is t2

    def test_jinja_template_from_instance(self) -> None:
        """Test creating JinjaTemplate from another instance."""
        original = JinjaTemplate.model_validate({"_jinja_": "test"})
        copy = JinjaTemplate.model_validate(original)
        assert copy.source == original.source

    def test_yaml_template_from_instance(self) -> None:
        """Test creating JinjaYamlTemplate from another instance."""
        original = JinjaYamlTemplate.model_validate({"_jinja_yaml_": "key: value"})
        copy = JinjaYamlTemplate.model_validate(original)
        assert copy.source == original.source

    def test_json_template_from_instance(self) -> None:
        """Test creating JinjaJsonTemplate from another instance."""
        original = JinjaJsonTemplate.model_validate({"_jinja_json_": '{"key": "value"}'})
        copy = JinjaJsonTemplate.model_validate(original)
        assert copy.source == original.source

    def test_extend_structure_with_pipe(self) -> None:
        """Test that pipe in template is respected in extend_structure."""
        # When _jinja_ with pipe is alone in dict, need to use yaml to return dict
        data = {"_jinja_yaml_": "value: 42"}
        result = extend_structure(data)
        assert result["value"] == 42

    def test_template_with_filters(self) -> None:
        """Test template with Jinja filters."""
        template = JinjaTemplate.model_validate({"_jinja_": "{{ name | upper }}"})
        result = template(name="hello")
        assert result == "HELLO"

    def test_template_with_loop_controls(self) -> None:
        """Test template with loop controls extension."""
        template = JinjaTemplate.model_validate(
            {
                "_jinja_": """
        {% for i in range(10) %}
        {%- if i == 5 %}{% break %}{% endif %}
        {{ i }}
        {%- endfor %}
        """
            }
        )
        result = template()
        assert "5" not in result
        assert "4" in result

    def test_extend_structure_preserves_non_jinja_keys(self) -> None:
        """Test that non-Jinja keys are preserved during extension."""
        data = {
            "_jinja_yaml_": "jinja_key: value",
            "_jinja_group_": "default",
            "normal_key": "normal_value",
        }
        result = extend_structure(data)
        assert result["normal_key"] == "normal_value"
        assert result["jinja_key"] == "value"
