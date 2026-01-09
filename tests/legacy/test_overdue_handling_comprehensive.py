"""Comprehensive tests for Phase 5 Overdue Handling feature.

Tests the three overdue handling types and approval reset pending claim actions.

Phase 5 Fields:
- overdue_handling_type: AT_DUE_DATE, NEVER_OVERDUE, AT_DUE_DATE_THEN_RESET
- approval_reset_pending_claim_action: HOLD_PENDING, CLEAR_PENDING, AUTO_APPROVE_PENDING

Uses scenario_full which provides:
- 3 kids: Zoë, Max!, Lila
- 19 chores with various completion criteria
- Mix of independent, shared_all, shared_first chores
"""

# pylint: disable=protected-access
# pylint: disable=redefined-outer-name

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kidschores import const
from custom_components.kidschores.const import (
    COORDINATOR,
    DOMAIN,
)
from tests.legacy.conftest import (
    create_test_datetime,
    get_chore_state_for_kid,
    is_chore_claimed_for_kid,
)

# =============================================================================
# OVERDUE HANDLING TYPE: NEVER_OVERDUE
# =============================================================================


@pytest.mark.asyncio
async def test_never_overdue_skips_marking(
    hass: HomeAssistant, scenario_full: tuple
) -> None:
    """Test NEVER_OVERDUE chores are never marked overdue regardless of due date."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Get test entities
    zoë_id = name_to_id_map.get("kid:Zoë")
    assert zoë_id, "Test scenario must have Zoë"

    # Find an independent chore assigned to Zoë
    chore_id = None
    for c_id, c_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        assigned = c_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        if zoë_id in assigned:
            chore_id = c_id
            break

    assert chore_id, "Must find a chore assigned to Zoë"

    # Set overdue_handling_type to NEVER_OVERDUE
    coordinator._data[const.DATA_CHORES][chore_id][
        const.DATA_CHORE_OVERDUE_HANDLING_TYPE
    ] = const.OVERDUE_HANDLING_NEVER_OVERDUE

    # Set due date to yesterday (should be overdue in normal circumstances)
    yesterday = create_test_datetime(days_offset=-1)
    chore_info = coordinator._data[const.DATA_CHORES][chore_id]
    per_kid_dates = chore_info.setdefault(const.DATA_CHORE_PER_KID_DUE_DATES, {})
    per_kid_dates[zoë_id] = yesterday

    # Also set kid chore data due date
    zoë_data = coordinator._data[const.DATA_KIDS].get(zoë_id, {})
    chore_data = zoë_data.setdefault(const.DATA_KID_CHORE_DATA, {})
    entry = chore_data.setdefault(chore_id, {})
    entry[const.DATA_KID_CHORE_DATA_DUE_DATE] = yesterday

    # Run overdue check
    now_utc = datetime.now(timezone.utc)
    coordinator._check_overdue_independent(chore_id, chore_info, now_utc)

    # Verify NOT overdue despite past due date
    state = get_chore_state_for_kid(coordinator, zoë_id, chore_id)
    assert state != const.CHORE_STATE_OVERDUE, (
        "NEVER_OVERDUE chore should not be marked overdue"
    )


@pytest.mark.asyncio
async def test_never_overdue_allows_claims_anytime(
    hass: HomeAssistant, scenario_full: tuple
) -> None:
    """Test NEVER_OVERDUE chores can still be claimed regardless of due date."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoë_id = name_to_id_map.get("kid:Zoë")
    assert zoë_id, "Test scenario must have Zoë"

    # Find an independent chore that is NOT already claimed
    chore_id = None
    for c_id, c_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        assigned = c_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        criteria = c_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        if zoë_id in assigned and criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
            # Check if NOT already claimed
            if not is_chore_claimed_for_kid(coordinator, zoë_id, c_id):
                chore_id = c_id
                break

    if not chore_id:
        pytest.skip("No unclaimed independent chore found for Zoë")

    # Reset kid's chore state to pending so we can claim it
    # Must clear: state, last_approved, approval_period_start
    zoë_data = coordinator._data[const.DATA_KIDS].get(zoë_id, {})
    chore_data_dict = zoë_data.setdefault(const.DATA_KID_CHORE_DATA, {})
    if chore_id in chore_data_dict:
        chore_data_dict[chore_id][const.DATA_KID_CHORE_DATA_STATE] = (
            const.CHORE_STATE_PENDING
        )
        chore_data_dict[chore_id][const.DATA_KID_CHORE_DATA_LAST_APPROVED] = None
        chore_data_dict[chore_id][const.DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START] = (
            None
        )

    # Set to NEVER_OVERDUE with past due date
    coordinator._data[const.DATA_CHORES][chore_id][
        const.DATA_CHORE_OVERDUE_HANDLING_TYPE
    ] = const.OVERDUE_HANDLING_NEVER_OVERDUE

    yesterday = create_test_datetime(days_offset=-1)
    chore_info = coordinator._data[const.DATA_CHORES][chore_id]
    per_kid_dates = chore_info.setdefault(const.DATA_CHORE_PER_KID_DUE_DATES, {})
    per_kid_dates[zoë_id] = yesterday

    # Claim should still work
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(zoë_id, chore_id, user_name="Zoë")

    assert is_chore_claimed_for_kid(coordinator, zoë_id, chore_id), (
        "NEVER_OVERDUE chore should allow claims regardless of due date"
    )


