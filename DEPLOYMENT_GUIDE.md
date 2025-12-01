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

### 1.3 Configure DNS

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
