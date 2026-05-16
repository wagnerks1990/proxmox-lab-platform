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
    operating_system = Column(String(50), nullable=True)
    default_protocol = Column(String(255), nullable=True)
    default_protocols = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    cluster_id = Column(Integer, ForeignKey('proxmox_clusters.id'), nullable=True)
    node_id = Column(Integer, ForeignKey('proxmox_nodes.id'), nullable=True)
    storage_pool = Column(String(100), nullable=True)
    network_bridge = Column(String(100), nullable=True)
    spice_enabled = Column(Boolean, default=False)
    rdp_enabled = Column(Boolean, default=False)
    web_terminal_enabled = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
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


class VMConsoleConnection(Base):
    __tablename__ = 'vm_console_connections'
    id = Column(Integer, primary_key=True)
    vm_id = Column(Integer, ForeignKey('student_vms.id'), nullable=False, unique=True)
    proxmox_vmid = Column(Integer, nullable=False)
    node = Column(String(100), nullable=True)
    protocol = Column(String(20), nullable=False)
    guacamole_connection_id = Column(String(100), nullable=False)
    guacamole_connection_name = Column(String(255), nullable=False)
    hostname = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username_mode = Column(String(50), nullable=True)
    credential_source = Column(String(50), nullable=True)
    last_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ConnectionLaunch(Base):
    __tablename__ = 'connection_launches'
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    vm_id = Column(Integer, ForeignKey('student_vms.id'), nullable=False)
    protocol = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default='success')
    details = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class VMPool(Base):
    __tablename__ = 'vm_pools'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    enabled = Column(Boolean, default=True)
    default_template_id = Column(Integer, ForeignKey('vm_templates.id'), nullable=True)
    max_vms = Column(Integer, default=20)
    max_running_vms = Column(Integer, default=10)
    auto_start = Column(Boolean, default=True)
    recycle_on_logout = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    cluster_id = Column(Integer, ForeignKey('proxmox_clusters.id'), nullable=True)
    node_id = Column(Integer, ForeignKey('proxmox_nodes.id'), nullable=True)
    storage_pool = Column(String(100), nullable=True)
    network_bridge = Column(String(100), nullable=True)
    placement_strategy = Column(String(50), nullable=True)
    preferred_node_id = Column(Integer, ForeignKey('proxmox_nodes.id'), nullable=True)
    resource_pool_id = Column(Integer, ForeignKey('vm_pools.id'), nullable=True)
    cpu_limit = Column(String(50), nullable=True)
    memory_limit_mb = Column(Integer, nullable=True)
    allowed_roles = Column(String(255), nullable=True)


class LabGroup(Base):
    __tablename__ = 'lab_groups'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    cluster_id = Column(Integer, ForeignKey('proxmox_clusters.id'), nullable=True)
    node_id = Column(Integer, ForeignKey('proxmox_nodes.id'), nullable=True)
    storage_pool = Column(String(100), nullable=True)
    network_bridge = Column(String(100), nullable=True)
    placement_strategy = Column(String(50), nullable=True)
    preferred_node_id = Column(Integer, ForeignKey('proxmox_nodes.id'), nullable=True)
    resource_pool_id = Column(Integer, ForeignKey('vm_pools.id'), nullable=True)
    cpu_limit = Column(String(50), nullable=True)
    memory_limit_mb = Column(Integer, nullable=True)
    allowed_roles = Column(String(255), nullable=True)


class LabGroupMember(Base):
    __tablename__ = 'lab_group_members'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('lab_groups.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class ProtocolSettings(Base):
    __tablename__ = 'protocol_settings'
    id = Column(Integer, primary_key=True)
    terminal_gateway_url = Column(String(255), nullable=True)
    enable_web_terminal = Column(Boolean, default=True)
    enable_rdp = Column(Boolean, default=True)
    enable_spice = Column(Boolean, default=True)
    enable_novnc = Column(Boolean, default=True)
    default_ssh_port = Column(Integer, default=22)
    updated_at = Column(DateTime, server_default=func.now())


class ProxmoxCluster(Base):
    __tablename__ = 'proxmox_clusters'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    api_url = Column(String(255), nullable=False)
    enabled = Column(Boolean, default=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class ProxmoxNode(Base):
    __tablename__ = 'proxmox_nodes'
    id = Column(Integer, primary_key=True)
    cluster_id = Column(Integer, ForeignKey('proxmox_clusters.id'), nullable=False)
    node_name = Column(String(100), nullable=False)
    management_ip = Column(String(64), nullable=True)
    enabled = Column(Boolean, default=True)
    status = Column(String(20), nullable=True)
    last_seen = Column(DateTime, nullable=True)
    cpu_usage = Column(String(50), nullable=True)
    memory_usage = Column(String(50), nullable=True)
    storage_summary = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class UserGroup(Base):
    __tablename__ = 'user_groups'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UserGroupMember(Base):
    __tablename__ = 'user_group_members'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('user_groups.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default='success')
    message = Column(String(255), nullable=True)
    details_json = Column(String(4000), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class DesktopPool(Base):
    __tablename__ = 'desktop_pools'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    pool_type = Column(String(20), default='lab')
    template_id = Column(Integer, ForeignKey('vm_templates.id'), nullable=True)
    resource_pool_id = Column(Integer, ForeignKey('vm_pools.id'), nullable=True)
    cpu_limit = Column(String(50), nullable=True)
    memory_limit_mb = Column(Integer, nullable=True)
    allowed_roles = Column(String(255), nullable=True)
    cluster_id = Column(Integer, ForeignKey('proxmox_clusters.id'), nullable=True)
    node_id = Column(Integer, ForeignKey('proxmox_nodes.id'), nullable=True)
    storage_pool = Column(String(100), nullable=True)
    network_bridge = Column(String(100), nullable=True)
    min_ready = Column(Integer, default=0)
    max_desktops = Column(Integer, default=20)
    auto_start = Column(Boolean, default=True)
    auto_recycle = Column(Boolean, default=False)
    naming_prefix = Column(String(50), nullable=True)
    assignment_mode = Column(String(20), default='manual')
    display_name = Column(String(120), nullable=True)
    is_active = Column(Boolean, default=True)
    force_password_change = Column(Boolean, default=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
