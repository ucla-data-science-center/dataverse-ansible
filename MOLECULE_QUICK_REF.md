# Molecule Quick Reference Guide

Quick commands and workflows for testing Dataverse Ansible with Docker/Molecule.

## Prerequisites

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Bootstrap project (installs collections, creates venv)
make bootstrap
```

## Common Workflows

### Fresh Deployment Test

```bash
# Destroy any existing container
uv run molecule destroy -s rocky9

# Run full deployment
uv run molecule converge -s rocky9

# Verify it worked
curl http://localhost:8080/api/info/version
```

### Idempotency Test

```bash
# After a successful converge, run it again
uv run molecule converge -s rocky9

# Should complete without errors or downloads
# Check for: "ok=X changed=0" (or minimal changes)
```

### Iterative Development

```bash
# Make changes to tasks/playbooks...

# Test only specific tasks
uv run molecule converge -s rocky9 -- --tags apache

# Or skip certain tasks
uv run molecule converge -s rocky9 -- --skip-tags sampledata
```

### Interactive Debugging

```bash
# SSH into the container
uv run molecule login -s rocky9

# Or via docker
docker exec -it rocky9 /bin/bash

# Check Payara logs
docker exec rocky9 tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log

# Check systemd services
docker exec rocky9 systemctl status payara
docker exec rocky9 systemctl status postgresql-16
docker exec rocky9 systemctl status httpd
```

### Full Test Lifecycle

```bash
# Complete test sequence
uv run molecule test -s rocky9

# This runs:
# 1. Dependency check
# 2. Cleanup
# 3. Destroy
# 4. Syntax check
# 5. Create
# 6. Prepare
# 7. Converge
# 8. Idempotence
# 9. Side effect check
# 10. Verify
# 11. Cleanup
# 12. Destroy
```

## Common Issues & Solutions

### Port 8080 Already in Use

```bash
# Find what's using it
lsof -i :8080

# Kill it or use different port in molecule.yml
```

### Dataverse Not Accessible from Host

**Symptom:** `curl http://localhost:8080` fails but works inside container

**Check:**
```bash
docker exec rocky9 netstat -tlnp | grep 8080
# Should show: :::8080 (all interfaces)
# Not: 127.0.0.1:8080 (localhost only)
```

**Fix:** Ensure `molecule/rocky9/group_vars/molecule.yml` has complete `dataverse.payara` section with `listen_address: 0.0.0.0`

See `TROUBLESHOOTING.md` for details.

### Converge Fails on Second Run

**Symptom:** "JVM option already exists" or similar idempotency errors

**Fix:** Our fork includes idempotency fixes. Make sure you're on latest `develop` branch:

```bash
git pull origin develop
```

### Container Won't Start (cgroup errors)

**Fix:** Already configured in `molecule.yml` with `cgroupns_mode: host`

If still failing, increase Docker Desktop resources.

## Useful Inspection Commands

### Check Dataverse Version

```bash
curl http://localhost:8080/api/info/version
```

### Check Database

```bash
docker exec -it rocky9 psql -U dvnuser -d dvndb
# Inside psql:
\dt              # List tables
\q               # Quit
```

### Check Solr

```bash
docker exec rocky9 systemctl status solr
docker exec rocky9 curl http://localhost:8983/solr/admin/cores?action=STATUS
```

### Check Payara Configuration

```bash
# List JVM options
docker exec -u dataverse rocky9 /usr/local/payara6/bin/asadmin list-jvm-options

# Check listen address
docker exec -u dataverse rocky9 /usr/local/payara6/bin/asadmin get server-config.network-config.network-listeners.network-listener.http-listener-1.address
```

## Performance Tips

### Speed Up Testing

```bash
# Skip sample data and previewers
uv run molecule converge -s rocky9 -- --skip-tags sampledata,previewers

# Use prepare playbook for caching
# (Already enabled in our molecule.yml)
```

### Cache Management

```bash
# View cached downloads
ls -lh ~/.cache/molecule/dataverse-ansible/rocky9/

# Clear cache if needed
rm -rf ~/.cache/molecule/dataverse-ansible/rocky9/
```

## Molecule Configuration Files

- `molecule/rocky9/molecule.yml` - Main configuration
- `molecule/rocky9/converge.yml` - Playbook to run
- `molecule/rocky9/prepare.yml` - Pre-caching setup
- `molecule/rocky9/group_vars/molecule.yml` - Test-specific variables

## Environment Variables

```bash
# Use different Python version
export UV_PYTHON=3.11

# Increase Ansible verbosity
export ANSIBLE_VERBOSITY=2

# Run molecule with verbose output
uv run molecule converge -s rocky9 -- -vvv
```

## Background Execution

```bash
# Run in background with logging
uv run molecule converge -s rocky9 2>&1 | tee /tmp/molecule-run.log &

# Check progress
tail -f /tmp/molecule-run.log

# Or via molecule
uv run molecule converge -s rocky9 > /tmp/output.log 2>&1 &
```

## Testing Strategy

### For Local Development

1. Destroy + Converge for fresh install
2. Test your changes
3. Run converge again (idempotency check)
4. Verify no errors or unwanted changes

### Before Pushing

1. Full `molecule test` run
2. Review all changes
3. Check PLAY RECAP for failures

### Before AWS Deployment

1. Test locally with molecule
2. Review variable differences (see `CONFIG_STRATEGY.md`)
3. Test on staging AWS instance first

## Quick Troubleshooting Checklist

- [ ] Is Docker running?
- [ ] Are ports available (8080, 5432, 8983)?
- [ ] Did you run `make bootstrap`?
- [ ] Are you in the right directory?
- [ ] Is the container still running? (`docker ps`)
- [ ] Check logs: `/tmp/molecule-*.log`
- [ ] Try destroy + converge for clean slate

## Resources

- Full troubleshooting: `TROUBLESHOOTING.md`
- Configuration strategy: `CONFIG_STRATEGY.md`
- Fork improvements: `FORK_IMPROVEMENTS.md`
- Molecule docs: https://ansible.readthedocs.io/projects/molecule/
- Dataverse docs: https://guides.dataverse.org/
