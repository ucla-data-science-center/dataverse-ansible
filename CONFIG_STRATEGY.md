# Dataverse Configuration Strategy: Local Testing vs AWS Deployment

## Overview

This document outlines the configuration strategy for testing Dataverse locally with Molecule/Docker and deploying to AWS environments.

## Configuration File Structure

```
molecule/rocky9/group_vars/
├── molecule.yml     # Local Docker testing overrides
├── dev.yml          # AWS dev environment overrides
└── prod.yml         # AWS prod environment overrides

defaults/main.yml    # Base defaults for ALL environments (493 lines)
```

### Configuration Precedence

1. **Lowest**: `defaults/main.yml` - Base role defaults
2. **Medium**: `molecule/rocky9/group_vars/*.yml` - Environment-specific overrides
3. **Highest**: Command-line `-e` extra vars (runtime overrides)

---

## ✅ What CAN Be Tested Locally (Molecule/Docker)

### Core Services & Versions
- ✅ **PostgreSQL**: Full database setup, users, schemas, version testing
- ✅ **Solr**: Search indexing, schema configuration
- ✅ **Payara**: Application server, JVM tuning, domain configuration
- ✅ **Apache**: HTTP reverse proxy, AJP connector, port configuration

### Application Features
- ✅ **Branding**: Logos, CSS, custom headers/footers
- ✅ **Language packs**: Multi-language support
- ✅ **Licenses**: Creative Commons, custom licenses
- ✅ **Custom metadata blocks**: Schema definitions
- ✅ **Sample data**: Test datasets and dataverses
- ✅ **File storage**: Local filesystem storage
- ✅ **External tools**: Data Explorer, previewers
- ✅ **API configuration**: Endpoints, blocked endpoints
- ✅ **Email**: localhost SMTP (no real emails sent)
- ✅ **User management**: Built-in users, roles
- ✅ **Dataverse version**: Test upgrades, different versions

### Current Molecule Configuration
```yaml
# molecule/rocky9/group_vars/molecule.yml (excerpts)
dataverse_hostname: localhost
dataverse_siteurl: "http://localhost:8080"
dataverse_use_ssl: false            # No SSL locally
dataverse_use_shib: false           # No Shibboleth locally
dataverse_doi_provider: none        # No real DOIs
dataverse_enable_telemetry: false
dataverse_postgresql_backups_enabled: false
rserve_install: false               # Skip R integration

# IMPORTANT for Docker: Payara must listen on all interfaces
dataverse:
  payara:
    listen_address: 0.0.0.0         # NOT 127.0.0.1 (default)
```

**Note**: The default `listen_address: 127.0.0.1` in `defaults/main.yml` prevents Docker port mapping from working. Must override to `0.0.0.0` for Molecule testing.

---

## ⚠️ Partial Testing (Can Simulate Locally)

### S3 Storage
**Local simulation options:**
- ✅ **LocalStack**: AWS S3-compatible mock service
- ✅ **MinIO**: S3-compatible object storage in Docker

```yaml
# Can test with localstack/minio
localstack:
  enabled: true
  port: 4566
  buckets:
    - label: LocalStack
      bucket_name: mybucket
      custom_endpoint_url: "http://localhost:4566"
```

**AWS deployment:**
```yaml
# AWS prod - use real S3
s3:
  enabled: true
  bucket_name: ucla-dataverse-prod
  region: us-west-2
  # No custom_endpoint_url
```

### DOI Registration
**Local testing:**
```yaml
dataverse_doi_provider: none  # Or use test.datacite.org
```

**AWS deployment:**
```yaml
dataverse:
  doi:
    provider: datacite
    baseurl: "https://mds.datacite.org/"      # Production DataCite
    username: "{{ vault_datacite_user }}"
    password: "{{ vault_datacite_pass }}"
```

---

## ❌ CANNOT Test Locally (AWS-Specific)

### SSL/TLS Certificates
**Why**: Requires real domain name and DNS resolution

**Local:** HTTP only
```yaml
apache:
  ssl:
    enabled: false
```

**AWS:**
```yaml
apache:
  ssl:
    enabled: true
    port: 443

letsencrypt:
  enabled: true
  email: sysadmin@ucla.edu
  certbot:
    autorenew: true
```

### Real Domain Names
**Local:**
```yaml
apache:
  public_fqdn: localhost  # or rocky9
dataverse_siteurl: "http://localhost:8080"
```

**AWS:**
```yaml
apache:
  public_fqdn: dataverse.ucla.edu
dataverse_siteurl: "https://dataverse.ucla.edu"
```

### RDS Database
**Why**: AWS-managed database service

**Local:** Local PostgreSQL in container
```yaml
db:
  use_rds: false
  postgres:
    host: localhost
```

**AWS:**
```yaml
db:
  use_rds: true
  postgres:
    host: "{{ vault_rds_endpoint }}"
    jdbcurl: "jdbc:postgresql://{{ vault_rds_endpoint }}:5432/dvndb"
```

### Production SMTP Relay
**Local:** localhost SMTP (no real emails)
```yaml
dataverse:
  smtp: localhost
```

**AWS:**
```yaml
dataverse:
  smtp: smtp-relay.ucla.edu  # or AWS SES
dataverse:
  service_email: noreply@ucla.edu
```

