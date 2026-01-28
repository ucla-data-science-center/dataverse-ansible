# Dataverse Migration Knowledge Check

## For: UCLA Dataverse Team
## Purpose: Reinforce understanding of our migration process and tools

---

## Instructions

Answer each question, then check your answers at the bottom. Use this to identify knowledge gaps and spark team discussion.

---

## Section 1: The Big Picture

### Q1. What migration strategy are we using?

- A) In-place upgrade (upgrade the existing server)
- B) Parallel deployment (build new environment, migrate data, switch DNS)
- C) Blue-green deployment with load balancer
- D) Containerized migration with Kubernetes

---

### Q2. Why did we choose this strategy instead of upgrading in place?

Select all that apply:

- [ ] A) We can test thoroughly before going live
- [ ] B) Instant rollback by switching DNS back
- [ ] C) It's faster than an in-place upgrade
- [ ] D) Zero risk to production during testing
- [ ] E) Required by Dataverse licensing

---

### Q3. What is our rollback plan if the migration fails?

- A) Restore from backup to the new server
- B) Point DNS back to the old 5.14 server
- C) Roll back the database using Flyway
- D) There is no rollback plan

---

## Section 2: Infrastructure Tools

### Q4. What does Terraform do in our migration?

- A) Deploys the Dataverse application
- B) Creates AWS infrastructure (EC2, RDS, S3, security groups)
- C) Upgrades the database schema
- D) Manages DNS changes

---

### Q5. What does Ansible do in our migration?

- A) Creates AWS resources
- B) Installs and configures software on the EC2 instance
- C) Handles the database schema migration
- D) Manages SSL certificates

---

### Q6. Match the Terraform command to its purpose:

| Command | Purpose |
|---------|---------|
| `terraform init` | ___ |
| `terraform plan` | ___ |
| `terraform apply` | ___ |
| `terraform output` | ___ |

Options:
1. Shows what resources will be created/changed (dry run)
2. Actually creates/modifies the infrastructure
3. Downloads providers and initializes the working directory
4. Displays values like the RDS endpoint after creation

---

### Q7. Why are we using AWS RDS instead of PostgreSQL on the EC2 instance?

Select all that apply:

- [ ] A) Automated backups and point-in-time recovery
- [ ] B) It's required by Dataverse 6.8
- [ ] C) Easier scaling independent of the application server
- [ ] D) Built-in high availability options
- [ ] E) Reduces operational burden (AWS manages the database)

---

### Q8. What PostgreSQL extensions does Dataverse require?

- A) `pg_trgm` only
- B) `pg_trgm` and `unaccent`
- C) `postgis` and `pg_trgm`
- D) No extensions required

---

## Section 3: The Migration Process

### Q9. What is Flyway?

- A) A tool for migrating files to S3
- B) A database schema migration tool built into Dataverse
- C) An AWS service for data transfer
- D) A Terraform provider

---

### Q10. What happens when we start Dataverse 6.8 with a 5.14 database?

- A) It crashes with a version mismatch error
- B) Flyway automatically runs migration scripts to upgrade the schema
- C) We need to manually run SQL upgrade scripts
- D) The database is wiped and recreated

---

### Q11. Put these migration steps in the correct order:

___ Import 5.14 database dump into RDS
___ Run Terraform to create infrastructure
___ Run Solr re-index
___ Run Ansible to deploy Dataverse 6.8
___ Stop Payara immediately after Ansible completes
___ Start Payara (Flyway runs automatically)
___ Switch DNS to new server

---

### Q12. Why do we stop Payara immediately after Ansible deploys Dataverse?

- A) To save AWS costs
- B) To prevent it from initializing an empty database before we import the 5.14 data
- C) Payara needs to be restarted after installation
- D) To allow Solr to start first

---

### Q13. Why must we re-index Solr after the migration?

- A) Solr data is stored in PostgreSQL and needs to sync
- B) The Solr schema changed between versions, and we have a fresh empty index
- C) Re-indexing improves search performance
- D) Flyway requires it

---

## Section 4: Safety & Security

### Q14. What does "disarming" the test database mean?

Select all that apply:

- [ ] A) Changing the siteUrl to point to the test domain
- [ ] B) Disabling real DOI minting
- [ ] C) Deleting sensitive user data
- [ ] D) Disabling email notifications to real users
- [ ] E) Removing admin access

---

### Q15. How is the RDS database protected from unauthorized access?

- A) It's in a private subnet with no internet access
- B) Security group only allows port 5432 from the EC2 instance
- C) It requires VPN access
- D) Both A and B

---

### Q16. Where should sensitive values like `db_password` be stored?

- A) Directly in the Terraform `.tf` files
- B) In `terraform.tfvars` (which is gitignored) or as environment variables
- C) In the README for easy reference
- D) In AWS Secrets Manager only

---

## Section 5: Version Changes

