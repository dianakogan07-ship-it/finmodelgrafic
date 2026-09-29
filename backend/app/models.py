from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)


class Project(Base):
    """Объект на экране «Мониторинг». Дашборд есть только у объектов с моделью."""
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200), default="")
    style: Mapped[str] = mapped_column(String(50), default="")
    angle: Mapped[int] = mapped_column(Integer, default=0)
    tag: Mapped[str] = mapped_column(String(100), default="")
    has_dashboard: Mapped[bool] = mapped_column(Boolean, default=False)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    version: Mapped[str] = mapped_column(String(100), unique=True)  # имя файла в MODEL_DIR без .xlsx
    filename: Mapped[str] = mapped_column(String(300))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    uploaded_by: Mapped[str] = mapped_column(String(100), default="")
    data: Mapped[dict] = mapped_column(JSON)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class Competitor(Base):
    __tablename__ = "competitors"
    __table_args__ = (UniqueConstraint("project_id", "key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    key: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    color: Mapped[str] = mapped_column(String(20))
    enabled_default: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    quarters: Mapped[list["CompetitorQuarter"]] = relationship(cascade="all, delete-orphan", order_by="CompetitorQuarter.id")


class CompetitorQuarter(Base):
    __tablename__ = "competitor_quarters"
    __table_args__ = (UniqueConstraint("competitor_id", "quarter"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id", ondelete="CASCADE"))
    quarter: Mapped[str] = mapped_column(String(20))  # «3кв. 26», как в модели
    price_k_rub_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    pace_k_m2: Mapped[float | None] = mapped_column(Float, nullable=True)


class Scenario(Base):
    """Сценарий пользователя: чипы и значения ползунков по проекту."""
    __tablename__ = "scenarios"
    __table_args__ = (UniqueConstraint("user_id", "project_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
