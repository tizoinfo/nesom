# 备件管理模块 - API接口详细设计

**版本**: 1.0  
**日期**: 2026-04-02  
**作者**: 高级项目经理  
**状态**: Draft  
**审核状态**: 待评审  
**继承自**: 概要设计-模块划分设计.md (备件管理API部分)  
**技术栈**: Vue 3.4 + Python 3.11 + FastAPI + MySQL 8.0 + Redis + Docker

## 1. 设计概述

### 1.1 设计目标
提供完整的备件管理RESTful API接口，支持：
- 备件档案全生命周期管理
- 多仓库库存管理和实时查询
- 入库、出库、调拨、盘点全流程
- 供应商管理和采购流程
- 库存预警和智能补货
- 成本核算和库存优化

### 1.2 设计原则
1. **RESTful规范**：资源导向，HTTP方法语义明确
2. **版本控制**：API版本前缀 `/api/v1/`
3. **数据一致性**：库存操作事务保障，防止超卖
4. **实时性**：库存数据实时更新，WebSocket推送变更
5. **移动端支持**：支持扫码出入库、移动盘点
6. **安全审计**：所有库存操作记录详细审计日志

### 1.3 技术约束
- **框架**: FastAPI 0.104+ (Python 3.11+)
- **认证**: JWT (JSON Web Token)
- **序列化**: Pydantic v2 模型验证
- **数据库**: SQLAlchemy 2.0 + MySQL 8.0
- **缓存**: Redis 7.0 (库存热点数据缓存)
- **消息队列**: RabbitMQ/Celery (异步库存计算)
- **WebSocket**: Socket.io (实时库存变更通知)

## 2. 通用设计规范

### 2.1 请求/响应格式

#### 成功响应格式
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {...},  // 具体数据
  "meta": {       // 分页元数据
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
  "message": "库存不足",
  "detail": {     // 错误详情
    "spare_part_code": "SP-PV-INV-001",
    "available_stock": 5,
    "requested_quantity": 10
  },
  "timestamp": "2026-04-02T10:30:00Z"
}
```

### 2.2 分页规范
- **参数**: `page` (默认1), `page_size` (默认20, 最大100)
- **响应**: 包含`data`数组和`meta`分页信息
- **性能**: 使用基于主键的游标分页优化

### 2.3 过滤和排序
- **过滤**: `filter[category_id]=cat_001&filter[status]=active`
- **范围过滤**: `filter[current_stock][gte]=10&filter[current_stock][lte]=100`
- **排序**: `sort=created_at.desc,spare_part_name.asc`
- **字段选择**: `fields=id,spare_part_code,spare_part_name,current_stock`

### 2.4 认证和授权
- **认证头**: `Authorization: Bearer <jwt_token>`
- **权限**: 基于角色的访问控制 (RBAC)
  - `spare_part:read` - 查看备件
  - `spare_part:create` - 创建备件
  - `spare_part:update` - 更新备件
  - `spare_part:delete` - 删除备件
  - `inventory:read` - 查看库存
  - `inventory:issue` - 出库操作
  - `inventory:receive` - 入库操作
  - `inventory:transfer` - 调拨操作
  - `inventory:adjust` - 库存调整
  - `purchase:manage` - 采购管理
  - `supplier:manage` - 供应商管理
- **操作审计**: 所有库存操作记录审计日志

## 3. API端点详细设计

### 3.1 备件档案管理接口

#### 3.1.1 获取备件列表
**端点**: `GET /api/v1/spare-parts`  
**描述**: 查询备件列表，支持分页、过滤、排序、字段选择

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 | 示例 |
|--------|------|------|------|------|
| page | int | 否 | 页码，默认1 | `1` |
| page_size | int | 否 | 每页数量，默认20，最大100 | `20` |
| filter | object | 否 | 过滤条件 | `{"status": "active", "category_id": "cat_001"}` |
| sort | string | 否 | 排序字段 | `created_at.desc,spare_part_name.asc` |
| fields | string | 否 | 返回字段，逗号分隔 | `id,spare_part_code,spare_part_name,current_stock` |
| include | string | 否 | 包含关联数据 | `category,warehouse_stock` |
| keyword | string | 否 | 关键词搜索（名称、规格、型号） | `逆变器` |
| low_stock_only | boolean | 否 | 仅查询低库存备件 | `true` |
| near_expiry_only | boolean | 否 | 仅查询近效期备件 | `true` |

**响应数据**:
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "id": "sp_001",
      "spare_part_code": "SP-PV-INV-001",
      "spare_part_name": "光伏逆变器电源模块",
      "specification": "DC-AC 5kW",
      "model": "PV-INV-PM5K",
      "brand": "阳光电源",
      "category": {
        "id": "cat_001",
        "category_name": "逆变器备件"
      },
      "unit": "piece",
      "current_stock": 25,
      "available_stock": 20,
      "reserved_stock": 5,
      "min_stock_level": 10,
      "max_stock_level": 100,
      "last_purchase_price": 1200.00,
      "status": "active",
      "is_low_stock": false,
      "is_near_expiry": false,
      "warehouse_stock": [
        {
          "warehouse_name": "中心仓库",
          "quantity": 15,
          "available": 10
        },
        {
          "warehouse_name": "上海场站仓",
          "quantity": 10,
          "available": 10
        }
      ]
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 156,
    "total_pages": 8
  }
}
```

