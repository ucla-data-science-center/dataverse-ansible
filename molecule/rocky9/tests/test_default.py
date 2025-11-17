# molecule/rocky9/tests/test_default.py
"""
Testinfra tests for Dataverse Ansible role.

Tests verify that all core services are running and listening on expected ports.
Issue #17: Basic port and service tests
"""

# Service Tests
def test_payara_service_running_and_enabled(host):
    """Test Payara application server is running and enabled."""
    service = host.service("payara")
    assert service.is_running
    assert service.is_enabled


def test_postgresql_service_running_and_enabled(host):
    """Test PostgreSQL database is running and enabled."""
    service = host.service("postgresql-16")
    assert service.is_running
    assert service.is_enabled


def test_solr_service_running_and_enabled(host):
    """Test Apache Solr search service is running and enabled."""
    service = host.service("solr")
    assert service.is_running
    assert service.is_enabled


def test_apache_service_running_and_enabled(host):
    """Test Apache HTTP server is running and enabled."""
    service = host.service("httpd")
    assert service.is_running
    assert service.is_enabled


# Port Tests
def test_port_8080_listening(host):
    """Test Payara is listening on port 8080."""
    # Payara listens on 127.0.0.1:8080 (localhost) by default
    # In Docker testing with port mapping, it may listen on 0.0.0.0:8080
    socket = host.socket("tcp://127.0.0.1:8080")
    assert socket.is_listening


def test_port_5432_listening(host):
    """Test PostgreSQL is listening on port 5432."""
    socket = host.socket("tcp://127.0.0.1:5432")
    assert socket.is_listening


def test_port_8983_listening(host):
    """Test Solr is listening on port 8983."""
    socket = host.socket("tcp://127.0.0.1:8983")
    assert socket.is_listening


def test_port_80_listening(host):
    """Test Apache is listening on port 80."""
    socket = host.socket("tcp://0.0.0.0:80")
    assert socket.is_listening


# Application Health Tests
def test_dataverse_api_responding(host):
    """Test Dataverse API returns version information."""
    cmd = host.run("curl -s http://localhost:8080/api/info/version")
    assert cmd.rc == 0
    assert "version" in cmd.stdout
    assert "6.8" in cmd.stdout


def test_solr_core_exists(host):
    """Test Solr collection1 core exists."""
    cmd = host.run("ls /usr/local/solr/server/solr/collection1")
    assert cmd.rc == 0


def test_postgresql_database_exists(host):
    """Test Dataverse database exists."""
    cmd = host.run("psql -U dvnuser -d dvndb -c '\\dt' -A -t")
    assert cmd.rc == 0
    assert "authenticateduser" in cmd.stdout


def test_apache_proxy_working(host):
    """Test Apache is proxying to Payara."""
    cmd = host.run("curl -s http://localhost/api/info/version")
    assert cmd.rc == 0
    assert "version" in cmd.stdout


# Blocked Endpoints Tests (Issue #8)
def test_builtin_users_blocked_via_proxy(host):
    """Test builtin-users endpoint is blocked via Apache proxy."""
    cmd = host.run("curl -s -o /dev/null -w '%{http_code}' http://localhost/api/builtin-users")
    assert cmd.rc == 0
    # Should return 302 (redirect to /) when blocked
    assert "302" in cmd.stdout


def test_builtin_users_accessible_direct(host):
    """Test builtin-users endpoint is accessible when bypassing proxy."""
    cmd = host.run("curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/api/builtin-users")
    assert cmd.rc == 0
    # Should return 405 (Method Not Allowed) - endpoint exists but requires POST
    assert "405" in cmd.stdout


def test_admin_endpoint_blocked_via_proxy(host):
    """Test admin endpoint is blocked via Apache proxy."""
    cmd = host.run("curl -s -o /dev/null -w '%{http_code}' http://localhost/api/admin")
    assert cmd.rc == 0
    # Should return 302 (redirect) when blocked
    assert "302" in cmd.stdout


def test_destroy_endpoint_blocked_via_proxy(host):
    """Test destroy endpoint is blocked via Apache proxy."""
    cmd = host.run("curl -s -o /dev/null -w '%{http_code}' http://localhost/api/datasets/test/destroy")
    assert cmd.rc == 0
    # Should return 302 (redirect) when blocked
    assert "302" in cmd.stdout
