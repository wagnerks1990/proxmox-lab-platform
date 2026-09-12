# Cloudflare edge and at-home student access

Cloudflare is an optional deployment edge for LabGoblin. It can publish the
existing web application without an inbound Internet listener and can add an
identity-aware gate before LabGoblin. It does not replace LabGoblin login,
organization membership, tenant isolation, role checks, session revocation, or
application rate limits.

The integration is disabled by default. Enabling it is a host operation, not a
setting available to a browser administrator. For a classroom deployment,
Cloudflare Tunnel plus Access is the recommended public connection path: it
lets students reach an assigned lab from home without publishing the appliance
or asking each student to install a VPN client.

## Student journey and security boundary

The intended student experience is deliberately simple:

1. Open the instructor-provided HTTPS URL from a normal browser.
2. Complete the district identity-provider sign-in and MFA required by the
   Cloudflare Access policy.
3. Sign in to LabGoblin with the student's LabGoblin account.
4. Open only the browser consoles and lab resources assigned to that student
   during the active run window.

Students do **not** need a Cloudflare account, WARP, a VPN client, a Tunnel
token, or access to the Cloudflare dashboard. Cloudflare Access is the outer
district-identity gate; LabGoblin login, enrollment, assignment windows,
ownership, RBAC, session revocation, and audit remain the application authority.

The public hostname exposes only LabGoblin's web proxy. It must never publish a
Proxmox management interface, SSH service, PostgreSQL, Redis, updater socket,
hypervisor API, VM network, or other internal service. Student remote work uses
LabGoblin's assigned browser-console path, not direct access to the management
plane or lab network.

## Supported design

Browser and API traffic passes through Cloudflare DNS, TLS, WAF, and Access,
then crosses the outbound Tunnel to the `cloudflared` container. The connector
reaches the LabGoblin web proxy over the private Compose network; the proxy
forwards API traffic to the backend on the normal internal network.

The `cloudflare` Compose profile starts the `cloudflared` service. The connector
read-only bind-mounts the restricted host token file
`/etc/labgoblin/cloudflare-tunnel-token` and connects outward to Cloudflare. The
host's LabGoblin HTTP port is bound to loopback with
`HTTP_BIND_ADDRESS=127.0.0.1`, so
the public path cannot bypass Cloudflare by addressing the appliance directly.
Do not add a public A or AAAA record for the appliance.

Cloudflare documents Tunnel as an outbound-only connection that does not
require a publicly routable origin. The connector requires outbound port 7844
over UDP for QUIC or TCP for HTTP/2. See the
[Tunnel overview](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/)
and [firewall requirements](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-with-firewall/).

## Prerequisites

- A domain managed in Cloudflare DNS.
- An exact HTTPS hostname such as `https://lab.example.edu`. Wildcard browser
  origins are not accepted.
- A Cloudflare Zero Trust team domain such as
  `school.cloudflareaccess.com` and the district identity provider connected to
  Access.
- A reusable Cloudflare Access group whose Include rule maps the district IdP
  group containing only students and staff approved for remote LabGoblin
  access. Pass the Cloudflare Access group ID, not an unverified display name or
  raw IdP assertion. This is strongly recommended. An allowed email domain is
  supported as a simpler fallback, but it is weaker because every account in
  that domain can pass the outer gate unless separately excluded.
- A temporary, root-readable file containing a narrowly scoped Cloudflare API
  token for provisioning. Never paste the token into a command.

Create a custom Cloudflare API token limited to the one LabGoblin account and
zone with exactly these permissions:

| Scope | Resource | Permission |
| --- | --- | --- |
| Account | selected account | Cloudflare Tunnel: Edit |
| Account | selected account | Access: Apps and Policies: Edit |
| Zone | selected zone | DNS: Edit |
| Zone | selected zone | Zone: Read |

`Zone: Read` is used to resolve and verify the exact `--zone` name. Do not grant
account-wide DNS, Access user/session management, Workers, R2, billing, or
global-key access.
LabGoblin runtime services never receive this provisioning token. Cloudflare
documents remotely managed tunnel creation and token permissions in its
[Tunnel API guide](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel-api/).
Do not use a temporary Quick Tunnel for a production or classroom deployment.

## Guided automated provisioning

`deploy/provision_cloudflare.py` is the preferred setup path. It plans and then
reconciles a named Tunnel, its `http://web:8080` ingress configuration, one
reusable Access policy, the exact-hostname self-hosted Access application, and
the proxied DNS record. DNS is created last so a partially configured path is
not advertised. After Cloudflare accepts the configuration, the provisioner
retrieves the Tunnel run token and invokes the local secure configuration helper.

