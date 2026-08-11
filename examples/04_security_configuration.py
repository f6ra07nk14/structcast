"""StructCast Example 04: Security Configuration.

Demonstrates StructCast's trust model: configuration is trusted input, so an
address is imported as written. What is still validated is attribute access —
dangerous dunders, non-ASCII names, and protected/private members.
"""

from structcast.utils.base import SecurityError, configure_security, import_from_address, validate_attribute

# ---------------------------------------------------------------------------
# 1. Trusted input — an address is imported as written
# ---------------------------------------------------------------------------
print("=== Trusted Input ===")

# There is no module allowlist or blocklist. Whatever the configuration names,
# import_from_address() imports. Handing StructCast a configuration file is
# equivalent to letting it execute code, so never load one from an untrusted
# source (a web request, a file upload, another tenant).
for address in ["math.sqrt", "collections.Counter", "os.system"]:
    imported = import_from_address(address)
    print(f"Address {address!r:24} imported as {imported!r}")

# ---------------------------------------------------------------------------
# 2. Attribute validation — prevents access to dangerous members
# ---------------------------------------------------------------------------
print("\n=== Attribute Validation ===")

# Normal attributes are fine
validate_attribute("method_name")
validate_attribute("obj.method.attribute")
print("Normal attributes: ALLOWED")

# Dangerous dunder methods are blocked
dangerous = ["__subclasses__", "__globals__", "__code__", "__import__"]
for attr in dangerous:
    try:
        validate_attribute(attr)
        print(f"Attribute '{attr}': ALLOWED (unexpected!)")
    except SecurityError:
        print(f"Attribute '{attr}': BLOCKED")

# The same guard applies to the target half of an address
try:
    import_from_address("collections.__dict__")
    print("Address 'collections.__dict__': ALLOWED (unexpected!)")
except SecurityError as err:
    print(f"Address 'collections.__dict__': BLOCKED ({err})")

# ---------------------------------------------------------------------------
# 3. Custom security settings
# ---------------------------------------------------------------------------
print("\n=== Custom Security Settings ===")

# Protected and private members are blocked by default
for attr in ["_protected_method", "__private_method"]:
    try:
        validate_attribute(attr)
        print(f"Member '{attr}': ALLOWED")
    except SecurityError:
        print(f"Member '{attr}': BLOCKED")

# Relax the protected-member guard to reach a library's underscore-prefixed API
configure_security(protected_member_check=False)
validate_attribute("_protected_method")
print("Member '_protected_method' after protected_member_check=False: ALLOWED")

# Per-call overrides work without touching the global settings
validate_attribute("__private_method", private_member_check=False)
print("Member '__private_method' with private_member_check=False: ALLOWED")

# Calling configure_security() with no arguments resets everything to defaults
configure_security()
print("Security settings reset to defaults.")
