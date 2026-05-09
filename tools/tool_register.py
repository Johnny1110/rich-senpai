"""Single source of truth for the lead agent's tool surface.

Every tool module exposes:

* ``SPEC``    — an Anthropic-shaped tool spec ``{name, description, input_schema}``
* a top-level callable whose attribute name matches the module name
  (e.g. ``tools.read_file`` exports ``read_file``)

Adding a tool is therefore a two-step change: create the module, then drop
its reference into the appropriate group below. ``TOOL_SPECS`` and
``TOOL_HANDLERS`` are derived automatically from the grouped list — no
parallel imports / dicts to keep in sync.

The grouping is purely organisational; downstream code sees a single flat
``TOOL_SPECS`` list, ordered group-by-group.
"""
from __future__ import annotations

from types import ModuleType
from typing import Any, Callable

from tools import (
    background_run,
    bash,
    broadcast,
    check_background,
    claim_task,
    compress,
    edit_file,
    http_request,
    idle,
    list_teammates,
    load_skill,
    plan_approval,
    read_file,
    read_inbox,
    send_message,
    shutdown_request,
    spawn_teammate,
    task,
    task_create,
    task_get,
    task_list,
    task_update,
    todo_write,
    update_short_memory,
    wait,
    write_file,
)


# ---------------------------------------------------------------------------
# Tool catalogue. Order inside each group is preserved in TOOL_SPECS so the
# model sees related tools next to each other.
# ---------------------------------------------------------------------------
TOOL_GROUPS: dict[str, list[ModuleType]] = {
    "fs_shell_data": [
        read_file,
        write_file,
        edit_file,
        bash,
        background_run,
        check_background,
        http_request,
        update_short_memory,
    ],
    "working_memory": [
        todo_write,
        task_create,
        task_get,
        task_update,
        task_list,
        claim_task,
    ],
    "delegation": [
        task,
        spawn_teammate,
        list_teammates,
        send_message,
        read_inbox,
        broadcast,
        shutdown_request,
        plan_approval,
    ],
    "context_management": [
        load_skill,
        compress,
        idle,
        wait,
    ],
}


def _handler_for(module: ModuleType) -> Callable[..., str]:
    """Resolve a tool module's callable handler.

    Convention: the handler attribute name equals the module's last path
    segment (``tools.read_file`` -> ``read_file``).
    """
    func_name = module.__name__.rsplit(".", 1)[-1]
    handler = getattr(module, func_name, None)
    if not callable(handler):
        raise RuntimeError(
            f"tool module '{module.__name__}' is missing a callable "
            f"named '{func_name}'"
        )
    return handler


_ALL_MODULES: list[ModuleType] = [
    module for group in TOOL_GROUPS.values() for module in group
]

TOOL_SPECS: list[dict[str, Any]] = [m.SPEC for m in _ALL_MODULES]

TOOL_HANDLERS: dict[str, Callable[..., str]] = {
    m.SPEC["name"]: _handler_for(m) for m in _ALL_MODULES
}


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> str:
    """Dispatch a tool_use block by name.

    Returns the handler's string output, or an error string when the tool
    is unknown / arguments don't match the handler signature.
    """
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return f"error: unknown tool '{name}'"
    try:
        return handler(**(arguments or {}))
    except TypeError as exc:
        return f"error: invalid arguments for '{name}': {exc}"
