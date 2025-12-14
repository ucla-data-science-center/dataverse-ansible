# Upstream PR Drafts

These are ready-to-submit PR descriptions for contributing fixes back to IQSS/dataverse-ansible.

---

## PR #1: Fix Installation Idempotency (Solr & Payara)

### Title
Fix Solr and Payara installation idempotency for molecule/docker testing

### Description

**Problem**

The Solr and Payara installation tasks are not truly idempotent due to conditional logic that checks if files were *downloaded* rather than if the software is *installed*.

**Current behavior:**
```yaml
- name: download and unzip solr
  get_url:
    url: "{{ solr_download_url }}"
    dest: /tmp/solr-{{ dataverse.solr.version }}.tgz
  register: solr_installer_download

- name: untar solr
  unarchive:
    src: /tmp/solr-{{ dataverse.solr.version }}.tgz
    dest: /tmp
  when: solr_installer_download.changed  # ← PROBLEM
```

**This breaks in the following scenario:**
1. Tarball already exists in `/tmp/` (from prepare playbook or previous run)
2. `get_url` reports `changed: false` (file exists, checksum matches)
3. Extraction and installation tasks are **skipped**
4. Solr/Payara directory created but **empty**
5. Subsequent tasks fail

**Impact:**
- prepare.yml caching optimization cannot be used
- Re-running converge downloads 570MB unnecessarily (Solr 370MB + Payara 200MB)
- Not truly idempotent

**Solution**

Check actual installation state instead of download state:

```yaml
- name: check if solr is already installed
  stat:
    path: "{{ dataverse.solr.root }}/bin/solr.in.sh"
  register: solr_installed

- name: download and unzip solr
  get_url:
    url: "{{ solr_download_url }}"
    dest: /tmp/solr-{{ dataverse.solr.version }}.tgz
  when: not solr_installed.stat.exists

- name: untar solr
  unarchive:
    src: /tmp/solr-{{ dataverse.solr.version }}.tgz
    dest: /tmp
  when: not solr_installed.stat.exists
```

**Benefits:**
1. ✅ True idempotency - safe to run converge multiple times
2. ✅ prepare.yml caching works correctly
3. ✅ Faster local iteration (avoids 570MB downloads)
4. ✅ Follows Ansible best practices (check desired state)
5. ✅ Backward compatible - no behavior change for fresh installs

**Testing:**

Tested extensively with Docker/Molecule:
- ✅ Fresh installation (Solr/Payara not present)
- ✅ Re-run converge (software already installed, skips gracefully)
- ✅ prepare.yml enabled (pre-cached tarball, still installs correctly)
- ✅ prepare.yml disabled (downloads fresh, installs correctly)

**Files Changed:**
- `tasks/solr.yml`
- `tasks/payara.yml`

---

## PR #2: Fix JVM Options Creation Idempotency

### Title
Fix JVM options creation to be idempotent

### Description

**Problem**

Several tasks use `asadmin create-jvm-options` without checking if the option already exists, causing failures on second converge:

```yaml
- name: upload to /tmp until we move away from JSF
  shell: '{{ payara_dir}}/bin/asadmin create-jvm-options "-Ddataverse.files.uploads=/tmp"'
  when: dataverse.uploads_dir is defined
```

**Error on re-run:**
```
remote failure: JVM option -Ddataverse.files.uploads=/tmp already exists in the configuration.
```

**Impact:**
- Converge fails on second run
- Not idempotent
- Prevents full molecule testing
- Playbook aborts before Payara restart tasks

**Solution**

Add existence checks before creating JVM options (following the pattern already used for `system-email` option):

```yaml
- name: check if uploads directory JVM option exists
  shell: "{{ payara_dir }}/bin/asadmin list-jvm-options | grep -q 'Ddataverse.files.uploads'"
  register: has_uploads_dir
  failed_when: false
  changed_when: false
  when: dataverse.uploads_dir is defined

- name: upload to /tmp until we move away from JSF
  shell: '{{ payara_dir}}/bin/asadmin create-jvm-options "-Ddataverse.files.uploads=/tmp"'
  when: dataverse.uploads_dir is defined and has_uploads_dir.rc != 0
```

**Fixed options:**
- `dataverse.files.uploads`
- `dataverse.oai.server.maxidentifiers`
- `dataverse.oai.server.maxrecords`
- `dataverse.feature.index-harvested-metadata-source`

