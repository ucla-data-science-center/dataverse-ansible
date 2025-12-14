# Fork Improvements Log

This document tracks improvements made to the UCLA fork that may be contributed upstream later.

## Let's Encrypt SSL Refactoring

**Date:** 2025-12-01
**Files Modified:** `tasks/certbot.yml`, `tasks/dataverse-apache.yml`, `templates/http.proxy.conf.j2`, `group_vars/staging.yml`
**Issue:** Complex SSL setup with manual Apache reconfiguration and non-standard certbot usage

### Problem

The original certbot implementation used `certbot certonly --standalone` mode with extensive manual configuration:

```yaml
# Original approach
- name: Stop services to allow certbot to generate a cert
  ansible.builtin.service:
    name: httpd
    state: stopped

- name: Generate new certificate
  command: 'certbot certonly --standalone ...'

- name: Enable SSL in apache config now that we have certificates
  ansible.builtin.set_fact:
    apache: "{{ apache | combine({'ssl': {'enabled': true}}) }}"

- name: Regenerate Apache config to use certificates
  template:
    src: http.proxy.conf.j2
    dest: "{{ apache_virtualhost_dir }}/http.proxy.conf"

- name: Start services after cert has been generated
  ansible.builtin.service:
    name: httpd
    state: started
```

**Issues:**
1. **Non-standard approach** - Used standalone mode instead of Apache plugin
2. **Manual configuration** - Required explicit Apache config regeneration
3. **State management** - Used `set_fact` to enable SSL in memory (not persisted)
4. **Complexity** - ~30 lines of code for certificate generation
5. **Service disruption** - Manually stopped/started Apache
6. **Renewal concerns** - Renewals might not update Apache config properly

### Solution

Refactored to use standard `certbot --apache` plugin with two-stage deployment:

```yaml
# New approach (simplified)
- name: Check if certificate already exists
  ansible.builtin.stat:
    path: /etc/letsencrypt/live/{{ servername }}/cert.pem
  register: letsencrypt_cert

- name: Generate certificate and configure Apache automatically
  ansible.builtin.command: 'certbot --apache --noninteractive --agree-tos --email {{ letsencrypt.certbot.email }} -d {{ servername }} --redirect'
  when: not letsencrypt_cert.stat.exists
```

**Template improvements:**
```jinja2
# Added Let's Encrypt certificate path support
{% if letsencrypt is defined and letsencrypt.enabled %}
  SSLCertificateFile /etc/letsencrypt/live/{{ servername }}/fullchain.pem
  SSLCertificateKeyFile /etc/letsencrypt/live/{{ servername }}/privkey.pem
{% elif apache.ssl.remote_cert %}
  # ... existing certificate handling
{% endif %}
```

**Deployment process:**
```yaml
# Stage 1 - Deploy with HTTP
apache.ssl.enabled: false
letsencrypt.enabled: false

# Stage 2 - Enable HTTPS (run playbook again)
apache.ssl.enabled: true
letsencrypt.enabled: true
```

### Benefits

1. **Standard approach** - Uses certbot's native Apache plugin
2. **Automatic configuration** - Certbot configures Apache VirtualHost
3. **Automatic redirect** - HTTP→HTTPS redirect via `--redirect` flag
4. **Less code** - Reduced from ~30 lines to ~10 lines
5. **Better renewals** - Certbot knows how to renew Apache configs
6. **Follows best practices** - Uses documented certbot workflow
7. **Two-stage deployment** - Clear separation of HTTP and HTTPS setup
8. **Idempotent** - Safe to run playbook multiple times

### Testing

Tested with:
- ✅ Fresh staging deployment (staging.ucladataverse.dev)
- ✅ Let's Encrypt certificate obtained successfully
- ✅ Apache configured automatically
- ✅ HTTP→HTTPS redirect working
- ✅ Certbot-renew.timer enabled for auto-renewal
- ✅ Re-running playbook is idempotent (skips if cert exists)

### Documentation

