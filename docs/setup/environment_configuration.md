# Environment Configuration Best Practices

This guide outlines the recommended strategy for managing configuration across different environments (Staging/Test vs. Production) in the Dataverse Ansible project.

## The `group_vars` Strategy

Ansible variable precedence can be complex. We use a **Role Defaults + Environment Overrides** strategy.

### 1. `defaults/main.yml` (The Foundation)
*   Contains sane defaults for a generic, single-node installation.
*   **Do not modify this file** for environment-specific settings.

### 2. `group_vars/all.yml` (The Base Structure)
*   Defines the **full nested dictionary structure** for complex variables like `dataverse`, `apache`, etc.
*   This is critical because Ansible replaces dictionaries by default, rather than merging them.
*   Inherited by *all* environments.

### 3. `group_vars/<environment>.yml` (The Override)
*   Specific files for `staging.yml`, `production.yml`, etc.
*   **Best Practice:** When overriding a dictionary (e.g., `dataverse`), you must often redeclare the **entire structure** or the relevant sub-keys if you want to be safe.
*   **Terraform Integration:** We have a bridge task (`tasks/terraform_bridge.yml`) that automatically injects Terraform outputs (like `dataverse_s3_bucket`) into the correct Ansible variables, so you don't need to manually copy IPs or bucket names into these files.

## Staging vs. Production

| Feature | Staging (`staging.yml`) | Production (`production.yml`) |
| :--- | :--- | :--- |
| **SSL/TLS** | Use Let's Encrypt Staging (`test_cert: true`) to avoid rate limits. | Use Let's Encrypt Production. |
| **Database** | `log_statements: all` for debugging. | `log_statements: none` for performance. |
| **Backups** | Optional/Minimal. | **Critical:** Enable S3 backups. |
| **PID Provider** | Fake/DataCite Test (`authority: 10.5072`). | Real DataCite/EZID (`authority: 10.xxxx`). |
| **Passwords** | Can use vault or lesser secrets for speed. | **MUST** use `ansible-vault` for all secrets. |
| **Versions** | Test new releases (e.g., `6.9`). | Stable releases only (e.g., `6.8`). |

## External Database (RDS) Configuration

If you are using AWS RDS (recommended), configure your `group_vars/<env>.yml` as follows:

```yaml
db:
  postgres:
    enabled: false        # CRITICAL: Disables local PostgreSQL installation
    host: "your-rds-endpoint.us-west-2.rds.amazonaws.com"
    port: 5432
    name: "dvndb"
    user: "postgres"      # Your RDS master username
    pass: "{{ vault_rds_password }}" # Encrypt this!
    version: 16
```

**Note:** Ensure your RDS Security Group allows inbound traffic on port 5432 from your EC2 instance's IP/Security Group.

## Terraform Integration

This project is designed to work with the `terraform-dataverse` repository.

1.  **Provision:** Terraform creates EC2 + S3 and outputs `inventory-<env>.yml`.
2.  **Inventory:** The generated inventory sets host variables like `dataverse_s3_bucket` and `aws_region`.
3.  **Bridge:** The `tasks/terraform_bridge.yml` task detects these variables and updates the `s3` configuration automatically:
    ```yaml
    # Automatically happens if dataverse_s3_bucket is defined
    s3:
      enabled: true
      bucket_name: "{{ dataverse_s3_bucket }}"
      region: "{{ aws_region }}"
      ...
    ```

## 5.14 to 6.8 Upgrade Strategy

Since you are migrating from Dataverse 5.14, you can leverage the built-in Flyway database migration tools.

Please follow the detailed guide in **[docs/operations/upgrade_path_5x_to_6x.md](../operations/upgrade_path_5x_to_6x.md)**.

**Summary:**
1.  **Parallel Deployment:** Provision a fresh 6.8 environment (Rocky 9 / Java 17).
2.  **Database Migration:** Export your 5.14 DB and import it into the new environment.
3.  **Auto-Upgrade:** Start Dataverse 6.8. Flyway will automatically detect the 5.14 schema and apply all necessary upgrades to reach 6.8.
4.  **Re-index:** Trigger a full Solr re-index to populate the search engine.
