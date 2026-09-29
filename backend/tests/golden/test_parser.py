"""Парсер на файле 09_09_26 — значения из ТЗ, раздел 2 и 9."""
from conftest import MODEL_PATH, needs_model

pytestmark = needs_model


def test_parse_model_09_09_26():
    from app.model.parser import parse

    d = parse(MODEL_PATH)
    assert d["warnings"] == []
    assert round(d["fr"] / 1e9, 1) == 18.6
    assert round(d["llcr"], 2) == 1.20
    assert d["labels"][0] == "1кв. 26" and d["cols"][0] == "U"
    assert set(d["queues"]) == {"1", "2", "3"}
    q1 = d["queues"]["1"]
    assert q1["rows"] == {"price": 12, "area": 15}
    assert d["queues"]["2"]["rows"] == {"price": 58, "area": 61}
    assert d["queues"]["3"]["rows"] == {"price": 104, "area": 107}
    assert abs(q1["total"] - 53395.77) < 0.01
    i = d["labels"].index("3кв. 26")
    assert d["cols"][i] == "W"
    assert [round(x) for x in q1["price"][i:i + 4]] == [573, 586, 607, 622]
    assert [round(x / 1000, 1) for x in q1["area"][i:i + 4]] == [1.9, 2.4, 2.0, 2.6]


def test_scenario_writes_cells():
    from app.model import scenario
    from app.model.parser import parse

    d = parse(MODEL_PATH)
    i = d["labels"].index("3кв. 26")
    q = {k: {"price": list(v["price"]), "area": list(v["area"])} for k, v in d["queues"].items()}
    assert scenario.to_writes(d, q) == []
    q["1"]["price"][i] += 10
    w = scenario.to_writes(d, q)
    assert w == [{"sheet": "Продажи", "cell": "W12", "value": (d["queues"]["1"]["price"][i] + 10) * 1000}]
