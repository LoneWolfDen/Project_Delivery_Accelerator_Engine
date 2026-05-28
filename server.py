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

# Configuration
HOST = "localhost"
PORT = 8080


class AcceleratorHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the delivery accelerator API."""

    def do_GET(self) -> None:
        """Handle GET requests."""
        # Serve Web UI
        if self.path == "/" or self.path == "":
            self._serve_static("index.html")
            return
        if self.path.startswith("/static/") or self.path.endswith((".html", ".css", ".js")):
            filename = self.path.lstrip("/")
            if not filename.startswith("static/"):
                filename = "static/" + filename
            self._serve_static(filename.replace("static/", ""))
            return

        # API endpoints
        if self.path == "/api/health":
            self._json_response({"status": "ok", "version": "3.0.0"})
        elif self.path == "/api/backends":
            from ai_backends import list_backends
            self._json_response({"backends": list_backends()})
        elif self.path == "/api/projects":
            projects = project_manager.list_projects()
            self._json_response({"projects": projects})
        elif self.path == "/api/projects/all":
            projects = project_manager.list_all_projects()
            self._json_response({"projects": projects})
        # ── Admin endpoints ──
        elif self.path == "/api/admin/config":
            config = project_manager.get_admin_config()
            self._json_response({"config": config})
        elif self.path == "/api/admin/health":
            health = project_manager.get_system_health_status()
            self._json_response({"health": health})
        elif self.path == "/api/admin/lifecycle":
            logs = project_manager.get_lifecycle_logs()
            self._json_response({"lifecycle": logs})
        elif self.path == "/api/admin/auto-archive-suggestions":
            suggestions = project_manager.get_auto_archive_suggestions()
            self._json_response({"suggestions": suggestions})
        # ── Project-specific endpoints ──
        elif self.path.startswith("/api/projects/") and self.path.endswith("/context"):
            project_id = self.path.split("/")[3]
            context = project_manager.get_project_context(project_id)
            toggles = project_manager.get_file_toggles(project_id)
            self._json_response({"project_id": project_id, "documents": context, "file_toggles": toggles})
        elif self.path.startswith("/api/projects/") and self.path.endswith("/file-toggles"):
            project_id = self.path.split("/")[3]
            toggles = project_manager.get_file_toggles(project_id)
            self._json_response({"project_id": project_id, "file_toggles": toggles})
        elif self.path.startswith("/api/projects/") and self.path.endswith("/intelligence"):
            project_id = self.path.split("/")[3]
            intelligence = project_manager.get_project_intelligence(project_id)
            self._json_response({"project_id": project_id, "intelligence": intelligence})
        elif self.path.startswith("/api/projects/") and self.path.endswith("/summary"):
            project_id = self.path.split("/")[3]
            summary = project_manager.get_project_summary(project_id)
            self._json_response({"project_id": project_id, "summary": summary})
        elif self.path.startswith("/api/projects/") and self.path.endswith("/versions"):
            project_id = self.path.split("/")[3]
            versions = project_manager.get_project_versions(project_id)
            self._json_response({"project_id": project_id, "versions": versions})
        elif self.path.startswith("/api/projects/") and "/versions/" in self.path:
            # GET /api/projects/{id}/versions/{version_id}
            parts = self.path.split("/")
            project_id = parts[3]
            version_id = parts[5]
            version = project_manager.get_project_version(project_id, version_id)
            if version:
                self._json_response({"project_id": project_id, "version": version})
            else:
                self._json_response({"error": f"Version not found: {version_id}"}, status=404)
        elif self.path.startswith("/api/projects/") and self.path.endswith("/run-history"):
            project_id = self.path.split("/")[3]
            history = project_manager.get_run_history_for_project(project_id)
            self._json_response({"project_id": project_id, "run_history": history})
        elif self.path.startswith("/api/projects/") and "/file-snapshot/" in self.path:
            # GET /api/projects/{id}/file-snapshot/{version_id}
            parts = self.path.split("/")
            project_id = parts[3]
            version_id = parts[5]
            snapshot = project_manager.get_file_snapshot(project_id, version_id)
            if snapshot:
                self._json_response(snapshot)
            else:
                self._json_response({"error": "Snapshot not found"}, status=404)
        elif self.path.startswith("/api/projects/") and self.path.endswith("/reviews"):
            # GET /api/projects/{id}/reviews?persona=solution_architect
            project_id = self.path.split("/")[3].split("?")[0]
            # Simple query param parsing
            persona_filter = None
            if "?" in self.path:
                query = self.path.split("?")[1]
                for param in query.split("&"):
                    if param.startswith("persona="):
                        persona_filter = param.split("=")[1]
            reviews = project_manager.get_project_review_history(project_id, persona_filter)
            self._json_response({"project_id": project_id, "reviews": reviews})
        elif self.path.startswith("/api/projects/") and "/evolution/" in self.path:
            # GET /api/projects/{id}/evolution/{category}
            parts = self.path.split("/")
            project_id = parts[3]
            category = parts[5]
            timeline = project_manager.get_project_evolution(project_id, category)
            self._json_response({"project_id": project_id, "category": category, "timeline": timeline})
        elif self.path.startswith("/api/projects/") and self.path.endswith("/proposal"):
            project_id = self.path.split("/")[3]
            proposal = project_manager.get_proposal_info(project_id)
            if proposal:
                self._json_response(proposal)
            else:
                self._json_response({"error": "No proposal exists"}, status=404)
        elif self.path.startswith("/api/projects/") and self.path.endswith("/phase-history"):
            project_id = self.path.split("/")[3]
            history = project_manager.get_phase_history_for_project(project_id)
            self._json_response({"project_id": project_id, "history": history})
        # ── Artifact API v1 ──
        elif "/artifacts" in self.path and self.path.startswith("/api/v1/projects/"):
            # GET /api/v1/projects/{projectId}/artifacts
            parts = self.path.split("/")
            project_id = parts[4]
            self._handle_list_artifacts(project_id)
        else:
            self._json_response({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        """Handle POST requests."""
        if self.path == "/api/projects":
            self._handle_create_project()
        elif self.path == "/api/ingest":
            self._handle_ingest()
        elif self.path.startswith("/api/projects/") and self.path.endswith("/build-context"):
            project_id = self.path.split("/")[3]
            self._handle_build_context(project_id)
        elif self.path == "/api/review":
            self._handle_review()
        elif self.path == "/api/personas":
            self._handle_list_personas()
        # ── Admin endpoints ──
        elif self.path == "/api/admin/config":
            self._handle_update_config()
        # ── Project lifecycle ──
        elif self.path.startswith("/api/projects/") and self.path.endswith("/archive"):
            project_id = self.path.split("/")[3]
            self._handle_archive_project(project_id)
        elif self.path.startswith("/api/projects/") and self.path.endswith("/restore"):
            project_id = self.path.split("/")[3]
            self._handle_restore_project(project_id)
        elif self.path.startswith("/api/projects/") and self.path.endswith("/delete"):
            project_id = self.path.split("/")[3]
            self._handle_delete_project(project_id)
        # ── Deep Dive & Feedback ──
        elif self.path.startswith("/api/projects/") and self.path.endswith("/deep-dive"):
            project_id = self.path.split("/")[3]
            self._handle_deep_dive(project_id)
        elif self.path.startswith("/api/projects/") and self.path.endswith("/deep-dive/feedback"):
            project_id = self.path.split("/")[3]
            self._handle_deep_dive_feedback(project_id)
        # ── Existing endpoints ──
        elif self.path.startswith("/api/projects/") and self.path.endswith("/compare-versions"):
            project_id = self.path.split("/")[3]
            self._handle_compare_versions(project_id)
        elif self.path.startswith("/api/projects/") and self.path.endswith("/compare-reviews"):
            project_id = self.path.split("/")[3]
            self._handle_compare_reviews(project_id)
        elif self.path.startswith("/api/projects/") and self.path.endswith("/proposal"):
            project_id = self.path.split("/")[3]
            self._handle_create_proposal(project_id)
        elif self.path.startswith("/api/projects/") and self.path.endswith("/proposal/version"):
            project_id = self.path.split("/")[3]
            self._handle_add_proposal_version(project_id)
        elif self.path.startswith("/api/projects/") and self.path.endswith("/phase"):
            project_id = self.path.split("/")[3]
            self._handle_phase_transition(project_id)
        elif self.path.startswith("/api/projects/") and self.path.endswith("/toggle-file"):
            project_id = self.path.split("/")[3]
            self._handle_toggle_file(project_id)
        # ── Guardrails ──
        elif self.path == "/api/validate-files":
            self._handle_validate_files()
        # ── Artifact API v1 ──
        elif "/artifacts/upload" in self.path and self.path.startswith("/api/v1/projects/"):
            parts = self.path.split("/")
            project_id = parts[4]
            self._handle_artifact_upload(project_id)
        elif "/artifacts/text" in self.path and self.path.startswith("/api/v1/projects/"):
            parts = self.path.split("/")
            project_id = parts[4]
            self._handle_artifact_text(project_id)
        elif "/artifacts/" in self.path and "/toggle" in self.path and self.path.startswith("/api/v1/projects/"):
            parts = self.path.split("/")
            project_id = parts[4]
            artifact_id = parts[6]
            self._handle_artifact_toggle(project_id, artifact_id)
        elif "/artifacts/" in self.path and "/delete" in self.path and self.path.startswith("/api/v1/projects/"):
            parts = self.path.split("/")
            project_id = parts[4]
            artifact_id = parts[6]
            self._handle_artifact_delete(project_id, artifact_id)
        else:
            self._json_response({"error": "Not found"}, status=404)

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

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
        """Handle persona review request."""
        body = self._read_body()
        if not body:
            self._json_response({"error": "Request body required"}, status=400)
            return

        project_id = body.get("project_id")
        persona_name = body.get("persona")
        ai_backend = body.get("ai_backend", "files_only")
        custom_prompt = body.get("custom_prompt")

        if not project_id:
            self._json_response({"error": "project_id required"}, status=400)
            return
        if not persona_name:
            self._json_response({"error": "persona required"}, status=400)
            return

        try:
            result = project_manager.run_persona_review(
                project_id=project_id,
                persona_name=persona_name,
                ai_backend=ai_backend,
                custom_prompt=custom_prompt,
            )
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=400)
        except Exception as e:
            self._json_response({"error": str(e)}, status=500)

    def _handle_list_personas(self) -> None:
        """Handle listing available personas."""
        from personas.engine import list_personas
        self._json_response({"personas": list_personas()})

    def _handle_build_context(self, project_id: str) -> None:
        """Build/rebuild project intelligence from ingested documents."""
        body = self._read_body()
        version_label = body.get("label") if body else None
        try:
            result = project_manager.build_project_intelligence(project_id, version_label)
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=404)
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
        """Create a proposal for a project."""
        body = self._read_body()
        name = body.get("name", "Untitled Proposal") if body else "Untitled Proposal"
        try:
            result = project_manager.create_proposal(
                project_id, name, body.get("client", ""), notes=body.get("notes", "")
            )
            self._json_response(result, status=201)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=400)

    def _handle_add_proposal_version(self, project_id: str) -> None:
        """Add a version to existing proposal."""
        body = self._read_body() or {}
        try:
            result = project_manager.add_proposal_version(
                project_id, body.get("label", ""), notes=body.get("notes", ""),
                changes=body.get("changes", ""),
            )
            self._json_response(result, status=201)
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
        try:
            result = project_manager.run_deep_dive_analysis(
                project_id, persona, custom_prompt
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
        from processors.artifact_store import list_artifacts
        artifacts = list_artifacts(project_id)
        self._json_response({"artifacts": artifacts})

    def _handle_artifact_upload(self, project_id: str) -> None:
        """POST /api/v1/projects/{projectId}/artifacts/upload

        Handles multipart/form-data file upload.
        Falls back to JSON body with base64 content for simple clients.
        """
        from processors.artifact_store import store_file_artifact
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
        from processors.artifact_store import store_text_artifact

        body = self._read_body() or {}
        text = body.get("text", "")
        category = body.get("category", "")
        title = body.get("title", "")
        metadata = body.get("metadata", {})

        if not category:
            self._json_response({"error": "category is required"}, status=400)
            return
        if not text or not text.strip():
            self._json_response({"error": "text is required"}, status=400)
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
        from processors.artifact_store import toggle_artifact_include

        body = self._read_body() or {}
        include = body.get("include", True)
        result = toggle_artifact_include(project_id, artifact_id, include)
        if result:
            self._json_response({"artifact": result})
        else:
            self._json_response({"error": "Artifact not found"}, status=404)

    def _handle_artifact_delete(self, project_id: str, artifact_id: str) -> None:
        """POST /api/v1/projects/{projectId}/artifacts/{artifactId}/delete"""
        from processors.artifact_store import delete_artifact

        deleted = delete_artifact(project_id, artifact_id)
        if deleted:
            self._json_response({"status": "deleted", "artifactId": artifact_id})
        else:
            self._json_response({"error": "Artifact not found"}, status=404)

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
    print("Project Delivery Accelerator Engine v3.0")
    print(f"Listening on http://{HOST}:{PORT}")
    print("V3: Admin, Archive/Restore, Persona Deep Dive, Version Control, Guardrails")
    server.serve_forever()


if __name__ == "__main__":
    main()
