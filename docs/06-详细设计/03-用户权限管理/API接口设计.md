# 用户权限管理模块 - API接口详细设计

**版本**: 1.0  
**日期**: 2026-04-01  
**作者**: 高级项目经理  
**状态**: Draft  
**审核状态**: 待评审  
**继承自**: 概要设计-模块划分设计.md (用户权限管理API部分)  
**实际代码参考**: backend/src/api/v1/auth.py, backend/src/api/v1/users.py, backend/src/api/v1/roles.py  
**数据库模型**: models_generated.py (Users, Roles, Permissions, Departments, AuditLogs等)

## 1. 设计概述

### 1.1 设计目标
提供完整的用户权限管理RESTful API接口，支持：
- 用户身份认证和会话管理（登录、登出、Token刷新）
- 用户全生命周期管理（增删改查、密码管理）
- 基于角色的访问控制（RBAC）管理
- 组织架构和部门管理
- 操作审计和日志查询
- 安全策略配置（密码策略、锁定策略等）

### 1.2 设计原则
1. **RESTful规范**：资源导向，HTTP方法语义明确
2. **版本控制**：API版本前缀 `/api/v1/`
3. **一致性**：统一响应格式、错误处理、分页规范
4. **安全性**：JWT认证，RBAC权限控制，防暴力破解
5. **性能**：高频接口优化，Redis缓存，数据库索引
6. **文档化**：OpenAPI规范，代码即文档

### 1.3 技术约束
- **框架**: FastAPI 0.104+ (Python 3.11+)
- **认证**: JWT (JSON Web Token) + 刷新令牌
- **序列化**: Pydantic v2 模型验证
- **数据库**: SQLAlchemy 2.0 + MySQL 8.0
- **缓存**: Redis 7.0 (会话、权限缓存)
- **加密**: bcrypt (密码), AES-256-GCM (MFA密钥)

## 2. 通用设计规范

### 2.1 请求/响应格式

