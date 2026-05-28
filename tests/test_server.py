"""Tests for the v2 API server."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import AcceleratorHandler


class TestServerImports:
    """Validate server module loads correctly."""

    def test_handler_class_exists(self):
        assert AcceleratorHandler is not None

    def test_handler_has_get(self):
        assert hasattr(AcceleratorHandler, "do_GET")

    def test_handler_has_post(self):
        assert hasattr(AcceleratorHandler, "do_POST")
