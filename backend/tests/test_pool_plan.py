from app.services.pool_planning_service import PoolPlanningService


class P:
    id = 1
    desired_size = 2
    vmid_start = 300
    vmid_end = 305
    naming_pattern = 'lab-{index}-{vmid}'
    name = 'labpool'
    pool_type = 'persistent'
    default_protocol = 'SSH_WS'
    vlan_tag = 100

    __dict__ = {
        'id': 1,
        'desired_size': 2,
        'vmid_start': 300,
        'vmid_end': 305,
        'naming_pattern': 'lab-{index}-{vmid}',
        'name': 'labpool',
        'pool_type': 'persistent',
        'default_protocol': 'SSH_WS',
        'vlan_tag': 100,
    }


def test_pool_plan_preview():
    out = PoolPlanningService().build_plan(P())
    assert out.desired_size == 2
    assert out.vmid_preview == [300, 301]
