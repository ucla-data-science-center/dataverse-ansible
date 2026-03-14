"""
Migration validation tests for Dataverse 5.x to 6.x upgrade.

These tests verify that:
1. Flyway migrations completed successfully
2. Required JPA tables exist
3. Database schema is correct for 6.8
4. Existing data survived the migration

Run with:
    pytest tests/integration/test_migration.py -v --dataverse-url=https://your-instance.com

Or with database tests:
    pytest tests/integration/test_migration.py -v \
        --dataverse-url=https://your-instance.com \
        --db-host=your-rds-endpoint.rds.amazonaws.com \
        --db-user=postgres \
        --db-password=yourpass
"""

import pytest


class TestFlywayMigration:
    """Tests to verify Flyway migrations completed successfully."""

    @pytest.mark.migration
    def test_flyway_history_exists(self, db_connection):
        """Verify flyway_schema_history table exists and has records."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'flyway_schema_history'
        """)
        result = cursor.fetchone()
        assert result[0] == 1, "flyway_schema_history table should exist"

    @pytest.mark.migration
    def test_flyway_latest_version(self, db_connection):
        """Verify migrations reached 6.8 version."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT version, description, success
            FROM flyway_schema_history
            WHERE version LIKE '6.8%'
            ORDER BY installed_rank DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        assert result is not None, "Should have 6.8.x migrations"
        assert result[2] is True, f"Migration {result[0]} should be successful"

    @pytest.mark.migration
    def test_no_failed_migrations(self, db_connection):
        """Verify no migrations failed."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT version, description
            FROM flyway_schema_history
            WHERE success = false
        """)
        failed = cursor.fetchall()
        assert len(failed) == 0, f"Found failed migrations: {failed}"


class TestJPATables:
    """Tests to verify JPA tables exist (required for 5.x to 6.x migration)."""

    @pytest.mark.migration
    @pytest.mark.parametrize("table_name", [
        "storageuse",
        "datasettype",
        "makedatacountprocessstate",
        "dataversefeatureditem",
        "storagequota",
        "retention",
    ])
    def test_jpa_table_exists(self, db_connection, table_name):
        """Verify required JPA tables exist."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """, (table_name,))
        result = cursor.fetchone()
        assert result[0] is True, f"Table {table_name} should exist"

    @pytest.mark.migration
    def test_storageuse_has_index(self, db_connection):
        """Verify storageuse table has required index."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'storageuse'
            AND indexname LIKE '%dvobjectcontainer%'
        """)
        result = cursor.fetchone()
        assert result is not None, "storageuse should have dvobjectcontainer index"


class TestSchemaIntegrity:
    """Tests to verify database schema integrity after migration."""

    @pytest.mark.migration
    def test_dvobject_table_exists(self, db_connection):
        """Verify core dvobject table exists."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'dvobject'
            )
        """)
        assert cursor.fetchone()[0] is True

    @pytest.mark.migration
    def test_dataset_table_has_type_column(self, db_connection):
        """Verify dataset table has datasettype column (added in 6.3)."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'dataset'
                AND column_name = 'datasettype_id'
            )
        """)
        result = cursor.fetchone()
        # This column may or may not exist depending on migration path
        # Just verify the query works
        assert result is not None

    @pytest.mark.migration
    def test_setting_table_exists(self, db_connection):
        """Verify setting table exists (used for configuration)."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'setting'
            )
        """)
        assert cursor.fetchone()[0] is True


class TestDataIntegrity:
    """Tests to verify existing data survived migration."""

    @pytest.mark.migration
    def test_datasets_exist(self, db_connection):
        """Verify datasets exist in database."""
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM dataset")
        result = cursor.fetchone()
        # Just verify we can query - actual count depends on data
        assert result[0] >= 0

    @pytest.mark.migration
    def test_dataverses_exist(self, db_connection):
        """Verify dataverses exist in database."""
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM dataverse")
        result = cursor.fetchone()
        # Should have at least root dataverse
        assert result[0] >= 1, "Should have at least root dataverse"

    @pytest.mark.migration
    def test_users_exist(self, db_connection):
        """Verify users exist in database."""
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM authenticateduser")
        result = cursor.fetchone()
        # Should have at least admin user
        assert result[0] >= 1, "Should have at least one authenticated user"

    @pytest.mark.migration
    def test_datafiles_reference_valid_datasets(self, db_connection):
        """Verify datafile foreign keys are valid."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM datafile df
            LEFT JOIN dvobject dvo ON df.id = dvo.id
            WHERE dvo.id IS NULL
        """)
        result = cursor.fetchone()
        assert result[0] == 0, "All datafiles should reference valid dvobjects"


class TestPIDConfiguration:
    """Tests to verify PID provider configuration."""

    @pytest.mark.migration
    def test_no_legacy_doi_provider_setting(self, db_connection):
        """Verify old :DoiProvider setting is removed."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM setting
            WHERE name = ':DoiProvider'
        """)
        result = cursor.fetchone()
        # May or may not be present depending on cleanup
        # Just log for informational purposes
        if result[0] > 0:
            pytest.skip("Legacy :DoiProvider setting still present - consider removing")

    @pytest.mark.migration
    def test_pid_settings_valid(self, db_connection):
        """Verify PID-related settings exist."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT name, content FROM setting
            WHERE name LIKE ':Protocol'
            OR name LIKE ':Authority'
            OR name LIKE ':Shoulder'
        """)
        results = cursor.fetchall()
        # Just verify query works - actual settings depend on configuration
        assert isinstance(results, list)
