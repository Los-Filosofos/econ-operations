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
            if connection.dialect.name == "sqlite":
                # Batch migrations recreate tables ("move and copy"); with the foreign-key
                # pragma on, dropping a referenced table fails. The pragma is a no-op inside
                # a transaction, so it goes through the DBAPI cursor before Alembic begins
                # (a SQLAlchemy-level execute would autobegin and Alembic would never commit).
                cursor = connection.connection.cursor()
                cursor.execute("PRAGMA foreign_keys=OFF")
                cursor.close()
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
