"""Tests for spare part CRUD service logic."""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.sparepart.schemas import ALLOWED_STATUS_TRANSITIONS
from src.modules.sparepart.service import generate_spare_part_code
from src.core.exceptions import AppException


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_allowed_status_transitions():
    """Verify the status transition map is correct per design."""
    assert ALLOWED_STATUS_TRANSITIONS["active"] == {"inactive", "obsolete"}
    assert ALLOWED_STATUS_TRANSITIONS["inactive"] == {"active", "obsolete"}
    assert ALLOWED_STATUS_TRANSITIONS["obsolete"] == set()


def test_obsolete_is_terminal():
    """Obsolete state should have no outgoing transitions."""
    assert len(ALLOWED_STATUS_TRANSITIONS["obsolete"]) == 0


def test_all_statuses_have_transition_entry():
    """Every valid status should be a key in the transition map."""
    from src.modules.sparepart.schemas import VALID_STATUSES
    for s in VALID_STATUSES:
        assert s in ALLOWED_STATUS_TRANSITIONS


def test_spare_part_code_format():
    """Verify the code format pattern SP-{cat_code}-{seq}."""
    import re
    pattern = r"^SP-.+-\d{3}$"
    assert re.match(pattern, "SP-INV-PART-001")
    assert re.match(pattern, "SP-CAT-A-042")
    assert not re.match(pattern, "INV-PART-001")
    assert not re.match(pattern, "SP-INV-PART-1")
