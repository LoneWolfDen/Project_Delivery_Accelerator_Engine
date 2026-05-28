"""Tests for sample data integrity – ensures test fixtures are valid."""

from pathlib import Path


SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"


class TestSampleDataExists:
    """Verify sample data files exist and are non-empty."""

    def test_scope_file_exists(self):
        assert (SAMPLE_DIR / "scope.txt").exists()

    def test_scope_cpg_file_exists(self):
        assert (SAMPLE_DIR / "scope_cpg.txt").exists()

    def test_scope_files_have_content(self):
        for name in ["scope.txt", "scope_cpg.txt"]:
            content = (SAMPLE_DIR / name).read_text()
            assert len(content) > 100, f"{name} is too short"

    def test_csv_files_exist(self):
        csv_files = list(SAMPLE_DIR.glob("*.csv"))
        assert len(csv_files) >= 2, "Expected at least 2 CSV sample files"