Created comprehensive documentation:
- **DEPLOYMENT_GUIDE.md** - Step-by-step for new deployments
- **REFACTORING_NOTES.md** - Technical details of changes
- **group_vars/TEMPLATE.yml** - Template for new environments
- **group_vars/staging.yml** - Two-stage deployment instructions

### Upstream Contribution

**Status:** Ready for upstream consideration
**Justification:** Simplifies SSL setup, follows certbot best practices, reduces complexity
**Compatibility:** Backward compatible - existing deployments unaffected
**Trade-offs:** Requires two-stage deployment for new instances (acceptable pattern)

---

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

## Payara Installation Idempotency Fix

**Date:** 2025-11-16
**Files Modified:** `tasks/payara.yml`
**Issue:** Same idempotency bug as Solr

### Problem

Identical pattern to Solr - extraction conditional on download changing:

```yaml
- name: download payara zip
  get_url:
    url: '{{ dataverse.payara.zipurl }}'
    checksum: '{{ dataverse.payara.zipchecksum }}'
    dest: /tmp/payara.zip
  register: payara_zip_download

- name: unzip to payara root without name/version tld
  shell: 'bsdtar --strip-components=1 -C {{ payara_dir }} -xf /tmp/payara.zip'
  when: payara_zip_download.changed  # ← PROBLEM
```

### Solution

Added stat check for Payara installation:

```yaml
- name: check if payara is already installed
  stat:
    path: "{{ payara_dir }}/glassfish/bin/asadmin"
  register: payara_installed

- name: download payara zip
  get_url: ...
  when: not payara_installed.stat.exists

- name: unzip to payara root without name/version tld
  shell: ...
  when: not payara_installed.stat.exists
```

### Benefits

Same as Solr fix - enables prepare.yml caching for Payara (~200MB download)

---

## JVM Options Idempotency Fix

**Date:** 2025-11-16
**Files Modified:** `tasks/dataverse-optional-settings.yml`
**Issue:** JVM option creation tasks were not idempotent

### Problem

Several tasks used `create-jvm-options` without checking if the option already exists:

```yaml
- name: upload to /tmp until we move away from JSF
  become: yes
  become_user: "{{ dataverse.payara.user }}"
  shell: '{{ payara_dir}}/bin/asadmin create-jvm-options "-Ddataverse.files.uploads={{ dataverse.uploads_dir }}"'
  when: dataverse.uploads_dir is defined  # ← PROBLEM: No existence check
```

**This breaks on re-runs:**
- First converge: Creates JVM option successfully
- Second converge: Fails with "JVM option already exists in the configuration"
- Caused idempotency test to fail

### Solution

Added existence checks before each `create-jvm-options` command:

```yaml
- name: check if uploads directory JVM option exists
  shell: "{{ payara_dir }}/bin/asadmin list-jvm-options | grep -q 'Ddataverse.files.uploads'"
  register: has_uploads_dir
  failed_when: false
  changed_when: false
  when: dataverse.uploads_dir is defined

- name: upload to /tmp until we move away from JSF
  become: yes
  become_user: "{{ dataverse.payara.user }}"
  shell: '{{ payara_dir}}/bin/asadmin create-jvm-options "-Ddataverse.files.uploads={{ dataverse.uploads_dir }}"'
  when: dataverse.uploads_dir is defined and has_uploads_dir.rc != 0
```

**Fixed options:**
- `dataverse.files.uploads`
- `dataverse.oai.server.maxidentifiers`
- `dataverse.oai.server.maxrecords`
- `dataverse.feature.index-harvested-metadata-source`

### Benefits

1. **True idempotency** - Can run converge multiple times without errors
2. **Completes full playbook** - No longer aborts on second run
3. **Enables full testing** - Payara restart tasks now execute properly
4. **Follows existing pattern** - Task file already had correct example (system email JVM option)

---

## Ansible Dict Merging Fix (Payara listen_address)

**Date:** 2025-11-16
**Files Modified:** `molecule/rocky9/group_vars/molecule.yml`, `TROUBLESHOOTING.md`
**Issue:** Ansible doesn't deep-merge nested dicts

