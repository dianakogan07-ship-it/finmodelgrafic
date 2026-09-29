import logging
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import modelstore
from ..calc import client as calc
from ..db import SessionLocal, get_db
from ..model import scenario
from ..model.parser import ModelError
from ..models import Competitor, Project, Scenario, User
from ..security import admin_user, current_user
from ..seed import replace_competitors

log = logging.getLogger("suz.api")
router = APIRouter(prefix="/api", tags=["projects"])


def _project(db: Session, pid: int) -> Project:
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(404, "Объект не найден")
    return p


def _qkey(label: str):
    m = re.search(r"(\d)\s*кв\.?\s*(\d{2,4})", label)
    return (int(m.group(2)[-2:]), int(m.group(1))) if m else (99, 9)


@router.get("/objects")
def objects(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return [
        {"id": p.id, "name": p.name, "style": p.style, "angle": p.angle, "tag": p.tag, "has_dashboard": p.has_dashboard}
        for p in db.scalars(select(Project).order_by(Project.angle))
    ]


@router.get("/projects/{pid}")
def project(pid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    p = _project(db, pid)
    return {"id": p.id, "name": p.name, "title": p.title or p.name.upper()}


@router.get("/projects/{pid}/model")
def model(pid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    _project(db, pid)
    mv = modelstore.active_version(db, pid)
    if not mv:
        raise HTTPException(404, "Для объекта не загружена модель")
    d = mv.data
    return {
        "model_version": mv.version,
        "filename": mv.filename,
        "uploaded_at": mv.uploaded_at.isoformat(),
        "warnings": mv.warnings,
        "labels": d["labels"],
        "cols": d["cols"],
        "sheet": d["sheet"],
        "queues": {q: {"price": v["price"], "area": v["area"], "total": v["total"], "rows": v["rows"]} for q, v in d["queues"].items()},
        "fr": d["fr"],
        "llcr": d["llcr"],
    }


@router.get("/projects/{pid}/competitors")
def competitors(pid: int, from_: str | None = Query(None, alias="from"), to: str | None = None, db: Session = Depends(get_db), _: User = Depends(current_user)):
    _project(db, pid)
    lo, hi = (_qkey(from_) if from_ else None), (_qkey(to) if to else None)
    out = []
    for c in db.scalars(select(Competitor).where(Competitor.project_id == pid).order_by(Competitor.sort)):
        series = [
            {"quarter": q.quarter, "price": q.price_k_rub_m2, "pace": q.pace_k_m2}
            for q in c.quarters
            if (lo is None or _qkey(q.quarter) >= lo) and (hi is None or _qkey(q.quarter) <= hi)
        ]
        out.append({"id": c.key, "name": c.name, "color": c.color, "enabled_default": c.enabled_default, "series": series})
    return out


class CompetitorIn(BaseModel):
    key: str
    name: str
    color: str
    enabled_default: bool = True
    series: list[dict] = []


@router.put("/projects/{pid}/competitors")
def put_competitors(pid: int, body: list[CompetitorIn], db: Session = Depends(get_db), _: User = Depends(admin_user)):
    replace_competitors(db, _project(db, pid), [c.model_dump() for c in body])
    return {"ok": True, "count": len(body)}


class RecalcIn(BaseModel):
    model_version: str
    queues: dict[str, dict[str, list[float]]]


def _version_data(pid: int, version: str):
    with SessionLocal() as db:
        mv = modelstore.active_version(db, pid)
        return (mv.version, mv.data) if mv else (None, None)


@router.post("/projects/{pid}/recalc")
async def recalc(pid: int, body: RecalcIn, _: User = Depends(current_user)):
    version, data = await run_in_threadpool(_version_data, pid, body.model_version)
    if not version:
        raise HTTPException(404, "Для объекта не загружена модель")
    if version != body.model_version:
        raise HTTPException(409, "Модель обновилась — перезагрузите страницу")
    try:
        writes = scenario.to_writes(data, body.queues)
    except scenario.ScenarioError as e:
        raise HTTPException(422, str(e))
    if not writes:
        return {"fr": data["fr"], "llcr": data["llcr"], "calc_ms": 0}
    try:
        res = await calc.recalc(version, writes, scenario.reads())
    except calc.CalcUnavailable as e:
        log.error("recalc failed: %s", e)
        raise HTTPException(503, "Сервис пересчёта недоступен, попробуйте позже")
    v = res["values"]
    if v.get("fr") is None or v.get("llcr") is None:
        raise HTTPException(500, "Модель вернула ошибку при пересчёте")
    return {"fr": v["fr"], "llcr": v["llcr"], "calc_ms": res.get("calc_ms", 0)}


@router.post("/projects/{pid}/model")
async def upload_model(pid: int, file: UploadFile = File(...), user: User = Depends(admin_user)):
    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(422, "Нужен файл .xlsx или .xlsm")
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        while chunk := await file.read(1 << 20):
            tmp.write(chunk)
    tmp_path = Path(tmp.name)

    def _import():
        with SessionLocal() as db:
            p = _project(db, pid)
            if not p.has_dashboard:
                raise HTTPException(422, "У объекта нет дашборда")
            return modelstore.import_file(db, p, tmp_path, file.filename, user.login)

    try:
        mv = await run_in_threadpool(_import)
    except ModelError as e:
        raise HTTPException(422, str(e))
    finally:
        tmp_path.unlink(missing_ok=True)

    engine_warnings = await modelstore.check_with_engine(mv)

    def _activate():
        with SessionLocal() as db:
            m = db.merge(mv)
            m.warnings = list(m.warnings) + engine_warnings
            modelstore.activate(db, m)
            return m.version, m.warnings

    version, warnings = await run_in_threadpool(_activate)
    return {"model_version": version, "warnings": warnings}


class ScenarioIn(BaseModel):
    state: dict


@router.get("/projects/{pid}/scenario")
def get_scenario(pid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    s = db.scalar(select(Scenario).where(Scenario.user_id == user.id, Scenario.project_id == pid))
    return s.state if s else {}


@router.put("/projects/{pid}/scenario")
def put_scenario(pid: int, body: ScenarioIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _project(db, pid)
    s = db.scalar(select(Scenario).where(Scenario.user_id == user.id, Scenario.project_id == pid))
    if not s:
        s = Scenario(user_id=user.id, project_id=pid, state={})
        db.add(s)
    s.state = body.state
    db.commit()
    return {"ok": True}
