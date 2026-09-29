"""Управление пользователями: python -m app.cli add-user <login> [--admin]  (пароль спросит)."""
import argparse
import getpass

from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .models import User
from .security import hash_password


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add-user")
    a.add_argument("login")
    a.add_argument("--admin", action="store_true")
    pw = sub.add_parser("set-password")
    pw.add_argument("login")
    args = ap.parse_args()

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.login == args.login))
        password = getpass.getpass("Пароль: ")
        if len(password) < 8:
            raise SystemExit("Пароль короче 8 символов")
        if args.cmd == "add-user":
            if u:
                raise SystemExit("Такой пользователь уже есть")
            db.add(User(login=args.login, password_hash=hash_password(password), is_admin=args.admin))
        else:
            if not u:
                raise SystemExit("Пользователь не найден")
            u.password_hash = hash_password(password)
        db.commit()
    print("Готово")


if __name__ == "__main__":
    main()