### Problem

Attempted to override only `dataverse.payara.listen_address`:

```yaml
# WRONG - This replaces the entire payara dict!
dataverse:
  payara:
    listen_address: 0.0.0.0
```

**What happened:**
- Ansible replaced the ENTIRE `dataverse.payara` dict
- Lost all other settings: `user`, `group`, `domain`, `zipurl`, etc.
- Payara installation broke due to missing variables

### Solution

Must specify the complete `dataverse.payara` section:

```yaml
# CORRECT - Full dict with all fields from defaults/main.yml
dataverse:
  payara:
    user: dataverse
    group: dataverse
    domain: domain1
    logformat: ulf
    adminuser: admin
    adminpass: notPr0d
    siteurl:
    listen_address: 0.0.0.0  # Our override
    launch_timeout: 180
    request_timeout: 1800
    root: /usr/local
    dir: payara6
    zipurl: https://nexus.payara.fish/repository/payara-community/fish/payara/distributions/payara/6.2025.3/payara-6.2025.3.zip
    zipchecksum: sha256:88f5c1e5b40ea4bc60ae3e34e6858c1b33145dc06c4b05c3d318ed67c131e210
```

### Impact

- ✅ Payara listens on `0.0.0.0` (all interfaces)
- ✅ Docker port mapping works
- ✅ Dataverse accessible at `localhost:8080` from host
- 📚 Documented in TROUBLESHOOTING.md for future reference

---

## Future Improvements to Track

### Non-idempotent Dataverse Installer

**File:** `tasks/dataverse-installer.yml` (assumed)
**Issue:** Installer cannot be run twice on same database
**Current approach:** Always destroy + converge for testing
**Potential upstream:** Add check for existing installation, skip if present

### Non-idempotent Dataverse Installer

**File:** `tasks/dataverse-installer.yml` (assumed)
**Issue:** Installer cannot be run twice on same database
**Current approach:** Always destroy + converge for testing
**Potential upstream:** Add check for existing installation, skip if present

### Shibboleth Configuration Idempotency ✅ FIXED

**Date:** 2025-11-20
**Files Modified:** `tasks/shibboleth.yml:92-109`
**Issue:** Same `when: download.changed` pattern as Solr/Payara

### Problem

The task registered Shibboleth auth provider based on file download state:

```yaml
- name: get shibAuthProvider.json to host
  get_url:
    url: http://guides.dataverse.org/.../shibAuthProvider.json
    dest: /tmp/shibAuthProvider.json
  register: shibAuthProvider_json_download

- name: enable shibboleth authentication in dataverse
  uri:
    url: http://localhost:8080/api/admin/authenticationProviders
    method: POST
    src: /tmp/shibAuthProvider.json
  when: shibAuthProvider_json_download.changed  # ← PROBLEM
```

**This breaks when:**
- File already exists (download changed=false, registration skipped)
- Re-running converge causes duplicate provider errors
- Not truly idempotent

### Solution

Check Dataverse API for existing provider:

```yaml
- name: get shibAuthProvider.json to host
  get_url:
    url: http://guides.dataverse.org/.../shibAuthProvider.json
    dest: /tmp/shibAuthProvider.json

- name: check if shibboleth authentication provider already exists
  uri:
    url: http://localhost:8080/api/admin/authenticationProviders
    method: GET
    return_content: yes
  register: existing_auth_providers
  failed_when: false
  changed_when: false

- name: enable shibboleth authentication in dataverse
  uri:
    url: http://localhost:8080/api/admin/authenticationProviders
    method: POST
    src: /tmp/shibAuthProvider.json
    body_format: json
    remote_src: yes
    status_code: 201
  when: existing_auth_providers.status == 200 and
        (existing_auth_providers.json.data | selectattr('id', 'equalto', 'shib') | list | length == 0)
```

### Benefits

1. ✅ **True idempotency** - Can run multiple times safely
2. ✅ **Works with pre-downloaded files** - Doesn't depend on download state
3. ✅ **Proper state checking** - Checks actual Dataverse API state
4. ✅ **No duplicate provider errors** on re-run
5. ✅ **Follows same pattern** as Solr/Payara/Log4j fixes

