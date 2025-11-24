# Dataverse Ansible Troubleshooting Guide

## Common Issues with Molecule/Docker Testing

### Issue: localhost:8080 not accessible from host machine

**Symptoms:**
- `curl http://localhost:8080` returns "Connection reset by peer"
- Container is running (`docker ps` shows port `0.0.0.0:8080->8080/tcp`)
- Dataverse works inside container (`docker exec rocky9 curl http://localhost:8080` succeeds)

**Root Cause:**
Payara is configured to listen on `127.0.0.1` (localhost only inside container) instead of `0.0.0.0` (all network interfaces).

**Diagnosis:**
```bash
# Check what interface Payara is listening on
docker exec rocky9 netstat -tlnp | grep 8080

# Should show:
# ❌ tcp6 0 0 127.0.0.1:8080  :::*  LISTEN  (WRONG - only localhost)
# ✅ tcp6 0 0 :::8080         :::*  LISTEN  (CORRECT - all interfaces)
```

**Solution:**
Add to `molecule/rocky9/group_vars/molecule.yml`:

**IMPORTANT:** Due to Ansible's dict merging behavior, you must specify the ENTIRE `dataverse.payara` section to override `listen_address`:

```yaml
# IMPORTANT for Docker: Payara must listen on all interfaces
# NOTE: Must specify full payara section due to Ansible dict merging
dataverse:
  payara:
    user: dataverse
    group: dataverse
    domain: domain1
    logformat: ulf
    adminuser: admin
    adminpass: notPr0d
    siteurl:
    listen_address: 0.0.0.0  # OVERRIDE (default: 127.0.0.1)
    launch_timeout: 180
    request_timeout: 1800
    root: /usr/local
    dir: payara6
    zipurl: https://nexus.payara.fish/repository/payara-community/fish/payara/distributions/payara/6.2025.3/payara-6.2025.3.zip
    zipchecksum: sha256:88f5c1e5b40ea4bc60ae3e34e6858c1b33145dc06c4b05c3d318ed67c131e210
```

**Why full section needed:**
Ansible doesn't deep-merge nested dicts by default. If you only specify `dataverse.payara.listen_address`, it replaces the entire `payara` dict, losing all other settings.

**Common dicts that need full specification in molecule group_vars:**
- `apache` - Must include `ssl`, `block`, `port`, `enabled`, etc.
- `dataverse` - Must include `payara`, `thumbnails`, and other sub-keys
- `db` - Must include `postgres`, `use_rds`, etc.

**Quick fix:** Copy the full dict structure from `defaults/main.yml` and only modify the values you need to override.

Then rebuild:
```bash
uv run molecule destroy -s rocky9
uv run molecule converge -s rocky9
```

**Why this happens:**
The default in `defaults/main.yml` is `listen_address: 127.0.0.1`, which is correct for production (security) but prevents Docker port mapping from working in local testing.

---

### Issue: Duplicate collection warning

**Symptoms:**
```
WARNING: Another version of 'community.general' 11.2.1 was found installed in
/Users/timdennis/websites/dataverse-ansible/collections/ansible_collections,
only the first one will be used
```

**Root Cause:**
Collection exists in two locations:
1. Vendored: `./collections/ansible_collections/community/general/` (correct, version controlled)
2. Global: `~/.ansible/collections/ansible_collections/community/general/` (from previous install)

**Impact:**
None - Ansible uses the vendored version (first in `collections_path`)

**Solution (Optional):**
```bash
# Remove global copy if desired
rm -rf ~/.ansible/collections/ansible_collections/community/general
```

---

### Issue: Solr log4j zip error (non-fatal)

**Symptoms:**
```
fatal: [rocky9]: FAILED! => zip error: Nothing to do!
(/usr/local/solr/server/lib/ext/log4j-core-2.21.0.jar)
```

**Root Cause:**
Playbook tries to remove `JndiLookup.class` from log4j for CVE-2021-44228 mitigation, but newer Solr versions (9.8.0) already removed it.

**Impact:**
None - task fails but is non-critical. Security patch already applied by Solr.

**Solution:**
Can be ignored, or update the task to check if class exists first:

```yaml
# In tasks/solr.yml - add a check before the zip command
- name: check if JndiLookup.class exists
  shell: unzip -l /usr/local/solr/server/lib/ext/log4j-core-*.jar | grep JndiLookup.class
  register: jndilookup_check
  failed_when: false
  changed_when: false

- name: remove JndiLookup.class from log4j-core.jar
  command: zip -q -d /usr/local/solr/server/lib/ext/log4j-core-*.jar org/apache/logging/log4j/core/lookup/JndiLookup.class
  when: jndilookup_check.rc == 0
```