#### 成功响应格式
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {...},  // 具体数据
  "meta": {       // 分页元数据（列表接口）
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

#### 错误响应格式
```json
{
  "code": 400,
  "message": "请求参数错误",
  "detail": {     // 错误详情
    "field": "username",
    "error": "用户名已存在"
  },
  "timestamp": "2026-04-01T10:30:00Z"
}
```

### 2.2 分页规范
- **参数**: `page` (默认1), `page_size` (默认20, 最大100)
- **响应**: 列表接口包含`data`数组和`meta`分页信息
- **性能**: 使用游标分页优化大数据集（基于时间或ID）

### 2.3 过滤和排序
- **过滤**: `filter[name]=value&filter[status]=active`
- **范围过滤**: `filter[created_at][gte]=2026-01-01&filter[created_at][lte]=2026-12-31`
- **排序**: `sort=created_at.desc,username.asc`
- **字段选择**: `fields=id,username,real_name,status`
- **关联展开**: `expand=department,roles`

### 2.4 认证和授权
- **认证头**: `Authorization: Bearer <access_token>`
- **刷新令牌**: 通过Refresh-Token头或Cookie
- **权限检查**: 基于角色的访问控制 (RBAC)，权限中间件
- **操作审计**: 自动记录操作日志，支持追溯

### 2.5 安全规范
- **防暴力破解**: 登录尝试限制，账户锁定
- **CSRF防护**: SameSite Cookie，关键操作二次验证
- **XSS防护**: 输入输出过滤，Content Security Policy
- **敏感信息**: 密码、令牌等字段在日志中脱敏

## 3. API端点详细设计

### 3.1 认证接口

#### 3.1.1 用户登录
**端点**: `POST /api/v1/auth/login`  
**描述**: 用户使用用户名/密码登录，返回访问令牌和刷新令牌

**请求头**:
- `Content-Type: application/json`

**请求体** (JSON Schema):
```json
{
  "type": "object",
  "required": ["username", "password"],
  "properties": {
    "username": {
      "type": "string",
      "minLength": 3,
      "maxLength": 50,
      "description": "用户名或邮箱"
    },
    "password": {
      "type": "string",
      "minLength": 1,
      "description": "密码"
    },
    "mfa_code": {
      "type": "string",
      "minLength": 6,
      "maxLength": 6,
      "description": "MFA验证码（如已启用MFA）"
    },
    "client_type": {
      "type": "string",
      "enum": ["web", "mobile", "api", "desktop"],
      "default": "web",
      "description": "客户端类型"
    },
    "client_info": {
      "type": "object",
      "description": "客户端信息（用户代理、IP等）"
    }
  }
}
```

**权限要求**: 无（公开接口）

**成功响应** (200):
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 900,  // 15分钟
    "refresh_expires_in": 604800,  // 7天
    "user": {
      "id": "user_001",
      "username": "zhangsan",
      "email": "zhangsan@example.com",
      "real_name": "张三",
      "avatar": "/avatars/user_001.jpg",
      "department_id": "dept_001",
      "department": {
        "id": "dept_001",
        "dept_name": "运维部"
      },
      "is_superadmin": false,
      "mfa_enabled": true,
      "permissions": [
        "device:read",
        "device:update",
        "workorder:create"
      ],
      "roles": [
        "ROLE_OPERATOR",
        "ROLE_DEPARTMENT_MANAGER"
      ]
    },
    "mfa_required": false  // 是否需要MFA验证
  }
}
```

**错误响应**:
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 用户名或密码错误
- `403 Forbidden`: 账户被锁定或未激活
- `429 Too Many Requests`: 登录尝试次数过多
- `423 Locked`: 账户被锁定，需等待解锁时间
- `500 Internal Server Error`: 服务器内部错误

**安全限制**:
1. 同一用户名5分钟内连续失败5次锁定账户30分钟
2. 同一IP地址1小时内失败20次封锁IP24小时
3. 成功登录后清除该用户名的失败记录
4. 记录登录尝试（成功/失败）到login_attempts表

#### 3.1.2 刷新访问令牌
**端点**: `POST /api/v1/auth/refresh`  
**描述**: 使用刷新令牌获取新的访问令牌

**请求头**:
- `Authorization: Bearer <refresh_token>` 或
- `Refresh-Token: <refresh_token>`

**权限要求**: 有效的刷新令牌

**成功响应** (200):
```json
{
  "code": 200,
  "message": "令牌刷新成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", // 可能轮换
    "token_type": "bearer",
    "expires_in": 900,
    "refresh_expires_in": 604800
  }
}
```

**错误响应**:
- `401 Unauthorized`: 刷新令牌无效或过期
- `403 Forbidden`: 刷新令牌已被撤销
- `429 Too Many Requests`: 刷新频率过高

**安全特性**:
1. 刷新令牌轮换机制（每次使用生成新令牌，旧令牌失效）
2. 刷新令牌存储于数据库，可强制撤销
3. 密码修改后所有刷新令牌自动失效

#### 3.1.3 用户登出
**端点**: `POST /api/v1/auth/logout`  
**描述**: 注销当前会话，撤销访问令牌和刷新令牌

**请求头**:
- `Authorization: Bearer <access_token>`

**请求体** (可选):
```json
{
  "type": "object",
  "properties": {
    "revoke_all": {
      "type": "boolean",
      "default": false,
      "description": "是否撤销所有会话"
    }
  }
}
```

**权限要求**: 有效的访问令牌

**成功响应** (200):
```json
{
  "code": 200,
  "message": "登出成功"
}
```

**实现要点**:
1. 将访问令牌加入Redis黑名单（短期）
2. 将刷新令牌标记为撤销状态
3. 如revoke_all=true，则撤销用户所有会话

#### 3.1.4 MFA管理接口

##### 3.1.4.1 初始化MFA
**端点**: `POST /api/v1/auth/mfa/setup`  
**描述**: 为当前用户初始化MFA，返回二维码和备份代码

**请求头**: `Authorization: Bearer <access_token>`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "MFA初始化成功",
  "data": {
    "secret": "JBSWY3DPEHPK3PXP", // 仅首次返回
    "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...",
    "backup_codes": ["ABCD-1234", "EFGH-5678", ...], // 加密存储
    "verification_required": true
  }
}
```

