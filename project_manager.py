"""project_manager — backward-compatibility shim.

All logic lives in ``services/``.  This module re-exports every public
symbol so that existing call-sites (server.py, tests, CLI) continue to
work without modification.

``PROJECTS_DIR`` and ``PROJECTS_FILE`` are re-exported as mutable names
so that server.py can override them via environment variable at startup,
and the change is reflected across all services/ modules.
"""
from __future__ import annotations

# ── Re-export mutable path globals (server.py writes to these at startup) ─────
import services.project as _proj_svc

# Keep the canonical copies in services.project; expose them here for the
# server startup code that does:  project_manager.PROJECTS_DIR = Path(...)
from services.project import PROJECTS_DIR, PROJECTS_FILE  # noqa: F401

# ── project / lifecycle ────────────────────────────────────────────────────────
from services.project import (  # noqa: F401
    MAX_ARCHIVED,
    ADMIN_PIN,
    _ensure_dirs,
    _get_max_active_projects,
    _validate_pin,
    load_projects,
    save_projects,
    create_project,
    get_project,
    list_projects,
    list_all_projects,
    archive_project,
    delete_project,
    restore_project,
    toggle_file_active,
    get_file_toggles,
    get_auto_archive_suggestions,
    update_iteration_on_build as _update_iteration_on_build,
    update_iteration_on_review as _update_iteration_on_review,
)

# ── ingest ─────────────────────────────────────────────────────────────────────
from services.ingest import (  # noqa: F401
    ingest_files_to_project,
    get_project_context,
)

# ── intelligence ───────────────────────────────────────────────────────────────
from services.intelligence import (  # noqa: F401
    build_project_intelligence,
    get_project_intelligence,
    get_project_summary,
)

# ── review ─────────────────────────────────────────────────────────────────────
from services.review import (  # noqa: F401
    run_persona_review,
    get_project_reviews,
    get_review_quality,
    complete_review_gate,
    set_active_review_gated,
    update_weakness_status,
    update_decision_status,
    get_review_diff,
    get_version_readiness,
    get_prompt_history,
)

# ── hierarchy ──────────────────────────────────────────────────────────────────
from services.hierarchy import (  # noqa: F401
    get_hierarchy,
    get_hierarchy_phases,
    set_hierarchy_phase,
    get_hierarchy_versions,
    get_hierarchy_version_detail,
    get_hierarchy_reviews,
    get_hierarchy_review_detail,
    get_hierarchy_metrics,
    set_active_review,
    delete_hierarchy_review,
    get_active_review_for_version,
    get_project_versions,
    get_project_version,
    compare_project_versions,
    compare_project_reviews,
    get_project_evolution,
    get_project_review_history,
    get_run_history_for_project,
    get_file_snapshot,
)

# ── proposal ───────────────────────────────────────────────────────────────────
from services.proposal import (  # noqa: F401
    create_proposal,
    add_proposal_version,
    get_proposal_info,
    list_proposal_versions_for_project,
    compare_proposals,
    update_proposal_status,
    generate_proposal_doc,
    get_proposal_doc,
)

# ── admin / phases ─────────────────────────────────────────────────────────────
from services.admin import (  # noqa: F401
    get_admin_config,
    update_admin_config,
    get_system_health_status,
    get_lifecycle_logs,
    validate_files_for_ingestion,
    transition_project_phase,
    get_phase_history_for_project,
    get_phase_info,
)

# ── deep-dive ──────────────────────────────────────────────────────────────────
from services.deepdive import (  # noqa: F401
    run_deep_dive_analysis,
    apply_deep_dive_feedback,
)

# ── diagram ────────────────────────────────────────────────────────────────────
from services.diagram import (  # noqa: F401
    generate_diagram,
    get_diagram,
    list_diagrams,
    VALID_DIAGRAM_TYPES as DIAGRAM_TYPES,
)

# ── presales ───────────────────────────────────────────────────────────────────
from services.presales import (  # noqa: F401
    get_presales_stop_condition,
    finalise_presales,
)
