"""SQLite database layer for Project Delivery Accelerator Engine.

Provides:
- Database: connection manager + schema initialisation
- db_path(): resolves the DB file path
- get_db(): returns a thread-local Database instance
"""

from .database import Database, get_db, db_path

__all__ = ["Database", "get_db", "db_path"]
