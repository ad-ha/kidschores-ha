"""Test INDEPENDENT mode overdue checking branching logic (Phase 3 Sprint 1, Step 1.9)."""

# pylint: disable=protected-access
# pylint: disable=redefined-outer-name

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kidschores import const
from custom_components.kidschores.const import (
    COORDINATOR,
    DOMAIN,
)
from tests.conftest import (
    create_test_datetime,
    is_chore_approved_for_kid,
    is_chore_claimed_for_kid,
)


@pytest.mark.skip(
    reason="Test architecture requires rewrite - direct _data manipulation bypasses state sync"
)
@pytest.mark.asyncio
async def test_independent_different_due_dates_per_kid(
    hass: HomeAssistant, scenario_full
):
    """Test INDEPENDENT mode with different due dates per kid.

    Verifies that per-kid due dates are checked independently.
    Kid A is overdue while Kid B is still pending on same INDEPENDENT chore.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Get test data
    zoë_id = name_to_id_map.get("kid:Zoë")
    max_id = name_to_id_map.get("kid:Max!")
    assert zoë_id and max_id, "Test scenario must have Zoë and Max!"

    # Find or create INDEPENDENT chore assigned to both kids
    chore_found = None
    for chore_id, chore_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        criteria = chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        if (
            criteria == const.COMPLETION_CRITERIA_INDEPENDENT
            and zoë_id in assigned_kids
            and max_id in assigned_kids
        ):
            chore_found = chore_id
            break

    if not chore_found:
        pytest.skip(
            "Test scenario must have INDEPENDENT chore assigned to multiple kids"
        )

    chore_info = coordinator._data[const.DATA_CHORES][chore_found]

    # Set per-kid due dates
    tomorrow = create_test_datetime(days_offset=1)
    next_week = create_test_datetime(days_offset=7)

    # Ensure per-kid due dates structure exists
    if const.DATA_CHORE_PER_KID_DUE_DATES not in chore_info:
        chore_info[const.DATA_CHORE_PER_KID_DUE_DATES] = {}

    per_kid_dates = chore_info[const.DATA_CHORE_PER_KID_DUE_DATES]
    per_kid_dates[zoë_id] = tomorrow
    per_kid_dates[max_id] = next_week

    # Also update kid chore data
    zoë_chore_data = (
        coordinator._data[const.DATA_KIDS][zoë_id]
        .setdefault(const.DATA_KID_CHORE_DATA, {})
        .setdefault(chore_found, {})
    )
    zoë_chore_data[const.DATA_KID_CHORE_DATA_DUE_DATE] = tomorrow

    max_chore_data = (
        coordinator._data[const.DATA_KIDS][max_id]
        .setdefault(const.DATA_KID_CHORE_DATA, {})
        .setdefault(chore_found, {})
    )
    max_chore_data[const.DATA_KID_CHORE_DATA_DUE_DATE] = next_week

    # Clear any existing approved/claimed status for this chore (fixture may pre-populate)
    # The overdue check skips chores where all assigned kids have claimed or approved
    # NOTE: This test uses deprecated list-based logic. Phase 4 uses timestamp-based tracking.
    # Test will need rewrite for approval_period_start / last_approved fields.
    for kid_id in [zoë_id, max_id]:
        kid_chore_data = (
            coordinator._data[const.DATA_KIDS][kid_id]
            .get(const.DATA_KID_CHORE_DATA, {})
            .get(chore_found, {})
        )
        # Clear timestamp fields (Phase 4 replacement for lists)
        kid_chore_data.pop(const.DATA_KID_CHORE_DATA_LAST_APPROVED, None)
        kid_chore_data.pop(const.DATA_KID_CHORE_DATA_LAST_CLAIMED, None)

    # Fast-forward past Zoë's due date (but before Max!'s)
    # Need actual datetime for dt_util.utcnow() mock, not ISO string
    from datetime import datetime, timedelta, timezone

    two_days_from_now_dt = datetime.now(timezone.utc) + timedelta(days=2)

    # Debug: Print state before overdue check
    print("\n=== DEBUG BEFORE OVERDUE CHECK ===")
    print(f"Mock time: {two_days_from_now_dt.isoformat()}")
    print(f"tomorrow var: {tomorrow}")
    print(f"next_week var: {next_week}")
    chore_info = coordinator._data[const.DATA_CHORES].get(chore_found, {})
    print(f"Chore '{chore_info.get('name')}' ID: {chore_found}")
    print(
        f"Chore per_kid_due_dates: {chore_info.get(const.DATA_CHORE_PER_KID_DUE_DATES, {})}"
    )
    print(f"Chore assigned_kids: {chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])}")
    print(
        f"Chore completion_criteria: {chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA, 'MISSING')}"
    )
    for kid_id, kid_name in [(zoë_id, "Zoë"), (max_id, "Max!")]:
        kid_chore_data = (
            coordinator._data[const.DATA_KIDS]
            .get(kid_id, {})
            .get(const.DATA_KID_CHORE_DATA, {})
            .get(chore_found, {})
        )
        print(f"Kid {kid_name} ID: {kid_id}")
        print(
            f"Kid {kid_name} last_approved: {kid_chore_data.get(const.DATA_KID_CHORE_DATA_LAST_APPROVED, 'None')}"
        )
        print(
            f"Kid {kid_name} last_claimed: {kid_chore_data.get(const.DATA_KID_CHORE_DATA_LAST_CLAIMED, 'None')}"
        )
    print("=== END DEBUG ===\n")

    # Add debug logging to coordinator
    import logging

    logging.getLogger("custom_components.kidschores").setLevel(logging.DEBUG)

    with patch(
        "custom_components.kidschores.coordinator.dt_util.utcnow",
        return_value=two_days_from_now_dt,
    ):
        await coordinator._check_overdue_chores()

    # Debug: Print state after overdue check
    print("\n=== DEBUG AFTER OVERDUE CHECK ===")
    for kid_id, kid_name in [(zoë_id, "Zoë"), (max_id, "Max!")]:
        kid_data = coordinator._data[const.DATA_KIDS].get(kid_id, {})
        print(
            f"Kid {kid_name} overdue_chores: {kid_data.get(const.DATA_KID_OVERDUE_CHORES, [])}"
        )
    print("=== END DEBUG ===\n")

    # Verify: Zoë is overdue, Max! is NOT
    zoë_overdue = coordinator._data[const.DATA_KIDS][zoë_id].get(
        const.DATA_KID_OVERDUE_CHORES, []
    )
    max_overdue = coordinator._data[const.DATA_KIDS][max_id].get(
        const.DATA_KID_OVERDUE_CHORES, []
    )

    assert chore_found in zoë_overdue, (
        f"Zoë should be overdue (due {tomorrow}, now {two_days_from_now_dt})"
    )
    assert chore_found not in max_overdue, (
        f"Max! should NOT be overdue (due {next_week}, now {two_days_from_now_dt})"
    )


@pytest.mark.asyncio
async def test_independent_overdue_one_kid_not_all(
    hass: HomeAssistant, scenario_medium
):
    """Test that overdue affects only specific kid, not all assigned kids.

    Verifies that marking one INDEPENDENT kid overdue doesn't automatically
    mark other assigned kids overdue.
    """
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoë_id = name_to_id_map.get("kid:Zoë")
    max_id = name_to_id_map.get("kid:Max!")
    lila_id = name_to_id_map.get("kid:Lila")

    if not (zoë_id and max_id and lila_id):
        pytest.skip("Test scenario must have Zoë, Max!, and Lila")

    # Find INDEPENDENT chore assigned to all three kids
    chore_found = None
    for chore_id, chore_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        criteria = chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        if criteria == const.COMPLETION_CRITERIA_INDEPENDENT and all(
            kid in assigned_kids for kid in [zoë_id, max_id, lila_id]
        ):
            chore_found = chore_id
            break

    if not chore_found:
        pytest.skip("Test scenario must have INDEPENDENT chore with 3+ assigned kids")

    chore_info = coordinator._data[const.DATA_CHORES][chore_found]

    # Set different due dates for each kid
    today = create_test_datetime(days_offset=0)
    tomorrow = create_test_datetime(days_offset=1)
    next_week = create_test_datetime(days_offset=7)

    if const.DATA_CHORE_PER_KID_DUE_DATES not in chore_info:
        chore_info[const.DATA_CHORE_PER_KID_DUE_DATES] = {}

    per_kid_dates = chore_info[const.DATA_CHORE_PER_KID_DUE_DATES]
    per_kid_dates[zoë_id] = today  # Overdue now
    per_kid_dates[max_id] = tomorrow  # Due tomorrow
    per_kid_dates[lila_id] = next_week  # Due next week

    # Update kid chore data
    for kid_id, due_date in [
        (zoë_id, today),
        (max_id, tomorrow),
        (lila_id, next_week),
    ]:
        kid_chore_data = (
            coordinator._data[const.DATA_KIDS][kid_id]
            .setdefault(const.DATA_KID_CHORE_DATA, {})
            .setdefault(chore_found, {})
        )
        kid_chore_data[const.DATA_KID_CHORE_DATA_DUE_DATE] = due_date

    # Clear any existing overdue state
    for kid_id in [zoë_id, max_id, lila_id]:
        coordinator._data[const.DATA_KIDS][kid_id][const.DATA_KID_OVERDUE_CHORES] = []

    # Run overdue check (now is tomorrow - after Zoë, before Max!)
    # Need actual datetime for dt_util.utcnow() mock
    from datetime import datetime, timedelta, timezone

    now_is_tomorrow_dt = datetime.now(timezone.utc) + timedelta(days=1)
    with patch("homeassistant.util.dt.utcnow", return_value=now_is_tomorrow_dt):
        await coordinator._check_overdue_chores()

    # Verify only Zoë and Max! are overdue
    zoë_overdue = coordinator._data[const.DATA_KIDS][zoë_id].get(
        const.DATA_KID_OVERDUE_CHORES, []
    )
    max_overdue = coordinator._data[const.DATA_KIDS][max_id].get(
        const.DATA_KID_OVERDUE_CHORES, []
    )
    lila_overdue = coordinator._data[const.DATA_KIDS][lila_id].get(
        const.DATA_KID_OVERDUE_CHORES, []
    )

    assert chore_found in zoë_overdue, "Zoë should be overdue"
    assert chore_found in max_overdue, "Max! should be overdue (due was tomorrow = now)"
    assert chore_found not in lila_overdue, "Lila should NOT be overdue (due next week)"


@pytest.mark.asyncio
async def test_migration_populates_per_kid_due_dates(
    hass: HomeAssistant, scenario_minimal
):
    """Test migration copies chore-level due dates to all assigned kids.

    Simulates a chore created before per-kid structure existed.
    Migration should populate per-kid due dates from template.
    """
    # NOTE: This test is skipped until _migrate_independent_chores is implemented
    pytest.skip("Migration method _migrate_independent_chores not yet implemented")

    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoë_id = name_to_id_map.get("kid:Zoë")
    assert zoë_id, "Test scenario must have Zoë"

    # Find INDEPENDENT chore
    chore_found = None
    for chore_id, chore_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        if (
            chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
            == const.COMPLETION_CRITERIA_INDEPENDENT
        ):
            chore_found = chore_id
            break

    if not chore_found:
        pytest.skip("Test scenario must have INDEPENDENT chore")

    chore_info = coordinator._data[const.DATA_CHORES][chore_found]

    # Simulate pre-migration state: has chore-level due date but no per-kid structure
    chore_template_date = create_test_datetime(days_offset=7)
    chore_info[const.DATA_CHORE_DUE_DATE] = chore_template_date

    # Remove per-kid structure if it exists
    if const.DATA_CHORE_PER_KID_DUE_DATES in chore_info:
        del chore_info[const.DATA_CHORE_PER_KID_DUE_DATES]

    # Run migration
    coordinator._migrate_independent_chores()

    # Verify per-kid structure was created
    assert const.DATA_CHORE_PER_KID_DUE_DATES in chore_info, (
        "Migration should create per-kid structure"
    )

    per_kid_dates = chore_info[const.DATA_CHORE_PER_KID_DUE_DATES]
    assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])

    # Verify all assigned kids inherited the template
    for kid_id in assigned_kids:
        assert kid_id in per_kid_dates, (
            f"Migration should populate per-kid date for kid {kid_id}"
        )
        assert per_kid_dates[kid_id] == chore_template_date, (
            f"Kid {kid_id} should inherit template date {chore_template_date}"
        )


@pytest.mark.skip(
    reason="Test architecture requires rewrite - direct _data manipulation bypasses state sync"
)
@pytest.mark.asyncio
async def test_fallback_to_chore_level_due_date(hass: HomeAssistant, scenario_minimal):
    """Test system falls back to chore-level if per-kid due date missing.

    Simulates scenario where per-kid structure exists but specific kid has no override.
    Should use chore-level template as fallback.
    """
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoë_id = name_to_id_map.get("kid:Zoë")
    assert zoë_id, "Test scenario must have Zoë"

    # Find INDEPENDENT chore
    chore_found = None
    for chore_id, chore_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        if (
            chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
            == const.COMPLETION_CRITERIA_INDEPENDENT
        ):
            chore_found = chore_id
            break

    if not chore_found:
        pytest.skip("Test scenario must have INDEPENDENT chore")

    chore_info = coordinator._data[const.DATA_CHORES][chore_found]

    # Set chore-level due date
    template_date = create_test_datetime(days_offset=7)
    chore_info[const.DATA_CHORE_DUE_DATE] = template_date

    # Create empty per-kid structure (no overrides)
    chore_info[const.DATA_CHORE_PER_KID_DUE_DATES] = {}

    # Clear overdue state
    coordinator._data[const.DATA_KIDS][zoë_id][const.DATA_KID_OVERDUE_CHORES] = []

    # Fast-forward past template date (need datetime object for dt_util.utcnow() mock)
    from datetime import datetime, timedelta, timezone

    now_is_two_weeks_dt = datetime.now(timezone.utc) + timedelta(days=14)

    with patch("homeassistant.util.dt.utcnow", return_value=now_is_two_weeks_dt):
        await coordinator._check_overdue_chores()

    # Verify fallback worked - Zoë should be marked overdue using template
    zoë_overdue = coordinator._data[const.DATA_KIDS][zoë_id].get(
        const.DATA_KID_OVERDUE_CHORES, []
    )

    assert chore_found in zoë_overdue, (
        "Fallback to chore-level due date should mark kid overdue"
    )


@pytest.mark.skip(
    reason="Test architecture requires rewrite - direct _data manipulation bypasses state sync"
)
@pytest.mark.asyncio
async def test_independent_claims_separate(hass: HomeAssistant, scenario_full):
    """Test Kid A claiming INDEPENDENT chore doesn't affect Kid B's state.

    Verifies that individual kid state changes are isolated in INDEPENDENT mode.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoë_id = name_to_id_map.get("kid:Zoë")
    max_id = name_to_id_map.get("kid:Max!")
    assert zoë_id and max_id, "Test scenario must have Zoë and Max!"

    # Find INDEPENDENT chore assigned to both
    chore_found = None
    for chore_id, chore_info in coordinator._data.get(const.DATA_CHORES, {}).items():
        criteria = chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        if (
            criteria == const.COMPLETION_CRITERIA_INDEPENDENT
            and zoë_id in assigned_kids
            and max_id in assigned_kids
        ):
            chore_found = chore_id
            break

    if not chore_found:
        pytest.skip("Test scenario must have INDEPENDENT chore with multiple kids")

    # Mock notifications to avoid ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Zoë claims chore
        coordinator.claim_chore(zoë_id, chore_found, user_name="Zoë")

    # Verify Zoë in claimed, Max! not (using v0.4.0 state model)
    assert is_chore_claimed_for_kid(coordinator, zoë_id, chore_found), (
        "Zoë should have claimed chore"
    )
    assert not is_chore_claimed_for_kid(coordinator, max_id, chore_found), (
        "Max! should NOT have claimed chore (independent state)"
    )

    # Approve Zoë's claim
    parent_id = name_to_id_map.get("parent:Môm Astrid Stârblüm")
    if parent_id:
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator.approve_chore(
                kid_id=zoë_id,
                chore_id=chore_found,
                parent_id=parent_id,
                parent_name="Môm Astrid Stârblüm",
            )

    # Verify Zoë approved, Max! still pending (using v0.4.0 state model)
    assert is_chore_approved_for_kid(coordinator, zoë_id, chore_found), (
        "Zoë should be approved"
    )
    assert not is_chore_approved_for_kid(coordinator, max_id, chore_found), (
        "Max! should NOT be approved (independent state)"
    )
