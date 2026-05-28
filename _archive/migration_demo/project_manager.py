"""Project persistence: max 5 projects, file uploads, artifact toggles."""
import json, uuid, shutil
from pathlib import Path

BASE = Path(__file__).parent
PROJECTS_FILE = BASE / "projects.json"
UPLOADS_DIR = BASE / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

ARTIFACTS = ["gantt", "gates", "deps", "dataflow", "epics", "resources", "tracking", "nfrs"]
LLM_BACKENDS = ["bedrock", "ollama", "files_only", "files+ollama"]


def _load() -> list:
    if PROJECTS_FILE.exists():
        try:
            return json.loads(PROJECTS_FILE.read_text())
        except Exception:
            pass
    return []


def _save(projects: list):
    PROJECTS_FILE.write_text(json.dumps(projects, indent=2))


def list_projects() -> list:
    return _load()


def get_project(pid: str) -> dict | None:
    return next((p for p in _load() if p["id"] == pid), None)


def create_project(name: str) -> dict | None:
    projects = _load()
    if len(projects) >= 5:
        return None
    pid = uuid.uuid4().hex[:8]
    project = {
        "id": pid,
        "name": name,
        "llm_backend": "bedrock",
        "ollama_model": "llama3",
        "artifact_toggles": {a: [] for a in ARTIFACTS},  # list of enabled filenames per artifact
    }
    projects.append(project)
    _save(projects)
    (UPLOADS_DIR / pid).mkdir(exist_ok=True)
    return project


def delete_project(pid: str) -> bool:
    projects = _load()
    new = [p for p in projects if p["id"] != pid]
    if len(new) == len(projects):
        return False
    _save(new)
    proj_dir = UPLOADS_DIR / pid
    if proj_dir.exists():
        shutil.rmtree(proj_dir)
    return True


def update_project(pid: str, patch: dict) -> dict | None:
    projects = _load()
    for p in projects:
        if p["id"] == pid:
            if "name" in patch:
                p["name"] = patch["name"]
            if "llm_backend" in patch and patch["llm_backend"] in LLM_BACKENDS:
                p["llm_backend"] = patch["llm_backend"]
            if "ollama_model" in patch:
                p["ollama_model"] = str(patch["ollama_model"]).strip() or "llama3"
            if "artifact_toggles" in patch:
                import datetime
                if "toggle_history" not in p:
                    p["toggle_history"] = []
                for artifact, files in patch["artifact_toggles"].items():
                    old = set(p["artifact_toggles"].get(artifact, []))
                    new = set(files)
                    for f in new - old:
                        p["toggle_history"].append({"ts": datetime.datetime.utcnow().isoformat(), "artifact": artifact, "file": f, "action": "enabled"})
                    for f in old - new:
                        p["toggle_history"].append({"ts": datetime.datetime.utcnow().isoformat(), "artifact": artifact, "file": f, "action": "disabled"})
                p["artifact_toggles"].update(patch["artifact_toggles"])
            _save(projects)
            return p
    return None


def list_files(pid: str) -> list:
    proj_dir = UPLOADS_DIR / pid
    if not proj_dir.exists():
        return []
    return [f.name for f in sorted(proj_dir.iterdir()) if f.is_file()]


def save_file(pid: str, filename: str, data: bytes) -> str:
    proj_dir = UPLOADS_DIR / pid
    proj_dir.mkdir(exist_ok=True)
    # Sanitise filename
    safe = Path(filename).name.replace(" ", "_")
    (proj_dir / safe).write_bytes(data)
    return safe


def delete_file(pid: str, filename: str) -> bool:
    fp = UPLOADS_DIR / pid / Path(filename).name
    if fp.exists():
        fp.unlink()
        return True
    return False


def get_project_data(pid: str) -> dict:
    """Return saved per-project tab data, or empty dict if none."""
    fp = UPLOADS_DIR / pid / "_project_data.json"
    if fp.exists():
        try:
            return json.loads(fp.read_text())
        except Exception:
            pass
    return {}


def save_project_data(pid: str, artifact: str, data) -> bool:
    """Persist generated tab data for a project artifact."""
    proj_dir = UPLOADS_DIR / pid
    proj_dir.mkdir(exist_ok=True)
    fp = proj_dir / "_project_data.json"
    existing = {}
    if fp.exists():
        try:
            existing = json.loads(fp.read_text())
        except Exception:
            pass
    existing[artifact] = data
    fp.write_text(json.dumps(existing))
    return True


def read_enabled_files(pid: str, artifact: str) -> str:
    """Return concatenated text of all enabled files for an artifact."""
    project = get_project(pid)
    if not project:
        return ""
    enabled = project["artifact_toggles"].get(artifact, [])
    proj_dir = UPLOADS_DIR / pid
    parts = []
    for fname in enabled:
        fp = proj_dir / fname
        if fp.exists():
            try:
                parts.append(f"=== {fname} ===\n{fp.read_text(errors='replace')}")
            except Exception:
                pass
    return "\n\n".join(parts)
