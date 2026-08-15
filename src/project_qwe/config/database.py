from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from project_qwe.config.settings import settings

url_obj = make_url(settings.DATABASE_URL)
if url_obj.database and url_obj.drivername.startswith("sqlite"):
    db_file = Path(url_obj.database)
    if db_file.parent and str(db_file.parent) != ".":
        db_file.parent.mkdir(parents=True, exist_ok=True)

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it closes after request completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