##### 3.1.4.2 验证MFA
**端点**: `POST /api/v1/auth/mfa/verify`  
**描述**: 验证MFA代码，完成MFA启用

**请求体**:
```json
{
  "type": "object",
  "required": ["code"],
  "properties": {
    "code": {
      "type": "string",
      "minLength": 6,
      "maxLength": 6,
      "description": "MFA验证码"
    }
  }
}
```

##### 3.1.4.3 禁用MFA
**端点**: `POST /api/v1/auth/mfa/disable`  
**描述**: 禁用当前用户的MFA功能

**请求体**:
```json
{
  "type": "object",
  "required": ["password"],
  "properties": {
    "password": {
      "type": "string",
      "description": "当前密码（二次验证）"
    }
  }
}
```

### 3.2 用户管理接口

#### 3.2.1 获取当前用户信息
**端点**: `GET /api/v1/users/me`  
**描述**: 获取当前登录用户的详细信息

**请求头**: `Authorization: Bearer <access_token>`

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| expand | string | 否 | 关联数据展开 | `department,roles.permissions` |

**权限要求**: 有效的访问令牌

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "id": "user_001",
    "username": "zhangsan",
    "email": "zhangsan@example.com",
    "phone": "13800138000",
    "real_name": "张三",
    "avatar": "/avatars/user_001.jpg",
    "department_id": "dept_001",
    "department": {
      "id": "dept_001",
      "dept_code": "OPS-001",
      "dept_name": "运维部",
      "dept_type": "department"
    },
    "position": "运维工程师",
    "employee_id": "EMP2024001",
    "status": "active",
    "is_superadmin": false,
    "last_login_at": "2026-04-01T10:25:30Z",
    "last_login_ip": "192.168.1.100",
    "last_password_change": "2026-03-01T09:00:00Z",
    "password_expires_at": "2026-05-30T09:00:00Z",
    "mfa_enabled": true,
    "timezone": "Asia/Shanghai",
    "locale": "zh-CN",
    "theme": "light",
    "roles": [
      {
        "id": "role_001",
        "role_code": "ROLE_OPERATOR",
        "role_name": "操作员",
        "permissions": [
          {"perm_code": "device:read", "perm_name": "查看设备"},
          {"perm_code": "workorder:create", "perm_name": "创建工单"}
        ]
      }
    ],
    "permissions": [
      "device:read",
      "device:update",
      "workorder:create",
      "workorder:read"
    ],
    "created_at": "2026-01-15T09:00:00Z",
    "updated_at": "2026-04-01T10:25:30Z"
  }
}
```

#### 3.2.2 更新当前用户信息
**端点**: `PUT /api/v1/users/me`  
**描述**: 更新当前用户的个人信息

**请求体** (部分字段):
```json
{
  "type": "object",
  "properties": {
    "real_name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 50,
      "description": "真实姓名"
    },
    "avatar": {
      "type": "string",
      "format": "uri",
      "description": "头像URL"
    },
    "phone": {
      "type": "string",
      "pattern": "^\\+?[1-9]\\d{1,14}$",
      "description": "手机号（国际格式）"
    },
    "timezone": {
      "type": "string",
      "description": "时区"
    },
    "locale": {
      "type": "string",
      "enum": ["zh-CN", "en-US"],
      "description": "语言区域"
    },
    "theme": {
      "type": "string",
      "enum": ["light", "dark", "auto"],
      "description": "主题偏好"
    }
  }
}
```

**权限要求**: 有效的访问令牌

**审计日志**: 记录用户信息变更

#### 3.2.3 修改密码
**端点**: `POST /api/v1/users/change-password`  
**描述**: 修改当前用户的密码

**请求体**:
```json
{
  "type": "object",
  "required": ["current_password", "new_password"],
  "properties": {
    "current_password": {
      "type": "string",
      "description": "当前密码"
    },
    "new_password": {
      "type": "string",
      "minLength": 8,
      "description": "新密码"
    },
    "confirm_password": {
      "type": "string",
      "description": "确认新密码"
    }
  }
}
```

**安全规则**:
1. 新密码必须符合密码策略（复杂度、历史密码检查）
2. 修改成功后，所有活跃会话强制登出（可选配置）
3. 记录密码修改审计日志

#### 3.2.4 获取用户列表（管理员）
**端点**: `GET /api/v1/users`  
**描述**: 管理员查询用户列表，支持分页、过滤、排序

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 | 示例 |
|--------|------|------|------|------|
| page | int | 否 | 页码，默认1 | `1` |
| page_size | int | 否 | 每页数量，默认20，最大100 | `20` |
| filter | object | 否 | 过滤条件 | `{"status": "active", "department_id": "dept_001"}` |
| sort | string | 否 | 排序字段 | `created_at.desc,username.asc` |
| fields | string | 否 | 返回字段，逗号分隔 | `id,username,real_name,status` |
| expand | string | 否 | 关联数据展开 | `department,roles` |
| search | string | 否 | 搜索（用户名、姓名、邮箱） | `张三` |

**权限要求**:
- 角色: `admin` 或 `user:read` 权限

**数据权限**:
- 超级管理员: 查看所有用户
- 部门管理员: 查看本部门及下级部门用户
- 普通管理员: 查看分配权限的用户

#### 3.2.5 创建用户（管理员）
**端点**: `POST /api/v1/users`  
**描述**: 管理员创建新用户

**请求体** (必需字段):
```json
{
  "type": "object",
  "required": ["username", "email", "real_name"],
  "properties": {
    "username": {
      "type": "string",
      "minLength": 3,
      "maxLength": 50,
      "pattern": "^[a-zA-Z0-9_]+$",
      "description": "用户名"
    },
    "email": {
      "type": "string",
      "format": "email",
      "description": "邮箱"
    },
    "real_name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 50,
      "description": "真实姓名"
    },
    "password": {
      "type": "string",
      "minLength": 8,
      "description": "初始密码（如为空则发送激活邮件）"
    },
    "department_id": {
      "type": "string",
      "format": "uuid",
      "description": "所属部门ID"
    },
    "position": {
      "type": "string",
      "maxLength": 50,
      "description": "职位"
    },
    "employee_id": {
      "type": "string",
      "maxLength": 50,
      "description": "员工工号"
    },
    "role_ids": {
      "type": "array",
      "items": {"type": "string", "format": "uuid"},
      "description": "初始角色ID列表"
    },
    "send_welcome_email": {
      "type": "boolean",
      "default": true,
      "description": "是否发送欢迎邮件"
    }
  }
}
```

**权限要求**:
- 角色: `admin` 且 `user:create` 权限

**业务规则**:
1. 用户名、邮箱必须唯一
2. 如不提供密码，生成随机密码并通过邮件发送
3. 用户初始状态为`pending`（需激活）或`active`
4. 记录用户创建审计日志

#### 3.2.6 更新用户（管理员）
**端点**: `PUT /api/v1/users/{user_id}`  
**描述**: 管理员更新用户信息

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| user_id | string | 是 | 用户ID |

**请求体**: 同创建接口，所有字段可选

**权限要求**:
- 角色: `admin` 且 `user:update` 权限
- 数据权限: 只能更新有管理权限的用户

#### 3.2.7 删除用户（管理员）
**端点**: `DELETE /api/v1/users/{user_id}`  
**描述**: 管理员删除用户（软删除）

**路径参数**: 同上

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| force | boolean | 否 | 是否强制删除（物理删除） | `false` |

**权限要求**:
- 角色: `admin` 且 `user:delete` 权限
- 限制: 不能删除自己，不能删除超级管理员

**业务规则**:
1. 默认软删除（设置deleted_at）
2. 软删除后用户不可登录，但数据保留
3. 强制删除需二次确认，删除所有关联数据
4. 记录删除审计日志

#### 3.2.8 重置用户密码（管理员）
**端点**: `POST /api/v1/users/{user_id}/reset-password`  
**描述**: 管理员重置用户密码

**请求体**:
```json
{
  "type": "object",
  "properties": {
    "new_password": {
      "type": "string",
      "minLength": 8,
      "description": "新密码（如为空则生成随机密码）"
    },
    "send_email": {
      "type": "boolean",
      "default": true,
      "description": "是否发送密码通知邮件"
    },
    "force_logout": {
      "type": "boolean",
      "default": true,
      "description": "是否强制用户所有会话登出"
    }
  }
}
```

**安全规则**:
1. 重置密码后，可选强制用户所有会话登出
2. 发送密码重置通知邮件（如配置）
3. 记录密码重置审计日志

#### 3.2.9 锁定/解锁用户（管理员）
**端点**: `POST /api/v1/users/{user_id}/lock` 和 `POST /api/v1/users/{user_id}/unlock`  
**描述**: 管理员锁定或解锁用户账户

**请求体** (锁定):
```json
{
  "type": "object",
  "properties": {
    "reason": {
      "type": "string",
      "enum": ["manual", "suspicious", "inactive"],
      "default": "manual",
      "description": "锁定原因"
    },
    "duration_minutes": {
      "type": "integer",
      "minimum": 1,
      "maximum": 525600, // 1年
      "default": 1440, // 24小时
      "description": "锁定时长（分钟）"
    },
    "notes": {
      "type": "string",
      "description": "锁定说明"
    }
  }
}
```

**审计日志**: 记录账户锁定/解锁操作

### 3.3 角色管理接口

#### 3.3.1 获取角色列表
**端点**: `GET /api/v1/roles`  
**描述**: 查询角色列表，支持分页、过滤

**权限要求**: `role:read` 权限

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "id": "role_001",
      "role_code": "ROLE_SUPERADMIN",
      "role_name": "超级管理员",
      "description": "系统超级管理员，拥有所有权限",
      "role_type": "system",
      "is_protected": true,
      "is_default": false,
      "data_scope": "all",
      "user_count": 2,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    },
    {
      "id": "role_002",
      "role_code": "ROLE_OPERATOR",
      "role_name": "操作员",
      "description": "设备操作员，可查看和操作设备",
      "role_type": "custom",
      "is_protected": false,
      "is_default": true,
      "data_scope": "department",
      "user_count": 45,
      "created_at": "2026-01-15T09:00:00Z",
      "updated_at": "2026-03-20T14:30:00Z"
    }
  ],
  "meta": {...}
}
```

