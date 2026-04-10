"""
Property-based tests for work order state machine.

Property 3: Work Order State Machine Legality
For any work order status change, only transitions allowed by the state machine
should succeed.

Validates: Requirements 4.2
Feature: nesom-development, Property 3: Work Order State Machine Legality
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from src.modules.workorder.schemas import ALLOWED_TRANSITIONS, VALID_STATUSES
from src.modules.workorder import service as wo_service
from src.core.exceptions import AppException


ALL_STATUSES = list(VALID_STATUSES)


def _make_work_order(status: str = "draft", work_order_id: str = "wo-001"):
    """Create a mock work order object."""
    wo = MagicMock()
    wo.id = work_order_id
    wo.work_order_no = "WO-TEST-20260409-001"
    wo.status = status
    wo.title = "Test"
    wo.description = "Test"
    wo.station_id = "st-001"
    wo.reported_by = "user-001"
    wo.reported_by_name = "Tester"
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


def _make_db_returning_wo(wo):
    """Create a mock async DB session that returns the given work order."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = wo
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


# ── Property 3: Work Order State Machine Legality ─────────────────────────────

@given(
    current_status=st.sampled_from(ALL_STATUSES),
    target_status=st.sampled_from(ALL_STATUSES),
)
@settings(max_examples=200)
def test_only_allowed_transitions_succeed(current_status: str, target_status: str):
    """
    Property 3: Work Order State Machine Legality
    For any work order in any status, attempting a transition to any other status
    should succeed if and only if the transition is in the ALLOWED_TRANSITIONS map.

    Validates: Requirements 4.2
    """
    wo = _make_work_order(status=current_status)
    db = _make_db_returning_wo(wo)

    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    is_allowed = target_status in allowed

    async def run():
        return await wo_service._transition_status(
            db,
            work_order_id="wo-001",
            target_status=target_status,
            changed_by="user-001",
            changed_by_name="Tester",
        )

    if is_allowed:
        result = asyncio.run(run())
        # Transition should succeed: status should be updated
        assert result.status == target_status
    else:
        try:
            asyncio.run(run())
            # Should not reach here
            assert False, f"Transition from {current_status} to {target_status} should have been rejected"
        except AppException as e:
            assert e.status_code == 422


@given(current_status=st.sampled_from(ALL_STATUSES))
@settings(max_examples=100)
def test_terminal_states_have_no_transitions(current_status: str):
    """
    Property 3 (corollary): Terminal states (closed, cancelled) should have
    no allowed outgoing transitions.

    Validates: Requirements 4.2
    """
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if current_status in ("closed", "cancelled"):
        assert len(allowed) == 0, f"Terminal state {current_status} should have no transitions"


@given(
    current_status=st.sampled_from(ALL_STATUSES),
    target_status=st.sampled_from(ALL_STATUSES),
)
@settings(max_examples=200)
def test_status_history_recorded_on_valid_transition(current_status: str, target_status: str):
    """
    Property 3 (history): For any valid transition, a status history record
    should be added to the database.

    Validates: Requirements 4.2
    """
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        return  # Skip invalid transitions

    wo = _make_work_order(status=current_status)
    db = _make_db_returning_wo(wo)

    async def run():
        return await wo_service._transition_status(
            db,
            work_order_id="wo-001",
            target_status=target_status,
            changed_by="user-001",
            changed_by_name="Tester",
        )

    asyncio.run(run())

    # db.add should have been called with a WorkOrderStatusHistory object
    assert db.add.called
    history_obj = db.add.call_args[0][0]
    assert history_obj.old_status == current_status
    assert history_obj.new_status == target_status
