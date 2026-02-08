"""StructCast Example 03: Jinja2 Template Rendering.

Demonstrates how to use the template module for dynamic configuration
generation via Jinja2 templates, including YAML/JSON output and
structured extension.
"""

from structcast.core.template import JinjaJsonTemplate, JinjaTemplate, JinjaYamlTemplate, extend_structure

# ---------------------------------------------------------------------------
# 1. Basic Jinja template
# ---------------------------------------------------------------------------
template = JinjaTemplate.model_validate({"_jinja_": "Hello {{ name }}!"})
result = template(name="World")
assert result == "Hello World!"
print(f"Basic template:   {result}")

# ---------------------------------------------------------------------------
# 2. Template with conditional logic
# ---------------------------------------------------------------------------
template = JinjaTemplate.model_validate(
    {
        "_jinja_": """\
{% if debug %}
log_level: DEBUG
{% else %}
log_level: INFO
{% endif %}\
"""
    }
)
debug_result = template(debug=True).strip()
prod_result = template(debug=False).strip()
print(f"Conditional (debug=True):  {debug_result}")
print(f"Conditional (debug=False): {prod_result}")

# ---------------------------------------------------------------------------
# 3. YAML template — renders then parses as YAML
# ---------------------------------------------------------------------------
template = JinjaYamlTemplate.model_validate(
    {
        "_jinja_yaml_": """\
server:
  host: {{ host }}
  port: {{ port }}
  workers: {{ workers }}
"""
    }
)
result = template(host="0.0.0.0", port=8080, workers=4)
print(f"\nYAML template result: {result}")
assert result["server"]["port"] == 8080

# ---------------------------------------------------------------------------
# 4. JSON template — renders then parses as JSON
# ---------------------------------------------------------------------------
template = JinjaJsonTemplate.model_validate({"_jinja_json_": '{"name": "{{ name }}", "version": "{{ version }}"}'})
result = template(name="MyApp", version="2.0")
print(f"JSON template result: {result}")
assert result["name"] == "MyApp"

# ---------------------------------------------------------------------------
# 5. Structured extension — resolve YAML templates inside data structures
# ---------------------------------------------------------------------------
data = {
    "_jinja_yaml_": "greeting: Hello {{ user }}\nfarewell: Goodbye {{ user }}",
}

result = extend_structure(data, template_kwargs={"default": {"user": "Alice"}})
print("\nStructured extension:")
print(f"  greeting: {result['greeting']}")
print(f"  farewell: {result['farewell']}")

# ---------------------------------------------------------------------------
# 6. Template groups — different contexts for different templates
# ---------------------------------------------------------------------------
data = {
    "user_section": {"_jinja_yaml_": 'name: "{{ name }}"', "_jinja_group_": "users"},
    "sys_section": {"_jinja_yaml_": 'version: "{{ version }}"', "_jinja_group_": "system"},
}

result = extend_structure(
    data,
    template_kwargs={
        "users": {"name": "Bob"},
        "system": {"version": "3.1"},
    },
)
print("\nTemplate groups:")
print(f"  user_section: {result['user_section']}")
print(f"  sys_section:  {result['sys_section']}")

# ---------------------------------------------------------------------------
# 7. YAML template with loop
# ---------------------------------------------------------------------------
template = JinjaYamlTemplate.model_validate(
    {
        "_jinja_yaml_": """\
endpoints:
{% for ep in endpoints %}
  - path: {{ ep.path }}
    method: {{ ep.method }}
{% endfor %}
"""
    }
)
result = template(
    endpoints=[
        {"path": "/api/users", "method": "GET"},
        {"path": "/api/users", "method": "POST"},
        {"path": "/api/health", "method": "GET"},
    ]
)
print("\nYAML loop template:")
for ep in result["endpoints"]:
    print(f"  {ep['method']} {ep['path']}")
