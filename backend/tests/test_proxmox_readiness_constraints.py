from app.api.routers.admin_proxmox_setup import _compute_asset_constraints


def test_single_node_assets_ready_pass_shape():
    data = _compute_asset_constraints(
        online_nodes={"pve-lab-01"},
        eligible_nodes={"pve-lab-01"},
        templates=[{"vmid": 303, "node": "pve-lab-01"}],
        iso_items=[{"node": "pve-lab-01", "content_id": "local:iso/ubuntu.iso"}],
        placement_policy="balanced",
    )
    assert data["asset_ready_nodes"] == ["pve-lab-01"]
    assert data["constrained_nodes"] == []


def test_multi_node_assets_cluster_wide_pass_shape():
    data = _compute_asset_constraints(
        online_nodes={"pve-lab-01", "pve-lab-02"},
        eligible_nodes={"pve-lab-01", "pve-lab-02"},
        templates=[{"vmid": 303, "node": "pve-lab-01"}, {"vmid": 303, "node": "pve-lab-02"}],
        iso_items=[
            {"node": "pve-lab-01", "content_id": "local:iso/ubuntu.iso"},
            {"node": "pve-lab-02", "content_id": "local:iso/ubuntu.iso"},
        ],
        placement_policy="balanced",
    )
    assert set(data["asset_ready_nodes"]) == {"pve-lab-01", "pve-lab-02"}
    assert data["constrained_nodes"] == []


def test_multi_node_template_node_limited_warn_shape():
    data = _compute_asset_constraints(
        online_nodes={"pve-lab-01", "pve-lab-02", "pve-lab-03"},
        eligible_nodes={"pve-lab-01", "pve-lab-02", "pve-lab-03"},
        templates=[{"vmid": 303, "node": "pve-lab-01"}],
        iso_items=[],
        placement_policy="balanced",
    )
    assert data["asset_ready_nodes"] == ["pve-lab-01"]
    assert set(data["constrained_nodes"]) == {"pve-lab-02", "pve-lab-03"}
    assert 303 in data["missing_templates_by_node"]["pve-lab-02"]


def test_multi_node_iso_node_limited_warn_shape():
    data = _compute_asset_constraints(
        online_nodes={"pve-lab-01", "pve-lab-02", "pve-lab-03"},
        eligible_nodes={"pve-lab-01", "pve-lab-02", "pve-lab-03"},
        templates=[],
        iso_items=[{"node": "pve-lab-01", "content_id": "local:iso/ubuntu.iso"}],
        placement_policy="balanced",
    )
    assert data["asset_ready_nodes"] == ["pve-lab-01"]
    assert set(data["constrained_nodes"]) == {"pve-lab-02", "pve-lab-03"}
    assert "local:iso/ubuntu.iso" in data["missing_isos_by_node"]["pve-lab-02"]


def test_manual_policy_uses_eligible_nodes_only():
    data = _compute_asset_constraints(
        online_nodes={"pve-lab-01", "pve-lab-02"},
        eligible_nodes={"pve-lab-01"},
        templates=[{"vmid": 303, "node": "pve-lab-01"}],
        iso_items=[],
        placement_policy="manual",
    )
    assert data["asset_ready_nodes"] == ["pve-lab-01"]
    assert data["constrained_nodes"] == []
    assert "pve-lab-02" not in data["missing_templates_by_node"]
