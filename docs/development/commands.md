# Commands Reference

Quick reference for day-to-day work on the UCLA Dataverse Ansible repo. Molecule/Docker commands are not included here — those are for local role development, not the standard AWS deployment path.

## Setup

```bash
uv sync               # install Python deps and create .venv
make bootstrap        # install vendored Ansible collections into ./collections
```

## Running tests against a live instance

All test commands run from inside `dataverse-ansible/`. The instance must be up and Ansible-deployed before these work.

```bash
# Full integration suite
uv run pytest tests/integration -v \
  --dataverse-url=https://staging.ucladataverse.dev

# Smoke tests only (no DB access needed)
uv run pytest tests/integration/test_smoke.py -v \
  --dataverse-url=https://staging.ucladataverse.dev

# Migration tests (requires DB credentials)
uv run pytest tests/integration/test_migration.py -v \
  --dataverse-url=https://staging.ucladataverse.dev \
  --db-host=<rds-endpoint> \
  --db-user=postgres \
  --db-password=<password>

# With an API token (needed for admin endpoint tests)
uv run pytest tests/integration -v \
  --dataverse-url=https://staging.ucladataverse.dev \
  --api-token=<admin-api-token>
```

Or use the Makefile targets from the repo root:

```bash
make test ENV=tim
make test-smoke ENV=tim
make test-migration ENV=tim DB_HOST=<rds> DB_PASS=<pass>
```

## Ansible Vault — encrypting secrets

Secrets in `group_vars/dev.yml` and `group_vars/test.yml` use inline vault-encrypted strings. Run these from inside `dataverse-ansible/`:

```bash
# Encrypt a new secret value
ansible-vault encrypt_string 'the-secret-value' \
  --name variable_name \
  --encrypt-vault-id default \
  --vault-password-file .vault-password
```

Copy the full output block (starting with `!vault |`) into the group_vars file, replacing the existing value. The `.vault-password` file is gitignored and must be backed up externally.

## API health checks

```bash
# Version check
curl -s https://staging.ucladataverse.dev/api/info/version | jq

# Root dataverse
curl -s https://staging.ucladataverse.dev/api/dataverses/root | jq

# Search
curl -s "https://staging.ucladataverse.dev/api/search?q=*" | jq
```

## Dependency management

```bash
uv add <package>          # add a new dependency
uv lock --upgrade         # update all deps
uv sync                   # sync .venv with uv.lock (run after git pull)
```
