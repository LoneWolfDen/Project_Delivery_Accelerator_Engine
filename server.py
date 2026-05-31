"""Project Delivery Accelerator Engine – Main Server.

Routing only.  All business logic lives in handlers/ and services/.
Each route resolves to a free function in handlers/<domain>.py.

AcceleratorHandler is responsible for:
- Parsing path + query string
- Reading request body
- Calling the appropriate handler function via respond=self._json_response
- Serving static files
- Special-casing the diagram XML download (raw bytes, not JSON)
"""

import json
import logging
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

import project_manager
from ai_backends import list_backends
from core.logging_config import configure_logging
from db.decision_log import get_decision_log
from version import __version__

import handlers.admin as h_admin
import handlers.artifact as h_artifact
import handlers.deepdive as h_deepdive
import handlers.diagram as h_diagram
import handlers.hierarchy as h_hierarchy
import handlers.ingest as h_ingest
import handlers.intelligence as h_intel
import handlers.presales as h_presales
import handlers.project as h_project
import handlers.proposal as h_proposal
import handlers.review as h_review
import services.hierarchy as svc_hierarchy
import services.intelligence as svc_intel
import services.presales as svc_presales
import services.project as svc_project
import services.proposal as svc_proposal
import services.review as svc_review

configure_logging()
logger = logging.getLogger(__name__)

HOST = os.environ.get("HOST", "localhost")
PORT = int(os.environ.get("PORT", "8080"))
APP_NAME = os.environ.get("APP_NAME", "Project Delivery Accelerator Engine")
APP_VERSION = __version__

# Allow Docker / env-var override of the data directory.
# Writing to both project_manager (shim) and services.project so the path
# propagates everywhere without a full import cycle.
_data_dir = os.environ.get("PROJECTS_DATA_DIR", "")
if _data_dir:
    _p = Path(_data_dir)
    project_manager.PROJECTS_DIR = _p
    project_manager.PROJECTS_FILE = _p / "projects.json"
    import services.project as _sp
    _sp.PROJECTS_DIR = _p
    _sp.PROJECTS_FILE = _p / "projects.json"