**权限要求**: `spare_part:read`

#### 3.1.2 创建备件
**端点**: `POST /api/v1/spare-parts`  
**描述**: 创建新的备件档案

**请求体**:
```json
{
  "spare_part_code": "SP-PV-INV-002",
  "spare_part_name": "光伏逆变器控制板",
  "category_id": "cat_001",
  "specification": "控制主板 V2.0",
  "model": "PV-INV-CTRL-V2",
  "brand": "华为",
  "unit": "piece",
  "unit_weight": 0.5,
  "unit_volume": 0.001,
  "attributes": {
    "color": "绿色",
    "size": "15x10cm"
  },
  "description": "光伏逆变器控制主板，支持智能监控",
  "technical_parameters": {
    "voltage": "12V",
    "current": "2A",
    "interface": "RS485"
  },
  "applicable_devices": [
    {"device_type": "光伏逆变器", "model": "SUN2000-5KTL"}
  ],
  "is_consumable": false,
  "is_controlled": true,
  "has_serial_number": true,
  "shelf_life_months": 36,
  "procurement_lead_time": 30,
  "min_order_quantity": 1,
  "economic_order_quantity": 10,
  "standard_cost": 800.00,
  "min_stock_level": 5,
  "max_stock_level": 50,
  "safety_stock_level": 10,
  "abc_classification": "B",
  "storage_requirements": {
    "temperature": "0-40℃",
    "humidity": "≤85%",
    "antistatic": true
  }
}
```

**响应数据**:
```json
{
  "code": 201,
  "message": "备件创建成功",
  "data": {
    "id": "sp_002",
    "spare_part_code": "SP-PV-INV-002",
    "qr_code": "data:image/png;base64,...",
    "created_at": "2026-04-02T10:30:00Z"
  }
}
```

**权限要求**: `spare_part:create`

#### 3.1.3 获取备件详情
**端点**: `GET /api/v1/spare-parts/{spare_part_id}`  
**描述**: 获取备件详细信息，包括库存分布、采购历史等

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| spare_part_id | string | 是 | 备件ID |

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| include | string | 否 | 包含关联数据: `category,transactions,purchase_history,stock_details` |

