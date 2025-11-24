# UCLA Dataverse Ansible - Quick Start Guide

This is UCLA's fork of the [IQSS Dataverse Ansible role](https://github.com/IQSS/dataverse-ansible) with improvements and UCLA-specific configurations.

**Repository:** https://github.com/ucla-data-science-center/dataverse-ansible
**Branch:** `develop` (our main branch)
**Upstream:** https://github.com/IQSS/dataverse-ansible

---

## 📚 Documentation Overview

We maintain several focused guides to help you work with this fork:

| Document | Purpose | Audience |
|----------|---------|----------|
| **[TEAM_GUIDE.md](TEAM_GUIDE.md)** | Complete team handbook - start here! | All team members |
| **[MOLECULE_QUICK_REF.md](MOLECULE_QUICK_REF.md)** | Quick reference for common commands | Developers |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Solutions to common issues | Everyone |
| **[CONFIG_STRATEGY.md](CONFIG_STRATEGY.md)** | Local vs AWS configuration approach | DevOps/Admins |
| **[FORK_IMPROVEMENTS.md](FORK_IMPROVEMENTS.md)** | Track our changes vs upstream | Maintainers |
| **[UPSTREAM_PR_DRAFT.md](UPSTREAM_PR_DRAFT.md)** | Ready-to-submit upstream PRs | Maintainers |

**👉 New team members: Start with [TEAM_GUIDE.md](TEAM_GUIDE.md)**

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- **Docker** - Must be running before you start
- **Git** - To clone this repository

### 1. Clone and Bootstrap

```bash
# Clone the repository
git clone https://github.com/ucla-data-science-center/dataverse-ansible.git
cd dataverse-ansible

# Bootstrap the project (installs uv, Python, dependencies, collections)
make bootstrap
```

