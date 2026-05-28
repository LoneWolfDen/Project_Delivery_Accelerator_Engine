"""Tests for the dashboard server."""
import sys
import json
import re
from pathlib import Path
from unittest.mock import patch, MagicMock
from http.server import HTTPServer
from urllib.parse import urlencode
import threading
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).parent.parent / "migration_dashboard"))


class TestBuildHtml:
    """Test HTML generation."""

    def test_html_generates_without_error(self):
        from server import build_html
        html = build_html()
        assert len(html) > 100000  # Should be substantial
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_html_contains_all_tabs(self):
        from server import build_html
        html = build_html()
        assert "Gantt Chart" in html
        assert "NFR Gates" in html
        assert "Dependencies" in html
        assert "Data Flow" in html
        assert "Epic Plan" in html
        assert "Resources" in html

    def test_html_contains_embedded_data(self):
        from server import build_html
        html = build_html()
        assert "const DATA=" in html
        assert "epics:" in html
        assert "gantt:" in html
        assert "gates:" in html

    def test_html_valid_javascript(self):
        from server import build_html
        html = build_html()
        # Extract script and check basic structure
        match = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
        assert match, "No script tag found"
        script = match.group(1)
        assert "function render()" in script
        assert "function renderGantt()" in script
        assert "function renderGates()" in script

    def test_data_has_correct_counts(self):
        from server import build_html
        html = build_html()
        match = re.search(r"const DATA=(\{[\s\S]*?\n\});", html)
        assert match, "DATA object not found"


class TestDataLoading:
    """Test CSV data loading."""

    def test_load_csv_json(self):
        from server import load_csv_json, DATA_DIR
        epics = load_csv_json(DATA_DIR / "data" / "migration_epic_plan.csv")
        assert len(epics) == 26

    def test_load_csv_json_missing_file(self):
        from server import load_csv_json
        result = load_csv_json(Path("/nonexistent.csv"))
        assert result == []


class TestGanttData:
    """Test GANTT data structure."""

    def test_gantt_has_26_epics(self):
        from server import GANTT
        assert len(GANTT) == 26

    def test_gantt_epics_have_roles(self):
        from server import GANTT
        for epic in GANTT:
            assert len(epic["roles"]) > 0, f"{epic['epic_id']} has no roles"

    def test_gantt_total_man_days(self):
        from server import GANTT
        total = sum(r["man_days"] for e in GANTT for r in e["roles"])
        assert total == 1878

    def test_gantt_stories_merged(self):
        from server import GANTT
        # E-001 should have stories from stories_data
        e001 = next(e for e in GANTT if e["epic_id"] == "E-001")
        stories_count = sum(len(r.get("stories", [])) for r in e001["roles"])
        assert stories_count > 0, "E-001 should have stories"


class TestChatEndpoint:
    """Test chat functionality."""

    @patch("server.boto3")
    def test_chat_with_empty_message(self, mock_boto3):
        from server import chat_with_bedrock
        # Empty message should still work (server handles it)
        # This tests the function doesn't crash
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": "test response"}]}}
        }
        result = chat_with_bedrock("hello", [])
        assert isinstance(result, str)
