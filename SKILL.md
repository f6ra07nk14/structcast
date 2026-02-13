---
name: structcast
description: StructCast converts YAML/JSON configuration into live Python objects with three core capabilities - (1) pattern-based instantiation that builds objects from dict/list patterns without writing factory code, (2) dot-notation data access and reshaping for navigating nested structures, and (3) Jinja2 template rendering embedded in data structures for dynamic config generation. Use this when working with config-driven pipelines, object instantiation patterns (_obj_, _addr_, _call_, _bind_, _attr_), specifier-based data extraction (FlexSpec, RawSpec, convert_spec, construct), or template expansion (_jinja_, _jinja_yaml_, _jinja_json_). All operations run through a mandatory security layer with module allowlists/blocklists.
---

# StructCast

Capability reference for each module, with entry points and key APIs.

## Quick Reference

**Instantiation**: `instantiate({"_obj_": [{"_addr_": "module.Class"}]})` 
**Data Access**: `construct(data, convert_spec({"key": "path.to.data"}))` 
**Templates**: `extend_structure(config, template_kwargs={...})` 
**Security**: `configure_security(allowed_modules={...})`

## Common Workflows

### Workflow 1: Simple Object Instantiation from YAML

```python
from structcast.core.instantiator import instantiate
from structcast.utils.base import load_yaml_from_string

config = """
processor:
  _obj_:
    - _addr_: collections.Counter
    - _call_:
        - [1, 2, 2, 3, 3, 3]
"""
data = load_yaml_from_string(config)
counter = instantiate(data["processor"])
# Result: Counter({3: 3, 2: 2, 1: 1})
```

### Workflow 2: Extract and Reshape Nested Data

```python
from structcast.core.specifier import FlexSpec

data = {
    "users": [
        {"profile": {"name": "Alice", "age": 30}},
        {"profile": {"name": "Bob", "age": 25}}
    ]
}

spec = FlexSpec.model_validate({
    "names": "users.*.profile.name",
    "ages": "users.*.profile.age"
})
result = spec(data)
# Result: {"names": ["Alice", "Bob"], "ages": [30, 25]}
```

### Workflow 3: Config-Driven Pipeline with Templates

```python
from structcast.core.template import extend_structure
from structcast.core.specifier import FlexSpec
from structcast.core.instantiator import instantiate

# 1. Load config with templates
config_with_templates = {
    "processor": {
        "_jinja_yaml_": """
        _obj_:
          - _addr_: "{{ processor_class }}"
          - _call_: {{ processor_kwargs | tojson }}
        """
    },
    "input_path": "data.{{ env }}.values"
}

# 2. Expand templates
expanded = extend_structure(config_with_templates, template_kwargs={
    "default": {"processor_class": "int", "processor_kwargs": {}, "env": "prod"}
})

# 3. Extract data paths and build objects
spec = FlexSpec.model_validate({"input": expanded["input_path"]})
processor = instantiate(expanded["processor"])

# 4. Apply to data
data = {"data": {"prod": {"values": ["123", "456"]}}}
values = spec(data)["input"]
result = [processor(v) for v in values]
# Result: [123, 456]
```

## Exceptions

**Module**: `structcast.core.exceptions`

Handle typed exceptions from each module:

| Exception | Raised By | Common Causes |
| -- | -- | -- |
| `SpecError` | `specifier.py` | Invalid spec syntax, access failures, resolver errors |
| `InstantiationError` | `instantiator.py` | Pattern validation errors, recursion/timeout limits |
| `StructuredExtensionError` | `template.py` | Template rendering failures, invalid extension operations |
| `SecurityError` | `utils/security.py` | Blocked imports, dangerous attributes, path violations |

## Object Instantiation

**Module**: `structcast.core.instantiator`

Create live Python objects from serializable dict/list patterns without writing imports or factory code.

