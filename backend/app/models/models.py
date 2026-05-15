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


class LabGroup(Base):
    __tablename__ = 'lab_groups'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


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
