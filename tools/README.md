# Agent tools

This package holds every tool the lead agent can call. Each tool lives in
its own module so a code reviewer can read one screen and understand one
tool. `tool_register.py` glues them together.

## Module contract

Every tool module must export:

* `SPEC` — an Anthropic-shaped tool spec:

  ```python
  SPEC = {
      "name": "<public tool name>",
      "description": "<one-paragraph guidance for the model>",
      "input_schema": { ... JSON schema ... },
  }
  ```

* A top-level callable whose attribute name matches the module's filename
  (e.g. `tools/read_file.py` exports `def read_file(...) -> str`). The
  return value should be a string the agent will read directly.

There is no per-module registration call — `tool_register.py` discovers
handlers by convention.

## Adding a new tool

1. Create `tools/<your_tool>.py`.
2. Define `SPEC` and a handler function with the matching name.
3. Add the module to the right group in `tool_register.TOOL_GROUPS`.

`TOOL_SPECS`, `TOOL_HANDLERS`, and `call_tool()` pick it up automatically —
no other edits required.

## Usage

```python
from tools import tool_register

# Pass straight to the LLM client
client.create_message(
    system=...,
    tools=tool_register.TOOL_SPECS,
    messages=[...],
)

# Dispatch a tool_use block returned by the model
result = tool_register.call_tool("read_file", {"path": "main.py"})
```

## Tool index

Run `python -c "from tools.tool_register import TOOL_GROUPS; \
import json; \
print(json.dumps({g: [m.SPEC['name'] for m in mods] for g, mods in TOOL_GROUPS.items()}, indent=2))"`
to see the live grouping.
