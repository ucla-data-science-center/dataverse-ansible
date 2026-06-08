# Team Guide

Internal practices for the UCLA DSC team working on the `dataverse-ansible` fork. For setup, architecture, and command reference, start with `context.md`.

## Branching and PRs

**Default branch:** `develop` (not `main`)

Branch naming:
- `config/*` — group_vars or defaults changes
- `task/*` — role task or template updates
- `doc/*` — documentation only

All PRs target `develop`. Use `gh pr create --base develop --fill` or open through GitHub.

**Critical:** The Dataverse installer is not idempotent. Never re-run the playbook against an existing instance. Destroy and rebuild with `make rebuild ENV=tim DB_PASS=<pass>`.

## Before making changes

1. Create a feature branch off `develop`
2. If it's an Ansible change, test locally with Molecule before pushing
3. Document the change in the commit message — what changed and why
4. If it's a significant fork improvement, add an entry to `development/changelog.md`

## Before deploying to an environment

1. Test in Molecule locally
2. Run `make test-smoke ENV=tim` against a rebuilt staging instance
3. Get a second set of eyes on any group_vars changes — secrets management mistakes are hard to undo

## Syncing with upstream

```bash
# Add upstream once
git remote add upstream https://github.com/IQSS/dataverse-ansible.git

# Check what's changed
git fetch upstream
git log develop..upstream/develop

# Merge
git checkout develop
git merge upstream/develop
git push origin develop
```

Test after every upstream merge. Their changes may conflict with our idempotency fixes.

## Contributing back upstream

We've fixed several idempotency issues (Solr, Payara, JVM options) that upstream doesn't have. Draft PR descriptions are in `development/upstream_contributions.md`. The general approach: test thoroughly in our environment first, bundle related fixes, submit with evidence.
