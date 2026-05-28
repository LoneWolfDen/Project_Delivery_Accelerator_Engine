"""Tests for migration data integrity and consistency."""
import csv
from pathlib import Path


class TestEpicPlan:
    """Validate epic plan data."""

    def test_epic_count(self, sample_epics):
        assert len(sample_epics) == 26

    def test_all_epics_have_required_fields(self, sample_epics):
        required = ["Phase", "Epic_ID", "Epic_Name", "Start_Week", "End_Week", "Owner_Team"]
        for epic in sample_epics:
            for field in required:
                assert epic.get(field), f"Epic {epic.get('Epic_ID')} missing {field}"

    def test_epic_ids_unique(self, sample_epics):
        ids = [e["Epic_ID"] for e in sample_epics]
        assert len(ids) == len(set(ids)), "Duplicate epic IDs found"

    def test_weeks_are_valid(self, sample_epics):
        for epic in sample_epics:
            start = int(epic["Start_Week"])
            end = int(epic["End_Week"])
            assert 1 <= start <= 37, f"{epic['Epic_ID']} invalid start week: {start}"
            assert 1 <= end <= 37, f"{epic['Epic_ID']} invalid end week: {end}"
            assert start <= end, f"{epic['Epic_ID']} start > end"

    def test_phases_present(self, sample_epics):
        phases = set(e["Phase"] for e in sample_epics)
        expected = {
            "Phase 0 - Mobilisation",
            "Phase 1 - Foundation",
            "Phase 2 - Core Business",
            "Phase 3 - Dependent",
            "Phase 4 - Legacy/Modernise",
        }
        assert phases == expected

    def test_total_duration_37_weeks(self, sample_epics):
        max_week = max(int(e["End_Week"]) for e in sample_epics)
        assert max_week == 37


class TestResourcePlan:
    """Validate resource plan data."""

    def test_resource_count(self, sample_resources):
        assert len(sample_resources) == 18

    def test_all_resources_have_required_fields(self, sample_resources):
        required = ["Role_ID", "Role", "Count", "Onboard_Week", "Offboard_Week"]
        for r in sample_resources:
            for field in required:
                assert r.get(field), f"Resource {r.get('Role_ID')} missing {field}"

    def test_onboard_before_offboard(self, sample_resources):
        for r in sample_resources:
            on = int(r["Onboard_Week"])
            off = int(r["Offboard_Week"])
            assert on < off, f"{r['Role_ID']} onboard ({on}) >= offboard ({off})"

    def test_role_ids_unique(self, sample_resources):
        ids = [r["Role_ID"] for r in sample_resources]
        assert len(ids) == len(set(ids))


class TestNFRRequirements:
    """Validate NFR requirements data."""

    def test_nfr_count(self, sample_nfrs):
        assert len(sample_nfrs) == 61

    def test_all_nfrs_have_required_fields(self, sample_nfrs):
        required = ["App_ID", "Migration_Phase", "NFR_Category", "Target_Metric", "Priority"]
        for nfr in sample_nfrs:
            for field in required:
                assert nfr.get(field), f"NFR for {nfr.get('App_ID')} missing {field}"

    def test_valid_phases(self, sample_nfrs):
        valid = {"Foundation", "Core Business", "Dependent", "Legacy/Modernise"}
        for nfr in sample_nfrs:
            assert nfr["Migration_Phase"] in valid, f"Invalid phase: {nfr['Migration_Phase']}"

    def test_valid_priorities(self, sample_nfrs):
        valid = {"Critical", "High", "Medium", "Low"}
        for nfr in sample_nfrs:
            assert nfr["Priority"] in valid, f"Invalid priority: {nfr['Priority']}"


class TestOperationalTracking:
    """Validate operational tracking data."""

    def test_app_count(self, sample_tracking):
        assert len(sample_tracking) == 20

    def test_all_apps_have_phase(self, sample_tracking):
        for app in sample_tracking:
            assert app.get("Migration_Phase"), f"{app['App_ID']} missing phase"

    def test_all_apps_have_owner(self, sample_tracking):
        for app in sample_tracking:
            assert app.get("Owner_Team"), f"{app['App_ID']} missing owner"

    def test_phase_order_valid(self, sample_tracking):
        for app in sample_tracking:
            order = int(app["Phase_Order"])
            assert 1 <= order <= 4, f"{app['App_ID']} invalid phase order: {order}"
