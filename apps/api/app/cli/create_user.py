"""Create the first administrator (or any user) without HTTP; the password is never an argument."""

import argparse
import json
import sys
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.api.users import UserCreate, new_user
from app.core.auth import Role
from app.core.config import Settings
from app.core.database import build_engine

MIN_PASSWORD_LENGTH = 12


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Crea un usuario en la base configurada; aplica antes alembic upgrade head."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", required=True, choices=[role.value for role in Role])
    parser.add_argument("--name", default=None, help="Nombre completo; por defecto el email.")
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="Leer la contraseña de la entrada estándar en vez de pedirla en la terminal.",
    )
    args = parser.parse_args(argv)
    password = sys.stdin.readline().rstrip("\r\n") if args.password_stdin else getpass()
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"La contraseña necesita al menos {MIN_PASSWORD_LENGTH} caracteres.", file=sys.stderr)
        return 2
    try:
        fields = UserCreate(
            email=args.email, full_name=args.name or args.email, role=args.role, password=password
        )
    except ValidationError as error:
        for issue in error.errors():
            print(f"{'.'.join(map(str, issue['loc']))}: {issue['msg']}", file=sys.stderr)
        return 2
    user = new_user(fields.email, fields.full_name, fields.role, fields.password)
    engine = build_engine(Settings().database_url)
    try:
        with Session(engine) as db:
            db.add(user)
            try:
                db.commit()
            except IntegrityError:
                print("El email ya existe.", file=sys.stderr)
                return 2
            db.refresh(user)
            print(json.dumps({"id": user.id, "email": user.email, "role": user.role}))
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