#### 3.3.2 获取角色详情
**端点**: `GET /api/v1/roles/{role_id}`  
**描述**: 获取角色详细信息，包含权限列表

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| expand | string | 否 | `permissions` 展开权限详情 |

#### 3.3.3 创建角色
**端点**: `POST /api/v1/roles`  
**描述**: 创建新角色

**权限要求**: `role:create` 权限

**请求体**:
```json
{
  "type": "object",
  "required": ["role_code", "role_name"],
  "properties": {
    "role_code": {
      "type": "string",
      "pattern": "^ROLE_[A-Z_]+$",
      "description": "角色编码，大写字母和下划线"
    },
    "role_name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100,
      "description": "角色名称"
    },
    "description": {
      "type": "string",
      "description": "角色描述"
    },
    "role_type": {
      "type": "string",
      "enum": ["system", "custom", "department"],
      "default": "custom",
      "description": "角色类型"
    },
    "is_default": {
      "type": "boolean",
      "default": false,
      "description": "是否默认角色"
    },
    "data_scope": {
      "type": "string",
      "enum": ["all", "department", "self", "custom"],
      "default": "self",
      "description": "数据权限范围"
    },
    "scope_expression": {
      "type": "object",
      "description": "数据权限表达式（data_scope=custom时）"
    },
    "permission_ids": {
      "type": "array",
      "items": {"type": "string", "format": "uuid"},
      "description": "初始权限ID列表"
    }
  }
}
```

