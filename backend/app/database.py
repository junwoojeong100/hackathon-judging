import os
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings


def _ensure_sqlite_dir(database_url: str) -> None:
    """Make sure the parent directory of a SQLite file exists."""
    if not database_url.startswith("sqlite"):
        return
    # sqlite:///./data/x.db  -> ./data/x.db ; sqlite:////app/data/x.db -> /app/data/x.db
    path = database_url.split("sqlite:///", 1)[-1]
    if path and path != ":memory:":
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
