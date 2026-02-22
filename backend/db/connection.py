"""SQLite connection singleton for the HVAC backend."""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "hvac.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

_connection: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    """Return the singleton SQLite connection (creates if needed)."""
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode = WAL")
        _connection.execute("PRAGMA foreign_keys = ON")
    return _connection


def init_db() -> None:
    """Create all tables from schema.sql."""
    db = get_db()
    schema_sql = SCHEMA_PATH.read_text()
    db.executescript(schema_sql)
    db.commit()


def reset_db() -> None:
    """Delete and recreate the database."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Execute a SELECT and return all rows."""
    return get_db().execute(sql, params).fetchall()


def query_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    """Execute a SELECT and return one row."""
    return get_db().execute(sql, params).fetchone()


def execute(sql: str, params: tuple = ()) -> None:
    """Execute a write statement."""
    db = get_db()
    db.execute(sql, params)
    db.commit()


def executemany(sql: str, params_list: list[tuple]) -> None:
    """Execute a write statement with many parameter sets."""
    db = get_db()
    db.executemany(sql, params_list)
    db.commit()