| Capability | Entry Point | Example |
| -- | -- | -- |
| Import by address | `instantiate({"_obj_": [{"_addr_": "collections.Counter"}]})` | Returns `Counter` class |
| Call with kwargs | `{"_call_": {"key": "val"}}` inside `_obj_` | `Counter(key=val)` |
| Call with args | `{"_call_": [[1, 2, 3]]}` inside `_obj_` | `Counter([1, 2, 3])` |
| Partial application | `{"_bind_": {"base": 16}}` inside `_obj_` | `partial(int, base=16)` |
| Attribute access | `{"_attr_": "real"}` inside `_obj_` | `obj.real` |
| Chain operations | `{"_obj_": [addr, attr, call]}` | Sequential build pipeline |
| Recursive walk | `instantiate(nested_dict_with_patterns)` | Resolves patterns at any depth |
| File-based import | `{"_addr_": "func", "_file_": "/path/to/mod.py"}` | Load from local `.py` file |
| Custom patterns | `register_pattern(YourPattern)` then use `{"_your_key_": ...}` | Extend with domain-specific patterns |

**Key classes**: `BasePattern` (ABC), `AddressPattern`, `AttributePattern`, `CallPattern`, `BindPattern`, `ObjectPattern`, `PatternResult`

**Custom Pattern Extension**:

Create domain-specific patterns by inheriting from `BasePattern`:

```python
from structcast.core.instantiator import BasePattern, PatternResult, register_pattern, validate_pattern_result
from pydantic import Field
from typing import Optional

class MultiplyPattern(BasePattern):
    factor: int = Field(alias="_multiply_")  # Must use Field(alias=...)
    
    def build(self, result: Optional[PatternResult] = None) -> PatternResult:
        res_t, ptns, runs, depth, start = validate_pattern_result(result)  # Required
        if not runs:
            raise InstantiationError("No value to multiply.")
        runs, last = runs[:-1], runs[-1]  # Extract last object from stack
        new_value = last * self.factor
        return res_t(patterns=ptns + [self], runs=runs + [new_value], depth=depth, start=start)

register_pattern(MultiplyPattern)  # Register globally
instantiate({"_obj_": [{"_addr_": "int"}, {"_call_": ["10"]}, {"_multiply_": 3}]})  # → 30
```

**Requirements**: Inherit `BasePattern`, use `Field(alias=...)`, implement `build()`, call `validate_pattern_result()`, return new `PatternResult` with updated `patterns` and `runs` lists. All security constraints (recursion, timeout) apply automatically.

**Constraints**: Max recursion depth 100, max time 30s. All imports validated by security layer.

## Data Access & Reshaping

**Module**: `structcast.core.specifier`

Navigate nested data with dot-notation paths and construct new structures from specs.

| Capability | Entry Point | Example |
| -- | -- | -- |
| Parse spec string | `convert_spec("a.b.0.c")` | `SpecIntermediate(source, ("a","b",0,"c"))` |
| Access nested path | `access(data, ("a", "b", 0))` | Returns `data["a"]["b"][0]` |
| Construct from spec | `construct(data, converted_spec)` | Builds new dict from spec + data |
| Constant value | `convert_spec("constant: 42")` | Returns literal `"42"` |
| Skip entry | `convert_spec("skip:")` | Omits key from output |
| Placeholder (deferred) | `convert_spec("placeholder: a.b")` | Multi-stage resolution |
| FlexSpec (unified) | `FlexSpec.model_validate({"key": "path"})` | Auto-dispatches RawSpec/ObjectSpec |
| FlexSpec with objects | `FlexSpec.model_validate({"_obj_": [...]})` | Inline instantiation |
| Copy semantics | `configure_spec(return_type=ReturnType.DEEP_COPY)` | Control reference/copy behavior |
| Custom resolver | `register_resolver("env", lambda k: os.environ.get(k))` | Extend spec language |
| Custom accessor | `register_accesser(MyType, my_accessor_fn)` | Access custom data types |
| BaseModel access | Enabled by default (`support_basemodel=True`) | Navigate Pydantic models |
| Attribute access | Enabled by default (`support_attribute=True`) | `getattr()` on objects |
| Post-processing pipe | `WithPipe` base, `_pipe_` alias | Chain transformations after spec |
| Configure settings | `configure_spec(return_type=..., support_basemodel=..., support_attribute=..., raise_error=...)` | Global spec behavior |

