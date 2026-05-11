"""Team unit — persistent teammates, file-backed task board, and the message bus."""
from core.unit.team.messaging import (
    VALID_MSG_TYPES,
    MessageBus,
    new_request_id,
    plan_requests,
    shutdown_requests,
)
from core.unit.team.tasks_file import TaskManager
from core.unit.team.team import TeammateManager

__all__ = [
    "TeammateManager",
    "TaskManager",
    "MessageBus",
    "VALID_MSG_TYPES",
    "plan_requests",
    "shutdown_requests",
    "new_request_id",
]
