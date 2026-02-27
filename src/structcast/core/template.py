"""Jinja template support for StructCast."""

from collections.abc import Mapping, Sequence
from copy import copy
from dataclasses import field
from functools import cached_property, reduce
from logging import getLogger
from operator import or_
from time import time
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

from jinja2 import Environment, StrictUndefined, Template, Undefined
from jinja2.meta import find_undeclared_variables
from jinja2.sandbox import ImmutableSandboxedEnvironment
from pydantic import Field, model_validator
from typing_extensions import Self

from structcast.core.base import WithExtra
from structcast.core.constants import MAX_RECURSION_DEPTH, MAX_RECURSION_TIME
from structcast.core.exceptions import InstantiationError, SpecError, StructuredExtensionError
from structcast.core.instantiator import ObjectPattern
from structcast.core.specifier import WithPipe
from structcast.utils.dataclasses import dataclass

if TYPE_CHECKING:
    from jinja2.ext import Extension
else:
    Extension = Any

logger = getLogger(__name__)


@dataclass
class JinjaSettings:
    """Settings for Jinja templates."""

    environment_type: type[Environment] = ImmutableSandboxedEnvironment
    """The type of Jinja environment to use."""

    undefined_type: type[Undefined] = StrictUndefined
    """The type of Jinja undefined to use."""

    trim_blocks: bool = True
    """Whether to trim blocks in the Jinja template."""

    lstrip_blocks: bool = True
    """Whether to left-strip blocks in the Jinja template."""

    raise_error: bool = True
    """Whether to raise an error on template rendering failure."""

    extensions: list[Union[str, type[Extension]]] = field(default_factory=lambda: ["jinja2.ext.loopcontrols"])
    """List of Jinja extensions to enable."""

    filters: dict[str, Callable[..., Any]] = field(default_factory=dict)
    """Custom Jinja filters to add to the environment."""


_jinja_settings = JinjaSettings()
"""Global settings for Jinja templates."""


def get_environment() -> Environment:
    """Get the Jinja environment options."""
    env = _jinja_settings.environment_type(
        undefined=_jinja_settings.undefined_type,
        trim_blocks=_jinja_settings.trim_blocks,
        lstrip_blocks=_jinja_settings.lstrip_blocks,
        extensions=_jinja_settings.extensions,
    )
    env.filters.update(_jinja_settings.filters)
    return env


def configure_jinja(
    settings: Optional[JinjaSettings] = None,
    *,
    environment_type: Optional[type[Environment]] = None,
    undefined_type: Optional[type[Undefined]] = None,
    trim_blocks: Optional[bool] = None,
    lstrip_blocks: Optional[bool] = None,
    extensions: Optional[list[Union[str, type[Extension]]]] = None,
    filters: Optional[dict[str, Callable[..., Any]]] = None,
) -> None:
    """Configure the Jinja environment settings.

    Args:
        settings (JinjaSettings | None): An instance of JinjaSettings to use for configuration.
            If provided, individual keyword arguments will be ignored.
            If None, individual keyword arguments will be used for configuration.
        environment_type (type[Environment] | None): The type of Jinja environment to use.
            If None, use default from settings.
        undefined_type (type[Undefined] | None): The type of Jinja undefined to use.
            If None, use default from settings.
        trim_blocks (bool | None): Whether to trim blocks in the Jinja template.
            If None, use default from settings.
        lstrip_blocks (bool | None): Whether to left-strip blocks in the Jinja template.
            If None, use default from settings.
        extensions (list[Union[str, type[Extension]]] | None): List of Jinja extensions to enable.
            If None, use default from settings.
        filters (dict[str, Callable[..., Any]] | None): Custom Jinja filters to add to the environment.
            If None, use default from settings.
    """
    if settings is None:
        kwargs: dict[str, Any] = {}
        if environment_type is not None:
            kwargs["environment_type"] = environment_type
        if undefined_type is not None:
            kwargs["undefined_type"] = undefined_type
        if trim_blocks is not None:
            kwargs["trim_blocks"] = trim_blocks
        if lstrip_blocks is not None:
            kwargs["lstrip_blocks"] = lstrip_blocks
        if extensions is not None:
            kwargs["extensions"] = extensions
        if filters is not None:
            kwargs["filters"] = filters
        settings = JinjaSettings(**kwargs)
    _jinja_settings.environment_type = settings.environment_type
    _jinja_settings.undefined_type = settings.undefined_type
    _jinja_settings.trim_blocks = settings.trim_blocks
    _jinja_settings.lstrip_blocks = settings.lstrip_blocks
    _jinja_settings.extensions = settings.extensions.copy()
    _jinja_settings.filters = settings.filters.copy()


