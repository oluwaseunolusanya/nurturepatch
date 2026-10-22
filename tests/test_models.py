"""Test database model relationships and tenant isolation."""

import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.db.base import Base
from app.db.models import Business, Child, Contract, Family


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


def test_business_can_own_family_child_and_contract(session):
    """Persist related records belonging to the same business."""
    business = Business(name="Example Childminding")
    family = Family(name="Example Family", business=business)
    child = Child(name="Example Child", business=business, family=family)
    contract = Contract(
        business=business,
        family=family,
        child=child,
        effective_from=date(2026, 9, 1),
        effective_to=None,
        rate_amount=Decimal("7.50"),
        rate_unit="hour",
    )

    session.add(contract)
    session.commit()

    assert family.business_id == business.id
    assert child.family_id == family.id
    assert contract.rate_amount == Decimal("7.50")


def test_child_cannot_reference_family_from_another_business(session):
    """Reject a child whose family belongs to another business."""
    first_business = Business(name="First Business")
    second_business = Business(name="Second Business")
    first_family = Family(name="First Family", business=first_business)

    session.add_all([first_family, second_business])
    session.commit()

    child = Child(
        name="Example Child",
        business=second_business,
        family=first_family,
    )
    session.add(child)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()


def test_contract_cannot_reference_child_from_another_business(session):
    """Reject a contract whose child belongs to another business."""
    first_business = Business(name="First Business")
    second_business = Business(name="Second Business")
    first_family = Family(name="First Family", business=first_business)
    first_child = Child(
        name="First Child",
        business=first_business,
        family=first_family,
    )
    second_family = Family(name="Second Family", business=second_business)

    session.add_all([first_child, second_family])
    session.commit()

    contract = Contract(
        business=second_business,
        family=second_family,
        child=first_child,
        effective_from=date(2026, 9, 1),
        rate_amount=Decimal("7.50"),
        rate_unit="hour",
    )
    session.add(contract)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()


def test_contract_rejects_end_date_before_start_date(session):
    """Reject a contract with an invalid effective date range."""
    business = Business(name="Example Business")
    family = Family(name="Example Family", business=business)
    child = Child(name="Example Child", business=business, family=family)
    contract = Contract(
        business=business,
        family=family,
        child=child,
        effective_from=date(2026, 10, 1),
        effective_to=date(2026, 9, 30),
        rate_amount=Decimal("7.50"),
        rate_unit="hour",
    )

    session.add(contract)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
