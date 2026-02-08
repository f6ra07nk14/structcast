"""StructCast Advanced Example 07: Dynamic Service Registry.

Demonstrates using Instantiator to build callable factories via _bind_,
Specifier to route config data into the right services, and Template
to generate connection descriptors — all from a single YAML config.
"""

from structcast.core.instantiator import instantiate
from structcast.core.specifier import construct, convert_spec
from structcast.core.template import JinjaYamlTemplate
from structcast.utils.base import load_yaml_from_string

# ═══════════════════════════════════════════════════════════════════════════
# Scenario: Build a service registry where each service has a formatter
# (partial function), extracted config fields, and a templated descriptor.
# ═══════════════════════════════════════════════════════════════════════════

# ---------------------------------------------------------------------------
# 1. Full application config
# ---------------------------------------------------------------------------
app_config_yaml = """\
services:
  cache:
    host: redis.local
    port: 6379
    db: 0
    max_connections: 50
  search:
    host: elastic.local
    port: 9200
    index_prefix: app
    replicas: 2
  queue:
    host: rabbit.local
    port: 5672
    vhost: production
    prefetch: 10

defaults:
  timeout: 30
  retries: 3
"""

app_config = load_yaml_from_string(app_config_yaml)

# ---------------------------------------------------------------------------
# 2. Use Specifier to extract service-specific views
# ---------------------------------------------------------------------------
print("=== Phase 1: Extract service configs with Specifier ===\n")

for service_name in ["cache", "search", "queue"]:
    spec = convert_spec(
        {
            "host": f"services.{service_name}.host",
            "port": f"services.{service_name}.port",
            "timeout": "defaults.timeout",
            "retries": "defaults.retries",
        }
    )
    view = construct(app_config, spec)
    print(f"  {service_name}: {view}")

# ---------------------------------------------------------------------------
# 3. Use Instantiator to build string formatters via _bind_
# ---------------------------------------------------------------------------
print("\n=== Phase 2: Build formatters with Instantiator ===\n")

# Create partial formatters: bind a template string to str.format_map
formatter_patterns = {
    "cache_uri": [
        "_obj_",
        {"_addr_": "str"},
        {"_attr_": "format_map"},
        {"_bind_": ["redis://{host}:{port}/{db}"]},
    ],
    "search_uri": [
        "_obj_",
        {"_addr_": "str"},
        {"_attr_": "format_map"},
        {"_bind_": ["http://{host}:{port}/{index_prefix}"]},
    ],
    "queue_uri": [
        "_obj_",
        {"_addr_": "str"},
        {"_attr_": "format_map"},
        {"_bind_": ["amqp://{host}:{port}/{vhost}"]},
    ],
}

formatters = instantiate(formatter_patterns)

# Apply formatters with actual config values
cache_uri = formatters["cache_uri"](app_config["services"]["cache"])
search_uri = formatters["search_uri"](app_config["services"]["search"])
queue_uri = formatters["queue_uri"](app_config["services"]["queue"])

print(f"  cache_uri:  {cache_uri}")
print(f"  search_uri: {search_uri}")
print(f"  queue_uri:  {queue_uri}")

# ---------------------------------------------------------------------------
# 4. Use YAML Template to generate a combined service descriptor
# ---------------------------------------------------------------------------
print("\n=== Phase 3: Generate service descriptor with Template ===\n")

descriptor_tpl = JinjaYamlTemplate.model_validate(
    {
        "_jinja_yaml_": """\
registry:
{% for name, svc in services.items() %}
  {{ name }}:
    endpoint: "{{ svc.host }}:{{ svc.port }}"
    timeout: {{ timeout }}
    retries: {{ retries }}
{% endfor %}
"""
    }
)

descriptor = descriptor_tpl(
    services=app_config["services"],
    timeout=app_config["defaults"]["timeout"],
    retries=app_config["defaults"]["retries"],
)

print("Generated service descriptor:")
for name, info in descriptor["registry"].items():
    print(f"  {name}:")
    for k, v in info.items():
        print(f"    {k}: {v}")
