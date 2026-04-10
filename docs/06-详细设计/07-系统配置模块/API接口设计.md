# 系统配置模块 - API接口设计

## 概述
本文档描述系统配置模块的RESTful API接口设计，包括系统参数管理、字典数据管理、审批流程配置、通知模板管理和日志配置等功能的接口定义。

## 设计原则
1. **RESTful风格**：遵循RESTful设计规范，使用合适的HTTP方法和状态码
2. **版本管理**：API支持版本控制，所有接口以`/api/v1/`为前缀
3. **统一响应格式**：所有接口返回统一格式的JSON响应
4. **权限控制**：每个接口都需要相应的权限验证
5. **参数校验**：对输入参数进行严格校验，返回明确的错误信息
6. **多租户支持**：所有接口默认支持多租户，通过请求头`X-Tenant-Id`传递租户信息

## 通用约定

### 请求头
| 请求头 | 说明 | 必填 |
|--------|------|------|
| X-Tenant-Id | 租户ID | 是 |
| Authorization | Bearer Token | 是 |
| Content-Type | application/json | 是 |

### 响应格式
```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "timestamp": 1680000000000
}
```

### 错误码定义
| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 接口详细设计

### 1. 系统参数管理接口

#### 1.1 获取系统参数列表
- **URL**: `GET /api/v1/configs`
- **说明**: 分页查询系统参数列表
- **请求参数**:
  ```json
  {
    "page": 1,
    "size": 20,
    "module": "SYSTEM",
    "configKey": "",
    "isSystem": 0
  }
  ```
- **响应数据**:
  ```json
  {
    "total": 100,
    "list": [
      {
        "id": 1,
        "configKey": "system.name",
        "configValue": "NESOM运维管理系统",
        "configType": "STRING",
        "module": "SYSTEM",
        "description": "系统名称",
        "isSensitive": 0,
        "isSystem": 1,
        "createdTime": "2026-04-01 10:00:00",
        "updatedTime": "2026-04-01 10:00:00"
      }
    ]
  }
  ```

#### 1.2 获取单个系统参数
- **URL**: `GET /api/v1/configs/{configKey}`
- **说明**: 根据配置键获取配置值
- **路径参数**: configKey - 配置键
- **响应数据**: 同1.1中的单个配置项

#### 1.3 创建系统参数
- **URL**: `POST /api/v1/configs`
- **说明**: 创建新的系统参数
- **请求体**:
  ```json
  {
    "configKey": "system.timeout",
    "configValue": "30",
    "configType": "NUMBER",
    "module": "SYSTEM",
    "description": "请求超时时间(秒)",
    "isSensitive": 0,
    "isSystem": 0
  }
  ```
- **响应数据**: 创建成功的配置项信息

#### 1.4 更新系统参数
- **URL**: `PUT /api/v1/configs/{configKey}`
- **说明**: 更新系统参数
- **路径参数**: configKey - 配置键
- **请求体**: 同1.3（可部分更新）
- **响应数据**: 更新后的配置项信息

#### 1.5 删除系统参数
- **URL**: `DELETE /api/v1/configs/{configKey}`
- **说明**: 删除系统参数（仅支持非系统级配置）
- **路径参数**: configKey - 配置键
- **响应数据**: 无

#### 1.6 批量更新系统参数
- **URL**: `PUT /api/v1/configs/batch`
- **说明**: 批量更新系统参数
- **请求体**:
  ```json
  {
    "configs": [
      {
        "configKey": "system.timeout",
        "configValue": "60"
      },
      {
        "configKey": "system.log.level",
        "configValue": "INFO"
      }
    ]
  }
  ```
- **响应数据**: 批量更新结果

### 2. 字典数据管理接口

#### 2.1 获取字典类型列表
- **URL**: `GET /api/v1/dict/types`
- **说明**: 获取所有字典类型
- **响应数据**:
  ```json
  {
    "types": ["gender", "status", "priority", "department"]
  }
  ```

#### 2.2 获取字典数据列表
- **URL**: `GET /api/v1/dict/data`
- **说明**: 根据字典类型获取字典数据
- **请求参数**:
  - dictType: 字典类型（必填）
  - status: 状态（0-禁用，1-启用，默认1）
