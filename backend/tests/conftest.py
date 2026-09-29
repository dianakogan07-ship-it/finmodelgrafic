import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_tmp = Path(os.environ.get("PYTEST_TMP", "/tmp")) / f"suz-test-{os.getpid()}"
_tmp.mkdir(parents=True, exist_ok=True)
os.environ.update(
    DATABASE_URL=f"sqlite:///{_tmp}/test.db",
    JWT_SECRET="test-secret",
    ADMIN_LOGIN="admin",
    ADMIN_PASSWORD="admin-pass-123",
    MODEL_DIR=str(_tmp / "models"),
    SEED_MODEL=os.environ.get("MODEL_PATH", str(_tmp / "no-model.xlsx")),
    CALC_URLS="http://127.0.0.1:9",  # недоступен: пересчёт в тестах API подменяется
)

MODEL_PATH = os.environ.get("MODEL_PATH")
needs_model = pytest.mark.skipif(not MODEL_PATH or not Path(MODEL_PATH).exists(), reason="MODEL_PATH не задан — положите xlsx модели")