Only nonsecret Cloudflare resource IDs are saved for later reconciliation.
Neither the API token nor Tunnel token is written to the repository, `.env`,
database, normal logs, or provisioner state. Keep the API token in a protected
temporary file and remove or revoke it after setup.

First preview the exact operations. Prefer the district IdP group form:

```bash
cd /opt/labgoblin/app
sudo python3 deploy/provision_cloudflare.py plan \
  --api-token-file /root/cloudflare-api-token \
  --account-id CLOUDFLARE_ACCOUNT_ID \
  --zone example.edu \
  --hostname lab.example.edu \
  --team-domain school.cloudflareaccess.com \
  --access-group-id CLOUDFLARE_ACCESS_GROUP_ID
```

Review the plan for the exact account, zone, hostname, origin service, and
Access selector. Then apply the same arguments with `apply`:

```bash
sudo python3 deploy/provision_cloudflare.py apply \
  --api-token-file /root/cloudflare-api-token \
  --account-id CLOUDFLARE_ACCOUNT_ID \
  --zone example.edu \
  --hostname lab.example.edu \
  --team-domain school.cloudflareaccess.com \
  --access-group-id CLOUDFLARE_ACCESS_GROUP_ID
sudo deploy/configure-cloudflare.sh status --json
```

Exactly one Access selector is required. If the district cannot yet supply a
group, replace `--access-group-id` with `--allow-email-domain students.example.edu`.
That fallback is broader and must be recorded as a pilot risk. Never use an
Everyone or Bypass policy for convenience. Set `--session-duration` to the
district-approved Access reauthentication interval when the default is not
appropriate. An Access session never extends a LabGoblin login, assignment, or
run window.

The provisioner is idempotent: rerun `plan` with the same protected arguments
to verify the resources it owns. It creates missing resources, but stops for
explicit review rather than silently overwriting configuration drift. By
default it does not adopt or overwrite an unrelated Tunnel, Access
application, policy, or DNS record with the same name.
Use `--adopt-existing` only after independently verifying the resource IDs,
configuration, ownership, and impact shown in the plan. For unattended
execution, `--yes` suppresses only the final confirmation after that review; it
does not bypass validation, ownership, or conflict checks. DNS is attempted
only after the Access, Tunnel, and local health gates. If a create request has
an ambiguous network outcome, the tool stops without retrying it and requires
fresh discovery before adoption. A failed local startup leaves the origin
loopback-bound. The local helper's `status --json` is suitable for
operator checks and contains no secret values. These controls are covered by
offline tests; final acceptance still requires the real staging checks below
against the district's Cloudflare account and identity provider.

## Manual Cloudflare-side setup

Use this path only when API-driven provisioning is prohibited. It produces the
same resource and security contract as the guided provisioner.

1. Add the public domain to Cloudflare DNS and verify that the intended
   hostname does not reveal or resolve directly to the appliance address.
2. Create a remotely managed, named Tunnel for this LabGoblin appliance.
3. Add a published application route for `lab.example.edu` with service URL
   `http://web:8080`. The name `web` resolves only on the connector's private
   Compose network. A remotely managed configuration supplies the required
   unmatched-route behavior.
4. Create a Cloudflare Access self-hosted application covering the exact same
   hostname. Add a least-privilege Allow policy for the intended identity group;
   do not create an Everyone or Bypass rule merely to simplify initial testing.
5. Record the Access application audience tag and the
   `<team>.cloudflareaccess.com` team domain.
6. Copy the named Tunnel token into a temporary protected file on the appliance.
   Do not paste the token itself into the `enable` command.

Cloudflare's current workflows are documented in
[Set up your first tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/),
[Published applications](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/),
and [Publish a self-hosted application](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/).

## Enable

Save the Tunnel token in a temporary root-readable file without including its
value in a command or shell history. Then run the host configuration helper
from the installed checkout:

```bash
cd /opt/labgoblin/app
sudo deploy/configure-cloudflare.sh enable \
  --hostname lab.example.edu \
  --team-domain school.cloudflareaccess.com \
  --audience 0123456789abcdef0123456789abcdef \
  --token-file /root/cloudflare-tunnel-token
sudo deploy/configure-cloudflare.sh status --json
```

The helper validates the hostname, team domain, audience, JWKS TTL, and token
file. It copies the token to the protected destination, validates the Compose
configuration, and starts the API, web, and connector with Compose `--wait`.
The connector health check must pass before enablement succeeds. If startup
fails, it restores the previous environment and restarts the normal API and web
services while keeping the host HTTP listener on loopback.
It configures this deployment contract:

