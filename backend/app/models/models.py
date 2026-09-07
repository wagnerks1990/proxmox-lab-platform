from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base


class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)


class Organization(Base):
    __tablename__ = 'organizations'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(80), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)


class OrganizationMembership(Base):
    __tablename__ = 'organization_memberships'
    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='uq_organization_membership_user'),
    )
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    role = Column(String(32), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)

    organization = relationship('Organization', foreign_keys=[organization_id])
    user = relationship('User', foreign_keys=[user_id])


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    display_name = Column(String(120), nullable=True)
    is_active = Column(Boolean, default=True)
    force_password_change = Column(Boolean, default=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    role = Column(String(50), nullable=True)  # deprecated: compatibility only

    role_rel = relationship('Role', foreign_keys=[role_id])


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


class ProxmoxCluster(Base):
    __tablename__ = 'proxmox_clusters'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    api_url = Column(String(255), nullable=False)
    verify_ssl = Column(Boolean, nullable=False, default=True)
    auth_mode = Column(String(32), nullable=False, default='token')
    root_username = Column(String(120), nullable=True)
    token_user = Column(String(120), nullable=True)
    token_id = Column(String(120), nullable=True)
    encrypted_token_secret = Column(String, nullable=True)
    token_created_by_app = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=False)
    last_validated_at = Column(DateTime, nullable=True)
    last_validation_status = Column(String(32), nullable=True)
    last_validation_error = Column(String(512), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)


class ProxmoxNode(Base):
    __tablename__ = 'proxmox_nodes'
    id = Column(Integer, primary_key=True)
    cluster_id = Column(Integer, ForeignKey('proxmox_clusters.id'), nullable=False, index=True)
    node_name = Column(String(120), nullable=False)
    status = Column(String(32), nullable=True)
    cpu_total = Column(Integer, nullable=True)
    cpu_used = Column(Integer, nullable=True)
    memory_total = Column(Integer, nullable=True)
    memory_used = Column(Integer, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    raw_summary_json = Column(String, nullable=True)


class ProxmoxClusterDefault(Base):
    __tablename__ = 'proxmox_cluster_defaults'
    id = Column(Integer, primary_key=True)
    cluster_id = Column(Integer, ForeignKey('proxmox_clusters.id'), nullable=False, unique=True, index=True)
    default_node = Column(String(120), nullable=True)
    default_storage = Column(String(120), nullable=True)
    default_bridge = Column(String(120), nullable=True)
    default_template_vmid = Column(Integer, nullable=True)
    clone_mode = Column(String(50), nullable=True)
    placement_policy = Column(String(50), nullable=True)
    notes = Column(String(500), nullable=True)


class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)


class GroupMembership(Base):
    __tablename__ = 'group_memberships'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    role_in_group = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class GroupTemplatePermission(Base):
    __tablename__ = 'group_template_permissions'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey('vm_templates.id'), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class AssetCatalog(Base):
    __tablename__ = 'asset_catalog'
    id = Column(Integer, primary_key=True)
    asset_type = Column(String(32), nullable=False, index=True)  # iso|ct_template|vm_template
    name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=True)
    storage_id = Column(String(120), nullable=True)
    content_type = Column(String(32), nullable=True)  # iso|vztmpl
    source_node = Column(String(120), nullable=True)
    source_vmid = Column(Integer, nullable=True)
    source_url = Column(String(1024), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    sha256 = Column(String(128), nullable=True)
    is_required = Column(Boolean, nullable=False, default=True)
    sync_method = Column(String(64), nullable=False, default='download-url')
    metadata_json = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)


class AssetNodeState(Base):
    __tablename__ = 'asset_node_state'
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey('asset_catalog.id'), nullable=False, index=True)
    node_name = Column(String(120), nullable=False, index=True)
    state = Column(String(32), nullable=False, default='missing', index=True)
    target_vmid = Column(Integer, nullable=True)
    target_volid = Column(String(255), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    sha256 = Column(String(128), nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    last_error = Column(String(1024), nullable=True)
    metadata_json = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)


class AssetSyncJob(Base):
    __tablename__ = 'asset_sync_jobs'
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey('asset_catalog.id'), nullable=True, index=True)
    target_node = Column(String(120), nullable=False, index=True)
    state = Column(String(32), nullable=False, default='queued', index=True)
    method = Column(String(64), nullable=False)
    source_node = Column(String(120), nullable=True)
    source_vmid = Column(Integer, nullable=True)
    target_vmid = Column(Integer, nullable=True)
    proxmox_upid = Column(String(255), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error = Column(String(2048), nullable=True)
    metadata_json = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class AssetSyncJobEvent(Base):
    __tablename__ = 'asset_sync_job_events'
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('asset_sync_jobs.id'), nullable=False, index=True)
    level = Column(String(16), nullable=False, default='info')
    message = Column(String(2048), nullable=False)
    metadata_json = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Class(Base):
    __tablename__ = 'classes'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    term = Column(String(120), nullable=True)
    instructor_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    join_code = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)


class Enrollment(Base):
    __tablename__ = 'enrollments'
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    role = Column(String(32), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Lab(Base):
    __tablename__ = 'labs'
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(String(255), nullable=True)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    default_pool_id = Column(Integer, ForeignKey('desktop_pools.id'), nullable=False, index=True)
    student_can_reset = Column(Boolean, nullable=False, default=False)
    student_can_power_off = Column(Boolean, nullable=False, default=False)
    terminal_enabled = Column(Boolean, nullable=False, default=False)
    console_enabled = Column(Boolean, nullable=False, default=False)
    rdp_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)


class ProxmoxHostAccess(Base):
    __tablename__ = 'proxmox_host_access'
    id = Column(Integer, primary_key=True)
    cluster_id = Column(Integer, ForeignKey('proxmox_clusters.id'), nullable=False, index=True)
    node_name = Column(String(120), nullable=False, index=True)
    runner_user = Column(String(120), nullable=False, default='proxmox-lab-runner')
    auth_method = Column(String(32), nullable=False, default='ssh_key')
    encrypted_private_key = Column(String, nullable=True)
    key_ref = Column(String(255), nullable=True)
    public_key_fingerprint = Column(String(255), nullable=True)
    capabilities_json = Column(String, nullable=True)
    status = Column(String(32), nullable=False, default='api_only')
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), nullable=False)
