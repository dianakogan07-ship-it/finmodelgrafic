import asyncio
import logging

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool

from . import modelstore
from .api import auth, projects
from .db import Base, SessionLocal, engine
from .seed import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("suz")

app = FastAPI(title="СУЗ API")
app.include_router(auth.router)
app.include_router(projects.router)


def _startup():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        imported = seed(db)
        active = []
        from sqlalchemy import select
        from .models import ModelVersion
        for mv in db.scalars(select(ModelVersion).where(ModelVersion.is_active)):
            active.append(mv)
        return imported, active


async def _warmup(imported, active):
    """Прогреть calc-воркер активными версиями; для импортированной — записать итог сверки."""
    for mv in active:
        warnings = await modelstore.check_with_engine(mv)
        if imported and mv.id == imported.id and warnings:
            def _save():
                with SessionLocal() as db:
                    m = db.merge(mv)
                    m.warnings = list(m.warnings) + warnings
                    db.commit()
            await run_in_threadpool(_save)
        for w in warnings:
            log.warning("%s: %s", mv.version, w)


@app.on_event("startup")
async def startup():
    imported, active = await run_in_threadpool(_startup)
    asyncio.create_task(_warmup(imported, active))


@app.get("/api/health")
def health():
    return {"ok": True}
