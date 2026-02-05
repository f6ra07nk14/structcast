"""Jinja template support for StructCast."""

from abc import abstractmethod
from collections.abc import Mapping, Sequence
from copy import copy
from dataclasses import field
from functools import cached_property
from logging import getLogger
from typing import TYPE_CHECKING, Any, Optional, Union

from jinja2 import Environment, StrictUndefined, Template, Undefined
from jinja2.meta import find_undeclared_variables
from jinja2.sandbox import ImmutableSandboxedEnvironment
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from structcast.core.instantiator import ObjectPattern, WithPipe
from structcast.core.specifier import SpecError
from structcast.utils.dataclasses import dataclass

if TYPE_CHECKING:
    from jinja2.ext import Extension

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

    extensions: list[Union[str, type["Extension"]]] = field(default_factory=lambda: ["jinja2.ext.loopcontrols"])
    """List of Jinja extensions to enable."""


__jinja_settings = JinjaSettings()
"""Global settings for Jinja templates."""


def get_environment() -> Environment:
    """Get the Jinja environment options."""
    return __jinja_settings.environment_type(
        undefined=__jinja_settings.undefined_type,
        trim_blocks=__jinja_settings.trim_blocks,
        lstrip_blocks=__jinja_settings.lstrip_blocks,
        extensions=__jinja_settings.extensions,
    )


