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

# Configuration
HOST = "localhost"
PORT = 8080
PROJECTS_DIR = Path("projects_data")


class AcceleratorHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the delivery accelerator API."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/api/health":
            self._json_response({"status": "ok", "version": "2.0.0"})
        elif self.path == "/api/projects":
            self._json_response({"projects": [], "message": "Not yet implemented"})
        else:
            self._json_response({"error": "Not found"}, status=404)

    def do_POST(self):
        """Handle POST requests."""
        if self.path == "/api/projects":
            self._json_response({"message": "Project creation not yet implemented"}, status=501)
        elif self.path == "/api/ingest":
            self._json_response({"message": "Ingestion not yet implemented"}, status=501)
        elif self.path == "/api/review":
            self._json_response({"message": "Persona review not yet implemented"}, status=501)
        else:
            self._json_response({"error": "Not found"}, status=404)

    def _json_response(self, data: Any, status: int = 200):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def main():
    """Start the server."""
    PROJECTS_DIR.mkdir(exist_ok=True)
    server = HTTPServer((HOST, PORT), AcceleratorHandler)
    print(f"Project Delivery Accelerator Engine v2.0")
    print(f"Listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
