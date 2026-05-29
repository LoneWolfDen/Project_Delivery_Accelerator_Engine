"""Admin Configuration – API keys, project limits, system settings.

Stores configuration in a JSON file with support for:
- API keys (encrypted placeholder, editable via API)
- Project limits (max active projects)
- Default persona and phase settings
- Admin PIN for destructive operations
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_DIR = Path("projects_data")
CONFIG_FILE = CONFIG_DIR / "admin_config.json"

# Mask for displaying stored API keys
KEY_MASK = "****"


@dataclass
class AdminConfig:
    """System-wide configuration."""

    # API Keys (stored as env var names or masked values)
    api_keys: Dict[str, str] = field(default_factory=lambda: {
        "groq": "",
        "openrouter": "",
        "gemini": "",
        "bedrock_access_key": "",
        "bedrock_secret_key": "",
    })

    # Project limits
    max_active_projects: int = 5

    # System defaults
    default_persona: str = "solution_architect"
    default_phase: str = "discovery"
    default_ai_backend: str = "files_only"

    # Admin PIN
    admin_pin: str = field(default_factory=lambda: os.environ.get("ADMIN_PIN", ""))

    # Auto-archive settings
    auto_archive_enabled: bool = False
    auto_archive_inactivity_days: int = 30

    # P8 – Dual-write storage mode
    # Both default True: app writes to SQLite AND keeps JSON files in sync.
    # Uncheck sqlite_write_enabled to disable SQLite entirely (file-only mode).
    # Uncheck file_write_enabled to stop writing JSON files (SQLite-only mode).
    sqlite_write_enabled: bool = True
    file_write_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config with masked API keys for display."""
        d = asdict(self)
        # Mask API keys for display
        masked_keys = {}
        for key, val in d["api_keys"].items():
            if val:
                masked_keys[key] = KEY_MASK
            else:
                masked_keys[key] = ""
        d["api_keys_masked"] = masked_keys
        return d

    def to_safe_dict(self) -> Dict[str, Any]:
        """Serialize config WITHOUT raw API keys (for API responses)."""
        d = asdict(self)
        masked_keys = {}
        for key, val in d["api_keys"].items():
            if val:
                masked_keys[key] = f"{val[:4]}{'*' * max(0, len(val) - 4)}"
            else:
                masked_keys[key] = ""
        d["api_keys"] = masked_keys
        return d


def load_config() -> AdminConfig:
    """Load admin configuration from disk, with env var fallback.

    Returns:
        AdminConfig instance with current settings.
    """
    CONFIG_DIR.mkdir(exist_ok=True)

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            data = json.load(f)
        config = AdminConfig(
            api_keys=data.get("api_keys", AdminConfig().api_keys),
            max_active_projects=data.get("max_active_projects", 5),
            default_persona=data.get("default_persona", "solution_architect"),
            default_phase=data.get("default_phase", "discovery"),
            default_ai_backend=data.get("default_ai_backend", "files_only"),
            admin_pin=data.get("admin_pin") or os.environ.get("ADMIN_PIN", ""),
            auto_archive_enabled=data.get("auto_archive_enabled", False),
            auto_archive_inactivity_days=data.get("auto_archive_inactivity_days", 30),
            sqlite_write_enabled=data.get("sqlite_write_enabled", True),
            file_write_enabled=data.get("file_write_enabled", True),
        )
    else:
        config = AdminConfig()

    # Override API keys from environment variables if present
    env_mappings = {
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "bedrock_access_key": "AWS_ACCESS_KEY_ID",
        "bedrock_secret_key": "AWS_SECRET_ACCESS_KEY",
    }
    for key_name, env_var in env_mappings.items():
        env_val = os.environ.get(env_var, "")
        if env_val:
            config.api_keys[key_name] = env_val

    return config


def save_config(config: AdminConfig) -> None:
    """Persist admin configuration to disk.

    Args:
        config: AdminConfig instance to save.
    """
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(asdict(config), f, indent=2)


def update_config(updates: Dict[str, Any]) -> AdminConfig:
    """Update specific configuration fields.

    Args:
        updates: Dict of fields to update (partial update supported).

    Returns:
        Updated AdminConfig instance.
    """
    config = load_config()

    if "max_active_projects" in updates:
        config.max_active_projects = int(updates["max_active_projects"])
    if "default_persona" in updates:
        config.default_persona = updates["default_persona"]
    if "default_phase" in updates:
        config.default_phase = updates["default_phase"]
    if "default_ai_backend" in updates:
        config.default_ai_backend = updates["default_ai_backend"]
    if "admin_pin" in updates:
        config.admin_pin = updates["admin_pin"]
    if "auto_archive_enabled" in updates:
        config.auto_archive_enabled = bool(updates["auto_archive_enabled"])
    if "auto_archive_inactivity_days" in updates:
        config.auto_archive_inactivity_days = int(updates["auto_archive_inactivity_days"])
    if "sqlite_write_enabled" in updates:
        config.sqlite_write_enabled = bool(updates["sqlite_write_enabled"])
    if "file_write_enabled" in updates:
        config.file_write_enabled = bool(updates["file_write_enabled"])

    # API keys update (only non-empty values)
    if "api_keys" in updates:
        for key, val in updates["api_keys"].items():
            if val and val != KEY_MASK:
                config.api_keys[key] = val

    save_config(config)
    return config