**响应数据**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "id": "sp_001",
    "spare_part_code": "SP-PV-INV-001",
    "spare_part_name": "光伏逆变器电源模块",
    "category": {
      "id": "cat_001",
      "category_code": "CAT-INV-PART",
      "category_name": "逆变器备件"
    },
    "specification": "DC-AC 5kW",
    "model": "PV-INV-PM5K",
    "brand": "阳光电源",
    "unit": "piece",
    "current_stock": 25,
    "available_stock": 20,
    "reserved_stock": 5,
    "in_transit_stock": 10,
    "total_value": 30000.00,
    "standard_cost": 1200.00,
    "last_purchase_price": 1250.00,
    "avg_purchase_price": 1210.50,
    "min_stock_level": 10,
    "max_stock_level": 100,
    "safety_stock_level": 20,
    "abc_classification": "B",
    "status": "active",
    "is_consumable": false,
    "is_controlled": false,
    "has_serial_number": false,
    "shelf_life_months": 24,
    "procurement_lead_time": 15,
    "last_inventory_date": "2026-03-15",
    "last_purchase_date": "2026-03-20",
    "last_issue_date": "2026-04-01",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2026-04-01T15:20:00Z",
    "stock_distribution": [
      {
        "warehouse_id": "wh_001",
        "warehouse_name": "中心仓库",
        "location_code": "A-01-02-03",
        "quantity": 15,
        "available": 10,
        "reserved": 5,
        "batch_no": "B2026032001",
        "expiry_date": "2028-03-20"
      },
      {
        "warehouse_id": "wh_002",
        "warehouse_name": "上海场站仓",
        "location_code": "B-02-01-01",
        "quantity": 10,
        "available": 10,
        "reserved": 0,
        "batch_no": "B2026040101",
        "expiry_date": "2028-04-01"
      }
    ],
    "recent_transactions": [
      {
        "transaction_no": "TR-20260402-001",
        "transaction_type": "issue_out",
        "quantity": -2,
        "unit_price": 1200.00,
        "warehouse_name": "中心仓库",
        "reference_no": "WO-SH01-20260402-001",
        "operator_name": "李四",
        "transaction_date": "2026-04-02T09:30:00Z"
      }
    ]
  }
}
```

**权限要求**: `spare_part:read`

#### 3.1.4 更新备件
**端点**: `PATCH /api/v1/spare-parts/{spare_part_id}`  
**描述**: 更新备件信息（部分更新）

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| spare_part_id | string | 是 | 备件ID |

**请求体**:
```json
{
  "spare_part_name": "光伏逆变器电源模块（升级版）",
  "specification": "DC-AC 5kW V2.0",
  "min_stock_level": 15,
  "max_stock_level": 120,
  "standard_cost": 1300.00,
  "description": "升级版电源模块，效率提升5%"
}
```

**响应数据**:
```json
{
  "code": 200,
  "message": "备件更新成功",
  "data": {
    "id": "sp_001",
    "updated_at": "2026-04-02T11:15:00Z"
  }
}
```

**权限要求**: `spare_part:update`

#### 3.1.5 删除备件
**端点**: `DELETE /api/v1/spare-parts/{spare_part_id}`  
**描述**: 删除备件（仅限无库存、无关联记录的备件）

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| spare_part_id | string | 是 | 备件ID |

**响应数据**:
```json
{
  "code": 200,
  "message": "备件删除成功"
}
```

**权限要求**: `spare_part:delete`

### 3.2 库存管理接口

#### 3.2.1 获取库存列表
**端点**: `GET /api/v1/inventory`  
**描述**: 查询库存列表，支持多维度筛选

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| warehouse_id | string | 否 | 仓库ID筛选 |
| spare_part_id | string | 否 | 备件ID筛选 |
| location_id | string | 否 | 库位ID筛选 |
| status | string | 否 | 库存状态: available,reserved,quarantine,frozen |
| batch_no | string | 否 | 批次号筛选 |
| expiry_date_from | string | 否 | 有效期起始日期 |
| expiry_date_to | string | 否 | 有效期截止日期 |
| low_stock_only | boolean | 否 | 仅查询低库存 |
| near_expiry_only | boolean | 否 | 仅查询近效期 |

**权限要求**: `inventory:read`

#### 3.2.2 实时库存查询
**端点**: `GET /api/v1/inventory/real-time`  
**描述**: 获取备件实时库存信息（多仓库汇总）

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| spare_part_ids | array | 是 | 备件ID数组 | `["sp_001","sp_002"]` |
| warehouse_ids | array | 否 | 仓库ID数组（不传则查询所有仓库） |

**响应数据**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "sp_001": {
      "total_stock": 25,
      "available_stock": 20,
      "reserved_stock": 5,
      "in_transit_stock": 10,
      "warehouse_details": [
        {
          "warehouse_id": "wh_001",
          "warehouse_name": "中心仓库",
          "quantity": 15,
          "available": 10,
          "reserved": 5
        },
        {
          "warehouse_id": "wh_002",
          "warehouse_name": "上海场站仓",
          "quantity": 10,
          "available": 10,
          "reserved": 0
        }
      ]
    }
  }
}
```

**权限要求**: `inventory:read`

#### 3.2.3 库存预留
**端点**: `POST /api/v1/inventory/reserve`  
**描述**: 为工单预留库存（防止超卖）

**请求体**:
```json
{
  "work_order_id": "wo_123456",
  "items": [
    {
      "spare_part_id": "sp_001",
      "warehouse_id": "wh_001",
      "quantity": 2,
      "expected_issue_date": "2026-04-02T14:00:00Z"
    },
    {
      "spare_part_id": "sp_002",
      "warehouse_id": "wh_001",
      "quantity": 1,
      "expected_issue_date": "2026-04-02T14:00:00Z"
    }
  ],
  "reserve_notes": "工单WO-SH01-20260402-001维修使用"
}
```

**响应数据**:
```json
{
  "code": 200,
  "message": "库存预留成功",
  "data": {
    "reservation_id": "resv_001",
    "reserved_items": [
      {
        "spare_part_id": "sp_001",
        "spare_part_name": "光伏逆变器电源模块",
        "warehouse_name": "中心仓库",
        "quantity": 2,
        "reserved_stock": 2,
        "available_after_reserve": 8
      }
    ],
    "expires_at": "2026-04-03T14:00:00Z"  // 24小时后自动释放
  }
}
```

**权限要求**: `inventory:issue`