**Key classes**: `SpecIntermediate`, `RawSpec`, `ObjectSpec`, `FlexSpec`, `WithPipe`, `SpecSettings`, `ReturnType`

**FlexSpec Auto-Dispatch Rules**:

- String/int/float/bool values → `RawSpec` (dot-path navigation)
- Dicts with `_obj_` key → `ObjectSpec` (instantiation)
- Dicts without patterns → recursive `FlexSpec` on values
- Lists/tuples → recursive `FlexSpec` on elements
- Explicit `_spec_` key → manual control over dispatch

**Pipe Usage Pattern**:

```python
# Extract data then apply transformations
spec = FlexSpec.model_validate({
    "sorted_users": {
        "_spec_": "data.users",
        "_pipe_": [
            {"_obj_": [{"_addr_": "sorted"}, {"_call_": {"key": {"_obj_": [{"_addr_": "operator.itemgetter"}, {"_call_": ["name"]}]}}}]},
            {"_obj_": [{"_addr_": "list"}, {"_call_": []}]}
        ]
    }
})

# Common pipe patterns:
# - Type casting: {"_obj_": [{"_addr_": "int"}, {"_call_": []}]}
# - Sorting: {"_obj_": [{"_addr_": "sorted"}, {"_call_": {}}]}
# - Filtering: {"_obj_": [{"_addr_": "filter"}, {"_bind_": {"function": ...}}, {"_call_": []}]}
```

## Template Rendering

**Module**: `structcast.core.template`

Embed Jinja2 templates inside data structures for dynamic configuration generation.

| Capability | Entry Point | Example |
| -- | -- | -- |
| Render string | `JinjaTemplate.model_validate({"_jinja_": "Hello {{ name }}"})` | Returns rendered string |
| Render → YAML | `JinjaYamlTemplate.model_validate({"_jinja_yaml_": yaml_str})` | Renders then parses YAML |
| Render → JSON | `JinjaJsonTemplate.model_validate({"_jinja_json_": json_str})` | Renders then parses JSON |
| Expand entire structure | `extend_structure(data, template_kwargs={...})` | Recursive template resolution |
| Template groups | `{"_jinja_group_": "group_name"}` alongside template | Scoped variable sets |
| Mapping pattern | `_jinja_yaml_` as key in dict → merge into parent | Dynamic key injection |
| Sequence pattern | `{"_jinja_yaml_": ...}` in list → splice into list | Dynamic list expansion |
| Post-processing | `_jinja_pipe_` field | Chain ObjectPatterns after render |
| Sandboxed execution | `ImmutableSandboxedEnvironment` (default) | Safe by default |
| Configure environment | `configure_jinja(environment_type=..., undefined_type=..., trim_blocks=..., lstrip_blocks=..., extensions=...)` | Override Jinja settings |

**Key classes**: `JinjaTemplate`, `JinjaYamlTemplate`, `JinjaJsonTemplate`, `JinjaSettings`

**JinjaSettings Configuration**:

- `environment_type`: Jinja environment class (default: `ImmutableSandboxedEnvironment`)
- `undefined_type`: How to handle undefined variables (default: `StrictUndefined`)
- `trim_blocks`: Remove first newline after block (default: `True`)
- `lstrip_blocks`: Strip leading spaces before blocks (default: `True`)
- `extensions`: List of Jinja extensions (default: `["jinja2.ext.loopcontrols"]`)

## Security Enforcement

**Module**: `structcast.utils.security`

Validate all dynamic imports, attribute access, and file paths.

| Capability | Entry Point | Example |
| -- | -- | -- |
| Configure security | `configure_security(blocked_modules=..., allowed_modules=...)` | Global settings |
| Block modules | `DEFAULT_BLOCKED_MODULES` | `os`, `subprocess`, `pickle`, etc. |
| Allow modules | `DEFAULT_ALLOWED_MODULES` | `builtins.int`, `math.sqrt`, etc. |
| Block dunders | `DEFAULT_DANGEROUS_DUNDERS` | `__subclasses__`, `__globals__`, etc. |
| Validate import | `validate_import(module_name, target)` | Checks blocklist + allowlist |
| Validate attribute | `validate_attribute("obj.method")` | Checks dunders + protected/private |
| Check file path | `check_path(path)` | Hidden dir + working dir checks |
| Register import dir | `register_dir(path)` / `unregister_dir(path)` | Extend allowed file search paths |

