"""Sync database schema: create missing tables and add missing columns, then seed test data."""
import asyncio
import uuid
from datetime import datetime, date, timedelta
import random

from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.core.security import get_password_hash
from src.database.base import Base

# Import ALL models so Base.metadata knows about them
from src.modules.auth.models import User, Role, Permission, RefreshToken  # noqa
from src.modules.device.models import Device, DeviceType, DeviceMetric, DeviceAlert, DeviceThreshold  # noqa
from src.modules.workorder.models import WorkOrder, WorkOrderDetail, WorkOrderStatusHistory, WorkOrderTemplate  # noqa
from src.modules.inspection.models import InspectionPlan, InspectionTask, InspectionResult  # noqa
from src.modules.sparepart.models import SparePartCategory, SparePart  # noqa
from src.modules.sparepart.inventory_models import Warehouse, InventoryDetail, InventorySnapshot, InventoryReservation  # noqa
from src.modules.report.models import ReportTemplate, ReportExecution, StatisticsCache  # noqa
from src.modules.system.models import SysConfig, SysDict, SysNoticeTemplate  # noqa


async def sync_schema():
    """Create all missing tables using SQLAlchemy metadata."""
    # Use a sync-compatible engine for DDL
    sync_url = settings.DATABASE_URL.replace("aiomysql", "pymysql")
    from sqlalchemy import create_engine
    engine = create_engine(sync_url, echo=False)
    Base.metadata.create_all(engine, checkfirst=True)
    engine.dispose()
    print("Schema sync complete - all missing tables created")

    # Add missing columns to existing tables
    async_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Add deleted_at to devices if missing
        try:
            await session.execute(text("SELECT deleted_at FROM devices LIMIT 0"))
        except Exception:
            await session.rollback()
            await session.execute(text("ALTER TABLE devices ADD COLUMN deleted_at DATETIME NULL"))
            await session.commit()
            print("Added deleted_at column to devices")

        # Add archived_at to work_orders if missing
        try:
            await session.execute(text("SELECT archived_at FROM work_orders LIMIT 0"))
        except Exception:
            await session.rollback()
            await session.execute(text("ALTER TABLE work_orders ADD COLUMN archived_at DATETIME NULL"))
            await session.commit()
            print("Added archived_at column to work_orders")

        # Create audit_logs table if missing (referenced by audit worker)
        try:
            await session.execute(text("SELECT 1 FROM audit_logs LIMIT 0"))
        except Exception:
            await session.rollback()
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id VARCHAR(36) NULL,
                    username VARCHAR(100) NULL,
                    action VARCHAR(50) NOT NULL,
                    resource_type VARCHAR(50) NOT NULL,
                    resource_id VARCHAR(100) NULL,
                    old_value JSON NULL,
                    new_value JSON NULL,
                    ip_address VARCHAR(45) NULL,
                    user_agent VARCHAR(500) NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_audit_user (user_id),
                    INDEX idx_audit_action (action),
                    INDEX idx_audit_resource (resource_type, resource_id),
                    INDEX idx_audit_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            await session.commit()
            print("Created audit_logs table")

    await async_engine.dispose()


def uid():
    return str(uuid.uuid4())


STATION_ID = uid()
ADMIN_ID = None  # will be set during seed


