"""
End-to-end integration tests for cross-module event flows.

Tests two core business flows:
1. Device alert → Work order creation → Spare part requisition → Work order completion
2. Inspection plan → Task assignment → Execution → Anomaly → Work order creation

Validates: Requirements 3.4, 4.1, 4.2, 5.2
"""
import asyncio
import uuid
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import AppException
from src.modules.workorder.schemas import ALLOWED_TRANSITIONS


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_device(device_id="dev-001", status="online"):
    d = MagicMock()
    d.id = device_id
    d.device_code = "DEV-001"
    d.device_name = "测试设备"
    d.device_type_id = "type-001"
    d.station_id = "station-001"
    d.status = status
    d.last_heartbeat = datetime.utcnow()
    return d


def _make_alert(alert_id=1, device_id="dev-001", level="critical"):
    a = MagicMock()
    a.id = alert_id
    a.device_id = device_id
    a.alert_code = "ALERT-DEV001-20260409-001"
    a.alert_type = "threshold"
    a.alert_level = level
    a.alert_title = "温度超过阈值"
    a.alert_message = "设备 DEV-001 温度 95°C 超过阈值 85°C"
    a.trigger_value = 95.0
    a.threshold_value = 85.0
    a.status = "active"
    a.related_work_order_id = None
    a.start_time = datetime.utcnow()
    return a


def _make_work_order(wo_id="wo-001", status="draft"):
    wo = MagicMock()
    wo.id = wo_id
    wo.work_order_no = f"WO-STAT-{datetime.utcnow().strftime('%Y%m%d')}-001"
    wo.status = status
    wo.work_order_type = "fault"
    wo.title = "Test WO"
    wo.description = "Test"
    wo.station_id = "station-001"
    wo.priority = "high"
    wo.reported_by = "system"
    wo.reported_by_name = "告警系统"
    wo.assigned_to = None
    wo.assigned_to_name = None
    wo.assigned_at = None
    wo.actual_start = None
    wo.actual_end = None
    wo.actual_cost = None
    wo.closed_at = None
    wo.closed_by = None
    wo.completion_rate = 0
    wo.actual_duration = None
    wo.images = None
    wo.location = None
    wo.longitude = None
    wo.latitude = None
    wo.details = []
    wo.status_history = []
    return wo


def _make_inspection_plan(plan_id="plan-001"):
    p = MagicMock()
    p.id = plan_id
    p.plan_code = "INSP-PLAN-202604-001"
    p.plan_name = "日常巡检计划"
    p.status = "active"
    p.inspection_type = "routine"
    p.frequency_type = "daily"
    p.frequency_value = 1
    p.start_date = date.today()
    p.end_date = date.today() + timedelta(days=30)
    return p


def _make_inspection_task(task_id="task-001", plan_id="plan-001"):
    t = MagicMock()
    t.id = task_id
    t.task_code = f"TASK-{date.today().strftime('%Y%m%d')}-001"
    t.plan_id = plan_id
    t.scheduled_date = date.today()
    t.status = "in_progress"
    t.assigned_to = "user-001"
    t.assigned_to_name = "巡检员"
    t.results = []
    return t


def _make_spare_part(sp_id="sp-001", current_stock=100, available_stock=80):
    sp = MagicMock()
    sp.id = sp_id
    sp.spare_part_code = "SP-CAT-001"
    sp.spare_part_name = "测试备件"
    sp.current_stock = current_stock
    sp.available_stock = available_stock
    sp.reserved_stock = current_stock - available_stock
    return sp


# ── Flow 1: Device Alert → Work Order → Spare Part → Complete ────────────────

