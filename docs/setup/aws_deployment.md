# Dataverse Deployment Guide

This guide walks through deploying Dataverse to AWS using Terraform and Ansible.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Domain name** configured (e.g., `yourdomain.com`)
3. **Local tools installed**:
   - Terraform
   - Ansible
   - Python 3.11+ with uv
   - SSH key pair for EC2 access

## Step 1: Provision AWS Infrastructure with Terraform

### 1.1 Update Terraform Variables

Edit `/path/to/terraform-dataverse/variables.tf`:

```hcl
variable "ssh_cidr" {
  default     = "YOUR_IP_ADDRESS/32"  # Your IP or VPN IP
}

variable "environment" {
  default     = "staging"  # or "production"
}

variable "instance_type" {
  default     = "t3.large"  # Adjust based on needs
}
```

### 1.2 Deploy Infrastructure

```bash
cd /path/to/terraform-dataverse

# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply (creates EC2 instance, security groups, Elastic IP)
terraform apply
```

**Note the Elastic IP** from the output - you'll need this for DNS configuration.

### 1.3 Capture Terraform Outputs

After `terraform apply` finishes, you will see outputs like:

```hcl
Outputs:

ansible_inventory_path = "./inventory-staging.yml"
dataverse_alerts_sns_topic_arn = "arn:aws:sns:us-west-2:123456789012:dataverse-alerts-staging"
instance_public_dns = "ec2-54-123-45-67.us-west-2.compute.amazonaws.com"
instance_public_ip = "54.123.45.67"
```

**Required Actions:**
1.  **Copy `instance_public_ip`**: You will use this in your Ansible inventory (`ansible_host`).
2.  **Copy `dataverse_alerts_sns_topic_arn`**: If configuring CloudWatch, put this in `group_vars`.

> **⚠️ Team Collaboration Note (Terraform State):**
> Terraform stores the state of your infrastructure in a local file named `terraform.tfstate`.
> *   **Do NOT commit this file to Git** (it contains secrets).
> *   **If collaborating:** You must share this file securely or migrate to a remote backend (like AWS S3) so everyone sees the same infrastructure state. Otherwise, running Terraform from another machine might destroy/recreate resources.

### 1.4 Configure DNS

In your DNS provider (e.g., Squarespace, Route53, Cloudflare):

1. Create an A record:
   - Name: `staging` (or subdomain of choice)
   - Type: `A`
   - Value: `ELASTIC_IP_FROM_TERRAFORM`
   - TTL: `300` (5 minutes)

2. Wait for DNS propagation (verify with `nslookup staging.yourdomain.com`)

## Step 2: Configure Ansible Inventory

### 2.1 Create Inventory File

Create `inventory/your_environment.yml`:

```yaml
all:
  hosts:
    dataverse-your-env:
      ansible_host: YOUR_ELASTIC_IP
      ansible_user: rocky  # or ec2-user for Amazon Linux
      ansible_ssh_private_key_file: ~/.ssh/your-key.pem
      ansible_python_interpreter: /usr/bin/python3
```

### 2.2 Create Group Variables

Create or copy `group_vars/your_environment.yml` from `group_vars/staging.yml`:

**Key variables to update:**

```yaml
# Domain configuration
dataverse_hostname: your-subdomain.yourdomain.com
dataverse_siteurl: "https://your-subdomain.yourdomain.com"

# Apache configuration
apache:
  public_fqdn: "your-subdomain.yourdomain.com"  # REQUIRED
  ssl:
    enabled: false  # Start with false for Stage 1

# Let's Encrypt
letsencrypt:
  enabled: false  # Start with false for Stage 1
  certbot:
    email: "your-email@yourdomain.com"

# Email configuration
dataverse_adminemail: "admin@yourdomain.com"
dataverse_service_email: "noreply@yourdomain.com"
dataverse_system_email: "noreply@yourdomain.com"

# SMTP (update with your mail server)
dataverse_smtp_host: smtp.yourdomain.com
dataverse_smtp_port: 587

# Payara
dataverse:
  payara:
    siteurl: "https://your-subdomain.yourdomain.com"  # REQUIRED
```

**Security-sensitive variables** (use ansible-vault):

```yaml
dataverse_adminpass: "CHANGE_ME"
dataverse_postgresql_password: "CHANGE_ME"
dataverse_postgresql_admin_password: "CHANGE_ME"
```

## Step 3: Two-Stage Deployment

### Stage 1 - Deploy HTTP (No SSL)

This stage installs Dataverse and gets it running on HTTP.

