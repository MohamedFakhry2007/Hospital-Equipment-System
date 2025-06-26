"""
Test configuration and fixtures for the application.
"""
import pytest

from app import create_app
from app.services.data_service import DataService


@pytest.fixture(scope='session')
def app():
    """Create a Flask app instance for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True # Disable login for most tests unless explicitly enabled
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create a test client using the Flask app fixture."""
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def sample_data():
    """Provide sample data for testing."""
    sample_ppm = {
        "EQUIPMENT": "Test Equipment",
        "MODEL": "Test Model",
        "SERIAL": "TEST_SERIAL",
        "MANUFACTURER": "Test Manufacturer",
        "LOG_NO": "123456",
        "PPM": "Yes"}
    return sample_ppm