---

### Issue: Port 8080 already in use

**Symptoms:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:8080: bind: address already in use
```

**Root Cause:**
Another service (or previous container) is using port 8080

**Solutions:**

**Option 1: Free up port 8080**
```bash
# Find what's using port 8080
lsof -i :8080
# Or on Linux:
ss -tlnp | grep 8080

# Stop the service or kill the process
```

**Option 2: Use different host port**
Edit `molecule/rocky9/molecule.yml`:
```yaml
platforms:
  - name: rocky9
    published_ports:
      - "8888:8080"  # Change host port to 8888
```

Then access at `http://localhost:8888`

---

### Issue: Dataverse installer fails - not idempotent

**Symptoms:**
- Molecule converge fails on second run
- Error: "Dataverse already installed" or database errors

**Root Cause:**
The Dataverse installer cannot be run twice on the same database/installation.

**Solution:**
Always destroy and recreate between test runs:

```bash
# CORRECT workflow
uv run molecule destroy -s rocky9
uv run molecule converge -s rocky9

# WRONG - will fail
uv run molecule converge -s rocky9  # first time - works
uv run molecule converge -s rocky9  # second time - FAILS
```

**For faster iteration:**
If testing non-installer tasks, use tags:
```bash
# Test only Apache configuration
uv run molecule converge -s rocky9 -- --tags apache

# Test only branding
uv run molecule converge -s rocky9 -- --tags branding
```

---

### Issue: Container won't start - cgroup errors

**Symptoms:**
```
Error: OCI runtime create failed: cgroup: cgroup mountpoint does not exist
```

**Root Cause:**
Docker Desktop on macOS doesn't support certain cgroup configurations

**Solution:**
Already configured in `molecule/rocky9/molecule.yml`:
```yaml
platforms:
  - name: rocky9
    cgroupns_mode: host  # Important for macOS
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup:rw
```

If still failing, check Docker Desktop resource limits.

---

## Debugging Tips

### Check container logs
```bash
# All systemd services
uv run molecule login -s rocky9
journalctl -xe

# Specific service
docker exec rocky9 systemctl status payara
docker exec rocky9 systemctl status postgresql-16
docker exec rocky9 systemctl status httpd
```

### Check Payara logs
```bash
docker exec rocky9 tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log
```

### Check PostgreSQL
```bash
# Connect to database
docker exec -it rocky9 psql -U dvnuser -d dvndb

# Check tables
\dt
\q
```

### Test Dataverse API
```bash
# From outside container
curl http://localhost:8080/api/info/version

# From inside container
docker exec rocky9 curl http://localhost:8080/api/info/version
```

### Full container shell
```bash
# Interactive shell
uv run molecule login -s rocky9

# Or via docker
docker exec -it rocky9 /bin/bash
```

---

## Performance Issues

### Issue: Slow converge time (20+ minutes)

**Normal behavior:**
- Full Dataverse installation takes 15-20 minutes
- Downloads Payara (~200MB), Solr, dependencies
- Compiles/deploys Dataverse WAR file
- Initializes database, creates sample data

**Speed up:**
1. **Use prepare playbook** - already configured, caches Solr download
2. **Skip optional features**:
   ```bash
   uv run molecule converge -s rocky9 -- --skip-tags sampledata,previewers
   ```
3. **Increase Docker resources** - Give Docker more CPU/RAM in settings

---

## Clean Up

### Remove all molecule containers
```bash
uv run molecule destroy -s rocky9
```

### Clean up Docker resources
```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Full cleanup (BE CAREFUL - removes all unused Docker resources)
docker system prune -a
```

### Reset molecule cache
```bash
rm -rf ~/.cache/molecule/dataverse-ansible/rocky9
```

---

## Getting Help

### Check playbook output
All task output is visible during `molecule converge`. Look for:
- `fatal:` - Task failed
- `changed:` - Task made changes
- `ok:` - Task succeeded, no changes
- `skipping:` - Task skipped (conditional)

### Verbose mode
```bash
# More verbose output
uv run molecule converge -s rocky9 -- -v

# Very verbose (shows all variable values)
uv run molecule converge -s rocky9 -- -vvv
```

### Check molecule logs
```bash
ls -la ~/.cache/molecule/dataverse-ansible/rocky9/
```

---

## Reference

- Molecule docs: https://ansible.readthedocs.io/projects/molecule/
- Dataverse installation guide: https://guides.dataverse.org/en/latest/installation/
- Docker docs: https://docs.docker.com/