async def seed_data():
    """Insert comprehensive test data."""
    from src.database.session import engine
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    global ADMIN_ID

    async with async_session() as s:
        # Get admin user id
        r = await s.execute(text("SELECT id FROM users WHERE username='admin'"))
        ADMIN_ID = r.scalar_one_or_none()
        if not ADMIN_ID:
            ADMIN_ID = uid()
            pw = get_password_hash("admin123")
            await s.execute(text(
                "INSERT INTO users (id,username,email,real_name,password_hash,status,is_superadmin) "
                "VALUES (:id,'admin','admin@nesom.com','系统管理员',:pw,'active',TRUE)"
            ), {"id": ADMIN_ID, "pw": pw})
            print(f"Created admin user: {ADMIN_ID}")

        # ── Device Types ──
        device_types = [
            ("DT_INVERTER", "逆变器", "inverter"),
            ("DT_PANEL", "光伏组件", "panel"),
            ("DT_TRANSFORMER", "变压器", "transformer"),
            ("DT_METER", "电表", "meter"),
            ("DT_WEATHER", "气象站", "weather_station"),
            ("DT_COMBINER", "汇流箱", "combiner"),
            ("DT_TRACKER", "跟踪支架", "tracker"),
        ]
        dt_ids = {}
        for i, (code, name, cat) in enumerate(device_types):
            r = await s.execute(text("SELECT id FROM device_types WHERE type_code=:c"), {"c": code})
            eid = r.scalar_one_or_none()
            if not eid:
                eid = uid()
                await s.execute(text(
                    "INSERT INTO device_types (id,type_code,type_name,category,sort_order) VALUES (:id,:c,:n,:cat,:s)"
                ), {"id": eid, "c": code, "n": name, "cat": cat, "s": i})
            dt_ids[code] = eid
        print(f"Ensured {len(device_types)} device types")

        # ── Devices (20+) ──
        r = await s.execute(text("SELECT COUNT(*) FROM devices"))
        if r.scalar_one() < 10:
            devices_data = [
                ("INV-001", "1号逆变器", "DT_INVERTER", "online", 92),
                ("INV-002", "2号逆变器", "DT_INVERTER", "online", 88),
                ("INV-003", "3号逆变器", "DT_INVERTER", "offline", 45),
                ("INV-004", "4号逆变器", "DT_INVERTER", "warning", 72),
                ("INV-005", "5号逆变器", "DT_INVERTER", "online", 95),
                ("PNL-A01", "A区光伏组件", "DT_PANEL", "online", 90),
                ("PNL-A02", "A区光伏组件2", "DT_PANEL", "online", 87),
                ("PNL-B01", "B区光伏组件", "DT_PANEL", "warning", 65),
                ("PNL-B02", "B区光伏组件2", "DT_PANEL", "online", 82),
                ("PNL-C01", "C区光伏组件", "DT_PANEL", "online", 91),
                ("TRF-001", "1号变压器", "DT_TRANSFORMER", "online", 96),
                ("TRF-002", "2号变压器", "DT_TRANSFORMER", "online", 93),
                ("MTR-001", "主电表", "DT_METER", "online", 100),
                ("MTR-002", "副电表", "DT_METER", "online", 98),
                ("WS-001", "气象站A", "DT_WEATHER", "online", 100),
                ("WS-002", "气象站B", "DT_WEATHER", "offline", 0),
                ("CMB-001", "1号汇流箱", "DT_COMBINER", "online", 85),
                ("CMB-002", "2号汇流箱", "DT_COMBINER", "warning", 70),
                ("TRK-001", "跟踪支架1", "DT_TRACKER", "online", 88),
                ("TRK-002", "跟踪支架2", "DT_TRACKER", "online", 90),
            ]
            # Delete old devices first
            await s.execute(text("DELETE FROM device_metrics"))
            await s.execute(text("DELETE FROM device_alerts"))
            await s.execute(text("DELETE FROM devices"))
            dev_ids = []
            for code, name, dt_code, status, health in devices_data:
                did = uid()
                dev_ids.append(did)
                await s.execute(text(
                    "INSERT INTO devices (id,station_id,device_type_id,device_code,device_name,status,health_score,"
                    "manufacturer,model,rated_power) "
                    "VALUES (:id,:sid,:tid,:code,:name,:st,:hs,:mfr,:mdl,:rp)"
                ), {"id": did, "sid": STATION_ID, "tid": dt_ids[dt_code], "code": code,
                    "name": name, "st": status, "hs": health,
                    "mfr": random.choice(["华为", "阳光电源", "锦浪", "固德威", "特变电工"]),
                    "mdl": f"SG{random.randint(50,250)}KTL",
                    "rp": random.choice([50, 100, 150, 200, 250])})
            print(f"Created {len(devices_data)} devices")

            # ── Device Metrics ──
            now = datetime.utcnow()
            metrics_count = 0
            for did in dev_ids[:5]:  # metrics for first 5 devices
                for h in range(24):
                    t = now - timedelta(hours=h)
                    for mt, unit, vmin, vmax in [
                        ("power", "kW", 10, 200), ("voltage", "V", 350, 420),
                        ("current", "A", 5, 50), ("temperature", "°C", 25, 65),
                    ]:
                        await s.execute(text(
                            "INSERT INTO device_metrics (device_id,metric_type,metric_value,metric_unit,collected_at,source) "
                            "VALUES (:did,:mt,:mv,:mu,:ca,'direct')"
                        ), {"did": did, "mt": mt, "mv": round(random.uniform(vmin, vmax), 2),
                            "mu": unit, "ca": t})
                        metrics_count += 1
            print(f"Created {metrics_count} device metrics")

            # ── Device Alerts ──
            alert_data = [
                (dev_ids[2], "ALT-001", "fault", "error", "逆变器离线告警", "3号逆变器通信中断超过30分钟", "active"),
                (dev_ids[3], "ALT-002", "performance", "warning", "功率输出偏低", "4号逆变器输出功率低于额定值60%", "active"),
                (dev_ids[7], "ALT-003", "performance", "warning", "组件效率下降", "B区光伏组件发电效率下降15%", "acknowledged"),
                (dev_ids[15], "ALT-004", "communication", "error", "气象站离线", "气象站B通信中断", "active"),
                (dev_ids[17], "ALT-005", "temperature", "warning", "汇流箱温度偏高", "2号汇流箱温度超过55°C", "resolved"),
                (dev_ids[0], "ALT-006", "performance", "info", "逆变器效率波动", "1号逆变器效率波动超过5%", "closed"),
            ]
            for did, code, atype, level, title, msg, status in alert_data:
                await s.execute(text(
                    "INSERT INTO device_alerts (device_id,alert_code,alert_type,alert_level,alert_title,"
                    "alert_message,status,start_time) VALUES (:did,:c,:at,:al,:t,:m,:s,:st)"
                ), {"did": did, "c": code, "at": atype, "al": level, "t": title,
                    "m": msg, "s": status, "st": now - timedelta(hours=random.randint(1, 48))})
            print(f"Created {len(alert_data)} device alerts")
        else:
            # Get existing device ids
            r = await s.execute(text("SELECT id FROM devices"))
            dev_ids = [row[0] for row in r.fetchall()]
            print(f"Devices already exist ({len(dev_ids)})")

        # ── Work Orders (10+) ──
        r = await s.execute(text("SELECT COUNT(*) FROM work_orders"))
        if r.scalar_one() < 5:
            await s.execute(text("DELETE FROM work_orders"))
            wo_data = [
                ("WO-20260401-001", "repair", "逆变器功率异常检修", "3号逆变器输出功率持续偏低需检修", "pending", "high"),
                ("WO-20260401-002", "maintenance", "光伏组件清洁维护", "A区光伏组件表面积灰严重需清洁", "in_progress", "medium"),
                ("WO-20260402-001", "inspection", "变压器例行巡检", "季度例行巡检任务", "completed", "low"),
                ("WO-20260402-002", "fault", "气象站通信故障", "气象站B通信模块故障需更换", "assigned", "high"),
                ("WO-20260403-001", "repair", "汇流箱温度异常处理", "2号汇流箱散热风扇故障", "in_progress", "high"),
                ("WO-20260403-002", "maintenance", "跟踪支架润滑保养", "跟踪支架定期润滑保养", "pending", "low"),
                ("WO-20260404-001", "fault", "逆变器离线故障排查", "3号逆变器通信中断故障排查", "draft", "emergency"),
                ("WO-20260404-002", "inspection", "电缆线路巡检", "高压电缆线路定期巡检", "completed", "medium"),
                ("WO-20260405-001", "maintenance", "逆变器滤网清洁", "所有逆变器进风口滤网清洁", "pending", "medium"),
                ("WO-20260405-002", "repair", "电表校准", "主电表年度校准", "completed", "low"),
            ]
            for code, wtype, title, desc, status, priority in wo_data:
                did = random.choice(dev_ids) if dev_ids else None
                await s.execute(text(
                    "INSERT INTO work_orders (id,work_order_no,work_order_type,title,description,"
                    "status,priority,station_id,device_id,reported_by,reported_by_name) "
                    "VALUES (:id,:c,:wt,:t,:d,:s,:p,:sid,:did,:rb,:rbn)"
                ), {"id": uid(), "c": code, "wt": wtype, "t": title, "d": desc,
                    "s": status, "p": priority, "sid": STATION_ID,
                    "did": did, "rb": ADMIN_ID, "rbn": "系统管理员"})
            print(f"Created {len(wo_data)} work orders")

        # ── Spare Part Categories ──
        r = await s.execute(text("SELECT COUNT(*) FROM spare_part_categories"))
        if r.scalar_one() == 0:
            cats = [
                ("CAT-ELEC", "电气元件", 1), ("CAT-MECH", "机械部件", 2),
                ("CAT-COMM", "通信设备", 3), ("CAT-TOOL", "工具耗材", 4),
            ]
            cat_ids = {}
            for code, name, sort in cats:
                cid = uid()
                cat_ids[code] = cid
                await s.execute(text(
                    "INSERT INTO spare_part_categories (id,category_code,category_name,level,sort_order,is_leaf,unit) "
                    "VALUES (:id,:c,:n,1,:s,TRUE,'piece')"
                ), {"id": cid, "c": code, "n": name, "s": sort})
            print(f"Created {len(cats)} spare part categories")

            # ── Spare Parts ──
            parts = [
                ("SP-INV-IGBT", "IGBT模块", "CAT-ELEC", "FF600R12ME4", "英飞凌", 5, 3, 2, 12800),
                ("SP-INV-FAN", "逆变器散热风扇", "CAT-MECH", "W2E200-HK38-01", "ebm-papst", 20, 10, 5, 450),
                ("SP-INV-FUSE", "直流熔断器", "CAT-ELEC", "170M6467", "Bussmann", 50, 20, 10, 280),
                ("SP-PNL-CONN", "MC4连接器", "CAT-ELEC", "MC4-30A", "史陶比尔", 200, 50, 30, 15),
                ("SP-PNL-BYPASS", "旁路二极管", "CAT-ELEC", "15SQ045", "通用", 100, 30, 20, 8),
                ("SP-TRF-OIL", "变压器油(桶)", "CAT-MECH", "25号变压器油", "昆仑", 10, 3, 2, 2800),
                ("SP-COMM-MOD", "4G通信模块", "CAT-COMM", "EC20-CE", "移远", 15, 5, 3, 350),
                ("SP-COMM-ANT", "天线", "CAT-COMM", "SMA-5dBi", "通用", 30, 10, 5, 45),
                ("SP-TOOL-MULTI", "万用表", "CAT-TOOL", "Fluke-87V", "福禄克", 5, 2, 1, 2500),
                ("SP-TOOL-CLAMP", "钳形电流表", "CAT-TOOL", "Fluke-376FC", "福禄克", 3, 1, 1, 3800),
                ("SP-CMB-SPD", "防雷器(SPD)", "CAT-ELEC", "T2-40kA", "菲尼克斯", 30, 10, 5, 680),
                ("SP-TRK-MOTOR", "跟踪电机", "CAT-MECH", "57BYG250", "通用", 8, 3, 2, 1200),
            ]
            for code, name, cat, spec, brand, cur, min_s, safety, price in parts:
                await s.execute(text(
                    "INSERT INTO spare_parts (id,spare_part_code,spare_part_name,category_id,specification,"
                    "brand,unit,current_stock,available_stock,min_stock_level,safety_stock_level,"
                    "standard_cost,last_purchase_price,status) "
                    "VALUES (:id,:c,:n,:cid,:spec,:brand,'piece',:cur,:cur,:min,:safe,:price,:price,'active')"
                ), {"id": uid(), "c": code, "n": name, "cid": cat_ids[cat], "spec": spec,
                    "brand": brand, "cur": cur, "min": min_s, "safe": safety, "price": price})
            print(f"Created {len(parts)} spare parts")

        # ── Warehouses ──
        r = await s.execute(text("SELECT COUNT(*) FROM warehouses"))
        if r.scalar_one() == 0:
            whs = [
                ("WH-CENTRAL", "中心仓库", "central"), ("WH-FIELD-A", "现场仓库A", "field"),
                ("WH-FIELD-B", "现场仓库B", "field"),
            ]
            for code, name, wtype in whs:
                await s.execute(text(
                    "INSERT INTO warehouses (id,warehouse_code,warehouse_name,warehouse_type,is_active) "
                    "VALUES (:id,:c,:n,:t,TRUE)"
                ), {"id": uid(), "c": code, "n": name, "t": wtype})
            print(f"Created {len(whs)} warehouses")

        # ── Inspection Plans & Tasks ──
        r = await s.execute(text("SELECT COUNT(*) FROM inspection_plans"))
        if r.scalar_one() == 0:
            plans = [
                ("IP-DAILY-001", "每日设备巡检", "routine", "daily", "active"),
                ("IP-WEEKLY-001", "每周电气检查", "routine", "weekly", "active"),
                ("IP-MONTHLY-001", "月度综合巡检", "routine", "monthly", "active"),
                ("IP-SPECIAL-001", "暴风雨后特殊巡检", "special", "custom", "completed"),
                ("IP-QUARTERLY-001", "季度安全检查", "routine", "quarterly", "draft"),
            ]
            today = date.today()
            for code, name, itype, freq, status in plans:
                pid = uid()
                await s.execute(text(
                    "INSERT INTO inspection_plans (id,plan_code,plan_name,inspection_type,frequency_type,"
                    "start_date,status,created_by,created_by_name,priority) "
                    "VALUES (:id,:c,:n,:it,:ft,:sd,:s,:cb,:cbn,'medium')"
                ), {"id": pid, "c": code, "n": name, "it": itype, "ft": freq,
                    "sd": today - timedelta(days=30), "s": status,
                    "cb": ADMIN_ID, "cbn": "系统管理员"})

                # Create tasks for active plans
                if status == "active":
                    for d in range(5):
                        task_date = today - timedelta(days=d)
                        task_status = "completed" if d > 0 else "in_progress"
                        await s.execute(text(
                            "INSERT INTO inspection_tasks (id,task_code,plan_id,scheduled_date,status,"
                            "total_checkpoints,completed_checkpoints,priority) "
                            "VALUES (:id,:c,:pid,:sd,:s,:tc,:cc,'medium')"
                        ), {"id": uid(), "c": f"{code}-T{d+1:03d}",
                            "pid": pid, "sd": task_date, "s": task_status,
                            "tc": random.randint(5, 15),
                            "cc": random.randint(3, 15) if d > 0 else random.randint(1, 5)})
            print(f"Created {len(plans)} inspection plans with tasks")

        # ── Report Templates ──
        r = await s.execute(text("SELECT COUNT(*) FROM report_templates"))
        if r.scalar_one() == 0:
            reports = [
                ("RPT-DAILY", "日报", "运营", "daily_report"),
                ("RPT-DEVICE", "设备运行报表", "设备", "device_report"),
                ("RPT-WORKORDER", "工单统计报表", "运维", "workorder_report"),
                ("RPT-ENERGY", "发电量统计", "运营", "energy_report"),
                ("RPT-ALARM", "告警统计报表", "设备", "alarm_report"),
            ]
            for code, name, cat, sub in reports:
                await s.execute(text(
                    "INSERT INTO report_templates (id,template_code,template_name,category,sub_category,"
                    "data_source_type,data_source_config,parameter_definitions,column_definitions,"
                    "visualization_config,layout_config,export_config,created_by,is_active,sort_order) "
                    "VALUES (:id,:c,:n,:cat,:sub,'sql','{}','[]','[]','{}','{}','{}', :cb,TRUE,0)"
                ), {"id": uid(), "c": code, "n": name, "cat": cat, "sub": sub, "cb": ADMIN_ID})
            print(f"Created {len(reports)} report templates")

        # ── System Config ──
        r = await s.execute(text("SELECT COUNT(*) FROM sys_config"))
        if r.scalar_one() == 0:
            configs = [
                ("system.name", "NESOM新能源运维管理系统", "STRING", "SYSTEM"),
                ("system.version", "1.0.0", "STRING", "SYSTEM"),
                ("alert.email.enabled", "true", "BOOLEAN", "ALERT"),
                ("alert.sms.enabled", "false", "BOOLEAN", "ALERT"),
                ("device.heartbeat.timeout", "300", "NUMBER", "DEVICE"),
                ("workorder.auto_assign", "true", "BOOLEAN", "WORKORDER"),
                ("inspection.photo_required", "true", "BOOLEAN", "INSPECTION"),
                ("report.retention_days", "365", "NUMBER", "REPORT"),
            ]
            for key, val, ctype, module in configs:
                await s.execute(text(
                    "INSERT INTO sys_config (config_key,config_value,config_type,module,created_time) "
                    "VALUES (:k,:v,:t,:m,NOW())"
                ), {"k": key, "v": val, "t": ctype, "m": module})
            print(f"Created {len(configs)} system configs")

        # ── System Dict ──
        r = await s.execute(text("SELECT COUNT(*) FROM sys_dict"))
        if r.scalar_one() == 0:
            dicts = [
                ("device_status", "online", "在线", "online"),
                ("device_status", "offline", "离线", "offline"),
                ("device_status", "warning", "告警", "warning"),
                ("device_status", "maintenance", "维护中", "maintenance"),
                ("workorder_type", "repair", "维修", "repair"),
                ("workorder_type", "maintenance", "保养", "maintenance"),
                ("workorder_type", "inspection", "巡检", "inspection"),
                ("workorder_type", "fault", "故障", "fault"),
                ("priority", "low", "低", "low"),
                ("priority", "medium", "中", "medium"),
                ("priority", "high", "高", "high"),
                ("priority", "emergency", "紧急", "emergency"),
            ]
            for dtype, code, name, val in dicts:
                await s.execute(text(
                    "INSERT INTO sys_dict (dict_type,dict_code,dict_name,dict_value,status,created_time) "
                    "VALUES (:dt,:c,:n,:v,1,NOW())"
                ), {"dt": dtype, "c": code, "n": name, "v": val})
            print(f"Created {len(dicts)} dict entries")

        # ── MinIO buckets ──
        try:
            from minio import Minio
            client = Minio(settings.MINIO_ENDPOINT, access_key=settings.MINIO_ACCESS_KEY,
                           secret_key=settings.MINIO_SECRET_KEY, secure=settings.MINIO_SECURE)
            for b in ["nesom-avatars", "nesom-documents", "nesom-reports", "nesom-attachments"]:
                if not client.bucket_exists(b):
                    client.make_bucket(b)
                    print(f"Created bucket: {b}")
        except Exception as e:
            print(f"MinIO: {e}")

        await s.commit()
        print("\n=== Seed complete ===")
        print("Admin: admin / admin123")

    await engine.dispose()


async def main():
    await sync_schema()
    await seed_data()


if __name__ == "__main__":
    asyncio.run(main())
