# Organization tenancy

Organizations are the isolation boundary for classroom resources. The API,
not the browser, decides whether a user may enter an organization and access an
object within it.

## Request contract

Authenticated resource requests may include:

```http
X-Organization-ID: 42
```

The value is an integer organization ID. It is not a credential. On every
request, the API confirms that the organization is enabled and that the user
has an active membership with a recognized tenant role.

| Account state | API behavior |
|---|---|
| One active organization | Selects it automatically if the header is absent |
| Multiple active organizations | Returns `400` until `X-Organization-ID` is supplied |
| No active organization | Returns `403` |
| Unknown or disabled organization | Returns `404` |
| Active user without membership | Returns `403` |
| Global platform `Admin` | May select an enabled organization using break-glass access |

Use `GET /api/organizations` to list the organizations the current account can
select. The web application stores the selected ID in local storage and adds
the header through its shared API client.

## Scoped resources

The following records carry `organization_id` and are filtered before object-
level authorization is evaluated:

- VM templates and student VMs;
- VM sessions and console access;
- desktop pools;
- groups and template permissions;
- classes, enrollments through their class, and labs;
- tenant audit events.

Infrastructure configuration such as the physical Proxmox cluster remains a
platform-level resource in this development phase. Live inventory can be
observed globally, but links to application templates and VMs are resolved only
inside the selected organization.

## Administrative safety

Creating an organization makes the creating platform administrator its first
active owner. The API rejects demoting or deactivating the last active owner.
Template imports, dashboard counts, event history, user-template permissions,
and reconciliation previews all use the selected organization.

## Tenant role policy

Tenant roles are ordered by authority:

| Role | Current authority |
|---|---|
| `student` | Use only owned VMs linked to an active enrollment, lab run, and assignment |
| `instructor` | Student authority plus templates, pools, sessions, events, and assigned-class/lab management |
| `admin` | Instructor authority plus organization groups and all classes in the organization |
| `owner` | Full tenant authority and protection from removing the organization's last active owner |

Tenant authority is evaluated from the selected active membership. A user's
legacy global role does not elevate that user inside a tenant. For example, a
globally labeled `Student` with an `instructor` membership receives instructor
authority in that organization, while the same account remains a student in a
different organization.

Instructors see and modify only classes assigned to their user ID and labs
belonging to those classes. Organization administrators and owners may manage
all classes in their organization. Physical Proxmox configuration, global user
accounts, organization creation, and deployment updates remain platform-admin
functions.

## WebSocket and streaming clients

WebSocket clients cannot set arbitrary HTTP headers in all browsers, so console
connections use an `organization_id` query parameter alongside the existing
short-lived authorization flow. The server still verifies membership before
loading the VM. Organization IDs are not secrets.

The event stream is authenticated separately because the browser `EventSource`
API cannot set an authorization header. The selected organization is sent as a
query parameter, verified with the authenticated user, and the server emits
only matching tenant-tagged events. Untagged system events are not sent through
this tenant stream. Persisted tenant audit history is also scoped.

## Development migration

Migration `20260907_0011` attaches existing core records to the `default`
organization created by migration `20260907_0009`. It then makes tenant columns
non-null where system events are not valid and converts global resource-name
uniqueness into per-organization uniqueness.

Before a future production release, run the authorization matrix against at
least two organizations and verify REST, console, dashboard, reconciliation,
and permission endpoints with same-ID and cross-ID attempts.
