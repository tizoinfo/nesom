## NESOM（新能源运维管理系统）

NESOM 是一个面向多品牌新能源设备的开放、中立运维管理平台，目标是在 **MVP 阶段以“简化优先”的前后端分离架构** 快速落地核心运维能力，并为后续扩展（微服务拆分、时序数据、预测性维护等）预留空间。

当前仓库主要用于**沉淀项目设计与管理文档**（`docs/`）。如后续加入 `frontend/`、`backend/` 等代码目录，本 `README` 会同步补充可运行的开发/部署指引。

## 快速入口

- **从这里开始**：`docs/INDEX.md`
- **文档目录说明（原有）**：`docs/README.md`

## 项目概览（摘录自概要设计）

- **定位**：新能源场站运维管理系统（多品牌设备接入、开放平台）
- **核心目标**：
  - 设备实时监控与智能预警
  - 工单全生命周期管理
  - 巡检与备件管理
  - 数据分析与报表
- **建议技术栈（规划）**：
  - 前端：Vue 3 + TypeScript + Element Plus + Vite
  - 后端：Python 3.11 + FastAPI + SQLAlchemy/Pydantic
  - 存储：MySQL 8 + Redis 7 + MinIO（可选），时序数据预留 InfluxDB
  - 部署：Docker Compose（MVP），生产可演进至 Kubernetes

## MVP 模块划分（7 个核心模块）

- 设备监控
- 工单管理
- 用户权限管理（认证授权 / RBAC）
- 备件管理
- 巡检管理
- 报表统计
- 系统配置

## 文档贡献

请阅读 `docs/CONTRIBUTING.md` 了解：

- 文档命名与放置规则
- Draft/Reviewed 状态标识
- 评审流程与模板使用方式