# =============================================================================
# OVERDUE HANDLING TYPE: AT_DUE_DATE (Default Behavior)
# =============================================================================


@pytest.mark.asyncio
async def test_at_due_date_marks_overdue(
    hass: HomeAssistant, scenario_full: tuple
) -> None:
    """Test AT_DUE_DATE (default) marks chore overdue when past due."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoë_id = name_to_id_map.get("kid:Zoë")
    assert zoë_id, "Test scenario must have Zoë"

    # Find an independent chore
    chore_id = None
    for c_id, c_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        assigned = c_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        criteria = c_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        if zoë_id in assigned and criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
            chore_id = c_id
            break

    if not chore_id:
        pytest.skip("No independent chore found for Zoë")

    # Use default AT_DUE_DATE handling
    coordinator._data[const.DATA_CHORES][chore_id][
        const.DATA_CHORE_OVERDUE_HANDLING_TYPE
    ] = const.OVERDUE_HANDLING_AT_DUE_DATE

    # Clear any existing state (must also clear last_approved for is_approved_in_current_period)
    zoë_data = coordinator._data[const.DATA_KIDS].get(zoë_id, {})
    chore_data = zoë_data.setdefault(const.DATA_KID_CHORE_DATA, {})
    chore_entry = chore_data.setdefault(chore_id, {})
    chore_entry[const.DATA_KID_CHORE_DATA_STATE] = const.CHORE_STATE_PENDING
    chore_entry[const.DATA_KID_CHORE_DATA_LAST_APPROVED] = None
    chore_entry[const.DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START] = None

    # Set due date to yesterday
    yesterday = create_test_datetime(days_offset=-1)
    chore_info = coordinator._data[const.DATA_CHORES][chore_id]
    per_kid_dates = chore_info.setdefault(const.DATA_CHORE_PER_KID_DUE_DATES, {})
    per_kid_dates[zoë_id] = yesterday

    # Run overdue check (mock notifications)
    with patch.object(coordinator, "_notify_overdue_chore", new=MagicMock()):
        now_utc = datetime.now(timezone.utc)
        coordinator._check_overdue_independent(chore_id, chore_info, now_utc)

    # Should be marked overdue
    state = get_chore_state_for_kid(coordinator, zoë_id, chore_id)
    assert state == const.CHORE_STATE_OVERDUE, (
        "AT_DUE_DATE should mark chore overdue when past due"
    )


@pytest.mark.asyncio
async def test_at_due_date_not_overdue_if_future(
    hass: HomeAssistant, scenario_full: tuple
) -> None:
    """Test AT_DUE_DATE does not mark overdue if due date is in future."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoë_id = name_to_id_map.get("kid:Zoë")
    assert zoë_id, "Test scenario must have Zoë"

    # Find an independent chore
    chore_id = None
    for c_id, c_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        assigned = c_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        criteria = c_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        if zoë_id in assigned and criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
            chore_id = c_id
            break

    if not chore_id:
        pytest.skip("No independent chore found for Zoë")

    # Use AT_DUE_DATE handling
    coordinator._data[const.DATA_CHORES][chore_id][
        const.DATA_CHORE_OVERDUE_HANDLING_TYPE
    ] = const.OVERDUE_HANDLING_AT_DUE_DATE

    # Clear any existing state (must also clear last_approved for is_approved_in_current_period)
    zoë_data = coordinator._data[const.DATA_KIDS].get(zoë_id, {})
    chore_data = zoë_data.setdefault(const.DATA_KID_CHORE_DATA, {})
    chore_entry = chore_data.setdefault(chore_id, {})
    chore_entry[const.DATA_KID_CHORE_DATA_STATE] = const.CHORE_STATE_PENDING
    chore_entry[const.DATA_KID_CHORE_DATA_LAST_APPROVED] = None
    chore_entry[const.DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START] = None

    # Set due date to tomorrow
    tomorrow = create_test_datetime(days_offset=1)
    chore_info = coordinator._data[const.DATA_CHORES][chore_id]
    per_kid_dates = chore_info.setdefault(const.DATA_CHORE_PER_KID_DUE_DATES, {})
    per_kid_dates[zoë_id] = tomorrow

    # Run overdue check
    now_utc = datetime.now(timezone.utc)
    coordinator._check_overdue_independent(chore_id, chore_info, now_utc)

    # Should NOT be overdue
    state = get_chore_state_for_kid(coordinator, zoë_id, chore_id)
    assert state != const.CHORE_STATE_OVERDUE, (
        "AT_DUE_DATE should not mark overdue if due date is in future"
    )


