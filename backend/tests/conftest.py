import os
import tempfile

# Isolate tests onto a throwaway SQLite DB / data dir BEFORE app modules import.
_TEST_DIR = tempfile.mkdtemp(prefix="hj_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_TEST_DIR, 'test.db')}"
os.environ["DATA_DIR"] = os.path.join(_TEST_DIR, "data")

import pytest

from app import models
from app.database import Base, SessionLocal, engine
from app.rubric_defaults import DEFAULT_CRITERIA


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    for c in DEFAULT_CRITERIA:
        db.add(models.Criterion(**c))
    db.commit()
    db.close()
    yield
