"""Версии модели: импорт xlsx, валидация, сверка пересчёта с Excel, активация."""
import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from . import settings
from .calc import client as calc
from .model import scenario
from .model.parser import parse
from .models import ModelVersion, Project

log = logging.getLogger("suz.model")


def _version_name(project: Project) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return re.sub(r"[^a-z0-9-]", "-", f"{project.slug}-{ts}".lower())


def import_file(db: Session, project: Project, src: Path, filename: str, user: str) -> ModelVersion:
    """Парсит файл (ModelError при ошибке), кладёт в MODEL_DIR, создаёт неактивную версию."""
    data = parse(src)
    warnings = data.pop("warnings")
    settings.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    name = _version_name(project)
    shutil.copyfile(src, settings.MODEL_DIR / f"{name}.xlsx")
    mv = ModelVersion(project_id=project.id, version=name, filename=filename, uploaded_by=user, data=data, warnings=warnings)
    db.add(mv)
    db.commit()
    return mv


async def check_with_engine(mv: ModelVersion) -> list[str]:
    """Загрузить версию в calc-воркер и сверить базовый пересчёт с кэшем Excel."""
    try:
        res = await calc.preload(mv.version, scenario.reads())
    except calc.CalcUnavailable as e:
        return [f"Пересчёт недоступен: {e}. ФР и LLCR будут показаны по данным файла, без пересчёта."]
    v = res["values"]
    out = []
    if v.get("fr") is None or abs(v["fr"] - mv.data["fr"]) > settings.CHECK_FR_TOL:
        out.append(f"Движок пересчёта даёт ФР {v.get('fr')} вместо {mv.data['fr']:.0f} из файла — пересчёт может быть неточным.")
    if v.get("llcr") is None or abs(v["llcr"] - mv.data["llcr"]) > settings.CHECK_LLCR_TOL:
        out.append(f"Движок пересчёта даёт LLCR {v.get('llcr')} вместо {mv.data['llcr']:.4f} из файла — пересчёт может быть неточным.")
    return out


def activate(db: Session, mv: ModelVersion):
    db.execute(update(ModelVersion).where(ModelVersion.project_id == mv.project_id).values(is_active=False))
    mv.is_active = True
    db.commit()


def active_version(db: Session, project_id: int) -> ModelVersion | None:
    return db.scalar(select(ModelVersion).where(ModelVersion.project_id == project_id, ModelVersion.is_active))
