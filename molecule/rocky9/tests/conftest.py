# molecule/rocky9/tests/conftest.py
"""
Pytest configuration for testinfra tests.
"""
import pytest


@pytest.fixture(scope='module')
def host(request):
    """
    Provide a testinfra host fixture that connects to the molecule container.
    """
    import testinfra
    # Connect to the docker container named 'rocky9'
    return testinfra.get_host('docker://rocky9')
