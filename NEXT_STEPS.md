# Next Steps for Dataverse Ansible Development

**Last Updated**: 2025-11-21

## Current Status

### ✅ Completed (Nov 21, 2025)

1. **Molecule rocky9 scenario fully working**
   - Dataverse 6.8 deploys successfully
   - All services running (Payara, PostgreSQL, Solr, Apache)
   - Accessible at http://localhost:8080

2. **UCLA customizations enabled and tested**
   - Branding: UCLA logo, custom header/stylesheet, "UC Regents" footer
   - Licenses: 7 Creative Commons licenses configured
   - Languages: English + Spanish support
   - Previewers and Data Explorer enabled
   - Codemeta custom metadata block enabled

3. **Fixed issues**
   - `de_ES` → `es_ES` locale typo in defaults
   - Language file copy task wasn't working (fixed in `tasks/dataverse-languages.yml`)
   - Removed duplicate `molecule/rocky9/group_vars/molecule.yml`

4. **Added idempotency check to installer**
   - Checks `/api/info/version` before running `install.py`
   - Skips installer if Dataverse already responding
   - Enables safe re-running of `molecule converge`

### 📊 Molecule Test Results

```
PLAY RECAP *********************************************************************
rocky9  : ok=216  changed=107  unreachable=0  failed=0  skipped=539
```

**Verified working:**
- UCLA logo on homepage ✅
- "Copyright © 2025 UC Regents" in footer ✅
- 7 CC licenses via API ✅
- Language files copied ✅
- Homepage loads without errors ✅

---

## Next Session: AWS Deployment

### Prerequisites to Gather

**1. Domain/DNS**
- [ ] Hostname for Dataverse (e.g., `dataverse.library.ucla.edu`)
- [ ] DNS access to create A record pointing to EC2 IP

**2. SSL Certificate** (pick one)
- [ ] Let's Encrypt: just need domain ready (automated)
- [ ] UCLA cert: `.crt`, `.key`, and intermediate chain files

**3. EC2 Instance**
- [ ] Rocky 9 or RHEL 9 AMI
- [ ] Instance size: t3.large or bigger (4GB+ RAM recommended)
- [ ] Security group: ports 22, 80, 443
- [ ] SSH key pair

**4. Credentials**
- [ ] DataCite DOI credentials (if using real DOIs)
- [ ] SMTP relay info (host, port, auth)
- [ ] AWS credentials (if using S3 storage)

**5. Optional**
- [ ] ORCID client ID/secret
- [ ] Shibboleth/UCLA SSO metadata
- [ ] Google Analytics key

### AWS Inventory Structure

Create an AWS-specific inventory:

```
inventories/
  aws/
    hosts.yml          # EC2 host(s)
    group_vars/
      dataverse.yml    # Copy from molecule, update for production
      vault.yml        # Encrypted secrets (ansible-vault)
```

### Key Configuration Changes for AWS

| Setting | Molecule Value | AWS Value |
|---------|---------------|-----------|
| `apache.ssl.enabled` | `false` | `true` |
| `letsencrypt.enabled` | `false` | `true` (or use own certs) |
| `apache.public_fqdn` | `""` | `dataverse.library.ucla.edu` |
| `dataverse.payara.siteurl` | `""` | `https://dataverse.library.ucla.edu` |
| `dataverse.doi.provider` | `FAKE` | `DataCite` |
| `dataverse.smtp` | `localhost` | Your SMTP relay |

### Deployment Commands

```bash
# Test connection
ansible -i inventories/aws/hosts.yml all -m ping

# Dry run
ansible-playbook -i inventories/aws/hosts.yml dataverse.pb --check

# Deploy
ansible-playbook -i inventories/aws/hosts.yml dataverse.pb
```

---

## Quick Reference

### Molecule Commands

```bash
# Run converge (idempotent now!)
uv run molecule converge -s rocky9

# Destroy and start fresh
uv run molecule destroy -s rocky9

# Shell into container
uv run molecule login -s rocky9

# Full test cycle
uv run molecule test -s rocky9
```

### Key Files

| File | Purpose |
|------|---------|
| `molecule/rocky9/group_vars/dataverse.yml` | Molecule test config (UCLA customizations) |
| `defaults/main.yml` | Role defaults (production values) |
| `tasks/dataverse-install.yml` | Installer with idempotency check |
| `tasks/dataverse-languages.yml` | Language pack configuration |

### Verify Deployment

```bash
# Check version
curl http://localhost:8080/api/info/version

# Check licenses
curl http://localhost:8080/api/licenses

# Check branding
curl -sL http://localhost:8080/ | grep -E "UC Regents|UCLA"
```

---

## Commits from This Session

1. `3d97d43` - Enable UCLA customizations in molecule rocky9 scenario
2. `d22533d` - Add idempotency check to skip installer if Dataverse already running

---

## Notes

- **Sample data disabled**: IQSS sample data scripts are fragile and timeout. Disabled in molecule config.
- **Counter enabled**: SUSHI metrics testing enabled with `upload_to_hub: false`
- **Thumbnails enabled**: Image preview generation enabled
