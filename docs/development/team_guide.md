# UCLA Dataverse Ansible - Team Guide

Internal guide for UCLA Data Science Center team working with the Dataverse Ansible fork.

## Quick Start

### First Time Setup

```bash
# Clone the fork
git clone https://github.com/ucla-data-science-center/dataverse-ansible.git
cd dataverse-ansible

# Bootstrap the project (installs uv, collections, creates venv)
make bootstrap

# Test locally with Molecule
uv run molecule converge -s rocky9

# Access Dataverse
open http://localhost:8080
```

### Update Your Local Copy

```bash
git pull origin develop
make bootstrap  # Refresh collections if needed
```

## Repository Structure

### Our Fork vs Upstream

- **Upstream:** `IQSS/dataverse-ansible` (original project)
- **Our Fork:** `ucla-data-science-center/dataverse-ansible`
- **Main Branch:** `develop` (we follow upstream's convention)
- **Testing Branch:** `fix/collections-pin` (current work)

### Important Files

**Configuration:**
- `group_vars/aws.yml` - AWS/production configuration
- `molecule/rocky9/group_vars/molecule.yml` - Local testing configuration
- `defaults/main.yml` - Role defaults (don't modify directly)

**Documentation (UCLA-specific):**
- `FORK_IMPROVEMENTS.md` - Tracks our changes vs upstream
- `CONFIG_STRATEGY.md` - Local vs AWS configuration approach
- `TROUBLESHOOTING.md` - Common issues and solutions
- `MOLECULE_QUICK_REF.md` - Quick command reference
- `TEAM_GUIDE.md` - This file

**Testing:**
- `molecule/` - Local Docker-based testing setup
- `Makefile` - Bootstrap and utility commands

## Development Workflow

### 1. Local Testing (Molecule/Docker)

```bash
# Test changes locally before AWS deployment
uv run molecule destroy -s rocky9
uv run molecule converge -s rocky9

# Verify idempotency
uv run molecule converge -s rocky9  # Should complete without errors
```

### 2. Deploy to AWS Staging

```bash
# Review configuration differences
diff molecule/rocky9/group_vars/molecule.yml group_vars/aws.yml

# Deploy to staging instance
ansible-playbook -i inventory/staging site.yml

# Verify deployment
curl https://staging.dataverse.ucla.edu/api/info/version
```

### 3. Deploy to Production

```bash
# ALWAYS test in staging first!
# Review changes with team
# Deploy during maintenance window

ansible-playbook -i inventory/production site.yml

# Verify production
curl https://dataverse.ucla.edu/api/info/version
```

## Configuration Management

### Environment Differences

| Setting | Molecule (Local) | AWS (Production) |
|---------|------------------|------------------|
| `listen_address` | `0.0.0.0` (Docker) | `127.0.0.1` (secure) |
| `use_ssl` | `false` | `true` |
| `siteurl` | `http://localhost:8080` | `https://dataverse.ucla.edu` |
| `smtp_host` | `localhost` | UCLA SMTP server |
| `doi_provider` | `none` or `fake` | `ezid` or `datacite` |

**See `CONFIG_STRATEGY.md` for complete details.**

### How to Override Settings

**For local testing:**
Edit `molecule/rocky9/group_vars/molecule.yml`

**For AWS:**
Edit `group_vars/aws.yml`

**IMPORTANT:** When overriding nested dicts (like `dataverse.payara`), you must specify the COMPLETE dict structure. Ansible doesn't deep-merge. See `TROUBLESHOOTING.md` for examples.

## Our Fork Improvements

We've made several improvements that will be contributed upstream:

### 1. Solr Installation Idempotency (✅ Fixed)
- **Issue:** Re-running converge would fail if Solr tarball was cached
- **Fix:** Check if Solr is installed, not if tarball was downloaded
- **Benefit:** Enables prepare.yml caching (370MB saved)

### 2. Payara Installation Idempotency (✅ Fixed)
- **Issue:** Same as Solr
- **Fix:** Check if Payara is installed
- **Benefit:** Enables prepare.yml caching (200MB saved)

### 3. JVM Options Idempotency (✅ Fixed)
- **Issue:** `create-jvm-options` fails on second run (option exists)
- **Fix:** Check if option exists before creating
- **Benefit:** Converge can run multiple times safely

### 4. Docker Testing Support (✅ Implemented)
- **Issue:** Payara listens on 127.0.0.1, breaking Docker port mapping
- **Fix:** Override listen_address to 0.0.0.0 in molecule.yml
- **Benefit:** Local testing works correctly

**See `FORK_IMPROVEMENTS.md` for technical details.**

## Dependency Management

### We Use UV (Not Conda/Pip)

**Why:** UV is 10-100x faster than pip/conda for Python package management.

```bash
# Install packages
uv pip install <package>

# Update dependencies
uv pip compile requirements.in -o requirements.txt
uv pip sync requirements.txt

# Or just use make
make bootstrap
```

### Vendored Collections

We vendor Ansible collections (don't rely on `ansible-galaxy install`):
- `community.general` 11.2.1
- `community.postgresql` 4.1.0

**Stored in:** `collections/ansible_collections/`

**Update:** Run `make bootstrap` or `ansible-galaxy collection install -r requirements.yml -p collections/`

## Common Tasks

### Update Dataverse Version

```yaml
# In group_vars/aws.yml or molecule.yml
dataverse:
  version: "6.8"  # Change this
```

Then test locally and deploy.

### Change PostgreSQL Version

```yaml
dataverse_postgresql_version: 16  # Default
```

### Add Custom Branding

```yaml
dataverse:
  copyright: "UC Regents"
  google_analytics_key: "UA-XXXXX-Y"
```

See Dataverse docs for more customization options.

### Enable Shibboleth

```yaml
# In AWS configuration
shibboleth:
  enabled: true
  # ... additional configuration
```

**Note:** Shibboleth has idempotency issues on re-runs (documented in FORK_IMPROVEMENTS.md).

## Troubleshooting

### "Dataverse not accessible from localhost"

**Check:**
```bash
docker exec rocky9 netstat -tlnp | grep 8080
```

**Should show:** `:::8080` (all interfaces)
**Not:** `127.0.0.1:8080` (localhost only)

**Fix:** See `TROUBLESHOOTING.md` - Ansible dict merging issue.

### "Port 8080 already in use"

```bash
lsof -i :8080  # Find what's using it
# Kill the process or change molecule.yml to use different port
```

### "JVM option already exists"

You're running an older version. Update to latest develop:

```bash
git pull origin develop
```

### "Molecule converge fails on second run"

This is expected if Dataverse installer ran. The installer is not idempotent.

**Solution:** Always destroy + converge:
```bash
uv run molecule destroy -s rocky9
uv run molecule converge -s rocky9
```

### Full Troubleshooting

See `TROUBLESHOOTING.md` for comprehensive guide.

## Syncing with Upstream

### Check for Upstream Updates

```bash
# Add upstream remote (one time)
git remote add upstream https://github.com/IQSS/dataverse-ansible.git

# Fetch upstream changes
git fetch upstream

# See what's new
git log develop..upstream/develop
```

### Merge Upstream Changes

```bash
# Merge upstream develop into our develop
git checkout develop
git merge upstream/develop

# Resolve conflicts if any
# Test thoroughly!
uv run molecule converge -s rocky9

# Push to our fork
git push origin develop
```

**CAUTION:** Always test after merging upstream changes. They may conflict with our improvements.

## Contributing Upstream

We plan to contribute our fixes back to IQSS/dataverse-ansible.

**See `UPSTREAM_PR_DRAFT.md` for prepared PR descriptions.**

**Strategy:**
1. Test thoroughly in UCLA environment (1-2 weeks)
2. Bundle related improvements (idempotency fixes)
3. Submit well-documented PRs with testing evidence

**Priority:**
- ⭐⭐⭐ Solr idempotency
- ⭐⭐⭐ Payara idempotency
- ⭐⭐⭐ JVM options idempotency
- ⭐⭐ Documentation improvements

## Team Practices

### Before Making Changes

1. Create a feature branch
2. Test locally with molecule
3. Document in commit messages
4. Update FORK_IMPROVEMENTS.md if significant

### Before Deploying to AWS

1. Test in molecule
2. Review with at least one other team member
3. Deploy to staging first
4. Verify staging works
5. Schedule production deployment

### Code Review

- All changes should be reviewed
- Test evidence should be provided
- Configuration changes need extra scrutiny

### Documentation

- Update relevant docs when changing configuration
- Add troubleshooting entries for new issues found
- Keep FORK_IMPROVEMENTS.md current

## Useful Resources

### Internal Docs
- Configuration Strategy: `../setup/configuration.md`
- Fork Tracking: `changelog.md`
- Troubleshooting: `../operations/troubleshooting.md`
- Quick Reference: `commands.md`

### External Resources
- Dataverse Installation Guide: https://guides.dataverse.org/en/latest/installation/
- Ansible Documentation: https://docs.ansible.com/
- Molecule Documentation: https://ansible.readthedocs.io/projects/molecule/
- UV Documentation: https://docs.astral.sh/uv/

### Upstream Project
- Original Repo: https://github.com/IQSS/dataverse-ansible
- Issues: https://github.com/IQSS/dataverse-ansible/issues
- Dataverse Project: https://dataverse.org/

## Getting Help

### Internal
- Check `TROUBLESHOOTING.md` first
- Ask in team Slack channel
- Review `FORK_IMPROVEMENTS.md` for known issues

### External
- Dataverse community: https://groups.google.com/g/dataverse-community
- Ansible community: https://groups.google.com/g/ansible-project
- GitHub issues: https://github.com/IQSS/dataverse-ansible/issues

## Maintenance Schedule

### Regular Tasks

**Weekly:**
- Check for upstream updates
- Review any staging deployment issues

**Monthly:**
- Review and update dependencies
- Check for Dataverse security updates

**Quarterly:**
- Plan Dataverse version upgrades
- Review fork improvements for upstream contribution
- Update documentation

## Contact

**Team:** UCLA Data Science Center
**Repository:** https://github.com/ucla-data-science-center/dataverse-ansible
**Production:** https://dataverse.ucla.edu

---

*Last Updated: 2025-11-16*
*Maintained by: UCLA Data Science Center Team*
