import re
from datetime import datetime

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import AuditLog, DeploymentUpdateRun, DeploymentUpdateSettings


_REF_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._/-]{0,119}$')


class UpdateAgentUnavailable(RuntimeError):
    pass


class DeploymentUpdateService:
    def __init__(self, db: Session):
        self.db = db

    def get_settings(self) -> DeploymentUpdateSettings:
        row = self.db.query(DeploymentUpdateSettings).order_by(DeploymentUpdateSettings.id.asc()).first()
        if row is None:
            row = DeploymentUpdateSettings()
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
        return row

    def update_settings(self, payload: dict, actor_id: int) -> DeploymentUpdateSettings:
        row = self.get_settings()
        if 'branch' in payload:
            branch = str(payload['branch']).strip()
            if not _REF_RE.fullmatch(branch) or '..' in branch:
                raise HTTPException(status_code=422, detail='Invalid Git reference')
            row.branch = branch
        if 'channel' in payload:
            channel = str(payload['channel']).lower()
            if channel not in {'stable', 'candidate', 'development'}:
                raise HTTPException(status_code=422, detail='Invalid update channel')
            row.channel = channel
        if 'automatic_updates' in payload:
            row.automatic_updates = bool(payload['automatic_updates'])
        if 'check_interval_minutes' in payload:
            interval = int(payload['check_interval_minutes'])
            if not 15 <= interval <= 10080:
                raise HTTPException(status_code=422, detail='Check interval must be between 15 and 10080 minutes')
            row.check_interval_minutes = interval
        if 'maintenance_hour_utc' in payload:
            hour = int(payload['maintenance_hour_utc'])
            if not 0 <= hour <= 23:
                raise HTTPException(status_code=422, detail='Maintenance hour must be 0 through 23 UTC')
            row.maintenance_hour_utc = hour
        row.updated_at = datetime.utcnow()
        self.db.add(AuditLog(actor_id=actor_id, action='deployment.update_settings', target_type='deployment', target_id='local'))
        self.db.commit()
        self.db.refresh(row)
        return row

    def agent_request(self, method: str, path: str, payload: dict | None = None) -> dict:
        if not settings.updater_token:
            raise UpdateAgentUnavailable('Updater token is not configured')
        try:
            transport = httpx.HTTPTransport(uds=settings.updater_socket_path)
            with httpx.Client(transport=transport, base_url='http://updater', timeout=900) as client:
                response = client.request(method, path, json=payload, headers={'X-Updater-Token': settings.updater_token})
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, OSError, ValueError) as exc:
            raise UpdateAgentUnavailable(str(exc)) from exc

    def run(self, action: str, actor_id: int | None, target_ref: str | None = None) -> dict:
        if action not in {'check', 'apply', 'rollback'}:
            raise ValueError('Unsupported update action')
        configured = self.get_settings()
        payload = {'repository': settings.updater_repository, 'branch': configured.branch}
        if target_ref:
            if not _REF_RE.fullmatch(target_ref) or '..' in target_ref:
                raise HTTPException(status_code=422, detail='Invalid target Git reference')
            payload['target_ref'] = target_ref
        run = DeploymentUpdateRun(requested_by=actor_id, action=action, status='running')
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        try:
            result = self.agent_request('POST', f'/v1/{action}', payload)
            run.status = 'success' if result.get('ok') else 'failed'
            run.from_version = result.get('from_version')
            run.to_version = result.get('to_version')
            run.backup_path = result.get('backup_path')
            run.details = str(result.get('message') or '')[:2048]
            if action == 'check':
                configured.last_checked_at = datetime.utcnow()
        except UpdateAgentUnavailable as exc:
            run.status = 'failed'
            run.details = str(exc)[:2048]
            result = {'ok': False, 'message': str(exc)}
        run.finished_at = datetime.utcnow()
        if actor_id is not None:
            self.db.add(AuditLog(actor_id=actor_id, action=f'deployment.{action}', target_type='deployment', target_id='local'))
        self.db.commit()
        result['run_id'] = run.id
        return result

    def status(self) -> dict:
        configured = self.get_settings()
        try:
            agent = self.agent_request('GET', '/v1/status')
        except UpdateAgentUnavailable as exc:
            agent = {'available': False, 'message': str(exc)}
        latest = self.db.query(DeploymentUpdateRun).order_by(DeploymentUpdateRun.id.desc()).first()
        return {
            'repository': settings.updater_repository,
            'settings': {
                'branch': configured.branch,
                'channel': configured.channel,
                'automatic_updates': configured.automatic_updates,
                'check_interval_minutes': configured.check_interval_minutes,
                'maintenance_hour_utc': configured.maintenance_hour_utc,
                'last_checked_at': configured.last_checked_at,
            },
            'agent': agent,
            'latest_run': None if latest is None else {
                'id': latest.id, 'action': latest.action, 'status': latest.status,
                'from_version': latest.from_version, 'to_version': latest.to_version,
                'details': latest.details, 'started_at': latest.started_at,
                'finished_at': latest.finished_at,
            },
        }
