---
name: structcast
description: Declarative data orchestration library that converts serializable config (dicts/lists in YAML or JSON) into live Python objects. Use this skill when working with StructCast's pattern-based object instantiation (_obj_, _addr_, _call_, _bind_, _attr_), dot-notation data access and reshaping (FlexSpec, RawSpec, convert_spec, construct), Jinja2 template rendering embedded in data structures (_jinja_, _jinja_yaml_, _jinja_json_), security configuration for dynamic imports, or building end-to-end config-driven pipelines combining these modules.
---

# StructCast

Capability reference for each module, with entry points and key APIs.

## Object Instantiation

**Module**: `structcast.core.instantiator`

Create live Python objects from serializable dict/list patterns without writing imports or factory code.

| Capability          | Entry Point                                                   | Example                        |
| ------------------- | ------------------------------------------------------------- | ------------------------------ |
| Import by address   | `instantiate({"_obj_": [{"_addr_": "collections.Counter"}]})` | Returns `Counter` class        |
| Call with kwargs    | `{"_call_": {"key": "val"}}` inside `_obj_`                   | `Counter(key=val)`             |
| Call with args      | `{"_call_": [[1, 2, 3]]}` inside `_obj_`                      | `Counter([1, 2, 3])`           |
| Partial application | `{"_bind_": {"base": 16}}` inside `_obj_`                     | `partial(int, base=16)`        |
| Attribute access    | `{"_attr_": "real"}` inside `_obj_`                           | `obj.real`                     |
| Chain operations    | `{"_obj_": [addr, attr, call]}`                               | Sequential build pipeline      |
| Recursive walk      | `instantiate(nested_dict_with_patterns)`                      | Resolves patterns at any depth |
| File-based import   | `{"_addr_": "func", "_file_": "/path/to/mod.py"}`             | Load from local `.py` file     |

**Key classes**: `BasePattern` (ABC), `AddressPattern`, `AttributePattern`, `CallPattern`, `BindPattern`, `ObjectPattern`, `PatternResult`

**Constraints**: Max recursion depth 100, max time 30s. All imports validated by security layer.

---

## Data Access & Reshaping

**Module**: `structcast.core.specifier`

Navigate nested data with dot-notation paths and construct new structures from specs.

| Capability             | Entry Point                                             | Example                                     |
| ---------------------- | ------------------------------------------------------- | ------------------------------------------- |
| Parse spec string      | `convert_spec("a.b.0.c")`                               | `SpecIntermediate(source, ("a","b",0,"c"))` |
| Access nested path     | `access(data, ("a", "b", 0))`                           | Returns `data["a"]["b"][0]`                 |
| Construct from spec    | `construct(data, converted_spec)`                       | Builds new dict from spec + data            |
| Constant value         | `convert_spec("constant: 42")`                          | Returns literal `"42"`                      |
| Skip entry             | `convert_spec("skip:")`                                 | Omits key from output                       |
| Placeholder (deferred) | `convert_spec("placeholder: a.b")`                      | Multi-stage resolution                      |
| FlexSpec (unified)     | `FlexSpec.model_validate({"key": "path"})`              | Auto-dispatches RawSpec/ObjectSpec          |
| FlexSpec with objects  | `FlexSpec.model_validate({"_obj_": [...]})`             | Inline instantiation                        |
| Copy semantics         | `configure_spec(return_type=ReturnType.DEEP_COPY)`      | Control reference/copy behavior             |
| Custom resolver        | `register_resolver("env", lambda k: os.environ.get(k))` | Extend spec language                        |
| Custom accesser        | `register_accesser(MyType, my_accessor_fn)`             | Access custom data types                    |
| BaseModel access       | Enabled by default (`support_basemodel=True`)           | Navigate Pydantic models                    |
| Attribute access       | Enabled by default (`support_attribute=True`)           | `getattr()` on objects                      |
| Post-processing pipe   | `WithPipe` base, `_pipe_` alias                         | Chain transformations after spec            |

**Key classes**: `SpecIntermediate`, `RawSpec`, `ObjectSpec`, `FlexSpec`, `WithPipe`, `SpecSettings`, `ReturnType`

---

## Template Rendering

**Module**: `structcast.core.template`

Embed Jinja2 templates inside data structures for dynamic configuration generation.

