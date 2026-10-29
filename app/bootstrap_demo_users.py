import os

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.schemas import UserRegister
from app.auth.security import hash_password
from app.models import User, UserRole


def populate_demo_users(db: Session) -> int:

    enabled = os.getenv("DEMO_USERS_ENABLED", "false").strip().lower()
    if enabled not in {"true", "false"}:
        raise RuntimeError("DEMO_USERS_ENABLED deve ser true ou false.")
    if enabled == "false":
        return 0

    definitions = (
        (UserRole.ADMIN, "DEMO_ADMIN", "Admin Demonstracao"),
        (UserRole.STAFF, "DEMO_STAFF", "Staff Demonstracao"),
        (UserRole.CUSTOMER, "DEMO_CUSTOMER", "Cliente Demonstracao"),
    )
    validated = []
    emails = set()
    for role, prefix, name in definitions:
        try:
            data = UserRegister(
                name=name,
                email=os.getenv(f"{prefix}_EMAIL", ""),
                password=os.getenv(f"{prefix}_PASSWORD", ""),
            )
        except ValidationError:
            raise RuntimeError(
                f"Configure {prefix}_EMAIL e {prefix}_PASSWORD com dados validos "
                "e senha de 12 a 128 caracteres."
            ) from None
        email = str(data.email)
        if email in emails:
            raise RuntimeError("Os emails das tres contas de demonstracao devem ser diferentes.")
        emails.add(email)
        validated.append((role, data))

    missing = []
    for role, data in validated:
        existing = db.scalar(select(User).where(User.email == str(data.email)))
        if existing is not None:
            if existing.role != role or not existing.is_active:
                raise RuntimeError(
                    "Uma conta de demonstracao ja existe com perfil diferente "
                    "ou esta inativa. Use um email exclusivo para esse perfil."
                )
        else:
            missing.append((role, data))

    users = [
        User(
            name=data.name,
            email=str(data.email),
            password_hash=hash_password(data.password.get_secret_value()),
            role=role,
            is_active=True,
        )
        for role, data in missing
    ]
    if not users:
        return 0
    db.add_all(users)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise RuntimeError(
            "Conflito ao criar as contas de demonstracao. Confira os emails configurados."
        ) from None
    return len(users)
