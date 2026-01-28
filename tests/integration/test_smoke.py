"""
Smoke tests for Dataverse deployment validation.

These tests verify basic functionality:
1. API endpoints respond correctly
2. Search works (Solr integration)
3. Datasets are accessible
4. File downloads work
5. User authentication works

Run with:
    pytest tests/integration/test_smoke.py -v --dataverse-url=https://your-instance.com

With API token for authenticated tests:
    pytest tests/integration/test_smoke.py -v \
        --dataverse-url=https://your-instance.com \
        --api-token=your-api-token
"""

import pytest
import requests


class TestAPIHealth:
    """Tests for API health and basic endpoints."""

    @pytest.mark.smoke
    @pytest.mark.api
    def test_api_version(self, api_session, dataverse_url):
        """Verify /api/info/version returns correct version."""
        response = api_session.get(f"{dataverse_url}/api/info/version")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert data.get("status") == "OK"
        assert "version" in data.get("data", {})

        version = data["data"]["version"]
        assert version.startswith("6."), f"Expected version 6.x, got {version}"

    @pytest.mark.smoke
    @pytest.mark.api
    def test_api_server_info(self, api_session, dataverse_url):
        """Verify /api/info/server returns server info."""
        response = api_session.get(f"{dataverse_url}/api/info/server")
        assert response.status_code == 200

        data = response.json()
        assert data.get("status") == "OK"

    @pytest.mark.smoke
    @pytest.mark.api
    def test_api_settings(self, api_session, dataverse_url):
        """Verify public settings endpoint works."""
        response = api_session.get(f"{dataverse_url}/api/info/settings/:Languages")
        # May return 404 if setting doesn't exist, or 200 if it does
        assert response.status_code in [200, 404]


class TestSearch:
    """Tests for Solr search functionality."""

    @pytest.mark.smoke
    @pytest.mark.api
    def test_search_endpoint_responds(self, api_session, dataverse_url):
        """Verify search endpoint responds."""
        response = api_session.get(f"{dataverse_url}/api/search", params={"q": "*"})
        assert response.status_code == 200

        data = response.json()
        assert data.get("status") == "OK"
        assert "data" in data

    @pytest.mark.smoke
    @pytest.mark.api
    def test_search_returns_results_structure(self, api_session, dataverse_url):
        """Verify search returns proper result structure."""
        response = api_session.get(f"{dataverse_url}/api/search", params={"q": "*"})
        assert response.status_code == 200

        data = response.json()
        search_data = data.get("data", {})

        assert "items" in search_data
        assert "total_count" in search_data
        assert isinstance(search_data["total_count"], int)

    @pytest.mark.smoke
    @pytest.mark.api
    def test_search_with_filter(self, api_session, dataverse_url):
        """Verify search with type filter works."""
        response = api_session.get(
            f"{dataverse_url}/api/search",
            params={"q": "*", "type": "dataset"}
        )
        assert response.status_code == 200

        data = response.json()
        items = data.get("data", {}).get("items", [])
        # If there are results, they should all be datasets
        for item in items:
            assert item.get("type") == "dataset"


class TestDataverse:
    """Tests for dataverse (collection) functionality."""

    @pytest.mark.smoke
    @pytest.mark.api
    def test_root_dataverse_exists(self, api_session, dataverse_url):
        """Verify root dataverse is accessible (tries 'root' then first dataverse)."""
        # Try 'root' first (standard Dataverse setup)
        response = api_session.get(f"{dataverse_url}/api/dataverses/root")
        if response.status_code == 404:
            # Fall back to ID 1 (common for migrated instances)
            response = api_session.get(f"{dataverse_url}/api/dataverses/1")

        assert response.status_code == 200, f"No root dataverse found. Status: {response.status_code}"

        data = response.json()
        assert data.get("status") == "OK"
        assert "data" in data
        assert "name" in data["data"]

    @pytest.mark.smoke
    @pytest.mark.api
    def test_root_dataverse_contents(self, api_session, dataverse_url):
        """Verify root dataverse contents can be listed."""
        # Try 'root' first
        response = api_session.get(f"{dataverse_url}/api/dataverses/root/contents")
        if response.status_code == 404:
            # Fall back to ID 1
            response = api_session.get(f"{dataverse_url}/api/dataverses/1/contents")

        assert response.status_code == 200

        data = response.json()
        assert data.get("status") == "OK"


class TestDatasets:
    """Tests for dataset functionality."""

    @pytest.mark.smoke
    @pytest.mark.api
    def test_datasets_endpoint(self, api_session, dataverse_url):
        """Verify datasets can be retrieved via search."""
        response = api_session.get(
            f"{dataverse_url}/api/search",
            params={"q": "*", "type": "dataset", "per_page": 1}
        )
        assert response.status_code == 200

        data = response.json()
        items = data.get("data", {}).get("items", [])

        if len(items) > 0:
            # Try to get the first dataset directly
            dataset = items[0]
            global_id = dataset.get("global_id")
            if global_id:
                detail_response = api_session.get(
                    f"{dataverse_url}/api/datasets/:persistentId",
                    params={"persistentId": global_id}
                )
                # Should get 200 for published or 403 for unpublished
                assert detail_response.status_code in [200, 403]

    @pytest.mark.smoke
    @pytest.mark.api
    @pytest.mark.slow
    def test_dataset_by_id(self, api_session, dataverse_url):
        """Verify dataset retrieval by ID works."""
        # Try to get dataset with ID 1 (may not exist)
        response = api_session.get(f"{dataverse_url}/api/datasets/1")
        # 200 if exists, 404 if not
        assert response.status_code in [200, 404]