#### 3.2.4 库存预留释放
**端点**: `POST /api/v1/inventory/reserve/{reservation_id}/release`  
**描述**: 释放预留的库存

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| reservation_id | string | 是 | 预留ID |

**请求体**:
```json
{
  "release_reason": "工单取消",
  "partial_release": [
    {
      "spare_part_id": "sp_001",
      "quantity": 1  // 部分释放，不传则全部释放
    }
  ]
}
```

**权限要求**: `inventory:issue`

### 3.3 入库管理接口

#### 3.3.1 采购收货入库
**端点**: `POST /api/v1/inventory/receive-purchase`  
**描述**: 采购订单收货入库

**请求体**:
```json
{
  "purchase_order_id": "po_001",
  "receipt_date": "2026-04-02T10:00:00Z",
  "receipt_notes": "供应商准时送达，包装完好",
  "items": [
    {
      "purchase_order_item_id": 1,
      "spare_part_id": "sp_001",
      "warehouse_id": "wh_001",
      "location_id": "loc_001",
      "quantity": 50,
      "unit_price": 1200.00,
      "batch_no": "B20260402001",
      "lot_no": "L20260402",
      "manufacture_date": "2026-03-01",
      "expiry_date": "2028-03-01",
      "serial_numbers": ["SN001", "SN002", "SN003"],  // 受控件
      "quality_status": "passed",  // passed, failed, pending
      "inspection_notes": "抽检合格"
    }
  ],
  "attachments": [
    {
      "type": "delivery_note",
      "url": "https://...",
      "filename": "送货单-20260402.pdf"
    }
  ]
}
```

**响应数据**:
```json
{
  "code": 200,
  "message": "收货入库成功",
  "data": {
    "transaction_ids": ["tr_001", "tr_002"],
    "updated_stock": {
      "sp_001": {
        "old_stock": 25,
        "new_stock": 75,
        "change": 50
      }
    },
    "purchase_order_status": "partially_received"
  }
}
```

**权限要求**: `inventory:receive`

#### 3.3.2 其他入库
**端点**: `POST /api/v1/inventory/receive-other`  
**描述**: 其他类型入库（退货、调拨、调整、生产等）

**请求体**:
```json
{
  "transaction_type": "return_in",  // return_in, transfer_in, adjust_in, production_in, other_in
  "reference_no": "RTN-20260402-001",
  "transaction_date": "2026-04-02T11:00:00Z",
  "items": [
    {
      "spare_part_id": "sp_001",
      "warehouse_id": "wh_001",
      "location_id": "loc_002",
      "quantity": 5,
      "unit_price": 1200.00,
      "batch_no": "B2026032001",
      "reason": "工单退库，未使用"
    }
  ],
  "remarks": "工单取消，备件退回仓库"
}
```

**权限要求**: `inventory:receive`

### 3.4 出库管理接口

#### 3.4.1 工单领用出库
**端点**: `POST /api/v1/inventory/issue-work-order`  
**描述**: 工单领用备件出库

**请求体**:
```json
{
  "work_order_id": "wo_123456",
  "issue_date": "2026-04-02T14:00:00Z",
  "issued_to": "user_002",  // 领用人
  "issued_to_name": "李四",
  "issue_notes": "现场维修领用",
  "items": [
    {
      "spare_part_id": "sp_001",
      "warehouse_id": "wh_001",
      "location_id": "loc_001",
      "quantity": 2,
      "unit_price": 1200.00,  // 自动获取成本价
      "batch_no": "B2026032001",  // 可选，不传则自动分配批次（先进先出）
      "serial_numbers": ["SN001", "SN002"],  // 受控件必须传
      "reservation_id": "resv_001"  // 预留ID，如果有预留
    }
  ]
}
```

**响应数据**:
```json
{
  "code": 200,
  "message": "出库成功",
  "data": {
    "transaction_ids": ["tr_003"],
    "issue_no": "ISS-20260402-001",
    "total_value": 2400.00,
    "updated_stock": {
      "sp_001": {
        "old_stock": 75,
        "new_stock": 73,
        "change": -2
      }
    }
  }
}
```

**权限要求**: `inventory:issue`

#### 3.4.2 扫码出库
**端点**: `POST /api/v1/inventory/issue-scan`  
**描述**: 移动端扫码出库（简化流程）

**请求体**:
```json
{
  "work_order_id": "wo_123456",
  "scanned_items": [
    {
      "qr_code": "nesom://sparepart/sp_001/batch/B2026032001/loc/loc_001",
      "quantity": 1,
      "operator_id": "user_002",
      "location": "A区光伏阵列",
      "longitude": 121.4737,
      "latitude": 31.2304
    }
  ]
}
```

**权限要求**: `inventory:issue` (移动端权限)