```dotenv
CLOUDFLARE_TUNNEL_ENABLED=true
CLOUDFLARE_PUBLIC_HOSTNAME=lab.example.edu
CLOUDFLARE_ACCESS_REQUIRED=true
CLOUDFLARE_ACCESS_TEAM_DOMAIN=school.cloudflareaccess.com
CLOUDFLARE_ACCESS_AUDIENCE=0123456789abcdef0123456789abcdef
CLOUDFLARE_ACCESS_JWKS_TTL_SECONDS=3600
CLOUDFLARE_TUNNEL_TOKEN_FILE=/etc/labgoblin/cloudflare-tunnel-token
CLOUDFLARE_TUNNEL_GID=1234
HTTP_BIND_ADDRESS=127.0.0.1
AUTH_COOKIE_SECURE=true
BROWSER_TRUSTED_ORIGINS=https://lab.example.edu
CORS_ALLOWED_ORIGINS=
```

The helper creates the `labgoblin-cloudflared` system group, resolves its
numeric GID, and installs the token as `root:labgoblin-cloudflared` mode `0440`.
Compose gives the otherwise non-root connector that numeric supplementary GID;
no other group or user receives read access. The file is read-only inside the
connector and must not be copied into `.env`, Compose YAML, the database,
support bundles, or shell history. `cloudflared` receives it as a read-only bind
mount. Compose falls back to the unprivileged numeric group `65534` when the GID
is absent, so manually starting the profile without running the helper fails
closed on token readability rather than granting root-group access.
Cloudflare supports a protected token file through `--token-file`; see
[Tunnel run parameters](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/).

The browser origin must contain only scheme and hostname, plus a non-default
port when one is genuinely public. Do not add a path, trailing slash, wildcard,
HTTP alternative, or the private appliance address. Secure cookies are
mandatory on the public route. Keep CORS empty for the same-origin application
unless a separately reviewed API client requires an exact origin.

## Cloudflare Access

Access is an outer gate. It can reject an unauthenticated request at
Cloudflare, but a request that passes Access must still authenticate to
LabGoblin and pass every normal RBAC and tenant check. Do not automatically
translate an Access email, group, or service token into a LabGoblin role.

The setup helper requires Access JWT validation at the origin and configures:

```dotenv
CLOUDFLARE_ACCESS_REQUIRED=true
CLOUDFLARE_ACCESS_TEAM_DOMAIN=school.cloudflareaccess.com
CLOUDFLARE_ACCESS_AUDIENCE=your-application-aud-tag
CLOUDFLARE_ACCESS_JWKS_TTL_SECONDS=3600
```

Use the exact team domain and Access application audience tag. When required,
LabGoblin validates the `Cf-Access-Jwt-Assertion` signature with the team's
JWKS and checks issuer, audience, and time claims before normal application
authentication. A missing or invalid assertion is denied. Merely checking that
the header exists is unsafe. Cloudflare recommends validating the assertion
header rather than relying on the `CF_Authorization` cookie; see
[Validate JWTs](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/)
and [Application token](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/application-token/).

For people, create an Access **Allow** policy based on the school's identity
provider and require MFA there when appropriate. For automation, create a
separate **Service Auth** policy and a dedicated service token. Do not use a
person's browser cookie for scheduled jobs. Rotate service-token secrets, use
Cloudflare's rotation grace period only while deploying both sides, and delete
the old token after verification. See [Access policies](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/)
and [Service tokens](https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/).

Turning Access on at the Cloudflare dashboard before setting and verifying the
three LabGoblin validation values can lock out every user. Conversely, the
helper's required mode denies every non-health request until the Access
application issues the expected audience. Stage and test the Cloudflare and
LabGoblin changes as one maintenance operation. The local `/api/health` and
`/api/ready` probes intentionally bypass origin Access validation so a broken
JWKS path cannot hide process health; loopback binding prevents that exception
from becoming an independent public route. Keep the same paths protected by
the Cloudflare Access application at the edge unless public health monitoring
is a reviewed requirement.

## Headers and client addresses

Cloudflare supplies `CF-Connecting-IP`, `X-Forwarded-Proto`, and `Cf-Ray` to the
origin. LabGoblin currently does not promote these values into identity or
audit fields. Never trust similarly named headers received through an
independent LAN or public listener. If a future feature consumes them, the
exclusive Tunnel path must be positively established first.

- Future use of `CF-Connecting-IP` is request metadata, not identity or
  authorization.
- Future use of `X-Forwarded-Proto` is limited to the trusted connector path when producing
  external URLs or enforcing HTTPS behavior.
