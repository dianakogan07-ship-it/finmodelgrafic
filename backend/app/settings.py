import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


DATABASE_URL = _env("DATABASE_URL", "sqlite:///./suz.db")
JWT_SECRET = _env("JWT_SECRET")
JWT_TTL_HOURS = int(_env("JWT_TTL_HOURS", "12"))
ADMIN_LOGIN = _env("ADMIN_LOGIN")
ADMIN_PASSWORD = _env("ADMIN_PASSWORD")

MODEL_DIR = Path(_env("MODEL_DIR", "./data/models"))
SEED_MODEL = Path(_env("SEED_MODEL", "./data/model.xlsx"))
CELL_MAP = Path(_env("CELL_MAP", str(ROOT.parent / "config" / "cell_map.yaml")))
SEEDS_DIR = ROOT / "seeds"

CALC_URLS = [u.strip().rstrip("/") for u in _env("CALC_URLS", "http://localhost:8001").split(",") if u.strip()]
CALC_TIMEOUT_S = float(_env("CALC_TIMEOUT_S", "180"))

# допуск сверки пересчёта движком с кэшем Excel при загрузке модели
CHECK_FR_TOL = 0.01e9
CHECK_LLCR_TOL = 0.005

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET не задан (см. .env.example)")