#### 3.4.3 其他出库
**端点**: `POST /api/v1/inventory/issue-other`  
**描述**: 其他类型出库（退货、调拨、报废、调整等）

**请求体**:
```json
{
  "transaction_type": "scrap_out",  // return_out, transfer_out, adjust_out, scrap_out, other_out
  "reference_no": "SCR-20260402-001",
  "transaction_date": "2026-04-02T15:00:00Z",
  "items": [
    {
      "spare_part_id": "sp_001",
      "warehouse_id": "wh_001",
      "location_id": "loc_001",
      "quantity": 1,
      "unit_price": 1200.00,
      "batch_no": "B20260115001",
      "reason": "设备报废，备件同步报废",
      "disposal_method": "recycle",  // recycle, destroy, sell
      "disposal_certificate": "https://..."  // 处置证明
    }
  ],
  "remarks": "设备报废，关联备件同步处理"
}
```

**权限要求**: `inventory:issue`

### 3.5 调拨管理接口

#### 3.5.1 创建调拨单
**端点**: `POST /api/v1/transfer-orders`  
**描述**: 创建仓库间调拨单

**请求体**:
```json
{
  "from_warehouse_id": "wh_001",
  "to_warehouse_id": "wh_002",
  "expected_completion_date": "2026-04-03T18:00:00Z",
  "transfer_type": "emergency",
  "items": [
    {
      "spare_part_id": "sp_001",
      "quantity": 10,
      "batch_no": "B2026032001",  // 可选，指定批次
      "expected_unit_price": 1200.00
    }
  ],
  "shipping_method": "self_pickup",  // self_pickup, courier, logistics
  "remarks": "上海场站紧急需求"
}
```

**响应数据**:
```json
{
  "code": 201,
  "message": "调拨单创建成功",
  "data": {
    "id": "to_001",
    "transfer_order_no": "TO-20260402-001",
    "transfer_status": "draft",
    "total_quantity": 10,
    "total_value": 12000.00
  }
}
```

**权限要求**: `inventory:transfer`

#### 3.5.2 调拨出库
**端点**: `POST /api/v1/transfer-orders/{transfer_order_id}/issue`  
**描述**: 调拨出库（调出仓库发货）

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| transfer_order_id | string | 是 | 调拨单ID |

**请求体**:
```json
{
  "issue_date": "2026-04-02T16:00:00Z",
  "issued_by": "user_003",
  "tracking_number": "SF123456789",
  "driver_info": {
    "name": "张三",
    "phone": "13800138000",
    "vehicle_no": "沪A12345"
  },
  "items": [
    {
      "transfer_order_item_id": 1,
      "actual_quantity": 10,
      "batch_no": "B2026032001",
      "location_id": "loc_001",
      "serial_numbers": ["SN001", "SN002"]  // 受控件
    }
  ],
  "attachments": [
    {
      "type": "shipping_label",
      "url": "https://...",
      "filename": "运单-20260402.jpg"
    }
  ]
}
```

**权限要求**: `inventory:transfer`

#### 3.5.3 调拨入库
**端点**: `POST /api/v1/transfer-orders/{transfer_order_id}/receive`  
**描述**: 调拨入库（调入仓库收货）

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| transfer_order_id | string | 是 | 调拨单ID |

**请求体**:
```json
{
  "receive_date": "2026-04-03T10:00:00Z",
  "received_by": "user_004",
  "quality_check": "passed",
  "items": [
    {
      "transfer_order_item_id": 1,
      "actual_quantity_received": 10,
      "warehouse_id": "wh_002",
      "location_id": "loc_005",
      "batch_no": "B2026032001",
      "serial_numbers": ["SN001", "SN002"],
      "quality_status": "passed",
      "notes": "包装完好，数量正确"
    }
  ]
}
```

**权限要求**: `inventory:receive`

### 3.6 盘点管理接口

#### 3.6.1 创建盘点单
**端点**: `POST /api/v1/inventory-orders`  
**描述**: 创建库存盘点任务

**请求体**:
```json
{
  "warehouse_id": "wh_001",
  "inventory_type": "cyclic",  // full, partial, cyclic, random, spot
  "inventory_method": "physical",  // physical, system, both
  "start_date": "2026-04-03",
  "planned_end_date": "2026-04-05",
  "team_leader_id": "user_003",
  "team_members": ["user_004", "user_005"],
  "scope": {
    "area_codes": ["A", "B"],  // 盘点区域
    "categories": ["cat_001", "cat_002"],  // 盘点分类
    "spare_part_ids": ["sp_001", "sp_002"]  // 盘点备件
  },
  "remarks": "季度循环盘点"
}
```

**权限要求**: `inventory:adjust`