class TestSolrIndexing:
    """Tests to verify Solr indexing status."""

    @pytest.mark.smoke
    @pytest.mark.api
    def test_index_status_endpoint(self, api_session, dataverse_url, api_token):
        """Verify index status endpoint works (requires auth)."""
        if not api_token:
            pytest.skip("API token required for admin endpoint")

        response = api_session.get(f"{dataverse_url}/api/admin/index/status")
        assert response.status_code == 200

        data = response.json()
        assert data.get("status") == "OK"

    @pytest.mark.smoke
    @pytest.mark.api
    def test_solr_direct_ping(self, api_session, dataverse_url):
        """Verify Solr responds (only works if Solr is accessible)."""
        # Note: Solr is usually only accessible from localhost
        # This test may fail if run remotely
        try:
            solr_url = dataverse_url.replace(":8080", ":8983").replace(":443", ":8983").replace(":80", ":8983")
            response = requests.get(f"{solr_url}/solr/collection1/admin/ping", timeout=5)
            if response.status_code == 200:
                data = response.json()
                assert data.get("status") == "OK"
        except requests.exceptions.ConnectionError:
            pytest.skip("Solr not directly accessible from test runner")


class TestWebInterface:
    """Tests for web interface accessibility."""

    @pytest.mark.smoke
    def test_homepage_loads(self, dataverse_url):
        """Verify homepage returns 200."""
        response = requests.get(dataverse_url, timeout=30)
        assert response.status_code == 200

    @pytest.mark.smoke
    def test_homepage_contains_dataverse(self, dataverse_url):
        """Verify homepage contains expected content."""
        response = requests.get(dataverse_url, timeout=30)
        assert response.status_code == 200
        # Check for common Dataverse page elements
        content = response.text.lower()
        assert "dataverse" in content or "dataset" in content

    @pytest.mark.smoke
    def test_https_redirect(self, dataverse_url):
        """Verify HTTP redirects to HTTPS (if applicable)."""
        if dataverse_url.startswith("https://"):
            http_url = dataverse_url.replace("https://", "http://")
            response = requests.get(http_url, allow_redirects=False, timeout=10)
            # Should redirect to HTTPS
            if response.status_code == 301 or response.status_code == 302:
                location = response.headers.get("Location", "")
                assert location.startswith("https://")


class TestAuthentication:
    """Tests for authentication endpoints."""

    @pytest.mark.smoke
    @pytest.mark.api
    def test_builtin_users_endpoint(self, api_session, dataverse_url):
        """Verify builtin-users endpoint exists (may be blocked)."""
        response = api_session.get(f"{dataverse_url}/api/builtin-users")
        # Endpoint may be blocked (403) or require POST (405) or work (200)
        assert response.status_code in [200, 403, 405]

    @pytest.mark.smoke
    @pytest.mark.api
    def test_api_token_validates(self, api_session, dataverse_url, api_token):
        """Verify API token works for authenticated endpoints."""
        if not api_token:
            pytest.skip("API token required for this test")

        response = api_session.get(f"{dataverse_url}/api/users/:me")
        assert response.status_code == 200

        data = response.json()
        assert data.get("status") == "OK"
        assert "data" in data


class TestS3Integration:
    """Tests for S3 storage integration."""

    @pytest.mark.smoke
    @pytest.mark.api
    def test_storage_driver_configured(self, api_session, dataverse_url, api_token):
        """Verify storage driver settings (requires auth)."""
        if not api_token:
            pytest.skip("API token required for admin endpoint")

        # Check for S3 configuration via API
        # This is informational - actual S3 functionality tested via file upload/download
        response = api_session.get(f"{dataverse_url}/api/info/settings/:FileAccessDefault")
        # Setting may or may not exist
        assert response.status_code in [200, 404]

    @pytest.mark.smoke
    @pytest.mark.api
    @pytest.mark.slow
    def test_file_download_redirect(self, api_session, dataverse_url):
        """Test that file downloads work (with S3 redirect if configured)."""
        # Find a file to download
        response = api_session.get(
            f"{dataverse_url}/api/search",
            params={"q": "*", "type": "file", "per_page": 1}
        )

        if response.status_code != 200:
            pytest.skip("Could not search for files")

        data = response.json()
        items = data.get("data", {}).get("items", [])

        if len(items) == 0:
            pytest.skip("No files found in instance")

        file_item = items[0]
        file_id = file_item.get("file_id")

        if file_id:
            # Try to download (may require auth for restricted files)
            download_response = requests.get(
                f"{dataverse_url}/api/access/datafile/{file_id}",
                allow_redirects=False,
                timeout=10
            )
            # 200 = direct download, 302/303 = redirect (S3), 403 = restricted, 404 = not found (indexing)
            assert download_response.status_code in [200, 302, 303, 403, 404], \
                f"File download returned unexpected status: {download_response.status_code}"