### Monitoring & Observability
**Local:** Skip monitoring
```yaml
prometheus:
  install: false
munin:
  install: false
grafana:
  install: false
```

**AWS:** Enable full monitoring stack
```yaml
prometheus:
  install: true
  url: "https://github.com/prometheus/prometheus/..."
grafana:
  install: true
```

### Shibboleth Authentication
**Why**: Requires real IdP integration

**Local:**
```yaml
dataverse_use_shib: false
```

**AWS:**
```yaml
dataverse_use_shib: true
shibboleth:
  idp_metadata_url: "https://shibboleth.ucla.edu/idp/shibboleth"
```

---

## Recommended Group_Vars Organization

### molecule.yml (Local Testing)
**Purpose**: Override defaults for local Docker testing
**Focus**: Disable production features, use localhost URLs

```yaml
# Essential local overrides
dataverse_hostname: localhost
dataverse_siteurl: "http://localhost:8080"
dataverse_use_ssl: false
dataverse_doi_provider: none
rserve_install: false
dataverse_postgresql_backups_enabled: false

# Compatibility shim (keep existing)
apache:
  port: 80
db:
  use_rds: false
  postgres:
    host: localhost
```

### dev.yml (AWS Development Environment)
**Purpose**: AWS-specific settings for development/staging
**Focus**: Real infrastructure but non-production

```yaml
# AWS dev-specific
apache:
  public_fqdn: dataverse-dev.ucla.edu
  ssl:
    enabled: true

letsencrypt:
  enabled: true
  certbot:
    test_cert: true  # Use Let's Encrypt staging

db:
  use_rds: true
  postgres:
    host: "{{ vault_dev_rds_endpoint }}"

dataverse:
  doi:
    provider: datacite
    baseurl: "https://mds.test.datacite.org/"  # DataCite test environment
```

### prod.yml (AWS Production Environment)
**Purpose**: Production AWS deployment
**Focus**: All production features enabled

```yaml
# AWS prod-specific
apache:
  public_fqdn: dataverse.ucla.edu
  ssl:
    enabled: true

letsencrypt:
  enabled: true
  certbot:
    test_cert: false  # Production certs

db:
  use_rds: true
  postgres:
    host: "{{ vault_prod_rds_endpoint }}"

dataverse:
  doi:
    provider: datacite
    baseurl: "https://mds.datacite.org/"  # Production DataCite

prometheus:
  install: true
grafana:
  install: true

dataverse:
  enable_telemetry: true
```

---

## Testing Strategy

### Phase 1: Local Feature Testing (Molecule)
**Test locally first:**
1. Branding and customization
2. Metadata blocks
3. License configuration
4. Sample data ingestion
5. API functionality
6. User workflows
7. Version upgrades

**Command:**
```bash
uv run molecule converge -s rocky9
```

### Phase 2: AWS Dev Deployment
**Test AWS-specific features:**
1. SSL/TLS with real domain
2. RDS connectivity
3. S3 storage integration
4. SMTP relay
5. Monitoring stack
6. DOI registration (test)

**Command:**
```bash
ansible-playbook -i inventory/dev dataverse.pb -e "@molecule/rocky9/group_vars/dev.yml"
```

### Phase 3: Production Deployment
**Full production deployment:**
1. Production DOI provider
2. Shibboleth (if needed)
3. Backup automation
4. Monitoring alerts

**Command:**
```bash
ansible-playbook -i inventory/prod dataverse.pb -e "@molecule/rocky9/group_vars/prod.yml"
```

---

## Known Issues from Molecule Run

### ⚠️ Non-Critical
1. **Solr log4j warning**: `zip error: Nothing to do!`
   - **Cause**: Log4j JndiLookup.class already removed in newer versions
   - **Impact**: None - CVE mitigation already applied by Solr
   - **Action**: Can ignore or update task to check if class exists first

2. **Duplicate collection warning**: `community.general 11.2.1 found in two locations`
   - **Cause**: Collection in both `./collections/` (vendored) and `~/.ansible/collections/`
   - **Impact**: None - first one is used
   - **Action**: Remove from `~/.ansible/collections/` if desired

### ✅ All Other Tasks: Success
- PostgreSQL 16 installed and configured
- Payara 6.2025.3 running
- Solr 9.8.0 operational
- Apache reverse proxy configured
- Dataverse 6.8 deployed

---

## Next Steps

1. **Authenticate gh CLI** (optional):
   ```bash
   gh auth login
   ```

2. **Create/Review GitHub Issues** for:
   - AWS RDS configuration
   - SSL/Let's Encrypt setup
   - S3 storage migration
   - Production SMTP configuration
   - Shibboleth integration

3. **Create group_vars files**:
   ```bash
   # Edit dev.yml and prod.yml with AWS-specific settings
   vi molecule/rocky9/group_vars/dev.yml
   vi molecule/rocky9/group_vars/prod.yml
   ```

4. **Test local changes**:
   ```bash
   molecule destroy -s rocky9
   molecule converge -s rocky9
   ```

5. **Access local Dataverse**:
   - URL: http://localhost:8080
   - User: dataverseAdmin
   - Password: admin1

---

## References

- Dataverse Installation Guide: https://guides.dataverse.org/en/latest/installation/
- Ansible Best Practices: https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html
- Molecule Documentation: https://ansible.readthedocs.io/projects/molecule/
