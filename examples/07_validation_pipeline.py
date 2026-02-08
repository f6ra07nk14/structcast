"""StructCast Advanced Example 07: Multi-Step Data Validation Pipeline.

Demonstrates _jinja_yaml_ in **list** context (sequence pattern) where
dynamic validation steps are spliced into a static pipeline, plus
_jinja_yaml_ in mapping context for dynamic output settings.

Workflow:
  1. YAML config with both list-embedded and mapping-embedded _jinja_yaml_
  2. load_yaml_from_string → extend_structure expands all templates
  3. FlexSpec reads the expanded pipeline config
  4. FlexSpec extracts input fields from a raw data payload
  5. Instantiator builds processing tools from step definitions
  6. Steps execute sequentially on the extracted data
  7. JinjaTemplate renders a processing summary

Sequence pattern recap::

    steps:
      - static_step_1
      - _jinja_yaml_: |
          - generated_step_a
          - generated_step_b
      - static_step_2

    →  after extend_structure the generated items are spliced into the list.
"""

from structcast.core.instantiator import instantiate
from structcast.core.specifier import FlexSpec
from structcast.core.template import JinjaTemplate, extend_structure
from structcast.utils.base import load_yaml_from_string

# ═══════════════════════════════════════════════════════════════════════════
# 1. YAML configuration with _jinja_yaml_ in BOTH list and mapping contexts
# ═══════════════════════════════════════════════════════════════════════════

CONFIG_YAML = """\
pipeline:
  name: User Data Validation

  # FlexSpec-compatible paths for extracting fields from a raw payload
  input_mapping:
    user_id: "payload.user.id"
    user_name: "payload.user.name"
    user_email: "payload.user.email"
    score: "payload.metrics.score"
    age: "payload.metrics.age"

  # ── List (sequence) pattern ──────────────────────────────────────
  # Static steps + dynamically generated validation steps.
  # _jinja_yaml_ inside a list item must produce a YAML sequence;
  # its items are spliced into the parent list at that position.
  steps:
    - name: extract
      description: Extract fields from payload
    - _jinja_yaml_: |
        {% for rule in validation_rules %}
        - name: "check_{{ rule.field }}"
          type: range_check
          field: "{{ rule.field }}"
          min_value: {{ rule.min }}
          max_value: {{ rule.max }}
        {% endfor %}
    - name: format
      description: Round numeric fields
      tool:
        _obj_:
          - _addr_: round
          - _bind_:
              ndigits: 0

  # ── Mapping pattern ─────────────────────────────────────────────
  # Static output format + dynamic destination and settings.
  output:
    format: summary
    _jinja_yaml_: |
      destination: "{{ output_dest }}"
      include_timestamp: {{ include_ts | lower }}

  # Report template (plain string — rendered manually later)
  summary_template: |
    ╔═══════════════════════════════════════════╗
    ║  Pipeline: {{ pipeline_name }}
    ╠═══════════════════════════════════════════╣
    {% for r in results -%}
    ║  [{{ r.step }}] {{ r.status }}{{ " — " ~ r.detail if r.detail else "" }}
    {% endfor -%}
    ╠═══════════════════════════════════════════╣
    ║  Output: {{ destination }} ({{ format }})
    ╚═══════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════════════════
# 2. Load & expand
# ═══════════════════════════════════════════════════════════════════════════

print("=== Phase 1: Load & Expand Configuration ===\n")

raw_config = load_yaml_from_string(CONFIG_YAML)

runtime_params = {
    "validation_rules": [
        {"field": "score", "min": 0, "max": 100},
        {"field": "age", "min": 0, "max": 150},
    ],
    "output_dest": "report_database",
    "include_ts": True,
}

expanded = extend_structure(raw_config, template_kwargs={"default": runtime_params})

print("  Expanded steps:")
for step in expanded["pipeline"]["steps"]:
    print(f"    - {step.get('name', '?')}: {step.get('description', step.get('type', ''))}")

print("\n  Expanded output:")
for k, v in expanded["pipeline"]["output"].items():
    print(f"    {k}: {v}")

# ═══════════════════════════════════════════════════════════════════════════
# 3. FlexSpec reads expanded config
# ═══════════════════════════════════════════════════════════════════════════

print("\n=== Phase 2: FlexSpec Reads Expanded Config ===\n")

config_spec = FlexSpec.model_validate(
    {
        "name": "pipeline.name",
        "input_map": "pipeline.input_mapping",
        "steps": "pipeline.steps",
        "output": "pipeline.output",
        "summary_tpl": "pipeline.summary_template",
    }
)
cfg = config_spec(expanded)

print(f"  Pipeline:  {cfg['name']}")
print(f"  Steps:     {len(cfg['steps'])}")
print(f"  Output to: {cfg['output']['destination']}")

# ═══════════════════════════════════════════════════════════════════════════
# 4. Extract input data from a raw payload with FlexSpec
# ═══════════════════════════════════════════════════════════════════════════

print("\n=== Phase 3: Extract Input Data ===\n")

raw_payload = {
    "payload": {
        "user": {
            "id": "U-1042",
            "name": "Diana Prince",
            "email": "diana@example.com",
        },
        "metrics": {"score": 87.6, "age": 32},
    }
}

input_spec = FlexSpec.model_validate(dict(cfg["input_map"]))
fields = input_spec(raw_payload)

for k, v in fields.items():
    print(f"  {k}: {v}")

# ═══════════════════════════════════════════════════════════════════════════
# 5. Execute pipeline steps
# ═══════════════════════════════════════════════════════════════════════════

print("\n=== Phase 4: Execute Pipeline Steps ===\n")

results = []

for step in cfg["steps"]:
    step_name = step["name"]

    if step_name == "extract":
        results.append(
            {
                "step": step_name,
                "status": "OK",
                "detail": f"{len(fields)} fields extracted",
            }
        )

    elif step.get("type") == "range_check":
        field = step["field"]
        val = fields.get(field)
        lo, hi = step["min_value"], step["max_value"]
        if val is not None and lo <= val <= hi:
            results.append(
                {
                    "step": step_name,
                    "status": "PASS",
                    "detail": f"{field}={val} in [{lo}, {hi}]",
                }
            )
        else:
            results.append(
                {
                    "step": step_name,
                    "status": "FAIL",
                    "detail": f"{field}={val} outside [{lo}, {hi}]",
                }
            )

    elif step_name == "format":
        tool = instantiate(dict(step["tool"]))
        for k in ("score", "age"):
            if k in fields and isinstance(fields[k], (int, float)):
                fields[k] = tool(fields[k])
        results.append({"step": step_name, "status": "OK", "detail": "numeric fields rounded"})

for r in results:
    icon = "✓" if r["status"] in ("OK", "PASS") else "✗"
    print(f"  {icon} [{r['step']}] {r['status']}: {r['detail']}")

# ═══════════════════════════════════════════════════════════════════════════
# 6. Render summary report
# ═══════════════════════════════════════════════════════════════════════════

print("\n=== Phase 5: Render Summary Report ===\n")

report = JinjaTemplate.model_validate({"_jinja_": cfg["summary_tpl"]})(
    pipeline_name=cfg["name"],
    results=results,
    destination=cfg["output"]["destination"],
    format=cfg["output"]["format"],
)
print(report)