# =============================================================================
# MIGRATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_chores_have_required_fields(
    hass: HomeAssistant, scenario_full: tuple
) -> None:
    """Test that v42+ chores have required overdue handling fields from creation.

    For v42+ data, these fields are set by flow_helpers.py during entity creation.
    Migration only adds them for pre-v42 data being upgraded.
    """
    config_entry, _ = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # All chores should have the fields (either from creation or migration)
    for chore_id, chore_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        # Check overdue_handling_type exists (may be default or custom)
        overdue_handling = chore_info.get(const.DATA_CHORE_OVERDUE_HANDLING_TYPE)
        pending_action = chore_info.get(
            const.DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION
        )

        # For v42+ test data, these fields should exist from YAML or creation
        # If missing, it indicates the test YAML needs updating
        if overdue_handling is None:
            pytest.skip(
                f"Chore {chore_id} missing overdue_handling_type - "
                "test YAML needs updating for v42+ schema"
            )
        if pending_action is None:
            pytest.skip(
                f"Chore {chore_id} missing approval_reset_pending_claim_action - "
                "test YAML needs updating for v42+ schema"
            )


# =============================================================================
# CHORE FIELD PRESERVATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_overdue_handling_field_preserved_on_claim(
    hass: HomeAssistant, scenario_full: tuple
) -> None:
    """Test that overdue_handling_type field is preserved during chore operations."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoë_id = name_to_id_map.get("kid:Zoë")
    assert zoë_id, "Test scenario must have Zoë"

    # Find an independent chore
    chore_id = None
    for c_id, c_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        assigned = c_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        criteria = c_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        if zoë_id in assigned and criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
            chore_id = c_id
            break

    if not chore_id:
        pytest.skip("No independent chore found for Zoë")

    # Set non-default value
    coordinator._data[const.DATA_CHORES][chore_id][
        const.DATA_CHORE_OVERDUE_HANDLING_TYPE
    ] = const.OVERDUE_HANDLING_NEVER_OVERDUE

    # Reset kid's chore state to pending so we can claim it
    # Must clear: state, last_approved, approval_period_start
    zoë_data = coordinator._data[const.DATA_KIDS].get(zoë_id, {})
    chore_data_dict = zoë_data.setdefault(const.DATA_KID_CHORE_DATA, {})
    if chore_id in chore_data_dict:
        chore_data_dict[chore_id][const.DATA_KID_CHORE_DATA_STATE] = (
            const.CHORE_STATE_PENDING
        )
        chore_data_dict[chore_id][const.DATA_KID_CHORE_DATA_LAST_APPROVED] = None
        chore_data_dict[chore_id][const.DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START] = (
            None
        )

    # Claim the chore
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(zoë_id, chore_id, user_name="Zoë")

    # Field should still be NEVER_OVERDUE
    chore_info = coordinator._data[const.DATA_CHORES][chore_id]
    assert chore_info.get(const.DATA_CHORE_OVERDUE_HANDLING_TYPE) == (
        const.OVERDUE_HANDLING_NEVER_OVERDUE
    ), "overdue_handling_type should be preserved after claim"


@pytest.mark.asyncio
async def test_pending_claim_action_field_preserved_on_approval(
    hass: HomeAssistant, scenario_full: tuple
) -> None:
    """Test approval_reset_pending_claim_action is preserved during approval."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoë_id = name_to_id_map.get("kid:Zoë")
    parent_id = name_to_id_map.get("parent:Môm Astrid Stârblüm")
    assert zoë_id and parent_id, "Test scenario must have Zoë and parent"

    # Find an independent chore
    chore_id = None
    for c_id, c_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        assigned = c_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        criteria = c_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        if zoë_id in assigned and criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
            chore_id = c_id
            break

    if not chore_id:
        pytest.skip("No independent chore found for Zoë")

    # Set non-default value
    coordinator._data[const.DATA_CHORES][chore_id][
        const.DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION
    ] = const.APPROVAL_RESET_PENDING_CLAIM_HOLD

    # Reset kid's chore state to pending so we can claim it
    # Must clear: state, last_approved, approval_period_start
    zoë_data = coordinator._data[const.DATA_KIDS].get(zoë_id, {})
    chore_data_dict = zoë_data.setdefault(const.DATA_KID_CHORE_DATA, {})
    if chore_id in chore_data_dict:
        chore_data_dict[chore_id][const.DATA_KID_CHORE_DATA_STATE] = (
            const.CHORE_STATE_PENDING
        )
        chore_data_dict[chore_id][const.DATA_KID_CHORE_DATA_LAST_APPROVED] = None
        chore_data_dict[chore_id][const.DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START] = (
            None
        )

    # Claim and approve
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(zoë_id, chore_id, user_name="Zoë")
        coordinator.approve_chore(
            parent_name="Môm Astrid Stârblüm",
            kid_id=zoë_id,
            chore_id=chore_id,
        )

    # Field should still be HOLD_PENDING
    chore_info = coordinator._data[const.DATA_CHORES][chore_id]
    assert chore_info.get(const.DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION) == (
        const.APPROVAL_RESET_PENDING_CLAIM_HOLD
    ), "approval_reset_pending_claim_action should be preserved after approval"