**Configuration:**
```yaml
# In group_vars/your_environment.yml
apache:
  ssl:
    enabled: false
letsencrypt:
  enabled: false
```

**Run playbook:**
```bash
# From dataverse-ansible directory
ansible-playbook -i inventory/your_environment.yml site.yml
```

**Expected duration:** 15-30 minutes

**Verify:**
- Visit `http://your-subdomain.yourdomain.com`
- You should see the Dataverse homepage

### Stage 2 - Enable HTTPS with Let's Encrypt

This stage obtains SSL certificate and configures HTTPS.

**Configuration:**
```yaml
# In group_vars/your_environment.yml
apache:
  ssl:
    enabled: true
letsencrypt:
  enabled: true
```

**Run playbook:**
```bash
ansible-playbook -i inventory/your_environment.yml site.yml
```

**Expected duration:** 2-5 minutes

**Verify:**
- Visit `https://your-subdomain.yourdomain.com`
- You should see valid SSL certificate
- HTTP should redirect to HTTPS

## Step 4: Post-Deployment Configuration

### 4.1 Login to Dataverse

- URL: `https://your-subdomain.yourdomain.com`
- Username: `dataverseAdmin`
- Password: Value of `dataverse_adminpass` from your config

### 4.2 Verify Services

SSH into the server and check service status:

```bash
ssh -i ~/.ssh/your-key.pem rocky@YOUR_ELASTIC_IP

# Check all services
sudo systemctl status httpd
sudo systemctl status payara
sudo systemctl status postgresql-16
sudo systemctl status solr

# Check logs if needed
sudo journalctl -u httpd -n 50
sudo journalctl -u payara -n 50
```

### 4.3 Configure Dataverse Settings

Via web UI or API, configure:
- Root dataverse metadata
- Authentication providers
- Metadata blocks
- Storage locations
- Branding (if customized)

## Troubleshooting

### DNS Not Resolving

```bash
# Check DNS propagation
nslookup your-subdomain.yourdomain.com

# If no result, wait or check DNS provider settings
```

### Let's Encrypt Certificate Failure

```bash
# Check certbot logs on server
sudo cat /var/log/letsencrypt/letsencrypt.log

# Common issues:
# - DNS not pointing to server yet
# - Port 80 not accessible (check security groups)
# - Domain already has cert (check /etc/letsencrypt/live/)
```

### Ansible Connection Refused

```bash
# Verify SSH key
ssh -i ~/.ssh/your-key.pem rocky@YOUR_ELASTIC_IP

# Check security group allows SSH from your IP
# Check ansible_host in inventory matches Elastic IP
```

### Dataverse Not Starting

```bash
# Check Payara logs
sudo tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log

# Check PostgreSQL
sudo systemctl status postgresql-16
sudo -u postgres psql -c "\l"  # List databases
```

## Certificate Renewal

Certificates automatically renew via systemd timer:

```bash
# Check renewal timer status
sudo systemctl status certbot-renew.timer

# Manually test renewal (dry-run)
sudo certbot renew --dry-run
```

## Architecture Overview

```
┌─────────────────┐
│   Internet      │
└────────┬────────┘
         │
         ↓ (443/80)
┌─────────────────┐
│  Apache HTTPd   │ ← Let's Encrypt SSL
│  (Reverse Proxy)│
└────────┬────────┘
         │
         ↓ (AJP 8009)
┌─────────────────┐
│  Payara 6       │
│  (App Server)   │
└────────┬────────┘
         │
         ↓
┌─────────────────┬─────────────────┐
│  PostgreSQL 16  │   Solr 9.8.0    │
│  (Database)     │   (Search)      │
└─────────────────┴─────────────────┘
```

## Additional Resources

- Dataverse Documentation: https://guides.dataverse.org/
- Let's Encrypt: https://letsencrypt.org/
- Ansible Documentation: https://docs.ansible.com/
- Project CLAUDE.md: See repository for development setup

## Support

For issues or questions:
1. Check logs on the server
2. Review Ansible playbook output
3. Consult Dataverse community forums
4. File issue in project repository

---
# Appendix: Deployment Checklist
# AWS Deployment Checklist

Quick reference checklist for deploying UCLA Dataverse to AWS. See [AWS Deployment Guide](aws_deployment.md) for detailed instructions.

---

## Pre-Deployment Checklist

### ☐ 1. AWS Infrastructure

- [ ] **EC2 Instance** launched
  - [ ] AMI: Rocky Linux 9 or RHEL 9
  - [ ] Instance type: t3.medium minimum (2 vCPU, 4GB RAM)
  - [ ] Storage: 50GB+ root volume
  - [ ] SSH key pair created and `.pem` file downloaded
