"""Admin Module – Configuration, Governance, and System Health.

Central administration for:
- API key management (secure storage, editable)
- Project limits and system settings
- Lifecycle logs (archived/deleted projects)
- System health monitoring
"""

from admin.config import AdminConfig, load_config, save_config
from admin.lifecycle import LifecycleLog, get_lifecycle_log, record_archive, record_delete
from admin.health import SystemHealth, get_system_health

__all__ = [
    "AdminConfig",
    "load_config",
    "save_config",
    "LifecycleLog",
    "get_lifecycle_log",
    "record_archive",
    "record_delete",
    "SystemHealth",
    "get_system_health",
]
