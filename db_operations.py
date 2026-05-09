"""Core PostgreSQL access layer.

Exposes `execute_sql(query)` — a single entry point that:
  * Reuses a process-wide threaded connection pool.
  * Optionally rejects mutating statements when read-only mode is enabled.
  * Wraps every call in a transaction that rolls back on any failure.

Designed to be wrapped as an agent tool in Phase 2 / 3 without changes here.
"""
from __future__ import annotations

import re
import threading
from typing import Any

import psycopg2
from psycopg2 import pool as pg_pool

from config import DB_CONFIG


_pool: pg_pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()


def _get_pool() -> pg_pool.ThreadedConnectionPool:
    """Lazily initialize a process-wide threaded connection pool."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = pg_pool.ThreadedConnectionPool(
                    minconn=DB_CONFIG.pool_min,
                    maxconn=DB_CONFIG.pool_max,
                    **DB_CONFIG.connection_kwargs(),
                )
    return _pool


def close_pool() -> None:
    """Close all pooled connections. Useful for tests and clean shutdown."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.closeall()
            _pool = None


_READ_ONLY_PREFIXES = {"SELECT", "WITH", "EXPLAIN", "SHOW", "VALUES", "TABLE"}
_DDL_PREFIXES = {"CREATE", "ALTER", "DROP", "TRUNCATE", "COMMENT", "RENAME"}
_LEADING_COMMENTS = re.compile(r"\s*(?:--[^\n]*\n|/\*.*?\*/)\s*", re.DOTALL)


def _strip_leading_noise(query: str) -> str:
    text = query.lstrip()
    while True:
        match = _LEADING_COMMENTS.match(text)
        if not match:
            break
        text = text[match.end():]
    return text.lstrip("(").lstrip()


def _first_keyword(query: str) -> str:
    stripped = _strip_leading_noise(query)
    if not stripped:
        return ""
    head = stripped.split(None, 1)[0]
    return head.rstrip(";").upper()


def _is_read_only_statement(query: str) -> bool:
    return _first_keyword(query) in _READ_ONLY_PREFIXES


def _is_ddl_statement(query: str) -> bool:
    return _first_keyword(query) in _DDL_PREFIXES


def _trigger_schema_sync() -> str | None:
    """Run the schema sync hook. Imported lazily to avoid a circular import
    with schema_manager (which imports this module). Returns a short status
    message on failure so the caller can surface it; returns None on success.
    """
    try:
        from schema_manager import sync_schema_desc
        result = sync_schema_desc()
    except Exception as exc:  # broad on purpose: a sync failure must not raise
        return f"schema_desc.md auto-sync failed: {exc}"
    if result.startswith("error:"):
        return f"schema_desc.md auto-sync {result}"
    return None


def _format_rows(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    if not rows:
        return "ok: 0 rows\n" + " | ".join(columns)
    widths = [len(col) for col in columns]
    str_rows = [tuple("" if v is None else str(v) for v in row) for row in rows]
    for row in str_rows:
        for i, value in enumerate(row):
            if len(value) > widths[i]:
                widths[i] = len(value)
    header = " | ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
    sep = "-+-".join("-" * w for w in widths)
    body = "\n".join(
        " | ".join(value.ljust(widths[i]) for i, value in enumerate(row))
        for row in str_rows
    )
    return f"ok: {len(rows)} rows\n{header}\n{sep}\n{body}"


def execute_sql(query: str) -> str:
    """Execute a SQL statement and return a human-readable string result.

    * SELECT / EXPLAIN / WITH return a formatted table of rows.
    * INSERT / UPDATE / DELETE / DDL return a row-count summary.
    * Any failure rolls back the transaction and returns an error string.
    * If `DB_READ_ONLY=true`, non-SELECT statements are rejected before
      they reach the database.
    """
    if not isinstance(query, str) or not query.strip():
        return "error: query must be a non-empty string"

    if DB_CONFIG.read_only and not _is_read_only_statement(query):
        first = _first_keyword(query) or "<empty>"
        return f"error: read-only mode rejected statement starting with {first!r}"

    try:
        pool_ = _get_pool()
    except psycopg2.Error as exc:
        return f"error: could not initialize connection pool: {exc}"

    conn = None
    result: str
    try:
        conn = pool_.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    if cursor.description is None:
                        if cursor.rowcount < 0:
                            result = "ok: statement executed"
                        else:
                            result = f"ok: {cursor.rowcount} rows affected"
                    else:
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        result = _format_rows(columns, rows)
        except psycopg2.Error as exc:
            return f"error: query failed and was rolled back: {exc}"
    except psycopg2.Error as exc:
        return f"error: could not acquire connection: {exc}"
    finally:
        if conn is not None:
            pool_.putconn(conn)

    if _is_ddl_statement(query):
        sync_warning = _trigger_schema_sync()
        if sync_warning is None:
            result += "\n[hook: schema_desc.md auto-synced]"
        else:
            result += f"\n[hook: warning — {sync_warning}]"

    return result
