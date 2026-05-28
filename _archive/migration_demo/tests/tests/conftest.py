"""Shared test fixtures for migration dashboard tests."""
import sys
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "migration_dashboard"))


@pytest.fixture
def data_dir():
    """Return path to test data directory."""
    return PROJECT_ROOT / "migration_dashboard" / "data"


@pytest.fixture
def diagrams_dir():
    """Return path to diagrams directory."""
    return PROJECT_ROOT / "migration_dashboard" / "diagrams"


@pytest.fixture
def sample_epics(data_dir):
    """Load epic plan CSV as list of dicts."""
    import csv
    with open(data_dir / "migration_epic_plan.csv") as f:
        return list(csv.DictReader(f))


@pytest.fixture
def sample_resources(data_dir):
    """Load resource plan CSV as list of dicts."""
    import csv
    with open(data_dir / "migration_resource_plan.csv") as f:
        return list(csv.DictReader(f))


@pytest.fixture
def sample_nfrs(data_dir):
    """Load NFR requirements CSV as list of dicts."""
    import csv
    with open(data_dir / "migration_nfr_requirements.csv") as f:
        return list(csv.DictReader(f))


@pytest.fixture
def sample_tracking(data_dir):
    """Load operational tracking CSV as list of dicts."""
    import csv
    with open(data_dir / "migration_operational_tracking.csv") as f:
        return list(csv.DictReader(f))
