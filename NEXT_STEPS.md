# Next Steps for Dataverse Ansible Development

**Last Updated**: 2025-11-24

## Current Status

### ✅ Completed (November 2025)

#### 1. **Local Development & Testing Infrastructure**
- [x] Molecule rocky9 scenario fully working
- [x] Dataverse 6.8 deploys successfully
- [x] All services running (Payara 6, PostgreSQL 16, Solr 9.8, Apache)
- [x] Accessible at http://localhost:8080
- [x] 16 testinfra tests passing
- [x] Idempotency improvements (Solr, Payara, Shibboleth, JVM options)

#### 2. **UCLA Branding & Customization** ✨
- [x] Complete UCLA Library themed UI (header, footer, homepage)
- [x] UCLA Dataverse logo (UCLA letterforms + "Dataverse" wordmark)
- [x] UCLA-themed favicons (2-ring icon in UCLA blue)
- [x] CSS icon color overrides (collections, datasets, files)
- [x] Support portal integration (NavbarSupportUrl → UCLA Jira)
- [x] Custom footer with social media links and service portals

#### 3. **Metadata & Language Support**
- [x] 7 metadata blocks configured:
  - CodeMeta (software/code)
  - HELADA (UCLA heritage language custom)
  - Geospatial
  - Social Science & Humanities
  - Astrophysics
  - Biomedical/Life Sciences
  - Journals
- [x] 5 language packs: English, Spanish, Chinese, Japanese, Korean

#### 4. **Sample Data Improvements**
- [x] API-based sample data (replaces fragile Python script)
- [x] Creates UCLA Data Science Center collection
- [x] Generates test datasets via REST API

#### 5. **Documentation** 📚
- [x] AWS deployment guide (AWS_DEPLOYMENT.md)
- [x] AWS deployment checklist (AWS_DEPLOYMENT_CHECKLIST.md)
- [x] 5.14 → 6.8 migration guide (MIGRATION_5.14_TO_6.8.md)
- [x] Team guide (TEAM_GUIDE.md)
- [x] Troubleshooting guide (TROUBLESHOOTING.md)
- [x] Molecule quick reference (MOLECULE_QUICK_REF.md)
- [x] Fork improvements log (FORK_IMPROVEMENTS.md)

---

## 🎯 Immediate Next Steps (Pre-Deployment)

### Phase 1: Information Gathering (This Week)

Before starting AWS deployment, collect this information:

- [ ] **Production 5.14 Instance Details**
  - [ ] Current Dataverse version
  - [ ] Database size and row counts
  - [ ] File storage size
  - [ ] Number of collections/datasets/files
  - [ ] Current DOI authority and provider
  - [ ] Current resource usage (CPU, memory, disk)

- [ ] **AWS Resources**
  - [ ] EC2 instance type decision (match or exceed current)
  - [ ] Storage requirements (2x current for safety)
  - [ ] Elastic IP allocated
  - [ ] Security groups configured

- [ ] **Credentials**
  - [ ] UCLA DOI credentials (production + test)
  - [ ] SMTP relay information
  - [ ] SSH key pair for EC2

- [ ] **DNS Strategy**
  - [ ] test.dataverse.ucla.edu access (for Phase 2)
  - [ ] OR budget for cheap test domain (~$12)

**Action:** Review [MIGRATION_5.14_TO_6.8.md](MIGRATION_5.14_TO_6.8.md) Pre-Migration Planning section

### Phase 2: Deploy Test Instance (Week 1)

