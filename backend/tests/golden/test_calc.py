"""Эталонные сценарии пересчёта (results.md). Нужны MODEL_PATH и aspose-cells-python.

Колонка excel — значения, снятые вручную в Excel; пока не сняты, сверяем с зафиксированным
расчётом Aspose (регрессия). Допуск ТЗ: 0,01 млрд / 0,005.
"""
import importlib.util
from pathlib import Path

import pytest

from conftest import MODEL_PATH, needs_model

pytestmark = needs_model
pytest.importorskip("aspose.cells")
# грузим calc-worker/engine.py по пути: в calc-worker есть свой app.py, он не должен затенить backend/app
_spec = importlib.util.spec_from_file_location("calc_engine", Path(__file__).resolve().parents[3] / "calc-worker" / "engine.py")
engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(engine)

P, D = "Продажи", "Dashboard_2"
TAIL = ["X", "Y", "Z", "AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI", "AJ", "AK", "AL", "AM", "AN"]

# (сценарий, ФР aspose млрд, LLCR aspose, ФР excel, LLCR excel)
GOLDEN = [
    ("base", 18.5758, 1.19910, 18.5758, 1.19910),
    ("w12+10k", 18.5898, 1.19905, None, None),
    ("w12-10k", 18.5619, 1.19916, None, None),
    ("w15+100", 18.5647, 1.19915, None, None),
    ("x12+10k", 18.5935, 1.19903, None, None),
    ("w12+30k_w15+500", 18.5733, 1.19911, None, None),
]


@pytest.fixture(scope="module")
def wb():
    wb, _, _ = engine.load(MODEL_PATH)
    return wb


def _changes(wb, name):
    g = lambda a: engine.get(wb, P, a)  # noqa: E731
    W12, W15, X12 = g("W12"), g("W15"), g("X12")

    def tail(delta):
        s = sum(g(c + "15") or 0 for c in TAIL)
        k = (s - delta) / s
        d = {"W15": W15 + delta}
        d.update({c + "15": g(c + "15") * k for c in TAIL if g(c + "15")})
        return d

    return {
        "base": {},
        "w12+10k": {"W12": W12 + 10000},
        "w12-10k": {"W12": W12 - 10000},
        "w15+100": tail(100),
        "x12+10k": {"X12": X12 + 10000},
        "w12+30k_w15+500": {**tail(500), "W12": W12 + 30000},
    }[name]


@pytest.mark.parametrize("name,fr_a,llcr_a,fr_x,llcr_x", GOLDEN)
def test_golden(wb, name, fr_a, llcr_a, fr_x, llcr_x):
    ch = _changes(wb, name)
    orig = {a: engine.get(wb, P, a) for a in ch}
    for a, v in ch.items():
        engine.put(wb, P, a, v)
    try:
        engine.calculate(wb)
        fr, llcr = engine.get(wb, D, "G69") / 1e9, engine.get(wb, D, "E81")
    finally:
        for a, v in orig.items():
            engine.put(wb, P, a, v)
    fr_ref, llcr_ref = (fr_x, llcr_x) if fr_x is not None else (fr_a, llcr_a)
    assert abs(fr - fr_ref) <= 0.01
    assert abs(llcr - llcr_ref) <= 0.005
