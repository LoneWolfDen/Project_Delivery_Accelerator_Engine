"""Project Delivery Accelerator Engine – Main Server.

Lightweight API server providing:
- Project CRUD
- File upload and ingestion
- Context building
- Persona-driven reviews
- AI backend switching
- Static file serving (Web UI)
"""

import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

import project_manager

# ── Runtime configuration (all overridable via environment variables) ─────────
HOST = os.environ.get("HOST", "localhost")
PORT = int(os.environ.get("PORT", "8080"))
APP_NAME = os.environ.get("APP_NAME", "Project Delivery Accelerator Engine")
APP_VERSION = "3.3.0"

# Redirect projects_data to PROJECTS_DATA_DIR env var when set (e.g. Docker volume)
_data_dir = os.environ.get("PROJECTS_DATA_DIR", "")
if _data_dir:
    from pathlib import Path as _Path
    project_manager.PROJECTS_DIR = _Path(_data_dir)
    project_manager.PROJECTS_FILE = _Path(_data_dir) / "projects.json"


class AcceleratorHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the delivery accelerator API."""

    def _parse_path(self):
        """Split self.path into clean path and query params dict.

        Returns (path_str, query_dict) – e.g.:
            '/api/projects/p1/hierarchy/metrics?version_id=v1&review_id=r1'
            → ('/api/projects/p1/hierarchy/metrics', {'version_id': 'v1', 'review_id': 'r1'})
        """
        if "?" in self.path:
            path_part, query_str = self.path.split("?", 1)
            params = {}
            for param in query_str.split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    params[k] = v
            return path_part, params
        return self.path, {}

    def do_GET(self) -> None:
        """Handle GET requests."""
        # Serve Web UI
        if self.path == "/" or self.path == "":
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

        # Normalize: strip query params for route matching
        clean_path, query = self._parse_path()

        # API endpoints
        if clean_path == "/api/health":
            self._json_response({"status": "ok", "version": APP_VERSION, "app": APP_NAME})
        elif clean_path == "/api/backends":
            from ai_backends import list_backends
            self._json_response({"backends": list_backends()})
        elif clean_path == "/api/projects":
            projects = project_manager.list_projects()
            self._json_response({"projects": projects})
        elif clean_path == "/api/projects/all":
            projects = project_manager.list_all_projects()
            self._json_response({"projects": projects})
        # ── Admin endpoints ──
        elif clean_path == "/api/admin/config":
            config = project_manager.get_admin_config()
            self._json_response({"config": config})
        elif clean_path == "/api/admin/health":
            health = project_manager.get_system_health_status()
            self._json_response({"health": health})
        elif clean_path == "/api/admin/lifecycle":
            logs = project_manager.get_lifecycle_logs()
            self._json_response({"lifecycle": logs})
        elif clean_path == "/api/admin/auto-archive-suggestions":
            suggestions = project_manager.get_auto_archive_suggestions()
            self._json_response({"suggestions": suggestions})
        # ── Hierarchy API (Phase→Version→Review) — MUST come before generic /versions, /reviews, /summary ──
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/hierarchy"):
            project_id = clean_path.split("/")[3]
            hierarchy = project_manager.get_hierarchy(project_id)
            self._json_response(hierarchy)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/hierarchy/phases"):
            project_id = clean_path.split("/")[3]
            phases = project_manager.get_hierarchy_phases(project_id)
            self._json_response({"project_id": project_id, "phases": phases})
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/hierarchy/metrics"):
            project_id = clean_path.split("/")[3]
            version_filter = query.get("version_id")
            review_filter = query.get("review_id")
            metrics = project_manager.get_hierarchy_metrics(project_id, version_filter, review_filter)
            self._json_response(metrics)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/hierarchy/versions"):
            # GET /api/projects/{id}/hierarchy/versions — list; MUST precede /versions/ item check
            project_id = clean_path.split("/")[3]
            phase_filter = query.get("phase_id")
            versions = project_manager.get_hierarchy_versions(project_id, phase_filter)
            self._json_response({"project_id": project_id, "versions": versions})
        elif clean_path.startswith("/api/projects/") and "/hierarchy/versions/" in clean_path:
            # GET /api/projects/{id}/hierarchy/versions/{version_id}
            parts = clean_path.split("/")
            project_id = parts[3]
            version_id = parts[6]
            detail = project_manager.get_hierarchy_version_detail(project_id, version_id)
            if detail:
                self._json_response(detail)
            else:
                self._json_response({"error": "Version not found"}, status=404)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/hierarchy/reviews"):
            # GET /api/projects/{id}/hierarchy/reviews — list; MUST precede /reviews/ item check
            project_id = clean_path.split("/")[3]
            version_filter = query.get("version_id")
            phase_filter = query.get("phase_id")
            reviews = project_manager.get_hierarchy_reviews(project_id, version_filter, phase_filter)
            self._json_response({"project_id": project_id, "reviews": reviews})
        elif clean_path.startswith("/api/projects/") and "/hierarchy/reviews/" in clean_path and clean_path.endswith("/quality"):
            # GET /api/projects/{id}/hierarchy/reviews/{review_id}/quality — MUST precede generic /reviews/ item
            parts = clean_path.split("/")
            project_id = parts[3]
            review_id = parts[6]
            result = project_manager.get_review_quality(project_id, review_id)
            self._json_response(result)
        elif clean_path.startswith("/api/projects/") and "/hierarchy/reviews/" in clean_path:
            # GET /api/projects/{id}/hierarchy/reviews/{review_id}
            parts = clean_path.split("/")
            project_id = parts[3]
            review_id = parts[6]
            detail = project_manager.get_hierarchy_review_detail(project_id, review_id)
            if detail:
                self._json_response(detail)
            else:
                self._json_response({"error": "Review not found"}, status=404)
        # ── P9: Pre-sales GET routes — MUST come before generic /summary ──
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/summary"):
            project_id = clean_path.split("/")[3]
            self._handle_get_presales_summary(project_id)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/stop-condition"):
            project_id = clean_path.split("/")[3]
            result = project_manager.get_presales_stop_condition(project_id)
            self._json_response(result)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/feedback"):
            project_id = clean_path.split("/")[3]
            self._handle_list_presales_feedback(project_id)
        elif clean_path.startswith("/api/projects/") and "/presales/feedback/" in clean_path:
            parts = clean_path.split("/")
            project_id = parts[3]
            feedback_id = parts[6]
            self._handle_get_presales_feedback_item(project_id, feedback_id)
        elif clean_path == "/api/feedback/form" and query.get("token"):
            self._handle_feedback_form(query["token"])
        # ── Project-specific endpoints ──
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/context"):
            project_id = clean_path.split("/")[3]
            context = project_manager.get_project_context(project_id)
            toggles = project_manager.get_file_toggles(project_id)
            self._json_response({"project_id": project_id, "documents": context, "file_toggles": toggles})
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/file-toggles"):
            project_id = clean_path.split("/")[3]
            toggles = project_manager.get_file_toggles(project_id)
            self._json_response({"project_id": project_id, "file_toggles": toggles})
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/intelligence"):
            project_id = clean_path.split("/")[3]
            intelligence = project_manager.get_project_intelligence(project_id)
            self._json_response({"project_id": project_id, "intelligence": intelligence})
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/summary"):
            project_id = clean_path.split("/")[3]
            summary = project_manager.get_project_summary(project_id)
            self._json_response({"project_id": project_id, "summary": summary})
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/versions"):
            # GET /api/projects/{id}/versions (legacy non-hierarchy versions list)
            project_id = clean_path.split("/")[3]
            versions = project_manager.get_project_versions(project_id)
            self._json_response({"project_id": project_id, "versions": versions})
        elif clean_path.startswith("/api/projects/") and "/versions/" in clean_path:
            # GET /api/projects/{id}/versions/{version_id}
            parts = clean_path.split("/")
            project_id = parts[3]
            version_id = parts[5]
            version = project_manager.get_project_version(project_id, version_id)
            if version:
                self._json_response({"project_id": project_id, "version": version})
            else:
                self._json_response({"error": f"Version not found: {version_id}"}, status=404)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/run-history"):
            project_id = clean_path.split("/")[3]
            history = project_manager.get_run_history_for_project(project_id)
            self._json_response({"project_id": project_id, "run_history": history})
        elif clean_path.startswith("/api/projects/") and "/file-snapshot/" in clean_path:
            parts = clean_path.split("/")
            project_id = parts[3]
            version_id = parts[5]
            snapshot = project_manager.get_file_snapshot(project_id, version_id)
            if snapshot:
                self._json_response(snapshot)
            else:
                self._json_response({"error": "Snapshot not found"}, status=404)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/reviews"):
            # GET /api/projects/{id}/reviews (legacy review history)
            project_id = clean_path.split("/")[3]
            persona_filter = query.get("persona")
            reviews = project_manager.get_project_review_history(project_id, persona_filter)
            self._json_response({"project_id": project_id, "reviews": reviews})
        elif clean_path.startswith("/api/projects/") and "/evolution/" in clean_path:
            parts = clean_path.split("/")
            project_id = parts[3]
            category = parts[5]
            timeline = project_manager.get_project_evolution(project_id, category)
            self._json_response({"project_id": project_id, "category": category, "timeline": timeline})
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/proposal/document"):
            # MUST precede /proposal to avoid endswith("/proposal") shadowing
            project_id = clean_path.split("/")[3]
            proposal_ver_id = query.get("proposal_ver_id", "")
            doc = project_manager.get_proposal_doc(project_id, proposal_ver_id)
            if doc:
                self._json_response({"document": doc})
            else:
                self._json_response({"error": "No document generated yet"}, status=404)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/proposal"):
            project_id = clean_path.split("/")[3]
            proposal = project_manager.get_proposal_info(project_id)
            if proposal:
                self._json_response(proposal)
            else:
                self._json_response({"error": "No proposal exists"}, status=404)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/phase-history"):
            project_id = clean_path.split("/")[3]
            history = project_manager.get_phase_history_for_project(project_id)
            self._json_response({"project_id": project_id, "history": history})
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/decision-log"):
            project_id = clean_path.split("/")[3]
            entity_type = query.get("entity_type")
            entity_id = query.get("entity_id")
            from db.decision_log import get_decision_log
            logs = get_decision_log(project_id, entity_type=entity_type, entity_id=entity_id)
            self._json_response({"project_id": project_id, "logs": logs, "count": len(logs)})
        elif clean_path.startswith("/api/projects/") and "/hierarchy/reviews/" in clean_path and clean_path.endswith("/diff"):
            # GET /api/projects/{id}/hierarchy/reviews/{review_id}/diff
            parts = clean_path.split("/")
            project_id = parts[3]
            review_id = parts[6]
            result = project_manager.get_review_diff(project_id, review_id)
            if result.get("error"):
                self._json_response(result, status=404)
            else:
                self._json_response(result)
        # S7-01: Decision Readiness indicator
        elif clean_path.startswith("/api/projects/") and "/hierarchy/versions/" in clean_path and clean_path.endswith("/readiness"):
            # GET /api/projects/{id}/hierarchy/versions/{version_id}/readiness
            parts = clean_path.split("/")
            project_id = parts[3]
            version_id = parts[6]
            result = project_manager.get_version_readiness(project_id, version_id)
            if result.get("error"):
                self._json_response(result, status=404)
            else:
                self._json_response(result)
        # S7-04: Learning-ready prompt history retrieval
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/prompt-history"):
            # GET /api/projects/{id}/prompt-history?persona_name=...&scenario_type=...
            project_id = clean_path.split("/")[3]
            result = project_manager.get_prompt_history(
                project_id,
                persona_name=query.get("persona_name") or None,
                scenario_type=query.get("scenario_type") or None,
            )
            self._json_response(result)

        # ── Diagram API ──
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/diagrams"):
            project_id = clean_path.split("/")[3]
            result = project_manager.list_diagrams(project_id)
            self._json_response(result)
        elif clean_path.startswith("/api/projects/") and "/diagrams/" in clean_path:
            parts = clean_path.split("/")
            project_id = parts[3]
            diagram_type = parts[5]
            result = project_manager.get_diagram(project_id, diagram_type)
            if result.get("error"):
                self._json_response(result, status=404)
            else:
                xml = result.get("xml", "")
                filename = f"{diagram_type}.drawio"
                self.send_response(200)
                self.send_header("Content-Type", "application/xml")
                self.send_header(
                    "Content-Disposition", f'attachment; filename="{filename}"'
                )
                self.send_header("Content-Length", str(len(xml.encode())))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(xml.encode())
        # ── Artifact API v1 ──
        elif "/artifacts" in clean_path and clean_path.startswith("/api/v1/projects/"):
            # GET /api/v1/projects/{projectId}/artifacts
            parts = clean_path.split("/")
            project_id = parts[4]
            self._handle_list_artifacts(project_id)
        # ── Job Status (Section C) ──
        elif clean_path.startswith("/api/v1/jobs/"):
            # GET /api/v1/jobs/{jobId}
            parts = clean_path.split("/")
            job_id = parts[4] if len(parts) > 4 else parts[3]
            self._handle_get_job(job_id)
        elif clean_path == "/api/personas":
            self._handle_list_personas()
        else:
            self._json_response({"errorCode": "NOT_FOUND", "message": "Not found"}, status=404)

    def do_POST(self) -> None:
        """Handle POST requests."""
        # Normalize path for route matching
        clean_path, query = self._parse_path()

        if clean_path == "/api/projects":
            self._handle_create_project()
        elif clean_path == "/api/ingest":
            self._handle_ingest()
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/build-context"):
            project_id = clean_path.split("/")[3]
            self._handle_build_context(project_id)
        elif clean_path.startswith("/api/projects/") and "/diagrams/" in clean_path and clean_path.endswith("/generate"):
            # POST /api/projects/{id}/diagrams/{type}/generate
            parts = clean_path.split("/")
            project_id = parts[3]
            diagram_type = parts[5]
            self._handle_generate_diagram(project_id, diagram_type)
        elif clean_path == "/api/review":
            self._handle_review()
        elif clean_path == "/api/personas":
            self._handle_list_personas()
        # ── Admin endpoints ──
        elif clean_path == "/api/admin/config":
            self._handle_update_config()
        # ── Project lifecycle ──
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/archive"):
            project_id = clean_path.split("/")[3]
            self._handle_archive_project(project_id)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/restore"):
            project_id = clean_path.split("/")[3]
            self._handle_restore_project(project_id)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/delete") and "/hierarchy/" not in clean_path:
            project_id = clean_path.split("/")[3]
            self._handle_delete_project(project_id)
        # ── Deep Dive & Feedback ──
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/deep-dive"):
            project_id = clean_path.split("/")[3]
            self._handle_deep_dive(project_id)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/deep-dive/feedback"):
            project_id = clean_path.split("/")[3]
            self._handle_deep_dive_feedback(project_id)
        # ── Existing endpoints ──
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/compare-versions"):
            project_id = clean_path.split("/")[3]
            self._handle_compare_versions(project_id)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/compare-reviews"):
            project_id = clean_path.split("/")[3]
            self._handle_compare_reviews(project_id)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/proposal"):
            project_id = clean_path.split("/")[3]
            self._handle_create_proposal(project_id)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/proposal/version"):
            project_id = clean_path.split("/")[3]
            self._handle_add_proposal_version(project_id)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/proposal/generate"):
            # POST /api/projects/{id}/proposal/generate
            project_id = clean_path.split("/")[3]
            body = self._read_body() or {}
            result = project_manager.generate_proposal_doc(
                project_id=project_id,
                proposal_ver_id=body.get("proposal_ver_id", ""),
                hierarchy_version_id=body.get("hierarchy_version_id", ""),
                review_id=body.get("review_id", ""),
                ai_backend=body.get("ai_backend", "files_only"),
                force=bool(body.get("force", False)),
            )
            if result.get("error"):
                self._json_response(result, status=422)
            else:
                self._json_response({"document": result}, status=201)
        elif clean_path.startswith("/api/projects/") and "/proposal/version/" in clean_path and clean_path.endswith("/status"):
            # POST /api/projects/{id}/proposal/version/{version_id}/status
            parts = clean_path.split("/")
            project_id = parts[3]
            version_id = parts[6]
            self._handle_update_proposal_version_status(project_id, version_id)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/phase"):
            project_id = clean_path.split("/")[3]
            self._handle_phase_transition(project_id)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/hierarchy/phase"):
            project_id = clean_path.split("/")[3]
            self._handle_hierarchy_phase_transition(project_id)
        elif self.path.startswith("/api/projects/") and "/hierarchy/reviews/" in self.path and self.path.endswith("/delete"):
            # POST /api/projects/{id}/hierarchy/reviews/{review_id}/delete
            parts = self.path.split("/")
            project_id = parts[3]
            review_id = parts[6]
            self._handle_delete_review(project_id, review_id)
        elif self.path.startswith("/api/projects/") and "/hierarchy/versions/" in self.path and self.path.endswith("/set-active-review"):
            # POST /api/projects/{id}/hierarchy/versions/{version_id}/set-active-review
            parts = self.path.split("/")
            project_id = parts[3]
            version_id = parts[6]
            self._handle_set_active_review(project_id, version_id)
        elif self.path.startswith("/api/projects/") and "/hierarchy/reviews/" in self.path and self.path.endswith("/complete"):
            # POST /api/projects/{id}/hierarchy/reviews/{review_id}/complete
            parts = self.path.split("/")
            project_id = parts[3]
            review_id = parts[6]
            body = self._read_body() or {}
            try:
                result = project_manager.complete_review_gate(
                    project_id, review_id,
                    body.get("completed_by", ""),
                    body.get("quality_status", "complete"),
                )
                self._json_response(result)
            except ValueError as e:
                self._json_response({"error": str(e)}, status=400)
        elif self.path.startswith("/api/projects/") and "/hierarchy/reviews/" in self.path and "/weakness/" in self.path and self.path.endswith("/status"):
            # POST /api/projects/{id}/hierarchy/reviews/{review_id}/weakness/{weakness_id}/status
            parts = self.path.split("/")
            project_id = parts[3]
            review_id = parts[6]
            weakness_id = parts[8]
            body = self._read_body() or {}
            result = project_manager.update_weakness_status(
                project_id, review_id, weakness_id, body.get("status", "")
            )
            if result.get("error"):
                self._json_response(result, status=400)
            else:
                self._json_response(result)
        elif self.path.startswith("/api/projects/") and "/hierarchy/reviews/" in self.path and "/decision/" in self.path and self.path.endswith("/status"):
            # POST /api/projects/{id}/hierarchy/reviews/{review_id}/decision/{decision_id}/status
            parts = self.path.split("/")
            project_id = parts[3]
            review_id = parts[6]
            decision_id = parts[8]
            body = self._read_body() or {}
            result = project_manager.update_decision_status(
                project_id, review_id, decision_id, body.get("status", "")
            )
            if result.get("error"):
                self._json_response(result, status=400)
            else:
                self._json_response(result)
        elif self.path.startswith("/api/projects/") and "/hierarchy/versions/" in self.path and self.path.endswith("/set-active-review-gated"):
            # POST /api/projects/{id}/hierarchy/versions/{version_id}/set-active-review-gated
            parts = self.path.split("/")
            project_id = parts[3]
            version_id = parts[6]
            body = self._read_body() or {}
            result = project_manager.set_active_review_gated(
                project_id, version_id,
                body.get("review_id", ""),
                body.get("decided_by", ""),
                force=bool(body.get("force", False)),
            )
            if result.get("error"):
                self._json_response(result, status=422)
            else:
                self._json_response(result)
        elif self.path.startswith("/api/projects/") and self.path.endswith("/toggle-file"):
            project_id = self.path.split("/")[3]
            self._handle_toggle_file(project_id)
        # ── Guardrails ──
        elif clean_path == "/api/validate-files":
            self._handle_validate_files()
        # ── Artifact API v1 ──
        elif "/artifacts/upload" in clean_path and clean_path.startswith("/api/v1/projects/"):
            parts = clean_path.split("/")
            project_id = parts[4]
            self._handle_artifact_upload(project_id)
        elif "/artifacts/text" in clean_path and clean_path.startswith("/api/v1/projects/"):
            parts = clean_path.split("/")
            project_id = parts[4]
            self._handle_artifact_text(project_id)
        elif "/artifacts/" in clean_path and "/toggle" in clean_path and clean_path.startswith("/api/v1/projects/"):
            parts = clean_path.split("/")
            project_id = parts[4]
            artifact_id = parts[6]
            self._handle_artifact_toggle(project_id, artifact_id)
        elif "/artifacts/" in clean_path and "/delete" in clean_path and clean_path.startswith("/api/v1/projects/"):
            parts = clean_path.split("/")
            project_id = parts[4]
            artifact_id = parts[6]
            self._handle_artifact_delete(project_id, artifact_id)
        # ── Processing Pipeline (Section C) ──
        elif "/artifacts/process" in clean_path and clean_path.startswith("/api/v1/projects/") and not clean_path.rstrip("/").split("/")[-1].startswith("a_"):
            # POST /api/v1/projects/{projectId}/artifacts/process  (process ALL)
            parts = clean_path.split("/")
            project_id = parts[4]
            self._handle_process_all_artifacts(project_id)
        elif "/artifacts/" in clean_path and "/process" in clean_path and clean_path.startswith("/api/v1/projects/"):
            # POST /api/v1/projects/{projectId}/artifacts/{artifactId}/process
            parts = clean_path.split("/")
            project_id = parts[4]
            artifact_id = parts[6]
            self._handle_process_artifact(project_id, artifact_id)
        # ── PATCH endpoint (Section D) ──
        elif "/artifacts/" in clean_path and clean_path.startswith("/api/v1/projects/") and "/toggle" not in clean_path and "/delete" not in clean_path and "/process" not in clean_path:
            # PATCH /api/v1/projects/{projectId}/artifacts/{artifactId} (update include/title/metadata)
            parts = clean_path.split("/")
            if len(parts) >= 7:
                project_id = parts[4]
                artifact_id = parts[6]
                self._handle_patch_artifact(project_id, artifact_id)
            else:
                self._json_response({"errorCode": "INVALID_REQUEST", "message": "Invalid artifact path"}, status=400)
        # ── P9: Pre-sales feedback API ──
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/feedback"):
            project_id = clean_path.split("/")[3]
            self._handle_create_presales_feedback(project_id)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/feedback/classify"):
            # POST /api/projects/{id}/presales/feedback/classify — DS-06 hybrid tagger
            project_id = clean_path.split("/")[3]
            self._handle_classify_feedback(project_id)
        elif clean_path.startswith("/api/projects/") and "/presales/feedback/" in clean_path and clean_path.endswith("/action"):
            parts = clean_path.split("/")
            project_id = parts[3]
            feedback_id = parts[6]
            self._handle_action_presales_feedback(project_id, feedback_id)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/share"):
            project_id = clean_path.split("/")[3]
            self._handle_create_feedback_token(project_id)
        elif clean_path.startswith("/api/projects/") and clean_path.endswith("/presales/finalise"):
            # POST /api/projects/{id}/presales/finalise — DS-08 atomic finalisation
            project_id = clean_path.split("/")[3]
            body = self._read_body() or {}
            decided_by = body.get("decided_by", "")
            if not decided_by:
                self._json_response({"error": "decided_by is required to finalise"}, status=400)
            else:
                result = project_manager.finalise_presales(
                    project_id,
                    decided_by=decided_by,
                    reason=body.get("reason", ""),
                    force=bool(body.get("force", False)),
                )
                if result.get("error"):
                    self._json_response(result, status=422)
                else:
                    self._json_response(result, status=200)
        elif clean_path == "/api/feedback/submit":
            self._handle_external_feedback_submit()
        else:
            self._json_response({"errorCode": "NOT_FOUND", "message": "Not found"}, status=404)

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_PATCH(self) -> None:
        """Handle PATCH requests – routed same as POST for artifact updates."""
        clean_path, query = self._parse_path()
        # PATCH /api/v1/projects/{projectId}/artifacts/{artifactId}
        if "/artifacts/" in clean_path and clean_path.startswith("/api/v1/projects/"):
            parts = clean_path.split("/")
            if len(parts) >= 7:
                project_id = parts[4]
                artifact_id = parts[6]
                self._handle_patch_artifact(project_id, artifact_id)
            else:
                self._json_response({"errorCode": "INVALID_REQUEST", "message": "Invalid path"}, status=400)
        else:
            self._json_response({"errorCode": "NOT_FOUND", "message": "Not found"}, status=404)

    # ══════════════════════════════════════════════════════════
    # P9 – Pre-sales Feedback Handlers
    # ══════════════════════════════════════════════════════════

    def _handle_get_presales_summary(self, project_id: str) -> None:
        """GET /api/projects/{id}/presales/summary"""
        from processors.presales_feedback import get_presales_summary
        result = get_presales_summary(project_id)
        self._json_response(result)

    def _handle_list_presales_feedback(self, project_id: str) -> None:
        """GET /api/projects/{id}/presales/feedback"""
        from db.project_store_sql import load_presales_feedback
        items = load_presales_feedback(project_id)
        self._json_response({"project_id": project_id, "feedback": items, "count": len(items)})

    def _handle_get_presales_feedback_item(self, project_id: str, feedback_id: str) -> None:
        """GET /api/projects/{id}/presales/feedback/{feedback_id}"""
        from db.project_store_sql import load_presales_feedback_item
        item = load_presales_feedback_item(feedback_id)
        if item and item.get("project_id") == project_id:
            self._json_response(item)
        else:
            self._json_response({"error": "Feedback not found"}, status=404)

    def _handle_classify_feedback(self, project_id: str) -> None:
        """POST /api/projects/{id}/presales/feedback/classify — DS-06 hybrid tagger.

        Splits raw text into paragraphs and classifies each one.
        files_only → heuristic pre-fill; AI backend → LLM classification.
        """
        from processors.feedback_classifier import classify_feedback
        body = self._read_body() or {}
        raw_text   = body.get("raw_text", "")
        ai_backend = body.get("ai_backend", "files_only")
        if not raw_text.strip():
            self._json_response({"error": "raw_text is required"}, status=400)
            return
        result = classify_feedback(raw_text, project_id, ai_backend)
        self._json_response(result)

    def _handle_create_presales_feedback(self, project_id: str) -> None:
        """POST /api/projects/{id}/presales/feedback — internal feedback capture.

        DS-06: accepts structured feedback_items[] (from hybrid tagger) OR
        legacy flat accepted/rejected/concerns lists.
        """
        import uuid as _uuid
        from db.project_store_sql import save_presales_feedback
        body = self._read_body() or {}
        feedback_id = f"fb_{_uuid.uuid4().hex[:8]}"
        # DS-06: prefer structured feedback_items if present
        feedback_items = body.get("feedback_items") or None
        raw_text       = body.get("raw_text", "")
        item = save_presales_feedback(
            project_id=project_id,
            feedback_id=feedback_id,
            proposal_ver_id=body.get("proposal_ver_id", ""),
            review_id=body.get("review_id", ""),
            source=body.get("source", "internal"),
            responder_name=body.get("responder_name", ""),
            responder_email=body.get("responder_email", ""),
            feedback_items=feedback_items,
            raw_text=raw_text,
            # legacy flat lists (ignored when feedback_items present)
            accepted=body.get("accepted", []),
            rejected=body.get("rejected", []),
            concerns=body.get("concerns", []),
            notes=body.get("notes", ""),
            next_action=body.get("next_action", ""),
            status="open",
            version_id=body.get("version_id", ""),
        )
        try:
            from processors.presales_feedback import attach_feedback_to_context
            attach_feedback_to_context(project_id, item)
        except Exception:
            pass
        self._json_response({"feedback": item}, status=201)

    def _handle_action_presales_feedback(self, project_id: str, feedback_id: str) -> None:
        """POST /api/projects/{id}/presales/feedback/{id}/action — update status/next_action."""
        from db.project_store_sql import load_presales_feedback_item, save_presales_feedback
        body = self._read_body() or {}
        item = load_presales_feedback_item(feedback_id)
        if not item or item.get("project_id") != project_id:
            self._json_response({"error": "Feedback not found"}, status=404)
            return
        updated = save_presales_feedback(
            project_id=project_id,
            feedback_id=feedback_id,
            proposal_ver_id=item["proposal_ver_id"],
            review_id=item["review_id"],
            source=item["source"],
            responder_name=item["responder_name"],
            responder_email=item["responder_email"],
            accepted=item["accepted"],
            rejected=item["rejected"],
            concerns=item["concerns"],
            notes=body.get("notes", item["notes"]),
            next_action=body.get("next_action", item["next_action"]),
            status=body.get("status", item["status"]),
        )
        self._json_response({"feedback": updated})

    def _handle_create_feedback_token(self, project_id: str) -> None:
        """POST /api/projects/{id}/presales/share — create external share token."""
        from db.project_store_sql import create_feedback_token
        body = self._read_body() or {}
        token = create_feedback_token(
            project_id=project_id,
            proposal_ver_id=body.get("proposal_ver_id", ""),
            review_id=body.get("review_id", ""),
            expires_days=int(body.get("expires_days", 7)),
        )
        # Build share URL (relative — host resolved by client)
        share_url = f"/feedback?token={token}"
        self._json_response({
            "token": token,
            "share_url": share_url,
            "expires_days": body.get("expires_days", 7),
        }, status=201)

    def _handle_feedback_form(self, token: str) -> None:
        """GET /api/feedback/form?token=… — return form context for external page."""
        from db.project_store_sql import validate_feedback_token
        row = validate_feedback_token(token)
        if not row:
            self._json_response({"error": "Invalid or expired token"}, status=404)
            return
        project_id = row["project_id"]
        # Load proposal summary for form display
        proposal = None
        try:
            proposal = project_manager.get_proposal_info(project_id)
        except Exception:
            pass
        project = project_manager.get_project(project_id)
        self._json_response({
            "valid": True,
            "project_id": project_id,
            "project_name": project.get("name", "") if project else "",
            "proposal_ver_id": row.get("proposal_ver_id", ""),
            "review_id": row.get("review_id", ""),
            "proposal": proposal,
        })

    def _handle_external_feedback_submit(self) -> None:
        """POST /api/feedback/submit — public endpoint, validated by token."""
        import uuid as _uuid
        from db.project_store_sql import validate_feedback_token, mark_token_used, save_presales_feedback
        body = self._read_body() or {}
        token = body.get("token", "")
        if not token:
            self._json_response({"error": "Token required"}, status=400)
            return
        row = validate_feedback_token(token)
        if not row:
            self._json_response({"error": "Invalid or expired token"}, status=403)
            return
        project_id = row["project_id"]
        feedback_id = f"fb_{_uuid.uuid4().hex[:8]}"
        item = save_presales_feedback(
            project_id=project_id,
            feedback_id=feedback_id,
            proposal_ver_id=row.get("proposal_ver_id", ""),
            review_id=row.get("review_id", ""),
            source="external",
            responder_name=body.get("responder_name", ""),
            responder_email=body.get("responder_email", ""),
            accepted=body.get("accepted", []),
            rejected=body.get("rejected", []),
            concerns=body.get("concerns", []),
            notes=body.get("notes", ""),
            next_action="",
            status="open",
        )
        mark_token_used(token)
        try:
            from processors.presales_feedback import attach_feedback_to_context
            attach_feedback_to_context(project_id, item)
        except Exception:
            pass
        self._json_response({"status": "submitted", "feedback_id": feedback_id}, status=201)

    def _handle_create_project(self) -> None:
        """Handle project creation."""
        body = self._read_body()
        if not body:
            self._json_response({"error": "Request body required"}, status=400)
            return

        name = body.get("name")
        if not name:
            self._json_response({"error": "Project name required"}, status=400)
            return

        try:
            project = project_manager.create_project(
                name=name,
                description=body.get("description", ""),
            )
            self._json_response({"project": project}, status=201)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=409)

    def _handle_ingest(self) -> None:
        """Handle file ingestion into a project."""
        body = self._read_body()
        if not body:
            self._json_response({"error": "Request body required"}, status=400)
            return

        project_id = body.get("project_id")
        file_paths = body.get("file_paths", [])

        if not project_id:
            self._json_response({"error": "project_id required"}, status=400)
            return
        if not file_paths:
            self._json_response({"error": "file_paths required"}, status=400)
            return

        try:
            paths = [Path(fp) for fp in file_paths]
            result = project_manager.ingest_files_to_project(project_id, paths)
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=404)
        except Exception as e:
            self._json_response({"error": str(e)}, status=500)

    def _handle_review(self) -> None:
        """Handle persona review request.

        Accepts either a single role string (``persona`` field) or a list
        of role names (``roles`` field, max 3).  Both map to the v2 engine.
        """
        body = self._read_body()
        if not body:
            self._json_response({"error": "Request body required"}, status=400)
            return

        project_id = body.get("project_id")
        # v2: accept "roles" list; fall back to legacy "persona" string
        roles = body.get("roles") or body.get("persona")
        ai_backend = body.get("ai_backend", "files_only")
        custom_prompt = body.get("custom_prompt")
        previous_review_id = body.get("previous_review_id", "")
        prompt_builder_state = body.get("prompt_builder_state")  # S2: structured builder state

        if not project_id:
            self._json_response({"error": "project_id required"}, status=400)
            return
        if not roles:
            self._json_response({"error": "roles (or persona) required"}, status=400)
            return

        try:
            result = project_manager.run_persona_review(
                project_id=project_id,
                persona_name=roles,
                ai_backend=ai_backend,
                custom_prompt=custom_prompt,
                previous_review_id=previous_review_id,
                prompt_builder_state=prompt_builder_state,
            )
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=400)
        except Exception as e:
            self._json_response({"error": str(e)}, status=500)

    def _handle_list_personas(self) -> None:
        """Return all visible roles with group metadata (v2)."""
        from personas.engine import list_roles
        roles = list_roles()
        # Keep 'personas' key for backward-compat with any stored UI state
        self._json_response({"personas": roles, "roles": roles})

    def _handle_build_context(self, project_id: str) -> None:
        """Build/rebuild project intelligence from ingested documents."""
        body = self._read_body() or {}
        version_label = body.get("label")
        ai_backend = body.get("ai_backend")  # optional override; falls back to project default
        try:
            result = project_manager.build_project_intelligence(
                project_id, version_label, ai_backend=ai_backend
            )
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=404)
        except Exception as e:
            self._json_response({"error": str(e)}, status=500)

    def _handle_generate_diagram(self, project_id: str, diagram_type: str) -> None:
        """Generate a .drawio diagram from built project intelligence.

        Optional body params: version_id, review_id — when supplied the
        diagram is enriched with findings from that review context.
        """
        body = self._read_body() or {}
        version_id = body.get("version_id") or None
        review_id = body.get("review_id") or None
        try:
            result = project_manager.generate_diagram(
                project_id, diagram_type,
                version_id=version_id,
                review_id=review_id,
            )
            if result.get("error"):
                self._json_response(result, status=400)
            else:
                self._json_response(result)
        except Exception as e:
            self._json_response({"error": str(e)}, status=500)

    def _handle_compare_versions(self, project_id: str) -> None:
        """Compare two context versions."""
        body = self._read_body()
        if not body:
            self._json_response({"error": "Request body required"}, status=400)
            return

        version_a = body.get("version_a")
        version_b = body.get("version_b")

        if not version_a or not version_b:
            self._json_response(
                {"error": "version_a and version_b required"}, status=400
            )
            return

        try:
            result = project_manager.compare_project_versions(
                project_id, version_a, version_b
            )
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=404)

    def _handle_compare_reviews(self, project_id: str) -> None:
        """Compare two review results."""
        body = self._read_body()
        if not body:
            self._json_response({"error": "Request body required"}, status=400)
            return

        review_a = body.get("review_a")
        review_b = body.get("review_b")

        if not review_a or not review_b:
            self._json_response(
                {"error": "review_a and review_b filenames required"}, status=400
            )
            return

        try:
            result = project_manager.compare_project_reviews(
                project_id, review_a, review_b
            )
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=404)

    def _handle_create_proposal(self, project_id: str) -> None:
        """Create a proposal for a project. DS-07: requires hierarchy_version_id + review_id."""
        body = self._read_body() or {}
        name = body.get("proposal_name") or body.get("name") or "Untitled Proposal"
        hierarchy_version_id = body.get("hierarchy_version_id", "")
        active_review_id     = body.get("review_id", "") or body.get("active_review_id", "")
        try:
            result = project_manager.create_proposal(
                project_id, name,
                client=body.get("client", ""),
                notes=body.get("notes", ""),
                hierarchy_version_id=hierarchy_version_id,
                active_review_id=active_review_id,
            )
            self._json_response(result, status=201)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=422)

    def _handle_add_proposal_version(self, project_id: str) -> None:
        """Add a version to existing proposal. DS-07: requires hierarchy_version_id + review_id."""
        body = self._read_body() or {}
        try:
            result = project_manager.add_proposal_version(
                project_id,
                label=body.get("label", ""),
                notes=body.get("notes", ""),
                changes=body.get("changes", ""),
                hierarchy_version_id=body.get("hierarchy_version_id", ""),
                active_review_id=body.get("review_id", "") or body.get("active_review_id", ""),
                feedback_applied=body.get("feedback_applied", []),
                changes_summary=body.get("changes_summary", ""),
            )
            self._json_response(result, status=201)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=422)

    def _handle_update_proposal_version_status(self, project_id: str, version_id: str) -> None:
        """POST /api/projects/{id}/proposal/version/{version_id}/status"""
        body = self._read_body() or {}
        new_status = body.get("status", "")
        if not new_status:
            self._json_response({"error": "status required"}, status=400)
            return
        # DS-08: enforce soft lock — reject writes unless override_reason provided
        try:
            from db.project_store_sql import get_db, Database
            db = get_db()
            row = db.fetchone(
                "SELECT lock_status, lock_reason FROM proposal_versions "
                "WHERE project_id=? AND version_id=?",
                (project_id, version_id),
            )
            if row and row.get("lock_status") == "soft_locked":
                override_reason = body.get("override_reason", "")
                if not override_reason:
                    self._json_response({
                        "error": "This proposal version is soft-locked (finalised). "
                                 "Provide 'override_reason' to proceed.",
                        "lock_reason": row.get("lock_reason", ""),
                        "lock_status": "soft_locked",
                    }, status=409)
                    return
                # Log the override
                from db.decision_log import log_decision
                log_decision(
                    project_id=project_id,
                    entity_type="proposal_version",
                    entity_id=version_id,
                    action="lock_overridden",
                    actor=body.get("decided_by", ""),
                    reason=override_reason,
                    metadata={"new_status": new_status},
                )
        except Exception:
            pass
        try:
            result = project_manager.update_proposal_status(project_id, version_id, new_status)
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=400)

    def _handle_phase_transition(self, project_id: str) -> None:
        """Transition project phase."""
        body = self._read_body() or {}
        new_phase = body.get("new_phase", "")
        reason = body.get("reason", "")
        if not new_phase:
            self._json_response({"error": "new_phase required"}, status=400)
            return
        try:
            result = project_manager.transition_project_phase(project_id, new_phase, reason)
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=400)

    def _handle_hierarchy_phase_transition(self, project_id: str) -> None:
        """Transition phase in hierarchy model."""
        body = self._read_body() or {}
        phase_id = body.get("phase_id", "")
        reason = body.get("reason", "")
        if not phase_id:
            self._json_response({"error": "phase_id required"}, status=400)
            return
        try:
            result = project_manager.set_hierarchy_phase(project_id, phase_id, reason)
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=400)

    def _handle_delete_review(self, project_id: str, review_id: str) -> None:
        """Delete a review from the hierarchy."""
        result = project_manager.delete_hierarchy_review(project_id, review_id)
        if result.get("error"):
            self._json_response(result, status=404)
        else:
            self._json_response(result)

    def _handle_set_active_review(self, project_id: str, version_id: str) -> None:
        """Set the active review for a version."""
        body = self._read_body() or {}
        review_id = body.get("review_id", "")
        if not review_id:
            self._json_response({"error": "review_id required"}, status=400)
            return
        result = project_manager.set_active_review(project_id, version_id, review_id)
        if result.get("error"):
            self._json_response(result, status=400)
        else:
            self._json_response(result)

    def _handle_archive_project(self, project_id: str) -> None:
        """Archive a project (requires PIN)."""
        body = self._read_body() or {}
        pin = body.get("pin", "")
        try:
            result = project_manager.archive_project(project_id, pin)
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=403)

    def _handle_delete_project(self, project_id: str) -> None:
        """Permanently delete a project (requires PIN)."""
        body = self._read_body() or {}
        pin = body.get("pin", "")
        try:
            result = project_manager.delete_project(project_id, pin)
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=403)

    def _handle_toggle_file(self, project_id: str) -> None:
        """Toggle file active/inactive for review cycles."""
        body = self._read_body() or {}
        filename = body.get("filename", "")
        active = body.get("active", True)
        if not filename:
            self._json_response({"error": "filename required"}, status=400)
            return
        try:
            result = project_manager.toggle_file_active(project_id, filename, active)
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=400)

    def _handle_restore_project(self, project_id: str) -> None:
        """Restore a project from archive (requires PIN)."""
        body = self._read_body() or {}
        pin = body.get("pin", "")
        try:
            result = project_manager.restore_project(project_id, pin)
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=403)

    def _handle_update_config(self) -> None:
        """Update admin configuration."""
        body = self._read_body()
        if not body:
            self._json_response({"error": "Request body required"}, status=400)
            return
        try:
            config = project_manager.update_admin_config(body)
            self._json_response({"config": config})
        except Exception as e:
            self._json_response({"error": str(e)}, status=500)

    def _handle_deep_dive(self, project_id: str) -> None:
        """Run Deep Dive analysis."""
        body = self._read_body() or {}
        persona = body.get("persona", "")
        custom_prompt = body.get("custom_prompt", "")
        review_id = body.get("review_id", "")
        weaknesses = []
        missing_categories = []
        decision_points = []
        if review_id:
            try:
                from models.hierarchy import _make_hierarchy_store
                from processors.review_quality import extract_weaknesses, compute_missing_categories
                store = _make_hierarchy_store(project_id)
                review = store.get_review(review_id)
                if review:
                    weaknesses = extract_weaknesses(review.findings)
                    missing_categories = compute_missing_categories(review.findings)
                    decision_points = [
                        dp for dp in (review.decision_points or [])
                        if dp.get("status", "open") == "open"
                    ]
            except Exception:
                pass
        try:
            result = project_manager.run_deep_dive_analysis(
                project_id, persona, custom_prompt,
                weaknesses=weaknesses,
                missing_categories=missing_categories,
                decision_points=decision_points,
            )
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=400)
        except Exception as e:
            self._json_response({"error": str(e)}, status=500)

    def _handle_deep_dive_feedback(self, project_id: str) -> None:
        """Apply feedback to deep dive results."""
        body = self._read_body() or {}
        try:
            result = project_manager.apply_deep_dive_feedback(
                project_id,
                accepted=body.get("accepted"),
                rejected=body.get("rejected"),
                added_to_prompt=body.get("added_to_prompt"),
            )
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=400)

    def _handle_validate_files(self) -> None:
        """Validate file types before ingestion."""
        body = self._read_body() or {}
        file_paths = body.get("file_paths", [])
        if not file_paths:
            self._json_response({"error": "file_paths required"}, status=400)
            return
        result = project_manager.validate_files_for_ingestion(file_paths)
        self._json_response(result)

    # ── Artifact API v1 Handlers ──

    def _handle_list_artifacts(self, project_id: str) -> None:
        """GET /api/v1/projects/{projectId}/artifacts"""
        from db.artifact_store_sql import list_artifacts
        artifacts = list_artifacts(project_id)
        self._json_response({"artifacts": artifacts})

    def _handle_artifact_upload(self, project_id: str) -> None:
        """POST /api/v1/projects/{projectId}/artifacts/upload

        Handles multipart/form-data file upload.
        Falls back to JSON body with base64 content for simple clients.
        """
        from db.artifact_store_sql import store_file_artifact
        import base64

        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))

        if "multipart/form-data" in content_type:
            # Parse multipart form data
            file_content, file_name, category, title, metadata = self._parse_multipart_upload(
                content_type, content_length
            )
        else:
            # JSON body fallback: {fileName, content (base64), category, title, metadata}
            body = self._read_body() or {}
            file_name = body.get("fileName", body.get("file_name", ""))
            content_b64 = body.get("content", "")
            category = body.get("category", "")
            title = body.get("title", "")
            metadata = body.get("metadata", {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except Exception:
                    metadata = {}

            if not file_name:
                self._json_response({"error": "fileName is required"}, status=400)
                return
            if not content_b64:
                self._json_response({"error": "content (base64) is required"}, status=400)
                return
            try:
                file_content = base64.b64decode(content_b64)
            except Exception:
                self._json_response({"error": "Invalid base64 content"}, status=400)
                return

        if not category:
            self._json_response({"error": "category is required"}, status=400)
            return

        try:
            artifact = store_file_artifact(
                project_id=project_id,
                file_name=file_name,
                file_content=file_content,
                category=category,
                title=title,
                metadata=metadata if isinstance(metadata, dict) else {},
            )
            self._json_response({"artifact": artifact.to_api_dict()}, status=201)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=400)

    def _handle_artifact_text(self, project_id: str) -> None:
        """POST /api/v1/projects/{projectId}/artifacts/text"""
        from db.artifact_store_sql import store_text_artifact
        from models.artifact import validate_metadata_for_category

        body = self._read_body() or {}
        text = body.get("text", "")
        category = body.get("category", "")
        title = body.get("title", "")
        metadata = body.get("metadata", {})

        if not category:
            self._json_response({"errorCode": "INVALID_REQUEST", "message": "category is required"}, status=400)
            return
        if not text or not text.strip():
            self._json_response({"errorCode": "INVALID_REQUEST", "message": "text is required"}, status=400)
            return

        # Validate metadata against category schema
        if metadata and isinstance(metadata, dict):
            valid, errors = validate_metadata_for_category(category, metadata)
            if not valid:
                self._json_response({"errorCode": "INVALID_REQUEST", "message": "; ".join(errors)}, status=400)
                return

        try:
            artifact = store_text_artifact(
                project_id=project_id,
                text=text,
                category=category,
                title=title,
                metadata=metadata if isinstance(metadata, dict) else {},
            )
            self._json_response({"artifact": artifact.to_api_dict()}, status=201)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=400)

    def _handle_artifact_toggle(self, project_id: str, artifact_id: str) -> None:
        """POST /api/v1/projects/{projectId}/artifacts/{artifactId}/toggle"""
        from db.artifact_store_sql import toggle_artifact_include

        body = self._read_body() or {}
        include = body.get("include", True)
        result = toggle_artifact_include(project_id, artifact_id, include)
        if result:
            self._json_response({"artifact": result})
        else:
            self._json_response({"error": "Artifact not found"}, status=404)

    def _handle_artifact_delete(self, project_id: str, artifact_id: str) -> None:
        """POST /api/v1/projects/{projectId}/artifacts/{artifactId}/delete"""
        from db.artifact_store_sql import delete_artifact

        deleted = delete_artifact(project_id, artifact_id)
        if deleted:
            self._json_response({"status": "deleted", "artifactId": artifact_id})
        else:
            self._json_response({"errorCode": "NOT_FOUND", "message": "Artifact not found"}, status=404)

    def _handle_process_artifact(self, project_id: str, artifact_id: str) -> None:
        """POST /api/v1/projects/{projectId}/artifacts/{artifactId}/process"""
        from processors.pipeline import process_artifact

        try:
            job = process_artifact(project_id, artifact_id)
            self._json_response({"job": job}, status=202)
        except Exception as e:
            self._json_response({"errorCode": "INTERNAL_ERROR", "message": str(e)}, status=500)

    def _handle_process_all_artifacts(self, project_id: str) -> None:
        """POST /api/v1/projects/{projectId}/artifacts/process"""
        from processors.pipeline import process_all_artifacts

        body = self._read_body() or {}
        only_included = body.get("onlyIncluded", True)
        force = body.get("force", True)  # Default force=True so re-processing always works

        try:
            queued_ids = process_all_artifacts(project_id, only_included, force=force)
            self._json_response({"queuedArtifactIds": queued_ids}, status=202)
        except Exception as e:
            self._json_response({"errorCode": "INTERNAL_ERROR", "message": str(e)}, status=500)

    def _handle_get_job(self, job_id: str) -> None:
        """GET /api/v1/jobs/{jobId}"""
        from processors.pipeline import JobStore

        job = JobStore.get_job(job_id)
        if job:
            self._json_response(job)
        else:
            self._json_response({"errorCode": "NOT_FOUND", "message": f"Job not found: {job_id}"}, status=404)

    def _handle_patch_artifact(self, project_id: str, artifact_id: str) -> None:
        """PATCH /api/v1/projects/{projectId}/artifacts/{artifactId}

        Update include flag, title, or metadata.
        """
        from processors.artifact_store import (
            get_artifact,
            _load_registry,
            _save_registry,
        )
        from models.artifact import Artifact, validate_metadata_for_category

        body = self._read_body() or {}
        if not body:
            self._json_response({"errorCode": "INVALID_REQUEST", "message": "Request body required"}, status=400)
            return

        registry = _load_registry(project_id)
        updated = False
        result_artifact = None

        for entry in registry:
            if entry.get("artifact_id") == artifact_id:
                if "include" in body:
                    entry["include"] = bool(body["include"])
                if "title" in body:
                    entry["title"] = body["title"]
                if "metadata" in body and isinstance(body["metadata"], dict):
                    # Validate metadata against category schema
                    category = entry.get("category", "")
                    valid, errors = validate_metadata_for_category(category, body["metadata"])
                    if not valid:
                        self._json_response({"errorCode": "INVALID_REQUEST", "message": "; ".join(errors)}, status=400)
                        return
                    entry["metadata"] = body["metadata"]
                updated = True
                result_artifact = Artifact.from_storage_dict(entry)
                break

        if not updated:
            self._json_response({"errorCode": "NOT_FOUND", "message": "Artifact not found"}, status=404)
            return

        _save_registry(project_id, registry)
        self._json_response({"artifact": result_artifact.to_api_dict()})

    def _parse_multipart_upload(self, content_type: str, content_length: int):
        """Parse multipart/form-data for file upload.

        Returns tuple: (file_content, file_name, category, title, metadata)
        """
        import re

        # Extract boundary
        boundary_match = re.search(r'boundary=([^\s;]+)', content_type)
        if not boundary_match:
            return b"", "", "", "", {}

        boundary = boundary_match.group(1).encode()
        raw_data = self.rfile.read(content_length)

        # Split by boundary
        parts = raw_data.split(b"--" + boundary)

        file_content = b""
        file_name = ""
        category = ""
        title = ""
        metadata = {}

        for part in parts:
            if not part or part == b"--\r\n" or part == b"--":
                continue

            # Split headers from body
            if b"\r\n\r\n" in part:
                headers_raw, body = part.split(b"\r\n\r\n", 1)
                headers_str = headers_raw.decode("utf-8", errors="replace")

                # Remove trailing boundary markers
                if body.endswith(b"\r\n"):
                    body = body[:-2]

                # Check Content-Disposition
                name_match = re.search(r'name="([^"]+)"', headers_str)
                filename_match = re.search(r'filename="([^"]+)"', headers_str)

                if name_match:
                    field_name = name_match.group(1)

                    if filename_match:
                        # File field
                        file_name = filename_match.group(1)
                        file_content = body
                    elif field_name == "category":
                        category = body.decode("utf-8", errors="replace").strip()
                    elif field_name == "title":
                        title = body.decode("utf-8", errors="replace").strip()
                    elif field_name == "metadata":
                        try:
                            metadata = json.loads(body.decode("utf-8", errors="replace"))
                        except Exception:
                            metadata = {}

        return file_content, file_name, category, title, metadata

    def _read_body(self) -> dict:
        """Read and parse JSON request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def _json_response(self, data: Any, status: int = 200) -> None:
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _serve_static(self, filename: str) -> None:
        """Serve a static file from the static/ directory."""
        static_dir = Path(__file__).parent / "static"
        file_path = static_dir / filename
        if not file_path.exists() or not file_path.is_file():
            self._json_response({"error": "Not found"}, status=404)
            return
        # Determine content type
        ext = file_path.suffix.lower()
        content_types = {
            ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
            ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml",
        }
        content_type = content_types.get(ext, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(file_path.read_bytes())


def main() -> None:
    """Start the server."""
    project_manager.PROJECTS_DIR.mkdir(exist_ok=True)
    server = HTTPServer((HOST, PORT), AcceleratorHandler)
    print(f"{APP_NAME} v{APP_VERSION}")
    print(f"Listening on http://{HOST}:{PORT}")
    data_dir = os.environ.get("PROJECTS_DATA_DIR", "projects_data/")
    print(f"Data directory: {data_dir}")
    server.serve_forever()


if __name__ == "__main__":
    main()