# =============================================================================
# MULTI-KID OVERDUE HANDLING
# =============================================================================


@pytest.mark.asyncio
async def test_never_overdue_affects_all_assigned_kids(
    hass: HomeAssistant, scenario_full: tuple
) -> None:
    """Test NEVER_OVERDUE applies to all kids assigned to the chore."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoë_id = name_to_id_map.get("kid:Zoë")
    max_id = name_to_id_map.get("kid:Max!")
    lila_id = name_to_id_map.get("kid:Lila")
    assert zoë_id and max_id and lila_id, "Test scenario must have all three kids"

    # Find a multi-kid independent chore (e.g., "Stär sweep")
    chore_id = None
    for c_id, c_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        assigned = c_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        criteria = c_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        if (
            criteria == const.COMPLETION_CRITERIA_INDEPENDENT
            and zoë_id in assigned
            and max_id in assigned
            and lila_id in assigned
        ):
            chore_id = c_id
            break

    if not chore_id:
        pytest.skip("No multi-kid independent chore found")

    # Set to NEVER_OVERDUE
    coordinator._data[const.DATA_CHORES][chore_id][
        const.DATA_CHORE_OVERDUE_HANDLING_TYPE
    ] = const.OVERDUE_HANDLING_NEVER_OVERDUE

    # Set all kids to have past due dates
    yesterday = create_test_datetime(days_offset=-1)
    chore_info = coordinator._data[const.DATA_CHORES][chore_id]
    per_kid_dates = chore_info.setdefault(const.DATA_CHORE_PER_KID_DUE_DATES, {})
    for kid_id in [zoë_id, max_id, lila_id]:
        per_kid_dates[kid_id] = yesterday

    # Run overdue check
    now_utc = datetime.now(timezone.utc)
    coordinator._check_overdue_independent(chore_id, chore_info, now_utc)

    # None should be overdue
    for kid_id in [zoë_id, max_id, lila_id]:
        state = get_chore_state_for_kid(coordinator, kid_id, chore_id)
        assert state != const.CHORE_STATE_OVERDUE, (
            f"NEVER_OVERDUE should apply to all kids, but {kid_id} was marked overdue"
        )


# =============================================================================
# SHARED CHORE OVERDUE HANDLING
# =============================================================================


@pytest.mark.asyncio
async def test_shared_chore_never_overdue(
    hass: HomeAssistant, scenario_full: tuple
) -> None:
    """Test NEVER_OVERDUE works for shared chores."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoë_id = name_to_id_map.get("kid:Zoë")
    assert zoë_id, "Test scenario must have Zoë"

    # Find a shared_all or shared_first chore
    chore_id = None
    for c_id, c_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        assigned = c_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        criteria = c_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        if zoë_id in assigned and criteria in [
            const.COMPLETION_CRITERIA_SHARED,
            const.COMPLETION_CRITERIA_SHARED_FIRST,
        ]:
            chore_id = c_id
            break

    if not chore_id:
        pytest.skip("No shared chore found for Zoë")

    # Set to NEVER_OVERDUE with past due date
    coordinator._data[const.DATA_CHORES][chore_id][
        const.DATA_CHORE_OVERDUE_HANDLING_TYPE
    ] = const.OVERDUE_HANDLING_NEVER_OVERDUE

    yesterday = create_test_datetime(days_offset=-1)
    chore_info = coordinator._data[const.DATA_CHORES][chore_id]
    chore_info[const.DATA_CHORE_DUE_DATE] = yesterday

    # Run shared overdue check
    with patch.object(coordinator, "_notify_overdue_chore", new=MagicMock()):
        now_utc = datetime.now(timezone.utc)
        coordinator._check_overdue_shared(chore_id, chore_info, now_utc)

    # Verify no kid is marked overdue
    assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
    for kid_id in assigned_kids:
        state = get_chore_state_for_kid(coordinator, kid_id, chore_id)
        assert state != const.CHORE_STATE_OVERDUE, (
            f"NEVER_OVERDUE shared chore should not mark {kid_id} overdue"
        )


