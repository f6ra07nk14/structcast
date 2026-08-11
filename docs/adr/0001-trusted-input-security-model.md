# ADR-0001: Configuration is trusted input

- **Status**: Accepted
- **Date**: 2026-08-11

## Context

`import_from_address()` used to guard every dynamic import with two lists in `utils/constants.py`:
`DEFAULT_BLOCKED_MODULES` (`os`, `subprocess`, `sys`, `pickle`, `socket`, `importlib`, `pathlib`, …) and
`DEFAULT_ALLOWED_MODULES` (a hand-written map of safe members of `builtins`, `math`, `json`, `datetime`, …).
`check_path()` additionally refused paths containing hidden directories or paths outside the working directory.

Two things were wrong with this.

**It blocked ordinary use.** StructCast's whole point is building live objects from configuration, and the objects
people actually want are the ones in their own project and in third-party libraries. Neither is on a hand-written
allowlist. `import_from_address("numpy.array")` was rejected by default. So was any application class, any
`torch.optim.Adam`, any private-but-public-in-practice path such as `numpy._core`. Every real user's first step was
to widen the allowlist until it no longer blocked anything, which means the list protected nobody and cost everybody.

**The allowlist doubled as the YAML tag registry.** `_YamlManager` registered one ruamel constructor per allowlisted
address so that `!<address>` tags could resolve. Adding a class to a config therefore required registering it in the
security allowlist — the two concerns were welded together for no reason other than implementation convenience.

Underneath both problems is a claim the library could not honour. The README promised configurations "can be safely
loaded from external sources". An allowlist cannot deliver that: `_call_` and `_bind_` invoke whatever they resolve,
`_attr_` walks object graphs, and any list of "safe" callables large enough to be useful contains a gadget chain.
Selling a sandbox we did not have was worse than having no sandbox, because it told users it was fine to feed
StructCast attacker-controlled YAML.

## Decision

Configuration is **trusted input**. Providing a configuration file to StructCast is equivalent to being able to
execute code in the host process. Consequently:

- `DEFAULT_BLOCKED_MODULES`, `DEFAULT_ALLOWED_MODULES` and `validate_import()` are removed, along with the
  `SecuritySettings` / `configure_security()` parameters `blocked_modules`, `allowed_modules`,
  `allowed_modules_check`, `blocked_modules_check`, `hidden_check` and `working_dir_check`.
- `import_from_address()` validates the module path only for identifier format and dangerous dunders, then imports it.
  The target half of the address remains an attribute access and is validated as one.
- `check_path()` is renamed `find_path()`: it resolves a path and searches registered directories, and no longer
  raises `SecurityError`.
- `!<address>` YAML tags resolve on demand through a multi-constructor, with no registration step. The registration
  is written onto each constructor instance (shadowing ruamel's class-level registry) so it does not leak into other
  `YAML(typ="safe")` instances in the process, ruamel's `add_multi_constructor` being a classmethod.
- The documentation says all of this in plain words instead of advertising a sandbox.

## Alternatives considered

**Keep the allowlist, add an explicit `register_yaml_tag()` API.** This separates the two welded concerns but keeps
the one that blocked ordinary use, and it adds a registration call to every workflow that already had a working
`!<address>` tag. It also preserves the misleading safety claim, which was the more serious defect.

**Drop custom tag construction entirely and require `_addr_` patterns.** Tags would then be a pure YAML concern and
the allowlist would have only one job. But `!<address>` tags are load-bearing for existing configurations and are
the ergonomic way to name a class inline; removing them is a bigger break than the one being made here, and it does
not change the trust model at all — `_addr_` imports the same code.

**Keep a blocklist only.** A blocklist of `os` and `subprocess` stops no one — `builtins.__import__` is not the only
route, and any sufficiently large library reachable from an allowed module re-exports what was blocked. It buys the
appearance of a guard at the cost of blocking legitimate `os.path` use.

## Consequences

- A configuration can import and call anything the process can. Applications are responsible for deciding where
  configuration comes from, and must not pass externally-supplied YAML/JSON to `instantiate()`, `load_yaml()` or
  `FlexSpec`.
- The README, `SKILL.md`, `README_AGENT.md` and `.github/copilot-instructions.md` are repositioned: the tagline no
  longer says "safely", the comparison tables no longer claim a security advantage over Hydra or glom, and the
  `### Security` section leads with the trust model.
- This is a breaking API change and ships as a `2.0.0` major release. Callers using the removed parameters or
  `structcast.utils.security` / `structcast.utils.constants` must update.
- Users who relied on the allowlist as a safety boundary must replace it with a boundary of their own — a schema
  that whitelists the addresses their application accepts, applied before the config reaches StructCast.

## What still protects the user

These remain and are the honest extent of the library's defences:

- **Attribute-access validation** — dangerous dunders are always blocked; non-ASCII, protected (`_foo`) and private
  (`__foo`) names are blocked by default, for `_attr_` paths and for the target half of an address.
- **YAML safe loader** — `ruamel.yaml` runs with `typ="safe"`, so standard `!!python/…` tags do not construct
  objects. StructCast's `!<address>` tags are the deliberate exception.
- **Jinja sandbox** — templates render in `ImmutableSandboxedEnvironment`.
- **`.py`-only module files** — loading a module from a file refuses any other suffix.
- **Recursion limits** — `MAX_RECURSION_DEPTH` (100) and `MAX_RECURSION_TIME` (30s) bound recursive traversal.
