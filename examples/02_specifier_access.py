"""StructCast Example 02: Specifier — Data Access & Transformation.

Demonstrates how to use the specifier module to declaratively access,
extract, and restructure nested data using string-based path specifications.
"""

from structcast.core.specifier import access, construct, convert_spec

# ---------------------------------------------------------------------------
# 1. Basic path access
# ---------------------------------------------------------------------------
data = {
    "server": {
        "host": "localhost",
        "port": 8080,
        "options": {"debug": True, "workers": 4},
    }
}

# Convert a dotted path into a spec intermediate
spec = convert_spec("server.host")
result = construct(data, spec)
assert result == "localhost"
print(f"Path access (server.host):           {result}")

# Deeper nesting
spec = convert_spec("server.options.debug")
result = construct(data, spec)
print(f"Path access (server.options.debug):  {result}")

# ---------------------------------------------------------------------------
# 2. List index access
# ---------------------------------------------------------------------------
data = {
    "users": [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 35},
    ]
}

spec = convert_spec("users.0.name")
result = construct(data, spec)
assert result == "Alice"
print(f"List index (users.0.name):           {result}")

spec = convert_spec("users.2.age")
result = construct(data, spec)
assert result == 35
print(f"List index (users.2.age):            {result}")

# ---------------------------------------------------------------------------
# 3. Constant resolver — Return literal values
# ---------------------------------------------------------------------------
spec = convert_spec("constant: 42")
result = construct(data, spec)
assert result == "42"
print(f"Constant resolver:                   {result}")

spec = convert_spec("constant: hello world")
result = construct(data, spec)
assert result == "hello world"
print(f"Constant resolver (string):          {result}")

# ---------------------------------------------------------------------------
# 4. Restructuring data with spec dict
# ---------------------------------------------------------------------------
data = {
    "database": {
        "primary": {"host": "db1.example.com", "port": 5432},
        "replica": {"host": "db2.example.com", "port": 5433},
    },
    "app": {"name": "MyApp", "version": "1.0"},
}

# Build a new structure by specifying source paths
spec_cfg = {
    "app_name": "app.name",
    "db_host": "database.primary.host",
    "db_port": "database.primary.port",
}

converted = convert_spec(spec_cfg)
result = construct(data, converted)
print("\nRestructured data:")
print(f"  app_name: {result['app_name']}")
print(f"  db_host:  {result['db_host']}")
print(f"  db_port:  {result['db_port']}")

# ---------------------------------------------------------------------------
# 5. Direct access() function
# ---------------------------------------------------------------------------
value = access(data, ("database", "replica", "host"))
print(f"\nDirect access:                       {value}")

# Access with integer index
list_data = {"items": ["alpha", "beta", "gamma"]}
value = access(list_data, ("items", 1))
print(f"Direct access (list index):          {value}")