#### 3.3.4 更新角色
**端点**: `PUT /api/v1/roles/{role_id}`  
**描述**: 更新角色信息

**限制**: 系统角色（is_protected=true）不可修改

#### 3.3.5 删除角色
**端点**: `DELETE /api/v1/roles/{role_id}`  
**描述**: 删除角色

**限制**:
1. 系统角色不可删除
2. 有关联用户的角色需先解除关联
3. 默认角色不可删除

#### 3.3.6 更新角色权限
**端点**: `PUT /api/v1/roles/{role_id}/permissions`  
**描述**: 批量更新角色权限

**请求体**:
```json
{
  "type": "object",
  "required": ["permission_ids"],
  "properties": {
    "permission_ids": {
      "type": "array",
      "items": {"type": "string", "format": "uuid"},
      "description": "权限ID列表（全量替换）"
    },
    "append": {
      "type": "boolean",
      "default": false,
      "description": "是否为追加模式（默认全量替换）"
    }
  }
}
```

**审计日志**: 记录角色权限变更

### 3.4 权限管理接口

#### 3.4.1 获取权限列表
**端点**: `GET /api/v1/permissions`  
**描述**: 查询系统权限列表，支持按模块、资源过滤

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| module | string | 否 | 按模块过滤 | `device` |
| resource | string | 否 | 按资源过滤 | `monitor` |
| action | string | 否 | 按操作过滤 | `read` |