The `make bootstrap` command:
- Installs [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- Sets up Python 3.11 virtual environment
- Installs Ansible and Molecule dependencies
- Vendors Ansible collections (community.general 11.2.1, community.postgresql 4.1.0)

### 2. Test Locally with Molecule

```bash
# Deploy Dataverse in a local Docker container
uv run molecule converge -s rocky9

# Access Dataverse at http://localhost:8080
# Default admin: dataverseAdmin / (see group_vars for password)
```

**That's it!** For detailed usage, see [MOLECULE_QUICK_REF.md](MOLECULE_QUICK_REF.md).

---

## 🎯 Common Tasks

### Local Testing
```bash
# Fresh deployment
uv run molecule destroy -s rocky9
uv run molecule converge -s rocky9

# Run tests
uv run pytest molecule/rocky9/tests/ -v

# Interactive debugging
docker exec -it rocky9 /bin/bash
```

See [MOLECULE_QUICK_REF.md](MOLECULE_QUICK_REF.md) for more commands.

### Deploy to AWS
```bash
# Review configuration differences
diff molecule/rocky9/group_vars/molecule.yml group_vars/aws.yml

# Deploy to staging
ansible-playbook -i inventory/staging site.yml
```

See [CONFIG_STRATEGY.md](CONFIG_STRATEGY.md) for configuration details.

### Troubleshooting
- **Port 8080 in use?** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#port-8080-already-in-use)
- **Dataverse not accessible?** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#dataverse-not-accessible-from-localhost)
- **Container won't start?** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#container-wont-start-cgroup-errors)

---

## 🔧 Our Fork Improvements

We've made several improvements that will be contributed back to upstream:

### ✅ Idempotency Fixes (Completed)
1. **Solr Installation** - Can now run converge multiple times safely
2. **Payara Installation** - Pre-cached downloads work correctly
3. **JVM Options** - No errors on re-runs
4. **prepare.yml Support** - Saves 570MB on repeated runs

### ✅ Testing Infrastructure (Completed)
- **16 testinfra tests** covering services, ports, health, security
- All tests passing in CI/molecule workflow

### ✅ UCLA Branding & Customization (Completed)
- **Custom header, footer, homepage** - UCLA Library themed pages
- **UCLA logo** - Combined UCLA letterforms + "Dataverse" wordmark
- **Favicons** - UCLA-themed 2-ring Dataverse icons
- **CSS overrides** - Collection/dataset/file icons in UCLA colors
- **Support portal integration** - NavbarSupportUrl points to UCLA Jira
- **Metadata blocks** - HELADA (heritage language), geospatial, social science, astrophysics, biomedical, journals
- **Language packs** - English, Spanish, Chinese, Japanese, Korean
- **Sample data API** - Reliable API-based sample data creation

### 📝 Documentation (Completed)
- Comprehensive troubleshooting guide
- Configuration strategy docs
- Ansible dict merging gotchas documented

See [FORK_IMPROVEMENTS.md](FORK_IMPROVEMENTS.md) for complete details.

---

## 🔄 Syncing with Upstream

We regularly sync with upstream to get latest updates:

```bash
# Add upstream remote (one time)
git remote add upstream https://github.com/IQSS/dataverse-ansible.git

# Check for upstream updates
git fetch upstream
git log develop..upstream/develop

# Merge upstream changes
git checkout develop
git merge upstream/develop
git push origin develop
```

**Always test after merging upstream changes!**

See [TEAM_GUIDE.md](TEAM_GUIDE.md#syncing-with-upstream) for details.

---

## 📋 Development Workflow

1. **Create feature branch** from `develop`
2. **Test locally** with molecule
3. **Run tests**: `uv run pytest molecule/rocky9/tests/ -v`
4. **Create PR** to `develop`
5. **Deploy to staging** after merge
6. **Deploy to production** after staging validation

See [TEAM_GUIDE.md](TEAM_GUIDE.md#development-workflow) for complete workflow.

---

## 🏗️ Repository Structure

```
dataverse-ansible/
├── tasks/              # Ansible role tasks (Solr, Payara, etc.)
├── defaults/           # Default variables
├── group_vars/         # Environment-specific configs
│   └── aws.yml        # AWS/production configuration
├── molecule/           # Testing scenarios
│   └── rocky9/        # Local Docker testing
│       ├── group_vars/ # Local test configuration
│       └── tests/     # Testinfra test suite
├── collections/        # Vendored Ansible collections
├── Makefile           # Bootstrap and utility commands
└── docs/              # Documentation (guides, references)
```

---

## 📞 Getting Help

### Team Resources
- **Slack:** #dataverse channel
- **GitHub Issues:** https://github.com/ucla-data-science-center/dataverse-ansible/issues
- **Documentation:** Start with [TEAM_GUIDE.md](TEAM_GUIDE.md)

### Upstream Resources
- **Dataverse Guides:** https://guides.dataverse.org/
- **Upstream Repo:** https://github.com/IQSS/dataverse-ansible
- **Community Forum:** https://groups.google.com/g/dataverse-community

---

## 🔗 Quick Links

| Resource | Link |
|----------|------|
| Production Instance | https://dataverse.ucla.edu |
| GitHub Issues | https://github.com/ucla-data-science-center/dataverse-ansible/issues |
| Upstream Repo | https://github.com/IQSS/dataverse-ansible |
| Dataverse Docs | https://guides.dataverse.org/ |
| uv Documentation | https://docs.astral.sh/uv/ |
| Molecule Docs | https://ansible.readthedocs.io/projects/molecule/ |

---

## 📝 Notes

- **Main branch:** `develop` (we follow upstream's convention)
- **Python version:** 3.11 (managed by uv via `.python-version`)
- **Vendored collections:** We vendor collections locally (don't rely on `ansible-galaxy install`)
- **Docker required:** Local testing uses Docker via Molecule
- **Improved idempotency:** We've made the role more idempotent (Solr, Payara, JVM options)

---

## 🤝 Contributing

See [UCLA-CONTRIBUTING.md](UCLA-CONTRIBUTING.md) for contribution guidelines.

For upstream contributions, see [UPSTREAM_PR_DRAFT.md](UPSTREAM_PR_DRAFT.md).

---

**Last Updated:** 2025-11-17
**Maintained by:** UCLA Data Science Center
