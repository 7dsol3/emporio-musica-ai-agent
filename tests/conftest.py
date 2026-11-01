from pathlib import Path

import pytest

from emporio.config import ROOT, Settings
from emporio.service import AgentService


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=ROOT / "data", state_dir=tmp_path / "state")


@pytest.fixture
def agent(settings):
    return AgentService(settings)
