# UCLA Dataverse Ansible Documentation

For the standard deployment workflow, start with the [parent infrastructure repo](../../README.md) and its [RUNBOOK](../../docs/RUNBOOK.md). The docs here are Ansible-specific.

## Setup

- **[Secrets Management](setup/secrets_management.md)** - How we use Ansible Vault: inline encrypt_string, `.vault-password`, and the dev.yml/test.yml structure.
- **[Environment Configuration](setup/environment_configuration.md)** - group_vars strategy and Terraform integration.
- **[Monitoring](setup/monitoring.md)** - CloudWatch setup.

## Development

- **[Commands Reference](development/commands.md)** - pytest, make targets, vault encrypt, API health checks.
- **[Contributing](development/contributing.md)** - Branching strategy and PR standards.
- **[Team Guide](development/team_guide.md)** - Team practices: branching, deploy checklist, upstream sync.
- **[Fork Changelog](development/changelog.md)** - History of our improvements and fixes.
- **[Upstream Contributions](development/upstream_contributions.md)** - Draft PRs for the upstream project.

## Operations

- **[Troubleshooting](operations/troubleshooting.md)** - Common issues and fixes.
- **[Migration Guide (5.14 to 6.8)](operations/migration_guide.md)** - Detailed cutover and rollback procedures. Current phase status is in `.planning/ROADMAP.md`.

---

**Repository:** https://github.com/ucla-data-science-center/dataverse-ansible
**Branch:** `develop`
