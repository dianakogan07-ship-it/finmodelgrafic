"""Создание таблиц и начальных данных при старте. Идемпотентно."""
import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import settings
from .model.parser import ModelError
from .models import Competitor, CompetitorQuarter, ModelVersion, Project, User
from .security import hash_password

log = logging.getLogger("suz.seed")


def seed(db: Session) -> ModelVersion | None:
    """Возвращает версию модели, импортированную из SEED_MODEL (её нужно сверить движком)."""
    if settings.ADMIN_LOGIN and settings.ADMIN_PASSWORD:
        if not db.scalar(select(User).where(User.login == settings.ADMIN_LOGIN)):
            db.add(User(login=settings.ADMIN_LOGIN, password_hash=hash_password(settings.ADMIN_PASSWORD), is_admin=True))
            log.info("создан администратор %s", settings.ADMIN_LOGIN)

    objects = json.loads((settings.SEEDS_DIR / "objects.json").read_text(encoding="utf-8"))
    for o in objects:
        if not db.scalar(select(Project).where(Project.slug == o["slug"])):
            db.add(Project(**o))
    db.commit()

    comp = json.loads((settings.SEEDS_DIR / "competitors.json").read_text(encoding="utf-8"))
    project = db.scalar(select(Project).where(Project.slug == comp["project"]))
    if project and not db.scalar(select(Competitor).where(Competitor.project_id == project.id)):
        replace_competitors(db, project, comp["competitors"])

    imported = None
    for p in db.scalars(select(Project).where(Project.has_dashboard)):
        has = db.scalar(select(ModelVersion.id).where(ModelVersion.project_id == p.id))
        if not has and settings.SEED_MODEL.exists():
            from . import modelstore
            try:
                imported = modelstore.import_file(db, p, settings.SEED_MODEL, settings.SEED_MODEL.name, "seed")
                modelstore.activate(db, imported)
                log.info("модель %s импортирована как %s", settings.SEED_MODEL, imported.version)
            except ModelError as e:
                log.error("модель %s не прошла проверку: %s", settings.SEED_MODEL, e)
            break  # файл-сид один — только для первого проекта с дашбордом
    return imported


def replace_competitors(db: Session, project: Project, items: list[dict]):
    for c in db.scalars(select(Competitor).where(Competitor.project_id == project.id)):
        db.delete(c)
    db.flush()
    for i, c in enumerate(items):
        comp = Competitor(
            project_id=project.id, key=c["key"], name=c["name"], color=c["color"],
            enabled_default=c.get("enabled_default", True), sort=i,
        )
        comp.quarters = [
            CompetitorQuarter(quarter=s["quarter"], price_k_rub_m2=s.get("price"), pace_k_m2=s.get("pace"))
            for s in c.get("series", [])
        ]
        db.add(comp)
    db.commit()
