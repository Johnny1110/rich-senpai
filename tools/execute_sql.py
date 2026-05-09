# execute_sql tool — thin wrapper exposing db_operations.execute_sql to the agent.
from db import db_operations

SPEC = {
    "name": "execute_sql",
    "description": (
        "Execute a single SQL statement against the agent's PostgreSQL "
        "database and return a string containing either the result rows "
        "or a status message. Each call runs inside its own transaction "
        "that is automatically rolled back if the statement fails. "
        "Supports SELECT, INSERT, UPDATE, DELETE, and DDL (CREATE/ALTER/"
        "DROP). When DB_READ_ONLY is enabled in the environment, only "
        "SELECT-style statements are allowed. Always apply LIMIT 100 to "
        "exploratory SELECTs to avoid flooding the response."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A single SQL statement to execute.",
            },
        },
        "required": ["query"],
    },
}


def execute_sql(query: str) -> str:
    return db_operations.execute_sql(query)
