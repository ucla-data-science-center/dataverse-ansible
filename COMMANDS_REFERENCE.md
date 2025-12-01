# Dataverse Ansible Commands Reference

**Quick reference for the most useful commands when working with UCLA Dataverse Ansible**

---

## Table of Contents

1. [Local Development (Molecule)](#local-development-molecule)
2. [Docker Commands](#docker-commands)
3. [Testing & Verification](#testing--verification)
4. [Ansible Commands](#ansible-commands)
5. [Git Workflow](#git-workflow)
6. [Debugging & Troubleshooting](#debugging--troubleshooting)

---

## Local Development (Molecule)

### Initial Setup

```bash
# Install uv (Python package manager) - only needed once
curl -LsSf https://astral.sh/uv/install.sh | sh

# Bootstrap the project (install dependencies, collections)
make bootstrap

# Alternative: Manual bootstrap steps
uv sync                                    # Install Python dependencies
uv run ansible-galaxy collection install -r collections/requirements.yml -p collections/
```

### Molecule Lifecycle Commands

```bash
# Create and start the container
uv run molecule create -s rocky9

# Run the Ansible playbook (deploy Dataverse)
uv run molecule converge -s rocky9

# Full test cycle (destroy, create, converge, verify)
uv run molecule test -s rocky9

# Destroy the container (clean up)
uv run molecule destroy -s rocky9

# Reset (destroy + create + converge)
uv run molecule reset -s rocky9
```

### Selective Deployment with Tags

```bash
# Run only specific tasks using tags
uv run molecule converge -s rocky9 -- --tags root,branding

# Common useful tags:
# - root: Root dataverse customization
# - branding: UCLA branding (header, footer, logo)
# - gui: GUI customization
# - harvest: Harvesting client setup
# - languages: Language packs
# - sampledata: Sample data creation
```

### Login to Container

```bash
# Open interactive shell in the running container
uv run molecule login -s rocky9

# Once inside, you can run commands like:
systemctl status payara
systemctl status postgresql-16
systemctl status solr
tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log
```

---

## Docker Commands

### Container Management

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Stop the container
docker stop rocky9

# Start a stopped container
docker start rocky9

# Remove the container
docker rm -f rocky9
```

### Execute Commands in Container

```bash
# Run a single command in the container
docker exec rocky9 <command>

# Examples:
docker exec rocky9 systemctl status payara
docker exec rocky9 curl -s http://localhost:8080/api/info/version
docker exec rocky9 cat /usr/local/payara6/glassfish/domains/domain1/logs/server.log

# Open interactive bash shell
docker exec -it rocky9 /bin/bash
```

### Check Service Status

```bash
# Check all services
docker exec rocky9 systemctl status payara postgresql-16 solr httpd

# Check individual services
docker exec rocky9 systemctl status payara
docker exec rocky9 systemctl status postgresql-16
docker exec rocky9 systemctl status solr
docker exec rocky9 systemctl status httpd

# Restart a service
docker exec rocky9 systemctl restart payara
```

### View Logs

```bash
# Payara (Dataverse application server) logs
docker exec rocky9 tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log
docker exec rocky9 tail -n 100 /usr/local/payara6/glassfish/domains/domain1/logs/server.log

# PostgreSQL logs
docker exec rocky9 tail -f /var/lib/pgsql/16/data/log/postgresql-*.log

# Solr logs
docker exec rocky9 tail -f /usr/local/solr/server/logs/solr.log

# Apache logs
docker exec rocky9 tail -f /var/log/httpd/error_log
docker exec rocky9 tail -f /var/log/httpd/access_log
```

---

## Testing & Verification

### API Health Checks

```bash
# Check Dataverse version
curl http://localhost:8080/api/info/version | jq

# Check server status
curl http://localhost:8080/api/info/server | jq

# Get root dataverse info
curl http://localhost:8080/api/dataverses/root | jq

# List harvesting clients
curl http://localhost:8080/api/harvest/clients | jq

# Search datasets
curl "http://localhost:8080/api/search?q=*" | jq
```

### Using jq for JSON Parsing

```bash
# Pretty print JSON
curl -s http://localhost:8080/api/info/version | jq

# Extract specific fields
curl -s http://localhost:8080/api/info/version | jq .data.version

# Filter and search
curl -s http://localhost:8080/api/dataverses/root | jq '.data | {name, affiliation, description}'
```

### Run Testinfra Tests

```bash
# Run all integration tests
uv run pytest molecule/rocky9/tests/ -v

# Run specific test file
uv run pytest molecule/rocky9/tests/test_services.py -v

# Run with more verbose output
uv run pytest molecule/rocky9/tests/ -vv
```

---

## Ansible Commands

### Direct Ansible Playbook Execution

```bash
# Run the main playbook (site.yml)
ansible-playbook -i inventory/production.yml site.yml

# Dry run (check mode - don't make changes)
ansible-playbook -i inventory/production.yml site.yml --check

# Run with specific tags
ansible-playbook -i inventory/production.yml site.yml --tags root,branding

# Skip specific tags
ansible-playbook -i inventory/production.yml site.yml --skip-tags sampledata

# Limit to specific hosts
ansible-playbook -i inventory/production.yml site.yml --limit dataverse-prod

# Use vault password for encrypted variables
ansible-playbook -i inventory/production.yml site.yml --ask-vault-pass

# Use vault password file
ansible-playbook -i inventory/production.yml site.yml --vault-password-file ~/.vault_pass
```

### Ansible Ad-Hoc Commands

```bash
# Ping all hosts
ansible all -i inventory/production.yml -m ping

# Check disk space
ansible all -i inventory/production.yml -a "df -h"

# Check service status
ansible all -i inventory/production.yml -a "systemctl status payara"

# Restart a service
ansible all -i inventory/production.yml -a "systemctl restart payara"

# Run command as root
ansible all -i inventory/production.yml -b -a "systemctl status payara"
```

### Ansible Vault (Encrypt Secrets)

```bash
# Create encrypted file
ansible-vault create group_vars/production/secrets.yml

# Edit encrypted file
ansible-vault edit group_vars/production/secrets.yml

# Encrypt existing file
ansible-vault encrypt group_vars/production/secrets.yml

# Decrypt file (temporarily)
ansible-vault decrypt group_vars/production/secrets.yml

# View encrypted file without editing
ansible-vault view group_vars/production/secrets.yml

# Change vault password
ansible-vault rekey group_vars/production/secrets.yml
```

---

## Git Workflow

### Basic Git Operations

```bash
# Check status
git status

# See what changed
git diff

# See what's staged
git diff --cached

# Stage specific files
git add files/branding/custom-header.html

# Stage all changes
git add .

# Commit with message
git commit -m "feat: Add UCLA branding customization"

# Push to remote
git push origin develop

# Pull latest changes
git pull origin develop
```

### Branching

```bash
# Create new branch
git checkout -b feature/new-branding

# Switch branches
git checkout develop

# List all branches
git branch -a

# Delete local branch
git branch -d feature/old-branch

# Delete remote branch
git push origin --delete feature/old-branch
```

### Syncing with Upstream

```bash
# Add upstream remote (one time)
git remote add upstream https://github.com/IQSS/dataverse-ansible.git

# Fetch upstream changes
git fetch upstream

# See what's different
git log develop..upstream/develop

# Merge upstream changes
git checkout develop
git merge upstream/develop
git push origin develop
```

### Viewing History

```bash
# View commit log
git log

# Compact log (one line per commit)
git log --oneline

# Show last 10 commits
git log -10

# View changes in a specific commit
git show <commit-hash>

# View file history
git log --follow files/branding/custom-header.html
```

---

## Debugging & Troubleshooting

### Check Configuration

```bash
# View merged configuration (defaults + group_vars)
ansible-inventory -i inventory/production.yml --list

# Check specific host variables
ansible-inventory -i inventory/production.yml --host dataverse-prod

# Validate playbook syntax
ansible-playbook site.yml --syntax-check

# List all tasks that would run
ansible-playbook -i inventory/production.yml site.yml --list-tasks

# List all tags
ansible-playbook -i inventory/production.yml site.yml --list-tags
```

### Verbose Output

```bash
# Run with verbose output (shows task execution)
uv run molecule converge -s rocky9 -v

# More verbose (shows task results)
uv run molecule converge -s rocky9 -vv

# Maximum verbosity (shows connection debugging)
uv run molecule converge -s rocky9 -vvv

# Extremely verbose (SSH and other internals)
uv run molecule converge -s rocky9 -vvvv
```

### Common Issues

```bash
# Port 8080 already in use?
lsof -i :8080
kill -9 <PID>

# Container won't start?
docker logs rocky9
docker inspect rocky9

# Molecule cache issues?
rm -rf ~/.cache/molecule/

# Clean up Docker resources
docker system prune -a

# Reset everything
uv run molecule destroy -s rocky9
docker system prune -a
uv run molecule test -s rocky9
```

### Manual API Testing

```bash
# Get API token from container
docker exec rocky9 cat /tmp/api.token

# Or check in Dataverse UI
# Login → Username dropdown → API Token

# Use API token in requests
curl -H "X-Dataverse-key:YOUR_TOKEN" \
  http://localhost:8080/api/dataverses/root

# Create a test dataverse
curl -H "X-Dataverse-key:YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{"name":"Test Collection","alias":"test","dataverseContacts":[{"contactEmail":"test@example.com"}],"affiliation":"Test","description":"Test collection","dataverseType":"RESEARCH_GROUP"}' \
  http://localhost:8080/api/dataverses/root
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it rocky9 sudo -u postgres psql dvndb

# Once in psql:
\dt                          # List tables
\d dataverse                 # Describe dataverse table
SELECT * FROM dataverse;     # Query dataverses
\q                           # Quit
```

### File System Navigation

```bash
# Important directories in the container
docker exec rocky9 ls -la /usr/local/payara6/glassfish/domains/domain1/
docker exec rocky9 ls -la /usr/local/dvn/data/
docker exec rocky9 ls -la /usr/local/solr/
docker exec rocky9 ls -la /var/lib/pgsql/16/data/

# Copy files from container
docker cp rocky9:/usr/local/payara6/glassfish/domains/domain1/logs/server.log ./server.log

# Copy files to container
docker cp custom-header.html rocky9:/usr/local/payara6/glassfish/domains/domain1/applications/dataverse/branding/
```

---

## Quick Troubleshooting Checklist

When something goes wrong, run these commands in order:

```bash
# 1. Check if services are running
docker exec rocky9 systemctl status payara postgresql-16 solr httpd

# 2. Check Dataverse API
curl http://localhost:8080/api/info/version

# 3. Check Payara logs
docker exec rocky9 tail -n 100 /usr/local/payara6/glassfish/domains/domain1/logs/server.log

# 4. Check PostgreSQL
docker exec rocky9 systemctl status postgresql-16

# 5. Check Solr
curl http://localhost:8983/solr/collection1/admin/ping

# 6. If all else fails, restart services
docker exec rocky9 systemctl restart payara
docker exec rocky9 systemctl restart postgresql-16
docker exec rocky9 systemctl restart solr
```

---

## AWS Deployment Commands

### Pre-Deployment Checks

```bash
# Test SSH connection
ssh -i ~/.ssh/dataverse.pem ec2-user@<EC2_IP>

# Ping AWS host
ansible all -i inventory/production.yml -m ping

# Check available disk space
ansible all -i inventory/production.yml -a "df -h"
```

### Deploy to AWS

```bash
# Full deployment
ansible-playbook -i inventory/production.yml site.yml --ask-vault-pass

# Dry run first (recommended)
ansible-playbook -i inventory/production.yml site.yml --check --diff

# Deploy with specific tags
ansible-playbook -i inventory/production.yml site.yml --tags root,branding

# Deploy and save log
ansible-playbook -i inventory/production.yml site.yml --ask-vault-pass | tee deployment.log
```

### Post-Deployment Verification

```bash
# Check services on remote host
ansible all -i inventory/production.yml -a "systemctl status payara postgresql-16 solr httpd"

# Check Dataverse version via API
curl https://dataverse.library.ucla.edu/api/info/version | jq

# Check root dataverse
curl https://dataverse.library.ucla.edu/api/dataverses/root | jq '.data | {name, affiliation}'
```

---

## Performance & Monitoring

```bash
# Check memory usage
docker exec rocky9 free -h

# Check CPU usage
docker exec rocky9 top -bn1 | head -20

# Check Payara heap usage
docker exec rocky9 /usr/local/payara6/bin/asadmin get-jvm-options | grep Xmx

# Monitor Solr performance
curl http://localhost:8983/solr/admin/metrics?prefix=CACHE

# Check PostgreSQL connections
docker exec rocky9 sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## Useful Aliases (Add to ~/.bashrc or ~/.zshrc)

```bash
# Molecule shortcuts
alias mc='uv run molecule converge -s rocky9'
alias md='uv run molecule destroy -s rocky9'
alias mt='uv run molecule test -s rocky9'
alias ml='uv run molecule login -s rocky9'
alias mr='uv run molecule reset -s rocky9'

# Docker shortcuts
alias dps='docker ps'
alias dlogs='docker exec rocky9 tail -f /usr/local/payara6/glassfish/domains/domain1/logs/server.log'
alias dsh='docker exec -it rocky9 /bin/bash'

# Dataverse API shortcuts
alias dvapi='curl http://localhost:8080/api'
alias dvversion='curl -s http://localhost:8080/api/info/version | jq'
alias dvroot='curl -s http://localhost:8080/api/dataverses/root | jq'

# Git shortcuts
alias gs='git status'
alias gd='git diff'
alias gl='git log --oneline -10'
alias gp='git push origin develop'
```

---

## Tips for Learning

1. **Start with Molecule**: Always test locally with molecule before deploying to AWS
2. **Use verbose mode**: Add `-v` or `-vv` to see what Ansible is doing
3. **Check logs immediately**: If something fails, check Payara logs first
4. **Use dry runs**: Always use `--check` before real deployments
5. **Keep backups**: Before major changes, backup the database and config
6. **Read the output**: Ansible tells you what changed in green, yellow, red
7. **Use jq**: Install `jq` for parsing JSON API responses nicely

---

## Documentation References

- **This project**: See README.md, TEAM_GUIDE.md, TROUBLESHOOTING.md
- **Dataverse API**: https://guides.dataverse.org/en/latest/api/
- **Ansible Docs**: https://docs.ansible.com/
- **Molecule Docs**: https://ansible.readthedocs.io/projects/molecule/
- **Docker Docs**: https://docs.docker.com/

---

**Last Updated:** 2025-11-25
**Maintained by:** UCLA Data Science Center

For questions or issues, see [TEAM_GUIDE.md](TEAM_GUIDE.md) or ask in #dataverse Slack channel.