- **响应数据**:
  ```json
  [
    {
      "id": 1,
      "dictCode": "MALE",
      "dictName": "男",
      "dictValue": "1",
      "sortOrder": 1,
      "parentId": null,
      "status": 1,
      "remark": ""
    }
  ]
  ```

#### 2.3 创建字典数据
- **URL**: `POST /api/v1/dict/data`
- **说明**: 创建字典数据
- **请求体**:
  ```json
  {
    "dictType": "gender",
    "dictCode": "UNKNOWN",
    "dictName": "未知",
    "dictValue": "0",
    "sortOrder": 3,
    "parentId": null,
    "status": 1,
    "remark": "性别未知"
  }
  ```
- **响应数据**: 创建成功的字典数据

#### 2.4 更新字典数据
- **URL**: `PUT /api/v1/dict/data/{id}`
- **说明**: 更新字典数据
- **路径参数**: id - 字典数据ID
- **请求体**: 同2.3（可部分更新）
- **响应数据**: 更新后的字典数据

#### 2.5 删除字典数据
- **URL**: `DELETE /api/v1/dict/data/{id}`
- **说明**: 删除字典数据（仅支持非系统字典）
- **路径参数**: id - 字典数据ID
- **响应数据**: 无

#### 2.6 导出字典数据
- **URL**: `GET /api/v1/dict/export`
- **说明**: 导出字典数据为Excel文件
- **请求参数**: dictType（可选）
- **响应**: Excel文件流

### 3. 审批流程配置接口

#### 3.1 获取审批流程列表
- **URL**: `GET /api/v1/approval/flows`
- **说明**: 分页查询审批流程配置
- **请求参数**:
  - page: 页码，默认1
  - size: 每页大小，默认20
  - businessType: 业务类型
  - isActive: 是否激活
- **响应数据**: 分页列表

#### 3.2 获取审批流程详情
- **URL**: `GET /api/v1/approval/flows/{flowCode}`
- **说明**: 根据流程编码获取审批流程详情
- **路径参数**: flowCode - 流程编码
- **查询参数**: version - 版本号（可选，默认最新版本）
- **响应数据**: 流程详情，包含节点配置

#### 3.3 创建审批流程
- **URL**: `POST /api/v1/approval/flows`
- **说明**: 创建新的审批流程
- **请求体**:
  ```json
  {
    "flowCode": "LEAVE_APPROVAL",
    "flowName": "请假审批流程",
    "businessType": "LEAVE",
    "flowConfig": {
      "nodes": [
        {
          "nodeId": "submit",
          "nodeName": "提交申请",
          "nodeType": "start"
        },
        {
          "nodeId": "dept_approve",
          "nodeName": "部门审批",
          "nodeType": "approval",
          "approvers": ["dept_manager"],
          "conditions": []
        }
      ],
      "transitions": [
        {
          "from": "submit",
          "to": "dept_approve",
          "condition": null
        }
      ]
    },
    "isActive": 1,
    "startTime": "2026-04-01 00:00:00"
  }
  ```
- **响应数据**: 创建成功的流程信息

#### 3.4 发布审批流程版本
- **URL**: `POST /api/v1/approval/flows/{flowCode}/publish`
- **说明**: 发布新的流程版本
- **路径参数**: flowCode - 流程编码
- **请求体**: 同3.3的flowConfig
- **响应数据**: 新版本号

#### 3.5 停用审批流程
- **URL**: `PUT /api/v1/approval/flows/{flowCode}/disable`
- **说明**: 停用审批流程
- **路径参数**: flowCode - 流程编码
- **响应数据**: 无

### 4. 通知模板管理接口

#### 4.1 获取通知模板列表
- **URL**: `GET /api/v1/notice/templates`
- **说明**: 分页查询通知模板
- **请求参数**:
  - noticeType: 通知类型（EMAIL/SMS/WECHAT/IN_APP）
  - status: 状态（0-禁用，1-启用）
- **响应数据**: 分页列表