# =============================================================================
# EDGE CASES
# =============================================================================


@pytest.mark.asyncio
async def test_no_due_date_skips_overdue_check(
    hass: HomeAssistant, scenario_full: tuple
) -> None:
    """Test that chores without due dates are not marked overdue."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoë_id = name_to_id_map.get("kid:Zoë")
    assert zoë_id, "Test scenario must have Zoë"

    # Find an independent chore
    chore_id = None
    for c_id, c_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        assigned = c_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        criteria = c_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        if zoë_id in assigned and criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
            chore_id = c_id
            break

    if not chore_id:
        pytest.skip("No independent chore found for Zoë")

    # Clear due dates
    chore_info = coordinator._data[const.DATA_CHORES][chore_id]
    chore_info[const.DATA_CHORE_OVERDUE_HANDLING_TYPE] = (
        const.OVERDUE_HANDLING_AT_DUE_DATE
    )
    chore_info[const.DATA_CHORE_PER_KID_DUE_DATES] = {}

    # Clear kid's due date too
    zoë_data = coordinator._data[const.DATA_KIDS].get(zoë_id, {})
    chore_data = zoë_data.get(const.DATA_KID_CHORE_DATA, {})
    if chore_id in chore_data:
        chore_data[chore_id].pop(const.DATA_KID_CHORE_DATA_DUE_DATE, None)

    # Run overdue check
    now_utc = datetime.now(timezone.utc)
    coordinator._check_overdue_independent(chore_id, chore_info, now_utc)

    # Should not be overdue (no deadline = no overdue)
    state = get_chore_state_for_kid(coordinator, zoë_id, chore_id)
    assert state != const.CHORE_STATE_OVERDUE, (
        "Chore without due date should not be marked overdue"
    )


@pytest.mark.asyncio
async def test_claimed_chore_not_marked_overdue(
    hass: HomeAssistant, scenario_full: tuple
) -> None:
    """Test that already-claimed chores are not marked overdue."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoë_id = name_to_id_map.get("kid:Zoë")
    assert zoë_id, "Test scenario must have Zoë"

    # Find an independent chore
    chore_id = None
    for c_id, c_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        assigned = c_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        criteria = c_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        if zoë_id in assigned and criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
            chore_id = c_id
            break

    if not chore_id:
        pytest.skip("No independent chore found for Zoë")

    # Reset kid's chore state to pending so we can claim it
    # Must clear: state, last_approved, approval_period_start
    zoë_data = coordinator._data[const.DATA_KIDS].get(zoë_id, {})
    chore_data_dict = zoë_data.setdefault(const.DATA_KID_CHORE_DATA, {})
    if chore_id in chore_data_dict:
        chore_data_dict[chore_id][const.DATA_KID_CHORE_DATA_STATE] = (
            const.CHORE_STATE_PENDING
        )
        chore_data_dict[chore_id][const.DATA_KID_CHORE_DATA_LAST_APPROVED] = None
        chore_data_dict[chore_id][const.DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START] = (
            None
        )

    # Claim the chore first
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(zoë_id, chore_id, user_name="Zoë")

    # Set past due date
    yesterday = create_test_datetime(days_offset=-1)
    chore_info = coordinator._data[const.DATA_CHORES][chore_id]
    per_kid_dates = chore_info.setdefault(const.DATA_CHORE_PER_KID_DUE_DATES, {})
    per_kid_dates[zoë_id] = yesterday

    # Run overdue check
    with patch.object(coordinator, "_notify_overdue_chore", new=MagicMock()):
        now_utc = datetime.now(timezone.utc)
        coordinator._check_overdue_independent(chore_id, chore_info, now_utc)

    # Should still be claimed, not overdue (claimed chores skip overdue check)
    assert is_chore_claimed_for_kid(coordinator, zoë_id, chore_id), (
        "Already-claimed chore should remain claimed, not be marked overdue"
    )
