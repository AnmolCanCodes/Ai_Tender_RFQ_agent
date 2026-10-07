import os
from typing import Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings


db_url: str = settings.DATABASE_URL
if db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    db_url,
    echo=(settings.ENVIRONMENT == "development"),
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def initialize_database(target_engine: Optional[Engine] = None) -> None:
    """Create the schema if it is missing so auth queries do not fail on a fresh DB."""
    bound_engine = target_engine or engine

    try:
        import app.models.organization  # noqa: F401
        import app.models.user  # noqa: F401
        import app.models.tender  # noqa: F401
        import app.models.document  # noqa: F401
        import app.models.chunk  # noqa: F401
        import app.models.requirement  # noqa: F401
        import app.models.company_profile  # noqa: F401
        import app.models.audit_log  # noqa: F401
    except Exception:
        pass

    if bound_engine.dialect.name == "postgresql":
        try:
            with bound_engine.begin() as connection:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass

    existing_tables = set(inspect(bound_engine).get_table_names())
    missing_tables = [table for table in Base.metadata.sorted_tables if table.name not in existing_tables]
    if missing_tables:
        Base.metadata.create_all(bind=bound_engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


        