"""Register table metadata for explicit Alembic migrations, never startup DDL."""

from sqlmodel import SQLModel

SQLModel.metadata.naming_convention = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = SQLModel.metadata

# Register tables after the naming convention, without importing service code.
from app.models.operations import Movement, OperationEvent, SourceSnapshot  # noqa: E402, F401
from app.models.users import User  # noqa: E402, F401
