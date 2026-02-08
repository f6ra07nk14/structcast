"""StructCast Example 05: YAML-Based Configuration Workflow.

Demonstrates a complete workflow: load YAML config, use specifiers to
extract data, instantiate objects, and render templates — all driven
by YAML configuration.
"""

from structcast.core.instantiator import instantiate
from structcast.core.specifier import construct, convert_spec
from structcast.core.template import JinjaTemplate
from structcast.utils.base import dump_yaml_to_string, load_yaml_from_string

# ---------------------------------------------------------------------------
# 1. Define a YAML configuration
# ---------------------------------------------------------------------------
yaml_config = """\
app:
  name: MyService
  version: "2.1"

database:
  host: db.example.com
  port: 5432
  credentials:
    user: admin
    password: secret

features:
  - logging
  - caching
  - rate_limiting
"""

# ---------------------------------------------------------------------------
# 2. Load YAML into Python dict
# ---------------------------------------------------------------------------
config = load_yaml_from_string(yaml_config)
print("Loaded config:")
print(dump_yaml_to_string(config))

# ---------------------------------------------------------------------------
# 3. Use specifiers to extract and restructure data
# ---------------------------------------------------------------------------
spec_cfg = {
    "service_name": "app.name",
    "db_connection": "database.host",
    "db_port": "database.port",
    "feature_count": "constant: 3",
}

converted = convert_spec(spec_cfg)
extracted = construct(config, converted)
print("Extracted data:")
for key, value in extracted.items():
    print(f"  {key}: {value}")

# ---------------------------------------------------------------------------
# 4. Use templates to generate a connection string
# ---------------------------------------------------------------------------
conn_template = JinjaTemplate.model_validate(
    {"_jinja_": "postgresql://{{ user }}:{{ password }}@{{ host }}:{{ port }}/mydb"}
)

connection_string = conn_template(
    user=config["database"]["credentials"]["user"],
    password=config["database"]["credentials"]["password"],
    host=config["database"]["host"],
    port=config["database"]["port"],
)
print(f"\nGenerated connection string: {connection_string}")

# ---------------------------------------------------------------------------
# 5. Instantiate a Counter from config-driven pattern
# ---------------------------------------------------------------------------
pattern = {
    "_obj_": [
        {"_addr_": "collections.Counter"},
        {"_call_": [config["features"]]},
    ]
}
counter = instantiate(pattern)
print(f"\nFeature counter: {counter}")

# ---------------------------------------------------------------------------
# 6. Serialize result back to YAML
# ---------------------------------------------------------------------------
output = {
    "extracted": extracted,
    "connection_string": connection_string,
}
print("\nFinal output as YAML:")
print(dump_yaml_to_string(output))
