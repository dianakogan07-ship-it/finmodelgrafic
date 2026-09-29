from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import settings
from .db import get_db
from .models import User

_bearer = HTTPBearer(auto_error=False)


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def check_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except ValueError:
        return False


def make_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_TTL_HOURS)
    return jwt.encode({"sub": str(user.id), "exp": exp}, settings.JWT_SECRET, algorithm="HS256")


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)) -> User:
    if not cred:
        raise HTTPException(401, "Нужен вход")
    try:
        uid = int(jwt.decode(cred.credentials, settings.JWT_SECRET, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Сессия истекла, войдите снова")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(401, "Пользователь не найден")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Только для администратора")
    return user
