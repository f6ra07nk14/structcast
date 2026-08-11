# StructCast — AI Agent Reference

> This document is designed for AI coding agents. For human developers, see [README.md](README.md).

## What This Project Does

StructCast turns **serializable config** (plain dicts/lists in YAML or JSON) into **live Python objects** through three composable modules — Instantiator, Specifier, and Template. No framework lock-in; everything stays serializable.

**Config is trusted input.** An `_addr_` is imported as written, so handing StructCast a config is equivalent to letting it execute code. Never load config from an untrusted source.

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
│   ├── base.py                 # Everything: SecuritySettings, configure_security(), validate_attribute(),
│   │                           #   import_from_address(), find_path(), load_yaml/dump_yaml, check_elements
│   ├── lazy_import.py          # DEFAULT_ALLOWED_DUNDERS, lazy module/attribute importers
│   ├── dataclasses.py          # Custom @dataclass (adds kw_only/slots on 3.10+)
│   └── types.py                # PathLike type alias
tests/
├── core/test_{instantiator,specifier,template}.py
├── utils/test_{base,lazy_import}.py
└── utils/__init__.py           # configure_security_context(), temporary_registered_dir()
examples/
├── 01-05                       # Single-module demos (instantiator, specifier, template, security, yaml)
└── 06-08                       # Cross-module integration pipelines (sensor, validation, multi-tenant)
```

## Data Flow — How the Modules Connect

```text
YAML config
  │  load_yaml_from_string()          ← utils/base.py (ruamel.yaml safe loader)
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

Every import and attribute access in this pipeline goes through `utils/base.py`.

## Custom Pattern Extension

StructCast's instantiation system is extensible via custom patterns. Create domain-specific patterns for operations not covered by the built-in set:

```python
from structcast.core.instantiator import BasePattern, PatternResult, register_pattern, validate_pattern_result
from pydantic import Field
from typing import Optional

class CustomPattern(BasePattern):
    """Your custom pattern."""
    param: str = Field(alias="_custom_")  # Must use alias
    
    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        # 1. Validate and extract context (enforces security)
        res_t, ptns, runs, depth, start = validate_pattern_result(result)
        
        # 2. Validate runs list
        if not runs:
            raise InstantiationError("No object to operate on.")
        
        # 3. Extract last run + remaining stack
        runs, last = runs[:-1], runs[-1]
        
        # 4. Process last run
        new_value = process(last, self.param)
        
        # 5. Return new PatternResult
        return res_t(patterns=ptns + [self], runs=runs + [new_value], depth=depth, start=start)

# Register before use
register_pattern(CustomPattern)

# Use in _obj_ chains
instantiate({"_obj_": [{"_addr_": "..."}, {"_custom_": "param"}]})
```

**Custom Pattern Contract:**

1. **Inherit from `BasePattern`** — frozen, extra='forbid', serialize_by_alias config inherited
2. **Use `Field(alias="_key_")`** — pattern keys must be aliases for Pydantic serialization
3. **Call `validate_pattern_result(result)`** — extracts (result_type, patterns, runs, depth, start) and enforces recursion/timeout limits
4. **Manipulate `runs` list** — last element is current object, earlier elements are history
5. **Return new `PatternResult`** — append self to `patterns`, append result to `runs`
6. **Register with `register_pattern()`** — adds pattern class to `_patterns` list in `core/instantiator.py`

Custom patterns are auto-discovered by `ObjectPattern.patterns` via `Union[tuple(_patterns + default_ptns)]` — no code changes needed after registration.

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
| Security       | `SecuritySettings` | `configure_security()` | `utils/base.py`     |
| Specifier      | `SpecSettings`     | `configure_spec()`     | `core/specifier.py` |
| Jinja/Template | `JinjaSettings`    | `configure_jinja()`    | `core/template.py`  |

**Critical for tests**: calling `configure_*()` with no arguments resets to defaults. Always restore after modification — use context managers in `tests/utils/__init__.py`.

## Security Enforcement Rules

**Trust model**: config is trusted input. There is no module allowlist or blocklist — `import_from_address("os.system")` succeeds and a YAML `!subprocess.Popen` tag imports that address on demand. Anyone who can supply a config can run code in the host process.

All dynamic imports flow through `utils/base.py → import_from_address()`, which enforces:

1. **Module path format** — each dotted part must be a Python identifier and must not be a dangerous dunder. Ordinary private module paths such as `numpy._core` are allowed.
2. **Attribute checks** — the target half of the address, and every `_attr_` path, go through `validate_attribute()`. `DEFAULT_DANGEROUS_DUNDERS` blocks `__subclasses__`, `__bases__`, `__globals__`, `__code__`, `__dict__`, `__class__`, `__mro__`, `__init__`, `__import__`. Non-ASCII, protected (`_foo`) and private (`__foo`) names are blocked by default and can be relaxed per call or globally.
3. **Module file loading** — `module_file` is resolved with `find_path()` (searching directories registered via `register_dir()`) and must have a `.py` suffix.

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
