# Dataverse 5.14 → 6.8 Migration Overview

## For: UCLA Dataverse Team
## Date: January 2025

---

## What We're Doing

We're upgrading UCLA Dataverse from version 5.14 to 6.8. Instead of upgrading in-place (risky), we're using a **Parallel Deployment** strategy: build a completely new environment, migrate the data, and switch over.

---

## Architecture Diagram

```
                            CURRENT STATE
    ┌─────────────────────────────────────────────────────────┐
    │                   PRODUCTION (5.14)                      │
    │                   dataverse.ucla.edu                     │
    │  ┌─────────────────────────────────────────────────────┐ │
    │  │              Single EC2 Instance                    │ │
    │  │  ┌─────────┐ ┌─────────┐ ┌──────┐ ┌─────────────┐  │ │
    │  │  │ Apache  │ │ Payara  │ │ Solr │ │ PostgreSQL  │  │ │
    │  │  │  httpd  │ │   5     │ │  8   │ │   (old)     │  │ │
    │  │  └─────────┘ └─────────┘ └──────┘ └─────────────┘  │ │
    │  │                    │                                │ │
    │  │              Local Files or S3                      │ │
    │  └─────────────────────────────────────────────────────┘ │
    └─────────────────────────────────────────────────────────┘


                            NEW STATE (Target)
    ┌─────────────────────────────────────────────────────────┐
    │                    TEST ENVIRONMENT                      │
    │                  (becomes production)                    │
    │                                                          │
    │  ┌────────────────────────┐    ┌─────────────────────┐  │
    │  │     EC2 Instance       │    │     AWS RDS         │  │
    │  │     (Rocky Linux 9)    │    │   (PostgreSQL 16)   │  │
    │  │  ┌─────────┐           │    │                     │  │
    │  │  │ Apache  │           │    │  - Managed backups  │  │
    │  │  │  httpd  │           │    │  - Auto-failover    │  │
    │  │  └─────────┘           │    │  - Point-in-time    │  │
    │  │  ┌─────────┐           │    │    recovery         │  │
    │  │  │ Payara  │◄─────────────► │                     │  │
    │  │  │   6     │   Port 5432    └─────────────────────┘  │
    │  │  │ Java 17 │           │                              │
    │  │  └─────────┘           │    ┌─────────────────────┐  │
    │  │  ┌─────────┐           │    │      AWS S3         │  │
    │  │  │  Solr   │           │    │  (File Storage)     │  │
    │  │  │   9     │           │    │                     │  │
    │  │  └─────────┘           │    │  - Durable storage  │  │
    │  │       │                │    │  - Versioning       │  │
    │  │       └────────────────────►│  - Lifecycle rules  │  │
    │  └────────────────────────┘    └─────────────────────┘  │
    └─────────────────────────────────────────────────────────┘
```

---

## Migration Flow

```
    ┌──────────────────────────────────────────────────────────────────────┐
    │                        MIGRATION PROCESS                              │
    └──────────────────────────────────────────────────────────────────────┘

    PHASE 1: Build Infrastructure
    ─────────────────────────────

    Terraform                         AWS
    ┌─────────┐                    ┌─────────────────────────────┐
    │  Plan   │ ──── apply ────►   │  Creates:                   │
    │  Code   │                    │  • EC2 (Rocky 9)            │
    └─────────┘                    │  • RDS (PostgreSQL 16)      │
                                   │  • Security Groups          │
                                   │  • S3 Bucket                │
                                   └─────────────────────────────┘
                                              │
                                              ▼
    PHASE 2: Deploy Application
    ───────────────────────────

    Ansible                        EC2 Instance
    ┌─────────┐                    ┌─────────────────────────────┐
    │Playbook │ ──── deploy ────►  │  Installs:                  │
    │  Run    │                    │  • Java 17                  │
    └─────────┘                    │  • Payara 6                 │
                                   │  • Solr 9                   │
                                   │  • Apache httpd             │
                                   │  • Dataverse 6.8 WAR        │
                                   └─────────────────────────────┘
                                              │
                                              ▼
                                   ┌─────────────────────────────┐
                                   │  STOP PAYARA IMMEDIATELY!   │
                                   │  (Don't let it init empty   │
                                   │   database)                 │
                                   └─────────────────────────────┘
                                              │
                                              ▼
    PHASE 3: Data Migration
    ───────────────────────

    Production 5.14                          Test RDS
    ┌─────────────────┐                    ┌─────────────────┐
    │  pg_dump        │                    │                 │
    │  dvndb          │ ──── restore ────► │  dvndb (5.14    │
    │  (5.14 schema)  │                    │  schema)        │
    └─────────────────┘                    └─────────────────┘
                                                    │
    Production Files                                │
    ┌─────────────────┐                            │
    │  /usr/local/    │                            │
    │  dvn/data/      │ ──── s3 sync ────► S3     │
    │  (or S3)        │                            │
    └─────────────────┘                            │
                                                    ▼
    PHASE 4: The Magic (Flyway Auto-Upgrade)
    ────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────┐
    │                                                             │
    │    Start Payara ──► Dataverse 6.8 boots                     │
    │                          │                                  │
    │                          ▼                                  │
    │    Flyway detects: "DB is version 5.14, I'm version 6.8"   │
    │                          │                                  │
    │                          ▼                                  │
    │    Automatically runs ~30 migration scripts:                │
    │    5.14 → 6.0 → 6.1 → 6.2 → ... → 6.8                      │
    │                          │                                  │
    │                          ▼                                  │
    │    Schema upgraded! Application ready.                      │
    │                                                             │
    └─────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
    PHASE 5: Re-index & Validate
    ────────────────────────────

    ┌─────────────────────────────────────────────────────────────┐
    │  curl http://localhost:8080/api/admin/index                 │
    │                                                             │
    │  Solr rebuilds search index (may take hours for large DB)   │
    │                                                             │
    │  Then: Test everything!                                     │
    │  • Browse collections                                       │
    │  • Search datasets                                          │
    │  • Download files                                           │
    │  • Check API                                                │
    └─────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
    PHASE 6: Cutover (When Ready)
    ─────────────────────────────

    ┌─────────────────┐              ┌─────────────────┐
    │  DNS:           │              │  DNS:           │
    │  dataverse.     │   ────►      │  dataverse.     │
    │  ucla.edu       │   switch     │  ucla.edu       │
    │  → OLD IP       │              │  → NEW IP       │
    └─────────────────┘              └─────────────────┘

    Old server stays running as rollback option for 1 week.
```