#### 3.6.2 移动端盘点录入
**端点**: `POST /api/v1/inventory-orders/{inventory_order_id}/count`  
**描述**: 移动端扫码盘点录入

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| inventory_order_id | string | 是 | 盘点单ID |

**请求体**:
```json
{
  "counted_by": "user_004",
  "counted_at": "2026-04-03T14:30:00Z",
  "items": [
    {
      "spare_part_id": "sp_001",
      "warehouse_id": "wh_001",
      "location_id": "loc_001",
      "batch_no": "B2026032001",
      "serial_number": "SN001",  // 受控件
      "system_quantity": 5,  // 系统库存
      "physical_quantity": 5,  // 实际盘点数量
      "difference": 0,
      "count_notes": "数量相符",
      "photo": "data:image/jpeg;base64,..."  // 盘点照片
    }
  ]
}
```

**权限要求**: `inventory:adjust` (移动端权限)

#### 3.6.3 生成盘点差异
**端点**: `POST /api/v1/inventory-orders/{inventory_order_id}/generate-discrepancy`  
**描述**: 生成盘点差异报告

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| inventory_order_id | string | 是 | 盘点单ID |

**响应数据**:
```json
{
  "code": 200,
  "message": "差异报告生成成功",
  "data": {
    "total_items": 156,
    "counted_items": 150,
    "matched_items": 145,
    "discrepancy_items": 5,
    "discrepancy_value": 6500.00,
    "accuracy_rate": 96.67,
    "discrepancies": [
      {
        "spare_part_id": "sp_001",
        "spare_part_name": "光伏逆变器电源模块",
        "location_code": "A-01-02-03",
        "batch_no": "B2026032001",
        "system_quantity": 5,
        "physical_quantity": 3,
        "difference": -2,
        "value_difference": -2400.00,
        "possible_causes": ["领用未记账", "盘点错误", "丢失"]
      }
    ]
  }
}
```

**权限要求**: `inventory:adjust`

#### 3.6.4 处理盘点差异
**端点**: `POST /api/v1/inventory-orders/{inventory_order_id}/adjust`  
**描述**: 审批并处理盘点差异

**请求体**:
```json
{
  "adjustment_date": "2026-04-05T10:00:00Z",
  "approved_by": "user_003",
  "adjustments": [
    {
      "discrepancy_id": 1,
      "adjustment_type": "write_off",  // write_off, add_stock, investigation
      "adjustment_quantity": -2,
      "unit_price": 1200.00,
      "adjustment_reason": "盘亏，原因待查",
      "responsible_person": "user_006",
      "corrective_actions": "加强库管，安装监控",
      "approval_notes": "同意核销，后续加强管理"
    }
  ]
}
```

**权限要求**: `inventory:adjust` + 审批权限

### 3.7 预警管理接口

#### 3.7.1 获取库存预警
**端点**: `GET /api/v1/alerts/inventory`  
**描述**: 获取库存预警信息

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| alert_type | string | 否 | 预警类型: low_stock, near_expiry, overstock, slow_moving |
| severity | string | 否 | 严重程度: info, warning, error, critical |
| warehouse_id | string | 否 | 仓库ID筛选 |
| acknowledged | boolean | 否 | 是否已确认 |

