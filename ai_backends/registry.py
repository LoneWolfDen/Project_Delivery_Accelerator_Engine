"""Backend registry – factory for creating and listing AI backends."""

from typing import Dict, List, Any, Optional

from ai_backends.base import AIBackend
from ai_backends.files_only import FilesOnlyBackend
from ai_backends.ollama_backend import OllamaBackend
from ai_backends.bedrock_backend import BedrockBackend
from ai_backends.gemini_backend import GeminiBackend


# Registry of all available backends
_BACKENDS: Dict[str, type] = {
    "files_only": FilesOnlyBackend,
    "ollama": OllamaBackend,
    "bedrock": BedrockBackend,
    "gemini": GeminiBackend,
}


def get_backend(name: str, **kwargs) -> AIBackend:
    """Get an AI backend instance by name.

    Args:
        name: Backend identifier ('files_only', 'ollama', 'bedrock', 'gemini').
        **kwargs: Backend-specific configuration (e.g. model, api_key).

    Returns:
        Configured AIBackend instance.

    Raises:
        ValueError: If backend name is unknown.
    """
    backend_class = _BACKENDS.get(name)
    if backend_class is None:
        available = ", ".join(_BACKENDS.keys())
        raise ValueError(f"Unknown AI backend: '{name}'. Available: {available}")

    return backend_class(**kwargs)


def list_backends() -> List[Dict[str, Any]]:
    """List all registered backends with availability status.

    Returns:
        List of dicts with name, display_name, available.
    """
    results = []
    for name, cls in _BACKENDS.items():
        try:
            instance = cls()
            results.append(instance.get_info())
        except Exception:
            results.append({
                "name": name,
                "display_name": name,
                "available": False,
            })
    return results


def register_backend(name: str, backend_class: type) -> None:
    """Register a new backend class.

    Args:
        name: Backend identifier.
        backend_class: Class that extends AIBackend.
    """
    _BACKENDS[name] = backend_class
