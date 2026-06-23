from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from review_app.db_postgres import ReviewDatabase


@pytest.fixture
def cases() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "review_case_id": [f"R{i:03d}" for i in range(1, 7)],
            "image_filename": [f"R{i:03d}.png" for i in range(1, 7)],
        }
    )


@pytest.fixture
def db(cases: pd.DataFrame) -> ReviewDatabase:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database = ReviewDatabase("sqlite+pysqlite:///:memory:", engine=engine)
    database.create_schema()
    database.seed_cases(cases)
    database.sync_reviewers(
        {
            "reviewer_a": ("unused", "primary"),
            "reviewer_b": ("unused", "primary"),
            "reviewer_c": ("unused", "adjudicator"),
            "admin": ("unused", "admin"),
        }
    )
    return database

