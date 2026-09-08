# Browser consoles

The browser never receives Proxmox VNC tickets, control-plane credentials, SSH private keys, or reusable guest passwords.

## noVNC

The launch API returns an internal `/console/{vm_id}` route. The browser opens a same-origin WebSocket authenticated by the HttpOnly session cookie. The backend requests a short-lived VNC ticket and proxies binary RFB traffic to Proxmox. The ticket exists only inside the backend connection.

## SSH terminal

The launch API returns `/terminal/{vm_id}`. Backend SSH requires both `LAB_VM_SSH_PRIVATE_KEY_PATH` and `LAB_VM_SSH_KNOWN_HOSTS`; unknown or changed host keys fail closed. Password-only shared classroom SSH is not supported by this path.

The current key is deployment-wide. Per-assignment keys and automatic rotation remain pilot work. Mount key material as a read-only secret and never bake it into an image or repository.

## Remaining live validation

The automated suite verifies authorization and the no-secret URL contract, but a real lab must validate keyboard layouts, resize behavior, binary noVNC transport, disconnect handling, changed-host-key failure, and concurrent session capacity.
