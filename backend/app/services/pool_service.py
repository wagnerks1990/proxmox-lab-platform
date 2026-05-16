from sqlalchemy.orm import Session
from app.models.models import DesktopPool
from app.architecture.events import bus, DomainEvent

ALLOWED_PROTOCOLS = {'SSH_WS', 'NOVNC', 'SPICE', 'RDP'}
ALLOWED_POOL_TYPES = {'persistent', 'non_persistent'}


class PoolService:
    def __init__(self, db: Session):
        self.db = db

    def validate_pool_config(self, payload: dict) -> list[str]:
        errs = []
        start, end = payload.get('vmid_start'), payload.get('vmid_end')
        desired_size = payload.get('desired_size', 0)
        if start is not None and end is not None and start > end:
            errs.append('vmid range invalid')
        if start is not None and end is not None and desired_size > (end - start + 1):
            errs.append('desired_size exceeds vmid range')
        if payload.get('default_protocol') not in ALLOWED_PROTOCOLS:
            errs.append('protocol not allowed')
        if payload.get('pool_type') not in ALLOWED_POOL_TYPES:
            errs.append('pool_type not allowed')
        vlan = payload.get('vlan_tag')
        if vlan is not None and (vlan < 1 or vlan > 4094):
            errs.append('vlan tag must be 1-4094')
        pattern = payload.get('naming_pattern')
        if pattern and '{index}' not in pattern and '{vmid}' not in pattern:
            errs.append('naming_pattern should include {index} or {vmid}')
        if errs:
            bus.publish(DomainEvent(name='VALIDATION_FAILED', payload={'scope': 'pool', 'errors': errs}))
        return errs
