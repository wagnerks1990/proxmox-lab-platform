# Proxmox Setup Wizard

- Root credentials are used only during bootstrap and are not stored.
- API token secrets are encrypted at rest.
- `CONFIG_ENCRYPTION_KEY` must be backed up.
- If token already exists, choose a different token ID or use manual token mode.
- Deleting a cluster removes app DB config only; it does not delete Proxmox VMs.
- Env fallback for Proxmox still exists when no active DB cluster is present.
