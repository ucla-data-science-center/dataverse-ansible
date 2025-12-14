# Engineering Session Log: December 2025

This document tracks major engineering sessions, debugging efforts, and architectural decisions for the UCLA Dataverse Ansible fork.

---

## 📅 December 13, 2025: The "Constraint Exists" Race Condition

**Objective:** Deploy Dataverse 6.8 to AWS Staging (EC2).
**Outcome:** **FIXED.** Reverted to stable baseline (`d5cb739`) and fixed SSL bootstrapping.

### 🛑 The Problem
Deployments to EC2 (Dataverse 6.8 + Payara 6.2025.3) consistently failed with:
```
PER01000: Got SQLException executing statement "ALTER TABLE fileaccessrequests ADD CONSTRAINT FK...": 
ERROR: constraint "fk_fileaccessrequests_datafile_id" for relation "fileaccessrequests" already exists
```

### 🕵️ Analysis & Root Cause
*   **Race Condition:** On fast EC2 environments, Payara starts and initializes **JPA (EclipseLink)** before the installer runs its SQL scripts.
*   **Conflict:**
    1.  **JPA** sees the entities and auto-generates the database schema (tables + constraints).
    2.  **Installer** runs `reference_data.sql` (or internal logic) and tries to create the same constraints.
    3.  **Crash:** The database rejects the duplicate constraint.
*   **Why now?** This issue is deterministic on EC2 but rare in Docker/Molecule due to timing differences. It affects both Dataverse 6.7 and 6.8.

### 🧪 Attempted Fixes (Failed)
1.  **JVM Options:** Tried disabling JPA via `-Declipselink.ddl-generation=none`. **Failed:** `persistence.xml` settings override system properties.
2.  **WAR Patching:** Extracted `dataverse.war`, modified `persistence.xml` to `ddl-generation="none"`, and repackaged using `zip` and `jar`.
    *   **Result:** Fixed the constraint error, BUT caused **Flyway** to crash with `Unable to find resource on disk`.
    *   **Reason:** Repackaging the WAR (even with `jar`) seemingly altered the archive structure in a way that broke Flyway's classpath resource scanner.
3.  **Installer Patch:** Modified `install.py` to pass deployment properties. **Failed.**

### ✅ The Solution (Baseline Restore)
We determined that the most reliable path was to revert to the known-good state from **December 1st**, which had successfully deployed before the upstream merge.

1.  **Hard Reset:** `git reset --hard d5cb739`
2.  **Infrastructure Rebuild:** `terraform destroy` -> `apply` (New IP: `52.24.202.10`)
3.  **SSL Bootstrapping Fix:**
    *   Updated `tasks/dataverse-apache.yml` to automatically handle the "Chicken-and-Egg" SSL problem.
    *   Logic: If cert missing -> Generate HTTP config -> Run Certbot -> Re-generate HTTPS config.
4.  **Result:** Successful deployment of Dataverse 6.8 on EC2 with SSL.

---

## 📅 December 1, 2025: Staging Deployment & SSL Refactor

**Commit:** `d5cb739`
**Objective:** Establish a working staging environment on AWS.

*   **SSL Refactor:** Switched from "standalone" Certbot mode to `certbot --apache` plugin.
*   **Two-Stage Deployment:** Documented workflow for deploying HTTP first, then HTTPS (now automated on Dec 13).
*   **Result:** First successful end-to-end deployment on `staging.ucladataverse.dev`.

---

## ⏭️ Next Steps (Recovery Plan)

We rolled back recent features to stabilize the build. We must now re-introduce them granularly:

1.  **Documentation:** (Completed) Reorganized into `docs/` structure.
2.  **Security Hardening:** Re-apply `tasks/dataverse-security-hardening.yml`.
3.  **SMTP/Rate Limiting:** Re-apply `tasks/dataverse-smtp-ratelimiting.yml` (ensuring JVM option idempotency).
4.  **CloudWatch:** Re-apply monitoring.
5.  **Upstream Merge:** Carefully re-merge upstream changes, testing on a fresh instance to catch the race condition if it returns.
