# StructCast Development Guide

## Copilot Interaction Policy

- **ALWAYS respond in English**, regardless of the language used in the user's request
- Non-English requests should be understood and acknowledged, but all responses, explanations, plans, and code comments must be in English

## Architecture

StructCast converts serializable config (dicts/lists) into live Python objects through three core modules in `src/structcast/core/`:

- **Instantiator** (`instantiator.py`) — Pattern-based object construction. Patterns use alias keys: `_addr_` (import), `_attr_` (attribute access), `_call_` (invocation), `_bind_` (partial application), composed inside `_obj_` lists. All patterns extend `BasePattern(BaseModel, ABC)` with a `build(result) -> PatternResult` method. Entry point: `instantiate(cfg)`.
- **Specifier** (`specifier.py`) — Dot-notation path access and data reshaping. Uses `SpecIntermediate` for parsed specs, `FlexSpec`/`RawSpec`/`ObjectSpec` for construction. Extensible via `register_resolver()` and `register_accesser()`. Entry point: `construct(data, spec)`.
- **Template** (`template.py`) — Jinja2 templates embedded in data structures. `JinjaTemplate`, `JinjaYamlTemplate`, `JinjaJsonTemplate` wrap templates with optional pipe chains. Templates run in `ImmutableSandboxedEnvironment` by default.

Shared utilities live in `src/structcast/utils/`:

- **Base** (`base.py`) — `import_from_address()`, `validate_attribute()`, `find_path()`, `load_yaml()`, `check_elements()`, plus `SecuritySettings` / `configure_security()`. Attribute-access validation (dunder, ASCII, protected/private) lives here; there is no import allowlist or blocklist.
- **Types/Dataclasses** — `PathLike` type alias; custom `@dataclass` wrapper adding `kw_only=True, slots=True` on Python 3.10+.

## Key Patterns & Conventions

- **Pydantic v2 models with aliases**: Pattern classes use `Field(alias="_addr_")` etc. Always use `model_validate()` not direct constructors in tests. Config: `frozen=True, extra="forbid", serialize_by_alias=True`.
- **Global settings via `configure_*` functions**: Each subsystem (`security`, `spec`, `jinja`) uses a module-level `_*_settings` dataclass instance mutated by `configure_*()`. Tests must restore defaults after modification.
- **Custom `@dataclass` wrapper** (`utils/dataclasses.py`): Use `from structcast.utils.dataclasses import dataclass` instead of `dataclasses.dataclass` — it adds `kw_only`/`slots` on 3.10+.
- **Recursion safety**: `instantiate()` and `convert_spec()` enforce `MAX_RECURSION_DEPTH` (100) and `MAX_RECURSION_TIME` (30s) from `core/constants.py`. Internal params `__depth__` and `__start__` must not be set by callers.
- **Google-style docstrings**: Enforced by ruff rule `D` with `convention = "google"`.
- **Python 3.9 compatibility**: Target is `py39`. Use `from __future__ import annotations` or `typing_extensions` for newer typing features. No walrus operators in hot paths; `Union[X, Y]` over `X | Y`.

## Development Workflow

```bash
# Setup
uv sync --group dev

# Run tests (includes doctests + coverage)
pytest                    # runs tests/ and src/structcast/ (doctests)

# Lint & format
ruff check src tests      # lint
ruff format src tests     # format

# Type checking
mypy src && mypy tests

# Full matrix (Python 3.9–3.13 × Pydantic 2.11.x–2.12.x)
tox
```

pytest is configured with `--doctest-modules --cov src/` and runs against both `tests/` and `src/structcast/`.

## Testing Conventions

- Tests mirror source layout: `tests/core/test_instantiator.py` ↔ `src/structcast/core/instantiator.py`.
- Use context managers from `tests/utils/__init__.py` to temporarily modify global state:
  - `configure_security_context(protected_member_check=..., ascii_check=...)` — resets security after block.
  - `temporary_registered_dir(path)` — registers/unregisters import directory.
- Test classes group by concern (e.g., `TestPatternSchemas`, `TestInstantiation`). Use `@pytest.mark.parametrize` for variant coverage.
- Doctests in source modules are part of the test suite — keep examples in docstrings runnable.

## Security Model

Config is trusted input: an address is imported as written, so supplying a config is equivalent to executing code. There is no module allowlist or blocklist. When adding new functionality:
- Never bypass `import_from_address()` in `utils/base.py` — it is the single place module paths and attribute targets are validated.
- Attribute access (the target half of an address and every `_attr_` path) is validated against `DEFAULT_DANGEROUS_DUNDERS` and ASCII/protected/private member checks.
- Do not reintroduce import allow/block lists; see `docs/adr/0001-trusted-input-security-model.md`.
