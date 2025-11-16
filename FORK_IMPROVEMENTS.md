# Fork Improvements Log

This document tracks improvements made to the UCLA fork that may be contributed upstream later.

## Solr Installation Idempotency Fix

**Date:** 2025-11-16
**Files Modified:** `tasks/solr.yml`
**Issue:** Solr installation logic was not truly idempotent

### Problem

The original role's Solr installation tasks used `when: solr_installer_download.changed` conditions:

```yaml
- name: download and unzip solr
  get_url:
    url: "{{ solr_download_url }}"
    checksum: "{{ dataverse.solr.checksum }}"
    dest: /tmp/solr-{{ dataverse.solr.version }}.tgz
  register: solr_installer_download

- name: untar solr
  unarchive: ...
  when: solr_installer_download.changed  # ← PROBLEM

- name: copy solr distro files into solr root
  shell: "/bin/cp -r /tmp/solr-*.tgz/* {{ dataverse.solr.root }}"
  when: solr_installer_download.changed  # ← PROBLEM
```

**This breaks when:**
1. Tarball already exists in `/tmp/` (from prepare playbook or previous converge)
2. `get_url` reports `changed: false` (file already present, checksum matches)
3. Extraction and installation tasks are **skipped**
4. `/usr/local/solr/` directory created but **empty**
5. Subsequent tasks fail: "Destination /usr/local/solr/bin/solr.in.sh does not exist!"

**Root cause:** The conditional checks "Did we just download?" instead of "Is Solr already installed?"

### Solution

Changed conditionals to check actual installation state:

```yaml
- name: check if solr is already installed
  stat:
    path: "{{ dataverse.solr.root }}/bin/solr.in.sh"
  register: solr_installed

- name: download and unzip solr
  get_url: ...
  when: not solr_installed.stat.exists

- name: untar solr
  unarchive: ...
  when: not solr_installed.stat.exists

- name: copy solr distro files into solr root
  shell: ...
  when: not solr_installed.stat.exists
```

### Benefits

1. **True idempotency** - Can run `molecule converge` multiple times safely
2. **Works with prepare.yml** - Caching optimization no longer breaks installation
3. **Faster local iteration** - prepare.yml caches 370MB Solr download
4. **Correct Ansible pattern** - Checks desired state, not intermediate steps

### Testing

Tested with:
- ✅ Fresh installation (Solr not present)
- ✅ Re-run converge (Solr already installed, skips gracefully)
- ✅ prepare.yml enabled (pre-cached tarball, still installs correctly)
- ✅ prepare.yml disabled (downloads fresh, installs correctly)

### Upstream Contribution

**Status:** Ready for upstream PR
**Justification:** Fixes genuine idempotency bug, follows Ansible best practices
**Compatibility:** Backward compatible - doesn't change behavior for fresh installs

---

## Future Improvements to Track

### Payara listen_address for Docker

**File:** `defaults/main.yml`
**Current:** `dataverse.payara.listen_address: 127.0.0.1`
**Issue:** Breaks Docker port mapping in local testing
**Workaround:** Override in `molecule/rocky9/group_vars/molecule.yml` to `0.0.0.0`
**Potential upstream:** Document this requirement for Docker/Molecule testing

### Non-idempotent Dataverse Installer

**File:** `tasks/dataverse-installer.yml` (assumed)
**Issue:** Installer cannot be run twice on same database
**Current approach:** Always destroy + converge for testing
**Potential upstream:** Add check for existing installation, skip if present

### Log4j CVE Mitigation

**File:** `tasks/solr.yml:74-79`
**Issue:** Attempts to remove JndiLookup.class already removed in Solr 9.8+
**Current:** `ignore_errors: yes` suppresses failure
**Improvement:** Check if class exists before attempting removal:

```yaml
- name: check if JndiLookup.class exists
  shell: unzip -l {{ dataverse.solr.root }}/server/lib/ext/log4j-core-*.jar | grep JndiLookup.class
  register: jndilookup_check
  failed_when: false
  changed_when: false

- name: remove JndiLookup.class from log4j-core.jar
  shell: zip -q -d {{ dataverse.solr.root }}/server/lib/ext/log4j-core-*.jar org/apache/logging/log4j/core/lookup/JndiLookup.class
  when: jndilookup_check.rc == 0
```

---

## Documentation Added

- `TROUBLESHOOTING.md` - Common Molecule/Docker issues and solutions
- `CONFIG_STRATEGY.md` - Local testing vs AWS deployment configuration strategy
- `FORK_IMPROVEMENTS.md` - This file, tracking fork-specific improvements
- Updated `CLAUDE.md` - AI assistant context with uv workflow

## Tooling Improvements

- Migrated from conda + pip-tools to **uv** for dependency management
- Vendored Ansible collections (community.general 11.2.1, community.postgresql 4.1.0)
- Added `Makefile` with `bootstrap` target for collection installation
- Created `.python-version` for consistent Python 3.11 usage
- Updated `.gitignore` for uv virtual environments

---

## Contribution Strategy

1. **Improve in fork first** - Test thoroughly in UCLA environment
2. **Document all changes** - Track in this file with justification
3. **After stable deployment** - Bundle logical improvements into upstream PRs
4. **Prioritize for upstream:**
   - Bug fixes (like Solr idempotency)
   - Docker/Molecule testing improvements
   - Documentation enhancements
