"""Base classes for structcast configurations."""

from typing import Any, cast

from pydantic import BaseModel, ConfigDict

from structcast.utils.security import get_default_dir


class Serializable(BaseModel):
    """Base configuration."""

    model_config = ConfigDict(frozen=True, validate_default=True, extra="forbid", serialize_by_alias=True)


class WithExtra(Serializable):
    """Base class for configurations with extra fields allowed."""

    model_config = ConfigDict(extra="allow")

    @property
    def model_extra(self) -> dict[str, Any]:
        """Get extra fields set during validation.

        Returns:
            A dictionary of extra fields, or `None` if `config.extra` is not set to `"allow"`.
        """
        return cast(dict[str, Any], self.__pydantic_extra__)


__all__ = ["Serializable", "WithExtra"]


def __dir__() -> list[str]:
    return get_default_dir(globals())
