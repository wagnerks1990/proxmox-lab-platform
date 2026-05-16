from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base


class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    role = relationship('Role')


class VMTemplate(Base):
    __tablename__ = 'vm_templates'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    proxmox_node = Column(String(50), nullable=False)
    source_vmid = Column(Integer, nullable=False)
    enabled = Column(Boolean, default=True)


class Permission(Base):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    template_id = Column(Integer, ForeignKey('vm_templates.id'), nullable=False)


class StudentVM(Base):
    __tablename__ = 'student_vms'
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    template_id = Column(Integer, ForeignKey('vm_templates.id'), nullable=False)
    vm_name = Column(String(100), nullable=False)
    vmid = Column(Integer, nullable=False)
    proxmox_node = Column(String(50), nullable=False)
    status = Column(String(20), default='provisioning')
    operating_system = Column(String(50), nullable=True)
    access_protocols = Column(String(255), nullable=True)
    ssh_enabled = Column(Boolean, default=True)
    rdp_enabled = Column(Boolean, default=False)
    spice_enabled = Column(Boolean, default=False)
    console_enabled = Column(Boolean, default=True)
    default_username = Column(String(100), nullable=True)
    assigned_ip = Column(String(64), nullable=True)
    hostname = Column(String(255), nullable=True)
    ssh_username = Column(String(100), nullable=True)
    ssh_auth_method = Column(String(50), nullable=True)
    ssh_port = Column(Integer, default=22)
    created_at = Column(DateTime, server_default=func.now())


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class ConnectionLaunch(Base):
    __tablename__ = 'connection_launches'
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    vm_id = Column(Integer, ForeignKey('student_vms.id'), nullable=False)
    protocol = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default='success')
    details = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class VMSession(Base):
    __tablename__ = 'vm_sessions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    vm_id = Column(Integer, ForeignKey('student_vms.id'), nullable=False)
    pool_id = Column(Integer, nullable=True)
    connection_launch_id = Column(Integer, ForeignKey('connection_launches.id'), nullable=True)
    protocol = Column(String(50), nullable=False)
    state = Column(String(32), nullable=False)
    node = Column(String(50), nullable=True)
    proxmox_vmid = Column(Integer, nullable=True)
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    launched_at = Column(DateTime, nullable=True)
    disconnected_at = Column(DateTime, nullable=True)
    expired_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    last_heartbeat_at = Column(DateTime, nullable=True)
    failure_reason = Column(String(255), nullable=True)
    client_ip = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    request_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)


class TelemetryEvent(Base):
    __tablename__ = 'telemetry_events'
    id = Column(Integer, primary_key=True)
    event_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default='info', index=True)
    source = Column(String(64), nullable=False)
    user_id = Column(Integer, nullable=True, index=True)
    vm_id = Column(Integer, nullable=True, index=True)
    session_id = Column(Integer, nullable=True, index=True)
    request_id = Column(String(100), nullable=True, index=True)
    metadata_json = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)


class DesktopPool(Base):
    __tablename__ = 'desktop_pools'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    pool_type = Column(String(32), nullable=False, index=True)
    template_vmid = Column(Integer, nullable=True)
    template_node = Column(String(50), nullable=True)
    default_protocol = Column(String(50), nullable=False)
    target_node = Column(String(50), nullable=True)
    storage = Column(String(100), nullable=True)
    bridge = Column(String(100), nullable=True)
    vlan_tag = Column(Integer, nullable=True)
    vmid_start = Column(Integer, nullable=True)
    vmid_end = Column(Integer, nullable=True)
    naming_pattern = Column(String(100), nullable=True)
    desired_size = Column(Integer, nullable=False, default=0)
    maintenance_mode = Column(Boolean, nullable=False, default=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)


class WorkerRun(Base):
    __tablename__ = 'worker_runs'
    id = Column(Integer, primary_key=True)
    worker_name = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)
    started_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    finished_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    summary_json = Column(String, nullable=True)
    error = Column(String(255), nullable=True)
    request_id = Column(String(100), nullable=True)
