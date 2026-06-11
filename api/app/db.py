from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def get_session() -> Generator[Session]:
    factory = sessionmaker(bind=get_engine())
    session = factory()
    try:
        yield session
    finally:
        session.close()


def check_postgres() -> bool:
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
