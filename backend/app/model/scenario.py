"""Сценарий (ряды цены и продаж по очередям) → записи в ячейки модели."""
from .cellmap import cell_map


class ScenarioError(ValueError):
    pass


def to_writes(data: dict, queues: dict) -> list[dict]:
    s = cell_map()["sales"]
    n = len(data["labels"])
    writes = []
    for q, cur in queues.items():
        base = data["queues"].get(str(q))
        if base is None:
            raise ScenarioError(f"Очереди {q} нет в модели.")
        price, area = cur.get("price"), cur.get("area")
        if price is None or area is None or len(price) != n or len(area) != n:
            raise ScenarioError(f"Очередь {q}: ожидается {n} значений цены и продаж.")
        if any(v is None or v < 0 for v in price) or any(v is None or v < 0 for v in area):
            raise ScenarioError(f"Очередь {q}: цена и продажи не могут быть отрицательными.")
        total = sum(area)
        if abs(total - base["total"]) > max(0.01, base["total"] * 1e-9):
            raise ScenarioError(
                f"Очередь {q}: сумма продаж {total:.2f} м² ≠ {base['total']:.2f} м² в модели — модель ломает проверки площади."
            )
        for i in range(n):
            col = data["cols"][i]
            if abs(price[i] - base["price"][i]) > 1e-9:
                writes.append({"sheet": s["sheet"], "cell": f"{col}{base['rows']['price']}", "value": price[i] * s["price_divisor"]})
            if abs(area[i] - base["area"][i]) > 1e-9:
                writes.append({"sheet": s["sheet"], "cell": f"{col}{base['rows']['area']}", "value": area[i]})
    return writes


def reads() -> list[dict]:
    return [{"key": k, "sheet": o["sheet"], "cell": o["cell"]} for k, o in cell_map()["outputs"].items()]