def configure_jinja(
    settings: Optional[JinjaSettings] = None,
    *,
    environment_type: Optional[type[Environment]] = None,
    undefined_type: Optional[type[Undefined]] = None,
    trim_blocks: Optional[bool] = None,
    lstrip_blocks: Optional[bool] = None,
    extensions: Optional[list[Union[str, type["Extension"]]]] = None,
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
        settings = JinjaSettings(**kwargs)
    __jinja_settings.environment_type = settings.environment_type
    __jinja_settings.undefined_type = settings.undefined_type
    __jinja_settings.trim_blocks = settings.trim_blocks
    __jinja_settings.lstrip_blocks = settings.lstrip_blocks
    __jinja_settings.extensions = settings.extensions.copy()


_ALIAS_JINJA = "_jinja_"
_ALIAS_JINJA_GROUP = "_jinja_group_"
_ALIAS_JINJA_PIPE = "_jinja_pipe_"
_ALIAS_JINJA_YAML = "_jinja_yaml_"
_ALIAS_JINJA_JSON = "_jinja_json_"
_YAML_LOAD_PATTERN = ["_obj_", {"_addr_": "structcast.utils.base.load_yaml_from_string"}]
_JSON_LOAD_PATTERN = ["_obj_", {"_addr_": "json.loads"}]


class JinjaTemplate(BaseModel, WithPipe):
    """A wrapper for a Jinja template that can be used as a field in a Pydantic model."""

    model_config = ConfigDict(frozen=True, validate_default=True, extra="forbid", serialize_by_alias=True)

    source: str = Field("", alias=_ALIAS_JINJA)
    """The Jinja template source."""

    pipe: list[ObjectPattern] = Field(default_factory=list, alias=_ALIAS_JINJA_PIPE)
    """List of casting patterns to apply after construction."""

    @model_validator(mode="before")
    @classmethod
    def _validate_raw(cls, raw: Any) -> Any:
        if isinstance(raw, JinjaTemplate):
            return raw
        if isinstance(raw, (list, tuple)) and raw and raw[0] == _ALIAS_JINJA:
            if len(raw) == 2:
                return {_ALIAS_JINJA: raw[1]}
            if len(raw) == 3:
                return {_ALIAS_JINJA: raw[1], _ALIAS_JINJA_PIPE: raw[2]}
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

    @abstractmethod
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
        if isinstance(raw, BaseModel):
            raw = raw.model_dump()
        if isinstance(raw, (list, tuple)) and raw and raw[0] in {_ALIAS_JINJA_YAML, _ALIAS_JINJA}:
            if len(raw) == 2:
                raw = {_ALIAS_JINJA: raw[1]}
            elif len(raw) == 3:
                logger.warning(f"Ignoring custom pipe in JinjaYamlTemplate: {raw[2]}")
                raw = {_ALIAS_JINJA: raw[1]}
            else:
                raise SpecError(f"Invalid Jinja YAML template format: {raw}")
        if isinstance(raw, (dict, Mapping)):
            raw = copy(raw)  # Avoid mutating the original mapping
            if _ALIAS_JINJA_YAML in raw:
                raw[_ALIAS_JINJA] = raw.pop(_ALIAS_JINJA_YAML)
            if _ALIAS_JINJA_PIPE in raw and raw[_ALIAS_JINJA_PIPE] != _YAML_LOAD_PATTERN:
                logger.warning(f"Ignoring custom pipe in JinjaYamlTemplate: {raw[_ALIAS_JINJA_PIPE]}")
            raw[_ALIAS_JINJA_PIPE] = _YAML_LOAD_PATTERN
        return raw


class JinjaJsonTemplate(JinjaTemplate):
    """A wrapper for a Jinja JSON template that can be used as a field in a Pydantic model."""

    @model_validator(mode="before")
    @classmethod
    def _validate_raw_with_json(cls, raw: Any) -> Any:
        if isinstance(raw, JinjaJsonTemplate):
            return raw
        if isinstance(raw, BaseModel):
            raw = raw.model_dump()
        if isinstance(raw, (list, tuple)) and raw and raw[0] in {_ALIAS_JINJA_JSON, _ALIAS_JINJA}:
            if len(raw) == 2:
                raw = {_ALIAS_JINJA: raw[1]}
            elif len(raw) == 3:
                logger.warning(f"Ignoring custom pipe in JinjaJsonTemplate: {raw[2]}")
                raw = {_ALIAS_JINJA: raw[1]}
            else:
                raise SpecError(f"Invalid Jinja JSON template format: {raw}")
        if isinstance(raw, (dict, Mapping)):
            raw = copy(raw)  # Avoid mutating the original mapping
            if _ALIAS_JINJA_JSON in raw:
                raw[_ALIAS_JINJA] = raw.pop(_ALIAS_JINJA_JSON)
            if _ALIAS_JINJA_PIPE in raw and raw[_ALIAS_JINJA_PIPE] != _JSON_LOAD_PATTERN:
                logger.warning(f"Ignoring custom pipe in JinjaJsonTemplate: {raw[_ALIAS_JINJA_PIPE]}")
            raw[_ALIAS_JINJA_PIPE] = _JSON_LOAD_PATTERN
        return raw


def _resolve_jinja_pattern(
    raw: Mapping,
    template_kwargs: dict[str, dict[str, Any]],
    default: str,
) -> tuple[Mapping, Optional[Any]]:
    find_jinja_yaml = _ALIAS_JINJA_YAML in raw
    find_jinja_json = _ALIAS_JINJA_JSON in raw
    find_jinja = _ALIAS_JINJA in raw
    if find_jinja_yaml + find_jinja_json + find_jinja > 1:
        raise SpecError(f"Multiple Jinja template aliases found in mapping: {raw}")
    if find_jinja_yaml:
        alias, cls = _ALIAS_JINJA_YAML, JinjaYamlTemplate
    elif find_jinja_json:
        alias, cls = _ALIAS_JINJA_JSON, JinjaJsonTemplate
    elif find_jinja:
        alias, cls = _ALIAS_JINJA, JinjaTemplate
    else:
        return raw, None
    temp, raw = raw[alias], {k: v for k, v in raw.items() if k != alias}
    group_kw = template_kwargs.get(raw.pop(_ALIAS_JINJA_GROUP, None) or default) or {}
    if _ALIAS_JINJA_PIPE in raw:
        temp[_ALIAS_JINJA_PIPE] = raw.pop(_ALIAS_JINJA_PIPE)
    part = cls.model_validate(temp)(**group_kw)
    return raw, part


def _resolve_jinja_pattern_in_mapping(
    raw: Mapping,
    template_kwargs: dict[str, dict[str, Any]],
    default: str,
) -> Mapping:
    raw, part = _resolve_jinja_pattern(raw, template_kwargs=template_kwargs, default=default)
    if part is None:
        return raw
    if isinstance(part, Mapping):
        return {**raw, **part}
    raise SpecError(f"Jinja template did not produce a mapping: {part}")


def _resolve_jinja_pattern_in_seq(raw: Sequence, template_kwargs: dict[str, dict[str, Any]], default: str) -> list[Any]:
    result = []
    for item in raw:
        if isinstance(item, (dict, Mapping)):
            item, part = _resolve_jinja_pattern(item, template_kwargs=template_kwargs, default=default)
            if part is None:
                result.append(item)
            elif isinstance(part, (list, tuple)):
                result.extend(part)
            else:
                raise SpecError(f"Jinja template did not produce a sequence: {part}")
        else:
            result.append(item)
    return result


def extend_structure(
    data: Any,
    *,
    template_kwargs: Optional[dict[str, dict[str, Any]]] = None,
    default: str = "default",
) -> Any:
    """Recursively extend a data structure by resolving Jinja templates.

    Args:
        data (Any): The data structure to extend.
        template_kwargs (dict[str, dict[str, Any]] | None):
            A mapping of template group names to keyword arguments for rendering.
        default (str): The default template group name to use when none is specified.

    Returns:
        Any: The extended data structure with Jinja templates resolved.
    """
    template_kwargs = template_kwargs or {}

    def _extend(raw: Any) -> Any:
        if isinstance(raw, dict):
            raw = _resolve_jinja_pattern_in_mapping(raw, template_kwargs=template_kwargs, default=default)
            return {k: _extend(v) for k, v in raw.items()}
        if isinstance(raw, Mapping):
            cls: type = type(raw)
            raw = _resolve_jinja_pattern_in_mapping(raw, template_kwargs=template_kwargs, default=default)
            return cls(**{k: _extend(v) for k, v in raw.items()})
        if isinstance(raw, (list, tuple)):
            cls = type(raw)
            raw = _resolve_jinja_pattern_in_seq(raw, template_kwargs=template_kwargs, default=default)
            return cls(_extend(v) for v in raw)
        return raw

    return _extend(data)
