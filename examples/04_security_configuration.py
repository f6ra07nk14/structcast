"""StructCast Example 04: Security Configuration.

Demonstrates how StructCast's security layer protects against unsafe
imports, dangerous attribute access, and path traversal attacks.
"""

from structcast.utils.security import SecurityError, configure_security, validate_attribute, validate_import

# ---------------------------------------------------------------------------
# 1. Import validation — safe builtins pass, dangerous modules blocked
# ---------------------------------------------------------------------------
print("=== Import Validation ===")

# Safe imports succeed silently
validate_import("builtins", "list")
validate_import("builtins", "dict")
print("Built-in 'list' and 'dict': ALLOWED")

# Dangerous modules are blocked
for module in ["os", "subprocess", "sys", "pickle"]:
    try:
        validate_import(module, None)
        print(f"Module '{module}': ALLOWED (unexpected!)")
    except SecurityError:
        print(f"Module '{module}': BLOCKED")

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

# ---------------------------------------------------------------------------
# 3. Custom security settings
# ---------------------------------------------------------------------------
print("\n=== Custom Security Settings ===")

# Tighten security: also block protected members (_name)
configure_security(protected_member_check=True, private_member_check=True)
try:
    validate_attribute("_protected_method")
    print("Protected member '_protected_method': ALLOWED")
except SecurityError:
    print("Protected member '_protected_method': BLOCKED")

# Reset to defaults
configure_security()
print("Security settings reset to defaults.")
