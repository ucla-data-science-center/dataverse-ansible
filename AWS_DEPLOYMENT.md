# AWS Deployment Guide

This guide covers deploying Dataverse to AWS EC2 using Ansible playbooks.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Steps](#detailed-steps)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)

---

## Overview

This repository supports two deployment methods:

| Method | Use Case | Command |
|--------|----------|---------|
| **Molecule** | Local development/testing | `uv run molecule converge -s rocky9` |
| **Playbook** | AWS staging/production | `ansible-playbook -i inventory/staging.yml site.yml` |

This guide focuses on **playbook-based AWS deployment**.

### Architecture

```
Internet → EC2 Security Group → Apache (80/443) → Payara (8080) → PostgreSQL (5432)
                                                   ↓
                                                Solr (8983)
```

---

## Prerequisites

### 1. AWS Resources

- **EC2 Instance** running Rocky Linux 9 or RHEL 9
  - Recommended: t3.medium or larger (2+ vCPU, 4+ GB RAM)
  - Storage: 50+ GB for `/` partition
- **Security Group** with inbound rules:
  - Port 22 (SSH) from your IP
  - Port 80 (HTTP) from anywhere (0.0.0.0/0)
  - Port 443 (HTTPS) from anywhere (optional, for SSL)
- **Elastic IP** (recommended for production)
- **SSH Key Pair** (.pem file downloaded)

### 2. Local Requirements

- **Ansible** installed via `make bootstrap`
- **SSH access** to EC2 instance
- **Git** (to clone this repository)

### 3. DNS (Optional but Recommended)

- A record pointing to your EC2 Elastic IP
- Example: `staging-dataverse.ucla.edu → 54.123.45.67`

---

## Quick Start

### 1. Clone and Bootstrap

```bash
git clone https://github.com/ucla-data-science-center/dataverse-ansible.git
cd dataverse-ansible
make bootstrap
```

### 2. Configure Inventory

Edit `inventory/staging.yml`:

```yaml
ansible_host: 54.123.45.67                           # Your EC2 public IP
ansible_user: ec2-user                                # Verify for your AMI
ansible_ssh_private_key_file: ~/.ssh/dataverse.pem   # Path to your .pem file
```

### 3. Configure Variables

Edit `group_vars/staging.yml`:

```yaml
dataverse_hostname: staging-dataverse.ucla.edu
dataverse_siteurl: "http://staging-dataverse.ucla.edu"
dataverse_adminemail: "your-email@ucla.edu"
dataverse_service_email: "noreply@ucla.edu"

# IMPORTANT: Set secure passwords (use ansible-vault in production)
dataverse_adminpass: "CHANGE_ME"
dataverse_postgresql_password: "CHANGE_ME"
dataverse_postgresql_admin_password: "CHANGE_ME"
```

### 4. Test Connection

```bash
ansible all -i inventory/staging.yml -m ping
```

Expected output:
```
dataverse-staging | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

### 5. Deploy Dataverse

```bash
ansible-playbook -i inventory/staging.yml site.yml
```

This will take 15-30 minutes depending on your EC2 instance size.

### 6. Verify Deployment

```bash
# Check services
ansible all -i inventory/staging.yml -m shell -a "systemctl status payara postgresql-16 solr httpd"

# Check Dataverse API
curl http://your-ec2-ip/api/info/version
```

---

## Detailed Steps

### Step 1: Launch EC2 Instance

**Using AWS Console:**

1. Navigate to EC2 → Launch Instance
2. Choose **Rocky Linux 9** or **RHEL 9** AMI
3. Instance type: **t3.medium** (minimum)
4. Key pair: Select or create new
5. Storage: **50 GB** gp3
6. Security group: Create with rules:
   - SSH (22) from your IP
   - HTTP (80) from 0.0.0.0/0
   - HTTPS (443) from 0.0.0.0/0
7. Launch instance

**Using Terraform (Future):**

See issue #22 for planned Terraform automation.

### Step 2: Configure Inventory

The inventory file defines connection details for your EC2 instance.

**inventory/staging.yml:**

```yaml
---
all:
  children:
    staging:
      hosts:
        dataverse-staging:
          ansible_host: 54.123.45.67              # EC2 public IP or DNS
          ansible_user: ec2-user                   # rocky, ec2-user, or ubuntu
          ansible_ssh_private_key_file: ~/.ssh/dataverse.pem
          ansible_ssh_common_args: '-o StrictHostKeyChecking=no'
          ansible_python_interpreter: /usr/bin/python3

      vars:
        ansible_become: yes
        ansible_become_method: sudo
```

**AMI-Specific Users:**

| AMI | ansible_user |
|-----|--------------|
| Rocky Linux 9 | `rocky` |
| RHEL 9 | `ec2-user` |
| Amazon Linux 2023 | `ec2-user` |
| Ubuntu 22.04 | `ubuntu` |

### Step 3: Configure Environment Variables

**group_vars/staging.yml** contains all staging-specific configuration.

**Critical Variables to Update:**

```yaml
# Domain/Email
dataverse_hostname: staging-dataverse.ucla.edu
dataverse_siteurl: "http://staging-dataverse.ucla.edu"
dataverse_adminemail: "your-email@ucla.edu"
dataverse_service_email: "noreply@ucla.edu"

# Passwords (use ansible-vault for production)
dataverse_adminpass: "SecurePassword123!"
dataverse_postgresql_password: "SecureDBPassword123!"
dataverse_postgresql_admin_password: "SecureAdminPassword123!"

# DOI Provider (DataCite test for staging)
dataverse_doi_provider: datacite
dataverse_doi_authority: "10.80343"  # Your test prefix
dataverse_doi_username: "DATACITE_USERNAME"
dataverse_doi_password: "DATACITE_PASSWORD"

# JVM Sizing (adjust for your EC2 instance)
dataverse_jvm_options:
  - "-Xms2g"      # t3.medium: 2g, t3.large: 4g, t3.xlarge: 8g
  - "-Xmx4g"      # t3.medium: 4g, t3.large: 8g, t3.xlarge: 16g
  - "-XX:+UseG1GC"
```

**See `group_vars/staging.yml` for complete configuration options.**

### Step 4: Secure Sensitive Variables (Production)

For production, encrypt passwords with ansible-vault:

```bash
# Encrypt a password
ansible-vault encrypt_string 'MySecurePassword' --name 'dataverse_adminpass'

# Output (paste into group_vars/staging.yml):
dataverse_adminpass: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          66386439653236336462626566653063336164663966303231363934653561363964363833
          ...
```

Alternatively, create a separate vault file:

```bash
# Create vault file
ansible-vault create group_vars/staging-vault.yml

# Contents:
---
vault_dataverse_adminpass: "SecurePassword"
vault_postgresql_password: "SecureDBPassword"

# Reference in staging.yml:
dataverse_adminpass: "{{ vault_dataverse_adminpass }}"
dataverse_postgresql_password: "{{ vault_postgresql_password }}"
```

Deploy with vault password:

```bash
ansible-playbook -i inventory/staging.yml site.yml --ask-vault-pass
```

### Step 5: Deploy

```bash
# Dry run (check mode)
ansible-playbook -i inventory/staging.yml site.yml --check

# Full deployment
ansible-playbook -i inventory/staging.yml site.yml

# Verbose output for debugging
ansible-playbook -i inventory/staging.yml site.yml -vvv
```

**Expected Output:**

```
PLAY [Deploy Dataverse] ********************************************************

TASK [Display deployment information] ******************************************
ok: [dataverse-staging] =>
  msg: |-
    Deploying Dataverse to: dataverse-staging
    Environment: staging
    Dataverse hostname: staging-dataverse.ucla.edu

TASK [Verify required variables are set] ***************************************
ok: [dataverse-staging] => {
    "changed": false,
    "msg": "All required variables are configured."
}

PLAY RECAP *********************************************************************
dataverse-staging : ok=124  changed=67   unreachable=0    failed=0    skipped=12   rescued=0    ignored=0
```

### Step 6: Post-Deployment Verification

**Check Services:**

```bash
# Via Ansible
ansible all -i inventory/staging.yml -m shell -a "systemctl status payara postgresql-16 solr httpd"

# Or SSH directly
ssh -i ~/.ssh/dataverse.pem ec2-user@54.123.45.67
sudo systemctl status payara postgresql-16 solr httpd
```

**Check API:**

```bash
# From your local machine
curl http://staging-dataverse.ucla.edu/api/info/version

# Expected response:
{
  "status": "OK",
  "data": {
    "version": "6.8",
    "build": "..."
  }
}
```

**Access Web Interface:**

Open browser: `http://staging-dataverse.ucla.edu`

- Login with admin credentials from `group_vars/staging.yml`
- Default: `dataverseAdmin` / `<dataverse_adminpass>`

---

## Configuration

### Environment-Specific Configurations

| Environment | Inventory | Group Vars | Use Case |
|-------------|-----------|------------|----------|
| **Local** | molecule/rocky9/molecule.yml | molecule/rocky9/group_vars/molecule.yml | Development/testing |
| **Staging** | inventory/staging.yml | group_vars/staging.yml | Pre-production testing |
| **Production** | inventory/production.yml | group_vars/production.yml | Production deployment |

### Key Configuration Differences: Local vs AWS

| Setting | Local (Molecule) | AWS (Staging/Prod) |
|---------|------------------|-------------------|
| **listen_address** | `0.0.0.0` (Docker port mapping) | `127.0.0.1` (behind Apache) |
| **DOI provider** | `fake` | `datacite` (test) or `ezid` |
| **SSL** | `false` | `true` (Let's Encrypt) |
| **JVM heap** | `-Xmx2g` (dev) | `-Xmx4g+` (production) |
| **Backups** | `false` | `true` |
| **Blocked endpoints** | Testing enabled | Production locked down |

See [CONFIG_STRATEGY.md](CONFIG_STRATEGY.md) for detailed comparison.

### Payara Listen Address (IMPORTANT)

Ansible's dict merging requires specifying the **complete** `dataverse.payara` structure:

**group_vars/staging.yml:**

```yaml
dataverse:
  payara:
    user: dataverse
    group: dataverse
    domain: domain1
    logformat: ulf
    adminuser: admin
    adminpass: notPr0d
    siteurl:
    listen_address: 127.0.0.1  # ← localhost only for production
    launch_timeout: 180
    request_timeout: 1800
    root: /usr/local
    dir: payara6
    zipurl: https://nexus.payara.fish/repository/payara-community/...
    zipchecksum: sha256:88f5c1e5b40ea4bc60ae3e34e6858c1b...
```

**Why?** Partial dict merge will cause Payara to listen on wrong address. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#ansible-dict-merging-gotcha).

---

## Troubleshooting

### Connection Issues

**Problem:** `ansible all -i inventory/staging.yml -m ping` fails

**Solutions:**

```bash
# Check SSH connectivity directly
ssh -i ~/.ssh/dataverse.pem ec2-user@54.123.45.67

# Verify security group allows port 22 from your IP
# Check ansible_user matches your AMI
# Verify .pem file has correct permissions
chmod 600 ~/.ssh/dataverse.pem
```

### Deployment Failures

**Problem:** Playbook fails during deployment

**Solutions:**

```bash
# Run with verbose output
ansible-playbook -i inventory/staging.yml site.yml -vvv

# Check specific task
ansible-playbook -i inventory/staging.yml site.yml --start-at-task="Install Payara"

# Skip failing tag
ansible-playbook -i inventory/staging.yml site.yml --skip-tags solr
```

### Service Not Starting

**Problem:** Payara/PostgreSQL/Solr won't start

**Check logs:**

```bash
# Payara
sudo tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log

# PostgreSQL
sudo tail -f /var/lib/pgsql/16/data/log/postgresql-*.log

# Solr
sudo tail -f /var/log/solr/solr.log

# Apache
sudo tail -f /var/log/httpd/error_log
```

### Dataverse Not Accessible

**Problem:** Can't access Dataverse via browser

**Check:**

```bash
# Is Apache running?
sudo systemctl status httpd

# Is Payara running?
sudo systemctl status payara

# Check port 8080 locally
curl http://localhost:8080/api/info/version

# Check Apache proxy
curl http://localhost/api/info/version

# Check from outside EC2
curl http://your-ec2-public-ip/api/info/version
```

**Common causes:**
- Security group not allowing port 80
- Apache not started
- Payara listening on wrong address

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more solutions.

---

## Security Best Practices

### 1. Passwords

- ❌ **Never** commit plaintext passwords to git
- ✅ Use ansible-vault for all production passwords
- ✅ Rotate passwords regularly
- ✅ Use strong passwords (16+ chars, mixed case, numbers, symbols)

### 2. SSH Access

- ✅ Use SSH key authentication (not passwords)
- ✅ Restrict security group port 22 to your IP only
- ✅ Consider using bastion host for production
- ✅ Disable root login: `PermitRootLogin no` in `/etc/ssh/sshd_config`

### 3. Firewall

```bash
# Configure firewalld on EC2 instance
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# Block direct Payara access from outside
# (Payara listens on 127.0.0.1 only, Apache proxies)
```

### 4. SSL/TLS

Enable Let's Encrypt (see issue #13):

```yaml
# group_vars/staging.yml
dataverse_use_ssl: true
letsencrypt:
  enabled: true
  email: "admin@ucla.edu"
  staging: false  # Use true for testing
```

### 5. Blocked Endpoints

Apache blocks sensitive endpoints by default:

```yaml
apache:
  block:
    admin: true          # /api/admin
    destroy: true        # /api/datasets/*/destroy
    builtin_users: true  # /api/builtin-users
    sword: true          # /api/sword
```

Verify blocking:

```bash
# Should return 302 (blocked)
curl -I http://your-domain/api/admin
curl -I http://your-domain/api/builtin-users
```

### 6. PostgreSQL

- ✅ Use strong database passwords
- ✅ Enable backups (configured by default)
- ✅ PostgreSQL listens on localhost only (default)
- ✅ Consider AWS RDS for production

### 7. Updates

```bash
# Keep OS packages updated
sudo dnf update -y

# Monitor Dataverse security advisories
# https://github.com/IQSS/dataverse/security/advisories
```

---

## Next Steps

After successful deployment:

1. **Configure SSL** - See issue #13 for Let's Encrypt setup
2. **Enable SSO** - See issue #11 for Shibboleth integration
3. **Set up monitoring** - CloudWatch, Datadog, or Prometheus
4. **Configure backups** - Database and file storage
5. **Load test** - Verify performance under load
6. **Document runbook** - Instance-specific procedures

---

## Additional Resources

- **Local Testing:** [MOLECULE_QUICK_REF.md](MOLECULE_QUICK_REF.md)
- **Configuration Strategy:** [CONFIG_STRATEGY.md](CONFIG_STRATEGY.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Team Guide:** [TEAM_GUIDE.md](TEAM_GUIDE.md)
- **Dataverse Guides:** https://guides.dataverse.org/
- **AWS Documentation:** https://docs.aws.amazon.com/ec2/

---

**Questions?** Open an issue: https://github.com/ucla-data-science-center/dataverse-ansible/issues