class AcceleratorHandler(SimpleHTTPRequestHandler):
    """HTTP handler — routing only, zero business logic."""

    # ── Path parsing ──────────────────────────────────────────────────────────

    def _parse_path(self):
        """Return (clean_path, query_dict) with query string stripped."""
        if "?" in self.path:
            path_part, query_str = self.path.split("?", 1)
            params = {}
            for param in query_str.split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    params[k] = v
            return path_part, params
        return self.path, {}

    # ── HTTP verbs ────────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        # Static files
        if self.path in ("/", ""):
            self._serve_static("index.html")
            return
        if self.path.startswith("/feedback"):
            self._serve_static("feedback.html")
            return
        if self.path.startswith("/static/") or self.path.endswith((".html", ".css", ".js")):
            filename = self.path.lstrip("/")
            if not filename.startswith("static/"):
                filename = "static/" + filename
            self._serve_static(filename.replace("static/", ""))
            return

        clean_path, query = self._parse_path()
        R = self._json_response  # shorthand

        if clean_path == "/api/health":
            R({"status": "ok", "version": APP_VERSION, "app": APP_NAME})

        elif clean_path == "/api/backends":
            R({"backends": list_backends()})

        elif clean_path == "/api/projects":
            R({"projects": svc_project.list_projects()})

        elif clean_path == "/api/projects/all":
            R({"projects": svc_project.list_all_projects()})

        elif clean_path == "/api/personas":
            h_intel.handle_list_personas(R)

        # ── Admin ─────────────────────────────────────────────────────────────
        elif clean_path == "/api/admin/config":
            from services.admin import get_admin_config
            R({"config": get_admin_config()})

        elif clean_path == "/api/admin/health":
            from services.admin import get_system_health_status
            R({"health": get_system_health_status()})

        elif clean_path == "/api/admin/lifecycle":
            from services.admin import get_lifecycle_logs
            R({"lifecycle": get_lifecycle_logs()})

        elif clean_path == "/api/admin/auto-archive-suggestions":
            R({"suggestions": svc_project.get_auto_archive_suggestions()})

        # ── Hierarchy (MUST precede generic /versions, /reviews, /summary) ────
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/hierarchy"):
            pid = clean_path.split("/")[3]
            R(svc_hierarchy.get_hierarchy(pid))

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/hierarchy/phases"):
            pid = clean_path.split("/")[3]
            R({"project_id": pid, "phases": svc_hierarchy.get_hierarchy_phases(pid)})

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/hierarchy/metrics"):
            pid = clean_path.split("/")[3]
            R(svc_hierarchy.get_hierarchy_metrics(
                pid, query.get("version_id"), query.get("review_id")
            ))

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/hierarchy/versions"):
            pid = clean_path.split("/")[3]
            R({"project_id": pid,
               "versions": svc_hierarchy.get_hierarchy_versions(pid, query.get("phase_id"))})

        elif clean_path.startswith("/api/projects/") and "/hierarchy/versions/" in clean_path and clean_path.endswith("/readiness"):
            parts = clean_path.split("/")
            pid, vid = parts[3], parts[6]
            result = svc_review.get_version_readiness(pid, vid)
            R(result, status=404 if result.get("error") else 200)

        elif clean_path.startswith("/api/projects/") and "/hierarchy/versions/" in clean_path:
            parts = clean_path.split("/")
            pid, vid = parts[3], parts[6]
            detail = svc_hierarchy.get_hierarchy_version_detail(pid, vid)
            R(detail) if detail else R({"error": "Version not found"}, status=404)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/hierarchy/reviews"):
            pid = clean_path.split("/")[3]
            reviews = svc_hierarchy.get_hierarchy_reviews(
                pid, query.get("version_id"), query.get("phase_id")
            )
            R({"project_id": pid, "reviews": reviews})

        elif clean_path.startswith("/api/projects/") and "/hierarchy/reviews/" in clean_path and clean_path.endswith("/quality"):
            parts = clean_path.split("/")
            pid, rid = parts[3], parts[6]
            R(svc_review.get_review_quality(pid, rid))

        elif clean_path.startswith("/api/projects/") and "/hierarchy/reviews/" in clean_path and clean_path.endswith("/diff"):
            parts = clean_path.split("/")
            pid, rid = parts[3], parts[6]
            result = svc_review.get_review_diff(pid, rid)
            R(result, status=404 if result.get("error") else 200)

        elif clean_path.startswith("/api/projects/") and "/hierarchy/reviews/" in clean_path:
            parts = clean_path.split("/")
            pid, rid = parts[3], parts[6]
            detail = svc_hierarchy.get_hierarchy_review_detail(pid, rid)
            R(detail) if detail else R({"error": "Review not found"}, status=404)

        # ── Pre-sales GET (MUST precede /summary) ────────────────────────────
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/summary"):
            h_presales.handle_get_presales_summary(clean_path.split("/")[3], R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/stop-condition"):
            R(svc_presales.get_presales_stop_condition(clean_path.split("/")[3]))

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/feedback"):
            h_presales.handle_list_presales_feedback(clean_path.split("/")[3], R)

        elif clean_path.startswith("/api/projects/") and "/presales/feedback/" in clean_path:
            parts = clean_path.split("/")
            h_presales.handle_get_presales_feedback_item(parts[3], parts[6], R)

        elif clean_path == "/api/feedback/form" and query.get("token"):
            h_presales.handle_feedback_form(query["token"], R)

        # ── Project-specific data ─────────────────────────────────────────────
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/context"):
            pid = clean_path.split("/")[3]
            from services.ingest import get_project_context
            R({"project_id": pid,
               "documents": get_project_context(pid),
               "file_toggles": svc_project.get_file_toggles(pid)})

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/file-toggles"):
            pid = clean_path.split("/")[3]
            R({"project_id": pid, "file_toggles": svc_project.get_file_toggles(pid)})

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/intelligence"):
            pid = clean_path.split("/")[3]
            R({"project_id": pid, "intelligence": svc_intel.get_project_intelligence(pid)})

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/summary"):
            pid = clean_path.split("/")[3]
            R({"project_id": pid, "summary": svc_intel.get_project_summary(pid)})

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/versions"):
            pid = clean_path.split("/")[3]
            R({"project_id": pid, "versions": svc_hierarchy.get_project_versions(pid)})

        elif clean_path.startswith("/api/projects/") and "/versions/" in clean_path:
            parts = clean_path.split("/")
            pid, vid = parts[3], parts[5]
            version = svc_hierarchy.get_project_version(pid, vid)
            R({"project_id": pid, "version": version}) if version else R(
                {"error": f"Version not found: {vid}"}, status=404
            )

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/run-history"):
            pid = clean_path.split("/")[3]
            R({"project_id": pid, "run_history": svc_hierarchy.get_run_history_for_project(pid)})

        elif clean_path.startswith("/api/projects/") and "/file-snapshot/" in clean_path:
            parts = clean_path.split("/")
            pid, vid = parts[3], parts[5]
            snap = svc_hierarchy.get_file_snapshot(pid, vid)
            R(snap) if snap else R({"error": "Snapshot not found"}, status=404)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/reviews"):
            pid = clean_path.split("/")[3]
            reviews = svc_hierarchy.get_project_review_history(pid, query.get("persona"))
            R({"project_id": pid, "reviews": reviews})

        elif clean_path.startswith("/api/projects/") and "/evolution/" in clean_path:
            parts = clean_path.split("/")
            pid, cat = parts[3], parts[5]
            R({"project_id": pid, "category": cat,
               "timeline": svc_hierarchy.get_project_evolution(pid, cat)})

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/proposal/document"):
            pid = clean_path.split("/")[3]
            doc = svc_proposal.get_proposal_doc(pid, query.get("proposal_ver_id", ""))
            R({"document": doc}) if doc else R({"error": "No document generated yet"}, status=404)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/proposal"):
            pid = clean_path.split("/")[3]
            proposal = svc_proposal.get_proposal_info(pid)
            R(proposal) if proposal else R({"error": "No proposal exists"}, status=404)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/phase-history"):
            pid = clean_path.split("/")[3]
            from services.admin import get_phase_history_for_project
            R({"project_id": pid, "history": get_phase_history_for_project(pid)})

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/decision-log"):
            pid = clean_path.split("/")[3]
            logs = get_decision_log(
                pid,
                entity_type=query.get("entity_type"),
                entity_id=query.get("entity_id"),
            )
            R({"project_id": pid, "logs": logs, "count": len(logs)})

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/prompt-history"):
            pid = clean_path.split("/")[3]
            R(svc_review.get_prompt_history(
                pid,
                persona_name=query.get("persona_name") or None,
                scenario_type=query.get("scenario_type") or None,
            ))

        # ── Diagram API ───────────────────────────────────────────────────────
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/diagrams"):
            from services.diagram import list_diagrams
            R(list_diagrams(clean_path.split("/")[3]))

        elif clean_path.startswith("/api/projects/") and "/diagrams/" in clean_path:
            parts = clean_path.split("/")
            pid, dtype = parts[3], parts[5]
            from services.diagram import get_diagram
            result = get_diagram(pid, dtype)
            if result.get("error"):
                R(result, status=404)
            else:
                xml = result.get("xml", "")
                self.send_response(200)
                self.send_header("Content-Type", "application/xml")
                self.send_header("Content-Disposition", f'attachment; filename="{dtype}.drawio"')
                self.send_header("Content-Length", str(len(xml.encode())))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(xml.encode())
                return

        # ── Artifact API v1 ───────────────────────────────────────────────────
        elif "/artifacts" in clean_path and clean_path.startswith("/api/v1/projects/"):
            h_artifact.handle_list_artifacts(clean_path.split("/")[4], R)

        elif clean_path.startswith("/api/v1/jobs/"):
            parts = clean_path.split("/")
            h_artifact.handle_get_job(parts[4] if len(parts) > 4 else parts[3], R)

        else:
            R({"errorCode": "NOT_FOUND", "message": "Not found"}, status=404)

    def do_POST(self) -> None:
        clean_path, query = self._parse_path()
        body = self._read_body()
        R = self._json_response

        if clean_path == "/api/projects":
            h_project.handle_create_project(body, R)

        elif clean_path == "/api/ingest":
            h_ingest.handle_ingest(body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/build-context"):
            h_intel.handle_build_context(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and "/diagrams/" in clean_path and clean_path.endswith("/generate"):
            parts = clean_path.split("/")
            h_diagram.handle_generate_diagram(parts[3], parts[5], body, R)

        elif clean_path == "/api/review":
            h_review.handle_review(body, R)

        elif clean_path == "/api/personas":
            h_intel.handle_list_personas(R)

        elif clean_path == "/api/admin/config":
            h_admin.handle_update_config(body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/archive"):
            h_project.handle_archive_project(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/restore"):
            h_project.handle_restore_project(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/delete") and "/hierarchy/" not in clean_path:
            h_project.handle_delete_project(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/deep-dive"):
            h_deepdive.handle_deep_dive(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/deep-dive/feedback"):
            h_deepdive.handle_deep_dive_feedback(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/compare-versions"):
            h_hierarchy.handle_compare_versions(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/compare-reviews"):
            h_hierarchy.handle_compare_reviews(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/proposal/generate"):
            h_proposal.handle_generate_proposal_doc(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/proposal/version"):
            h_proposal.handle_add_proposal_version(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and "/proposal/version/" in clean_path and clean_path.endswith("/status"):
            parts = clean_path.split("/")
            h_proposal.handle_update_proposal_version_status(parts[3], parts[6], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/proposal"):
            h_proposal.handle_create_proposal(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/phase"):
            h_admin.handle_phase_transition(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/hierarchy/phase"):
            h_admin.handle_hierarchy_phase_transition(clean_path.split("/")[3], body, R)

        elif self.path.startswith("/api/projects/") and "/hierarchy/reviews/" in self.path and self.path.endswith("/delete"):
            parts = self.path.split("/")
            h_review.handle_delete_review(parts[3], parts[6], R)

        elif self.path.startswith("/api/projects/") and "/hierarchy/versions/" in self.path and self.path.endswith("/set-active-review"):
            parts = self.path.split("/")
            h_review.handle_set_active_review(parts[3], parts[6], body, R)

        elif self.path.startswith("/api/projects/") and "/hierarchy/reviews/" in self.path and self.path.endswith("/complete"):
            parts = self.path.split("/")
            h_review.handle_complete_review(parts[3], parts[6], body, R)

        elif self.path.startswith("/api/projects/") and "/hierarchy/reviews/" in self.path and "/weakness/" in self.path and self.path.endswith("/status"):
            parts = self.path.split("/")
            h_review.handle_weakness_status(parts[3], parts[6], parts[8], body, R)

        elif self.path.startswith("/api/projects/") and "/hierarchy/reviews/" in self.path and "/decision/" in self.path and self.path.endswith("/status"):
            parts = self.path.split("/")
            h_review.handle_decision_status(parts[3], parts[6], parts[8], body, R)

        elif self.path.startswith("/api/projects/") and "/hierarchy/versions/" in self.path and self.path.endswith("/set-active-review-gated"):
            parts = self.path.split("/")
            h_review.handle_set_active_review_gated(parts[3], parts[6], body, R)

        elif self.path.startswith("/api/projects/") and self.path.endswith("/toggle-file"):
            h_project.handle_toggle_file(self.path.split("/")[3], body, R)

        elif clean_path == "/api/validate-files":
            h_ingest.handle_validate_files(body, R)

        elif "/artifacts/upload" in clean_path and clean_path.startswith("/api/v1/projects/"):
            pid = clean_path.split("/")[4]
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" in content_type:
                content_length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(content_length)
                h_artifact.handle_artifact_upload(pid, {}, R, raw_multipart=raw, content_type=content_type)
            else:
                h_artifact.handle_artifact_upload(pid, body, R)

        elif "/artifacts/text" in clean_path and clean_path.startswith("/api/v1/projects/"):
            h_artifact.handle_artifact_text(clean_path.split("/")[4], body, R)

        elif "/artifacts/" in clean_path and "/toggle" in clean_path and clean_path.startswith("/api/v1/projects/"):
            parts = clean_path.split("/")
            h_artifact.handle_artifact_toggle(parts[4], parts[6], body, R)

        elif "/artifacts/" in clean_path and "/delete" in clean_path and clean_path.startswith("/api/v1/projects/"):
            parts = clean_path.split("/")
            h_artifact.handle_artifact_delete(parts[4], parts[6], R)

        elif "/artifacts/process" in clean_path and clean_path.startswith("/api/v1/projects/") and not clean_path.rstrip("/").split("/")[-1].startswith("a_"):
            h_artifact.handle_process_all_artifacts(clean_path.split("/")[4], body, R)

        elif "/artifacts/" in clean_path and "/process" in clean_path and clean_path.startswith("/api/v1/projects/"):
            parts = clean_path.split("/")
            h_artifact.handle_process_artifact(parts[4], parts[6], R)

        elif "/artifacts/" in clean_path and clean_path.startswith("/api/v1/projects/") and "/toggle" not in clean_path and "/delete" not in clean_path and "/process" not in clean_path:
            parts = clean_path.split("/")
            if len(parts) >= 7:
                h_artifact.handle_patch_artifact(parts[4], parts[6], body, R)
            else:
                R({"errorCode": "INVALID_REQUEST", "message": "Invalid artifact path"}, status=400)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/feedback/classify"):
            h_presales.handle_classify_feedback(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/feedback"):
            h_presales.handle_create_presales_feedback(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and "/presales/feedback/" in clean_path and clean_path.endswith("/action"):
            parts = clean_path.split("/")
            h_presales.handle_action_presales_feedback(parts[3], parts[6], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/share"):
            h_presales.handle_create_feedback_token(clean_path.split("/")[3], body, R)

        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/finalise"):
            decided_by = body.get("decided_by", "")
            if not decided_by:
                R({"error": "decided_by is required to finalise"}, status=400)
            else:
                result = svc_presales.finalise_presales(
                    clean_path.split("/")[3],
                    decided_by=decided_by,
                    reason=body.get("reason", ""),
                    force=bool(body.get("force", False)),
                )
                R(result, status=422 if result.get("error") else 200)

        elif clean_path == "/api/feedback/submit":
            h_presales.handle_external_feedback_submit(body, R)

        else:
            R({"errorCode": "NOT_FOUND", "message": "Not found"}, status=404)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_PATCH(self) -> None:
        clean_path, _ = self._parse_path()
        body = self._read_body()
        if "/artifacts/" in clean_path and clean_path.startswith("/api/v1/projects/"):
            parts = clean_path.split("/")
            if len(parts) >= 7:
                h_artifact.handle_patch_artifact(parts[4], parts[6], body, self._json_response)
            else:
                self._json_response({"errorCode": "INVALID_REQUEST", "message": "Invalid path"}, status=400)
        else:
            self._json_response({"errorCode": "NOT_FOUND", "message": "Not found"}, status=404)

    # ── Infrastructure ────────────────────────────────────────────────────────

    def _read_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def _json_response(self, data: Any, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _serve_static(self, filename: str) -> None:
        static_dir = Path(__file__).parent / "static"
        file_path = static_dir / filename
        if not file_path.exists() or not file_path.is_file():
            self._json_response({"error": "Not found"}, status=404)
            return
        ext = file_path.suffix.lower()
        content_types = {
            ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
            ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml",
        }
        self.send_response(200)
        self.send_header("Content-Type", content_types.get(ext, "application/octet-stream"))
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def log_message(self, fmt: str, *args: Any) -> None:  # silence default stderr log
        logger.debug("%s - %s", self.address_string(), fmt % args)


def main() -> None:
    import services.project as sp
    sp.PROJECTS_DIR.mkdir(exist_ok=True)
    server = HTTPServer((HOST, PORT), AcceleratorHandler)
    logger.info("%s v%s — listening on http://%s:%s", APP_NAME, APP_VERSION, HOST, PORT)
    logger.info("Data directory: %s", os.environ.get("PROJECTS_DATA_DIR", "projects_data/"))
    server.serve_forever()


if __name__ == "__main__":
    main()
