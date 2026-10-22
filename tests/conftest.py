"""Shared PostgreSQL fixtures for tests."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.db.base import Base


@pytest.fixture
def session():
    """Provide an isolated session in the dedicated PostgreSQL test database."""
    database_url = os.environ.get("TEST_DATABASE_URL")

    if not database_url:
        pytest.fail(
            "TEST_DATABASE_URL must point to the dedicated test PostgreSQL database."
        )

    try:
        url = make_url(database_url)
    except (ValueError, TypeError):
        pytest.fail("TEST_DATABASE_URL must be a valid SQLAlchemy database URL.")

    if url.get_backend_name() != "postgresql":
        pytest.fail("Model tests require PostgreSQL; SQLite is not supported.")

    if url.database != "nurturepatch_test":
        pytest.fail(
            "Model tests may only run against the 'nurturepatch_test' database."
        )

    admin_engine = create_engine(url)
    schema_name = f"test_{uuid4().hex}"
    test_engine = None

    try:
        with admin_engine.connect() as connection:
            database_name = connection.exec_driver_sql(
                "SELECT current_database()"
            ).scalar_one()

        if database_name != "nurturepatch_test":
            pytest.fail("Connected database is not the dedicated test database.")

        with admin_engine.begin() as connection:
            connection.execute(CreateSchema(schema_name))

        test_engine = create_engine(
            url,
            connect_args={"options": f"-csearch_path={schema_name}"},
        )
        Base.metadata.create_all(test_engine)

        with Session(test_engine) as database_session:
            yield database_session
            database_session.rollback()
    finally:
        if test_engine is not None:
            test_engine.dispose()

        try:
            with admin_engine.begin() as connection:
                connection.execute(DropSchema(schema_name, cascade=True))
        finally:
            admin_engine.dispose()