**Benefits:**
1. ✅ True idempotency - converge can run multiple times
2. ✅ Playbook completes successfully on re-runs
3. ✅ Enables full molecule/testing workflow
4. ✅ Follows existing pattern in same file (system-email option)

**Testing:**

- ✅ Fresh install: JVM options created
- ✅ Second converge: Options skipped (already exist)
- ✅ No errors, exit code 0
- ✅ Payara restart tasks execute properly

**Files Changed:**
- `tasks/dataverse-optional-settings.yml`

---

## PR #3: Documentation - Ansible Dict Merging Gotcha

### Title
Document Ansible dict merging behavior for overriding nested variables

### Description

**Issue**

When overriding nested dictionary variables (like `dataverse.payara.listen_address`), Ansible replaces the entire parent dict instead of deep-merging. This can cause subtle bugs.

**Example Problem:**

`defaults/main.yml`:
```yaml
dataverse:
  payara:
    user: dataverse
    group: dataverse
    domain: domain1
    listen_address: 127.0.0.1
    # ... many more fields
```

`group_vars/testing.yml` (WRONG):
```yaml
dataverse:
  payara:
    listen_address: 0.0.0.0  # Oops! This replaces the ENTIRE payara dict
```

**Result:** All other payara settings (`user`, `group`, `domain`, etc.) are lost, breaking the deployment.

**Solution**

Must specify the complete nested dict:

`group_vars/testing.yml` (CORRECT):
```yaml
dataverse:
  payara:
    user: dataverse
    group: dataverse
    domain: domain1
    listen_address: 0.0.0.0  # Override only this
    # ... copy all other fields from defaults/main.yml
```

**Proposed Documentation**

Add a section to README or a new TESTING.md file explaining:
1. Ansible's dict replacement behavior
2. When this matters (nested dicts in defaults)
3. How to correctly override (copy full structure)
4. Common gotchas for Docker/molecule testing

Alternatively, add inline comments to `defaults/main.yml` warning about this:

```yaml
# NOTE: When overriding nested dicts (e.g., dataverse.payara), you must
# specify the COMPLETE dict structure. Ansible replaces the entire dict
# rather than deep-merging. See TESTING.md for details.
dataverse:
  payara:
    ...
```

**Benefit:**
- Prevents subtle bugs
- Helps developers using Docker/molecule testing
- Documents non-obvious Ansible behavior

**Files Changed:**
- `README.md` or new `TESTING.md` (documentation only)
- Optional: `defaults/main.yml` (add warning comments)

---

## Submission Strategy

**Recommendation:** Submit PR #1 and PR #2 together as a single "Fix idempotency for molecule testing" PR.

**Rationale:**
- Both are bugfixes
- Both enable the same use case (molecule testing)
- Both follow the same pattern (check state before action)
- Easier to review together

PR #3 is documentation-only and can be separate.

**Timing:**
- Wait for UCLA production deployment validation
- Submit after 1-2 weeks of stable operation
- Include testing evidence from molecule runs

**Draft Commit Message:**

```
Fix installation and JVM options idempotency for molecule testing

This enables the prepare.yml caching optimization and allows converge
to be run multiple times safely.

Fixes:
1. Solr installation - check if installed vs if downloaded
2. Payara installation - check if installed vs if downloaded
3. JVM options creation - check if exists before creating

Benefits:
- Enables prepare.yml caching (saves 570MB downloads)
- True idempotency for converge
- Supports full molecule testing workflow

Tested with molecule/docker:
- Fresh installations work correctly
- Re-running converge skips appropriately
- No errors, proper exit codes
- All services start correctly

Files changed:
- tasks/solr.yml
- tasks/payara.yml
- tasks/dataverse-optional-settings.yml
```

---

## Testing Evidence to Include

When submitting, include:
1. Molecule test output showing both fresh install and re-run
2. PLAY RECAP showing ok/changed counts
3. Verification that Dataverse starts and is accessible
4. Note about prepare.yml caching working correctly

Example:
```
First run:  ok=150 changed=45 failed=0
Second run: ok=150 changed=2  failed=0  (only changed: cache update tasks)

Solr download: skipped (already installed)
Payara download: skipped (already installed)
JVM options: skipped (already exist)

Dataverse accessible: ✅
API version check: ✅
```
