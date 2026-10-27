from datetime import datetime, timezone
from typing import Annotated

from pydantic import (
    BaseModel, ConfigDict, EmailStr, Field, SecretStr, StringConstraints, field_validator,
)

from app.models import UserRole


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    email: EmailStr = Field(max_length=254)
    password: SecretStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, value):
        # Never strip, truncate, normalize or coerce a password.
        if not isinstance(value, str) or not 1 <= len(value) <= 128:
            raise ValueError("A senha deve conter entre 1 e 128 caracteres.")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("A senha deve conter caracteres Unicode válidos.") from None
        return value


class UserRegister(Credentials):
    name: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=100)]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("O nome deve conter caracteres Unicode válidos.") from None
        return value

    @field_validator("password")
    @classmethod
    def validate_new_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if len(password) < 12 or not password.strip():
            raise ValueError("A senha deve conter entre 12 e 128 caracteres e não pode ser só espaços.")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def utc_created_at(cls, value: datetime) -> datetime:
        # SQLite stores naive datetimes; creation timestamps are always UTC.
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class CSRFResponse(BaseModel):
    csrf_token: str