### Log4j CVE Mitigation ✅ FIXED

**Date:** 2025-11-20
**Files Modified:** `tasks/solr.yml:80-92`
**Issue:** Attempts to remove JndiLookup.class already removed in Solr 9.8+
**Old behavior:** `ignore_errors: yes` suppresses failure

### Problem

The task tried to remove `JndiLookup.class` from log4j to mitigate CVE-2021-44228:

```yaml
- name: remove JndiLookup.class from log4j-core.jar
  ansible.builtin.shell:
    cmd: 'zip -q -d {{ dataverse.solr.root }}/server/lib/ext/log4j-core-*.jar org/apache/logging/log4j/core/lookup/JndiLookup.class'
  become: yes
  become_user: root
  ignore_errors: yes  # ← PROBLEM: Masks all errors
```

**This breaks when:**
- Newer Solr versions (9.8+) already removed the vulnerable class
- Command fails with "nothing to do" error
- `ignore_errors: yes` masks real problems

### Solution

Added existence check before removal:

```yaml
- name: check if JndiLookup.class exists in log4j-core.jar
  ansible.builtin.shell:
    cmd: 'unzip -l {{ dataverse.solr.root }}/server/lib/ext/log4j-core-*.jar | grep -q JndiLookup.class'
  register: jndilookup_check
  failed_when: false
  changed_when: false

- name: remove JndiLookup.class from log4j-core.jar
  ansible.builtin.shell:
    cmd: 'zip -q -d {{ dataverse.solr.root }}/server/lib/ext/log4j-core-*.jar org/apache/logging/log4j/core/lookup/JndiLookup.class'
  become: yes
  become_user: root
  when: jndilookup_check.rc == 0  # Only run if class exists
```

### Benefits

1. ✅ **Clean output** - No more "failed" messages on newer Solr
2. ✅ **Real error detection** - If removal fails when class exists, we'll know
3. ✅ **Works with any Solr version** - Old or new
4. ✅ **True idempotency** - Check state before action
5. ✅ **Follows Ansible best practices**

---

## Documentation Added

- `TROUBLESHOOTING.md` - Common Molecule/Docker issues and solutions
- `CONFIG_STRATEGY.md` - Local testing vs AWS deployment configuration strategy
- `FORK_IMPROVEMENTS.md` - This file, tracking fork-specific improvements
- Updated `CLAUDE.md` - AI assistant context with uv workflow

## Molecule/Docker Testing Improvements

### Docker Container Preparation ✅ FIXED

**Date:** 2025-11-20
**Files Modified:** `molecule/rocky9/prepare.yml`

**Problem:** Minimal Docker containers don't have `sudo` or `which` commands that the playbook expects.

**Solution:** Install required utilities in prepare phase:
```yaml
- name: Install sudo and which (required for Docker containers)
  ansible.builtin.raw: dnf install -y sudo which
  changed_when: false
```

### Site.yml Playbook Role Inclusion ✅ FIXED

**Date:** 2025-11-20
**Files Modified:** `site.yml:44-54`

**Problem:** `role: .` syntax doesn't work properly with Ansible.

**Solution:** Use `include_role` with `playbook_dir` variable:
```yaml
tasks:
  - name: Include dataverse role tasks
    ansible.builtin.include_role:
      name: "{{ playbook_dir }}"
      apply:
        tags: all
```

### Group Vars File Naming ✅ FIXED

**Date:** 2025-11-20
**Files Modified:** `molecule/rocky9/group_vars/`

**Problem:** Variables file was named `molecule.yml` but needed to be `all.yml` or match inventory group name.

**Solution:** Renamed `molecule.yml` → `all.yml` to apply to all hosts in inventory.

## Tooling Improvements

- Migrated from conda + pip-tools to **uv** for dependency management
- Vendored Ansible collections (community.general 11.2.1, community.postgresql 4.1.0)
- Added `Makefile` with `bootstrap` target for collection installation
- Created `.python-version` for consistent Python 3.11 usage
- Updated `.gitignore` for uv virtual environments
- **Fixed molecule/Docker testing** - prepare.yml, site.yml, group_vars structure