**响应数据**:
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "id": "alert_001",
      "alert_type": "low_stock",
      "severity": "warning",
      "spare_part_id": "sp_001",
      "spare_part_name": "光伏逆变器电源模块",
      "warehouse_name": "中心仓库",
      "current_stock": 8,
      "threshold": 10,
      "difference": -2,
      "alert_message": "库存低于安全库存水平",
      "suggested_action": "建议采购20件",
      "alert_time": "2026-04-02T10:30:00Z",
      "acknowledged": false,
      "acknowledged_by": null,
      "acknowledged_at": null
    },
    {
      "id": "alert_002",
      "alert_type": "near_expiry",
      "severity": "error",
      "spare_part_id": "sp_002",
      "spare_part_name": "控制主板",
      "warehouse_name": "中心仓库",
      "batch_no": "B20230115001",
      "expiry_date": "2026-05-01",
      "days_remaining": 30,
      "threshold_days": 60,
      "quantity": 15,
      "total_value": 12000.00,
      "alert_message": "批次B20230115001将在30天后过期",
      "suggested_action": "优先使用或退货",
      "alert_time": "2026-04-02T10:35:00Z",
      "acknowledged": false
    }
  ]
}
```

**权限要求**: `inventory:read`

#### 3.7.2 确认预警
**端点**: `POST /api/v1/alerts/{alert_id}/acknowledge`  
**描述**: 确认预警信息

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| alert_id | string | 是 | 预警ID |

**请求体**:
```json
{
  "acknowledge_notes": "已通知采购部门处理",
  "action_taken": "created_purchase_order",
  "action_reference": "PO-20260402-001"
}
```

**权限要求**: `inventory:read` (预警确认权限)

### 3.8 统计报表接口

#### 3.8.1 库存统计
**端点**: `GET /api/v1/statistics/inventory`  
**描述**: 获取库存统计报表

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| time_range | string | 否 | 时间范围: today, week, month, quarter, year, custom |
| start_date | string | 否 | 开始日期（自定义范围） |
| end_date | string | 否 | 结束日期（自定义范围） |
| warehouse_id | string | 否 | 仓库ID筛选 |
| category_id | string | 否 | 分类ID筛选 |
| group_by | string | 否 | 分组方式: category, warehouse, abc_classification |

**响应数据**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "summary": {
      "total_items": 156,
      "total_value": 1250000.00,
      "total_quantity": 8500,
      "avg_unit_price": 147.06,
      "turnover_rate": 2.5,
      "stockout_rate": 0.02
    },
    "by_category": [
      {
        "category_name": "逆变器备件",
        "item_count": 45,
        "total_value": 450000.00,
        "percentage": 36.0
      }
    ],
    "by_warehouse": [
      {
        "warehouse_name": "中心仓库",
        "item_count": 120,
        "total_value": 950000.00,
        "percentage": 76.0
      }
    ],
    "by_abc_classification": [
      {
        "classification": "A",
        "item_count": 15,
        "total_value": 750000.00,
        "percentage": 60.0
      }
    ],
    "trends": {
      "inventory_value": [
        {"date": "2026-03-01", "value": 1200000.00},
        {"date": "2026-04-01", "value": 1250000.00}
      ],
      "in_out_ratio": [
        {"date": "2026-03-01", "in": 150000.00, "out": 120000.00},
        {"date": "2026-04-01", "in": 180000.00, "out": 130000.00}
      ]
    }
  }
}
```

**权限要求**: `inventory:read` + 统计权限

#### 3.8.2 出入库统计
**端点**: `GET /api/v1/statistics/transactions`  
**描述**: 获取出入库交易统计

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| transaction_type | string | 否 | 事务类型筛选 |
| spare_part_id | string | 否 | 备件ID筛选 |
| warehouse_id | string | 否 | 仓库ID筛选 |
| group_by | string | 否 | 分组方式: day, week, month, spare_part, warehouse |

**权限要求**: `inventory:read` + 统计权限

#### 3.8.3 呆滞料分析
**端点**: `GET /api/v1/statistics/slow-moving`  
**描述**: 获取呆滞料分析报告

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| threshold_days | int | 否 | 呆滞阈值（天），默认180 |
| min_value | decimal | 否 | 最小金额筛选 |
| warehouse_id | string | 否 | 仓库ID筛选 |

**响应数据**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "summary": {
      "total_slow_moving_items": 12,
      "total_value": 85000.00,
      "avg_days_no_move": 245
    },
    "items": [
      {
        "spare_part_id": "sp_015",
        "spare_part_name": "旧型号控制板",
        "warehouse_name": "中心仓库",
        "quantity": 25,
        "unit_price": 800.00,
        "total_value": 20000.00,
        "last_transaction_date": "2025-08-15",
        "days_no_move": 230,
        "slow_moving_level": "high",
        "suggested_actions": ["降价促销", "调拨到场站", "报废处理"]
      }
    ]
  }
}
```

**权限要求**: `inventory:read` + 统计权限

### 3.9 移动端专用接口

#### 3.9.1 扫码查询库存
**端点**: `GET /api/v1/mobile/inventory/scan/{qr_content}`  
**描述**: 移动端扫码查询备件库存

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| qr_content | string | 是 | 二维码内容 |

**响应数据**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "spare_part_id": "sp_001",
    "spare_part_code": "SP-PV-INV-001",
    "spare_part_name": "光伏逆变器电源模块",
    "specification": "DC-AC 5kW",
    "current_stock": 25,
    "available_stock": 20,
    "warehouse_stock": [
      {
        "warehouse_name": "中心仓库",
        "location_code": "A-01-02-03",
        "quantity": 15,
        "available": 10
      }
    ],
    "batch_info": [
      {
        "batch_no": "B2026032001",
        "quantity": 5,
        "expiry_date": "2028-03-20",
        "days_remaining": 717
      }
    ]
  }
}
```

**权限要求**: 移动端认证用户

#### 3.9.2 移动端快速出库
**端点**: `POST /api/v1/mobile/inventory/quick-issue`  
**描述**: 移动端快速出库（简化流程）

