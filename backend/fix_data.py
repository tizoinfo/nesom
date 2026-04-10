"""Fix missing dictionary data and other data issues."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.core.config import settings


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as s:
        # ── Add missing dictionary data ──
        dicts = [
            # Device status
            ("device_status", "online", "在线", "online", 1),
            ("device_status", "offline", "离线", "offline", 2),
            ("device_status", "warning", "告警", "warning", 3),
            ("device_status", "fault", "故障", "fault", 4),
            ("device_status", "maintenance", "维护中", "maintenance", 5),
            # Work order type
            ("workorder_type", "repair", "维修", "repair", 1),
            ("workorder_type", "maintenance", "保养", "maintenance", 2),
            ("workorder_type", "inspection", "巡检", "inspection", 3),
            ("workorder_type", "fault", "故障", "fault", 4),
            ("workorder_type", "other", "其他", "other", 5),
            # Work order status
            ("workorder_status", "draft", "草稿", "draft", 1),
            ("workorder_status", "pending", "待处理", "pending", 2),
            ("workorder_status", "assigned", "已分配", "assigned", 3),
            ("workorder_status", "in_progress", "进行中", "in_progress", 4),
            ("workorder_status", "pending_review", "待审核", "pending_review", 5),
            ("workorder_status", "completed", "已完成", "completed", 6),
            ("workorder_status", "closed", "已关闭", "closed", 7),
            ("workorder_status", "cancelled", "已取消", "cancelled", 8),
            # Priority
            ("priority", "low", "低", "low", 1),
            ("priority", "medium", "中", "medium", 2),
            ("priority", "high", "高", "high", 3),
            ("priority", "emergency", "紧急", "emergency", 4),
            # Emergency level
            ("emergency_level", "normal", "普通", "normal", 1),
            ("emergency_level", "urgent", "紧急", "urgent", 2),
            ("emergency_level", "critical", "严重", "critical", 3),
            # Alert level
            ("alert_level", "info", "信息", "info", 1),
            ("alert_level", "warning", "警告", "warning", 2),
            ("alert_level", "error", "错误", "error", 3),
            ("alert_level", "critical", "严重", "critical", 4),
            # Alert type
            ("alert_type", "fault", "故障", "fault", 1),
            ("alert_type", "performance", "性能", "performance", 2),
            ("alert_type", "temperature", "温度", "temperature", 3),
            ("alert_type", "communication", "通信", "communication", 4),
            ("alert_type", "voltage", "电压", "voltage", 5),
            ("alert_type", "current", "电流", "current", 6),
            ("alert_type", "humidity", "湿度", "humidity", 7),
            # Inspection type
            ("inspection_type", "routine", "例行巡检", "routine", 1),
            ("inspection_type", "special", "专项巡检", "special", 2),
            ("inspection_type", "emergency", "应急巡检", "emergency", 3),
            # Inspection plan status
            ("inspection_plan_status", "draft", "草稿", "draft", 1),
            ("inspection_plan_status", "active", "已激活", "active", 2),
            ("inspection_plan_status", "paused", "已暂停", "paused", 3),
            ("inspection_plan_status", "completed", "已完成", "completed", 4),
            ("inspection_plan_status", "cancelled", "已取消", "cancelled", 5),
            # Inspection task status
            ("inspection_task_status", "pending", "待分配", "pending", 1),
            ("inspection_task_status", "assigned", "已分配", "assigned", 2),
            ("inspection_task_status", "in_progress", "进行中", "in_progress", 3),
            ("inspection_task_status", "completed", "已完成", "completed", 4),
            ("inspection_task_status", "cancelled", "已取消", "cancelled", 5),
            ("inspection_task_status", "overdue", "已过期", "overdue", 6),
            # Frequency type
            ("frequency_type", "daily", "每日", "daily", 1),
            ("frequency_type", "weekly", "每周", "weekly", 2),
            ("frequency_type", "monthly", "每月", "monthly", 3),
            ("frequency_type", "quarterly", "每季度", "quarterly", 4),
            ("frequency_type", "yearly", "每年", "yearly", 5),
            ("frequency_type", "custom", "自定义", "custom", 6),
            # Spare part status
            ("spare_part_status", "active", "启用", "active", 1),
            ("spare_part_status", "inactive", "停用", "inactive", 2),
            ("spare_part_status", "obsolete", "淘汰", "obsolete", 3),
            # Warehouse type
            ("warehouse_type", "central", "中心仓库", "central", 1),
            ("warehouse_type", "regional", "区域仓库", "regional", 2),
            ("warehouse_type", "field", "现场仓库", "field", 3),
            ("warehouse_type", "virtual", "虚拟仓库", "virtual", 4),
            # Transaction type (inventory)
            ("transaction_type_in", "purchase_in", "采购入库", "purchase_in", 1),
            ("transaction_type_in", "return_in", "退货入库", "return_in", 2),
            ("transaction_type_in", "transfer_in", "调拨入库", "transfer_in", 3),
            ("transaction_type_in", "adjust_in", "盘盈入库", "adjust_in", 4),
            ("transaction_type_out", "issue_out", "领用出库", "issue_out", 1),
            ("transaction_type_out", "return_out", "退料出库", "return_out", 2),
            ("transaction_type_out", "transfer_out", "调拨出库", "transfer_out", 3),
            ("transaction_type_out", "adjust_out", "盘亏出库", "adjust_out", 4),
            ("transaction_type_out", "scrap_out", "报废出库", "scrap_out", 5),
            # ABC classification
            ("abc_classification", "A", "A类(关键)", "A", 1),
            ("abc_classification", "B", "B类(重要)", "B", 2),
            ("abc_classification", "C", "C类(一般)", "C", 3),
            # Report category
            ("report_category", "device", "设备", "device", 1),
            ("report_category", "workorder", "运维", "workorder", 2),
            ("report_category", "inspection", "巡检", "inspection", 3),
            ("report_category", "energy", "运营", "energy", 4),
            # Boolean
            ("yes_no", "yes", "是", "1", 1),
            ("yes_no", "no", "否", "0", 2),
        ]

        inserted = 0
        for dtype, code, name, val, sort in dicts:
            r = await s.execute(text(
                "SELECT COUNT(*) FROM sys_dict WHERE dict_type=:dt AND dict_code=:c"
            ), {"dt": dtype, "c": code})
            if r.scalar_one() == 0:
                await s.execute(text(
                    "INSERT INTO sys_dict (dict_type,dict_code,dict_name,dict_value,sort_order,status,created_time) "
                    "VALUES (:dt,:c,:n,:v,:s,1,NOW())"
                ), {"dt": dtype, "c": code, "n": name, "v": val, "s": sort})
                inserted += 1

        await s.commit()
        print(f"Inserted {inserted} dictionary entries")

        # Verify
        r = await s.execute(text("SELECT COUNT(*) FROM sys_dict"))
        total = r.scalar_one()
        r = await s.execute(text("SELECT COUNT(DISTINCT dict_type) FROM sys_dict"))
        types = r.scalar_one()
        print(f"Total dict entries: {total}, dict types: {types}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
