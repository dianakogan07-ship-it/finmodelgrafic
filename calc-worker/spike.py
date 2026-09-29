"""Спайк: сверка пересчёта Aspose с Excel и эталонные сценарии ТЗ (раздел 9).

python spike.py path/to/model.xlsx
"""
import sys
import time

from aspose.cells import CellsHelper as H

import engine

P, D = "Продажи", "Dashboard_2"


def cols(a, b):
    return [H.column_index_to_name(c) for c in range(H.column_name_to_index(a), H.column_name_to_index(b) + 1)]


def main(path):
    t = time.time()
    wb, fixed, cache = engine.load(path)
    print(f"load {time.time() - t:.1f} s, formulas patched: {fixed}")
    g = lambda s, a: engine.get(wb, s, a)

    t = time.time()
    engine.calculate(wb)
    print(f"base calc {time.time() - t:.1f} s")
    errors = diffs = 0
    for i in range(len(wb.worksheets)):
        ws = wb.worksheets[i]
        for c in ws.cells:
            if not c.is_formula:
                continue
            a, b = cache[(ws.name, c.name)], c.value
            if isinstance(b, str) and b.startswith("#") and not (isinstance(a, str) and a.startswith("#")):
                errors += 1
            elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) > 1e-6 * max(1, abs(a)):
                diffs += 1
    print(f"vs Excel cache: new errors {errors}, numeric diffs >1e-6 {diffs}")
    base = g(D, "G69"), g(D, "E81")
    print(f"base G69 {base[0] / 1e9:.4f} bn, E81 {base[1]:.4f}")

    q1 = cols("U", "AW")
    tail_cols = cols("X", "AN")
    W12, W15, X12 = g(P, "W12"), g(P, "W15"), g(P, "X12")

    def tail(delta):
        s = sum(g(P, c + "15") or 0 for c in tail_cols)
        k = (s - delta) / s
        d = {"W15": W15 + delta}
        d.update({c + "15": g(P, c + "15") * k for c in tail_cols if g(P, c + "15")})
        return d

    def curve(new_w12):
        k = new_w12 / W12
        return {c + "12": g(P, c + "12") * k for c in cols("W", "AN")}

    s5 = tail(500)
    s5["W12"] = W12 + 30000
    scenarios = [
        ("1. W12 +10 000", {"W12": W12 + 10000}),
        ("2. W12 −10 000", {"W12": W12 - 10000}),
        ("3. W15 +100, хвост X:AN пропорц.", tail(100)),
        ("4. X12 +10 000", {"X12": X12 + 10000}),
        ("5. W12 +30 000, W15 +500 (хвост пропорц.)", s5),
        ("6. Ползунок цены 573→603: W12:AN12 ×k", curve(603000)),
        ("7. Ползунок темпа 1 900→2 400: W15, хвост пропорц.", tail(500)),
    ]
    rows = []
    for name, ch in scenarios:
        orig = {a: g(P, a) for a in ch}
        for a, v in ch.items():
            engine.put(wb, P, a, v)
        t = time.time()
        engine.calculate(wb)
        dt = time.time() - t
        fr, ll = g(D, "G69"), g(D, "E81")
        area = sum(g(P, c + "15") or 0 for c in q1)
        for a, v in orig.items():
            engine.put(wb, P, a, v)
        rows.append((name, fr, ll, area, dt))
        print(f"{name}: G69 {fr / 1e9:.4f} ({(fr - base[0]) / 1e9:+.4f}), E81 {ll:.4f} ({ll - base[1]:+.5f}), "
              f"area q1 {area:.2f}, {dt:.1f} s")
    engine.calculate(wb)
    print("revert equals base:", (g(D, "G69"), g(D, "E81")) == base)
    return rows


if __name__ == "__main__":
    main(sys.argv[1])