- [ ] **Security Group** configured
  - [ ] Port 22 (SSH) from your IP
  - [ ] Port 80 (HTTP) from 0.0.0.0/0
  - [ ] Port 443 (HTTPS) from 0.0.0.0/0
- [ ] **Elastic IP** allocated and associated (production)
- [ ] **DNS A record** created (e.g., dataverse.library.ucla.edu → Elastic IP)

### ☐ 2. Local Setup

- [ ] Repository cloned: `git clone https://github.com/ucla-data-science-center/dataverse-ansible.git`
- [ ] Dependencies installed: `make bootstrap`
- [ ] Python 3.11 virtual environment activated
- [ ] Ansible collections vendored in `./collections/`

### ☐ 3. Credentials & Access

- [ ] SSH key permissions set: `chmod 600 ~/.ssh/dataverse.pem`
- [ ] SSH connection tested: `ssh -i ~/.ssh/dataverse.pem ec2-user@<EC2_IP>`
- [ ] UCLA DOI credentials obtained (DataCite or EZID)
- [ ] SMTP relay information from UCLA IT

### ☐ 4. Configuration Files

#### Inventory File: `inventory/production.yml`

- [ ] `ansible_host` set to EC2 public IP or DNS
- [ ] `ansible_user` matches AMI (ec2-user, rocky, or ubuntu)
- [ ] `ansible_ssh_private_key_file` points to correct .pem file

#### Variables File: `group_vars/production.yml`

**Critical Settings:**