**Key classes**: `SecuritySettings`, `SecurityError`

**SecuritySettings Fields**:

- `blocked_modules: set[str]` — Module names to block (default: `DEFAULT_BLOCKED_MODULES`)
- `allowed_modules: dict[str, Optional[set[Optional[str]]]]` — Allowlist with specific members
  - `None` value → disable allowlist for that module
  - `set` value → only listed members allowed
  - `None` in set → all members allowed
- `dangerous_dunders: set[str]` — Blocked dunder attributes (default: `DEFAULT_DANGEROUS_DUNDERS`)
- `ascii_check: bool` — Block non-ASCII attribute names (default: `True`)
- `protected_member_check: bool` — Block `_protected` members (default: `True`)
- `private_member_check: bool` — Block `__private` members (default: `True`)
- `hidden_check: bool` — Block paths with hidden directories (default: `True`)
- `working_dir_check: bool` — Enforce working directory containment (default: `True`)

## YAML Operations

**Module**: `structcast.utils.base` (delegates to `security.py`)

| Capability | Entry Point |
| -- | -- |
| Load YAML file | `load_yaml(path)` — path-validated, uses `ruamel.yaml` |
| Load YAML string | `load_yaml_from_string(yaml_str)` — safe YAML parsing |
| Dump to YAML file | `dump_yaml(data, path)` — path-validated, preserves formatting |
| Dump to YAML string | `dump_yaml_to_string(data)` — serialize to YAML string |
| Security-checked import | `import_from_address(addr)` — validates then imports module/attr |
| Normalize to list | `check_elements(value)` — `None`→`[]`, scalar→`[scalar]`, seq→`list` |
| Unroll call arguments | `unroll_call(args, kwargs)` — normalize to `(*args, **kwargs)` tuple |

## Integration Pipeline

**Pattern**: Combine all modules into an end-to-end config-driven workflow.

```
load_yaml_from_string → extend_structure → FlexSpec → instantiate → process → JinjaTemplate
```

| Phase | Module | Function |
| -- | -- | -- |
| Parse | `utils/base` | `load_yaml_from_string(yaml)` |
| Expand | `core/template` | `extend_structure(data, template_kwargs={"default": params})` |
| Extract | `core/specifier` | `FlexSpec.model_validate(spec)(expanded)` |
| Build | `core/instantiator` | `instantiate(obj_pattern)` |
| Process | (user code) | Apply built objects to extracted data |
| Report | `core/template` | `JinjaTemplate.model_validate({...})(**data)` |

**Signature pattern — two-stage FlexSpec**:

1. First FlexSpec reads config to extract dot-path strings
2. Second FlexSpec uses those extracted paths as specs against a different data source

See `examples/06_sensor_dashboard.py`, `examples/07_validation_pipeline.py`, `examples/08_multi_tenant_analytics.py`.

## Troubleshooting

### Common Errors

**`SecurityError: Module 'X' is blocked`**
- **Cause**: Importing from a blocked module (e.g., `os`, `subprocess`)
- **Solution**: Either use an allowed alternative or configure security with `configure_security(blocked_modules=...)`

**`InstantiationError: Maximum recursion depth exceeded`**
- **Cause**: Circular references or deeply nested patterns (depth > 100)
- **Solution**: Flatten your configuration or check for circular pattern references

**`SpecError: Key (X) not found in mapping`**
- **Cause**: Dot-path accessing non-existent key
- **Solution**: Use `configure_spec(raise_error=False)` to return `None` instead, or validate data shape first

**`ValidationError` when creating patterns**
- **Cause**: Using direct constructor instead of `model_validate()`
- **Solution**: Always use `Pattern.model_validate(data)` not `Pattern(**data)`

**Template variables undefined**
- **Cause**: Missing variables in `template_kwargs` with `StrictUndefined`
- **Solution**: Provide all variables or configure with `configure_jinja(undefined_type=Undefined)`
