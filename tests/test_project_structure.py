"""Smoke tests for the initial application package structure."""

import app
import app.schemas
import app.services


def test_application_packages_can_be_imported():
    """Verify that the application packages can be imported."""
    assert app is not None
    assert app.schemas is not None
    assert app.services is not None
