"""System Health – Operational visibility for admin dashboard.

Tracks:
- Last intelligence run status
- API connectivity status (Groq, Gemini, etc.)
- System resource summary
- Backend availability
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

HEALTH_DIR = Path("projects_data")
HEALTH_FILE = HEALTH_DIR / "system_health.json"


class SystemHealth:
    """System health status container."""

    def __init__(
        self,
        last_intelligence_run: Optional[Dict[str, Any]] = None,
        api_status: Optional[Dict[str, Any]] = None,
        system_info: Optional[Dict[str, Any]] = None,
    ):
        self.last_intelligence_run = last_intelligence_run or {}
        self.api_status = api_status or {}
        self.system_info = system_info or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "last_intelligence_run": self.last_intelligence_run,
            "api_status": self.api_status,
            "system_info": self.system_info,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


def get_system_health() -> SystemHealth:
    """Get current system health status.

    Checks:
    - Last intelligence run from stored state
    - API key presence for each backend
    - Backend availability

    Returns:
        SystemHealth with current status.
    """
    last_run = _get_last_intelligence_run()
    api_status = _check_api_connectivity()
    system_info = _get_system_info()

    return SystemHealth(
        last_intelligence_run=last_run,
        api_status=api_status,
        system_info=system_info,
    )


def record_intelligence_run(
    project_id: str,
    project_name: str,
    success: bool,
    version_id: str = "",
    error: str = "",
    duration_ms: float = 0,
) -> None:
    """Record an intelligence run for health tracking.

    Args:
        project_id: Project that ran intelligence.
        project_name: Project name.
        success: Whether the run succeeded.
        version_id: Version ID created.
        error: Error message if failed.
        duration_ms: Duration in milliseconds.
    """
    HEALTH_DIR.mkdir(exist_ok=True)

    record = {
        "project_id": project_id,
        "project_name": project_name,
        "success": success,
        "version_id": version_id,
        "error": error,
        "duration_ms": duration_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Load existing health state
    health_state = _load_health_state()
    health_state["last_intelligence_run"] = record

    # Keep last 5 runs
    runs = health_state.get("recent_runs", [])
    runs.append(record)
    if len(runs) > 5:
        runs = runs[-5:]
    health_state["recent_runs"] = runs

    _save_health_state(health_state)


def _get_last_intelligence_run() -> Dict[str, Any]:
    """Get the most recent intelligence run record."""
    state = _load_health_state()
    last = state.get("last_intelligence_run", {})
    if not last:
        return {"status": "never_run", "message": "No intelligence runs recorded"}
    return last


def _check_api_connectivity() -> Dict[str, Any]:
    """Check API key presence and basic connectivity.

    Does NOT make actual API calls – just checks configuration.
    """
    env_checks = {
        "groq": {
            "env_var": "GROQ_API_KEY",
            "configured": bool(os.environ.get("GROQ_API_KEY", "")),
        },
        "openrouter": {
            "env_var": "OPENROUTER_API_KEY",
            "configured": bool(os.environ.get("OPENROUTER_API_KEY", "")),
        },
        "gemini": {
            "env_var": "GEMINI_API_KEY",
            "configured": bool(os.environ.get("GEMINI_API_KEY", "")),
        },
        "bedrock": {
            "env_var": "AWS_ACCESS_KEY_ID",
            "configured": bool(os.environ.get("AWS_ACCESS_KEY_ID", "")),
        },
        "ollama": {
            "env_var": "OLLAMA_HOST",
            "configured": True,  # Local, always "available"
            "note": "Local backend – requires Ollama running",
        },
    }

    # Also check from admin config file
    from admin.config import load_config
    config = load_config()
    for key_name, check in env_checks.items():
        config_val = config.api_keys.get(key_name, "")
        if config_val and not check["configured"]:
            check["configured"] = True
            check["source"] = "admin_config"
        elif check["configured"]:
            check["source"] = "environment"

    return env_checks


def _get_system_info() -> Dict[str, Any]:
    """Get basic system information."""
    projects_dir = Path("projects_data")
    project_count = 0
    if projects_dir.exists():
        projects_file = projects_dir / "projects.json"
        if projects_file.exists():
            with open(projects_file) as f:
                projects = json.load(f)
            project_count = len([p for p in projects if p.get("status", "active") == "active"])

    return {
        "active_projects": project_count,
        "data_directory": str(projects_dir),
        "data_directory_exists": projects_dir.exists(),
    }


def _load_health_state() -> Dict[str, Any]:
    """Load health state from disk."""
    HEALTH_DIR.mkdir(exist_ok=True)
    if not HEALTH_FILE.exists():
        return {}
    with open(HEALTH_FILE) as f:
        return json.load(f)


def _save_health_state(state: Dict[str, Any]) -> None:
    """Save health state to disk."""
    HEALTH_DIR.mkdir(exist_ok=True)
    with open(HEALTH_FILE, "w") as f:
        json.dump(state, f, indent=2)
