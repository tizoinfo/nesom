"""Seed script: create admin user, roles, permissions, and MinIO buckets."""
import asyncio
import uuid
from datetime import datetime

from sqlalchemy import text
from src.core.security import get_password_hash
from src.core.config import settings
from src.database.session import engine


ADMIN_PASSWORD = "admin123"

PERMISSIONS = [
    # device
    ("device:create", "创建设备", "device", "device", "create"),
    ("device:read", "查看设备", "device", "device", "read"),
    ("device:update", "更新设备", "device", "device", "update"),
    ("device:delete", "删除设备", "device", "device", "delete"),
    # workorder
    ("workorder:create", "创建工单", "workorder", "workorder", "create"),
    ("workorder:read", "查看工单", "workorder", "workorder", "read"),
    ("workorder:update", "更新工单", "workorder", "workorder", "update"),
    ("workorder:delete", "删除工单", "workorder", "workorder", "delete"),
    # sparepart
    ("sparepart:create", "创建备件", "sparepart", "sparepart", "create"),
    ("sparepart:read", "查看备件", "sparepart", "sparepart", "read"),
    ("sparepart:update", "更新备件", "sparepart", "sparepart", "update"),
    ("sparepart:delete", "删除备件", "sparepart", "sparepart", "delete"),
    # inspection
    ("inspection:create", "创建巡检", "inspection", "inspection", "create"),
    ("inspection:read", "查看巡检", "inspection", "inspection", "read"),
    ("inspection:update", "更新巡检", "inspection", "inspection", "update"),
    ("inspection:delete", "删除巡检", "inspection", "inspection", "delete"),
    # report
    ("report:read", "查看报表", "report", "report", "read"),
    ("report:execute", "生成报表", "report", "report", "execute"),
    # system
    ("system:config", "系统配置", "system", "config", "manage"),
    ("system:user:manage", "用户管理", "system", "user", "manage"),
    ("system:role:manage", "角色管理", "system", "role", "manage"),
]

# Device types for testing
DEVICE_TYPES = [
    ("DT_INVERTER", "逆变器", "inverter", None, 1),
    ("DT_PANEL", "光伏组件", "panel", None, 2),
    ("DT_TRANSFORMER", "变压器", "transformer", None, 3),
    ("DT_METER", "电表", "meter", None, 4),
    ("DT_WEATHER", "气象站", "weather_station", None, 5),
]


