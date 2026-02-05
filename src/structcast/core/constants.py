"""Constants for StructCast core."""

MAX_INSTANTIATION_DEPTH = 100
"""Maximum recursion depth for nested instantiation."""

MAX_INSTANTIATION_TIME = 30
"""Maximum time (in seconds) for a single instantiation operation."""

SPEC_FORMAT = "__spec_{resolver}__"
"""Specification format string."""

SPEC_SOURCE = SPEC_FORMAT.format(resolver="source")
"""Specification source identifier."""