ALIAS_JINJA = "_jinja_"
ALIAS_JINJA_GROUP = "_jinja_group_"
ALIAS_JINJA_PIPE = "_jinja_pipe_"
ALIAS_JINJA_YAML = "_jinja_yaml_"
ALIAS_JINJA_JSON = "_jinja_json_"
ALIAS_ALL = [ALIAS_JINJA, ALIAS_JINJA_GROUP, ALIAS_JINJA_JSON, ALIAS_JINJA_PIPE, ALIAS_JINJA_YAML]
_YAML_LOAD_PATTERN = ["_obj_", {"_addr_": "structcast.utils.base.load_yaml_from_string"}]
_JSON_LOAD_PATTERN = ["_obj_", {"_addr_": "json.loads"}]


class JinjaTemplate(WithPipe):
    """A wrapper for a Jinja template that can be used as a field in a Pydantic model."""

    source: str = Field("", alias=ALIAS_JINJA)
    """The Jinja template source."""

    pipe: list[ObjectPattern] = Field(default_factory=list, alias=ALIAS_JINJA_PIPE)
    """List of casting patterns to apply after construction."""

    @model_validator(mode="before")
    @classmethod
    def _validate_raw(cls, raw: Any) -> Any:
        if isinstance(raw, JinjaTemplate):
            return raw
        if isinstance(raw, (list, tuple)) and raw and raw[0] == ALIAS_JINJA:
            if len(raw) == 2:
                return {ALIAS_JINJA: raw[1]}
            if len(raw) == 3:
                return {ALIAS_JINJA: raw[1], ALIAS_JINJA_PIPE: raw[2]}
            raise SpecError(f"Invalid Jinja template format: {raw}")
        return raw

    @model_validator(mode="after")
    def _validate_template(self) -> Self:
        """Validate the Jinja template."""
        _ = self._template_and_variables  # Ensure the template is valid and cache the compiled template and variables.
        return self

    @cached_property
    def _template_and_variables(self) -> tuple[Template, set[str]]:
        """Compile the Jinja template."""
        env = get_environment()
        gram = env.parse(self.source)
        return env.from_string(gram), find_undeclared_variables(gram)

    @property
    def template(self) -> Template:
        """Get the compiled Jinja template."""
        return self._template_and_variables[0]

    @property
    def variables(self) -> set[str]:
        """Get the undeclared variables in the Jinja template."""
        return self._template_and_variables[1]

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Render the Jinja template with the given context."""
        return self.casting(self.template.render(*args, **kwargs))


class JinjaYamlTemplate(JinjaTemplate):
    """A wrapper for a Jinja YAML template that can be used as a field in a Pydantic model."""

    @model_validator(mode="before")
    @classmethod
    def _validate_raw_with_yaml(cls, raw: Any) -> Any:
        if isinstance(raw, JinjaYamlTemplate):
            return raw
        if isinstance(raw, (list, tuple)) and raw and raw[0] in {ALIAS_JINJA_YAML, ALIAS_JINJA}:
            if len(raw) == 2:
                raw = {ALIAS_JINJA: raw[1]}
            elif len(raw) == 3:
                logger.warning(f"Ignoring custom pipe in JinjaYamlTemplate: {raw[2]}")
                raw = {ALIAS_JINJA: raw[1]}
            else:
                raise SpecError(f"Invalid Jinja YAML template format: {raw}")
        if isinstance(raw, (dict, Mapping)):
            raw = copy(raw)  # Avoid mutating the original mapping
            if ALIAS_JINJA_YAML in raw:
                raw[ALIAS_JINJA] = raw.pop(ALIAS_JINJA_YAML)
            if ALIAS_JINJA_PIPE in raw and raw[ALIAS_JINJA_PIPE] != _YAML_LOAD_PATTERN:
                logger.warning(f"Ignoring custom pipe in JinjaYamlTemplate: {raw[ALIAS_JINJA_PIPE]}")
            raw[ALIAS_JINJA_PIPE] = _YAML_LOAD_PATTERN
        return raw


class JinjaJsonTemplate(JinjaTemplate):
    """A wrapper for a Jinja JSON template that can be used as a field in a Pydantic model."""

    @model_validator(mode="before")
    @classmethod
    def _validate_raw_with_json(cls, raw: Any) -> Any:
        if isinstance(raw, JinjaJsonTemplate):
            return raw
        if isinstance(raw, (list, tuple)) and raw and raw[0] in {ALIAS_JINJA_JSON, ALIAS_JINJA}:
            if len(raw) == 2:
                raw = {ALIAS_JINJA: raw[1]}
            elif len(raw) == 3:
                logger.warning(f"Ignoring custom pipe in JinjaJsonTemplate: {raw[2]}")
                raw = {ALIAS_JINJA: raw[1]}
            else:
                raise SpecError(f"Invalid Jinja JSON template format: {raw}")
        if isinstance(raw, (dict, Mapping)):
            raw = copy(raw)  # Avoid mutating the original mapping
            if ALIAS_JINJA_JSON in raw:
                raw[ALIAS_JINJA] = raw.pop(ALIAS_JINJA_JSON)
            if ALIAS_JINJA_PIPE in raw and raw[ALIAS_JINJA_PIPE] != _JSON_LOAD_PATTERN:
                logger.warning(f"Ignoring custom pipe in JinjaJsonTemplate: {raw[ALIAS_JINJA_PIPE]}")
            raw[ALIAS_JINJA_PIPE] = _JSON_LOAD_PATTERN
        return raw


class Parameters(WithExtra):
    """Parameters for template formatting."""

    shared: dict[str, Any] = Field(default_factory=dict, alias="_shared_")
    """Shared parameters for all groups."""

    default: dict[str, Any] = Field(default_factory=dict, alias="_default_")
    """Default parameters for the default group."""

    @model_validator(mode="after")
    def _validate_parameters(self) -> Self:
        if "default" in self.model_extra:
            self.default.update(self.model_extra.pop("default"))
        for key, value in self.model_extra.items():
            if key in ALIAS_ALL:
                raise SpecError(f'Key "{key}" is reserved for template aliases and cannot be used in parameters.')
            if not isinstance(value, dict):
                raise SpecError(f'Parameters for group "{key}" must be a dictionary but got: {value}')
        if duplicate_keys := set(self.default) & set(self.shared):
            raise ValueError(f'Duplicate keys found in both "default" and "shared" parameters: {duplicate_keys}')
        return self

    @cached_property
    def template_kwargs(self) -> dict[str, dict[str, Any]]:
        """Get the template keyword arguments for formatting."""
        res = {k: {**v, **self.shared} for k, v in self.model_extra.items()}
        res["default"] = {**self.default, **self.shared}
        return res

    def merge(self, other: Union[dict[str, dict[str, Any]], "Parameters"]) -> "Parameters":
        """Merge the given template keyword arguments with the parameters.

        Args:
            other (dict[str, dict[str, Any]] | Parameters): The template keyword arguments to merge, or another
                `Parameters` instance to merge with.

        Returns:
            A new `Parameters` instance with the merged template keyword arguments.
        """

        def _get(group: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
            return group.get(name, None) or {}

        other = (other if isinstance(other, Parameters) else type(self).model_validate(other)).template_kwargs
        owner = self.template_kwargs
        return type(self).model_validate({k: {**_get(owner, k), **_get(other, k)} for k in set(owner) | set(other)})

    def __or__(self, other: Optional[Union[dict[str, dict[str, Any]], "Parameters"]]) -> "Parameters":
        """Merge the given template keyword arguments with the parameters using the `|` operator.

        Args:
            other (dict[str, dict[str, Any]] | Parameters | None): The template keyword arguments to merge,
                another `Parameters` instance to merge with, or `None` to return the original parameters.

        Returns:
            A new `Parameters` instance with the merged template keyword arguments.
        """
        return self if other is None else self.merge(other)

    @classmethod
    def create(cls, *parameters: Optional[Union[dict[str, dict[str, Any]], "Parameters"]]) -> "Parameters":
        """Create a `Parameters` instance from the given template keyword arguments.

        Args:
            *parameters (dict[str, dict[str, Any]] | Parameters | None): The template keyword arguments to create the
                `Parameters` instance with. Can be specified multiple times, and will be merged together.

        Returns:
            A `Parameters` instance created from the given template keyword arguments.
        """
        return reduce(or_, parameters, cls())


def _resolve_jinja_pattern(
    raw: Mapping[str, Any],
    template_kwargs: dict[str, dict[str, Any]],
    default: str,
) -> tuple[bool, dict[str, Any], Any]:
    find_jinja_yaml = ALIAS_JINJA_YAML in raw
    find_jinja_json = ALIAS_JINJA_JSON in raw
    find_jinja = ALIAS_JINJA in raw
    if find_jinja_yaml + find_jinja_json + find_jinja > 1:
        raise SpecError(f"Multiple Jinja template aliases found in mapping: {raw}")
    if find_jinja_yaml:
        alias, cls = ALIAS_JINJA_YAML, JinjaYamlTemplate
    elif find_jinja_json:
        alias, cls = ALIAS_JINJA_JSON, JinjaJsonTemplate
    elif find_jinja:
        alias, cls = ALIAS_JINJA, JinjaTemplate
    else:
        return False, raw, None
    temp, raw = {alias: raw[alias]}, {k: v for k, v in raw.items() if k != alias}
    group_kw = template_kwargs.get(raw.pop(ALIAS_JINJA_GROUP, None) or default) or {}
    if ALIAS_JINJA_PIPE in raw:
        temp[ALIAS_JINJA_PIPE] = raw.pop(ALIAS_JINJA_PIPE)
    return True, raw, cls.model_validate(temp)(**group_kw)


def _resolve_jinja_pattern_in_mapping(
    raw: Mapping[str, Any], template_kwargs: dict[str, dict[str, Any]], default: str
) -> tuple[bool, Mapping]:
    resolved, raw, part = _resolve_jinja_pattern(raw, template_kwargs=template_kwargs, default=default)
    if not resolved:
        return False, raw
    if not raw:
        return True, part
    if isinstance(part, Mapping):
        return True, {**raw, **part}
    raise StructuredExtensionError(f"Jinja template did not produce a mapping: {part}")


def _resolve_jinja_pattern_in_seq(
    raw: Sequence, template_kwargs: dict[str, dict[str, Any]], default: str
) -> tuple[bool, list]:
    result = []
    resolved = False
    for item in raw:
        if not isinstance(item, Mapping):
            result.append(item)
            continue
        sub_resolved, raw, part = _resolve_jinja_pattern(item, template_kwargs=template_kwargs, default=default)
        if not sub_resolved:
            result.append(item)
            continue
        resolved = True
        if raw:
            if not isinstance(part, Mapping):
                raise StructuredExtensionError(f"Jinja template did not produce a mapping: {part}")
            tmp_d = {**raw, **part}
            result.append(tmp_d if (cls := type(raw)) is dict else cls(tmp_d))
        elif isinstance(part, (list, tuple)):
            result.extend(part)
        else:
            raise StructuredExtensionError(f"Jinja template did not produce a sequence: {part}")
    return resolved, result


def extend_structure(
    data: Any,
    *,
    template_kwargs: Optional[Union[dict[str, dict[str, Any]], Parameters]] = None,
    default: str = "default",
    __depth__: int = 0,
    __start__: Optional[float] = None,
) -> Any:
    """Recursively extend a data structure by resolving Jinja templates.

    Args:
        data (Any): The data structure to extend.
        template_kwargs (dict[str, dict[str, Any]] | Parameters | None):
            A mapping of template group names to keyword arguments for rendering, or a `Parameters` instance.
        default (str): The default template group name to use when none is specified.

    Returns:
        Any: The extended data structure with Jinja templates resolved.

    Raises:
        InstantiationError: If the maximum recursion depth or time is exceeded.
        StructuredExtensionError: If a Jinja template produces an invalid structure.
        SpecError: If there is an error in the Jinja template specification.
    """
    if __start__ is None:
        __start__ = time()
    if isinstance(template_kwargs, Parameters):
        t_kw = template_kwargs.template_kwargs
    else:
        t_kw = Parameters.create(template_kwargs).template_kwargs

    def _extend(raw: Any, dep: int) -> Any:
        if dep >= MAX_RECURSION_DEPTH:
            raise InstantiationError(f"Maximum recursion depth exceeded: {MAX_RECURSION_DEPTH}")
        if (time() - __start__) > MAX_RECURSION_TIME:
            raise InstantiationError(f"Maximum recursion time exceeded: {MAX_RECURSION_TIME} seconds")
        dep += 1
        if isinstance(raw, Mapping):
            resolved, tmp_d = _resolve_jinja_pattern_in_mapping(raw, template_kwargs=t_kw, default=default)
            tmp_d = _extend(tmp_d, dep) if resolved else {k: _extend(v, dep) for k, v in tmp_d.items()}
            return tmp_d if (cls := type(raw)) is dict else cls(tmp_d)
        if not isinstance(raw, str) and isinstance(raw, (list, tuple, Sequence)):
            resolved, tmp_l = _resolve_jinja_pattern_in_seq(raw, template_kwargs=t_kw, default=default)
            return type(raw)(_extend(tmp_l, dep) if resolved else [_extend(v, dep) for v in tmp_l])
        return raw

    return _extend(data, __depth__)


__all__ = [
    "ALIAS_ALL",
    "ALIAS_JINJA",
    "ALIAS_JINJA_GROUP",
    "ALIAS_JINJA_JSON",
    "ALIAS_JINJA_PIPE",
    "ALIAS_JINJA_YAML",
    "JinjaJsonTemplate",
    "JinjaSettings",
    "JinjaTemplate",
    "JinjaYamlTemplate",
    "Parameters",
    "configure_jinja",
    "extend_structure",
    "get_environment",
]


if not TYPE_CHECKING:
    import sys

    from structcast.utils.lazy_import import LazySelectedImporter

    sys.modules[__name__] = LazySelectedImporter(__name__, globals())
