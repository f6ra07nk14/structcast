# Context

Glossary of StructCast's ubiquitous language. Use these words in issues, tests and code; don't drift to synonyms.

## Address

A dotted string naming an importable Python object, resolved by `import_from_address()` in `utils/base.py`.
`resolve_address()` splits it into a **module path** and a **target**: everything before the last dot is the module
path, the last segment is the target. `"collections.Counter"` → module path `collections`, target `Counter`. An
address with no dot (`"list"`) has no module path and resolves against `default_module`, or `builtins` if none was
given. Addresses also appear as YAML tags: `!collections.Counter` is resolved by importing that address.

Say "address", not "path" — `path` in this codebase means a filesystem path.

## Module path

The part of an address before the last dot, passed to `import_module()`. Validated only for identifier format and
dangerous dunders, so `numpy._core` is accepted. It is *not* checked against any allowlist or blocklist.

## Target

The last segment of an address: an attribute looked up on the imported module with `getattr`. Unlike the module path
it goes through `validate_attribute()`, so dangerous dunders, and by default non-ASCII, `_protected` and `__private`
names, are rejected.

## Pattern

A serializable dict/list instruction that `instantiate()` turns into a live object. Each pattern is a Pydantic model
keyed by its alias:

| Alias     | Class              | Meaning                                                      |
| --------- | ------------------ | ------------------------------------------------------------ |
| `_addr_`  | `AddressPattern`   | Import an address (optionally from a `_file_` module file)   |
| `_attr_`  | `AttributePattern` | Walk a dotted attribute path on the previous result          |
| `_call_`  | `CallPattern`      | Call the previous result with the given args/kwargs          |
| `_bind_`  | `BindPattern`      | `functools.partial` the previous result                      |
| `_obj_`   | `ObjectPattern`    | A list of the above, applied left to right                   |

The patterns inside an `_obj_` form a chain: each one consumes the object the previous one produced. `register_pattern()`
adds a custom pattern class to that set.

## Specifier / spec

The `core/specifier.py` subsystem, and the data it interprets. A **spec** is a serializable description of where
values come from — a dotted source path (`"users.0.name"`), a resolver expression (`"constant: 42"`, `"skip:"`), or a
nested dict/list of those. `convert_spec()` turns a spec into `SpecIntermediate` values; `construct()` applies them to
data; `access()` reads a single already-split path. `RawSpec`, `ObjectSpec` and `FlexSpec` are the model wrappers.

"Specifier" is the module/subsystem; "spec" is the data. Don't call a spec a "pattern" — patterns build objects, specs
read data.

## Trusted input

Configuration is trusted input: providing a configuration file is equivalent to being able to execute code in the
host process. There is no import allowlist or blocklist, and StructCast is not a sandbox for configuration of unknown
origin. See `docs/adr/0001-trusted-input-security-model.md`.

## Registered directory

A directory added with `register_dir()` (removed with `unregister_dir()`) that `find_path()` searches when it is given
a *relative* path that does not resolve against the current working directory. Absolute paths never consult the list.
The list is only a search path — it confines nothing.
