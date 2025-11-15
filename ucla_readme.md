## Local Setup (Recommended)

These instructions assume:

- You have already cloned this repository locally:

    ```bash
    git clone https://github.com/ucla-data-science-center/dataverse-ansible.git
    cd dataverse-ansible
    ```

- Docker is installed and running on your system.

---

### 1. Install uv

[uv](https://docs.astral.sh/uv/) is a fast Python package and project manager that handles everything: Python installation, virtual environments, and dependency management.

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Or install via Homebrew (macOS):**
```bash
brew install uv
```

After installation, restart your terminal or run:
```bash
source ~/.bashrc  # or ~/.zshrc
```

---

### 2. Set Up the Development Environment

uv will automatically:
- Install Python 3.11 (if not already available)
- Create a virtual environment in `.venv`
- Install all dependencies from `pyproject.toml`

```bash
uv sync
```

This installs:
- `ansible-core` (2.16.6)
- `molecule` (24.2.1)
- `molecule-docker` (2.1.0)
- `docker` Python SDK
- All transitive dependencies

---

### 3. Install Ansible Collections

The project vendors specific versions of Ansible collections locally:

```bash
make bootstrap
```

This installs:
- `community.general` (11.2.1)
- `community.postgresql` (4.1.0)

---

## Running with Molecule and Docker

The `rocky9` Molecule scenario uses Docker as a provisioner. It relies on a custom image with `systemd` support, allowing `sudo` commands to run inside the container. This avoids modifying the Ansible role's privilege escalation behavior.

From the root of the cloned repository, run:

```bash
uv run molecule converge --scenario-name rocky9
```

Or, activate the virtual environment and run commands directly:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run molecule
molecule converge --scenario-name rocky9
```

This will build a Docker container, install Dataverse, and configure services.

Once complete, you should be able to access Dataverse at:

    http://localhost:8080

**Default admin login:**

- **Username**: `dataverseAdmin`
- **Password**: defined in `tests/group_vars/vagrant.yml` (see `dataverse_adminpass`)

To verify the server is responding:

```bash
curl -I http://localhost:8080
```

---

## Common Development Commands

### Run Molecule scenarios
```bash
# Full test cycle (destroy, create, converge, verify, destroy)
uv run molecule test --scenario-name rocky9

# Just create and provision (for iterative development)
uv run molecule converge --scenario-name rocky9

# Login to the running container
uv run molecule login --scenario-name rocky9

# Destroy the container
uv run molecule destroy --scenario-name rocky9
```

### Manage dependencies
```bash
# Add a new dependency
uv add ansible-core@2.17.0

# Update all dependencies
uv lock --upgrade

# Sync environment after pulling changes
uv sync
```

### Run Ansible directly
```bash
# Check version
uv run ansible --version

# Run a playbook
uv run ansible-playbook dataverse.pb -i inventory
```

---

## Teardown and Rebuild

Because the Dataverse installer is not idempotent, it's recommended to fully reset the container between changes.

To stop and delete the container:

```bash
uv run molecule destroy --scenario-name rocky9
```

Then rebuild with:

```bash
uv run molecule converge --scenario-name rocky9
```

---

## Troubleshooting

### Python version mismatch
uv automatically uses Python 3.11 as specified in `.python-version`. If you have issues:

```bash
# Check which Python uv is using
uv python list

# Force uv to use a specific Python version
uv python install 3.11
```

### Dependencies out of sync
```bash
# Remove virtual environment and reinstall
rm -rf .venv
uv sync
```

### Port 8080 already in use
Edit `molecule/rocky9/molecule.yml` and change the published port mapping from `"8080:8080"` to another host port like `"8888:8080"`.

---

## Notes

- Ensure Docker Desktop (macOS) or the Docker daemon (Linux/WSL2) is running before launching `molecule converge`.
- The `.venv` directory is git-ignored and should not be committed.
- `uv.lock` is the lockfile that pins exact versions - commit this for reproducibility.
- For more uv documentation: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

---
