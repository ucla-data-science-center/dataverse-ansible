# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Ansible role for deploying [Dataverse](https://dataverse.org), a research data repository platform. The role installs and configures all required components: Apache httpd (reverse proxy), Payara/GlassFish (Java EE application server), PostgreSQL (database), and Solr (search/indexing).

**Important**: The Dataverse installer is **not idempotent**. Running the playbook multiple times on the same host will fail. For testing iterations, fully destroy and recreate the environment.

## Development Environment Setup

This project uses Conda + pip-tools for Python dependency management, and Molecule with Docker for testing.

### Initial Setup

```bash
# Create conda environment
conda env create -f environment.yml
conda activate dataverse-ansible

# Install Python dependencies
pip-compile requirements.in
pip-sync

# Install Ansible collections (vendored locally)
make bootstrap
```

The `make bootstrap` command installs vendored collections from `collections/requirements.yml` into `./collections`. This project vendors specific versions of `community.general` (11.2.1) and `community.postgresql` (4.1.0).

## Testing with Molecule

### Run Full Test Cycle
```bash
molecule test -s rocky9
```

### Iterative Development
```bash
# Start/create the container and run the playbook
molecule converge -s rocky9

# Open a shell in the running container
molecule login -s rocky9

# Destroy the container (required between test runs due to non-idempotency)
molecule destroy -s rocky9
# or
molecule reset -s rocky9
```

Dataverse will be accessible at `http://localhost:8080` after a successful converge.

**Default credentials**:
- Username: `dataverseAdmin`
- Password: see `dataverse_adminpass` in `tests/group_vars/vagrant.yml`

### Molecule Configuration

The `rocky9` scenario (`molecule/rocky9/`) uses:
- **Driver**: Docker with a systemd-enabled Rocky Linux 9 image
- **Inventory**: Links to `group_vars/` for configuration
- **Playbooks**: `prepare.yml` (setup), `converge.yml` (main role execution)
- **Port mapping**: 8080:8080 for Dataverse API/UI access

## Running the Role

### Local Development with Vagrant
```bash
vagrant up
```
Access at `http://localhost:8880` (or check Vagrantfile for port mappings).

### Direct Ansible Playbook Execution

**Main playbook**: `dataverse.pb`

```bash
# Basic run
ansible-playbook -i <inventory> -e "@defaults/main.yml" dataverse.pb

# With specific tags
ansible-playbook -i <inventory> -e "@defaults/main.yml" dataverse.pb --tags "apache,postgres"

# Local connection mode (for single-host deployments)
ansible-playbook --connection=local -i inventory dataverse.pb -e "@defaults/main.yml"
```

## Architecture

### Role Structure

- **`tasks/main.yml`**: Orchestrates all task imports in dependency order
- **`tasks/`**: Individual task files for each component (apache, postgres, solr, payara, etc.)
- **`defaults/main.yml`**: Default configuration variables (override via group_vars or -e)
- **`templates/`**: Jinja2 templates for config files
- **`handlers/`**: Service restart handlers
- **`files/`**: Static files (branding, scripts, etc.)

### Key Components and Services

| Component | Location | Service Control |
|-----------|----------|-----------------|
| Apache httpd | `/etc/httpd/conf.d` | `systemctl {start\|stop\|restart} httpd` |
| Payara (GlassFish) | `/usr/local/payara5` | `systemctl {start\|stop\|restart} payara` |
| PostgreSQL | `/var/lib/pgsql/*/data/` | `systemctl {start\|stop\|restart} postgresql-*` |
| Solr | `/usr/local/solr` | `systemctl {start\|stop\|restart} solr` |

### Task Execution Flow

The role follows this high-level sequence (see `tasks/main.yml` for complete order):

1. **Sanity checks** - Validate environment
2. **Prerequisites** - Install system packages, configure firewall/SELinux
3. **Apache** - Install and configure reverse proxy
4. **PostgreSQL** - Install, initialize database, create users/schemas
5. **Dataverse source** - Clone/checkout repository (if building from source)
6. **Payara** - Install application server, configure JVM settings
7. **Solr** - Install and configure search index
8. **S3/Storage** - Configure storage backend (local/S3/MinIO/localstack)
9. **Dataverse installation** - Run the Dataverse installer
10. **Post-install** - Configure API settings, metadata blocks, authentication
11. **Optional features** - Shibboleth, sample data, previewers, external tools

### Configuration Architecture

**Configuration hierarchy** (highest precedence first):
1. Extra vars passed with `-e` at runtime
2. `group_vars/` files (environment-specific)
3. `defaults/main.yml` (role defaults)

**Key configuration variables**:
- `dataverse_branch`: Git branch to deploy (default: `release`)
- `dataverse_repo`: Source repository URL
- `apache.ssl.enabled`: Enable HTTPS
- `db.postgres.enabled`: Enable PostgreSQL installation
- `dataverse.adminpass`: Admin user password
- `dataverse.payara.siteurl`: Full public URL (critical for OAuth/OIDC)

## Vendored Collections

This project vendors Ansible collections locally in `./collections` to pin specific versions. The `ansible.cfg` sets `collections_path = ./collections:~/.ansible/collections:/usr/share/ansible/collections`.

**IMPORTANT**: When using modules from these collections, use Fully Qualified Collection Names (FQCN):
- `community.general.apache2_module` (not just `apache2_module`)
- `community.postgresql.postgresql_db` (not just `postgresql_db`)

If you encounter "module not found" errors, verify:
1. Collections are installed: `make bootstrap`
2. FQCNs are used in task files
3. `ansible.cfg` collections_path is correct

## Ansible Tags

Use tags to run specific portions of the role:

```bash
# Install only Apache
ansible-playbook dataverse.pb --tags "apache"

# Install prerequisites and PostgreSQL
ansible-playbook dataverse.pb --tags "prereqs,postgres"

# Skip time-consuming tasks
ansible-playbook dataverse.pb --skip-tags "sampledata"
```

Common tags: `prereqs`, `apache`, `postgres`, `solr`, `payara`, `dataverse`, `shibboleth`, `sampledata`

## Git Workflow (UCLA Fork)

**Main branch**: `develop` (not `main`)
**Branch naming**:
- `config/*` - Configuration changes (group_vars, defaults)
- `task/*` - Role task/template updates
- `doc/*` - Documentation

**Pull requests**: Target `develop` branch

```bash
# Create feature branch
git checkout -b task/fix-payara-config

# Create PR via GitHub CLI
gh pr create --base develop --fill
```

## Supported Platforms

- **RHEL/Rocky Linux 8, 9** (primary support)
- **Debian 11, 12** (supported)

The role auto-detects OS and includes appropriate task files (e.g., `postgres_redhat.yml` vs `postgres_debian.yml`).

## Troubleshooting

### Dataverse Installation Fails
- Check `/usr/local/payara5/glassfish/domains/domain1/logs/server.log`
- Verify PostgreSQL is running: `systemctl status postgresql-*`
- Ensure Solr is accessible: `curl http://localhost:8983/solr/`

### Collections Not Found
```bash
make bootstrap  # Reinstall vendored collections
```

### Port 8080 Already in Use (Molecule)
Edit `molecule/rocky9/molecule.yml` published_ports to use a different host port.

### Non-Idempotent Errors
The Dataverse installer cannot be run twice. Destroy and recreate:
```bash
molecule destroy -s rocky9
molecule converge -s rocky9
```
