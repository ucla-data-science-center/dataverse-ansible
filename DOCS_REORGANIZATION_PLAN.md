# Documentation Reorganization Plan

**Status:** DRAFT - For team review
**Created:** 2025-11-24
**Purpose:** Optional plan to organize documentation into subdirectories

---

## Current State

All 14 markdown files are in the root directory:

```
dataverse-ansible/
├── AWS_DEPLOYMENT_CHECKLIST.md (8K)
├── AWS_DEPLOYMENT.md (16K)
├── CLAUDE.md (8K)
├── CONFIG_STRATEGY.md (12K)
├── FORK_IMPROVEMENTS.md (20K)
├── MIGRATION_5.14_TO_6.8.md (40K)
├── MOLECULE_QUICK_REF.md (8K)
├── NEXT_STEPS.md (12K)
├── README.md (12K)
├── TEAM_GUIDE.md (12K)
├── TROUBLESHOOTING.md (12K)
├── UCLA-CONTRIBUTING.md (4K)
├── ucla_readme.md (8K)
└── UPSTREAM_PR_DRAFT.md (12K)
```

**Total:** 184KB across 14 files

---

## Proposed Structure

Move files into logical subdirectories:

```
dataverse-ansible/
├── README.md                          # Keep (Ansible Galaxy expects it)
├── ucla_readme.md                     # Keep (main entry point)
│
├── docs/
│   ├── deployment/
│   │   ├── AWS_DEPLOYMENT.md          # AWS deployment guide
│   │   ├── AWS_DEPLOYMENT_CHECKLIST.md # Quick checklist
│   │   └── MIGRATION_5.14_TO_6.8.md   # Migration playbook
│   │
│   ├── development/
│   │   ├── MOLECULE_QUICK_REF.md      # Local testing
│   │   ├── CONFIG_STRATEGY.md         # Configuration approach
│   │   └── TROUBLESHOOTING.md         # Common issues
│   │
│   ├── team/
│   │   ├── TEAM_GUIDE.md              # Team handbook
│   │   ├── UCLA-CONTRIBUTING.md       # Contribution guide
│   │   └── NEXT_STEPS.md              # Roadmap
│   │
│   └── meta/
│       ├── FORK_IMPROVEMENTS.md       # Change log
│       ├── UPSTREAM_PR_DRAFT.md       # Upstream contributions
│       └── CLAUDE.md                  # AI assistant context
│
├── tasks/
├── defaults/
├── templates/
└── ... (rest of Ansible role structure)
```

---

## Benefits

### Pros ✅

1. **Cleaner root directory**
   - Only 2 README files in root
   - Easier to navigate at a glance
   - Professional appearance

2. **Logical grouping**
   - Deployment docs together
   - Development docs together
   - Team/process docs together
   - Meta/maintenance docs together

3. **Scalability**
   - Easy to add more docs without cluttering root
   - Clear place for new documentation
   - Better for large teams

4. **Discoverability**
   - Directory names indicate content
   - Related docs co-located
   - Easier for new team members

### Cons ⚠️

1. **Breaking changes**
   - All existing links need updating
   - Team members need to learn new structure
   - Git history shows files "moved"

2. **Initial effort**
   - ~2 hours to reorganize
   - Update all internal links
   - Test all links work
   - Update team about changes

3. **Not urgent**
   - Current structure works fine
   - No functional benefit
   - Purely organizational

---

## Implementation Plan

### Phase 1: Prepare (30 min)

1. **Create directory structure:**
```bash
mkdir -p docs/{deployment,development,team,meta}
```

2. **Create README files for each directory:**

**docs/deployment/README.md:**
```markdown
# Deployment Documentation

Guides for deploying Dataverse to AWS and managing production infrastructure.

- [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) - Complete AWS deployment guide
- [AWS_DEPLOYMENT_CHECKLIST.md](AWS_DEPLOYMENT_CHECKLIST.md) - Quick reference checklist
- [MIGRATION_5.14_TO_6.8.md](MIGRATION_5.14_TO_6.8.md) - Production upgrade playbook
```

**docs/development/README.md:**
```markdown
# Development Documentation

Guides for local development and testing.

- [MOLECULE_QUICK_REF.md](MOLECULE_QUICK_REF.md) - Quick reference for Molecule commands
- [CONFIG_STRATEGY.md](CONFIG_STRATEGY.md) - Configuration strategy: local vs AWS
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
```

**docs/team/README.md:**
```markdown
# Team Documentation

Internal team processes and contribution guidelines.

- [TEAM_GUIDE.md](TEAM_GUIDE.md) - Complete team handbook
- [UCLA-CONTRIBUTING.md](UCLA-CONTRIBUTING.md) - How to contribute
- [NEXT_STEPS.md](NEXT_STEPS.md) - Roadmap and future work
```

**docs/meta/README.md:**
```markdown
# Meta Documentation

Maintainer docs, change logs, and tooling configurations.

- [FORK_IMPROVEMENTS.md](FORK_IMPROVEMENTS.md) - Log of improvements to the fork
- [UPSTREAM_PR_DRAFT.md](UPSTREAM_PR_DRAFT.md) - Ready-to-submit upstream PRs
- [CLAUDE.md](CLAUDE.md) - AI assistant context and instructions
```

