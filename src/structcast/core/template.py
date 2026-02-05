from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
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

    extensions: Sequence[Union[str, type["Extension"]]] = field(default_factory=lambda: ["jinja2.ext.loopcontrols"])
    """List of Jinja extensions to enable."""

    raise_error: bool = True
    """Whether to raise an error on template rendering failure."""


__jinja_settings = JinjaSettings()


def get_environment() -> Environment:
    """Get the Jinja environment options."""
    return __jinja_settings.environment_type(
        undefined=__jinja_settings.undefined_type,
        trim_blocks=__jinja_settings.trim_blocks,
        lstrip_blocks=__jinja_settings.lstrip_blocks,
        extensions=__jinja_settings.extensions,
    )


def register_jinja_extension(extension: Union[str, type["Extension"]]) -> None:
    """Register a Jinja extension.

    Args:
        extension (str | type[Extension]): The Jinja extension to register.
    """
    if extension not in {e if isinstance(e, str) else e.__name__ for e in __jinja_settings.extensions}:
        __jinja_settings.extensions.append(extension)


def configure_jinja(
    environment_type: Optional[type[Environment]] = None,
    undefined_type: Optional[type[Undefined]] = None,
    trim_blocks: Optional[bool] = None,
    lstrip_blocks: Optional[bool] = None,
) -> None:
    """Configure the Jinja environment settings.

    Args:
        environment_type (type[Environment] | None): The type of Jinja environment to use.
        undefined_type (type[Undefined] | None): The type of Jinja undefined to use.
        trim_blocks (bool | None): Whether to trim blocks in the Jinja template.
        lstrip_blocks (bool | None): Whether to left-strip blocks in the Jinja template
    """
    if environment_type is not None:
        __jinja_settings.environment_type = environment_type
    if undefined_type is not None:
        __jinja_settings.undefined_type = undefined_type
    if trim_blocks is not None:
        __jinja_settings.trim_blocks = trim_blocks
    if lstrip_blocks is not None:
        __jinja_settings.lstrip_blocks = lstrip_blocks


_ALIAS_JINJA = "_jinja_"
_ALIAS_JINJA_YAML = "_jyaml_"
_ALIAS_JINJA_JSON = "_jjson_"


class _JinjaTemplate(BaseModel, ABC):
    """A wrapper for a Jinja template that can be used as a field in a Pydantic model."""

    model_config = ConfigDict(frozen=True, validate_default=True, extra="forbid", serialize_by_alias=True)

    source: str = Field("", alias=_ALIAS_JINJA)
    """The Jinja template source."""

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


class JinjaTemplate(_JinjaTemplate, WithPipe):
    """A wrapper for a Jinja template that can be used as a field in a Pydantic model.

    This class also supports the pipe operator for rendering the template with a context.
    """

    @model_validator(mode="before")
    @classmethod
    def _validate_raw(cls, raw: Any) -> Any:
        if isinstance(raw, JinjaTemplate):
            return raw
        if isinstance(raw, (list, tuple)) and raw and raw[0] == _ALIAS_JINJA:
            if len(raw) == 2:
                return {_ALIAS_JINJA: raw[1]}
            if len(raw) == 3:
                return {_ALIAS_JINJA: raw[1], "_pipe_": raw[2]}
            raise SpecError(f"Invalid Jinja template format: {raw}")
        return raw

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Render the Jinja template with the given context."""
        return self.casting(self.template.render(*args, **kwargs))


class JinjaYamlTemplate(JinjaTemplate):
    """A wrapper for a Jinja YAML template that can be used as a field in a Pydantic model."""

    pipe: list[ObjectPattern] = Field(
        default_factory=lambda: ["_obj_", {"_addr_": "structcast.utils.base.load_yaml_from_string"}], alias="_pipe_"
    )
    """The pipe to use for rendering the template and loading the YAML."""

    @model_validator(mode="before")
    @classmethod
    def _validate_raw_with_yaml(cls, raw: Any) -> Any:
        if isinstance(raw, JinjaYamlTemplate):
            return raw
        if isinstance(raw, BaseModel):
            raw = raw.model_dump()
        if isinstance(raw, (dict, Mapping)):
            raw = raw.copy()  # Avoid mutating the original mapping
            if _ALIAS_JINJA_YAML in raw:
                raw[_ALIAS_JINJA] = raw.pop(_ALIAS_JINJA_YAML)
            # todo


class JinjaJsonTemplate(JinjaTemplate):
    """A wrapper for a Jinja JSON template that can be used as a field in a Pydantic model."""

    pipe: list[ObjectPattern] = Field(default_factory=lambda: ["_obj_", {"_addr_": "json.loads"}], alias="_pipe_")
    """The pipe to use for rendering the template and loading the JSON."""


def _resolve_jinja_pattern_in_mapping(
    raw: Mapping, template_kwargs: dict[str, dict[str, Any]], default: str
) -> tuple[Mapping, Mapping]:
    if _ALIAS_JINJA_YAML in raw:
        alias = _ALIAS_JINJA_YAML
    elif _ALIAS_JINJA_JSON in raw:
        alias = _ALIAS_JINJA_JSON
    else:
        return raw, {}
    part, raw = raw[alias], {k: v for k, v in raw.items() if k != alias}


def extend_structure(
    raw: Any,
    *,
    template_kwargs: Optional[dict[str, dict[str, Any]]] = None,
    default: str = "default",
) -> Any:
    if isinstance(raw, dict):
        return {k: convert_spec(v) for k, v in raw.items()}
    if isinstance(raw, Mapping):
        return type(raw)(**{k: convert_spec(v) for k, v in raw.items()})
    if isinstance(raw, (list, tuple)):
        return type(raw)(convert_spec(v) for v in raw)
