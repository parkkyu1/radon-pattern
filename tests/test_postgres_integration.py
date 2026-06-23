from __future__ import annotations

import os

import pytest

from review_app.db_postgres import ReviewDatabase


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="Set TEST_DATABASE_URL to run the PostgreSQL integration test.",
)
def test_postgres_connection_and_schema() -> None:
    db = ReviewDatabase(os.environ["TEST_DATABASE_URL"])
    db.create_schema()
    assert db.engine.dialect.name == "postgresql"

