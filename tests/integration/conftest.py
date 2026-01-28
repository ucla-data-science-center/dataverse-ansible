"""
Pytest configuration and fixtures for Dataverse integration tests.

These tests validate migration success and basic functionality after deployment.
Run against a deployed Dataverse instance (not in Docker/Molecule).
"""

import os
import pytest
import requests
from urllib.parse import urljoin


def pytest_addoption(parser):
    """Add command-line options for test configuration."""
    parser.addoption(
        "--dataverse-url",
        action="store",
        default=os.environ.get("DATAVERSE_URL", "http://localhost:8080"),
        help="Base URL of the Dataverse instance to test",
    )
    parser.addoption(
        "--db-host",
        action="store",
        default=os.environ.get("DB_HOST", "localhost"),
        help="PostgreSQL host",
    )
    parser.addoption(
        "--db-port",
        action="store",
        default=os.environ.get("DB_PORT", "5432"),
        help="PostgreSQL port",
    )
    parser.addoption(
        "--db-name",
        action="store",
        default=os.environ.get("DB_NAME", "dvndb"),
        help="PostgreSQL database name",
    )
    parser.addoption(
        "--db-user",
        action="store",
        default=os.environ.get("DB_USER", "postgres"),
        help="PostgreSQL user",
    )
    parser.addoption(
        "--db-password",
        action="store",
        default=os.environ.get("DB_PASSWORD", ""),
        help="PostgreSQL password",
    )
    parser.addoption(
        "--api-token",
        action="store",
        default=os.environ.get("DATAVERSE_API_TOKEN", ""),
        help="Dataverse API token for authenticated requests",
    )


@pytest.fixture(scope="session")
def dataverse_url(request):
    """Get the Dataverse base URL."""
    url = request.config.getoption("--dataverse-url")
    # Ensure URL doesn't have trailing slash
    return url.rstrip("/")


@pytest.fixture(scope="session")
def db_config(request):
    """Get database configuration."""
    return {
        "host": request.config.getoption("--db-host"),
        "port": request.config.getoption("--db-port"),
        "dbname": request.config.getoption("--db-name"),
        "user": request.config.getoption("--db-user"),
        "password": request.config.getoption("--db-password"),
    }


@pytest.fixture(scope="session")
def api_token(request):
    """Get API token for authenticated requests."""
    return request.config.getoption("--api-token")


@pytest.fixture(scope="session")
def api_session(dataverse_url, api_token):
    """Create a requests session with default headers."""
    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    if api_token:
        session.headers["X-Dataverse-key"] = api_token
    return session


@pytest.fixture(scope="session")
def db_connection(db_config):
    """Create database connection (optional - only if psycopg2 available)."""
    try:
        import psycopg2
        conn = psycopg2.connect(**db_config)
        yield conn
        conn.close()
    except ImportError:
        pytest.skip("psycopg2 not installed - skipping database tests")
    except Exception as e:
        pytest.skip(f"Could not connect to database: {e}")


def api_get(session, base_url, endpoint, **kwargs):
    """Helper function to make API GET requests."""
    url = urljoin(base_url + "/", endpoint.lstrip("/"))
    response = session.get(url, **kwargs)
    return response


def api_post(session, base_url, endpoint, **kwargs):
    """Helper function to make API POST requests."""
    url = urljoin(base_url + "/", endpoint.lstrip("/"))
    response = session.post(url, **kwargs)
    return response
