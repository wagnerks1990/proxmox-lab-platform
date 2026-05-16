from app.services.pool_service import PoolService


def test_pool_validation_flags_bad_inputs():
    svc = PoolService(None)
    errs = svc.validate_pool_config({'pool_type':'x','default_protocol':'bad','vlan_tag':5000,'vmid_start':200,'vmid_end':100,'desired_size':5,'naming_pattern':'pool'})
    assert errs
