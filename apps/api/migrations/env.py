"""Alembic environment: explicit migrations only, never DDL on server startup."""

from logging.config import fileConfig

from alembic import context

from app.core.config import Settings
from app.core.database import build_engine, normalize_database_url
from app.models import metadata

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

if context.is_offline_mode():
    context.configure(
        url=normalize_database_url(Settings().database_url),
        target_metadata=metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = build_engine(Settings().database_url)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=metadata,
                compare_type=True,
                render_as_batch=connection.dialect.name == "sqlite",
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
