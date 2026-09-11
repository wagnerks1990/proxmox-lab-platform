#!/usr/bin/env python3
"""Run a destructive, disposable end-to-end classroom VM lifecycle test."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import time
import urllib.error
import urllib.parse
import urllib.request


ADMIN_PASSWORD = "LiveTest-Admin-42!"
STUDENT_PASSWORD = "LiveTest-Student-42!"


class Client:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        parsed = urllib.parse.urlsplit(self.base_url)
        self.origin = f"{parsed.scheme}://{parsed.netloc}"
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies)
        )
        self.organization_id: int | None = None

    def request(
        self,
        method: str,
        path: str,
        payload: object | None = None,
        *,
        expected: set[int] = {200},
    ):
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {
            "Content-Type": "application/json",
            # Exercise the browser's cookie/Origin CSRF contract.
            "Origin": self.origin,
        }
        if self.organization_id is not None:
            headers["X-Organization-ID"] = str(self.organization_id)
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, headers=headers, method=method
        )
        try:
            with self.opener.open(request, timeout=30) as response:
                body = response.read()
                if response.status not in expected:
                    raise RuntimeError(
                        f"{method} {path}: expected {sorted(expected)}, got {response.status}"
                    )
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            if exc.code in expected:
                return json.loads(body) if body else None
            raise RuntimeError(
                f"{method} {path}: HTTP {exc.code}: {body[:1000]}"
            ) from exc


def data(response: dict) -> object:
    if response.get("success") is not True:
        raise RuntimeError(f"API envelope reported failure: {response}")
    return response["data"]


def poll_operation(client: Client, operation_id: int, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        operation = client.request("GET", f"/api/operations/{operation_id}")
        if operation["state"] == "succeeded":
            return operation
        if operation["state"] == "failed":
            raise RuntimeError(
                f"operation {operation_id} failed: {operation.get('error')}"
            )
        time.sleep(1)
    raise TimeoutError(f"operation {operation_id} did not finish within {timeout:g}s")


def run(base_url: str, bootstrap_token: str, timeout: float) -> None:
    client = Client(base_url)
    ready = client.request("GET", "/api/ready")
    if ready.get("ready") is not True:
        raise RuntimeError(f"readiness response was not ready=true: {ready}")

    client.request(
        "POST",
        "/api/bootstrap/admin",
        {
            "token": bootstrap_token,
            "username": "live-admin",
            "email": "live-admin@example.com",
            "password": ADMIN_PASSWORD,
        },
        expected={204},
    )
    organization = client.request(
        "POST",
        "/api/admin/organizations",
        {"name": "Disposable Live Test", "slug": "disposable-live-test"},
        expected={201},
    )
    client.organization_id = organization["id"]

    cluster = client.request(
        "POST",
        "/api/admin/proxmox/clusters/manual-token",
        {
            "name": "mock",
            "api_url": "https://mock-proxmox:8006/api2/json",
            "token_user": "live-test@pve",
            "token_id": "platform",
            "token_secret": "live-test-only",
            "verify_ssl": False,
        },
    )
    client.request(
        "POST", f"/api/admin/proxmox/clusters/{cluster['cluster_id']}/activate"
    )
    imported = client.request(
        "POST",
        "/api/admin/proxmox/templates/import",
        {
            "name": "Classroom Template",
            "node": "pve-live-test",
            "vmid": 9000,
            "enabled": True,
        },
    )
    template_id = imported["imported"][0]["id"]

    student = client.request(
        "POST",
        "/api/admin/users",
        {
            "username": "live-student",
            "email": "live-student@example.com",
            "password": STUDENT_PASSWORD,
            "role": "Student",
            "force_password_change": False,
        },
    )
    client.request(
        "PUT",
        f"/api/admin/organizations/{organization['id']}/members/{student['id']}",
        {"role": "student", "is_active": True},
    )
    classroom = data(
        client.request("POST", "/api/admin/classes", {"name": "Live Test Class"})
    )
    client.request(
        "POST",
        f"/api/admin/classes/{classroom['id']}/enrollments",
        {"user_id": student["id"], "role": "student"},
    )
    pool = data(
        client.request(
            "POST",
            "/api/admin/pools",
            {
                "name": "Live Test Pool",
                "pool_type": "persistent",
                "template_vmid": 9000,
                "template_node": "pve-live-test",
                "default_protocol": "NOVNC",
                "target_node": "pve-live-test",
            },
        )
    )
    lab = data(
        client.request(
            "POST",
            "/api/admin/labs",
            {
                "class_id": classroom["id"],
                "name": "Live Test Lab",
                "default_pool_id": pool["id"],
                "student_can_power_off": True,
            },
        )
    )
    lab_run = data(
        client.request(
            "POST",
            "/api/admin/lab-runs",
            {"lab_id": lab["id"], "name": "Live Test Run", "max_vms_per_student": 1},
            expected={201},
        )
    )
    assignment = data(
        client.request(
            "POST",
            f"/api/admin/lab-runs/{lab_run['id']}/assignments",
            {"user_id": student["id"], "template_id": template_id},
            expected={201},
        )
    )
    data(
        client.request(
            "PATCH",
            f"/api/admin/lab-runs/{lab_run['id']}/state",
            {"action": "activate"},
        )
    )

    client.request("POST", "/api/auth/logout", expected={204})
    client.request(
        "POST",
        "/api/auth/login",
        {"username": "live-student", "password": STUDENT_PASSWORD},
        expected={204},
    )
    create = client.request(
        "POST",
        "/api/vms",
        {
            "template_id": template_id,
            "assignment_id": assignment["id"],
            "lab_name": "live",
            "auto_start": True,
        },
        expected={202},
    )
    poll_operation(client, create["operation_id"], timeout)
    vm_id, vmid = create["id"], create["vmid"]
    stopped = client.request("POST", f"/api/vms/{vm_id}/stop", expected={202})
    poll_operation(client, stopped["operation_id"], timeout)
    started = client.request("POST", f"/api/vms/{vm_id}/start", expected={202})
    poll_operation(client, started["operation_id"], timeout)

    client.request("POST", "/api/auth/logout", expected={204})
    client.request(
        "POST",
        "/api/auth/login",
        {"username": "live-admin", "password": ADMIN_PASSWORD},
        expected={204},
    )
    deleted = client.request(
        "DELETE",
        f"/api/vms/{vm_id}?{urllib.parse.urlencode({'confirmation': f'DELETE {vmid}'})}",
        expected={202},
    )
    poll_operation(client, deleted["operation_id"], timeout)
    client.request("GET", f"/api/vms/{vm_id}/status", expected={404})
    client.request("POST", "/api/auth/logout", expected={204})
    print(
        "live test passed: bootstrap, classroom authorization, VM lifecycle, deletion, and logout",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--bootstrap-token", required=True)
    parser.add_argument("--operation-timeout", type=float, default=90)
    parser.add_argument("--i-understand-this-deletes-data", action="store_true")
    args = parser.parse_args()
    host = urllib.parse.urlsplit(args.base_url).hostname
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("refusing to run: --base-url must use a loopback host")
    if not args.i_understand_this_deletes_data:
        raise SystemExit("refusing to run without --i-understand-this-deletes-data")
    run(args.base_url, args.bootstrap_token, args.operation_timeout)


if __name__ == "__main__":
    main()
