# StructCast — AI Agent Reference

> This document is designed for AI coding agents. For human developers, see [README.md](README.md).

## What This Project Does

StructCast turns **serializable config** (plain dicts/lists in YAML or JSON) into **live Python objects** through three composable modules — Instantiator, Specifier, and Template — all gated by a **mandatory security layer**. No framework lock-in; everything stays serializable.

## Repository Map

```text
src/structcast/
├── core/                       # The three pillars
│   ├── instantiator.py         # _obj_ / _addr_ / _call_ / _bind_ / _attr_ patterns → live objects
│   ├── specifier.py            # Dot-path access + FlexSpec / RawSpec / ObjectSpec → data reshaping
│   ├── template.py             # Jinja2 templates (_jinja_ / _jinja_yaml_ / _jinja_json_) → dynamic config
│   ├── constants.py            # MAX_RECURSION_DEPTH (100), MAX_RECURSION_TIME (30s), SPEC_FORMAT
│   └── exceptions.py           # SpecError, InstantiationError, StructuredExtensionError
├── utils/
│   ├── security.py             # SecuritySettings, configure_security(), import_from_address() (real impl)
│   ├── base.py                 # Public thin wrappers: import_from_address, load_yaml, dump_yaml, check_elements
│   ├── constants.py            # DEFAULT_BLOCKED_MODULES, DEFAULT_ALLOWED_MODULES, DEFAULT_DANGEROUS_DUNDERS
│   ├── dataclasses.py          # Custom @dataclass (adds kw_only/slots on 3.10+)
│   └── types.py                # PathLike type alias
tests/
├── core/test_{instantiator,specifier,template}.py
├── utils/{test_base,test_security}.py
└── utils/__init__.py           # configure_security_context(), temporary_registered_dir()
examples/
├── 01-05                       # Single-module demos (instantiator, specifier, template, security, yaml)
└── 06-08                       # Cross-module integration pipelines (sensor, validation, multi-tenant)
```

## Data Flow — How the Modules Connect

```text
YAML config
  │  load_yaml_from_string()          ← utils/base.py (delegates to security.py)
  ▼
Plain dict/list
  │  extend_structure()               ← template.py: resolves _jinja_yaml_ / _jinja_json_ / _jinja_
  ▼
Expanded dict/list
  │  FlexSpec.model_validate(spec)    ← specifier.py: convert dot-paths to SpecIntermediate
  │  spec(data)                       ← specifier.py: construct() navigates + reshapes
  ▼
Extracted config sections
  │  instantiate(pattern)             ← instantiator.py: builds live objects from _obj_ patterns
  ▼
Live Python objects
  │  (your processing code)
  ▼
JinjaTemplate(...)(**kwargs)          ← template.py: render final output
```

Every import/attribute access in this pipeline passes through `utils/security.py`.

## Pattern Alias Quick Reference

### Instantiator Patterns (inside `_obj_` lists)

| Alias    | Class              | What it does                                                                |
| -------- | ------------------ | --------------------------------------------------------------------------- |
| `_addr_` | `AddressPattern`   | Import by dotted path: `{"_addr_": "collections.Counter"}`                  |
| `_attr_` | `AttributePattern` | Attribute access: `{"_attr_": "real"}`                                      |
| `_call_` | `CallPattern`      | Invoke callable: `{"_call_": {"key": "val"}}` or `{"_call_": [arg1, arg2]}` |
| `_bind_` | `BindPattern`      | `functools.partial`: `{"_bind_": {"base": 16}}`                             |
| `_obj_`  | `ObjectPattern`    | Chain patterns: `{"_obj_": [addr, call]}`                                   |

### Template Aliases

| Alias           | Class                | Output                                         |
| --------------- | -------------------- | ---------------------------------------------- |
| `_jinja_`       | `JinjaTemplate`      | Raw rendered string                            |
| `_jinja_yaml_`  | `JinjaYamlTemplate`  | Rendered → parsed as YAML                      |
| `_jinja_json_`  | `JinjaJsonTemplate`  | Rendered → parsed as JSON                      |
| `_jinja_pipe_`  | (field on templates) | Post-processing pipeline (ObjectPattern list)  |
| `_jinja_group_` | (field on templates) | Template group selector for `extend_structure` |

### Specifier Resolvers

| Resolver    | Syntax               | Behavior                                    |
| ----------- | -------------------- | ------------------------------------------- |
| Source      | `"a.b.0.c"`          | Navigate nested path in source data         |
| Constant    | `"constant: value"`  | Return literal value                        |
| Skip        | `"skip:"`            | Omit this entry from output                 |
| Placeholder | `"placeholder: ..."` | Deferred resolution (multi-stage construct) |

### Spec Construction Classes