**权限要求**: `permission:read` 权限

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "id": "perm_001",
      "perm_code": "device:monitor:read",
      "perm_name": "查看设备监控",
      "module": "device",
      "resource": "monitor",
      "action": "read",
      "description": "查看设备监控数据和状态",
      "is_system": true,
      "depends_on": []
    },
    {
      "id": "perm_002",
      "perm_code": "device:monitor:update",
      "perm_name": "更新设备监控",
      "module": "device",
      "resource": "monitor",
      "action": "update",
      "description": "修改设备监控配置",
      "is_system": true,
      "depends_on": ["device:monitor:read"]
    }
  ],
  "meta": {...}
}
```

### 3.5 部门管理接口

#### 3.5.1 获取部门树
**端点**: `GET /api/v1/departments/tree`  
**描述**: 获取完整的部门树形结构

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| root_id | string | 否 | 根部门ID（默认顶级部门） |
| depth | int | 否 | 查询深度，默认3层 |
| include_users | boolean | 否 | 是否包含用户列表 | `false` |

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "id": "dept_001",
    "dept_code": "COMPANY",
    "dept_name": "NESOM公司",
    "dept_type": "company",
    "children": [
      {
        "id": "dept_002",
        "dept_code": "OPS-001",
        "dept_name": "运维部",
        "dept_type": "department",
        "manager_id": "user_001",
        "manager": {
          "id": "user_001",
          "username": "zhangsan",
          "real_name": "张三"
        },
        "user_count": 15,
        "children": [...]
      }
    ]
  }
}
```

#### 3.5.2 获取部门详情
**端点**: `GET /api/v1/departments/{dept_id}`  
**描述**: 获取部门详细信息，包含用户列表

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| page | int | 否 | 用户列表页码 |
| page_size | int | 否 | 用户列表每页数量 |

#### 3.5.3 创建部门
**端点**: `POST /api/v1/departments`  
**描述**: 创建新部门

**权限要求**: `department:create` 权限

**请求体**:
```json
{
  "type": "object",
  "required": ["dept_code", "dept_name"],
  "properties": {
    "dept_code": {
      "type": "string",
      "pattern": "^[A-Z0-9_-]+$",
      "description": "部门编码"
    },
    "dept_name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100,
      "description": "部门名称"
    },
    "parent_id": {
      "type": "string",
      "format": "uuid",
      "description": "父部门ID"
    },
    "dept_type": {
      "type": "string",
      "enum": ["company", "division", "department", "team", "station"],
      "default": "department"
    },
    "manager_id": {
      "type": "string",
      "format": "uuid",
      "description": "部门负责人ID"
    },
    "sort_order": {
      "type": "integer",
      "default": 0,
      "description": "显示顺序"
    }
  }
}
```

#### 3.5.4 更新部门
**端点**: `PUT /api/v1/departments/{dept_id}`  
**描述**: 更新部门信息

**限制**: 不能将部门移动到自己的子部门下

#### 3.5.5 删除部门
**端点**: `DELETE /api/v1/departments/{dept_id}`  
**描述**: 删除部门