### Phase 2: Move Files (15 min)

```bash
# Deployment docs
git mv AWS_DEPLOYMENT.md docs/deployment/
git mv AWS_DEPLOYMENT_CHECKLIST.md docs/deployment/
git mv MIGRATION_5.14_TO_6.8.md docs/deployment/

# Development docs
git mv MOLECULE_QUICK_REF.md docs/development/
git mv CONFIG_STRATEGY.md docs/development/
git mv TROUBLESHOOTING.md docs/development/

# Team docs
git mv TEAM_GUIDE.md docs/team/
git mv UCLA-CONTRIBUTING.md docs/team/
git mv NEXT_STEPS.md docs/team/

# Meta docs
git mv FORK_IMPROVEMENTS.md docs/meta/
git mv UPSTREAM_PR_DRAFT.md docs/meta/
git mv CLAUDE.md docs/meta/
```

### Phase 3: Update Links (1 hour)

Search and replace in all markdown files:

**Before:**
```markdown
[AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)
[TEAM_GUIDE.md](TEAM_GUIDE.md)
...
```

**After:**
```markdown
[AWS_DEPLOYMENT.md](docs/deployment/AWS_DEPLOYMENT.md)
[TEAM_GUIDE.md](docs/team/TEAM_GUIDE.md)
...
```

**Command to find all links:**
```bash
grep -r "\.md" *.md docs/**/*.md | grep -E "\]\(.*\.md\)" | sort -u
```

### Phase 4: Update Main READMEs (15 min)

Update `ucla_readme.md` with new paths:

```markdown
| Document | Purpose | Audience |
|----------|---------|----------|
| **[TEAM_GUIDE.md](docs/team/TEAM_GUIDE.md)** | Complete team handbook | All team members |
| **[AWS_DEPLOYMENT.md](docs/deployment/AWS_DEPLOYMENT.md)** | AWS deployment guide | DevOps |
...
```

### Phase 5: Test & Validate (15 min)

1. Click every link in documentation
2. Verify all links work
3. Test on GitHub (preview markdown rendering)
4. Fix any broken links

### Phase 6: Commit & Communicate (15 min)

```bash
git add docs/ *.md
git commit -m "docs: Reorganize documentation into subdirectories

Moved documentation into logical subdirectories:
- docs/deployment/ - AWS deployment and migration guides
- docs/development/ - Local testing and troubleshooting
- docs/team/ - Team processes and contribution guides
- docs/meta/ - Maintainer docs and change logs

Updated all internal links to reflect new structure.
README.md and ucla_readme.md remain in root as entry points.
"

git push origin develop
```

**Announce to team:**
> 📚 **Documentation Reorganized**
>
> We've moved docs into subdirectories for better organization:
> - `docs/deployment/` - AWS guides
> - `docs/development/` - Local testing
> - `docs/team/` - Team processes
> - `docs/meta/` - Maintainer docs
>
> Start point still `ucla_readme.md` in root!

---

## Alternative: Keep Current Structure

### Why Current Structure is Fine

1. **Works well** - Team knows where things are
2. **No breaking changes** - All links continue to work
3. **Quick access** - All docs one `ls` away
4. **Not many files** - 14 files isn't overwhelming

### When to Reorganize

Consider reorganizing when:
- File count exceeds ~20 files
- Team feedback indicates navigation issues
- Multiple people struggling to find docs
- Adding many new specialized docs

---

## Decision Matrix

| Factor | Keep Current | Reorganize |
|--------|-------------|------------|
| **Effort** | 0 hours | 2 hours |
| **Team disruption** | None | Low (just new paths) |
| **Benefits** | None | Cleaner structure |
| **Risks** | None | Broken links if done wrong |
| **Urgency** | N/A | Not urgent |

---

## Recommendation

**Keep current structure** for now because:

✅ Current structure works well
✅ Only 14 files (manageable)
✅ No complaints from team
✅ Better to focus on deployment

**Consider reorganizing if/when:**
- File count grows to 20+
- Team requests better organization
- Adding major new documentation sections
- Onboarding new team members struggles with navigation

---

## Implementation Timeline (If Proceeding)

| Week | Task |
|------|------|
| **Week 1** | Team review and feedback on plan |
| **Week 2** | Create directory structure and README files |
| **Week 3** | Move files and update links |
| **Week 4** | Test, commit, communicate |

**Estimated effort:** 2 hours active work + 1 week review period

---

## Feedback Questions

For team discussion:

1. Do you find the current root directory cluttered?
2. Have you struggled to find documentation?
3. Would subdirectories help or hinder your workflow?
4. Is this worth 2 hours of work right now?
5. Any alternative organizations you'd prefer?

---

**Decision:** To be determined by team
**Next Steps:** Get team feedback, then proceed or close

**Document Owner:** UCLA Data Science Center
**Last Updated:** 2025-11-24
