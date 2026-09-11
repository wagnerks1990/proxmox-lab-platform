# LabGoblin brand and naming

## Canonical identity

| Item | Value |
| --- | --- |
| Product | **LabGoblin** |
| Category | Virtual Lab Provisioning & Management |
| Primary tagline | **Real Skills. Virtual Machines.** |
| Campaign line | **Build. Deploy. Learn. Repeat.** |
| Alternate campaign line | Virtual Labs. Real Opportunities. |

LabGoblin is the product. Proxmox VE is currently the primary hypervisor integration and should be named only where the underlying platform matters technically.

## Positioning

LabGoblin gives instructors and students a controlled layer over virtual lab infrastructure. It covers templates, assignments, lab runs, provisioning, lifecycle operations, access policy, reconciliation, and auditing without exposing broad hypervisor access to students.

In the broader Goblin product family:

- **RoomGoblin** manages classrooms and physical labs.
- **LabGoblin** manages virtual labs and student virtual environments.
- **PatchGoblin** is reserved for patch/update management.
- **ScreenGoblin** is reserved for digital signage.

Avoid copy that makes these products sound interchangeable.

## Voice

LabGoblin should sound technical, capable, approachable, education-first, and slightly playful. Use direct language. The goblin identity adds personality; it must not reduce clarity around security, destructive actions, permissions, or operational status.

## Color system

| Token | Hex | Purpose |
| --- | --- | --- |
| Goblin Green | `#22C55E` | Primary brand/action |
| Deep Space | `#0B1220` | Main dark background |
| Slate Surface | `#1F2937` | Cards/panels |
| Steel Secondary | `#3B4754` | Secondary UI |
| Cloud Light | `#E5E7EB` | Light neutral/text |
| Mint Accent | `#A7F3D0` | Success/highlight |
| White | `#FFFFFF` | High-contrast text |

Green should identify primary actions, active state, success, and brand emphasis. Do not flood large UI surfaces with saturated green. Never rely on green alone to communicate state; use text and/or an icon as well.

## Typography

- Preferred UI/body: **Inter**.
- Optional display/marketing: **Poppins**.
- Fallback: `system-ui, "Segoe UI", Arial, sans-serif`.

Font binaries are not stored in the repository. Use properly licensed sources if web fonts are added later.

## Logo and icon

The canonical application icon is `frontend/public/brand/labgoblin-icon.svg`.

Rules:

- Do not stretch, skew, or rotate the logo.
- Keep adequate clear space around the mark.
- Do not recolor the green mark arbitrarily.
- Do not use decorative glow/shadow effects where they reduce legibility.
- Use accessible `alt` text when the mark communicates identity; use empty `alt` text when adjacent text already says LabGoblin.

## Product naming

Write the product as **LabGoblin** with capital L and G.

Acceptable technical identifiers for new, non-compatibility-sensitive work:

- `labgoblin`
- `lab-goblin`

Do not create new technical identifiers named `proxmox-lab-platform` unless they are explicitly required for backward compatibility.

## Legacy compatibility boundary

The following identifiers currently remain intentionally unchanged because existing deployments, updates, rollback, credentials, or automation may depend on them:

- GitHub repository slug: `wagnerks1990/proxmox-lab-platform`
- install root: `/opt/proxmox-lab-platform`
- state root: `/var/lib/proxmox-lab-platform`
- updater service/group/files containing `proxmox-lab-updater`
- existing environment variable names beginning with `PROXMOX_`, because those describe the integration
- existing database/schema names such as `proxmox_lab`
- API fields/routes that explicitly describe Proxmox integration objects

These are implementation compatibility identifiers, not the public product name.

## Future repository rename

When the GitHub repository itself is renamed to `labgoblin`, update all of the following in one compatibility-reviewed change:

1. README installation URLs.
2. `mkdocs.yml` `repo_url`.
3. updater default repository URL.
4. `.env.example` updater repository URL.
5. deployment/first-run documentation.
6. tests and fixtures that assert repository URLs.
7. automation or external deployment references.

GitHub normally redirects old repository URLs after a rename, but do not rely on that as the sole updater migration strategy. Existing installations should be tested for fetch/update/rollback behavior.

## AI/coding-agent contract

Agents must read `AI_CONTEXT.md`, `AGENTS.md`, and this file before branding or infrastructure changes. Agents must keep documentation synchronized and must not weaken authorization, tenant isolation, secret handling, auditability, durable operations, update safety, or rollback behavior for the sake of rebranding.
