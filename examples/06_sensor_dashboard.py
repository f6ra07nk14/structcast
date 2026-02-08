"""StructCast Advanced Example 06: IoT Sensor Monitoring Dashboard.

Demonstrates the full workflow:
  YAML config with _jinja_yaml_ (mapping pattern)
  → load_yaml_from_string → extend_structure → FlexSpec → data processing

The YAML config uses _jinja_yaml_ inside mapping contexts to dynamically
merge sensor paths, alert thresholds, and an Instantiator pattern into
static configuration at runtime.  FlexSpec reads the expanded config,
then a second FlexSpec uses the extracted sensor mapping to pull values
from raw device data.  Instantiator builds a rounding processor, and
JinjaTemplate renders the final dashboard report.

Mapping pattern recap::

    some_section:
        static_key: value
        _jinja_yaml_: |
          dynamic_key: {{ dynamic_value }}

    →  after extend_structure the template output merges into the parent dict.
"""

from structcast.core.instantiator import instantiate
from structcast.core.specifier import FlexSpec
from structcast.core.template import JinjaTemplate, extend_structure
from structcast.utils.base import load_yaml_from_string

# ═══════════════════════════════════════════════════════════════════════════
# 1. YAML configuration with _jinja_yaml_ in mapping context
#
#    Static keys coexist with _jinja_yaml_ inside the same dict.
#    extend_structure renders the template and merges the result into
#    the surrounding mapping.
# ═══════════════════════════════════════════════════════════════════════════

