# Contributing

This repository is the UCLA Library fork of [`gdcc/dataverse-ansible`](https://github.com/gdcc/dataverse-ansible),
which is licensed under the GNU General Public License v3.0 (GPL-3.0).

**GPL-3.0 is a copyleft license.** Any modifications or contributions to this repository
must also be distributed under GPL-3.0. If you contribute a change, you are agreeing
to license it under the same terms.

For full contribution guidelines, see **[docs/development/contributing.md](docs/development/contributing.md)**.

## Short version

- Branch from `develop`, not `main`
- Branch naming: `config/`, `task/`, `doc/` prefixes (see contributing guide)
- PRs go to the `develop` branch; assign a team member for review
- Test with Molecule before opening a PR: `molecule test -s rocky9`
- Do not commit secrets -- use vault or placeholders

## Upstream

UCLA-specific changes that are generally useful should be considered for contribution
back to the upstream project at [gdcc/dataverse-ansible](https://github.com/gdcc/dataverse-ansible).
See [docs/development/upstream_contributions.md](docs/development/upstream_contributions.md)
for in-progress upstream PRs.

## UCLA-specific workflow

This repo is managed by the [dataverse-infrastructure](https://github.com/ucla-data-science-center/dataverse-infrastructure)
parent repo. For the standard deployment workflow (Makefile targets, environment setup), start there.

## Questions

Open a GitHub issue or contact the Data Science Center team.
