from app.services.pool_service import PoolService


def test_invalid_template_size_range_style_validation():
    errs = PoolService(db=None).validate_pool_config({
        'default_protocol': 'NOVNC',
        'pool_type': 'persistent',
        'vmid_start': 20,
        'vmid_end': 10,
        'desired_size': 1,
    })
    assert 'vmid range invalid' in errs


def test_invalid_protocol_and_pool_type():
    errs = PoolService(db=None).validate_pool_config({
        'default_protocol': 'BAD',
        'pool_type': 'BAD',
        'desired_size': 0,
    })
    assert 'protocol not allowed' in errs
    assert 'pool_type not allowed' in errs