CONFIG_YAML = """\
dashboard:
  title: Sensor Monitoring Dashboard
  version: "2.0"

  # ── Mapping pattern ──────────────────────────────────────────────
  # Static sensor paths + dynamic extras merged at runtime.
  sensor_mapping:
    temperature: "readings.sensors.temperature"
    humidity: "readings.sensors.humidity"
    _jinja_yaml_: |
      {% if include_pressure %}
      pressure: "readings.sensors.pressure"
      {% endif %}
      {% if include_wind %}
      wind_speed: "readings.wind.speed"
      wind_direction: "readings.wind.direction"
      {% endif %}

  # ── Mapping pattern ──────────────────────────────────────────────
  # Static alert flag + dynamic thresholds.
  alerts:
    enabled: true
    _jinja_yaml_: |
      thresholds:
        temperature_max: {{ temp_max }}
        humidity_max: {{ humidity_max }}
        {% if include_pressure %}
        pressure_min: {{ pressure_min }}
        pressure_max: {{ pressure_max }}
        {% endif %}

  # ── Mapping pattern ──────────────────────────────────────────────
  # Entire Instantiator pattern generated from template.
  processor:
    _jinja_yaml_: |
      _obj_:
        - _addr_: round
        - _bind_:
            ndigits: {{ precision }}

  # Plain string template (NOT a _jinja_ pattern — survives extend_structure).
  # Rendered manually at report time with JinjaTemplate.
  report_template: |
    ╔════════════════════════════════════════════╗
    ║  {{ title }}
    ╠════════════════════════════════════════════╣
    {% for name, value in readings.items() -%}
    ║  {{ "%-20s" | format(name) }}  {{ value }}
    {% endfor -%}
    ╠════════════════════════════════════════════╣
    {% for msg in alerts -%}
    ║  ⚠ {{ msg }}
    {% endfor -%}
    ╚════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════════════════
# 2. Load YAML and expand templates with runtime parameters
# ═══════════════════════════════════════════════════════════════════════════

print("=== Phase 1: Load & Expand Configuration ===\n")

raw_config = load_yaml_from_string(CONFIG_YAML)

# Runtime parameters (e.g. from CLI flags or environment)
runtime_params = {
    "include_pressure": True,
    "include_wind": False,
    "temp_max": 40.0,
    "humidity_max": 85.0,
    "pressure_min": 950.0,
    "pressure_max": 1050.0,
    "precision": 1,
}

expanded = extend_structure(raw_config, template_kwargs={"default": runtime_params})

print("  Expanded sensor_mapping:")
for key, val in expanded["dashboard"]["sensor_mapping"].items():
    print(f"    {key}: {val}")

print("\n  Expanded alert thresholds:")
for key, val in expanded["dashboard"]["alerts"]["thresholds"].items():
    print(f"    {key}: {val}")

print(f"\n  Expanded processor: {dict(expanded['dashboard']['processor'])}")

# ═══════════════════════════════════════════════════════════════════════════
# 3. FlexSpec reads the expanded configuration
# ═══════════════════════════════════════════════════════════════════════════

print("\n=== Phase 2: FlexSpec Reads Expanded Config ===\n")

config_spec = FlexSpec.model_validate(
    {
        "title": "dashboard.title",
        "sensor_paths": "dashboard.sensor_mapping",
        "thresholds": "dashboard.alerts.thresholds",
        "processor": "dashboard.processor",
        "report_tpl": "dashboard.report_template",
    }
)
app = config_spec(expanded)

print(f"  title:        {app['title']}")
print(f"  sensor_paths: {dict(app['sensor_paths'])}")
print(f"  thresholds:   {dict(app['thresholds'])}")

# ═══════════════════════════════════════════════════════════════════════════
# 4. Second FlexSpec: use sensor_paths as spec to extract from device data
#
#    The sensor_paths dict extracted from config contains FlexSpec-compatible
#    strings (e.g. "readings.sensors.temperature").  We feed them directly
#    into a new FlexSpec that navigates the raw device payload.
# ═══════════════════════════════════════════════════════════════════════════

print("\n=== Phase 3: Extract Sensor Readings from Device ===\n")

raw_device_data = {
    "readings": {
        "sensors": {
            "temperature": 38.264,
            "humidity": 72.891,
            "pressure": 1012.456,
        },
        "wind": {"speed": 12.7, "direction": "NW"},
    },
    "device": {"id": "WS-001", "location": "Rooftop A"},
}

sensor_spec = FlexSpec.model_validate(dict(app["sensor_paths"]))
raw_readings = sensor_spec(raw_device_data)

print("  Raw sensor readings:")
for name, val in raw_readings.items():
    print(f"    {name}: {val}")

# ═══════════════════════════════════════════════════════════════════════════
# 5. Instantiate processor and apply to readings
# ═══════════════════════════════════════════════════════════════════════════

print("\n=== Phase 4: Process Readings ===\n")

rounder = instantiate(dict(app["processor"]))
processed = {name: rounder(val) for name, val in raw_readings.items()}

print("  Processed (rounded) readings:")
for name, val in processed.items():
    print(f"    {name}: {val}")

# ═══════════════════════════════════════════════════════════════════════════
# 6. Alert checking using configuration thresholds
# ═══════════════════════════════════════════════════════════════════════════

print("\n=== Phase 5: Check Alerts ===\n")

alert_messages: list[str] = []
th = app["thresholds"]

if processed["temperature"] > th["temperature_max"]:
    alert_messages.append(f"Temperature {processed['temperature']} exceeds max {th['temperature_max']}")
if processed["humidity"] > th["humidity_max"]:
    alert_messages.append(f"Humidity {processed['humidity']} exceeds max {th['humidity_max']}")
if "pressure" in processed:
    p = processed["pressure"]
    if p < th.get("pressure_min", 0):
        alert_messages.append(f"Pressure {p} below min {th['pressure_min']}")
    if p > th.get("pressure_max", 9999):
        alert_messages.append(f"Pressure {p} above max {th['pressure_max']}")

if not alert_messages:
    alert_messages.append("All readings within normal range")

for msg in alert_messages:
    print(f"  {msg}")

# ═══════════════════════════════════════════════════════════════════════════
# 7. Render dashboard report with JinjaTemplate
# ═══════════════════════════════════════════════════════════════════════════

print("\n=== Phase 6: Render Dashboard Report ===\n")

report = JinjaTemplate.model_validate({"_jinja_": app["report_tpl"]})(
    title=app["title"],
    readings=processed,
    alerts=alert_messages,
)
print(report)
