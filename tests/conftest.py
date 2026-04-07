import os
import pytest
from pathlib import Path


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory for tests."""
    config_dir = tmp_path / "mbquery"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_profile() -> dict:
    return {
        "url": "https://metabase.example.com",
        "auth": {"method": "api-key", "api_key": "mb_test123"},
        "default_db": 2,
    }
