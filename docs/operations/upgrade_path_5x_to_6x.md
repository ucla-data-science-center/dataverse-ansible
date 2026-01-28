# Dataverse 5.14 to 6.8 Upgrade Strategy

**Context:** You are migrating from an existing Dataverse 5.14 installation to a new Dataverse 6.8 infrastructure (Rocky 9 / Java 17 / Payara 6).

## The Strategy: Parallel Deployment with Database Migration

Since you are already on version 5.14, your database includes **Flyway** migration history. This allows us to use a "Parallel Deployment" strategy where the application handles the database upgrade automatically.

### Phase 1: Deploy New Infrastructure (Terraform + Ansible)
Provision the new Dataverse 6.8 environment using the Terraform/Ansible pipeline.
*   **OS:** Rocky Linux 9
*   **Java:** OpenJDK 17
*   **App Server:** Payara 6 Community (6.2023.8+)
*   **Solr:** Solr 9.x (with Dataverse 6.8 schema)

### Phase 2: Data Migration

1.  **Stop 5.14 Services:** Ensure no new data is written.
2.  **Database Dump:**
    *   Create a full dump of the 5.14 database.
    *   *Note:* Dataverse 6.8 supports PostgreSQL 13+. If your 5.14 DB is on an older version (e.g., 9.6, 10), `pg_dump` followed by `pg_restore` into the new DB server is the correct upgrade path.
3.  **File Migration:**
    *   Sync your file storage (S3 bucket or local filesystem) to the new location.
    *   **S3 Note:** Dataverse 6.x uses AWS SDK v2. The `payload-signing` option is deprecated and removed. Ensure your Ansible config does not force this setting.

### Phase 3: The Upgrade (Flyway)

1.  **Import Database:** Restore the 5.14 dump into the new PostgreSQL instance.
2.  **Verify Flyway History:** Before starting, verify the source DB has history:
    ```sql
    SELECT * FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 5;
    ```
3.  **Start Dataverse 6.8:**
    *   Start the Payara service.
    *   **Automated Action:** On startup, Dataverse will detect the existing `flyway_schema_history` table (from 5.14).
    *   It will automatically execute all necessary migration scripts (SQL) to bring the schema from 5.14 -> 6.0 -> 6.8.
    *   *Check `server.log` to confirm successful migration.*

### Phase 4: Solr Re-indexing (CRITICAL)

Because we "jumped" versions, we skipped the manual Solr schema updates that would occur in an in-place upgrade.
*   **State:** You have a fresh Solr 9 install with the latest 6.8 schema, but an empty index.
*   **Action:** You **MUST** trigger a full re-index of the system.
    ```bash
    # Trigger full re-index
    curl http://localhost:8080/api/admin/index
    
    # Monitor status (this process may take hours)
    curl http://localhost:8080/api/admin/index/status
    ```

### Phase 5: Post-Migration Validation

1.  **Verify Object Counts:** Compare dataset and file counts with your 5.14 production instance.
2.  **Smoke Tests:**
    *   [ ] Can browse collections?
    *   [ ] Can search for known datasets?
    *   [ ] Can download files (verifies S3 mapping)?
    *   [ ] Does the API respond (e.g., `/api/info/version`)?

## RDS Specifics (If using AWS RDS)
*   **Extensions:** Ensure `pg_trgm` and `unaccent` are enabled on the RDS instance:
    ```sql
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
    CREATE EXTENSION IF NOT EXISTS unaccent;
    ```
*   **Security:** Ensure the RDS Security Group allows port 5432 **only** from the Dataverse EC2 instance Security Group.

## Rollback Plan
*   **Safety Net:** Keep the old 5.14 production instance **running but inaccessible** (e.g., remove DNS pointer) until the new 6.8 instance is fully validated for at least one week.
*   **Revert:** If the migration fails, simply point DNS back to the old 5.14 IP.

## Summary of Changes (5.14 -> 6.8)

| Component | 5.14 | 6.8 | Action |
| :--- | :--- | :--- | :--- |
| **OS** | CentOS 7 | Rocky 9 | New Install |
| **Java** | Java 11 | Java 17 | New Install |
| **Payara** | Payara 5 | Payara 6 | New Install |
| **Solr** | Solr 8 | Solr 9 | New Install + Re-index |
| **Database** | Postgres <13 | Postgres 16 | Dump/Restore + Flyway Auto-upgrade |
| **S3 SDK** | v1 | v2 | Config update (Auto-handled by defaults) |
