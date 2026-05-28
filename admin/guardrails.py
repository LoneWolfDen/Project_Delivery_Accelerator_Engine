"""Guardrails – Safeguards for intelligence operations.

Prevents:
- Running intelligence with zero files
- Invalid file types
- Missing API key when AI backend selected

Validates:
- File type support
- API key presence for selected backend
- Project state eligibility
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from admin.config import load_config

# Supported file extensions for ingestion
SUPPORTED_FILE_TYPES = {".txt", ".md", ".csv", ".eml", ".json", ".yaml", ".yml"}


def validate_intelligence_run(
    project_id: str,
    file_count: int,
    ai_backend: str = "files_only",
) -> Tuple[bool, List[str]]:
    """Validate prerequisites for running intelligence.

    Args:
        project_id: Project ID.
        file_count: Number of ingested files.
        ai_backend: Selected AI backend.

    Returns:
        Tuple of (is_valid, list_of_errors).
    """
    errors: List[str] = []

    # Guard: zero files
    if file_count == 0:
        errors.append("Cannot run intelligence with zero ingested files. Ingest documents first.")

    # Guard: API key presence for AI backends
    if ai_backend and ai_backend != "files_only":
        key_check = check_api_key_for_backend(ai_backend)
        if not key_check["configured"]:
            errors.append(
                f"API key not configured for backend '{ai_backend}'. "
                f"Set {key_check.get('env_var', 'the API key')} or configure via Admin."
            )

    return (len(errors) == 0, errors)


def validate_file_types(file_paths: List[str]) -> Tuple[bool, List[str], List[str]]:
    """Validate file types for ingestion.

    Args:
        file_paths: List of file path strings.

    Returns:
        Tuple of (all_valid, valid_paths, error_messages).
    """
    valid_paths: List[str] = []
    errors: List[str] = []

    for fp in file_paths:
        ext = Path(fp).suffix.lower()
        if ext in SUPPORTED_FILE_TYPES:
            valid_paths.append(fp)
        else:
            errors.append(
                f"Unsupported file type '{ext}' for: {fp}. "
                f"Supported: {', '.join(sorted(SUPPORTED_FILE_TYPES))}"
            )

    return (len(errors) == 0, valid_paths, errors)


def validate_review_prerequisites(
    project_id: str,
    has_intelligence: bool,
    ai_backend: str = "files_only",
) -> Tuple[bool, List[str]]:
    """Validate prerequisites for running a persona review.

    Args:
        project_id: Project ID.
        has_intelligence: Whether intelligence has been built.
        ai_backend: Selected AI backend.

    Returns:
        Tuple of (is_valid, list_of_errors).
    """
    errors: List[str] = []

    if not has_intelligence:
        errors.append("No intelligence built. Run 'Build Intelligence' first.")

    if ai_backend and ai_backend != "files_only":
        key_check = check_api_key_for_backend(ai_backend)
        if not key_check["configured"]:
            errors.append(
                f"API key not configured for '{ai_backend}'. "
                f"Review will fall back to files_only analysis."
            )

    return (len(errors) == 0, errors)


def validate_project_state(
    project_status: str, operation: str
) -> Tuple[bool, str]:
    """Validate project state allows the requested operation.

    Args:
        project_status: Current project status (active/archived/deleted).
        operation: Operation being attempted.

    Returns:
        Tuple of (allowed, error_message).
    """
    if project_status == "deleted":
        return (False, f"Cannot perform '{operation}' on a deleted project.")

    if project_status == "archived":
        allowed_ops = {"restore", "view", "export"}
        if operation not in allowed_ops:
            return (False, f"Cannot perform '{operation}' on an archived project. Restore it first.")

    return (True, "")


def check_api_key_for_backend(backend_name: str) -> Dict[str, Any]:
    """Check if API key is configured for a specific backend.

    Args:
        backend_name: Backend identifier.

    Returns:
        Dict with configured (bool) and env_var name.
    """
    import os

    backend_keys = {
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "bedrock": "AWS_ACCESS_KEY_ID",
        "ollama": None,  # Local, no key needed
        "files_only": None,  # No key needed
    }

    env_var = backend_keys.get(backend_name)

    if env_var is None:
        return {"configured": True, "env_var": None, "backend": backend_name}

    # Check environment
    configured = bool(os.environ.get(env_var, ""))

    # Also check admin config
    if not configured:
        config = load_config()
        configured = bool(config.api_keys.get(backend_name, ""))

    return {"configured": configured, "env_var": env_var, "backend": backend_name}
