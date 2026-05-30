"""Canonical filesystem paths for the application.

All modules that need to resolve a data path should import from here::

    from core.paths import PROJECTS_DIR, DB_PATH

The PROJECTS_DATA_DIR environment variable overrides the default location.
This allows Docker volume mounts without patching module globals at startup.
"""

import os
from pathlib import Path

# ── Runtime override (Docker volume, test isolation) ──────────────────────────
_data_dir_env = os.environ.get("PROJECTS_DATA_DIR", "")
PROJECTS_DIR: Path = Path(_data_dir_env) if _data_dir_env else Path("projects_data")

# Derived paths — all relative to PROJECTS_DIR
PROJECTS_FILE: Path = PROJECTS_DIR / "projects.json"
DB_PATH: Path = PROJECTS_DIR / "accelerator.db"
