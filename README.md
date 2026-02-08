# StructCast

**Declarative data orchestration — from configuration to live objects, safely.**

StructCast is a Python library that bridges the gap between static configuration and runtime behavior. Define your data pipelines, object construction, and dynamic templates in plain YAML or JSON, and let StructCast turn them into live Python objects — with security built in from the ground up.

---

## Why StructCast?

Modern applications often rely on deeply nested configuration to control everything from database connections to ML pipeline parameters. Managing this configuration typically involves ad-hoc parsing code, fragile string interpolation, or heavyweight frameworks that impose their own CLI and project structure.

StructCast was designed to solve three recurring challenges:

1. **Configuration-driven object construction** — Instantiate arbitrary Python objects from serializable dict/list patterns, without writing boilerplate factory code or coupling your application to a specific framework.
2. **Nested data extraction and restructuring** — Navigate complex data hierarchies with concise dot-notation paths and reshape results into the exact structure your application expects.
3. **Dynamic configuration generation** — Embed Jinja2 templates directly inside data structures, enabling conditional logic, loops, and runtime variable injection while keeping everything serializable and auditable.

All of this runs through a **sandboxed security layer** that validates imports, blocks dangerous attributes, and prevents code injection — so configurations can be safely loaded from external sources.

---

## Table of Contents