- [ ] Launch EC2 instance (Rocky Linux 9)
- [ ] Deploy fresh 6.8 via Ansible
- [ ] Test on Elastic IP (http://54.x.x.x)
- [ ] Validate UCLA branding
- [ ] Document any issues

**Action:** Follow [MIGRATION_5.14_TO_6.8.md](MIGRATION_5.14_TO_6.8.md) Phase 1

### Phase 3: Integration Testing (Week 2-3)

- [ ] Configure SSL with domain
- [ ] Clone production database
- [ ] Test 5.14 → 6.8 schema upgrade
- [ ] Sync production files
- [ ] DOI testing with test authority
- [ ] Load testing
- [ ] Backup/restore validation

**Action:** Follow [MIGRATION_5.14_TO_6.8.md](MIGRATION_5.14_TO_6.8.md) Phase 2

### Phase 4: Production Cutover (Week 4)

- [ ] Schedule maintenance window
- [ ] Final production backup
- [ ] DNS cutover to new instance
- [ ] Validate and monitor

**Action:** Follow [MIGRATION_5.14_TO_6.8.md](MIGRATION_5.14_TO_6.8.md) Phase 3

---

## 🚀 Future Enhancements (Post-Migration)

### High Priority

#### 1. **Shibboleth/SSO Integration**
**Status:** Not yet configured
**Effort:** Medium (2-3 days)
**Benefit:** UCLA authentication, improved security

Tasks:
- [ ] Obtain UCLA Shibboleth metadata
- [ ] Configure Shibboleth SP on Dataverse instance
- [ ] Test authentication flow
- [ ] Disable built-in user registration

**Resources:**
- Dataverse Shibboleth guide: https://guides.dataverse.org/en/6.8/installation/shibboleth.html
- UCLA Shibboleth docs: (check with UCLA IT)

#### 2. **Production DOI Configuration**
**Status:** Currently using FAKE provider
**Effort:** Low (1 hour + credential acquisition)
**Benefit:** Real DOI minting for production

Tasks:
- [ ] Obtain UCLA production DOI credentials
- [ ] Update `dataverse.doi` configuration
- [ ] Test DOI minting on production
- [ ] Verify DOI resolution

#### 3. **SMTP/Email Configuration**
**Status:** Using localhost
**Effort:** Low (1-2 hours)
**Benefit:** Real email notifications

Tasks:
- [ ] Get UCLA SMTP relay information
- [ ] Configure `dataverse.smtp` setting
- [ ] Test email delivery
- [ ] Configure email templates if needed

### Medium Priority

#### 4. **S3 Storage Migration**
**Status:** Using local file storage
**Effort:** Medium (3-5 days)
**Benefit:** Scalability, backups, durability

Tasks:
- [ ] Create S3 bucket
- [ ] Configure bucket policies and CORS
- [ ] Update Ansible configuration
- [ ] Test direct upload/download
- [ ] Migrate existing files (if desired)

**Resources:**
- Dataverse S3 guide: https://guides.dataverse.org/en/6.8/installation/config.html#s3-storage

#### 5. **Make Data Count Integration**
**Status:** Configured but no API token
**Effort:** Low (1 hour)
**Benefit:** Usage metrics for datasets

Tasks:
- [ ] Obtain DataCite Hub API token
- [ ] Update `dataverse.counter.hub_api_token`
- [ ] Enable `upload_to_hub: true`
- [ ] Verify metrics collection

#### 6. **PostgreSQL RDS Migration**
**Status:** Using EC2-hosted PostgreSQL
**Effort:** Medium (2-3 days)
**Benefit:** Managed backups, HA, scaling

Tasks:
- [ ] Provision RDS PostgreSQL 16 instance
- [ ] Configure security groups
- [ ] Migrate database
- [ ] Update Ansible configuration
- [ ] Test connectivity

### Low Priority

#### 7. **Monitoring & Alerting**
**Status:** Basic systemd monitoring only
**Effort:** Medium (3-5 days)
**Benefit:** Proactive issue detection

Options:
- AWS CloudWatch (easiest for AWS deployment)
- Prometheus + Grafana
- Datadog
- New Relic

Tasks:
- [ ] Set up monitoring service
- [ ] Configure metrics collection
- [ ] Create dashboards
- [ ] Set up alerts (downtime, high CPU, disk space)

#### 8. **Load Balancing / High Availability**
**Status:** Single EC2 instance
**Effort:** High (1-2 weeks)
**Benefit:** Zero downtime deployments, scaling

Tasks:
- [ ] Design HA architecture
- [ ] Set up Application Load Balancer
- [ ] Configure Auto Scaling Group
- [ ] Test failover scenarios
- [ ] Implement session persistence

#### 9. **Additional External Tools**
**Status:** Data Explorer enabled
**Effort:** Low per tool
**Benefit:** Enhanced user workflows

Available tools:
- [ ] Whole Tale integration
- [ ] Data Curation Tool
- [ ] TwoRavens (statistical analysis)
- [ ] Jupyverse (Jupyter notebooks)

**Resources:**
- External Tools guide: https://guides.dataverse.org/en/6.8/installation/external-tools.html

#### 10. **Custom Metadata Blocks**
**Status:** 7 blocks configured (including HELADA)
**Effort:** Low per block
**Benefit:** Domain-specific metadata

Tasks:
- [ ] Identify additional metadata needs
- [ ] Create TSV definitions
- [ ] Add to custom metadata repository
- [ ] Configure in Ansible

---

## 🔄 Ongoing Maintenance

### Weekly
- [ ] Check application logs for errors
- [ ] Monitor disk space usage
- [ ] Review security alerts

### Monthly
- [ ] OS security updates (`dnf update`)
- [ ] Review and rotate logs
- [ ] Test backup restoration
- [ ] Review user feedback

### Quarterly
- [ ] Dataverse version updates (6.8 → 6.9, etc.)
- [ ] Review and update documentation
- [ ] Security audit
- [ ] Performance review

### Annually
- [ ] Major version upgrades (if applicable)
- [ ] SSL certificate renewal (automatic with Let's Encrypt)
- [ ] Disaster recovery drill
- [ ] Infrastructure cost review

---

## 📝 Technical Debt & Known Issues

### Issues to Address

1. **Dataverse Installer Idempotency**
   - **Status:** Partial fix (checks if Dataverse responding)
   - **Issue:** Can't safely re-run installer on same database
   - **Impact:** Must destroy/recreate for full testing
   - **Solution:** More robust state checking in installer task

2. **Sample Data Python Script**
   - **Status:** Deprecated in favor of API approach
   - **Issue:** Legacy script times out and has Python dependency issues
   - **Impact:** None (replaced with API-based task)
   - **Action:** Consider removing old task file

3. **Vendored Ansible Collections**
   - **Status:** Working but manually versioned
   - **Issue:** No automated updates
   - **Impact:** Must manually track collection updates
   - **Solution:** Consider dependabot or similar for collection updates

### Upstream Contributions Planned

See [UPSTREAM_PR_DRAFT.md](UPSTREAM_PR_DRAFT.md) for detailed PR drafts:

- [ ] Solr installation idempotency fix
- [ ] Payara installation idempotency fix
- [ ] JVM options idempotency fixes
- [ ] Shibboleth auth provider idempotency
- [ ] Log4j CVE mitigation improvements
- [ ] Molecule/Docker testing improvements

---

## 📚 Resources

### Documentation
- [Dataverse Installation Guide](https://guides.dataverse.org/en/6.8/installation/)
- [Dataverse Admin Guide](https://guides.dataverse.org/en/6.8/admin/)
- [Dataverse API Guide](https://guides.dataverse.org/en/6.8/api/)
- [Dataverse User Guide](https://guides.dataverse.org/en/6.8/user/)

### Community
- [Dataverse Community Forum](https://groups.google.com/g/dataverse-community)
- [Dataverse Slack](https://dataversecommunity.slack.com)
- [GitHub Issues](https://github.com/IQSS/dataverse/issues)

### UCLA Internal
- Team Slack: #dataverse channel
- GitHub: https://github.com/ucla-data-science-center/dataverse-ansible
- Production instance: https://dataverse.ucla.edu

---

## 🎓 Learning Resources

For new team members or contributors:

1. **Ansible Basics**
   - https://docs.ansible.com/ansible/latest/user_guide/
   - Focus on: roles, tasks, handlers, templates, variables

2. **Dataverse Architecture**
   - https://guides.dataverse.org/en/6.8/installation/architecture.html
   - Components: Payara, PostgreSQL, Solr, Apache

3. **Molecule Testing**
   - https://ansible.readthedocs.io/projects/molecule/
   - Our quick ref: [MOLECULE_QUICK_REF.md](MOLECULE_QUICK_REF.md)

4. **AWS EC2 & Deployment**
   - https://docs.aws.amazon.com/ec2/
   - Our guide: [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)

---

**Questions?** Check [TEAM_GUIDE.md](TEAM_GUIDE.md) or ask in #dataverse Slack channel!
