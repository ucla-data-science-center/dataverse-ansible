# AWS Deployment Checklist

Quick reference checklist for deploying UCLA Dataverse to AWS. See [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) for detailed instructions.

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
- **Troubleshooting:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **GitHub Issues:** https://github.com/ucla-data-science-center/dataverse-ansible/issues
- **Dataverse Guides:** https://guides.dataverse.org/
- **Team Slack:** #dataverse channel

---

**Last Updated:** 2025-11-24
**Maintained by:** UCLA Data Science Center