**限制**:
1. 有关联用户的部门不能删除（需先转移用户）
2. 有子部门的部门不能删除（需先删除子部门）
3. 根部门不能删除

### 3.6 审计日志接口

#### 3.6.1 查询审计日志
**端点**: `GET /api/v1/audit-logs`  
**描述**: 查询审计日志，支持复杂过滤

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| start_time | datetime | 否 | 开始时间 | `2026-04-01T00:00:00Z` |
| end_time | datetime | 否 | 结束时间 | `2026-04-01T23:59:59Z` |
| user_id | string | 否 | 用户ID过滤 |
| username | string | 否 | 用户名过滤 |
| event_type | string | 否 | 事件类型过滤 |
| resource_type | string | 否 | 资源类型过滤 |
| resource_id | string | 否 | 资源ID过滤 |
| action | string | 否 | 操作类型过滤 |
| status | string | 否 | 状态过滤 | `success` |
| ip_address | string | 否 | IP地址过滤 |
| page, page_size | int | 否 | 分页参数 |

**权限要求**: `audit:read` 权限（敏感操作）

**数据权限**: 普通用户只能查看自己的操作日志

### 3.7 系统配置接口

#### 3.7.1 获取安全配置
**端点**: `GET /api/v1/system/configs/security`  
**描述**: 获取系统安全配置（密码策略、会话策略等）

**权限要求**: `system:config:read` 权限

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "password_policy": {
      "min_length": 8,
      "require_uppercase": true,
      "require_lowercase": true,
      "require_digits": true,
      "require_special_chars": false,
      "max_age_days": 90,
      "history_size": 5,
      "lockout_threshold": 5,
      "lockout_duration_minutes": 30
    },
    "session_policy": {
      "access_token_ttl": 900,
      "refresh_token_ttl": 604800,
      "max_concurrent_sessions": 5,
      "idle_timeout": 1800,
      "absolute_timeout": 86400
    },
    "mfa_policy": {
      "enforced_roles": ["ROLE_ADMIN", "ROLE_OPERATOR"],
      "backup_code_count": 10,
      "recovery_email_required": true
    }
  }
}
```

#### 3.7.2 更新安全配置
**端点**: `PUT /api/v1/system/configs/security`  
**描述**: 更新系统安全配置

**权限要求**: `system:config:update` 权限（超级管理员）

**审计日志**: 记录安全配置变更

## 4. 接口性能优化

### 4.1 缓存策略
1. **权限缓存**: 用户权限列表缓存到Redis，有效期5分钟
2. **会话缓存**: 会话验证使用Redis，避免频繁数据库查询
3. **配置缓存**: 系统配置缓存到Redis，变更时清除
4. **部门树缓存**: 部门树结构缓存10分钟

### 4.2 数据库优化
1. **索引设计**: 高频查询字段建立复合索引
2. **查询优化**: 使用JOIN优化权限查询
3. **分页优化**: 大数据集使用游标分页
4. **分区表**: 审计日志按月分区

### 4.3 并发处理
1. **登录限流**: 基于IP和用户名的令牌桶限流
2. **缓存击穿**: 使用互斥锁防止缓存击穿
3. **数据库连接池**: 合理配置连接池参数
4. **异步处理**: 审计日志异步写入消息队列

## 5. 安全设计

### 5.1 认证安全
1. **JWT安全**: HS256算法，短期有效期，Redis黑名单
2. **刷新令牌**: 加密存储，轮换机制，可撤销
3. **MFA支持**: TOTP，备份代码，恢复机制
4. **防暴力破解**: 登录尝试限制，账户锁定，IP封锁

### 5.2 授权安全
1. **RBAC模型**: 角色-权限-用户三层授权
2. **数据权限**: 基于部门的数据隔离
3. **权限缓存**: 减少权限检查开销
4. **权限验证**: 服务器端强制验证

### 5.3 输入安全
1. **参数验证**: Pydantic严格类型验证
2. **SQL注入防护**: 使用ORM参数化查询
3. **XSS防护**: 输出编码，CSP头
4. **CSRF防护**: SameSite Cookie，关键操作二次验证

### 5.4 审计安全
1. **完整记录**: 所有关键操作记录审计日志
2. **防篡改**: 审计日志加密签名（可选）
3. **隐私保护**: 敏感字段脱敏
4. **合规性**: 日志保留180天（等保2.0）

## 6. 错误码定义

### 6.1 通用错误码
| 错误码 | HTTP状态 | 描述 |
|--------|----------|------|
| 1000 | 400 | 请求参数错误 |
| 1001 | 401 | 未授权访问 |
| 1002 | 403 | 权限不足 |
| 1003 | 404 | 资源不存在 |
| 1004 | 409 | 资源冲突（如用户名已存在） |
| 1005 | 429 | 请求过于频繁 |
| 1006 | 500 | 服务器内部错误 |

### 6.2 认证相关错误码
| 错误码 | HTTP状态 | 描述 |
|--------|----------|------|
| 2001 | 401 | 用户名或密码错误 |
| 2002 | 401 | Token已过期 |
| 2003 | 401 | Token无效 |
| 2004 | 403 | 账户被锁定 |
| 2005 | 403 | 账户未激活 |
| 2006 | 403 | 需要MFA验证 |
| 2007 | 423 | 账户被锁定，需等待解锁 |
| 2008 | 429 | 登录尝试次数过多 |

### 6.3 业务相关错误码
| 错误码 | HTTP状态 | 描述 |
|--------|----------|------|
| 3001 | 403 | 不能删除自己 |
| 3002 | 403 | 不能删除超级管理员 |
| 3003 | 403 | 不能修改系统角色 |
| 3004 | 409 | 用户名已存在 |
| 3005 | 409 | 邮箱已存在 |
| 3006 | 409 | 手机号已存在 |
| 3007 | 409 | 部门编码已存在 |
| 3008 | 409 | 角色编码已存在 |

## 7. API版本管理

### 7.1 版本策略
- **URL版本化**: `/api/v1/` 路径前缀
- **向后兼容**: 新版本不破坏旧版本接口
- **版本弃用**: 提前通知，提供迁移方案
- **版本生命周期**: 每个版本支持至少2年

### 7.2 变更记录
| 版本 | 日期 | 变更描述 |
|------|------|----------|
| v1.0 | 2026-04-01 | 初始版本，基础认证和权限管理 |

## 8. 附录

### 8.1 OpenAPI规范
```yaml
openapi: 3.0.3
info:
  title: NESOM用户权限管理API
  version: 1.0.0
  description: 新能源运维管理系统用户权限管理模块API
