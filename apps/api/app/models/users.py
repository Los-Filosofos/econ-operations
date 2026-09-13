"""Application users; roles are validated in app.core.auth, never trusted from the browser."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=255, unique=True)
    full_name: str = Field(max_length=255)
    role: str = Field(max_length=32)
    password_hash: str = Field(max_length=255, repr=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class UserRecord(BaseModel):
    """Public projection of a user; the password hash never leaves the server."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
