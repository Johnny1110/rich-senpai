"""Centralized configuration loaded from environment variables.

Reads a local .env file if present (via python-dotenv) so credentials never
have to be hardcoded. Import `DB_CONFIG` for psycopg2 connection params.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _get_env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or value == ""):
        raise RuntimeError(f"missing required environment variable: {name}")
    return value or ""


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"invalid integer for {name}: {raw!r}") from exc


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str
    pool_min: int
    pool_max: int
    read_only: bool

    def connection_kwargs(self) -> dict[str, str | int]:
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
        }


DB_CONFIG = DBConfig(
    host=_get_env("POSTGRES_HOST", "localhost"),
    port=_get_int("POSTGRES_PORT", 5432),
    dbname=_get_env("POSTGRES_DB", "agent_db"),
    user=_get_env("POSTGRES_USER", "agent"),
    password=_get_env("POSTGRES_PASSWORD", "agent_password"),
    pool_min=_get_int("DB_POOL_MIN", 1),
    pool_max=_get_int("DB_POOL_MAX", 5),
    read_only=_get_bool("DB_READ_ONLY", False),
)