- Treat `X-Forwarded-For` as an untrusted chain unless every proxy hop is known.
- `Cf-Ray` may be useful for future request correlation; it is not a credential.
- Enforce the configured public hostname and reject unexpected `Host` values.

Cloudflare describes these fields in [Cloudflare HTTP headers](https://developers.cloudflare.com/fundamentals/reference/http-headers/).
IP allowlisting is not a substitute for Tunnel or Access. Cloudflare edge IPs
are shared, and Cloudflare rates origin allowlisting as a weaker design. If a
deployment deliberately retains a direct public origin, block all non-Cloudflare
sources, keep the published ranges current, enforce the expected Host, use
Full (strict) TLS and Authenticated Origin Pulls, and document the remaining
bypass risk. Authenticated Origin Pulls has no effect on a hostname routed
through Tunnel. See [Protect your origin server](https://developers.cloudflare.com/fundamentals/security/protect-your-origin-server/),
[Cloudflare IP addresses](https://developers.cloudflare.com/fundamentals/concepts/cloudflare-ip-addresses/),
[Full (strict)](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/),
and [Authenticated Origin Pulls](https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/).

## Cache, WAF, and rate limits

Explicitly bypass Cloudflare cache for `/api/*`, login, account, administration,
SSE, WebSocket, console, and any response that carries authentication or CSRF
state. Cache only fingerprinted static frontend assets. An unsafe cache rule can
break login or mishandle `Set-Cookie`; Cloudflare's
[dynamic-content guidance](https://developers.cloudflare.com/cache/troubleshooting/dynamic-content-and-login-issues/)
explains the risk.

Enable Cloudflare managed WAF rules in log or challenge-free observation mode
first, inspect false positives, and then enforce reviewed rules. Edge controls
are defense in depth; backend validation and authorization remain required.

Use conservative route-specific rate limits for login and other expensive
unauthenticated endpoints. Many students can share one school NAT address, so
an aggressive per-IP threshold can deny an entire class. Keep application
account/session-aware throttles. Do not apply browser challenges to JSON APIs,
service-token traffic, event streams, or console handshakes. API limits should
return HTTP 429. See [Rate limiting rules](https://developers.cloudflare.com/waf/rate-limiting-rules/)
and [rate limiting best practices](https://developers.cloudflare.com/waf/rate-limiting-rules/best-practices/).

## Event streams and consoles

Cloudflare Tunnel supports HTTP and WebSocket applications. The existing
same-origin session, origin validation, RBAC, and assignment-window checks still
apply to the SSE operations stream and console WebSocket handshake. Do not put
Access assertions, service-token secrets, LabGoblin sessions, or console grants
in URLs.

Do not cache or buffer the SSE route. Configure timeouts so an intentional
long-lived connection is not treated as an abusive request. Verify stream
reconnect, session revocation, WebSocket upgrade, resize, and disconnect in the
real Cloudflare path; a healthy Tunnel status alone does not prove these flows.

## Verification

After enabling the profile:

```bash
cd /opt/labgoblin/app
sudo deploy/configure-cloudflare.sh status --json
sudo docker compose ps
curl -fsS http://127.0.0.1:8080/api/ready
```

An unauthenticated request to `https://lab.example.edu/api/ready` should be
stopped by Cloudflare Access. Test the public endpoint with an allowed browser
identity or a dedicated service token; do not place the Client Secret on a
command line or in shell history.

### Required real staging checklist

The automated test suite mocks Cloudflare APIs and Access signing keys. It does
not prove that a real Tunnel, district IdP, Cloudflare policy, browser session,
or long-lived console path works. Before a student pilot, retain dated evidence
for all of the following against a non-production LabGoblin environment:

1. `plan` shows only the intended account, zone, hostname, Tunnel, Access
   application, reusable policy, and proxied DNS record; a second `plan` after
   `apply` reports no unintended drift.
2. Local `status --json`, Compose service health, and loopback readiness are
   healthy; the connector recovers after a controlled restart.
3. DNS returns Cloudflare addresses, HTTPS has a valid certificate, and no
   public DNS record discloses the appliance address.
4. The appliance HTTP port, Proxmox UI/API, SSH, PostgreSQL, Redis, updater, and
   VM networks are unreachable from an external network.
5. A district IdP user outside the approved group is denied, an approved test
   student is accepted, and removing that student from the group closes a new
   Access session. If email-domain fallback is used, verify and record its
   intentionally broader population.
6. LabGoblin still requires its own login after Access succeeds. Disabling the
   LabGoblin account, ending the assignment, changing membership, logging out,
   and revoking the session each terminate application access.
7. A student can see and control only their assigned VM during the run window;
   direct URLs for another student, organization, admin route, Proxmox, SSH,
   database, or internal network remain denied.
8. Secure cookies, unsafe-request origin checks, expected-host enforcement,
   login throttling, logout, and session revocation work through the public
   hostname in every supported browser.
9. SSE remains connected without proxy buffering and stops after authorization
   is revoked. Browser-console WebSocket upgrade, resize, reconnect, expiry,
   revocation, and a representative 80-minute class session all succeed from a
   home/mobile connection as well as the school network.
10. API, authentication, console, and event-stream responses are not cached;
    WAF and rate-limit rules do not challenge API/WebSocket/SSE requests or
    block a classroom sharing one NAT address.
11. Missing, forged, expired, wrong-audience, and wrong-issuer Access assertions
    fail at the origin, and no forwarded Cloudflare header becomes identity or
    authorization.
12. The API-token file and temporary Tunnel-token file are removed or securely
    retained as documented; neither secret appears in state, `.env`, logs,
    process arguments, shell history, support output, or the repository.
13. Simulated Cloudflare loss leaves local health available to an operator but
    does not expose a direct-origin fallback. Intentional disable and re-enable
    both complete without changing student authorization.

## Rotation

To rotate a Tunnel token, rerun the provisioner's `plan` and `apply` workflow
with a protected API-token file. For a manually managed Tunnel, rotate it in
Cloudflare and rerun the full `deploy/configure-cloudflare.sh enable` command
with the new protected `--token-file`. Confirm connector health and the
authenticated public workflow, securely remove the temporary source file, and
re-check the installed token's root ownership and mode.

Access signing keys rotate through the published JWKS and should not be pinned
as static files. Service-token Client Secrets require their own rotation; they
are unrelated to the Tunnel token. Changing the Access application recreates or
changes its audience tag, so update and verify the LabGoblin audience in the
same maintenance window.

## Outage and local recovery

If Cloudflare or the outbound Tunnel path is unavailable, the loopback-bound
origin intentionally remains unavailable to remote users. An operator with SSH
access can still inspect services and call local health endpoints. Do not expose
the origin publicly as an outage workaround.

To intentionally remove the integration, first confirm that the appliance HTTP
port is not forwarded through an Internet firewall. `disable` removes the
connector profile but deliberately keeps HTTP bound to loopback by default.
This prevents a Cloudflare rollback from silently creating a LAN or public
listener.

```bash
cd /opt/labgoblin/app
sudo deploy/configure-cloudflare.sh disable
sudo deploy/configure-cloudflare.sh status --json
```

To restore the saved pre-Cloudflare LAN bind deliberately, use
`sudo deploy/configure-cloudflare.sh disable --restore-lan-bind` only after
confirming host and perimeter firewall policy. The helper restores the saved
browser origin, cookie, and CORS settings together with that explicit bind.
Test authentication from the replacement origin before declaring service
restored. Retain the token file only if the Tunnel is expected to return;
otherwise revoke the Tunnel credential in Cloudflare and run
`sudo deploy/configure-cloudflare.sh disable --remove-token` to remove the
installed file. The harmless dedicated system group remains in place.

Rollback of an application release does not roll back Cloudflare dashboard
resources. Record Tunnel, DNS, Access, WAF, and rate-limit changes separately so
they can be reversed in the correct order.

The LabGoblin updater preserves the `cloudflare` profile while updating a
revision that declares the connector. A rollback to a revision from before this
integration omits the unknown profile and connector, so Cloudflare publication
stops instead of blocking recovery.

## R2 backup decision

Cloudflare R2 is deliberately not integrated as a LabGoblin backup destination
yet. The current updater backup covers PostgreSQL, not the full recovery set.
Uploading it to object storage would create the appearance of disaster recovery
while omitting the encryption key, protected environment, TLS material, and
other required host state.

R2 support may be considered only after LabGoblin can produce a complete,
client-side encrypted backup; keep the encryption key outside the bucket;
upload with bucket-scoped credentials; attach checksums and a signed manifest;
apply lifecycle and immutable retention; and repeatedly restore into an
isolated environment. Relevant Cloudflare controls are documented under
[R2 authentication](https://developers.cloudflare.com/r2/api/tokens/),
[data security](https://developers.cloudflare.com/r2/reference/data-security/),
[object lifecycles](https://developers.cloudflare.com/r2/buckets/object-lifecycles/),
and [bucket locks](https://developers.cloudflare.com/r2/buckets/bucket-locks/).
R2 must not be the only backup copy.