---

## Why This Approach?

| Concern | How We Address It |
|---------|-------------------|
| **Data Loss** | We never touch production. We work on a copy. |
| **Downtime** | Minimal. New system is ready before we switch DNS. |
| **Rollback** | Instant. Just point DNS back to old server. |
| **Testing** | Full testing with real data before going live. |
| **Database Upgrade** | Flyway handles it automatically. Battle-tested. |

---

## Key Safety Measures

### "Disarming" the Test Environment

Before testing with production data, we configure the test system to be safe:

```sql
-- Change site URL (so links point to test, not production)
UPDATE setting SET content = 'https://test.dataverse.ucla.edu'
WHERE name = ':SiteUrl';

-- Disable DOI minting (don't create real DOIs for test data)
UPDATE setting SET content = 'FAKE'
WHERE name = ':DoiProvider';

-- Disable email notifications (don't email real users)
UPDATE setting SET content = 'false'
WHERE name = ':SystemEmail';
```

### Security

- RDS is **not publicly accessible**
- Database only accepts connections from the EC2 instance
- All credentials managed via Terraform variables (not in code)
- Passwords stored in `.tfvars` files that are gitignored

---

## Component Version Changes

| Component | Old (5.14) | New (6.8) | Notes |
|-----------|------------|-----------|-------|
| **OS** | CentOS 7 | Rocky Linux 9 | CentOS 7 EOL was June 2024 |
| **Java** | 11 | 17 | LTS version |
| **Payara** | 5 | 6 | Major upgrade |
| **PostgreSQL** | 9.x/10.x | 16 | Via AWS RDS |
| **Solr** | 8 | 9 | New schema, requires re-index |
| **AWS S3 SDK** | v1 | v2 | Breaking config changes handled |

---

## Timeline Overview

```
Week 1: Infrastructure
├── Day 1-2: Terraform creates EC2 + RDS + S3
├── Day 3-4: Ansible deploys Dataverse 6.8
└── Day 5: Basic smoke tests with sample data

Week 2-3: Data Migration & Testing
├── Clone production database to test RDS
├── Sync production files to test S3
├── Flyway auto-upgrades schema
├── Re-index Solr
├── Full functional testing
└── Fix any issues found

Week 4: Cutover (when ready)
├── Final data sync during maintenance window
├── DNS switch to new infrastructure
├── Monitor closely for 48 hours
└── Keep old system as rollback for 1 week
```

---

## Who Does What

| Task | Responsible | Tools |
|------|-------------|-------|
| Terraform infrastructure | DevOps/Tim | Terraform CLI |
| Ansible deployment | DevOps/Tim | Ansible playbook |
| Database dump/restore | DevOps/DBA | pg_dump, psql |
| File sync | DevOps | aws s3 sync |
| Functional testing | Team | Browser, API |
| DNS cutover | IT/Networking | DNS management |
| User communication | Team Lead | Email |

---

## Questions?

Contact: Tim Dennis / UCLA Data Science Center

Reference docs:
- `docs/operations/upgrade_path_5x_to_6x.md` - Technical details
- `docs/operations/migration_guide.md` - Step-by-step runbook
- `docs/setup/environment_configuration.md` - Ansible configuration
