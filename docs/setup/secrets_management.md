# Secrets Management

Secrets in `group_vars/dev.yml` and `group_vars/test.yml` are encrypted inline using `ansible-vault encrypt_string`. There are no separate vault files — encrypted values live directly in the group_vars file next to the plaintext config.

The vault password is stored in `.vault-password` at the project root (inside `dataverse-ansible/`). This file is gitignored and must be backed up externally (LastPass or equivalent). If it's lost, the encrypted secrets are unrecoverable.

## Initial setup

```bash
# Generate a vault password (run once per environment)
openssl rand -base64 24 > dataverse-ansible/.vault-password
chmod 600 dataverse-ansible/.vault-password
```

Save the contents somewhere secure before doing anything else.

## Encrypting a secret

Run from inside `dataverse-ansible/`:

```bash
ansible-vault encrypt_string 'the-actual-secret' \
  --name variable_name \
  --encrypt-vault-id default \
  --vault-password-file .vault-password
```

Copy the full output block into the group_vars file:

```yaml
variable_name: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          61626633376333653337323536393531...
```

## What's encrypted in our setup

`dev.yml` and `test.yml` both encrypt these three:
- `dataverse_adminpass`
- `dataverse_postgresql_password`
- `payara_adminpass`

One constraint that causes real problems if missed: `dataverse_postgresql_password` in group_vars must match `db_password` in `terraform.tfvars` exactly. Terraform creates the RDS instance with one value; Ansible connects to it with the other. They're set independently.

## Viewing or rotating a secret

There's no `ansible-vault edit` for inline strings. To rotate: generate a new value, encrypt it with the command above, and replace the vault block in group_vars. Commit the change.

## Running playbooks

Ansible finds `.vault-password` automatically via `vault_password_file = .vault-password` in `ansible.cfg`. No flags needed:

```bash
ansible-playbook -i ../terraform-dataverse/environments/tim/inventory-dev.yml site.yml
```

If someone else's machine doesn't have `.vault-password`, they'll get a decryption error. Share the password via LastPass, not Slack.
