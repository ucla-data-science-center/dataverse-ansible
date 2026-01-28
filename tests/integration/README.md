# Dataverse Integration Tests

This directory contains integration tests for validating Dataverse deployments,
particularly useful after 5.x to 6.x migrations.

## Test Categories

### Migration Tests (`test_migration.py`)
Validates that the 5.x to 6.x migration completed successfully:
- Flyway migrations completed without errors
- Required JPA tables exist (storageuse, datasettype, etc.)
- Database schema is correct
- Existing data survived migration

### Smoke Tests (`test_smoke.py`)
Validates basic Dataverse functionality:
- API health endpoints respond
- Search works (Solr integration)
- Datasets are accessible
- File downloads work
- User authentication works

## Running Tests

### Prerequisites

Install test dependencies:
```bash
cd dataverse-ansible
uv sync
```

### Run All Tests
```bash
uv run pytest tests/integration -v \
    --dataverse-url=https://your-instance.com
```

### Run Migration Tests Only
```bash
uv run pytest tests/integration/test_migration.py -v \
    --dataverse-url=https://your-instance.com \
    --db-host=your-rds-endpoint.rds.amazonaws.com \
    --db-user=postgres \
    --db-password=yourpass
```

### Run Smoke Tests Only
```bash
uv run pytest tests/integration/test_smoke.py -v \
    --dataverse-url=https://your-instance.com
```

### Run with API Token (for authenticated endpoints)
```bash
uv run pytest tests/integration -v \
    --dataverse-url=https://your-instance.com \
    --api-token=your-api-token
```

### Run by Marker
```bash
# Only migration tests
uv run pytest tests/integration -v -m migration

# Only smoke tests
uv run pytest tests/integration -v -m smoke

# Only API tests
uv run pytest tests/integration -v -m api

# Skip slow tests
uv run pytest tests/integration -v -m "not slow"
```

## Environment Variables

You can also configure tests via environment variables:

```bash
export DATAVERSE_URL=https://your-instance.com
export DB_HOST=your-rds-endpoint.rds.amazonaws.com
export DB_PORT=5432
export DB_NAME=dvndb
export DB_USER=postgres
export DB_PASSWORD=yourpass
export DATAVERSE_API_TOKEN=your-token

uv run pytest tests/integration -v
```

## Test Configuration

Test configuration is in `pyproject.toml`:
- Default timeout: 60 seconds per test
- Markers: `migration`, `smoke`, `api`, `slow`

## Post-Migration Test Checklist

After running a 5.x to 6.x migration, run these tests in order:

1. **Flyway Migrations**
   ```bash
   uv run pytest tests/integration/test_migration.py::TestFlywayMigration -v
   ```

2. **JPA Tables**
   ```bash
   uv run pytest tests/integration/test_migration.py::TestJPATables -v
   ```

3. **Data Integrity**
   ```bash
   uv run pytest tests/integration/test_migration.py::TestDataIntegrity -v
   ```

4. **API Health**
   ```bash
   uv run pytest tests/integration/test_smoke.py::TestAPIHealth -v
   ```

5. **Search Functionality**
   ```bash
   uv run pytest tests/integration/test_smoke.py::TestSearch -v
   ```

6. **Full Smoke Suite**
   ```bash
   uv run pytest tests/integration/test_smoke.py -v
   ```

## Expected Results

### Successful Migration
All migration tests should pass with:
- Flyway history showing 6.8.x migrations
- All JPA tables exist with indexes
- No failed migrations
- Data counts > 0 (unless fresh install)

### Successful Deployment
All smoke tests should pass with:
- Version endpoint returns 6.x
- Search returns valid structure
- Root dataverse exists
- Homepage loads

## Troubleshooting

### Database Connection Fails
- Verify RDS security group allows connections from test runner
- Check credentials are correct
- Ensure psycopg2-binary is installed

### API Tests Return 403
- Some endpoints require authentication
- Add `--api-token` with admin API token

### Solr Tests Skip
- Solr is typically only accessible from localhost
- These tests will skip if run remotely

### Timeout Errors
- Increase timeout with `--timeout=120`
- Or add `@pytest.mark.timeout(120)` to specific tests