- [StructCast](#structcast)
  - [Why StructCast?](#why-structcast)
  - [Table of Contents](#table-of-contents)
  - [Key Features](#key-features)
  - [Installation](#installation)
    - [Install from PyPI](#install-from-pypi)
    - [Add to an existing project](#add-to-an-existing-project)
    - [Install from source (development)](#install-from-source-development)
  - [Quick Start](#quick-start)
    - [1. Instantiate Objects from Config](#1-instantiate-objects-from-config)
    - [2. Access Nested Data with Specifiers](#2-access-nested-data-with-specifiers)
    - [3. Generate Config with Templates](#3-generate-config-with-templates)
  - [Core Modules](#core-modules)
    - [Instantiator](#instantiator)
    - [Specifier](#specifier)
    - [Template](#template)
    - [Security](#security)
    - [Utilities](#utilities)
  - [Advanced Patterns](#advanced-patterns)
    - [`extend_structure` — Embedding Templates in Data](#extend_structure--embedding-templates-in-data)
    - [Chained FlexSpec](#chained-flexspec)
    - [End-to-End Integration Workflow](#end-to-end-integration-workflow)
  - [Comparison with Hydra and glom](#comparison-with-hydra-and-glom)
    - [StructCast vs Hydra](#structcast-vs-hydra)
    - [StructCast vs glom](#structcast-vs-glom)
    - [Summary Table](#summary-table)
  - [Examples](#examples)
    - [Advanced Examples](#advanced-examples)
  - [Requirements](#requirements)
  - [License](#license)

---

## Key Features

| Feature                         | Description                                                                                     |
| ------------------------------- | ----------------------------------------------------------------------------------------------- |
| **Pattern-based instantiation** | Build live Python objects from plain dict/list patterns (`_addr_`, `_call_`, `_bind_`, `_obj_`) |
| **Path-based data access**      | Navigate nested data with dot-notation strings (`"a.b.0.c"`)                                    |
| **Custom resolvers**            | Register domain-specific spec resolvers for extensible data extraction                          |
| **Jinja2 templating**           | Embed Jinja templates in data structures with YAML/JSON auto-parsing                            |
| **Sandboxed execution**         | All templates run in `ImmutableSandboxedEnvironment` by default                                 |
| **Security layer**              | Module blocklist/allowlist, attribute validation, path traversal protection                     |
| **YAML-native**                 | First-class YAML loading/dumping via `ruamel.yaml` with security checks                         |
| **Pydantic integration**        | Patterns and specs are validated as Pydantic models at parse time                               |
| **Serializable**                | Every pattern is a plain dict/list — store in YAML, JSON, or databases                          |

---

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable Python package management. You can also install with `pip`.

### Install from PyPI

```bash
# Using uv (recommended)
uv pip install structcast

# Using pip
pip install structcast
```

### Add to an existing project

```bash
# Using uv
uv add structcast

# Using pip
pip install structcast
```

### Install from source (development)

```bash
git clone https://github.com/f6ra07nk14/structcast.git
cd structcast

# Create virtual environment and install in editable mode with dev dependencies
uv sync --group dev

# Or with pip
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -e ".[dev]"
```

**Requirements:** Python >= 3.9

**Dependencies:** `jinja2`, `pydantic`, `ruamel.yaml`, `typing-extensions`

---

## Quick Start

The following three examples cover StructCast's core capabilities. Each builds on the previous one — start here to get a working understanding of the library in minutes.

### 1. Instantiate Objects from Config

Use declarative dict patterns to import and call any Python callable — classes, functions, or methods — without writing import or factory code:

```python
from structcast.core.instantiator import instantiate

# Import a class and call it with arguments
pattern = {
    "_obj_": [
        {"_addr_": "collections.Counter"},
        {"_call_": [["a", "b", "a", "c", "a"]]},
    ]
}
counter = instantiate(pattern)
print(counter)  # Counter({'a': 3, 'b': 1, 'c': 1})
```

Patterns are composable: chain `_addr_` (import) → `_attr_` (attribute access) → `_call_` (invocation) → `_bind_` (partial application) inside an `_obj_` list.

### 2. Access Nested Data with Specifiers

Use dot-notation path strings to reach into deeply nested data and reshape it into the structure your application expects:

```python
from structcast.core.specifier import convert_spec, construct

data = {
    "database": {
        "primary": {"host": "db1.example.com", "port": 5432},
    },
    "app": {"name": "MyApp"},
}

# Restructure with a spec dict
spec = convert_spec({
    "app_name": "app.name",
    "db_host": "database.primary.host",
})
result = construct(data, spec)
# {'app_name': 'MyApp', 'db_host': 'db1.example.com'}
```

For complex scenarios, `FlexSpec` automatically chooses between path-based access and object instantiation, and supports nested dict/list structures in a single declaration:

```python
from structcast.core.specifier import FlexSpec

data = {
    "user": {"name": "Alice", "age": 30},
    "settings": {"theme": "dark"},
}

# FlexSpec accepts dicts, lists, path strings, and ObjectSpec — all at once
spec = FlexSpec.model_validate({
    "profile": {"name": "user.name", "age": "user.age"},
    "theme": "settings.theme",
    "label": "constant: v1",
})
result = spec(data)
# {'profile': {'name': 'Alice', 'age': 30}, 'theme': 'dark', 'label': 'v1'}
```

### 3. Generate Config with Templates

Embed Jinja2 templates directly inside data structures to generate configuration dynamically at runtime. Templates are rendered in a sandboxed environment by default:

```python
from structcast.core.template import JinjaTemplate, extend_structure

# Render a single template
template = JinjaTemplate.model_validate({
    "_jinja_": "postgresql://{{ user }}:{{ pass }}@{{ host }}:{{ port }}/mydb"
})
conn = template(user="admin", pass="secret", host="localhost", port=5432)
print(conn)  # postgresql://admin:secret@localhost:5432/mydb

# Resolve YAML templates inside a data structure
data = {
    "_jinja_yaml_": """\
greeting: Hello {{ user }}!
farewell: Goodbye {{ user }}!
""",
}

result = extend_structure(
    data, template_kwargs={"default": {"user": "Alice"}}
)
print(result["greeting"])   # Hello Alice!
print(result["farewell"])   # Goodbye Alice!
```

---

## Core Modules

StructCast is organized around five modules, each responsible for one aspect of the data orchestration pipeline. They can be used independently or composed together for complex workflows.

### Instantiator

The Instantiator converts declarative config patterns into live Python objects. Each pattern is a plain dict (or list) with a sentinel key that tells StructCast what operation to perform:

| Pattern              | Alias    | Purpose                                                       |
| -------------------- | -------- | ------------------------------------------------------------- |
| **AddressPattern**   | `_addr_` | Import a class/function by dotted address                     |
| **AttributePattern** | `_attr_` | Access an attribute on the current object                     |
| **CallPattern**      | `_call_` | Call the current callable (dict → `**kwargs`, list → `*args`) |
| **BindPattern**      | `_bind_` | Partially apply arguments (`functools.partial`)               |
| **ObjectPattern**    | `_obj_`  | Chain multiple patterns into a single build sequence          |

**Example — partial application:**

Patterns are composable. The following example chains `_addr_` (import) and `_bind_` (partial application) to build a reusable converter:

```python
from structcast.core.instantiator import instantiate

# Create a hex-to-int converter via partial application
pattern = {
    "_obj_": [
        {"_addr_": "int"},
        {"_bind_": {"base": 16}},
    ]
}
hex_to_int = instantiate(pattern)
assert hex_to_int("FF") == 255
```

The `instantiate()` function recursively walks any nested dict/list, detecting and executing patterns wherever they appear. Non-pattern values pass through unchanged, making it safe to call on mixed data structures.

### Specifier

The Specifier module provides a three-phase process for extracting and reshaping data:

1. **Convert** — Parse configuration strings into intermediate spec objects
2. **Access** — Navigate into data using path tuples `("a", "b", 0, "c")`
3. **Construct** — Build a new data structure from specs + source data

**Built-in resolvers:**

| Resolver | Syntax           | Behavior                          |
| -------- | ---------------- | --------------------------------- |
| Source   | `"a.b.c"`        | Access nested path in source data |
| Constant | `"constant: 42"` | Return the literal value          |
| Skip     | `"skip:"`        | Skip this entry (sentinel)        |

**Custom resolvers:**

```python
from structcast.core.specifier import register_resolver, convert_spec, construct
import os

# Register an environment variable resolver
register_resolver("env", lambda key: os.environ.get(key))

# Use it in specs
spec = convert_spec("env: HOME")
result = construct({}, spec)  # Returns value of $HOME
```

**Copy semantics** can be configured via `ReturnType`:

- `REFERENCE` — return direct reference (default)
- `SHALLOW_COPY` — return a shallow copy
- `DEEP_COPY` — return a deep copy

**FlexSpec — unified specification:**

`FlexSpec` is the recommended entry point for most use cases. It automatically dispatches to `RawSpec` (path-based access) or `ObjectSpec` (instantiation) depending on the input, and recursively handles nested dict/list structures. Use `FlexSpec` when a single spec needs to mix extraction paths, constants, and object construction:

```python
from structcast.core.specifier import FlexSpec

data = {"metrics": {"cpu": 82.5, "mem": 64.1}, "host": "web-01"}

# String → RawSpec path access
assert FlexSpec.model_validate("host")(data) == "web-01"

# Dict → nested FlexSpec producing a new structure
spec = FlexSpec.model_validate({
    "server": "host",
    "readings": ["metrics.cpu", "metrics.mem"],
    "static": "constant: OK",
})
assert spec(data) == {
    "server": "web-01",
    "readings": [82.5, 64.1],
    "static": "OK",
}

# ObjectSpec inside FlexSpec — instantiate objects inline
spec = FlexSpec.model_validate({
    "sorter": {"_obj_": [{"_addr_": "sorted"}]},
    "name": "host",
})
result = spec(data)
assert result["sorter"] is sorted
assert result["name"] == "web-01"
```

`FlexSpec` is fully serializable via Pydantic and round-trips through `model_dump()` / `model_validate()`.

### Template

The Template module integrates Jinja2 into data structures, enabling dynamic configuration generation. Three template types correspond to different output formats:

| Template            | Alias          | Output                       |
| ------------------- | -------------- | ---------------------------- |
| `JinjaTemplate`     | `_jinja_`      | Raw rendered string          |
| `JinjaYamlTemplate` | `_jinja_yaml_` | Rendered then parsed as YAML |
| `JinjaJsonTemplate` | `_jinja_json_` | Rendered then parsed as JSON |

Templates run in a **sandboxed environment** (`ImmutableSandboxedEnvironment`) by default and support:

- Conditional logic (`{% if %}`)
- Loops (`{% for %}`)
- Variable interpolation (`{{ var }}`)
- Template groups for scoped contexts
- Post-processing pipelines (`_jinja_pipe_`)

**YAML template example:**

```python
from structcast.core.template import JinjaYamlTemplate

template = JinjaYamlTemplate.model_validate({
    "_jinja_yaml_": """\
server:
  host: {{ host }}
  port: {{ port }}
{% for feature in features %}
  {{ feature }}: true
{% endfor %}
"""
})

result = template(host="0.0.0.0", port=8080, features=["logging", "caching"])
# result = {'server': {'host': '0.0.0.0', 'port': 8080, 'logging': True, 'caching': True}}
```

**`extend_structure` — recursive template expansion:**

While standalone template models render individual values, `extend_structure` is designed for bulk operations: it recursively walks an entire data structure and resolves all embedded `_jinja_yaml_`, `_jinja_json_`, and `_jinja_` templates in place. Template variables are organized by named **template groups**:

```python
expanded = extend_structure(
    data,
    template_kwargs={"default": {"user": "Alice", "debug": True}},
)
```

The `"default"` group is used unless a template specifies `_jinja_group_` to select a different group. This allows different parts of a config tree to receive different sets of variables.

`_jinja_yaml_` can appear in two structural contexts, each with distinct merge behavior:

**Mapping pattern** — When `_jinja_yaml_` is a key inside a dict alongside static keys, its rendered output (must produce a YAML mapping) is **merged** into the parent dict:

```yaml
server:
  host: 0.0.0.0
  port: 8080
  _jinja_yaml_: |
    workers: {{ num_workers }}
    debug: {{ debug_mode }}
```

After `extend_structure`, this becomes:

```python
{"server": {"host": "0.0.0.0", "port": 8080, "workers": 4, "debug": True}}
```

Static keys and dynamically generated keys coexist in the same mapping.

**Sequence pattern** — When a `{"_jinja_yaml_": ...}` item appears inside a list, its rendered output (must produce a YAML sequence) is **spliced** into the parent list at that position:

```yaml
steps:
  - name: init
  - _jinja_yaml_: |
      {% for check in checks %}
      - name: "validate_{{ check }}"
      {% endfor %}
  - name: finalize
```

After `extend_structure` with `checks=["email", "age"]`, the list becomes:

```python
[
    {"name": "init"},
    {"name": "validate_email"},
    {"name": "validate_age"},
    {"name": "finalize"},
]
```

Both patterns can coexist in a single config tree and are resolved recursively. See [Advanced Patterns](#advanced-patterns) for full integration examples.

### Security

StructCast includes a comprehensive security layer that guards all dynamic operations. Since configurations may be loaded from external or untrusted sources, every import, attribute access, and file path is validated before execution:

- **Module blocklist** — blocks dangerous modules (`os`, `subprocess`, `sys`, `pickle`, `socket`, and more)
- **Module allowlist** — only permits known-safe builtins and standard library modules
- **Attribute validation** — blocks dangerous dunder methods (`__subclasses__`, `__globals__`, `__code__`, and more)
- **Protected/private member checks** — optionally block `_protected` and `__private` members
- **Path security** — prevents hidden directory access and path traversal attacks
- **Recursion limits** — maximum depth (100) and timeout (30s) for all recursive operations

```python
from structcast.utils.security import configure_security

# Tighten security settings
configure_security(
    ascii_check=True,
    protected_member_check=True,
    hidden_check=True,
)
```

### Utilities

The `utils.base` module provides helper functions used throughout the library and available for direct use in application code:

| Function                    | Purpose                         |
| --------------------------- | ------------------------------- |
| `import_from_address(addr)` | Security-checked dynamic import |
| `load_yaml(path)`           | Load YAML with path validation  |
| `load_yaml_from_string(s)`  | Parse YAML from a string        |
| `dump_yaml(data, path)`     | Write YAML with path validation |
| `dump_yaml_to_string(data)` | Serialize data to YAML string   |

---

## Advanced Patterns

The advanced examples (06–08) combine multiple StructCast modules into end-to-end workflows. This section documents the key patterns they rely on, so you can apply them in your own projects.

### `extend_structure` — Embedding Templates in Data

The [mapping and sequence patterns](#template) described above are the foundation of dynamic configuration. The following example combines both patterns in a single config:

```python
from structcast.core.template import extend_structure
from structcast.utils.base import load_yaml_from_string

config_yaml = """\
pipeline:
  name: DataProcessor

  # Mapping pattern: merge dynamic settings into a static dict
  settings:
    output_format: json
    _jinja_yaml_: |
      batch_size: {{ batch_size }}
      retry: {{ retry }}

  # Sequence pattern: splice dynamic steps into a static list
  steps:
    - name: load
    - _jinja_yaml_: |
        {%- for t in transforms %}
        - name: "{{ t }}"
        {%- endfor %}
    - name: save
"""

raw = load_yaml_from_string(config_yaml)
expanded = extend_structure(
    raw,
    template_kwargs={"default": {
        "batch_size": 64,
        "retry": True,
        "transforms": ["normalize", "deduplicate"],
    }},
)

# settings: {output_format: json, batch_size: 64, retry: True}
# steps: [{name: load}, {name: normalize}, {name: deduplicate}, {name: save}]
```

### Chained FlexSpec

A powerful pattern used throughout the advanced examples is **two-stage FlexSpec**: one `FlexSpec` extracts configuration metadata (including path strings), and a second `FlexSpec` uses those extracted paths as its spec against a different data source. This enables fully config-driven data extraction without hardcoding any paths in application code:

```python
from structcast.core.specifier import FlexSpec

# Step 1: Config defines extraction paths
config = {
    "extraction": {
        "temperature": "sensors.temp",
        "humidity": "sensors.hum",
    }
}

# FlexSpec reads the config to get the extraction paths
config_spec = FlexSpec.model_validate({"paths": "extraction"})
cfg = config_spec(config)
# cfg["paths"] = {"temperature": "sensors.temp", "humidity": "sensors.hum"}

# Step 2: Feed the extracted paths as a NEW FlexSpec against raw device data
raw_data = {"sensors": {"temp": 22.5, "hum": 68.0}}
data_spec = FlexSpec.model_validate(dict(cfg["paths"]))
readings = data_spec(raw_data)
# readings = {"temperature": 22.5, "humidity": 68.0}
```

This pattern appears in examples 06 and 07: the YAML config contains FlexSpec-compatible path strings that become specs for navigating raw payloads at runtime.

The `"constant: value"` resolver is particularly useful in this context — it allows config-defined specs to include literal values alongside path-based lookups:

```python
# In YAML config (after _jinja_yaml_ expansion)
# tenants:
#   acme:
#     label: "constant: Acme Corp"
#     transactions: "warehouse.acme.txns"

tenant_spec = FlexSpec.model_validate({
    "label": "constant: Acme Corp",
    "transactions": "warehouse.acme.txns",
})
result = tenant_spec(warehouse_data)
# result["label"] = "Acme Corp" (literal)
# result["transactions"] = <data from warehouse.acme.txns>
```

### End-to-End Integration Workflow

The advanced examples follow a consistent multi-phase pipeline that chains all core modules together. Understanding this flow is key to building your own StructCast-powered applications:

```text
YAML config → load_yaml_from_string → extend_structure → FlexSpec → instantiate → process → JinjaTemplate
```

| Phase       | Module                  | Purpose                                                                       |
| ----------- | ----------------------- | ----------------------------------------------------------------------------- |
| **Define**  | —                       | Write YAML config with embedded `_jinja_yaml_` templates and `_obj_` patterns |
| **Load**    | `load_yaml_from_string` | Parse YAML into Python dicts                                                  |
| **Expand**  | `extend_structure`      | Resolve all `_jinja_yaml_` templates with runtime parameters                  |
| **Extract** | `FlexSpec`              | Read the expanded config to pull out relevant sections                        |
| **Build**   | `instantiate`           | Construct live Python objects from `_obj_` patterns found in config           |
| **Process** | (your code)             | Apply instantiated tools to extracted data                                    |
| **Report**  | `JinjaTemplate`         | Render a final human-readable output                                          |

```python
# Typical integration skeleton
from structcast.core.instantiator import instantiate
from structcast.core.specifier import FlexSpec
from structcast.core.template import JinjaTemplate, extend_structure
from structcast.utils.base import load_yaml_from_string

# 1. Load YAML config
raw = load_yaml_from_string(yaml_string)

# 2. Expand _jinja_yaml_ templates with runtime params
expanded = extend_structure(raw, template_kwargs={"default": runtime_params})

# 3. Extract config sections with FlexSpec
spec = FlexSpec.model_validate({
    "tool": "config.processor",
    "paths": "config.extraction_paths",
    "report_tpl": "config.report_template",
})
cfg = spec(expanded)

# 4. Build tools from _obj_ patterns in config
tool = instantiate(dict(cfg["tool"]))

# 5. Chained FlexSpec: use config-defined paths to extract from raw data
data_spec = FlexSpec.model_validate(dict(cfg["paths"]))
extracted = data_spec(raw_payload)

# 6. Process data with instantiated tool
result = {k: tool(v) for k, v in extracted.items()}

# 7. Render report
report = JinjaTemplate.model_validate({"_jinja_": cfg["report_tpl"]})(data=result)
```

See the [Advanced Examples](#advanced-examples) for complete, runnable implementations of this workflow.

---

## Comparison with Hydra and glom

StructCast shares design philosophies with both [Hydra](https://hydra.cc/) (by Facebook Research) and [glom](https://glom.readthedocs.io/), but occupies a distinct niche as a **composable library** rather than a full framework. The following comparison highlights when each tool is the right choice.

### StructCast vs Hydra

**Similarities:**

- Both use **YAML-based hierarchical configuration** as a primary data format
- Both support **dynamic object instantiation** from config — Hydra uses `_target_` to reference classes; StructCast uses `_addr_` + `_call_` patterns
- Both enable **runtime overrides** and composable configuration
- Both provide validation and safety mechanisms for configuration data

**Differences:**

| Aspect                     | Hydra                                                             | StructCast                                                                  |
| -------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------- |
| **Scope**                  | Full application framework (CLI, multi-run, logging, output dirs) | Library focused on data orchestration (instantiation, access, templating)   |
| **Config language**        | OmegaConf (YAML + variable interpolation)                         | Plain dicts/lists + Jinja2 templates                                        |
| **Object instantiation**   | Single `_target_` key pointing to a class                         | Composable pattern chain (`_addr_` → `_attr_` → `_call_` → `_bind_`)        |
| **Partial application**    | `_partial_: true` flag                                            | Dedicated `_bind_` pattern with arg flexibility                             |
| **Variable interpolation** | Built-in OmegaConf resolvers (`${db.host}`)                       | Jinja2 templates (`{{ db.host }}`) with full logic support                  |
| **Data access**            | Dot-notation on OmegaConf containers                              | Specifier module with custom resolvers and accessors                        |
| **Templating**             | Not built-in (static interpolation only)                          | Full Jinja2 with conditionals, loops, YAML/JSON auto-parsing                |
| **Security**               | No built-in security layer                                        | Comprehensive: module blocklist/allowlist, attribute filtering, path checks |
| **CLI integration**        | First-class CLI with overrides and tab completion                 | Not included (library-only)                                                 |
| **Multi-run / sweeps**     | Built-in parameter sweep support                                  | Not included                                                                |

**When to choose Hydra:** You need a full application framework with CLI argument parsing, experiment sweeps, and output directory management.

**When to choose StructCast:** You need a composable library for building objects from config, accessing nested data, and generating dynamic configurations with security constraints — without framework lock-in.

### StructCast vs glom

**Similarities:**

- Both provide **path-based access** to nested data structures (`"a.b.c"`)
- Both support **declarative data restructuring** (spec dicts that map output keys to source paths)
- Both offer **extensibility** through custom specs/resolvers
- Both handle heterogeneous data (dicts, lists, objects) through a unified interface

**Differences:**

| Aspect              | glom                                                                 | StructCast                                                                               |
| ------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Primary focus**   | Data access and transformation                                       | Full data orchestration (access + instantiation + templating)                            |
| **Spec language**   | Rich built-in specs (`T`, `Coalesce`, `Match`, `Check`, `Invoke`, …) | String-based specs with custom resolvers                                                 |
| **Object creation** | `Invoke` spec for calling functions                                  | Full pattern system (`_addr_`, `_call_`, `_bind_`, `_obj_`) with recursive instantiation |
| **Templating**      | Not included                                                         | Jinja2 integration with YAML/JSON auto-parsing                                           |
| **Serializability** | Specs are Python objects (not easily serializable)                   | All patterns are plain dicts/lists (YAML/JSON serializable)                              |
| **Fallback values** | `Coalesce` and `default` parameter                                   | Resolver-based (`constant:`, `skip:`)                                                    |
| **Type validation** | `Check` spec                                                         | Pydantic model validation on patterns                                                    |
| **Security**        | Not included                                                         | Built-in module/attribute/path security                                                  |
| **Streaming**       | Built-in streaming iteration support                                 | Not included                                                                             |
| **Mutation**        | `Assign`, `Delete` for in-place mutation                             | Not included (functional approach)                                                       |

**When to choose glom:** You need a rich, in-process data query/transformation library with streaming, mutation, and advanced pattern matching.

**When to choose StructCast:** You need serializable configuration-driven workflows that combine object instantiation, data access, and template rendering with security guarantees.

### Summary Table

| Feature              | StructCast                     | Hydra               | glom                      |
| -------------------- | ------------------------------ | ------------------- | ------------------------- |
| Nested data access   | Path specs `"a.b.0.c"`         | OmegaConf resolvers | Path strings / `T` object |
| Object instantiation | `_addr_` + `_call_` patterns   | `_target_` key      | `Invoke` spec             |
| Partial application  | `_bind_` pattern               | `_partial_: true`   | `Invoke` + `partial`      |
| Templating           | Jinja2 (sandboxed)             | None                | None                      |
| Serializable config  | Yes (plain dict/list)          | Yes (YAML)          | No (Python objects)       |
| Security layer       | Yes (blocklist/allowlist/path) | No                  | No                        |
| CLI framework        | No                             | Yes                 | No                        |
| Parameter sweeps     | No                             | Yes (multi-run)     | No                        |
| Data streaming       | No                             | No                  | Yes                       |
| In-place mutation    | No                             | Via OmegaConf       | Yes (`Assign`/`Delete`)   |

---

## Examples

Full runnable examples are in the [`examples/`](examples/) directory. They are ordered by complexity — start with 01 for fundamentals, then progress to the advanced integration examples:

| Example                                                               | Description                                                                        |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| [01_basic_instantiation.py](examples/01_basic_instantiation.py)       | Pattern-based object construction: `_addr_`, `_call_`, `_attr_`, `_bind_`, `_obj_` |
| [02_specifier_access.py](examples/02_specifier_access.py)             | Dot-notation data access, constant resolver, data restructuring                    |
| [03_template_rendering.py](examples/03_template_rendering.py)         | Jinja2 templates, YAML/JSON output, structured extension, template groups          |
| [04_security_configuration.py](examples/04_security_configuration.py) | Import validation, attribute checking, custom security settings                    |
| [05_yaml_workflow.py](examples/05_yaml_workflow.py)                   | End-to-end YAML config workflow combining all modules                              |

Run any example directly:

```bash
python examples/01_basic_instantiation.py
```

### Advanced Examples

These examples demonstrate **cross-module integration** — combining `load_yaml_from_string`, `extend_structure`, `FlexSpec`, `instantiate`, and `JinjaTemplate` in realistic workflows. Each one builds a complete data pipeline where YAML configs with embedded `_jinja_yaml_` templates are expanded, extracted, processed, and rendered at runtime:

| Example                                                               | Description                                                                                                                   |
| --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| [06_sensor_dashboard.py](examples/06_sensor_dashboard.py)             | **Mapping pattern**: `_jinja_yaml_` merges dynamic sensor paths, thresholds, and Instantiator patterns into static config     |
| [07_validation_pipeline.py](examples/07_validation_pipeline.py)       | **List pattern**: `_jinja_yaml_` splices dynamic validation steps into a static pipeline; mapping pattern for output settings |
| [08_multi_tenant_analytics.py](examples/08_multi_tenant_analytics.py) | **Both patterns**: mapping generates per-tenant FlexSpec specs; list splices aggregation tools; per-tenant data processing    |

---

## Requirements

- Python >= 3.9
- [Jinja2](https://jinja.palletsprojects.com/) >= 3.1.6
- [Pydantic](https://docs.pydantic.dev/) >= 2.11.0
- [ruamel.yaml](https://yaml.readthedocs.io/) >= 0.19.1
- [typing-extensions](https://pypi.org/project/typing-extensions/) >= 4.15.0

## License

MIT License — see [LICENSE](LICENSE) for details.
