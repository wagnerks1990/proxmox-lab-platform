# Proxmox Setup Wizard

- Root credentials are used only during bootstrap and are not stored.
- API token secrets are encrypted at rest.
- `CONFIG_ENCRYPTION_KEY` must be backed up.
- If token already exists, choose a different token ID or use manual token mode.
- Deleting a cluster removes app DB config only; it does not delete Proxmox VMs.
- Env fallback for Proxmox still exists when no active DB cluster is present.
- Discovery-driven defaults are available:
  - nodes
  - storage targets
  - VM templates
  - bridges/networks
- If discovery is empty/unavailable, manual defaults input is still supported.

- Placement policy options:
  - `manual` (requires online default node)
  - `balanced` (resource-aware node scoring)
  - `prefer_default_then_balance`


## Cluster readiness panel
The Proxmox Setup page includes a Cluster Readiness panel with PASS/WARN/FAIL, eligible/excluded nodes, reasons, and recommended next steps.