#### 4.2 获取通知模板详情
- **URL**: `GET /api/v1/notice/templates/{templateCode}`
- **说明**: 根据模板编码获取模板详情
- **路径参数**: templateCode - 模板编码
- **响应数据**: 模板详情

#### 4.3 创建通知模板
- **URL**: `POST /api/v1/notice/templates`
- **说明**: 创建新的通知模板
- **请求体**:
  ```json
  {
    "templateCode": "PASSWORD_RESET",
    "templateName": "密码重置通知",
    "noticeType": "EMAIL",
    "titleTemplate": "密码重置通知",
    "contentTemplate": "尊敬的{username}，您的密码重置验证码是：{code}，有效期10分钟。",
    "variables": [
      {
        "name": "username",
        "description": "用户名",
        "required": true
      },
      {
        "name": "code",
        "description": "验证码",
        "required": true
      }
    ],
    "isHtml": 0,
    "status": 1
  }
  ```
- **响应数据**: 创建成功的模板信息

#### 4.4 发送测试通知
- **URL**: `POST /api/v1/notice/templates/{templateCode}/test`
- **说明**: 使用模板发送测试通知
- **路径参数**: templateCode - 模板编码
- **请求体**:
  ```json
  {
    "recipient": "test@example.com",
    "variables": {
      "username": "测试用户",
      "code": "123456"
    }
  }
  ```
- **响应数据**: 发送结果

### 5. 日志配置接口

#### 5.1 获取日志配置列表
- **URL**: `GET /api/v1/log/configs`
- **说明**: 获取所有模块的日志配置
- **响应数据**: 日志配置列表

#### 5.2 更新日志配置
- **URL**: `PUT /api/v1/log/configs/{module}`
- **说明**: 更新指定模块的日志配置
- **路径参数**: module - 模块名称
- **请求体**:
  ```json
  {
    "logLevel": "DEBUG",
    "retentionDays": 90,
    "storageType": "ELK",
    "configJson": {
      "elkHost": "http://elk-server:9200",
      "indexPrefix": "nesom-logs"
    },
    "isEnabled": 1
  }
  ```
- **响应数据**: 更新后的配置

#### 5.3 获取审计日志
- **URL**: `GET /api/v1/log/audit`
- **说明**: 分页查询审计日志
- **请求参数**:
  - startTime: 开始时间
  - endTime: 结束时间
  - module: 模块名称
  - operation: 操作类型
  - username: 用户名
- **响应数据**: 分页列表

### 6. 公共接口

#### 6.1 刷新配置缓存
- **URL**: `POST /api/v1/configs/cache/refresh`
- **说明**: 刷新所有配置缓存
- **请求参数**: type - 缓存类型（config/dict/flow，默认全部）
- **响应数据**: 刷新结果

#### 6.2 获取系统健康状态
- **URL**: `GET /api/v1/health`
- **说明**: 获取系统配置模块健康状态
- **响应数据**:
  ```json
  {
    "status": "UP",
    "components": {
      "database": "UP",
      "redis": "UP",
      "configCache": "UP"
    },
    "details": {
      "configCount": 150,
      "dictCount": 200,
      "lastRefreshTime": "2026-04-02 10:30:00"
    }
  }
  ```

## API安全设计

### 1. 认证与授权
- 使用JWT Token进行身份认证
- 每个接口都需要对应的权限码
- 权限码格式：`模块:功能:操作`，如`config:sys:read`

### 2. 参数校验
- 使用Bean Validation进行参数校验
- 对敏感参数进行脱敏处理
- 对JSON格式的配置字段进行语法校验

### 3. 防重放攻击
- 对重要操作接口（如配置更新）添加防重放机制
- 使用时间戳和随机数生成签名

### 4. 限流控制
- 对公共查询接口进行限流，防止恶意请求
- 对配置更新接口进行更严格的限流控制

## API版本管理
- 当前版本：v1
- 版本升级时，旧版本API需至少保留6个月
- 新功能优先在新版本中提供，逐步淘汰旧版本

## 接口文档生成
- 使用Swagger/OpenAPI 3.0生成在线接口文档
- 文档地址：`/api-docs`
- 提供接口测试功能

---
*最后更新：2026-04-02*