**请求体**:
```json
{
  "work_order_no": "WO-SH01-20260402-001",
  "operator_id": "user_002",
  "location": "A区光伏阵列",
  "items": [
    {
      "qr_code": "nesom://sparepart/sp_001/batch/B2026032001",
      "quantity": 1,
      "photo": "data:image/jpeg;base64,..."
    }
  ]
}
```

**权限要求**: 移动端认证用户 + `inventory:issue`

#### 3.9.3 移动端盘点
**端点**: `POST /api/v1/mobile/inventory/count`  
**描述**: 移动端盘点数据提交

**请求体**:
```json
{
  "inventory_order_id": "inv_001",
  "operator_id": "user_004",
  "counts": [
    {
      "location_qr": "nesom://location/loc_001",
      "spare_part_qr": "nesom://sparepart/sp_001",
      "batch_qr": "nesom://batch/B2026032001",
      "physical_quantity": 5,
      "photo": "data:image/jpeg;base64,...",
      "count_notes": "数量正确"
    }
  ]
}
```

**权限要求**: 移动端认证用户 + `inventory:adjust`

## 4. 错误码设计

### 4.1 通用错误码
| 错误码 | 描述 | HTTP状态码 |
|--------|------|------------|
| 40001 | 请求参数错误 | 400 |
| 40101 | 未认证 | 401 |
| 40301 | 权限不足 | 403 |
| 40401 | 资源不存在 | 404 |
| 40901 | 资源冲突 | 409 |
| 42201 | 业务规则验证失败 | 422 |
| 50001 | 服务器内部错误 | 500 |

### 4.2 库存特定错误码
| 错误码 | 描述 | 解决方案 |
|--------|------|----------|
| 43001 | 库存不足 | 检查可用库存，或从其他仓库调拨 |
| 43002 | 批次库存不足 | 指定批次库存不足，尝试其他批次 |
| 43003 | 序列号不存在 | 检查序列号是否正确 |
| 43004 | 序列号已出库 | 序列号已被使用 |
| 43005 | 库存已被预留 | 库存已被其他工单预留 |
| 43006 | 库存操作冲突 | 请稍后重试 |
| 43007 | 库存计算错误 | 联系管理员检查库存数据 |
| 43008 | 效期已过 | 备件已过期，不能出库 |
| 43009 | 库位容量不足 | 选择其他库位或调整库存 |

## 5. 性能优化

### 5.1 缓存策略
1. **备件信息缓存**: Redis缓存热点备件数据，TTL 10分钟
2. **库存数据缓存**: 高频查询库存数据缓存，TTL 1分钟
3. **统计结果缓存**: 预计算统计结果，TTL 15分钟
4. **预警数据缓存**: 预警计算结果缓存，TTL 5分钟

### 5.2 数据库优化
1. **索引优化**: 为高频查询字段建立组合索引
2. **读写分离**: 报表查询走只读副本
3. **分区策略**: 大表按时间分区
4. **批量操作**: 支持批量库存操作减少事务数

### 5.3 异步处理
1. **库存计算**: 库存汇总计算异步进行
2. **预警计算**: 库存预警规则异步计算
3. **通知发送**: 库存预警通知异步发送
4. **报表生成**: 复杂报表异步生成

## 6. 安全设计

### 6.1 数据安全
1. **敏感数据加密**: 采购价格、成本数据加密存储
2. **传输加密**: HTTPS + 请求签名
3. **访问控制**: 基于角色的数据访问权限
4. **操作审计**: 所有库存操作记录审计日志

### 6.2 库存安全
1. **并发控制**: 乐观锁防止超卖
2. **操作验证**: 关键操作需要复核或审批
3. **差异处理**: 库存差异调查和处理流程
4. **数据一致性**: 事务保障库存数据一致性

### 6.3 移动端安全
1. **设备绑定**: 移动端设备首次登录需要绑定
2. **离线加密**: 离线数据本地加密存储
3. **操作限制**: 移动端操作权限限制
4. **会话管理**: 移动端会话独立管理

## 7. 监控和日志

### 7.1 监控指标
1. **库存准确率**: 盘点准确率监控
2. **操作响应时间**: API响应时间监控
3. **库存周转率**: 库存周转效率监控
4. **预警准确率**: 预警触发准确率监控

### 7.2 日志记录
1. **操作日志**: 记录所有库存操作
2. **审计日志**: 记录敏感操作审计信息
3. **性能日志**: 记录慢查询和耗时操作
4. **错误日志**: 记录系统错误和异常

---

**下一步**：
1. 评审本API设计
2. 生成OpenAPI规范文档
3. 实现API接口代码
4. 编写API测试用例

**评审人**：后端架构师、前端开发、测试工程师  
**评审日期**：2026-04-02