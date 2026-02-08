# StructCast

**Elegantly orchestrating structured data via a flexible and serializable workflow.**

StructCast is a Python library for declaratively constructing, accessing, transforming, and templating structured data. It turns plain configuration (dicts, YAML, JSON) into live Python objects, extracts and reshapes nested data via path-based specifications, and generates dynamic configuration through Jinja2 templates — all with a built-in security layer that prevents code injection and unsafe operations.

---

## Table of Contents

- [StructCast](#structcast)
  - [Table of Contents](#table-of-contents)
  - [Key Features](#key-features)
  - [Installation](#installation)
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
  - [Comparison with Hydra and glom](#comparison-with-hydra-and-glom)
    - [StructCast vs Hydra](#structcast-vs-hydra)
    - [StructCast vs glom](#structcast-vs-glom)
    - [Summary Table](#summary-table)
  - [Examples](#examples)
  - [Requirements](#requirements)
  - [License](#license)

---

## Key Features

| Feature                         | Description                                                                               |
| ------------------------------- | ----------------------------------------------------------------------------------------- |
| **Pattern-based instantiation** | Build live Python objects from plain dict/list patterns (`_addr_`, `_call_`, `_bind_`, …) |
| **Path-based data access**      | Navigate nested data with dot-notation strings (`"a.b.0.c"`)                              |
| **Custom resolvers**            | Register domain-specific spec resolvers for extensible data extraction                    |
| **Jinja2 templating**           | Embed Jinja templates in data structures with YAML/JSON auto-parsing                      |
| **Sandboxed execution**         | All templates run in `ImmutableSandboxedEnvironment` by default                           |
| **Security layer**              | Module blocklist/allowlist, attribute validation, path traversal protection               |
| **YAML-native**                 | First-class YAML loading/dumping via `ruamel.yaml` with security checks                   |
| **Pydantic integration**        | Patterns and specs are validated as Pydantic models at parse time                         |
| **Serializable**                | Every pattern is a plain dict/list — store in YAML, JSON, or databases                    |

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

### 1. Instantiate Objects from Config

Use declarative dict patterns to import and call Python objects:

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

Extract and restructure nested data using dot-notation paths:

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

### 3. Generate Config with Templates

Embed Jinja2 templates directly in data structures:

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

### Instantiator

The instantiator converts declarative config patterns into live Python objects. Each pattern is a plain dict (or list) with a sentinel key:

| Pattern              | Alias    | Purpose                                                       |
| -------------------- | -------- | ------------------------------------------------------------- |
| **AddressPattern**   | `_addr_` | Import a class/function by dotted address                     |
| **AttributePattern** | `_attr_` | Access an attribute on the current object                     |
| **CallPattern**      | `_call_` | Call the current callable (dict → `**kwargs`, list → `*args`) |
| **BindPattern**      | `_bind_` | Partially apply arguments (`functools.partial`)               |
| **ObjectPattern**    | `_obj_`  | Chain multiple patterns into one build sequence               |

**Example — partial application:**

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

The `instantiate()` function recursively walks any nested dict/list, detecting and executing patterns wherever they appear. Non-pattern values pass through unchanged.

### Specifier

The specifier module provides a three-phase process for data access:

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

### Template

The template module integrates Jinja2 into data structures with three template types:

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

### Security

StructCast includes a comprehensive security layer that guards all dynamic operations:

- **Module blocklist** — blocks dangerous modules (`os`, `subprocess`, `sys`, `pickle`, `socket`, …)
- **Module allowlist** — only permits known-safe builtins and standard library modules
- **Attribute validation** — blocks dangerous dunder methods (`__subclasses__`, `__globals__`, `__code__`, …)
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

The `utils.base` module provides helper functions used across the library:

| Function                      | Purpose                                                 |
| ----------------------------- | ------------------------------------------------------- |
| `check_elements(x)`           | Normalize `None` / single / tuple / set → list          |
| `import_from_address(addr)`   | Security-checked dynamic import                         |
| `load_yaml(path)`             | Load YAML with path validation                          |
| `load_yaml_from_string(s)`    | Parse YAML from a string                                |
| `dump_yaml(data, path)`       | Write YAML with path validation                         |
| `dump_yaml_to_string(data)`   | Serialize data to YAML string                           |
| `unroll_call(value, call=fn)` | Call `fn` with smart unpacking (dict→kwargs, list→args) |

---

## Comparison with Hydra and glom

StructCast shares design philosophies with both [Hydra](https://hydra.cc/) (by Facebook Research) and [glom](https://glom.readthedocs.io/), but occupies a distinct niche. The table and discussion below highlight the similarities and differences.

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

Full runnable examples are in the [`examples/`](examples/) directory:

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

---

## Requirements

- Python >= 3.9
- [Jinja2](https://jinja.palletsprojects.com/) >= 3.1.6
- [Pydantic](https://docs.pydantic.dev/) >= 2.11.0
- [ruamel.yaml](https://yaml.readthedocs.io/) >= 0.19.1
- [typing-extensions](https://pypi.org/project/typing-extensions/) >= 4.15.0

## License

MIT License — see [LICENSE](LICENSE) for details.