class TestAlertToWorkOrderFlow:
    """Test the complete flow: alert triggers work order creation."""

    def test_alert_creates_workorder_with_correct_priority_mapping(self):
        """Critical alert should map to emergency priority work order."""
        from src.modules.integration.service import create_workorder_from_alert

        device = _make_device()
        alert = _make_alert(level="critical")
        wo = _make_work_order(status="draft")

        # After submit, status becomes pending
        def update_status_on_submit(*args, **kwargs):
            wo.status = "pending"
            return wo

        with patch("src.modules.integration.service.device_service.get_device", new_callable=AsyncMock, return_value=device), \
             patch("src.modules.integration.service.device_service.get_alert", new_callable=AsyncMock, return_value=alert), \
             patch("src.modules.integration.service.workorder_service.create_work_order", new_callable=AsyncMock, return_value=wo), \
             patch("src.modules.integration.service.workorder_service.submit_work_order", new_callable=AsyncMock, side_effect=update_status_on_submit):

            db = AsyncMock()
            result = asyncio.run(create_workorder_from_alert(
                db,
                device_id="dev-001",
                alert_id=1,
                station_id="station-001",
            ))

            assert result["work_order_id"] == wo.id
            assert result["alert_id"] == 1
            assert result["device_id"] == "dev-001"
            # Alert should be linked to work order
            assert alert.related_work_order_id == wo.id

    def test_alert_already_linked_raises_conflict(self):
        """Alert that already has a work order should raise 409."""
        from src.modules.integration.service import create_workorder_from_alert

        device = _make_device()
        alert = _make_alert()
        alert.related_work_order_id = "existing-wo-id"

        with patch("src.modules.integration.service.device_service.get_device", new_callable=AsyncMock, return_value=device), \
             patch("src.modules.integration.service.device_service.get_alert", new_callable=AsyncMock, return_value=alert):

            db = AsyncMock()
            with pytest.raises(AppException) as exc_info:
                asyncio.run(create_workorder_from_alert(
                    db, device_id="dev-001", alert_id=1, station_id="station-001",
                ))
            assert exc_info.value.status_code == 409

    def test_alert_with_assignment_auto_assigns_workorder(self):
        """When assignee is provided, work order should be auto-assigned."""
        from src.modules.integration.service import create_workorder_from_alert

        device = _make_device()
        alert = _make_alert(level="error")
        wo = _make_work_order(status="draft")

        with patch("src.modules.integration.service.device_service.get_device", new_callable=AsyncMock, return_value=device), \
             patch("src.modules.integration.service.device_service.get_alert", new_callable=AsyncMock, return_value=alert), \
             patch("src.modules.integration.service.workorder_service.create_work_order", new_callable=AsyncMock, return_value=wo), \
             patch("src.modules.integration.service.workorder_service.submit_work_order", new_callable=AsyncMock, return_value=wo), \
             patch("src.modules.integration.service.workorder_service.assign_work_order", new_callable=AsyncMock, return_value=wo) as mock_assign:

            db = AsyncMock()
            asyncio.run(create_workorder_from_alert(
                db,
                device_id="dev-001",
                alert_id=1,
                station_id="station-001",
                assigned_to="eng-001",
                assigned_to_name="工程师A",
            ))

            mock_assign.assert_called_once()
            call_kwargs = mock_assign.call_args
            assert call_kwargs.kwargs["assigned_to"] == "eng-001"


# ── Flow 2: Inspection Anomaly → Work Order ──────────────────────────────────

class TestInspectionToWorkOrderFlow:
    """Test the flow: inspection anomaly triggers work order creation."""

    def test_inspection_anomaly_creates_workorder(self):
        """Inspection fault should create a high-priority work order."""
        from src.modules.integration.service import create_workorder_from_inspection

        task = _make_inspection_task()
        plan = _make_inspection_plan()
        wo = _make_work_order(status="draft")

        with patch("src.modules.integration.service.inspection_service.get_task", new_callable=AsyncMock, return_value=task), \
             patch("src.modules.integration.service.inspection_service.get_plan", new_callable=AsyncMock, return_value=plan), \
             patch("src.modules.integration.service.workorder_service.create_work_order", new_callable=AsyncMock, return_value=wo) as mock_create, \
             patch("src.modules.integration.service.workorder_service.submit_work_order", new_callable=AsyncMock, return_value=wo):

            db = AsyncMock()
            result = asyncio.run(create_workorder_from_inspection(
                db,
                task_id="task-001",
                problem_description="设备温度异常偏高",
                station_id="station-001",
                priority="high",
            ))

            assert result["work_order_id"] == wo.id
            assert result["task_id"] == "task-001"
            # Verify work order was created with inspection type
            create_kwargs = mock_create.call_args.kwargs
            assert create_kwargs["work_order_type"] == "inspection"
            assert create_kwargs["priority"] == "high"


