"""StructCast Advanced Example 06: Config-Driven Data Pipeline.

Demonstrates building a complete data processing pipeline from YAML
configuration by integrating Instantiator (to create transformers),
Specifier (to extract input data), and Template (to format output).
"""

from structcast.core.instantiator import instantiate
from structcast.core.specifier import construct, convert_spec
from structcast.core.template import JinjaTemplate
from structcast.utils.base import load_yaml_from_string

# ═══════════════════════════════════════════════════════════════════════════
# Scenario: A data pipeline that reads raw records, builds processing
# functions from config, extracts fields with specifiers, and renders
# a report with templates.
# ═══════════════════════════════════════════════════════════════════════════

# ---------------------------------------------------------------------------
# 1. Raw source data (could come from an API, database, etc.)
# ---------------------------------------------------------------------------
raw_data = {
    "records": [
        {"id": 1, "name": "Alice", "score": 85, "department": "engineering"},
        {"id": 2, "name": "Bob", "score": 92, "department": "engineering"},
        {"id": 3, "name": "Charlie", "score": 78, "department": "marketing"},
        {"id": 4, "name": "Diana", "score": 95, "department": "engineering"},
        {"id": 5, "name": "Eve", "score": 88, "department": "marketing"},
    ],
    "metadata": {
        "source": "quarterly_review",
        "period": "2026-Q1",
    },
}

# ---------------------------------------------------------------------------
# 2. Pipeline configuration in YAML
# ---------------------------------------------------------------------------
pipeline_yaml = """\
# Specifier: extract fields from raw data
extract:
  all_names: "records"
  report_source: "metadata.source"
  report_period: "metadata.period"

# Instantiator: build processing functions
processors:
  sorter:
    _obj_:
      - _addr_: sorted
        _file_: null
      - _bind_:
          key: ["_obj_", {"_addr_": "operator.itemgetter"}, {"_call_": "score"}]
          reverse: true

# Template: format the final report
report_template:
  _jinja_: |
    === {{ title }} ===
    Period: {{ period }}
    Source: {{ source }}
    {% for entry in rankings %}
    {{ loop.index }}. {{ entry.name }} ({{ entry.department }}) - Score: {{ entry.score }}
    {% endfor %}
    Total participants: {{ total }}
"""

pipeline_config = load_yaml_from_string(pipeline_yaml)

# ---------------------------------------------------------------------------
# 3. Phase 1 — Extract data with Specifier
# ---------------------------------------------------------------------------
print("Phase 1: Extracting data with Specifier...")
extract_spec = convert_spec(pipeline_config["extract"])
extracted = construct(raw_data, extract_spec)

print(f"  Report source: {extracted['report_source']}")
print(f"  Report period: {extracted['report_period']}")
print(f"  Records count: {len(extracted['all_names'])}")

# ---------------------------------------------------------------------------
# 4. Phase 2 — Build processors with Instantiator
# ---------------------------------------------------------------------------
print("\nPhase 2: Building processors with Instantiator...")
processors = instantiate(pipeline_config["processors"])

# Use the instantiated sorter (sorted with key=itemgetter('score'), reverse=True)
sorted_records = processors["sorter"](extracted["all_names"])
print("  Sorted records by score (descending):")
for rec in sorted_records:
    print(f"    {rec['name']}: {rec['score']}")

# ---------------------------------------------------------------------------
# 5. Phase 3 — Render report with Template
# ---------------------------------------------------------------------------
print("\nPhase 3: Rendering report with Template...")
report_tpl = JinjaTemplate.model_validate(pipeline_config["report_template"])

report = report_tpl(
    title="Quarterly Performance Report",
    period=extracted["report_period"],
    source=extracted["report_source"],
    rankings=sorted_records,
    total=len(sorted_records),
)
print(report)
