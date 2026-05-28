"""Shared test fixtures for Project Delivery Accelerator tests."""

import sys
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def sample_data_dir():
    """Return path to sample data directory."""
    return PROJECT_ROOT / "sample_data"


@pytest.fixture
def sample_scope_text(sample_data_dir):
    """Load the healthcare scope document as text."""
    return (sample_data_dir / "scope.txt").read_text()


@pytest.fixture
def sample_scope_cpg_text(sample_data_dir):
    """Load the CPG scope document as text."""
    return (sample_data_dir / "scope_cpg.txt").read_text()
