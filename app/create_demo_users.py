"""Explicit, interactive creation of local demo users: python -m app.create_demo_users."""

import argparse
import getpass
import warnings
from pathlib import Path


def _secure_password(prompt: str) -> str:
    # getpass falls back to echoed input without a terminal; refuse that fallback.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass(prompt)


def create_demo_users(db, *, input_fn=None, password_fn=None):
    from pydantic import ValidationError
    from sqlalchemy import select

    from app.auth.schemas import UserRegister
    from app.auth.security import hash_password
    from app.models import User, UserRole

    input_fn = input_fn or input
    password_fn = password_fn or _secure_password
    users = []
    emails = set()
    for role in UserRole:
        name = input_fn(f"Nome do usuário {role.value}: ")
        email = input_fn(f"Email do usuário {role.value}: ")
        password = password_fn(f"Senha do usuário {role.value} (12 a 128 caracteres): ")
        confirmation = password_fn("Confirme a senha: ")
        if password != confirmation:
            raise ValueError("As senhas não conferem. Nenhum usuário foi criado.")
        try:
            data = UserRegister(name=name, email=email, password=password)
        except ValidationError as error:
            fields = ", ".join(str(item["loc"][0]) for item in error.errors())
            raise ValueError(f"Dados inválidos ({fields}). Nenhum usuário foi criado.") from None
        normalized_email = str(data.email)
        if normalized_email in emails or db.scalar(select(User.id).where(User.email == normalized_email)) is not None:
            raise ValueError("Email já cadastrado ou repetido. Nenhum usuário foi criado.")
        emails.add(normalized_email)
        users.append(User(
            name=data.name, email=normalized_email,
            password_hash=hash_password(data.password.get_secret_value()), role=role,
        ))
    # Commit all three together, only after every input has passed validation.
    db.add_all(users)
    db.commit()
    return users


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Criar três usuários locais de demonstração, com senhas privadas.")
    parser.add_argument("--env-file", type=Path, help="Arquivo .env opcional; não substitui variáveis já definidas.")
    args = parser.parse_args(argv)
    if args.env_file:
        if not args.env_file.is_file():
            parser.error("Arquivo de ambiente não encontrado.")
        from dotenv import load_dotenv

        load_dotenv(args.env_file, override=False)

    # Import the database only after loading DATABASE_URL from the optional file.
    from sqlalchemy.exc import IntegrityError

    from app.database import SessionLocal, engine
    from app.models import User

    User.__table__.create(bind=engine, checkfirst=True)
    with SessionLocal() as db:
        try:
            create_demo_users(db)
        except (ValueError, EOFError, KeyboardInterrupt, getpass.GetPassWarning):
            db.rollback()
            print("Criação cancelada ou dados inválidos. Nenhum usuário foi criado; use um terminal com entrada segura.")
            return 1
        except IntegrityError:
            db.rollback()
            print("Conflito de email. Nenhum usuário foi criado.")
            return 1
    print("Usuários admin, staff e customer criados. Nenhuma senha foi exibida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
