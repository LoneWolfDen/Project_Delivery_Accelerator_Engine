"""Project Delivery Accelerator Engine – Main Server.

Lightweight API server providing:
- Project CRUD
- File upload and ingestion
- Context building
- Persona-driven reviews
- AI backend switching
"""

import json
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
        if self.path == "/api/health":
            self._json_response({"status": "ok", "version": "2.0.0"})
        elif self.path == "/api/projects":
            projects = project_manager.list_projects()
            self._json_response({"projects": projects})
        elif self.path.startswith("/api/projects/") and self.path.endswith("/context"):
            project_id = self.path.split("/")[3]
            context = project_manager.get_project_context(project_id)
            self._json_response({"project_id": project_id, "documents": context})
        elif self.path.startswith("/api/projects/") and self.path.endswith("/intelligence"):
            project_id = self.path.split("/")[3]
            intelligence = project_manager.get_project_intelligence(project_id)
            self._json_response({"project_id": project_id, "intelligence": intelligence})
        elif self.path.startswith("/api/projects/") and self.path.endswith("/summary"):
            project_id = self.path.split("/")[3]
            summary = project_manager.get_project_summary(project_id)
            self._json_response({"project_id": project_id, "summary": summary})
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
        try:
            result = project_manager.build_project_intelligence(project_id)
            self._json_response(result)
        except ValueError as e:
            self._json_response({"error": str(e)}, status=404)
        except Exception as e:
            self._json_response({"error": str(e)}, status=500)

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


def main() -> None:
    """Start the server."""
    project_manager.PROJECTS_DIR.mkdir(exist_ok=True)
    server = HTTPServer((HOST, PORT), AcceleratorHandler)
    print("Project Delivery Accelerator Engine v2.0")
    print(f"Listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