async def seed():
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # ── Admin user ──
        result = await session.execute(text("SELECT id FROM users WHERE username='admin'"))
        existing = result.scalar_one_or_none()
        if existing:
            pw_hash = get_password_hash(ADMIN_PASSWORD)
            await session.execute(
                text("UPDATE users SET password_hash=:ph WHERE username='admin'"),
                {"ph": pw_hash},
            )
            admin_id = existing
            print(f"Admin user updated (id={admin_id})")
        else:
            admin_id = str(uuid.uuid4())
            pw_hash = get_password_hash(ADMIN_PASSWORD)
            await session.execute(
                text(
                    "INSERT INTO users (id, username, email, real_name, password_hash, status, is_superadmin) "
                    "VALUES (:id, :username, :email, :real_name, :ph, 'active', TRUE)"
                ),
                {"id": admin_id, "username": "admin", "email": "admin@nesom.com",
                 "real_name": "系统管理员", "ph": pw_hash},
            )
            print(f"Created admin user (id={admin_id})")

        # ── ROLE_ADMIN ──
        result = await session.execute(text("SELECT id FROM roles WHERE role_code='ROLE_ADMIN'"))
        role_row = result.scalar_one_or_none()
        if not role_row:
            role_id = str(uuid.uuid4())
            await session.execute(
                text("INSERT INTO roles (id, role_code, role_name, description, role_type, is_protected, data_scope) "
                     "VALUES (:id, 'ROLE_ADMIN', '系统管理员', '拥有全部权限', 'system', TRUE, 'all')"),
                {"id": role_id},
            )
            print(f"Created ROLE_ADMIN (id={role_id})")
        else:
            role_id = role_row
            print(f"ROLE_ADMIN exists (id={role_id})")

        # ── ROLE_OPERATOR ──
        result = await session.execute(text("SELECT id FROM roles WHERE role_code='ROLE_OPERATOR'"))
        op_role_row = result.scalar_one_or_none()
        if not op_role_row:
            op_role_id = str(uuid.uuid4())
            await session.execute(
                text("INSERT INTO roles (id, role_code, role_name, description, role_type, is_protected, data_scope) "
                     "VALUES (:id, 'ROLE_OPERATOR', '运维人员', '日常运维操作权限', 'system', TRUE, 'department')"),
                {"id": op_role_id},
            )
            print(f"Created ROLE_OPERATOR (id={op_role_id})")
        else:
            op_role_id = op_role_row

        # ── Permissions ──
        perm_ids = []
        for perm_code, perm_name, module, resource, action in PERMISSIONS:
            result = await session.execute(
                text("SELECT id FROM permissions WHERE perm_code=:pc"), {"pc": perm_code}
            )
            pid = result.scalar_one_or_none()
            if not pid:
                pid = str(uuid.uuid4())
                await session.execute(
                    text("INSERT INTO permissions (id, perm_code, perm_name, module, resource, action, is_system) "
                         "VALUES (:id, :pc, :pn, :mod, :res, :act, TRUE)"),
                    {"id": pid, "pc": perm_code, "pn": perm_name,
                     "mod": module, "res": resource, "act": action},
                )
            perm_ids.append(pid)
        print(f"Ensured {len(perm_ids)} permissions")

        # ── Assign ALL permissions to ROLE_ADMIN ──
        for pid in perm_ids:
            result = await session.execute(
                text("SELECT 1 FROM role_permissions WHERE role_id=:rid AND permission_id=:pid"),
                {"rid": role_id, "pid": pid},
            )
            if not result.scalar_one_or_none():
                await session.execute(
                    text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid)"),
                    {"rid": role_id, "pid": pid},
                )
        print("Assigned all permissions to ROLE_ADMIN")

        # ── Assign read permissions to ROLE_OPERATOR ──
        for pid, (perm_code, *_) in zip(perm_ids, PERMISSIONS):
            if ":read" in perm_code or ":create" in perm_code or ":update" in perm_code:
                result = await session.execute(
                    text("SELECT 1 FROM role_permissions WHERE role_id=:rid AND permission_id=:pid"),
                    {"rid": op_role_id, "pid": pid},
                )
                if not result.scalar_one_or_none():
                    await session.execute(
                        text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid)"),
                        {"rid": op_role_id, "pid": pid},
                    )
        print("Assigned operational permissions to ROLE_OPERATOR")

        # ── Assign ROLE_ADMIN to admin user ──
        result = await session.execute(
            text("SELECT 1 FROM user_roles WHERE user_id=:uid AND role_id=:rid"),
            {"uid": admin_id, "rid": role_id},
        )
        if not result.scalar_one_or_none():
            await session.execute(
                text("INSERT INTO user_roles (user_id, role_id) VALUES (:uid, :rid)"),
                {"uid": admin_id, "rid": role_id},
            )
        print("Admin user has ROLE_ADMIN")

        # ── Test operator user ──
        result = await session.execute(text("SELECT id FROM users WHERE username='operator'"))
        op_user = result.scalar_one_or_none()
        if not op_user:
            op_user_id = str(uuid.uuid4())
            await session.execute(
                text("INSERT INTO users (id, username, email, real_name, password_hash, status, is_superadmin) "
                     "VALUES (:id, 'operator', 'operator@nesom.com', '运维员张三', :ph, 'active', FALSE)"),
                {"id": op_user_id, "ph": get_password_hash("operator123")},
            )
            await session.execute(
                text("INSERT INTO user_roles (user_id, role_id) VALUES (:uid, :rid)"),
                {"uid": op_user_id, "rid": op_role_id},
            )
            print(f"Created operator user (operator / operator123)")
        else:
            print("Operator user exists")

        # ── Device types ──
        for type_code, type_name, category, parent, sort in DEVICE_TYPES:
            result = await session.execute(
                text("SELECT id FROM device_types WHERE type_code=:tc"), {"tc": type_code}
            )
            if not result.scalar_one_or_none():
                await session.execute(
                    text("INSERT INTO device_types (id, type_code, type_name, category, sort_order) "
                         "VALUES (:id, :tc, :tn, :cat, :so)"),
                    {"id": str(uuid.uuid4()), "tc": type_code, "tn": type_name,
                     "cat": category, "so": sort},
                )
        print("Ensured device types")

        # ── Sample devices ──
        result = await session.execute(text("SELECT COUNT(*) FROM devices"))
        dev_count = result.scalar_one()
        if dev_count == 0:
            # Get inverter type id
            result = await session.execute(
                text("SELECT id FROM device_types WHERE type_code='DT_INVERTER'")
            )
            inv_type_id = result.scalar_one()
            result = await session.execute(
                text("SELECT id FROM device_types WHERE type_code='DT_PANEL'")
            )
            panel_type_id = result.scalar_one()

            station_id = str(uuid.uuid4())
            devices = [
                (str(uuid.uuid4()), station_id, "INV-001", "1号逆变器", inv_type_id, "online"),
                (str(uuid.uuid4()), station_id, "INV-002", "2号逆变器", inv_type_id, "online"),
                (str(uuid.uuid4()), station_id, "INV-003", "3号逆变器", inv_type_id, "offline"),
                (str(uuid.uuid4()), station_id, "PNL-001", "A区光伏组件", panel_type_id, "online"),
                (str(uuid.uuid4()), station_id, "PNL-002", "B区光伏组件", panel_type_id, "warning"),
            ]
            for did, sid, code, name, tid, status in devices:
                await session.execute(
                    text("INSERT INTO devices (id, station_id, device_code, device_name, device_type_id, status) "
                         "VALUES (:id, :sid, :code, :name, :tid, :st)"),
                    {"id": did, "sid": sid, "code": code, "name": name, "tid": tid, "st": status},
                )
            print(f"Created {len(devices)} sample devices")
        else:
            print(f"Devices already exist ({dev_count})")

        # ── Sample work orders ──
        result = await session.execute(text("SELECT COUNT(*) FROM work_orders"))
        wo_count = result.scalar_one()
        if wo_count == 0:
            result = await session.execute(text("SELECT id FROM devices LIMIT 2"))
            device_ids = [r[0] for r in result.fetchall()]
            station_id_r = await session.execute(text("SELECT station_id FROM devices LIMIT 1"))
            wo_station_id = station_id_r.scalar_one_or_none() or str(uuid.uuid4())
            orders = [
                ("WO-20260401-001", "repair", "逆变器功率异常检修", "1号逆变器输出功率持续偏低，需检修", "pending", "high"),
                ("WO-20260401-002", "maintenance", "光伏组件清洁维护", "A区光伏组件表面积灰严重，需清洁", "in_progress", "medium"),
                ("WO-20260402-001", "inspection", "变压器例行巡检", "季度例行巡检任务", "completed", "low"),
            ]
            for i, (code, wtype, title, desc, status, priority) in enumerate(orders):
                dev_id = device_ids[i % len(device_ids)] if device_ids else None
                await session.execute(
                    text("INSERT INTO work_orders (id, work_order_no, work_order_type, title, description, "
                         "status, priority, station_id, device_id, reported_by, reported_by_name) "
                         "VALUES (:id, :code, :wt, :title, :desc, :st, :pri, :sid, :did, :rb, :rbn)"),
                    {"id": str(uuid.uuid4()), "code": code, "wt": wtype, "title": title,
                     "desc": desc, "st": status, "pri": priority, "sid": wo_station_id,
                     "did": dev_id, "rb": admin_id, "rbn": "系统管理员"},
                )
            print(f"Created {len(orders)} sample work orders")
        else:
            print(f"Work orders already exist ({wo_count})")

        await session.commit()
        print("\n=== Seed complete ===")
        print(f"Admin:    admin / {ADMIN_PASSWORD}")
        print(f"Operator: operator / operator123")

    # ── MinIO buckets ──
    try:
        from minio import Minio
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        for bucket in ["nesom-avatars", "nesom-documents", "nesom-reports", "nesom-attachments"]:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                print(f"Created MinIO bucket: {bucket}")
            else:
                print(f"MinIO bucket exists: {bucket}")
    except Exception as e:
        print(f"MinIO setup failed: {e}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
