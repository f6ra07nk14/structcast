"""StructCast Advanced Example 08: Multi-Stage Transform with Pipe.

Demonstrates how to chain Specifier extraction with Instantiator-built
post-processing pipes and Template rendering to implement a multi-stage
data transformation — all expressed as serializable configuration.
"""

from structcast.core.instantiator import instantiate
from structcast.core.specifier import FlexSpec, construct, convert_spec
from structcast.core.template import JinjaTemplate

# ═══════════════════════════════════════════════════════════════════════════
# Scenario: Extract values from source data, apply transformation pipes
# (type casting, formatting), then assemble a final report.
# ═══════════════════════════════════════════════════════════════════════════

# ---------------------------------------------------------------------------
# 1. Source data
# ---------------------------------------------------------------------------
source = {
    "sensor_readings": {
        "temperature": "23.7",
        "humidity": "61.2",
        "pressure": "1013.25",
    },
    "device": {
        "id": "SENSOR-42",
        "location": "Building A, Floor 3",
        "firmware": "2.4.1",
    },
}

# ---------------------------------------------------------------------------
# 2. FlexSpec with _pipe_ — extract + transform in one step
# ---------------------------------------------------------------------------
print("=== Phase 1: Spec + Pipe extraction ===\n")

# Extract temperature as float via pipe (instantiator builds `float`)
temp_spec = FlexSpec.model_validate(
    {
        "_spec_": "sensor_readings.temperature",
        "_pipe_": ["_obj_", {"_addr_": "float"}],
    }
)
temperature = temp_spec(source)
print(f"  Temperature (float): {temperature} (type: {type(temperature).__name__})")

# Extract humidity as float
humidity_spec = FlexSpec.model_validate(
    {
        "_spec_": "sensor_readings.humidity",
        "_pipe_": ["_obj_", {"_addr_": "float"}],
    }
)
humidity = humidity_spec(source)
print(f"  Humidity (float):    {humidity} (type: {type(humidity).__name__})")

# Extract pressure as float
pressure_spec = FlexSpec.model_validate(
    {
        "_spec_": "sensor_readings.pressure",
        "_pipe_": ["_obj_", {"_addr_": "float"}],
    }
)
pressure = pressure_spec(source)
print(f"  Pressure (float):    {pressure} (type: {type(pressure).__name__})")

# ---------------------------------------------------------------------------
# 3. Instantiate helper objects for further processing
# ---------------------------------------------------------------------------
print("\n=== Phase 2: Instantiate processing tools ===\n")

# Build a rounding function with precision=1
rounder = instantiate(["_obj_", {"_addr_": "round"}, {"_bind_": {"ndigits": 1}}])
print(f"  rounder(23.756) = {rounder(23.756)}")

# Build an OrderedDict from the processed values
processed = instantiate(
    {
        "_obj_": [
            {"_addr_": "collections.OrderedDict"},
            {
                "_call_": {
                    "temperature": rounder(temperature),
                    "humidity": rounder(humidity),
                    "pressure": rounder(pressure),
                }
            },
        ]
    }
)
print(f"  Processed readings: {dict(processed)}")

# ---------------------------------------------------------------------------
# 4. Plain specifier to extract device info
# ---------------------------------------------------------------------------
print("\n=== Phase 3: Extract device metadata ===\n")

device_spec = convert_spec(
    {
        "device_id": "device.id",
        "location": "device.location",
        "firmware": "device.firmware",
    }
)
device_info = construct(source, device_spec)
for k, v in device_info.items():
    print(f"  {k}: {v}")

# ---------------------------------------------------------------------------
# 5. Render a combined report via Template
# ---------------------------------------------------------------------------
print("\n=== Phase 4: Render report with Template ===\n")

report_tpl = JinjaTemplate.model_validate(
    {
        "_jinja_": """\
╔══════════════════════════════════════╗
║       Sensor Status Report           ║
╠══════════════════════════════════════╣
║ Device:   {{ device_id }}
║ Location: {{ location }}
║ Firmware: v{{ firmware }}
╠══════════════════════════════════════╣
║ Readings:
{% for name, value in readings.items() -%}
║   {{ "%-15s" | format(name) }} {{ value }}
{% endfor -%}
╚══════════════════════════════════════╝\
"""
    }
)

report = report_tpl(
    **device_info,
    readings=dict(processed),
)
print(report)