---

## UCLA Branding and Customization ✅ COMPLETED

**Date:** 2025-11-24
**Files Modified:** Multiple branding files, defaults/main.yml, tasks/dataverse-gui.yml, tasks/dataverse-optional-settings.yml
**Purpose:** Full UCLA Library themed Dataverse instance

### Custom Branding Files

Created complete UCLA branding matching library.ucla.edu design:

**New Files:**
- `files/branding/custom-header.html` - UCLA Library themed header
- `files/branding/custom-footer.html` - UCLA footer with social links, service portal links
- `files/branding/custom-homepage.html` - UCLA Dataverse homepage
- `files/branding/custom-stylesheet.css` - UCLA colors (#2774AE blue, #FFD100 gold, #003B5C dark blue)
- `files/branding/logo_UCLA_Dataverse.svg` - Combined UCLA letterforms + "Dataverse" wordmark
- `files/branding/dataverseUCLA_logo.png` - PNG version for header (172x50px)

**Favicon Files:**
- `files/favicons/favicon.ico` - Multi-resolution .ico file
- `files/favicons/favicon-16x16.png` - Small icon
- `files/favicons/favicon-32x32.png` - Standard icon
- `files/favicons/apple-touch-icon.png` - iOS home screen (180x180)
- `files/favicons/dataverse_2ring_ucla.svg` - UCLA-themed 2-ring icon (source)

### Metadata Blocks Configuration

Added comprehensive metadata block support in `defaults/main.yml`:

```yaml
custom_metadata_blocks:
  enabled: true
  urls:
    - CodeMeta (software/code)
    - HELADA (UCLA heritage language custom block)
    - Geospatial
    - Social Science & Humanities
    - Astrophysics
    - Biomedical/Life Sciences
    - Journals
```

**UCLA Custom Block:**
- https://github.com/ucla-data-science-center/dataverse-custom-metadata
- HELADA metadata for Heritage Language Institute
- 16 specialized fields for language research data

### Language Packs

Expanded language support for UCLA's diverse community:

```yaml
language:
  enabled: true
  languages:
   - English (en_US)
   - Spanish (es_ES)
   - Chinese Simplified (zh_CN)  # NEW
   - Japanese (ja_JP)            # NEW
   - Korean (ko_KR)              # NEW
```

### Support Portal Integration

Integrated UCLA Jira service portal:

**Configuration (`defaults/main.yml`):**
```yaml
branding:
  support_url: "https://uclalibrary.atlassian.net/servicedesk/customer/portal/5/group/13/create/46"
```

**Implementation (`tasks/dataverse-optional-settings.yml`):**
```yaml
- name: set NavbarSupportUrl to UCLA Jira service portal
  uri:
    url: "{{ dataverse.api.location }}/admin/settings/:NavbarSupportUrl"
    method: PUT
    body: "{{ dataverse.branding.support_url }}"
    status_code: 200
  when: dataverse.branding.support_url is defined
```

**Result:** "Support" navbar link now opens UCLA Library Jira portal instead of built-in contact form.

### CSS Icon Color Overrides

Custom CSS to change Dataverse icon colors from burnt orange to UCLA blue:

```css
/* Collection icons: UCLA blue */
.icon-dataverse, .text-dataverse {
    color: #2774AE !important;
}

/* Dataset icons: UCLA dark blue */
.icon-dataset, .text-dataset {
    color: #003B5C !important;
}

/* File icons: neutral grey */
.icon-file, .text-file {
    color: #757575 !important;
}
```

**Method:** CSS overrides (modern approach) instead of deprecated FontCustom icon font generation.

### Root Dataverse Customization

Added ability to customize root dataverse metadata instead of generic "Root" name:

**New File:** `tasks/dataverse-root-customize.yml`

**Configuration:**
```yaml
root:
  name: "UCLA Dataverse"
  affiliation: "UCLA Library"
  description: "UCLA Dataverse is a repository for research data and related materials produced by the UCLA community. Powered by the open-source Dataverse software."
```

**Implementation:**
- Uses PUT `/api/dataverses/root` to update metadata
- Runs after GUI branding, before sample data
- Tags: `root`, `branding`

**Note:** The alias "root" cannot be changed (Dataverse requirement), but name, affiliation, and description can be customized for institutional branding.

### Sample Data API Implementation

Created reliable API-based sample data instead of fragile Python script:

**New File:** `tasks/sampledata-api.yml`

**Configuration:**
```yaml
sampledata:
  enabled: false
  use_api: true  # Use API instead of Python script
  collection_name: "UCLA Data Science Center"
  collection_alias: "ucla-dsc"
  collection_description: "Research data from the UCLA Library Data Science Center."
  contact_email: "datascience@library.ucla.edu"
  affiliation: "UCLA Library"
```

**Benefits:**
- ✅ No Python dependencies or virtualenv issues
- ✅ Uses Dataverse REST API directly via Ansible `uri` module
- ✅ Creates collection + 2 sample datasets
- ✅ Reliable for testing and demos

### Branding Deployment Fixes

Fixed critical path issue in `tasks/dataverse-gui.yml`:

**Problem:** LogoCustomizationFile needs **URL path**, other settings need **filesystem paths**.

**Solution:**
```yaml
# Most branding files use filesystem paths
- name: Update branding file settings (filesystem paths)
  uri:
    body: '{{ gui_file_path }}/branding/{{ item.file }}'
  when: item.setting != 'LogoCustomizationFile'

# Logo is the exception - needs URL path
- name: Update logo setting (URL path)
  uri:
    body: '/branding/{{ dataverse.branding.logoFile }}'
  when: item.setting == 'LogoCustomizationFile'
```

### OAI-PMH Harvesting Client Configuration

Added automated configuration for OAI-PMH harvesting clients to import metadata from remote repositories:

**New File:** `tasks/dataverse-harvest-clients.yml`

**Configuration:**
```yaml
harvest_clients:
  - nickname: "social-science-data-archive"
    server_url: "https://dataverse.harvard.edu/oai"
    oai_set: "UCLA_SSDA"
    metadata_format: "oai_ddi"
    schedule: false  # On-demand only
    archive_type: "dataverse"
    archive_url: "https://dataverse.harvard.edu"
    dataverse_alias: "root"
```

**Implementation:**
- Uses POST `/api/harvest/clients` with correct field names from HarvestingClient model
- Supports scheduling (daily/weekly), custom HTTP headers, multiple clients
- Tags: `harvest`, `harvestclients`

**Use Case:** UCLA's historic Social Science Data Archive (SSDA) collection is hosted at Harvard Dataverse. This configuration makes those datasets searchable within UCLA Dataverse while maintaining links to the original Harvard source.

### Benefits

1. **Complete UCLA branding** - Header, footer, logo, colors match library.ucla.edu
2. **Comprehensive metadata support** - 7 metadata blocks for diverse research needs
3. **Multilingual interface** - Serves UCLA's international community
4. **Integrated support** - Direct link to UCLA service portal
5. **Reliable testing** - API-based sample data works consistently
6. **Professional appearance** - UCLA-themed favicons and icons
7. **Automated harvesting** - Historic SSDA collection from Harvard Dataverse

### Upstream Contribution

**Status:** UCLA-specific customization, not for upstream
**Reasoning:**
- Branding files are institution-specific
- Configuration pattern (support_url, metadata blocks, languages) could be useful examples
- Sample data API approach could benefit upstream as an alternative to Python script

---

## Contribution Strategy

1. **Improve in fork first** - Test thoroughly in UCLA environment
2. **Document all changes** - Track in this file with justification
3. **After stable deployment** - Bundle logical improvements into upstream PRs
4. **Prioritize for upstream:**
   - Bug fixes (like Solr idempotency)
   - Docker/Molecule testing improvements
   - Documentation enhancements
