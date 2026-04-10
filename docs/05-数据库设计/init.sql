-- NESOM MVP 数据库初始化脚本（基线）
-- 生成日期: 2026-04-09
--
-- 说明：
-- 1) 本脚本依据 `docs/05-数据库设计/*.md` 与 `docs/06-详细设计/*/数据库设计.md` 进行基线收敛。
-- 2) 当前脚本只覆盖“字段级定义最明确、且依赖闭环”的核心表，确保可执行。
-- 3) 对于尚未完成统一收敛的表（如 stations/tenants/suppliers、巡检/备件/报表的部分扩展表、集成/运维专用库等），
--    请在数据库评审后补齐并追加到本脚本（或拆分为多个模块化 init 脚本）。

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------
-- 0) Database
-- ------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS nesom
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE nesom;

-- ------------------------------------------------------------
-- 1) 设备监控（device_monitoring）
-- 依赖顺序：device_types -> devices -> device_metrics/device_alerts
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS device_types (
  id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
  type_code VARCHAR(50) NOT NULL,
  type_name VARCHAR(100) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  parent_id VARCHAR(36) NULL,
  category VARCHAR(50) NULL,
  sub_category VARCHAR(50) NULL,
  parameter_template JSON NULL,
  maintenance_template JSON NULL,
  description TEXT NULL,
  icon VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_type_code (type_code),
  INDEX idx_category (category),
  INDEX idx_parent_id (parent_id),
  CONSTRAINT fk_device_types_parent
    FOREIGN KEY (parent_id) REFERENCES device_types(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS devices (
  id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
  station_id VARCHAR(36) NOT NULL,
  device_type_id VARCHAR(36) NOT NULL,
  device_code VARCHAR(50) NOT NULL,
  device_name VARCHAR(100) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'offline',
  area_id VARCHAR(36) NULL,
  manufacturer VARCHAR(100) NULL,
  model VARCHAR(100) NULL,
  serial_number VARCHAR(100) NULL,
  rated_power DECIMAL(10,2) NULL,
  rated_voltage DECIMAL(8,2) NULL,
  rated_current DECIMAL(8,2) NULL,
  parameters JSON NULL,
  installation_date DATE NULL,
  commissioning_date DATE NULL,
  warranty_period INT NULL,
  warranty_expiry DATE NULL,
  health_score INT NULL,
  last_maintenance_date DATE NULL,
  next_maintenance_date DATE NULL,
  location_description TEXT NULL,
  longitude DECIMAL(10,6) NULL,
  latitude DECIMAL(10,6) NULL,
  altitude DECIMAL(8,2) NULL,
  description TEXT NULL,
  images JSON NULL,
  documents JSON NULL,
  qr_code VARCHAR(255) NULL,
  responsible_person_id VARCHAR(36) NULL,
  responsible_person_name VARCHAR(100) NULL,
  last_heartbeat DATETIME NULL,
  data_collection_status VARCHAR(20) NOT NULL DEFAULT 'disabled',
  data_collection_config JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_station_device_code (station_id, device_code),
  INDEX idx_status (status),
  INDEX idx_device_type (device_type_id),
  INDEX idx_station (station_id),
  INDEX idx_station_status (station_id, status),
  INDEX idx_manufacturer (manufacturer),
  CONSTRAINT fk_devices_device_type
    FOREIGN KEY (device_type_id) REFERENCES device_types(id) ON DELETE RESTRICT
  -- NOTE: station_id 外键依赖 stations(id)，当前未在基线中统一定义，暂不加外键
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS device_metrics (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  device_id VARCHAR(36) NOT NULL,
  metric_type VARCHAR(50) NOT NULL,
  metric_value DECIMAL(12,4) NOT NULL,
  metric_unit VARCHAR(20) NOT NULL,
  quality TINYINT DEFAULT 100,
  collected_at DATETIME(3) NOT NULL,
  received_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  source VARCHAR(50) DEFAULT 'direct',
  tags JSON NULL,
  INDEX idx_device_collected (device_id, collected_at DESC),
  INDEX idx_collected_at (collected_at),
  INDEX idx_metric_type (metric_type),
  CONSTRAINT fk_device_metrics_device
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS device_alerts (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  device_id VARCHAR(36) NOT NULL,
  alert_code VARCHAR(50) NOT NULL,
  alert_type VARCHAR(50) NOT NULL,
  alert_level ENUM('info','warning','error','critical') NOT NULL,
  alert_title VARCHAR(200) NOT NULL,
  alert_message TEXT NOT NULL,
  alert_data JSON NULL,
  trigger_value DECIMAL(12,4) NULL,
  threshold_value DECIMAL(12,4) NULL,
  start_time DATETIME(3) NOT NULL,
  end_time DATETIME(3) NULL,
  acknowledged_at DATETIME NULL,
  acknowledged_by VARCHAR(36) NULL,
  acknowledged_by_name VARCHAR(100) NULL,
  resolved_at DATETIME NULL,
  resolved_by VARCHAR(36) NULL,
  resolved_by_name VARCHAR(100) NULL,
  resolution_notes TEXT NULL,
  status ENUM('active','acknowledged','resolved','closed') NOT NULL DEFAULT 'active',
  related_work_order_id VARCHAR(36) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_alert_code (alert_code),
  INDEX idx_device_status (device_id, status),
  INDEX idx_alert_level (alert_level),
  INDEX idx_start_time (start_time DESC),
  CONSTRAINT fk_device_alerts_device
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 2) 用户权限（auth / RBAC）
-- 依赖顺序：users/roles/permissions -> user_roles/role_permissions
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
  id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  phone VARCHAR(20) UNIQUE NULL,
  password_hash VARCHAR(255) NOT NULL,
  real_name VARCHAR(50) NOT NULL,
  avatar VARCHAR(255) NULL,
  department_id VARCHAR(36) NULL,
  position VARCHAR(50) NULL,
  employee_id VARCHAR(50) UNIQUE NULL,
  status ENUM('active','inactive','locked','pending') NOT NULL DEFAULT 'active',
  is_superadmin BOOLEAN NOT NULL DEFAULT FALSE,
  last_login_at DATETIME NULL,
  last_login_ip VARCHAR(45) NULL,
  last_password_change DATETIME NULL,
  password_expires_at DATETIME NULL,
  failed_login_attempts INT NOT NULL DEFAULT 0,
  lockout_until DATETIME NULL,
  mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  mfa_secret VARCHAR(255) NULL,
  mfa_backup_codes JSON NULL,
  timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Shanghai',
  locale VARCHAR(10) NOT NULL DEFAULT 'zh-CN',
  theme VARCHAR(20) NOT NULL DEFAULT 'light',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at DATETIME NULL,
  INDEX idx_status (status),
  INDEX idx_department (department_id),
  INDEX idx_username_status (username, status)
  -- NOTE: department_id 外键依赖 departments(id)，当前未在基线中统一定义，暂不加外键
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS roles (
  id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
  role_code VARCHAR(50) UNIQUE NOT NULL,
  role_name VARCHAR(100) NOT NULL,
  description TEXT NULL,
  role_type ENUM('system','custom','department') NOT NULL DEFAULT 'custom',
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  is_protected BOOLEAN NOT NULL DEFAULT FALSE,
  max_users INT NULL,
  priority INT NOT NULL DEFAULT 0,
  data_scope ENUM('all','department','self','custom') NOT NULL DEFAULT 'self',
  scope_expression JSON NULL,
  created_by VARCHAR(36) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_role_type (role_type),
  INDEX idx_is_default (is_default),
  INDEX idx_priority (priority DESC)
  -- NOTE: created_by 外键依赖 users(id)，可在评审后补齐
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS permissions (
  id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
  perm_code VARCHAR(100) UNIQUE NOT NULL,
  perm_name VARCHAR(100) NOT NULL,
  module VARCHAR(50) NOT NULL,
  resource VARCHAR(50) NOT NULL,
  action ENUM('create','read','update','delete','execute','manage') NOT NULL DEFAULT 'read',
  description TEXT NULL,
  is_system BOOLEAN NOT NULL DEFAULT FALSE,
  depends_on JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_module_resource_action (module, resource, action),
  INDEX idx_module_resource (module, resource)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_roles (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id VARCHAR(36) NOT NULL,
  role_id VARCHAR(36) NOT NULL,
  assigned_by VARCHAR(36) NULL,
  assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  notes TEXT NULL,
  UNIQUE KEY uk_user_role (user_id, role_id),
  INDEX idx_user_id (user_id),
  INDEX idx_role_id (role_id),
  INDEX idx_expires_at (expires_at),
  CONSTRAINT fk_user_roles_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_user_roles_role
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
  CONSTRAINT fk_user_roles_assigned_by
    FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS role_permissions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  role_id VARCHAR(36) NOT NULL,
  permission_id VARCHAR(36) NOT NULL,
  granted_by VARCHAR(36) NULL,
  granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_deny BOOLEAN NOT NULL DEFAULT FALSE,
  `condition` JSON NULL,
  UNIQUE KEY uk_role_permission (role_id, permission_id),
  INDEX idx_role_id (role_id),
  INDEX idx_permission_id (permission_id),
  CONSTRAINT fk_role_permissions_role
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
  CONSTRAINT fk_role_permissions_permission
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
  CONSTRAINT fk_role_permissions_granted_by
    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 3) 工单管理（workorder）
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS work_orders (
  id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
  work_order_no VARCHAR(50) UNIQUE NOT NULL,
  work_order_type ENUM('repair','inspection','maintenance','fault','other') NOT NULL DEFAULT 'repair',
  title VARCHAR(200) NOT NULL,
  description TEXT NOT NULL,
  status ENUM('draft','pending','assigned','in_progress','pending_review','completed','closed','cancelled') NOT NULL DEFAULT 'draft',
  priority ENUM('low','medium','high','emergency') NOT NULL DEFAULT 'medium',
  emergency_level ENUM('normal','urgent','critical') NOT NULL DEFAULT 'normal',
  station_id VARCHAR(36) NOT NULL,
  device_id VARCHAR(36) NULL,
  device_name VARCHAR(100) NULL,
  device_code VARCHAR(50) NULL,
  reported_by VARCHAR(36) NOT NULL,
  reported_by_name VARCHAR(100) NOT NULL,
  reported_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  assigned_to VARCHAR(36) NULL,
  assigned_to_name VARCHAR(100) NULL,
  assigned_at DATETIME NULL,
  scheduled_start DATETIME NULL,
  scheduled_end DATETIME NULL,
  actual_start DATETIME NULL,
  actual_end DATETIME NULL,
  estimated_duration INT NULL,
  actual_duration INT NULL,
  completion_rate INT DEFAULT 0,
  cost_estimate DECIMAL(12,2) NULL,
  actual_cost DECIMAL(12,2) NULL,
  location VARCHAR(255) NULL,
  longitude DECIMAL(10,6) NULL,
  latitude DECIMAL(10,6) NULL,
  qr_code VARCHAR(255) NULL,
  images JSON NULL,
  attachments JSON NULL,
  tags JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  closed_at DATETIME NULL,
  closed_by VARCHAR(36) NULL,
  archived_at DATETIME NULL,
  INDEX idx_status (status),
  INDEX idx_priority (priority),
  INDEX idx_type (work_order_type),
  INDEX idx_station_status (station_id, status),
  INDEX idx_assigned_status (assigned_to, status),
  INDEX idx_reported_at (reported_at DESC),
  INDEX idx_scheduled_end (scheduled_end),
  CONSTRAINT fk_work_orders_device
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE SET NULL,
  CONSTRAINT fk_work_orders_reported_by
    FOREIGN KEY (reported_by) REFERENCES users(id) ON DELETE RESTRICT,
  CONSTRAINT fk_work_orders_assigned_to
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
  -- NOTE: station_id 外键依赖 stations(id)，当前未在基线中统一定义，暂不加外键
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 4) 系统配置（system_config）
-- 注意：该模块详细设计使用 tenant_id、多套命名（created_time/updated_time）。
-- 为保证可执行，本脚本按该模块原设计建表（sys_*）。
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS sys_config (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  tenant_id VARCHAR(32) NOT NULL,
  config_key VARCHAR(100) NOT NULL,
  config_value TEXT NULL,
  config_type VARCHAR(20) NOT NULL DEFAULT 'STRING',
  module VARCHAR(50) NOT NULL DEFAULT 'SYSTEM',
  description VARCHAR(500) NULL,
  is_sensitive TINYINT NOT NULL DEFAULT 0,
  is_system TINYINT NOT NULL DEFAULT 0,
  version INT NOT NULL DEFAULT 1,
  created_by VARCHAR(32) NOT NULL,
  created_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_by VARCHAR(32) NULL,
  updated_time DATETIME NULL,
  UNIQUE KEY uniq_tenant_config (tenant_id, config_key),
  INDEX idx_module (module),
  INDEX idx_created_time (created_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sys_dict (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  tenant_id VARCHAR(32) NOT NULL,
  dict_type VARCHAR(50) NOT NULL,
  dict_code VARCHAR(50) NOT NULL,
  dict_name VARCHAR(100) NOT NULL,
  dict_value VARCHAR(500) NULL,
  sort_order INT NOT NULL DEFAULT 0,
  parent_id BIGINT NULL,
  is_system TINYINT NOT NULL DEFAULT 0,
  status TINYINT NOT NULL DEFAULT 1,
  remark VARCHAR(500) NULL,
  created_by VARCHAR(32) NOT NULL,
  created_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_tenant_dict (tenant_id, dict_type, dict_code),
  INDEX idx_parent_id (parent_id),
  INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sys_approval_flow (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  tenant_id VARCHAR(32) NOT NULL,
  flow_code VARCHAR(50) NOT NULL,
  flow_name VARCHAR(100) NOT NULL,
  business_type VARCHAR(50) NOT NULL,
  flow_version INT NOT NULL DEFAULT 1,
  flow_config JSON NOT NULL,
  is_active TINYINT NOT NULL DEFAULT 1,
  start_time DATETIME NULL,
  end_time DATETIME NULL,
  created_by VARCHAR(32) NOT NULL,
  created_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_tenant_flow (tenant_id, flow_code, flow_version),
  INDEX idx_business_type (business_type),
  INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sys_notice_template (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  tenant_id VARCHAR(32) NOT NULL,
  template_code VARCHAR(50) NOT NULL,
  template_name VARCHAR(100) NOT NULL,
  notice_type VARCHAR(20) NOT NULL,
  title_template VARCHAR(500) NULL,
  content_template TEXT NOT NULL,
  variables JSON NULL,
  is_html TINYINT NOT NULL DEFAULT 0,
  status TINYINT NOT NULL DEFAULT 1,
  created_by VARCHAR(32) NOT NULL,
  created_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_tenant_template (tenant_id, template_code),
  INDEX idx_notice_type (notice_type),
  INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sys_log_config (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  tenant_id VARCHAR(32) NOT NULL,
  module VARCHAR(50) NOT NULL,
  log_level VARCHAR(10) NOT NULL DEFAULT 'INFO',
  retention_days INT NOT NULL DEFAULT 30,
  storage_type VARCHAR(20) NOT NULL DEFAULT 'LOCAL',
  config_json JSON NULL,
  is_enabled TINYINT NOT NULL DEFAULT 1,
  created_by VARCHAR(32) NOT NULL,
  created_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_tenant_module (tenant_id, module),
  INDEX idx_log_level (log_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sys_audit_log (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  tenant_id VARCHAR(32) NOT NULL,
  user_id VARCHAR(32) NOT NULL,
  username VARCHAR(100) NOT NULL,
  operation VARCHAR(50) NOT NULL,
  module VARCHAR(50) NOT NULL,
  table_name VARCHAR(50) NULL,
  record_id VARCHAR(100) NULL,
  old_value JSON NULL,
  new_value JSON NULL,
  ip_address VARCHAR(50) NULL,
  user_agent VARCHAR(500) NULL,
  operation_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status TINYINT NOT NULL DEFAULT 1,
  error_message TEXT NULL,
  INDEX idx_tenant_user (tenant_id, user_id),
  INDEX idx_operation_time (operation_time),
  INDEX idx_module_operation (module, operation)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 5) 初始化数据（可选：仅保留最小示例）
-- ------------------------------------------------------------

INSERT INTO sys_config (tenant_id, config_key, config_value, config_type, module, description, created_by)
VALUES
  ('default', 'system.name', 'NESOM运维管理系统', 'STRING', 'SYSTEM', '系统名称', 'system'),
  ('default', 'system.version', '1.0.0', 'STRING', 'SYSTEM', '系统版本', 'system'),
  ('default', 'system.locale', 'zh-CN', 'STRING', 'SYSTEM', '默认语言区域', 'system')
ON DUPLICATE KEY UPDATE
  config_value = VALUES(config_value),
  updated_by = VALUES(created_by),
  updated_time = CURRENT_TIMESTAMP;

INSERT INTO sys_dict (tenant_id, dict_type, dict_code, dict_name, dict_value, sort_order, is_system, status, remark, created_by)
VALUES
  ('default', 'gender', 'MALE', '男', '1', 1, 1, 1, NULL, 'system'),
  ('default', 'gender', 'FEMALE', '女', '2', 2, 1, 1, NULL, 'system'),
  ('default', 'status', 'ENABLED', '启用', '1', 1, 1, 1, NULL, 'system'),
  ('default', 'status', 'DISABLED', '禁用', '0', 2, 1, 1, NULL, 'system')
ON DUPLICATE KEY UPDATE
  dict_name = VALUES(dict_name),
  dict_value = VALUES(dict_value),
  sort_order = VALUES(sort_order),
  status = VALUES(status);

SET FOREIGN_KEY_CHECKS = 1;

-- ------------------------------------------------------------
-- Refresh tokens table (required by auth module)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS refresh_tokens (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  token_hash VARCHAR(255) UNIQUE NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  expires_at DATETIME NOT NULL,
  revoked BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_token_hash (token_hash),
  INDEX idx_user_id (user_id),
  CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Seed data: admin user + admin role
-- Password: admin123 (bcrypt hash)
-- ------------------------------------------------------------
INSERT INTO roles (id, role_code, role_name, description, role_type, is_protected, is_default, data_scope)
VALUES ('00000000-0000-0000-0000-000000000001', 'ROLE_ADMIN', '系统管理员', '系统管理员角色', 'system', TRUE, FALSE, 'all')
ON DUPLICATE KEY UPDATE role_name=role_name;

INSERT INTO users (id, username, email, real_name, password_hash, status, is_superadmin)
VALUES ('00000000-0000-0000-0000-000000000010', 'admin', 'admin@nesom.com', '系统管理员',
        '$2b$12$LJ3m4ys3Gz8y3v5FGqKfxOcBAHGHDYKJGnZ0xMbKqpR6Y.2K1W9Gu', 'active', TRUE)
ON DUPLICATE KEY UPDATE username=username;

INSERT INTO user_roles (user_id, role_id)
VALUES ('00000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000001')
ON DUPLICATE KEY UPDATE user_id=user_id;

