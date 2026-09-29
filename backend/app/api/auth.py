from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import check_password, current_user, make_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    login: str
    password: str


def _user(u: User):
    return {"login": u.login, "is_admin": u.is_admin}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.login == body.login.strip()))
    if not u or not check_password(body.password, u.password_hash):
        raise HTTPException(401, "Неверный логин или пароль")
    return {"token": make_token(u), "user": _user(u)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return _user(user)