| Class        | Alias    | Purpose                                                                              |
| ------------ | -------- | ------------------------------------------------------------------------------------ |
| `RawSpec`    | `_spec_` | Path-based access with optional kwargs                                               |
| `ObjectSpec` | `_spec_` | Instantiates objects from `_obj_` patterns                                           |
| `FlexSpec`   | `_spec_` | Auto-dispatches: strings→RawSpec, `_obj_`→ObjectSpec, dicts/lists→recursive FlexSpec |
| `WithPipe`   | `_pipe_` | Base class adding post-construction casting pipeline                                 |

## Global Settings Architecture

Three subsystems each have a module-level settings dataclass instance mutated by a `configure_*()` function:

| Subsystem      | Settings class     | Function               | File                |
| -------------- | ------------------ | ---------------------- | ------------------- |
| Security       | `SecuritySettings` | `configure_security()` | `utils/security.py` |
| Specifier      | `SpecSettings`     | `configure_spec()`     | `core/specifier.py` |
| Jinja/Template | `JinjaSettings`    | `configure_jinja()`    | `core/template.py`  |

**Critical for tests**: calling `configure_*()` with no arguments resets to defaults. Always restore after modification — use context managers in `tests/utils/__init__.py`.

## Security Enforcement Rules

All dynamic imports flow through `utils/security.py → import_from_address()`:

1. **Blocklist** — `DEFAULT_BLOCKED_MODULES` in `utils/constants.py` blocks `os`, `subprocess`, `sys`, `pickle`, `socket`, `ctypes`, `importlib`, `pathlib`, `io`, `inspect`, `threading`, `multiprocessing`, `structcast.utils`, and more.
2. **Allowlist** — `DEFAULT_ALLOWED_MODULES` whitelists specific safe members of `builtins`, `collections`, `datetime`, `math`, `json`, `functools`, `itertools`, `operator`, `string`, `base64`, `enum`, `uuid`, `decimal`, `random`, `secrets`, `html`, `urllib.parse`, `ipaddress`, `time`, `structcast.utils.base`.
3. **Attribute checks** — `DEFAULT_DANGEROUS_DUNDERS` blocks `__subclasses__`, `__bases__`, `__globals__`, `__code__`, `__dict__`, `__class__`, `__mro__`, `__init__`, `__import__`. Protected (`_foo`) and private (`__foo`) members blocked by default.
4. **Path checks** — hidden directory detection, working directory containment, `.py`-only module loading.

**Rule**: Never bypass `import_from_address()` for any dynamic import.

## Development Commands

```bash
uv sync --group dev                # Setup
pytest                             # Tests + doctests + coverage (tests/ + src/structcast/)
ruff check src tests               # Lint
ruff format src tests              # Format
mypy src && mypy tests             # Type check
tox                                # Full matrix: Python 3.9–3.13 × Pydantic 2.11.x–2.12.x
```

## Code Conventions

- **Python 3.9 target** — use `Union[X, Y]` not `X | Y`; use `typing_extensions` or `from __future__ import annotations` for newer features
- **Pydantic v2 with aliases** — patterns use `Field(alias="_addr_")`, model config: `frozen=True, extra="forbid", serialize_by_alias=True`. Always construct via `model_validate()` in tests
- **Google-style docstrings** — enforced by ruff rule `D` with `convention = "google"`
- **Custom `@dataclass`** — always use `from structcast.utils.dataclasses import dataclass` (adds `kw_only=True, slots=True` on 3.10+)
- **Recursion guards** — `__depth__` and `__start__` params on `instantiate()`, `convert_spec()`, `extend_structure()` are internal — never set from external code
- **Test layout** — mirrors source: `tests/core/test_instantiator.py` ↔ `src/structcast/core/instantiator.py`
- **Test isolation** — use `configure_security_context()` and `temporary_registered_dir()` from `tests/utils/__init__.py`
- **Doctests are tests** — examples in docstrings run as part of pytest suite (`--doctest-modules`)

## Key Integration Example (08_multi_tenant_analytics.py pattern)

```python
# 1. Load + expand
raw = load_yaml_from_string(yaml_config)
expanded = extend_structure(raw, template_kwargs={"default": runtime_params})

# 2. Extract config
config_spec = FlexSpec.model_validate({
    "tools": "platform.aggregations",
    "tenants": "platform.tenants",
    "report": "platform.report_template",
})
cfg = config_spec(expanded)

# 3. Build tools from _obj_ patterns
tools = [instantiate(dict(t["tool"])) for t in cfg["tools"]]

# 4. Chained FlexSpec — config-defined paths extract from raw data
for tenant_name, tenant_cfg in cfg["tenants"].items():
    data_spec = FlexSpec.model_validate(dict(tenant_cfg))
    extracted = data_spec(warehouse_data)
    # 5. Apply tools + render report with JinjaTemplate
```

This "two-stage FlexSpec" (config paths → data extraction) is the project's signature integration pattern.