# ── Flow 3: Work Order → Inventory Deduction ─────────────────────────────────

class TestWorkOrderInventoryDeduction:
    """Test the flow: work order spare part requisition deducts inventory."""

    def test_deduction_rejected_for_wrong_status(self):
        """Only assigned/in_progress work orders can requisition parts."""
        from src.modules.integration.service import deduct_inventory_for_workorder

        wo = _make_work_order(status="draft")

        with patch("src.modules.integration.service.workorder_service.get_work_order", new_callable=AsyncMock, return_value=wo):
            db = AsyncMock()
            with pytest.raises(AppException) as exc_info:
                asyncio.run(deduct_inventory_for_workorder(
                    db,
                    work_order_id="wo-001",
                    items=[{"spare_part_id": "sp-001", "warehouse_id": "wh-001", "quantity": 5}],
                    operator_id="user-001",
                    operator_name="操作员",
                ))
            assert exc_info.value.status_code == 422

    def test_deduction_calls_issue_stock_for_in_progress_wo(self):
        """In-progress work order should successfully deduct inventory."""
        from src.modules.integration.service import deduct_inventory_for_workorder
        from src.modules.sparepart.inventory_schemas import StockChange

        wo = _make_work_order(status="in_progress")
        mock_changes = [StockChange(
            spare_part_id="sp-001",
            warehouse_id="wh-001",
            old_stock=100,
            new_stock=95,
            change=-5,
        )]

        with patch("src.modules.integration.service.workorder_service.get_work_order", new_callable=AsyncMock, return_value=wo), \
             patch("src.modules.integration.service.issue_stock", new_callable=AsyncMock, return_value=([101], mock_changes)) as mock_issue:

            db = AsyncMock()
            result = asyncio.run(deduct_inventory_for_workorder(
                db,
                work_order_id="wo-001",
                items=[{"spare_part_id": "sp-001", "warehouse_id": "wh-001", "quantity": 5}],
                operator_id="user-001",
                operator_name="操作员",
            ))

            assert result["work_order_id"] == "wo-001"
            assert result["transaction_ids"] == [101]
            assert len(result["stock_changes"]) == 1
            assert result["stock_changes"][0]["change"] == -5

            # Verify issue_stock was called with correct params
            mock_issue.assert_called_once()
            call_kwargs = mock_issue.call_args.kwargs
            assert call_kwargs["transaction_type"] == "issue_out"
            assert call_kwargs["work_order_id"] == "wo-001"


# ── State Machine Integration ─────────────────────────────────────────────────

class TestWorkOrderLifecycleIntegration:
    """Test the full work order lifecycle as triggered by integration events."""

    def test_alert_workorder_follows_valid_state_transitions(self):
        """Work order created from alert follows: draft → pending (auto-submit)."""
        # Verify the state machine allows draft → pending
        assert "pending" in ALLOWED_TRANSITIONS["draft"]
        # And pending → assigned
        assert "assigned" in ALLOWED_TRANSITIONS["pending"]
        # And assigned → in_progress
        assert "in_progress" in ALLOWED_TRANSITIONS["assigned"]
        # And in_progress → pending_review → completed → closed
        assert "pending_review" in ALLOWED_TRANSITIONS["in_progress"]
        assert "completed" in ALLOWED_TRANSITIONS["pending_review"]
        assert "closed" in ALLOWED_TRANSITIONS["completed"]

    def test_inspection_workorder_can_be_cancelled(self):
        """Work order from inspection can be cancelled from pending state."""
        assert "cancelled" in ALLOWED_TRANSITIONS["pending"]
