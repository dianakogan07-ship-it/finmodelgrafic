"""Calc-воркер: держит книги открытыми и пересчитывает сценарии.

POST /recalc  {model_version, writes:[{sheet,cell,value}], reads:[{key,sheet,cell}]}
              → {values:{key:value}, calc_ms}
Входы пишутся в книгу, после расчёта откатываются — следующий запрос видит базовую модель.
Книга однопоточная: запросы к одной версии идут по очереди (lock).
"""
import logging
import os
import threading
import time
from collections import OrderedDict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import engine

MODEL_DIR = os.environ.get("MODEL_DIR", "/data/models")
MAX_BOOKS = int(os.environ.get("CALC_MAX_BOOKS", "1"))

log = logging.getLogger("calc")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="SUZ calc-worker")


class Book:
    def __init__(self, version, path):
        t = time.time()
        self.version = version
        self.wb, self.fixed, _ = engine.load(path)
        engine.calculate(self.wb)
        self.lock = threading.Lock()
        self.load_s = round(time.time() - t, 1)
        log.info("loaded %s: %s formulas patched, %.1f s", version, self.fixed, self.load_s)


_books: "OrderedDict[str, Book]" = OrderedDict()
_books_lock = threading.Lock()
_loading: dict[str, threading.Lock] = {}


def book(version: str) -> Book:
    if "/" in version or "\\" in version or version.startswith("."):
        raise HTTPException(400, "bad model_version")
    with _books_lock:
        if version in _books:
            _books.move_to_end(version)
            return _books[version]
        vlock = _loading.setdefault(version, threading.Lock())
    with vlock:  # одна загрузка на версию, даже при параллельных запросах
        with _books_lock:
            if version in _books:
                return _books[version]
        path = os.path.join(MODEL_DIR, f"{version}.xlsx")
        if not os.path.exists(path):
            raise HTTPException(404, f"model {version} not found")
        b = Book(version, path)
        with _books_lock:
            _books[version] = b
            while len(_books) > MAX_BOOKS:
                _books.popitem(last=False)
        return b


class Write(BaseModel):
    sheet: str
    cell: str
    value: float


class Read(BaseModel):
    key: str
    sheet: str
    cell: str


class RecalcIn(BaseModel):
    model_version: str
    writes: list[Write] = []
    reads: list[Read]


class LoadIn(BaseModel):
    model_version: str
    reads: list[Read] = []


def _num(v):
    return v if isinstance(v, (int, float)) else None


@app.get("/health")
def health():
    return {"ok": True, "loaded": list(_books)}


@app.post("/load")
def load(body: LoadIn):
    """Загрузить версию заранее; вернуть значения после пересчёта Aspose (для сверки с кэшем Excel)."""
    b = book(body.model_version)
    with b.lock:
        values = {r.key: _num(engine.get(b.wb, r.sheet, r.cell)) for r in body.reads}
    return {"values": values, "load_s": b.load_s, "patched": b.fixed}


@app.post("/recalc")
def recalc(body: RecalcIn):
    b = book(body.model_version)
    with b.lock:
        orig = []
        try:
            for w in body.writes:
                orig.append((w.sheet, w.cell, engine.get(b.wb, w.sheet, w.cell)))
                engine.put(b.wb, w.sheet, w.cell, w.value)
            t = time.time()
            engine.calculate(b.wb)
            ms = int((time.time() - t) * 1000)
            values = {r.key: _num(engine.get(b.wb, r.sheet, r.cell)) for r in body.reads}
        finally:
            # пересчёт после отката не нужен: спайк показал, что результат не зависит от
            # предыдущего состояния итераций (tests/golden, «повтор» и «откат»)
            for sheet, cell, v in orig:
                engine.put(b.wb, sheet, cell, v)
    log.info("recalc %s: %d writes, %d ms", body.model_version, len(body.writes), ms)
    return {"values": values, "calc_ms": ms}
