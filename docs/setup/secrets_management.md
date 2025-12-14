# Ansible Vault Guide

This guide explains how to use Ansible Vault to encrypt sensitive credentials in this project.

## Overview

Ansible Vault encrypts sensitive data (passwords, API keys, etc.) so they can be safely committed to version control. The encrypted files can only be decrypted with the vault password.

**File structure:**
- `group_vars/staging.yml` - Public configuration (not encrypted)
- `group_vars/staging_vault.yml` - Encrypted secrets (encrypted with ansible-vault)
- `group_vars/staging_vault.yml.TEMPLATE` - Template for creating vault files
- `~/.ansible_vault_pass` - Your local vault password file (NOT committed to git)

## Initial Setup (One-Time)

### Step 1: Create Vault Password File

```bash
# Generate a strong random password
openssl rand -base64 32

# Save it to the vault password file
echo "your-generated-password-here" > ~/.ansible_vault_pass
chmod 600 ~/.ansible_vault_pass
```

**Important:**
- Keep this password secure!
- Share it securely with team members (1Password, LastPass, etc.)
- Never commit `~/.ansible_vault_pass` to git (it's in .gitignore)

### Step 2: Verify ansible.cfg Configuration

The project's `ansible.cfg` already contains:
```ini
vault_password_file = ~/.ansible_vault_pass
```

This tells Ansible where to find your vault password.

## Creating an Encrypted Vault File

### Method 1: From Template (Recommended)

```bash
# 1. Copy the template to a temporary location
cp group_vars/staging_vault.yml.TEMPLATE /tmp/staging_vault.yml

# 2. Edit the file and replace CHANGE_ME values
nano /tmp/staging_vault.yml

# 3. Encrypt and save to the correct location
ansible-vault encrypt /tmp/staging_vault.yml --output group_vars/staging_vault.yml

# 4. Clean up
rm /tmp/staging_vault.yml
```

### Method 2: Create Directly

```bash
# This opens your editor to create an encrypted file
ansible-vault create group_vars/staging_vault.yml
```

## Working with Vault Files

### Edit an Encrypted File

```bash
# Opens in your default editor (decrypts automatically)
ansible-vault edit group_vars/staging_vault.yml
```

### View an Encrypted File

```bash
# View without editing
ansible-vault view group_vars/staging_vault.yml
```

### Verify File is Encrypted

```bash
# Encrypted files start with: $ANSIBLE_VAULT;1.1;AES256
head -n 1 group_vars/staging_vault.yml
```

## Running Playbooks with Vault

### Automatic (Recommended)

If `~/.ansible_vault_pass` exists and `ansible.cfg` is configured, vaults decrypt automatically:

```bash
ansible-playbook -i inventory/staging.yml site.yml
```

### Manual Password Entry

If you don't have `~/.ansible_vault_pass`, you'll be prompted:

```bash
ansible-playbook -i inventory/staging.yml site.yml --ask-vault-pass
```

### Using a Different Password File

```bash
ansible-playbook -i inventory/staging.yml site.yml --vault-password-file /path/to/password
```

## What to Encrypt

### ✅ Always Encrypt:
- `vault_dataverse_adminpass` - Dataverse admin password
- `vault_dataverse_postgresql_password` - Database user password
- `vault_dataverse_postgresql_admin_password` - Database admin password
- `vault_dataverse_doi_username` - DOI service username
- `vault_dataverse_doi_password` - DOI service password
- `vault_dataverse_smtp_password` - SMTP password (if required)
- `vault_aws_access_key_id` - AWS credentials (if using S3)
- `vault_aws_secret_access_key` - AWS credentials (if using S3)

### ✅ Safe to Keep Plaintext:
- Domain names
- Email addresses
- Service ports
- File paths
- Boolean flags
- Public URLs

## Example Vault File Contents

```yaml
---
# group_vars/staging_vault.yml (encrypted)

vault_dataverse_adminpass: "MyStr0ng!Passw0rd#2024"
vault_dataverse_postgresql_password: "Db$ecure!Pass2024"
vault_dataverse_postgresql_admin_password: "P0stgres@dminP@ss"
vault_dataverse_doi_username: "UCLA.LIBRARY"
vault_dataverse_doi_password: "datacite-secret-key-here"
vault_dataverse_payara_adminpass: "P@yara@dmin2024!"
```

## Referencing Vault Variables

In your plaintext config files (like `staging.yml`), reference vault variables:

```yaml
# group_vars/staging.yml (plaintext)
dataverse_adminpass: "{{ vault_dataverse_adminpass }}"
dataverse_postgresql_password: "{{ vault_dataverse_postgresql_password }}"
```

## Troubleshooting

### ERROR! Attempting to decrypt but no vault secrets found

**Cause:** The vault file isn't encrypted or doesn't exist.

**Solution:**
```bash
# Check if file exists and is encrypted
ls -la group_vars/staging_vault.yml
head -n 1 group_vars/staging_vault.yml
```

### ERROR! Decryption failed

**Cause:** Wrong vault password or corrupted vault file.

**Solution:**
```bash
# Verify your password file
cat ~/.ansible_vault_pass

# Try to view the vault manually
ansible-vault view group_vars/staging_vault.yml
```

### Variables Not Found

**Cause:** Ansible isn't loading the vault file.

**Solution:**
- Ensure filename matches group name: `group_vars/staging_vault.yml` for `staging` group
- Check inventory file structure
- Verify vault file is in the correct directory

### Password File Not Found

**Cause:** `~/.ansible_vault_pass` doesn't exist or has wrong permissions.

**Solution:**
```bash
# Check if file exists
ls -la ~/.ansible_vault_pass

# Fix permissions
chmod 600 ~/.ansible_vault_pass
```

## Rotating Vault Password

If you need to change the vault password:

```bash
# Decrypt the vault file
ansible-vault decrypt group_vars/staging_vault.yml

# Update your password file
echo "new-password-here" > ~/.ansible_vault_pass

# Re-encrypt with new password
ansible-vault encrypt group_vars/staging_vault.yml
```

## Best Practices

1. **Never commit unencrypted secrets** to version control
2. **Share vault password securely** with team members (use 1Password, LastPass, etc.)
3. **Use strong passwords** for vault files (at least 20 characters)
4. **Keep `~/.ansible_vault_pass` secure** with `chmod 600`
5. **Commit encrypted vault files** to git (they're safe when encrypted)
6. **Use separate vault files** for each environment (staging, production)
7. **Document which variables** need to be set in vault files
8. **Test decryption** after creating/editing vault files

## Team Workflow

### For the vault password owner:

1. Generate a strong password: `openssl rand -base64 32`
2. Save to `~/.ansible_vault_pass`
3. Share password securely with team (1Password, encrypted email, etc.)

### For team members:

1. Receive vault password from owner
2. Save to `~/.ansible_vault_pass` with `chmod 600`
3. Test: `ansible-vault view group_vars/staging_vault.yml`

## Security Notes

- ⚠️ **Encrypted files are only as secure as the vault password**
- ⚠️ **Anyone with the vault password can decrypt all secrets**
- ⚠️ **Rotate vault password if it's compromised**
- ⚠️ **Don't share passwords via insecure channels** (Slack, unencrypted email)
- ✅ **Commit encrypted vault files to git** - they're safe when encrypted
- ✅ **Use ansible-vault edit** to modify secrets - it handles encryption automatically

## References

- [Ansible Vault Documentation](https://docs.ansible.com/ansible/latest/user_guide/vault.html)
- [Ansible Best Practices - Variables and Vaults](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html#variables-and-vaults)
