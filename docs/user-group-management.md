# User and Group Management

This admin area manages app users, roles, and template permissions.

## Roles
- Student
- Teacher
- Admin

Development default may use `admin/admin` only for local/dev. Never use that in production.

## User workflow
1. Create user (username, email, password, role).
2. Edit display/role/active flags.
3. Reset password (hash stored server-side only; hash never returned).
4. Assign direct template permissions.
5. Review activity summary (VM/session/audit counts).

## Deactivate vs delete
- If a user has dependent records (VMs/sessions/audit logs), API prefers deactivation unless forced.
- User/group management never deletes Proxmox VMs.

## Group/Class workflow
1. Create group/class.
2. Add/remove group members.
3. Assign group template permissions.
4. Group deletion removes memberships/permissions only; users remain.

## Direct vs group permissions
- Direct permissions are stored per user (`permissions` table).
- Group template permissions are stored per group (`group_template_permissions`).
- If no templates are imported, import Proxmox templates before assigning permissions.

## Security
- `password_hash` is never exposed by admin APIs.
- Direct and group template-permission endpoints remain available for alpha
  data migration, but they do not authorize V2 student provisioning. Use the
  Classroom lab-run assignment workflow for student VM access.
- Passwords are never logged or returned.
- No Proxmox credentials/secrets are exposed in user/group management endpoints.
