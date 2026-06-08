# Dataverse 5.14 → 6.8 Migration Guide

> **Current migration status is tracked in `.planning/` at the repo root** — see `ROADMAP.md` for phase progress and `PROJECT.md` for active constraints and decisions. This document is the detailed reference for cutover procedures, rollback triggers, and post-migration tasks. It will feed directly into Phase 6 (Maintenance Window Planning).

Complete migration guide for upgrading UCLA Dataverse from 5.14 to 6.8 on AWS.

**Current Production:** dataverse.ucla.edu (Dataverse 5.14)
**Target:** Dataverse 6.8 with UCLA branding
**Strategy:** Deploy fresh 6.8 instance, test thoroughly, then cutover DNS

---

## Table of Contents

- [Overview](#overview)
- [Pre-Migration Planning](#pre-migration-planning)
- [Phase 1: Elastic IP Testing (Week 1)](#phase-1-elastic-ip-testing-week-1)
- [Phase 2: Full Integration Testing (Week 2-3)](#phase-2-full-integration-testing-week-2-3)
- [Phase 3: Production Cutover (Week 4)](#phase-3-production-cutover-week-4)
- [Rollback Procedures](#rollback-procedures)
- [Post-Migration Tasks](#post-migration-tasks)

---

## Overview

### Migration Approach

We're using a **parallel deployment strategy** rather than in-place upgrade:

1. ✅ Deploy new 6.8 instance on separate EC2
2. ✅ Test thoroughly with production data clone
3. ✅ Switch DNS to new instance when ready
4. ✅ Keep old 5.14 instance as rollback option

### Why This Approach?

- **Safety:** Can rollback instantly by switching DNS back
- **Testing:** Full testing without affecting production
- **Flexibility:** Test as long as needed before cutover
- **Reduced downtime:** Pre-warm new instance, DNS switch is quick

### Major Changes: 5.14 → 6.8

**Application Server:** Payara 5 → Payara 6
**PostgreSQL:** Likely older version → 16
**Solr:** Older version → 9.8.0
**Java:** 11 → 17
**Schema changes:** ~30+ database migrations
**API changes:** Review breaking changes in release notes

---

## Pre-Migration Planning

### ☐ Information Gathering

Collect this information from current production (dataverse.ucla.edu):

#### Current Production Details

```bash
# SSH to current production
ssh production-5.14-server

# Get current versions
cat /usr/local/payara5/glassfish/domains/domain1/applications/dataverse/WEB-INF/classes/BuildNumber.properties
psql --version
java -version

# Get current configuration
sudo /usr/local/payara5/bin/asadmin list-jvm-options | grep dataverse
sudo /usr/local/payara5/bin/asadmin get server.network-config.network-listeners.network-listener.http-listener-1.port

# Database size and statistics
sudo -u postgres psql -d dvndb -c "SELECT pg_size_pretty(pg_database_size('dvndb'));"
sudo -u postgres psql -d dvndb -c "SELECT schemaVersion FROM _dvobject LIMIT 1;"
sudo -u postgres psql -d dvndb -c "SELECT COUNT(*) FROM dvobject WHERE dtype='Dataverse';" # Collections
sudo -u postgres psql -d dvndb -c "SELECT COUNT(*) FROM dvobject WHERE dtype='Dataset';" # Datasets
sudo -u postgres psql -d dvndb -c "SELECT COUNT(*) FROM dvobject WHERE dtype='DataFile';" # Files

# File storage size
sudo du -sh /usr/local/dvn/data/

# Current settings
curl http://localhost:8080/api/admin/settings | jq '.' > current-settings.json
```

**Document:**
- [ ] Current Dataverse version: __________
- [ ] Current Payara version: __________
- [ ] Current PostgreSQL version: __________
- [ ] Database size: __________
- [ ] File storage size: __________
- [ ] Number of collections: __________
- [ ] Number of datasets: __________
- [ ] Number of files: __________
- [ ] DOI authority: __________
- [ ] DOI provider (DataCite/EZID): __________

#### AWS Resources Needed

- [ ] **New EC2 Instance**
  - AMI: Rocky Linux 9
  - Instance type: __________ (match or exceed current)
  - Root volume: __________ GB (2x current database + file storage size)
  - Elastic IP: Allocated
  - Security groups: Configured (22, 80, 443)

- [ ] **DNS Options** (choose one):
  - [ ] Option A: Use Elastic IP only (can't test SSL)
  - [ ] Option B: Point test.dataverse.ucla.edu to new EC2 (best option)
  - [ ] Option C: Buy cheap test domain: __________

- [ ] **Credentials**
  - [ ] UCLA DOI credentials (DataCite or EZID)
  - [ ] SMTP relay information
  - [ ] SSH key pair (.pem file)

#### Team Coordination

- [ ] Schedule weekly sync meetings
- [ ] Identify stakeholders to notify
- [ ] Document current user workflows to test
- [ ] Create communication plan for cutover
- [ ] Define success criteria

---

## Phase 1: Elastic IP Testing (Week 1)

**Goal:** Validate basic 6.8 installation and UCLA branding with fresh instance
**Domain:** Use Elastic IP only (e.g., http://54.123.45.67)
**SSL:** Disabled (can't get cert for IP address)

### Day 1: Deploy Fresh 6.8 Instance

#### 1.1 Launch EC2 Instance

```bash
# From AWS Console:
# - Rocky Linux 9 AMI
# - Instance type: t3.medium minimum
# - 50GB+ root volume
# - Security group: SSH (22), HTTP (80), HTTPS (443)
# - Allocate and associate Elastic IP
```

Document your instance:
- [ ] EC2 Instance ID: __________
- [ ] Elastic IP: __________
- [ ] Private IP: __________

#### 1.2 Configure Ansible Inventory

Create `inventory/phase1-elastic-ip.yml`:

```yaml
---
all:
  children:
    phase1:
      hosts:
        dataverse-phase1:
          ansible_host: 54.123.45.67  # Your Elastic IP
          ansible_user: rocky  # Or ec2-user for RHEL
          ansible_ssh_private_key_file: ~/.ssh/dataverse.pem
          ansible_ssh_common_args: '-o StrictHostKeyChecking=no'
          ansible_python_interpreter: /usr/bin/python3

      vars:
        ansible_become: yes
        ansible_become_method: sudo
```

#### 1.3 Configure Group Variables

Create `group_vars/phase1.yml`:

```yaml
---
# PHASE 1: Elastic IP Testing (NO SSL, NO DOI)

dataverse:
  adminpass: "TEMP_ADMIN_PASS_123!"  # Change after cutover
  allow_signups: true  # For testing

  payara:
    # CRITICAL: Full dict required (see TROUBLESHOOTING.md)
    user: dataverse
    group: dataverse
    domain: domain1
    logformat: ulf
    adminuser: admin
    adminpass: notPr0d
    siteurl: "http://54.123.45.67"  # Your Elastic IP
    listen_address: 127.0.0.1  # Behind Apache
    launch_timeout: 180
    request_timeout: 1800
    root: /usr/local
    dir: payara6
    zipurl: https://nexus.payara.fish/repository/payara-community/fish/payara/distributions/payara/6.2025.3/payara-6.2025.3.zip
    zipchecksum: sha256:88f5c1e5b40ea4bc60ae3e34e6858c1b33145dc06c4b05c3d318ed67c131e210

  service_email: noreply@test-migration.ucla.edu
  smtp: localhost  # Local delivery only for testing

  pid:
    protocol: doi
    authority: "10.5072"  # Test/fake DOI prefix
    shoulder: "FK2/"

  doi:
    provider: FAKE  # Don't mint real DOIs yet
    baseurl: "https://mds.test.datacite.org/"
    username: "testaccount"
    password: "notused"

  branding:
    enabled: true  # UCLA branding will deploy automatically

  sampledata:
    enabled: true  # Deploy sample data for testing
    use_api: true

apache:
  ssl:
    enabled: false  # Can't get cert for IP address
  port: 80

db:
  postgres:
    enabled: true
    adminpass: "TEMP_DB_ADMIN_PASS"
    name: dvndb
    host: localhost
    user: dvnuser
    pass: "TEMP_DB_PASS"
    version: 16
    port: 5432
```

#### 1.4 Test Connection

```bash
# Test SSH connection
ssh -i ~/.ssh/dataverse.pem rocky@54.123.45.67

# Test Ansible connection
ansible all -i inventory/phase1-elastic-ip.yml -m ping
```

Expected output:
```
dataverse-phase1 | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

#### 1.5 Deploy Dataverse 6.8

```bash
# From your local machine
cd ~/websites/dataverse-ansible
git checkout develop
git pull origin develop

# Ensure dependencies are current
make bootstrap

# Deploy!
ansible-playbook -i inventory/phase1-elastic-ip.yml site.yml

# This will take 20-30 minutes
```

**Monitor deployment:**
```bash
# In another terminal, monitor progress
ssh -i ~/.ssh/dataverse.pem rocky@54.123.45.67
sudo tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log
```

### Day 2: Validate Fresh Installation

#### 2.1 Service Health Checks

```bash
# Check all services via Ansible
ansible all -i inventory/phase1-elastic-ip.yml -a "systemctl status payara postgresql-16 solr httpd"

# Or SSH directly
ssh -i ~/.ssh/dataverse.pem rocky@54.123.45.67

sudo systemctl status payara
sudo systemctl status postgresql-16
sudo systemctl status solr
sudo systemctl status httpd
```

All should show **active (running)** in green.

#### 2.2 API Checks

```bash
# From your local machine
export ELASTIC_IP="54.123.45.67"

# Version endpoint
curl http://$ELASTIC_IP/api/info/version
# Should return: {"status":"OK","data":{"version":"6.8",...}}

# Server info
curl http://$ELASTIC_IP/api/info/server
# Should return server details

# Sample data check (if enabled)
curl http://$ELASTIC_IP/api/dataverses/ucla-dsc
# Should return UCLA Data Science Center collection
```

#### 2.3 UCLA Branding Verification

Open browser: `http://54.123.45.67`

**Checklist:**
- [ ] UCLA Library header displays
- [ ] UCLA Dataverse logo visible in header
- [ ] UCLA-themed homepage loads
- [ ] UCLA favicon shows (blue 2-ring icon)
- [ ] Footer shows UCLA Library links and social media
- [ ] "Support" link opens UCLA Jira portal
- [ ] Icon colors are UCLA blue (not burnt orange)

#### 2.4 Functional Testing

**Test basic workflows:**

1. **Login**
   - [ ] Log in as dataverseAdmin (password from group_vars)
   - [ ] Can access admin dashboard

2. **Create Collection**
   - [ ] Create new dataverse collection
   - [ ] Verify metadata blocks available:
     - [ ] Citation (default)
     - [ ] Geospatial
     - [ ] Social Science
     - [ ] Astrophysics
     - [ ] Biomedical
     - [ ] Journals
     - [ ] CodeMeta
     - [ ] HELADA (UCLA custom)

3. **Create Dataset**
   - [ ] Create test dataset
   - [ ] Add metadata
   - [ ] Upload test file (try different sizes: 1MB, 100MB, 1GB)
   - [ ] Publish dataset
   - [ ] Verify DOI minted (will be fake/test DOI)

4. **Search & Discovery**
   - [ ] Search for datasets
   - [ ] Browse collections
   - [ ] Filter by facets

5. **Language Selection**
   - [ ] Switch to Spanish
   - [ ] Switch to Chinese
   - [ ] Switch to Japanese
   - [ ] Switch to Korean
   - [ ] Verify UI translates

### Day 3-5: Document Issues & Test Edge Cases

**Create testing spreadsheet tracking:**
- [ ] Feature tested
- [ ] Expected behavior
- [ ] Actual behavior
- [ ] Pass/Fail
- [ ] Notes/issues

**Test edge cases:**
- [ ] Large file uploads (>1GB)
- [ ] Special characters in metadata
- [ ] Embargo/restricted datasets
- [ ] Guest user access
- [ ] Dataset versioning
- [ ] File replacement

**Known 6.8 changes to verify:**
- Review: https://github.com/IQSS/dataverse/releases/tag/v6.8
- Test any features you currently use that changed

### Phase 1 Deliverables

- [ ] Fresh 6.8 instance running successfully
- [ ] UCLA branding validated
- [ ] Basic functionality tested and documented
- [ ] Issue list compiled
- [ ] Decision: proceed to Phase 2 or address issues

---

## Phase 2: Full Integration Testing (Week 2-3)

**Goal:** Test with production data clone, SSL, and proper domain
**Domain:** test.dataverse.ucla.edu (or cheap test domain)
**SSL:** Enabled with Let's Encrypt
**Data:** Clone of production database and files

### Prerequisites

Before starting Phase 2, you need:

- [ ] **Domain configured** (choose one):
  - [ ] IT updates test.dataverse.ucla.edu → Elastic IP (preferred)
  - [ ] Purchase test domain (e.g., ucla-dataverse-test.com) and configure DNS
- [ ] **Production backup** created and accessible
- [ ] **Phase 1 issues** resolved or documented as known limitations

### Week 2 Day 1: Domain & SSL Configuration

#### 2.1 Update DNS

**Option A: test.dataverse.ucla.edu**

Submit IT ticket to update DNS:
```
Hostname: test.dataverse.ucla.edu
Type: A
Value: 54.123.45.67 (your Elastic IP)
TTL: 300 (5 minutes, for faster testing)
```

**Option B: Cheap test domain**

At your domain registrar (Namecheap, Google Domains, etc.):
```
@ (root)    A    54.123.45.67    300
www         A    54.123.45.67    300
```

**Verify DNS propagation:**
```bash
dig test.dataverse.ucla.edu +short
# Should return: 54.123.45.67

# Or
nslookup test.dataverse.ucla.edu
```

#### 2.2 Update Configuration for SSL

Update `group_vars/phase2.yml`:

```yaml
---
# PHASE 2: Full Integration Testing with SSL

dataverse:
  payara:
    siteurl: "https://test.dataverse.ucla.edu"  # HTTPS with proper domain
    # ... rest of payara config same as phase1 ...

  service_email: noreply@test.dataverse.ucla.edu
  smtp: smtp.ucla.edu  # Use real UCLA SMTP relay

  pid:
    protocol: doi
    authority: "10.XXXXX"  # Your UCLA TEST DOI prefix
    shoulder: "FK2/"

  doi:
    provider: datacite  # Use DataCite test API
    baseurl: "https://mds.test.datacite.org/"
    dataciterestapiurl: "https://api.test.datacite.org"
    username: "UCLA_DATACITE_TEST_USERNAME"
    password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          ... # Encrypt with ansible-vault encrypt_string

apache:
  ssl:
    enabled: true
  public_fqdn: test.dataverse.ucla.edu

letsencrypt:
  enabled: true
  certbot:
    email: "your-email@ucla.edu"
    test_cert: false  # Use real certs
    autorenew: true
```

Create inventory `inventory/phase2-ssl.yml`:

```yaml
---
all:
  children:
    phase2:
      hosts:
        dataverse-phase2:
          ansible_host: test.dataverse.ucla.edu  # Use domain now
          ansible_user: rocky
          ansible_ssh_private_key_file: ~/.ssh/dataverse.pem
          ansible_python_interpreter: /usr/bin/python3

      vars:
        ansible_become: yes
```

#### 2.3 Re-deploy with SSL

```bash
# Encrypt DOI password
ansible-vault encrypt_string 'YOUR_DATACITE_TEST_PASSWORD' --name 'dataverse_doi_password'

# Add to group_vars/phase2.yml

# Deploy with SSL
ansible-playbook -i inventory/phase2-ssl.yml site.yml --ask-vault-pass
```

#### 2.4 Verify SSL

```bash
# Check cert
curl -I https://test.dataverse.ucla.edu

# Should show:
# HTTP/2 200
# server: Apache/2.4.x

# Check cert details
openssl s_client -connect test.dataverse.ucla.edu:443 -servername test.dataverse.ucla.edu < /dev/null | grep "Verify return code"
# Should show: Verify return code: 0 (ok)
```

Open browser: `https://test.dataverse.ucla.edu`
- [ ] HTTPS works with valid certificate (green padlock)
- [ ] No certificate warnings

### Week 2 Day 2-3: Clone Production Data

**WARNING:** This step requires production database access and coordination with your DBA/team.

#### 2.5 Backup Production Database

On current production (5.14):

```bash
# Create dump directory
sudo mkdir -p /backup/migration
sudo chown postgres:postgres /backup/migration

# Create database dump
sudo -u postgres pg_dump dvndb -Fc -f /backup/migration/dvndb-5.14-$(date +%Y%m%d).dump

# Verify backup
ls -lh /backup/migration/
# Should show file size matching your database size

# Create plain text backup too (for inspection)
sudo -u postgres pg_dump dvndb -f /backup/migration/dvndb-5.14-$(date +%Y%m%d).sql
```

#### 2.6 Transfer Database to Phase 2 Instance

```bash
# From production server
scp /backup/migration/dvndb-5.14-*.dump rocky@54.123.45.67:/tmp/

# Or use S3 as intermediary
aws s3 cp /backup/migration/dvndb-5.14-*.dump s3://ucla-dataverse-migration/

# Then on phase2 instance
aws s3 cp s3://ucla-dataverse-migration/dvndb-5.14-*.dump /tmp/
```

#### 2.7 Restore to Phase 2 Instance

On phase 2 instance (6.8):

```bash
# SSH to phase2
ssh -i ~/.ssh/dataverse.pem rocky@test.dataverse.ucla.edu

# Stop Payara
sudo systemctl stop payara

# Drop existing database and recreate
sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS dvndb;
CREATE DATABASE dvndb OWNER dvnuser;
\c dvndb
CREATE EXTENSION IF NOT EXISTS pg_trgm;
EOF

# Restore the 5.14 backup
sudo -u postgres pg_restore -d dvndb /tmp/dvndb-5.14-*.dump

# Start Payara (will auto-upgrade schema from 5.14 → 6.8)
sudo systemctl start payara

# Monitor upgrade in logs
sudo tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log
# Look for: "Database schema is being updated..."
# This may take 5-30 minutes depending on data size
```

**Expected log messages during schema upgrade:**
```
INFO: Database schema is being updated...
INFO: Running migration script: upgrade_v5.14_to_v6.0.sql
INFO: Running migration script: upgrade_v6.0_to_v6.1.sql
...
INFO: Running migration script: upgrade_v6.7_to_v6.8.sql
INFO: Database schema update complete. Current version: 6.8
```

#### 2.8 Verify Database Migration

```bash
# Check current schema version
sudo -u postgres psql -d dvndb -c "SELECT value FROM setting WHERE name='DbVersion';"
# Should return: 6.8

# Check object counts match production
sudo -u postgres psql -d dvndb << EOF
SELECT
  COUNT(CASE WHEN dtype='Dataverse' THEN 1 END) as collections,
  COUNT(CASE WHEN dtype='Dataset' THEN 1 END) as datasets,
  COUNT(CASE WHEN dtype='DataFile' THEN 1 END) as files
FROM dvobject;
EOF

# Compare to production counts documented in pre-migration checklist
```

### Week 2 Day 4-5: File Storage Migration

#### 2.9 Backup Production Files

On production (5.14):

```bash
# Create tarball of file storage
sudo tar -czf /backup/migration/dvn-data-$(date +%Y%m%d).tar.gz /usr/local/dvn/data/

# Or use rsync for incremental (faster for large datasets)
# To S3:
aws s3 sync /usr/local/dvn/data/ s3://ucla-dataverse-migration/data/

# Check size
du -sh /usr/local/dvn/data/
```

#### 2.10 Transfer Files to Phase 2

**Option A: Direct rsync (if instances can communicate):**
```bash
# From production to phase2
sudo rsync -avz --progress /usr/local/dvn/data/ rocky@54.123.45.67:/usr/local/dvn/data/
```

**Option B: Via S3 (recommended for large datasets):**
```bash
# Already uploaded in 2.9, now download on phase2:
ssh rocky@test.dataverse.ucla.edu

sudo mkdir -p /usr/local/dvn/data
sudo chown dataverse:dataverse /usr/local/dvn/data

# Download from S3
sudo -u dataverse aws s3 sync s3://ucla-dataverse-migration/data/ /usr/local/dvn/data/
```

#### 2.11 Verify File Migration

```bash
# On phase2 instance
# Check file count
sudo find /usr/local/dvn/data -type f | wc -l

# Check total size
sudo du -sh /usr/local/dvn/data

# Restart Payara to pick up files
sudo systemctl restart payara

# Verify a few datasets can display files
curl https://test.dataverse.ucla.edu/api/datasets/:persistentId?persistentId=doi:10.XXXXX/YYY
```

### Week 3: Comprehensive Testing with Production Data

#### 2.12 Test All Core Functionality

**Dataset Access:**
- [ ] Can view published datasets
- [ ] Can download files from datasets
- [ ] File previews work (if enabled)
- [ ] Citations display correctly
- [ ] DOI links work

**Search & Discovery:**
- [ ] Search returns expected results
- [ ] Facets work correctly
- [ ] Browse collections matches production
- [ ] Sorting works

**User Accounts:**
- [ ] Existing users can log in (if not using Shibboleth yet)
- [ ] User permissions preserved (can edit own datasets)
- [ ] Admin users have correct permissions

**Metadata:**
- [ ] All metadata blocks display correctly
- [ ] Custom metadata preserved
- [ ] Citation formats correct

**API:**
- [ ] Test API endpoints used by your applications
- [ ] Verify API tokens work
- [ ] Test SWORD API if used

#### 2.13 Test DOI Minting (with test authority)

Create a new dataset and publish:

```bash
# Via UI or API
curl -X POST https://test.dataverse.ucla.edu/api/dataverses/root/datasets \
  -H "X-Dataverse-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @test-dataset.json

# Publish it
curl -X POST "https://test.dataverse.ucla.edu/api/datasets/:persistentId/actions/:publish?persistentId=doi:10.XXXXX/TEST&type=major" \
  -H "X-Dataverse-key: YOUR_API_KEY"

# Verify DOI was minted at DataCite test
# Check: https://mds.test.datacite.org/metadata/10.XXXXX/TEST
```

**Checklist:**
- [ ] DOI minted successfully
- [ ] DOI metadata sent to DataCite
- [ ] DOI resolves (may take a few minutes)
- [ ] DOI landing page shows correct information

#### 2.14 Load Testing

If your production site has significant traffic:

```bash
# Install Apache Bench
sudo dnf install httpd-tools -y

# Simple load test
ab -n 1000 -c 10 https://test.dataverse.ucla.edu/

# Monitor during test
ssh rocky@test.dataverse.ucla.edu
htop  # Watch CPU/memory usage
sudo tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log
```

**Record results:**
- [ ] Requests per second: __________
- [ ] Average response time: __________
- [ ] Any errors: __________
- [ ] CPU usage: __________
- [ ] Memory usage: __________

#### 2.15 Backup & Restore Testing

Test your backup procedures on the phase 2 instance:

```bash
# Create backup
sudo -u postgres pg_dump dvndb -Fc -f /tmp/test-backup.dump
sudo tar -czf /tmp/test-files.tar.gz /usr/local/dvn/data

# Simulate restore (optional - creates downtime)
sudo systemctl stop payara
sudo -u postgres dropdb dvndb
sudo -u postgres createdb dvndb -O dvnuser
sudo -u postgres pg_restore -d dvndb /tmp/test-backup.dump
sudo systemctl start payara
```

**Document:**
- [ ] Backup time: __________
- [ ] Backup size: __________
- [ ] Restore time: __________
- [ ] Restore successful: Yes/No

### Phase 2 Deliverables

- [ ] SSL working with proper domain
- [ ] Production data migrated (database + files)
- [ ] Schema upgraded successfully (5.14 → 6.8)
- [ ] All datasets accessible
- [ ] DOI minting tested with test authority
- [ ] Load testing completed
- [ ] Backup/restore procedures validated
- [ ] Issue list updated
- [ ] Go/No-go decision for Phase 3

---

## Phase 3: Production Cutover (Week 4)

**Goal:** Switch production traffic to new 6.8 instance
**Risk Level:** HIGH - Coordinate carefully
**Duration:** 2-4 hours (plan for 4 hour maintenance window)

### Pre-Cutover Requirements

All must be checked before proceeding:

- [ ] Phase 2 testing complete and documented
- [ ] All critical issues resolved
- [ ] Stakeholders notified of cutover date/time
- [ ] Maintenance window scheduled (off-peak hours)
- [ ] Team members identified and available
- [ ] Rollback plan reviewed and understood
- [ ] Emergency contacts documented

### Cutover Timeline

**Recommended:** Saturday 6:00 AM - 10:00 AM Pacific (low traffic period)

#### T-24 hours: Final Preparation

- [ ] Announce maintenance window to users
- [ ] Post banner on current site about upcoming maintenance
- [ ] Create fresh production backup
- [ ] Review cutover checklist with team
- [ ] Verify all credentials available

#### T-2 hours: Pre-Cutover Tasks

1. **Create final production backup:**

```bash
# On production 5.14
BACKUP_DATE=$(date +%Y%m%d-%H%M)

# Database
sudo -u postgres pg_dump dvndb -Fc -f /backup/final-production-$BACKUP_DATE.dump

# Files
sudo rsync -avz /usr/local/dvn/data/ /backup/final-files-$BACKUP_DATE/

# Verify backups
ls -lh /backup/final-*
```

2. **Document current production state:**

```bash
# Current version
curl http://localhost:8080/api/info/version > /tmp/pre-cutover-version.json

# Dataset counts
sudo -u postgres psql -d dvndb -c "
  SELECT
    COUNT(CASE WHEN dtype='Dataverse' THEN 1 END) as collections,
    COUNT(CASE WHEN dtype='Dataset' THEN 1 END) as datasets,
    COUNT(CASE WHEN dtype='DataFile' THEN 1 END) as files
  FROM dvobject;
" > /tmp/pre-cutover-counts.txt

# Last dataset created
sudo -u postgres psql -d dvndb -c "
  SELECT id, identifier, createdate
  FROM dvobject
  WHERE dtype='Dataset'
  ORDER BY createdate DESC
  LIMIT 5;
" > /tmp/pre-cutover-last-datasets.txt
```

#### T-0: Begin Maintenance

**🚨 CUTOVER STARTS HERE 🚨**

##### Step 1: Put production site in maintenance mode (T+0 min)

On production 5.14:

```bash
# Create maintenance page
cat > /var/www/html/maintenance.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>UCLA Dataverse - Scheduled Maintenance</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        h1 { color: #2774AE; }
    </style>
</head>
<body>
    <h1>Scheduled Maintenance</h1>
    <p>UCLA Dataverse is currently undergoing scheduled maintenance.</p>
    <p>We expect to be back online by 10:00 AM Pacific.</p>
    <p>We apologize for any inconvenience.</p>
</body>
</html>
EOF

# Configure Apache to show maintenance page
sudo tee /etc/httpd/conf.d/maintenance.conf << 'EOF'
RewriteEngine On
RewriteCond %{REQUEST_URI} !^/maintenance.html$
RewriteRule ^(.*)$ /maintenance.html [R=503,L]
ErrorDocument 503 /maintenance.html
Header always set Retry-After "3600"
EOF

# Reload Apache
sudo systemctl reload httpd

# Stop Payara to prevent new data
sudo systemctl stop payara
```

**Verify maintenance mode:**
```bash
curl http://dataverse.ucla.edu
# Should show maintenance page
```

##### Step 2: Sync final data to Phase 2 instance (T+5 min)

```bash
# On production 5.14
# Incremental database sync (capture any last-minute changes)
sudo -u postgres pg_dump dvndb -Fc -f /tmp/final-sync-$BACKUP_DATE.dump
scp /tmp/final-sync-$BACKUP_DATE.dump rocky@test.dataverse.ucla.edu:/tmp/

# Incremental file sync
sudo rsync -avz --delete /usr/local/dvn/data/ rocky@test.dataverse.ucla.edu:/usr/local/dvn/data/
```

##### Step 3: Restore final data on 6.8 instance (T+20 min)

On phase 2 instance:

```bash
# SSH to phase2
ssh rocky@test.dataverse.ucla.edu

# Stop Payara
sudo systemctl stop payara

# Restore final database state
sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS dvndb;
CREATE DATABASE dvndb OWNER dvnuser;
\c dvndb
CREATE EXTENSION pg_trgm;
EOF

sudo -u postgres pg_restore -d dvndb /tmp/final-sync-*.dump

# Ensure files are in place (already synced via rsync)
sudo chown -R dataverse:dataverse /usr/local/dvn/data

# Start Payara (will complete any schema upgrades)
sudo systemctl start payara

# Monitor startup
sudo tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log
# Wait for: "Dataverse started successfully"
```

##### Step 4: Final validation on 6.8 instance (T+40 min)

```bash
# Health checks
curl https://test.dataverse.ucla.edu/api/info/version
curl https://test.dataverse.ucla.edu/api/info/server

# Verify dataset counts
sudo -u postgres psql -d dvndb -c "
  SELECT
    COUNT(CASE WHEN dtype='Dataverse' THEN 1 END) as collections,
    COUNT(CASE WHEN dtype='Dataset' THEN 1 END) as datasets,
    COUNT(CASE WHEN dtype='DataFile' THEN 1 END) as files
  FROM dvobject;
"
# Compare to pre-cutover counts
```

**Checklist:**
- [ ] All services running
- [ ] API responding correctly
- [ ] Dataset counts match production
- [ ] Can view datasets via UI
- [ ] Can download files
- [ ] Search works

##### Step 5: Update production configuration (T+60 min)

Update `group_vars/production.yml`:

```yaml
---
# PRODUCTION: dataverse.ucla.edu

dataverse:
  adminpass: !vault |...  # Use REAL production password
  allow_signups: false  # Disable for production

  payara:
    siteurl: "https://dataverse.ucla.edu"  # Production domain
    # ... full payara config ...

  service_email: noreply@dataverse.ucla.edu
  smtp: smtp.ucla.edu  # UCLA SMTP relay

  pid:
    protocol: doi
    authority: "10.XXXXX"  # UCLA PRODUCTION DOI prefix
    shoulder: ""

  doi:
    provider: datacite  # Or ezid
    baseurl: "https://mds.datacite.org/"  # PRODUCTION DataCite
    dataciterestapiurl: "https://api.datacite.org"
    username: "UCLA_DATACITE_PRODUCTION"
    password: !vault |...  # PRODUCTION credentials

apache:
  ssl:
    enabled: true
  public_fqdn: dataverse.ucla.edu
  block:
    admin: true  # Block /api/admin from public
    builtin_users: true
    destroy: true

letsencrypt:
  enabled: true
  certbot:
    email: "admin@ucla.edu"
    test_cert: false
```

Create inventory `inventory/production.yml`:

```yaml
---
all:
  children:
    production:
      hosts:
        dataverse-production:
          ansible_host: 54.123.45.67  # Same Elastic IP
          ansible_user: rocky
          ansible_ssh_private_key_file: ~/.ssh/dataverse.pem

      vars:
        ansible_become: yes
```

##### Step 6: Deploy production configuration (T+70 min)

```bash
# From local machine
ansible-playbook -i inventory/production.yml site.yml --ask-vault-pass --tags "dataverse-optional-settings"
# This updates settings without reinstalling everything
```

##### Step 7: Update DNS (T+90 min)

**🚨 CRITICAL STEP 🚨**

**Option A: UCLA IT controls DNS**

Submit emergency DNS change request:
```
Hostname: dataverse.ucla.edu
Type: A
Old Value: 192.168.1.100 (old production IP)
New Value: 54.123.45.67 (new EC2 Elastic IP)
TTL: 300 (temporary for testing, increase to 3600 after validation)
```

**Option B: You control DNS**

Update DNS at your provider:
```bash
# Update A record
dataverse.ucla.edu -> 54.123.45.67
TTL: 300 (5 minutes)
```

##### Step 8: Monitor DNS propagation (T+95 min)

```bash
# Check DNS
dig dataverse.ucla.edu +short
# Should return: 54.123.45.67

# Test from different locations
# Use: https://dnschecker.org/#A/dataverse.ucla.edu

# Test SSL on new domain
curl -I https://dataverse.ucla.edu
# Should show HTTPS and valid cert
```

**Wait for DNS to fully propagate** (5-15 minutes with low TTL)

##### Step 9: Acquire production SSL certificate (T+110 min)

On the 6.8 instance (now receiving traffic via dataverse.ucla.edu):

```bash
# Certbot will auto-detect domain from Apache config
sudo certbot --apache -d dataverse.ucla.edu

# Follow prompts, select redirect HTTP -> HTTPS

# Verify cert
curl -I https://dataverse.ucla.edu
# Should show valid Let's Encrypt cert for dataverse.ucla.edu
```

##### Step 10: Final production validation (T+120 min)

**From your local machine:**

```bash
# API checks
curl https://dataverse.ucla.edu/api/info/version
curl https://dataverse.ucla.edu/api/info/server

# Test dataset access (use a known DOI)
curl https://dataverse.ucla.edu/api/datasets/:persistentId?persistentId=doi:10.XXXXX/YYYY
```

**In browser:**

- [ ] Visit https://dataverse.ucla.edu
- [ ] HTTPS works with valid certificate
- [ ] UCLA branding displays
- [ ] Can browse collections
- [ ] Can search datasets
- [ ] Can download files
- [ ] Can log in as admin
- [ ] Test creating new dataset
- [ ] Test publishing dataset (mints real DOI!)

**Monitor logs:**

```bash
ssh rocky@dataverse.ucla.edu
sudo tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log
sudo tail -f /var/log/httpd/access_log
```

##### Step 11: Remove maintenance mode (T+150 min)

**Only if all validation passed!**

Old production instance is still showing maintenance page. Users hitting old IPs will still see maintenance until:
1. DNS fully propagates (5-60 min depending on ISP caching)
2. Old server is shut down

**You can optionally:**
```bash
# On old 5.14 instance
# Keep it running in maintenance mode for 24 hours as rollback option
# OR shut it down if confident
sudo systemctl stop httpd
```

##### Step 12: Announce completion (T+180 min)

- [ ] Email stakeholders: "Migration complete"
- [ ] Post announcement on website
- [ ] Update status page
- [ ] Thank team members

### Post-Cutover Monitoring (Next 24-48 hours)

#### Monitor closely:

```bash
# Watch server logs
ssh rocky@dataverse.ucla.edu
sudo journalctl -u payara -f

# Monitor resource usage
htop

# Check for errors
sudo tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log | grep ERROR
```

#### Check metrics:

- [ ] Response times normal
- [ ] No spike in errors
- [ ] DOI minting working
- [ ] File downloads working
- [ ] Search performing well
- [ ] No user complaints

#### Update DNS TTL (after 24 hours):

Once confident everything is stable:
```
dataverse.ucla.edu -> 54.123.45.67
TTL: 3600 (1 hour) or 86400 (24 hours)
```

### Phase 3 Deliverables

- [ ] Production traffic switched to 6.8 instance
- [ ] DNS updated and propagated
- [ ] SSL certificate issued for production domain
- [ ] All validation checks passed
- [ ] Users able to access site
- [ ] No critical issues
- [ ] Old instance preserved as backup (optional)

---

## Rollback Procedures

If major issues occur during Phase 3 cutover, follow this rollback plan.

### When to Rollback

Rollback if ANY of these occur:
- Database migration fails
- Critical functionality broken (can't access datasets, can't download files)
- Data loss detected
- Performance severely degraded
- Security issue discovered

### Rollback Step-by-Step

#### Option 1: DNS Rollback (Fast - 5-15 minutes)

If old 5.14 instance is still running:

1. **Revert DNS:**
```bash
# Update A record back to old server
dataverse.ucla.edu -> 192.168.1.100 (old production IP)
TTL: 300
```

2. **Remove maintenance mode on old server:**
```bash
# SSH to old 5.14 instance
sudo rm /etc/httpd/conf.d/maintenance.conf
sudo systemctl reload httpd
sudo systemctl start payara
```

3. **Verify old site works:**
```bash
curl http://dataverse.ucla.edu/api/info/version
# Should show version 5.14
```

**Downtime:** 5-15 minutes (DNS propagation)

#### Option 2: Elastic IP Reassociation (Faster - 2-5 minutes)

If you can reassociate the Elastic IP:

1. **In AWS Console:**
   - Go to EC2 → Elastic IPs
   - Find your Elastic IP
   - Actions → Disassociate
   - Actions → Associate → Select old 5.14 EC2 instance

2. **Verify old site:**
```bash
curl http://dataverse.ucla.edu/api/info/version
```

**Downtime:** 2-5 minutes (no DNS propagation needed)

### After Rollback

1. **Announce rollback:**
   - Email stakeholders
   - Post status update
   - Apologize for inconvenience

2. **Debug issues:**
   - Review logs from failed cutover
   - Identify root cause
   - Create fix plan

3. **Reschedule cutover:**
   - Fix issues
   - Test fixes on Phase 2 instance
   - Schedule new cutover date

---

## Post-Migration Tasks

After successful cutover and 24-48 hours of stable operation:

### Week 5: Cleanup & Optimization

#### 1. Decommission Old Instance

**Only after confirming 6.8 stable for 1 week:**

```bash
# On old 5.14 instance
# Create final archive
sudo tar -czf /backup/old-5.14-final-archive.tar.gz \
  /usr/local/payara5 \
  /usr/local/dvn/data \
  /etc/httpd

# Transfer archive to long-term storage
aws s3 cp /backup/old-5.14-final-archive.tar.gz s3://ucla-dataverse-archives/

# Verify archive uploaded
aws s3 ls s3://ucla-dataverse-archives/

# Stop all services
sudo systemctl stop payara httpd postgresql-* solr

# Optional: Terminate EC2 instance (keep EBS volume as snapshot for 30 days)
```

**Before terminating:**
- [ ] Final backup verified
- [ ] Archive uploaded to S3
- [ ] Team consensus on decommissioning
- [ ] No open issues related to old instance

#### 2. Update Documentation

- [ ] Update runbooks with new 6.8 procedures
- [ ] Document any configuration changes
- [ ] Update disaster recovery procedures
- [ ] Document lessons learned
- [ ] Update team wiki/documentation

#### 3. Performance Tuning

Based on monitoring data:

```yaml
# Adjust JVM heap if needed
dataverse:
  memheap: 8192  # Increase if memory usage high

# Optimize PostgreSQL
db:
  postgres:
    # Add tuning parameters in postgresql.conf
```

#### 4. Enable Additional Features

Now that 6.8 is stable, consider:

- [ ] **Shibboleth SSO** - Enable UCLA authentication
- [ ] **S3 Storage** - Migrate from local to S3
- [ ] **Make Data Count** - Enable usage metrics
- [ ] **Additional Metadata Blocks** - If needed
- [ ] **External Tools** - Integrate with other services

#### 5. Schedule Regular Maintenance

- [ ] Weekly database backups
- [ ] Monthly OS updates
- [ ] Quarterly Dataverse updates (6.8 → 6.9, etc.)
- [ ] Annual disaster recovery test

### Ongoing Monitoring

Set up monitoring/alerting for:

- [ ] **Uptime:** Service availability (Pingdom, UptimeRobot)
- [ ] **Performance:** Response times, throughput
- [ ] **Errors:** Application errors, failed requests
- [ ] **Resources:** CPU, memory, disk usage
- [ ] **Security:** Failed logins, suspicious activity
- [ ] **Backups:** Backup success/failure notifications

---

## Success Criteria

The migration is considered successful when:

- [x] All services running on 6.8
- [x] All datasets accessible
- [x] All files downloadable
- [x] Search working correctly
- [x] DOI minting functional
- [x] SSL configured and working
- [x] UCLA branding applied
- [x] No data loss detected
- [x] Performance acceptable
- [x] No critical bugs
- [x] Users able to work normally
- [x] 7 days of stable operation

---

## Communication Plan

### Pre-Migration

**T-2 weeks:**
- [ ] Email all users about upcoming migration
- [ ] Post announcement on homepage
- [ ] Update status page

**T-1 week:**
- [ ] Reminder email to users
- [ ] Banner on site about maintenance window

**T-24 hours:**
- [ ] Final reminder email
- [ ] Social media posts

### During Migration

**During maintenance window:**
- [ ] Maintenance page displayed
- [ ] Status page updated regularly
- [ ] Team communication via Slack

### Post-Migration

**T+0 (cutover complete):**
- [ ] Email announcing completion
- [ ] Remove maintenance banner
- [ ] Update status page

**T+24 hours:**
- [ ] Send status update (all good or issues encountered)

**T+1 week:**
- [ ] Thank you email to users for patience
- [ ] Summary of improvements in 6.8

---

## Contacts & Escalation

Document your team contacts:

| Role | Name | Email | Phone | Slack |
|------|------|-------|-------|-------|
| **Project Lead** | __________ | __________ | __________ | __________ |
| **DevOps** | __________ | __________ | __________ | __________ |
| **DBA** | __________ | __________ | __________ | __________ |
| **Networking/DNS** | __________ | __________ | __________ | __________ |
| **Security** | __________ | __________ | __________ | __________ |

**Escalation path:**
1. Team Slack channel: #dataverse-migration
2. Project Lead (for decisions)
3. IT Director (for major issues)

---

## References

- [AWS Deployment Guide](AWS_DEPLOYMENT.md)
- [AWS Deployment Checklist](AWS_DEPLOYMENT_CHECKLIST.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Dataverse 6.8 Release Notes](https://github.com/IQSS/dataverse/releases/tag/v6.8)
- [Dataverse Installation Guide](https://guides.dataverse.org/en/6.8/installation/)
- [Dataverse Upgrade Guide](https://guides.dataverse.org/en/6.8/admin/upgrading.html)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-24
**Maintained by:** UCLA Data Science Center
