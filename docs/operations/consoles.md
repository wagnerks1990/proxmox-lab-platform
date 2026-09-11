# Browser consoles

The browser never receives Proxmox VNC tickets, control-plane credentials, SSH private keys, or reusable guest passwords.

## noVNC

The launch API returns an internal `/console/{vm_id}` route. The browser opens a same-origin WebSocket authenticated by the HttpOnly session cookie. The backend requests a short-lived VNC ticket and proxies binary RFB traffic to Proxmox. The ticket exists only inside the backend connection.

## SSH terminal

SSH terminal access is disabled by default with `SSH_TERMINAL_ENABLED=false`.
The API rejects terminal launch and WebSocket requests while it is disabled, and
the web application does not expose a terminal launch control.

Do not enable the pilot merely because a deployment-wide key and known-hosts
file exist. Before setting `SSH_TERMINAL_ENABLED=true`, the deployment must use
per-assignment credentials and prove that the connection destination is bound
to trusted IPAM, DHCP, MAC, and assignment data rather than a guest-agent claim.
A hostile guest reporting another VM or management address must fail before any
TCP connection is attempted. Unknown or changed host keys must also fail closed.

## Remaining live validation

The automated suite verifies authorization and the no-secret URL contract, but a real lab must validate keyboard layouts, resize behavior, binary noVNC transport, disconnect handling, changed-host-key failure, hostile guest IP claims, credential isolation, and concurrent session capacity.