- [ ] `dataverse.payara.siteurl` set to public URL (e.g., https://dataverse.library.ucla.edu)
- [ ] `dataverse.pid.authority` set to UCLA's DOI prefix (e.g., 10.XXXXX)
- [ ] `dataverse.doi.provider` set to "datacite" or "ezid"
- [ ] `dataverse.doi.username` set
- [ ] `dataverse.doi.password` encrypted with ansible-vault
- [ ] `dataverse.doi.baseurl` set to production URL
- [ ] `dataverse.service_email` set to UCLA email (noreply@dataverse.library.ucla.edu)
- [ ] `dataverse.smtp` set to UCLA SMTP relay
- [ ] `dataverse.adminpass` encrypted with ansible-vault
- [ ] `db.postgres.pass` encrypted with ansible-vault
- [ ] `db.postgres.adminpass` encrypted with ansible-vault

**Security Settings:**

- [ ] `dataverse.allow_signups` set to false (require approval)
- [ ] `apache.block.admin` set to true
- [ ] `apache.block.builtin_users` set to true
- [ ] `apache.block.destroy` set to true

**SSL/TLS (Recommended):**

- [ ] `letsencrypt.enabled` set to true
- [ ] `letsencrypt.certbot.email` set to admin email
- [ ] `apache.ssl.enabled` set to true

---

## Deployment Checklist

### ☐ 5. Pre-Deployment Testing

- [ ] Ansible ping successful: `ansible all -i inventory/production.yml -m ping`
- [ ] Dry run completed: `ansible-playbook -i inventory/production.yml site.yml --check`
- [ ] Reviewed deployment plan and estimated duration (20-30 min)

### ☐ 6. Deploy

```bash
# Full deployment
ansible-playbook -i inventory/production.yml site.yml --ask-vault-pass

# Or with vault password file
ansible-playbook -i inventory/production.yml site.yml --vault-password-file ~/.vault_pass
```

- [ ] Deployment completed without errors
- [ ] All services started successfully

### ☐ 7. Post-Deployment Verification

**Service Status:**

- [ ] Payara running: `sudo systemctl status payara`
- [ ] PostgreSQL running: `sudo systemctl status postgresql-16`
- [ ] Solr running: `sudo systemctl status solr`
- [ ] Apache running: `sudo systemctl status httpd`

**API Health Checks:**

- [ ] Version endpoint: `curl https://dataverse.library.ucla.edu/api/info/version`
- [ ] Server endpoint: `curl https://dataverse.library.ucla.edu/api/info/server`

**Web Interface:**

- [ ] Homepage loads: https://dataverse.library.ucla.edu
- [ ] UCLA branding displays correctly
  - [ ] Header with UCLA Library logo
  - [ ] Footer with UCLA links and social media
  - [ ] UCLA Dataverse logo visible
  - [ ] Favicon shows UCLA-themed icon
- [ ] Can log in with admin credentials
- [ ] Support link opens UCLA Jira portal

**Metadata & Language:**

- [ ] Create test dataset, verify metadata blocks available:
  - [ ] Citation (default)
  - [ ] Geospatial
  - [ ] Social Science
  - [ ] Astrophysics
  - [ ] Biomedical
  - [ ] Journals
  - [ ] CodeMeta
  - [ ] HELADA
- [ ] Language selector shows: EN, ES, ZH, JA, KR

---

## Production Hardening Checklist

### ☐ 8. Security

- [ ] Ansible vault used for all passwords
- [ ] Security group restricts SSH to known IPs only
- [ ] SSL/TLS enabled via Let's Encrypt
- [ ] HTTPS redirect configured (HTTP → HTTPS)
- [ ] Admin endpoints blocked by Apache
- [ ] Firewalld configured on EC2 instance
- [ ] Root login disabled in SSH config
- [ ] Regular security updates scheduled

### ☐ 9. Monitoring & Backups

- [ ] CloudWatch agent installed (or alternative monitoring)
- [ ] PostgreSQL backups configured
- [ ] File storage backups configured
- [ ] Log rotation configured
- [ ] Disk space monitoring enabled
- [ ] Service uptime monitoring enabled

### ☐ 10. DOI & Integration Testing

- [ ] Test DOI minting with real dataset
- [ ] Verify DOI resolves correctly
- [ ] Test Make Data Count integration (if enabled)
- [ ] Test SMTP email delivery
- [ ] Test file uploads (various sizes)
- [ ] Test dataset publishing workflow

### ☐ 11. Documentation

- [ ] Document production-specific settings
- [ ] Create runbook for common operations
- [ ] Document backup/restore procedures
- [ ] Document rollback procedures
- [ ] Share admin credentials with team (securely)
- [ ] Update team wiki/docs with deployment info

---

## Rollback Plan

If deployment fails or issues arise:

### Option 1: Redeploy Fresh Instance

```bash
# Terminate EC2 instance
# Launch new EC2 instance
# Reassociate Elastic IP
# Run deployment again
```

### Option 2: Restore from Backup

```bash
# Stop services
sudo systemctl stop payara postgresql-16

# Restore database backup
sudo -u postgres pg_restore -d dvndb /path/to/backup.dump

# Restore file storage
sudo rsync -av /backup/dvn/data/ /usr/local/dvn/data/

# Restart services
sudo systemctl start postgresql-16 payara
```

---

## Quick Commands Reference

```bash
# Check all services
ansible all -i inventory/production.yml -a "systemctl status payara postgresql-16 solr httpd"

# Restart Payara
ansible all -i inventory/production.yml -a "systemctl restart payara"

# Check Payara logs
ansible all -i inventory/production.yml -a "tail -n 50 /usr/local/payara6/glassfish/domains/domain1/logs/server.log"

# Check disk space
ansible all -i inventory/production.yml -a "df -h"

# Update packages
ansible all -i inventory/production.yml -a "dnf update -y"
```

---

## Troubleshooting

| Issue | Command | Reference |
|-------|---------|-----------|
| Can't connect to EC2 | `ssh -vvv -i ~/.ssh/dataverse.pem ec2-user@<IP>` | AWS_DEPLOYMENT.md |
| Payara won't start | `sudo tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log` | TROUBLESHOOTING.md |
| PostgreSQL issues | `sudo tail -f /var/lib/pgsql/16/data/log/postgresql-*.log` | TROUBLESHOOTING.md |
| 502 Bad Gateway | Check Payara status and Apache proxy config | AWS_DEPLOYMENT.md |
| DOI minting fails | Verify DOI credentials and authority in settings | Dataverse Guides |

---

## Post-Deployment Next Steps

1. **Load Testing** - Use Apache Bench or JMeter
2. **Shibboleth SSO** - See issue #11
3. **S3 Storage** - Migrate from local file storage to S3
4. **RDS Migration** - Consider AWS RDS for PostgreSQL
5. **Auto-scaling** - Consider ECS/EKS for containerized deployment
6. **Disaster Recovery** - Document and test DR procedures

---

## Support

- **Documentation:** See [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)
- **Troubleshooting:** See [Troubleshooting Guide](../operations/troubleshooting.md)
- **GitHub Issues:** https://github.com/ucla-data-science-center/dataverse-ansible/issues
- **Dataverse Guides:** https://guides.dataverse.org/
- **Team Slack:** #dataverse channel

---

**Last Updated:** 2025-11-24
**Maintained by:** UCLA Data Science Center