servers:
  - url: https://api.nesom.example.com/api/v1
paths:
  /auth/login:
    post:
      summary: 用户登录
      description: 使用用户名密码登录，返回访问令牌
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LoginRequest'
      responses:
        '200':
          description: 登录成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/LoginResponse'
components:
  schemas:
    LoginRequest:
      type: object
      required: [username, password]
      properties:
        username:
          type: string
          description: 用户名或邮箱
        password:
          type: string
          description: 密码
```

### 8.2 测试用例
1. **认证测试**: 正常登录、错误密码、锁定账户、Token刷新
2. **权限测试**: 无权限访问、越权访问、数据隔离
3. **并发测试**: 多用户同时登录、权限变更即时生效
4. **安全测试**: SQL注入、XSS、CSRF、暴力破解防护
5. **性能测试**: 高频权限检查、大量用户查询、审计日志写入

### 8.3 部署配置
```yaml
# config/security.yaml
jwt:
  secret_key: ${JWT_SECRET_KEY}
  algorithm: HS256
  access_token_expire_minutes: 15
  refresh_token_expire_days: 7
  
password:
  min_length: 8
  require_uppercase: true
  require_lowercase: true
  require_digits: true
  max_age_days: 90
  
session:
  max_concurrent_sessions: 5
  idle_timeout_minutes: 30
```

---

**下一步**：
1. 评审本API设计
2. 生成OpenAPI规范文档
3. 实现API接口代码
4. 编写API测试用例
5. 性能测试和安全测试

**评审人**：后端架构师、安全专家、前端工程师  
**评审日期**：2026-04-02