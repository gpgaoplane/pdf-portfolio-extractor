from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
HOLDOUT = {"LendBridge_Q2_2024.pdf", "NovaCloud_Q3_2024.pdf",
           "MediSight_Q4_2024.pdf", "PeopleFlow_Q4_2024.pdf"}  # never read (D-005)

@pytest.fixture
def data_dir() -> Path:
    return DATA_DIR