### Q17. Match the component to its version change:

| Component | Old → New |
|-----------|-----------|
| Operating System | ___ |
| Java | ___ |
| Payara | ___ |
| PostgreSQL | ___ |
| Solr | ___ |

Options:
1. 11 → 17
2. 5 → 6
3. CentOS 7 → Rocky Linux 9
4. 9.x/10.x → 16
5. 8 → 9

---

### Q18. Why are we moving from CentOS 7 to Rocky Linux 9?

- A) Rocky Linux is faster
- B) CentOS 7 reached end-of-life (EOL) in June 2024
- C) Dataverse 6.8 requires Rocky Linux
- D) AWS doesn't support CentOS anymore

---

## Section 6: Troubleshooting Scenarios

### Q19. Terraform fails with "Cannot find version 16.3 for postgres". What do you do?

- A) Switch to MySQL
- B) Check available PostgreSQL versions in your AWS region and update the variable
- C) Contact AWS support
- D) Use a different AWS region

---

### Q20. After starting Payara, you see no errors but search returns zero results. What's likely wrong?

- A) The database migration failed
- B) Solr hasn't been re-indexed yet
- C) Apache isn't running
- D) The S3 bucket is misconfigured

---

### Q21. You can't connect to RDS from the EC2 instance. What should you check first?

- A) The database password
- B) The security group rules (is port 5432 allowed from EC2?)
- C) The Solr configuration
- D) The Apache virtual host

---

## Section 7: Quick Reference

### Q22. What command triggers a full Solr re-index?

```
curl http://localhost:8080/api/admin/____________
```

---

### Q23. What command checks the Solr re-index status?

```
curl http://localhost:8080/api/admin/____________
```

---

### Q24. After `terraform apply` completes, what command shows the RDS endpoint?

```
terraform ____________
```

---

---

# Answer Key

## Section 1: The Big Picture

**Q1:** B) Parallel deployment

**Q2:** A, B, D (C is false - parallel deployment takes more time upfront but is safer; E is false)

**Q3:** B) Point DNS back to the old 5.14 server

## Section 2: Infrastructure Tools

**Q4:** B) Creates AWS infrastructure

**Q5:** B) Installs and configures software on the EC2 instance

**Q6:**
- `terraform init` → 3 (Downloads providers and initializes)
- `terraform plan` → 1 (Shows what will be created - dry run)
- `terraform apply` → 2 (Actually creates infrastructure)
- `terraform output` → 4 (Displays values like RDS endpoint)

**Q7:** A, C, D, E (B is false - RDS is our choice, not a requirement)

**Q8:** B) `pg_trgm` and `unaccent`

## Section 3: The Migration Process

**Q9:** B) A database schema migration tool built into Dataverse

**Q10:** B) Flyway automatically runs migration scripts

**Q11:** Correct order:
1. Run Terraform to create infrastructure
2. Run Ansible to deploy Dataverse 6.8
3. Stop Payara immediately after Ansible completes
4. Import 5.14 database dump into RDS
5. Start Payara (Flyway runs automatically)
6. Run Solr re-index
7. Switch DNS to new server

**Q12:** B) To prevent it from initializing an empty database

**Q13:** B) The Solr schema changed between versions, and we have a fresh empty index

## Section 4: Safety & Security

**Q14:** A, B, D (C and E are not part of disarming)

**Q15:** D) Both A and B

**Q16:** B) In `terraform.tfvars` (gitignored) or environment variables

## Section 5: Version Changes

**Q17:**
- Operating System → 3 (CentOS 7 → Rocky Linux 9)
- Java → 1 (11 → 17)
- Payara → 2 (5 → 6)
- PostgreSQL → 4 (9.x/10.x → 16)
- Solr → 5 (8 → 9)

**Q18:** B) CentOS 7 reached end-of-life (EOL) in June 2024

## Section 6: Troubleshooting Scenarios

**Q19:** B) Check available PostgreSQL versions and update the variable

**Q20:** B) Solr hasn't been re-indexed yet

**Q21:** B) The security group rules

## Section 7: Quick Reference

**Q22:** `curl http://localhost:8080/api/admin/index`

**Q23:** `curl http://localhost:8080/api/admin/index/status`

**Q24:** `terraform output rds_endpoint`

---

## Scoring

| Score | Level |
|-------|-------|
| 22-24 | Expert - You could run this migration solo |
| 18-21 | Proficient - Solid understanding, ready to contribute |
| 14-17 | Developing - Review the overview document |
| < 14 | Learning - Pair with someone experienced |

---

## Discussion Questions for Team Meeting

1. What's the riskiest part of this migration? How do we mitigate it?
2. If Flyway migration fails halfway through, what's our recovery path?
3. How long should we keep the old 5.14 server running after cutover?
4. What tests should we run before declaring the migration successful?
5. Who needs to be notified before/during/after the maintenance window?
