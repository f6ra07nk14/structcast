"""StructCast Advanced Example 08: Multi-Tenant Data Aggregation Platform.

Demonstrates **both** _jinja_yaml_ patterns (mapping + list) in a single
complex configuration, showcasing the full flexibility of the workflow.

Workflow:
  1. YAML config uses mapping _jinja_yaml_ to generate per-tenant FlexSpec
     extraction specs and list _jinja_yaml_ to splice dynamic aggregation tools
  2. load_yaml_from_string → extend_structure expands all templates
  3. FlexSpec reads the expanded platform config
  4. For each tenant, FlexSpec extracts data from a raw data warehouse
  5. Instantiator builds aggregation tools from config
  6. Aggregations are applied per-tenant
  7. JinjaTemplate renders the final analytics report

Both patterns in one config::

    tenants:                          # mapping pattern
      _jinja_yaml_: |
        acme:
          data_path: "warehouse.acme"
        globex:
          data_path: "warehouse.globex"

    aggregations:                     # list pattern
      - name: count
        tool: ...
      - _jinja_yaml_: |
          - name: total
            tool: ...
"""

from structcast.core.instantiator import instantiate
from structcast.core.specifier import FlexSpec
from structcast.core.template import JinjaTemplate, extend_structure
from structcast.utils.base import load_yaml_from_string

# ═══════════════════════════════════════════════════════════════════════════
# 1. YAML configuration with BOTH mapping and list _jinja_yaml_ patterns
# ═══════════════════════════════════════════════════════════════════════════

CONFIG_YAML = """\
platform:
  name: Multi-Tenant Analytics

  # ── Mapping pattern ──────────────────────────────────────────────
  # Generates per-tenant extraction specs dynamically.
  # Each tenant entry maps FlexSpec paths into the data warehouse.
  # "constant:" is a built-in Specifier resolver for literal values.
  tenants:
    _jinja_yaml_: |
      {% for t in active_tenants %}
      {{ t.id }}:
        label: "constant: {{ t.name }}"
        tier: "constant: {{ t.tier }}"
        transactions: "warehouse.{{ t.id }}.transactions"
      {% endfor %}

  # ── List pattern ─────────────────────────────────────────────────
  # Base aggregation tool + dynamic additions spliced in.
  aggregations:
    - name: count
      description: Number of transactions
      tool:
        _obj_:
          - _addr_: len
    - _jinja_yaml_: |
        {% for agg in custom_aggregations %}
        - name: "{{ agg.name }}"
          description: "{{ agg.description }}"
          tool:
            _obj_:
              - _addr_: "{{ agg.func }}"
        {% endfor %}

  # ── Mapping pattern ──────────────────────────────────────────────
  # Display settings with dynamic precision.
  display:
    currency: USD
    _jinja_yaml_: |
      precision: {{ display_precision }}

  # Plain report template (rendered manually later)
  report_template: |
    ╔══════════════════════════════════════════════╗
    ║  {{ platform_name }}
    ╠══════════════════════════════════════════════╣
    {% for tid, info in results.items() -%}
    ║  {{ info.label }} ({{ info.tier }})
    {% for metric, value in info.metrics.items() -%}
    ║    {{ "%-15s" | format(metric) }}  {{ value }}
    {% endfor -%}
    ║
    {% endfor -%}
    ╚══════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════════════════
# 2. Load & expand
# ═══════════════════════════════════════════════════════════════════════════

print("=== Phase 1: Load & Expand Configuration ===\n")

raw_config = load_yaml_from_string(CONFIG_YAML)

runtime_params = {
    "active_tenants": [
        {"id": "acme", "name": "Acme Corp", "tier": "premium"},
        {"id": "globex", "name": "Globex Inc", "tier": "standard"},
    ],
    "custom_aggregations": [
        {"name": "total", "description": "Sum of transaction amounts", "func": "sum"},
        {"name": "maximum", "description": "Largest single transaction", "func": "max"},
    ],
    "display_precision": 2,
}

expanded = extend_structure(raw_config, template_kwargs={"default": runtime_params})

print("  Tenant specs:")
for tid, spec in expanded["platform"]["tenants"].items():
    print(f"    {tid}: {dict(spec)}")

print("\n  Aggregation tools:")
for agg in expanded["platform"]["aggregations"]:
    print(f"    - {agg['name']}: {agg['description']}")

print(f"\n  Display precision: {expanded['platform']['display']['precision']}")

# ═══════════════════════════════════════════════════════════════════════════
# 3. FlexSpec reads expanded config
# ═══════════════════════════════════════════════════════════════════════════

print("\n=== Phase 2: FlexSpec Reads Expanded Config ===\n")

config_spec = FlexSpec.model_validate(
    {
        "platform_name": "platform.name",
        "tenants": "platform.tenants",
        "aggregations": "platform.aggregations",
        "precision": "platform.display.precision",
        "report_tpl": "platform.report_template",
    }
)
cfg = config_spec(expanded)

print(f"  Platform:     {cfg['platform_name']}")
print(f"  Tenants:      {list(cfg['tenants'].keys())}")
print(f"  Aggregations: {[a['name'] for a in cfg['aggregations']]}")
print(f"  Precision:    {cfg['precision']}")

# ═══════════════════════════════════════════════════════════════════════════
# 4. Build aggregation tools with Instantiator
# ═══════════════════════════════════════════════════════════════════════════

print("\n=== Phase 3: Build Aggregation Tools ===\n")

agg_tools = {}
for agg in cfg["aggregations"]:
    tool = instantiate(dict(agg["tool"]))
    agg_tools[agg["name"]] = tool
    print(f"  Built tool: {agg['name']} → {tool}")

# Also build a rounder for display formatting
rounder = instantiate(["_obj_", {"_addr_": "round"}, {"_bind_": {"ndigits": cfg["precision"]}}])

# ═══════════════════════════════════════════════════════════════════════════
# 5. Process each tenant
# ═══════════════════════════════════════════════════════════════════════════

print("\n=== Phase 4: Process Each Tenant ===\n")

# Raw data warehouse
warehouse_data = {
    "warehouse": {
        "acme": {
            "transactions": [1200.50, 3400.75, 2800.00, 5100.25, 1900.80],
        },
        "globex": {
            "transactions": [800.00, 1500.30, 2200.90],
        },
    }
}

results = {}

for tid, tenant_spec_data in cfg["tenants"].items():
    # FlexSpec interprets each tenant's spec: paths + constants
    tenant_spec = FlexSpec.model_validate(dict(tenant_spec_data))
    tenant_info = tenant_spec(warehouse_data)

    print(f"  Tenant: {tenant_info['label']} ({tenant_info['tier']})")
    print(f"    Transactions: {tenant_info['transactions']}")

    # Apply each aggregation tool
    metrics = {}
    for name, tool in agg_tools.items():
        raw_value = tool(tenant_info["transactions"])
        metrics[name] = rounder(raw_value) if isinstance(raw_value, float) else raw_value
        print(f"    {name}: {metrics[name]}")

    results[tid] = {
        "label": tenant_info["label"],
        "tier": tenant_info["tier"],
        "metrics": metrics,
    }
    print()

# ═══════════════════════════════════════════════════════════════════════════
# 6. Render analytics report
# ═══════════════════════════════════════════════════════════════════════════

print("=== Phase 5: Render Analytics Report ===\n")

report = JinjaTemplate.model_validate({"_jinja_": cfg["report_tpl"]})(
    platform_name=cfg["platform_name"],
    results=results,
)
print(report)
