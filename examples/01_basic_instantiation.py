"""StructCast Example 01: Basic Instantiation Patterns.

Demonstrates how to use the instantiator module to construct Python
objects declaratively from plain dict/list configuration.
"""

from structcast.core.instantiator import instantiate

# ---------------------------------------------------------------------------
# 1. AddressPattern — Import a built-in class
# ---------------------------------------------------------------------------
pattern = ["_obj_", {"_addr_": "list"}]
result = instantiate(pattern)
assert result is list
print(f"AddressPattern (builtin):  {result}")  # <class 'list'>

# Import from the standard library
pattern = ["_obj_", {"_addr_": "collections.Counter"}]
Counter = instantiate(pattern)
print(f"AddressPattern (stdlib):   {Counter}")  # <class 'collections.Counter'>

# ---------------------------------------------------------------------------
# 2. ObjectPattern — Chain patterns to build objects
# ---------------------------------------------------------------------------
# Create a list by importing `list` then calling it with arguments
pattern = ["_obj_", {"_addr_": "list"}, {"_call_": [[1, 2, 3]]}]
result = instantiate(pattern)
assert result == [1, 2, 3]
print(f"ObjectPattern (list call): {result}")

# ---------------------------------------------------------------------------
# 3. CallPattern — Different argument styles
# ---------------------------------------------------------------------------
# Keyword arguments (dict → **kwargs)
pattern = ["_obj_", {"_addr_": "dict"}, {"_call_": {"a": 1, "b": 2}}]
result = instantiate(pattern)
assert result == {"a": 1, "b": 2}
print(f"CallPattern (kwargs):      {result}")

# Positional arguments (list → *args)
pattern = ["_obj_", {"_addr_": "tuple"}, {"_call_": [[10, 20, 30]]}]
result = instantiate(pattern)
print(f"CallPattern (args):        {result}")

# ---------------------------------------------------------------------------
# 4. AttributePattern — Access attributes on objects
# ---------------------------------------------------------------------------
pattern = ["_obj_", {"_addr_": "collections.Counter"}, {"_call_": [["a", "b", "a", "c", "a"]]}]
result = instantiate(pattern)
print(f"Chain (addr+call):         {result}")  # Counter({'a': 3, ...})

# ---------------------------------------------------------------------------
# 5. BindPattern — Partial application (currying)
# ---------------------------------------------------------------------------
pattern = ["_obj_", {"_addr_": "int"}, {"_bind_": {"base": 16}}]
hex_to_int = instantiate(pattern)
assert hex_to_int("FF") == 255
assert hex_to_int("10") == 16
print(f"BindPattern (hex→int):     hex_to_int('FF') = {hex_to_int('FF')}")

# ---------------------------------------------------------------------------
# 6. Nested configuration — Recursive instantiation
# ---------------------------------------------------------------------------
config = {
    "counter": ["_obj_", {"_addr_": "collections.Counter"}, {"_call_": [["x", "y", "x", "z", "x"]]}],
    "static_value": 42,
    "plain_list": "unchanged",
}
result = instantiate(config)
print("\nNested config result:")
print(f"  counter:      {result['counter']}")
print(f"  static_value: {result['static_value']}")
print(f"  plain_list:   {result['plain_list']}")