| Capability              | Entry Point                                                     | Example                           |
| ----------------------- | --------------------------------------------------------------- | --------------------------------- |
| Render string           | `JinjaTemplate.model_validate({"_jinja_": "Hello {{ name }}"})` | Returns rendered string           |
| Render → YAML           | `JinjaYamlTemplate.model_validate({"_jinja_yaml_": yaml_str})`  | Renders then parses YAML          |
| Render → JSON           | `JinjaJsonTemplate.model_validate({"_jinja_json_": json_str})`  | Renders then parses JSON          |
| Expand entire structure | `extend_structure(data, template_kwargs={...})`                 | Recursive template resolution     |
| Template groups         | `{"_jinja_group_": "group_name"}` alongside template            | Scoped variable sets              |
| Mapping pattern         | `_jinja_yaml_` as key in dict → merge into parent               | Dynamic key injection             |
| Sequence pattern        | `{"_jinja_yaml_": ...}` in list → splice into list              | Dynamic list expansion            |
| Post-processing         | `_jinja_pipe_` field                                            | Chain ObjectPatterns after render |
| Sandboxed execution     | `ImmutableSandboxedEnvironment` (default)                       | Safe by default                   |
| Configurable env        | `configure_jinja(environment_type=...)`                         | Override sandbox settings         |

**Key classes**: `JinjaTemplate`, `JinjaYamlTemplate`, `JinjaJsonTemplate`, `JinjaSettings`

---

## Security Enforcement

**Module**: `structcast.utils.security`

Validate all dynamic imports, attribute access, and file paths.

| Capability            | Entry Point                                                    | Example                               |
| --------------------- | -------------------------------------------------------------- | ------------------------------------- |
| Configure security    | `configure_security(blocked_modules=..., allowed_modules=...)` | Global settings                       |
| Block modules         | `DEFAULT_BLOCKED_MODULES`                                      | `os`, `subprocess`, `pickle`, etc.    |
| Allow modules         | `DEFAULT_ALLOWED_MODULES`                                      | `builtins.int`, `math.sqrt`, etc.     |
| Block dunders         | `DEFAULT_DANGEROUS_DUNDERS`                                    | `__subclasses__`, `__globals__`, etc. |
| Validate import       | `validate_import(module_name, target)`                         | Checks blocklist + allowlist          |
| Validate attribute    | `validate_attribute("obj.method")`                             | Checks dunders + protected/private    |
| Check file path       | `check_path(path)`                                             | Hidden dir + working dir checks       |
| Register import dir   | `register_dir(path)` / `unregister_dir(path)`                  | Extend allowed file search paths      |

**Key classes**: `SecuritySettings`, `SecurityError`

---

## YAML Operations

**Module**: `structcast.utils.base` (delegates to `security.py`)

| Capability              | Entry Point                                                          |
| ----------------------- | -------------------------------------------------------------------- |
| Load YAML file          | `load_yaml(path)` — path-validated                                   |
| Load YAML string        | `load_yaml_from_string(yaml_str)`                                    |
| Load YAML stream        | `load_yaml_from_stream(stream)`                                      |
| Dump to YAML file       | `dump_yaml(data, path)` — path-validated                             |
| Dump to YAML string     | `dump_yaml_to_string(data)`                                          |
| Security-checked import | `import_from_address(addr)`                                          |
| Normalize to list       | `check_elements(value)` — `None`→`[]`, scalar→`[scalar]`, seq→`list` |

---

## Integration Pipeline

**Pattern**: Combine all modules into an end-to-end config-driven workflow.

```
load_yaml_from_string → extend_structure → FlexSpec → instantiate → process → JinjaTemplate
```

| Phase   | Module              | Function                                                      |
| ------- | ------------------- | ------------------------------------------------------------- |
| Parse   | `utils/base`        | `load_yaml_from_string(yaml)`                                 |
| Expand  | `core/template`     | `extend_structure(data, template_kwargs={"default": params})` |
| Extract | `core/specifier`    | `FlexSpec.model_validate(spec)(expanded)`                     |
| Build   | `core/instantiator` | `instantiate(obj_pattern)`                                    |
| Process | (user code)         | Apply built objects to extracted data                         |
| Report  | `core/template`     | `JinjaTemplate.model_validate({...})(**data)`                 |

**Signature pattern — two-stage FlexSpec**:

1. First FlexSpec reads config to extract dot-path strings
2. Second FlexSpec uses those extracted paths as specs against a different data source

See `examples/06_sensor_dashboard.py`, `examples/07_validation_pipeline.py`, `examples/08_multi_tenant_analytics.py`.

---

## Testing

**Module**: `tests/`

| Capability                  | Entry Point                                                            |
| --------------------------- | ---------------------------------------------------------------------- |
| Run all tests + doctests    | `pytest` (configured in `pyproject.toml`)                              |
| Temporary security config   | `configure_security_context(allowed_modules=..., blocked_modules=...)` |
| Temporary import dir        | `temporary_registered_dir(path)`                                       |
| Construct patterns in tests | Always use `Model.model_validate({...})`, never direct constructors    |
| Full compatibility matrix   | `tox` — Python 3.9–3.13 × Pydantic 2.11.x–2.12.x                       |
