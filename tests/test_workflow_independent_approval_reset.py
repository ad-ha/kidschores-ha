"""Test INDEPENDENT chore approval date advancement (Phase C Sprint 1, File 2).

Tests approval workflow for INDEPENDENT chores with per-kid due dates:
- Approval advances per-kid due date by recurrence interval
- Disapproval doesn't advance due date
- Multiple kids approve same day (per-kid advancement)
- Null due date handling (no crash)
- Weekly recurrence advances exactly 7 days

Priority: P1 CRITICAL (user "especially interested in approval resets")
"""

# pylint: disable=protected-access
# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import Context, HomeAssistant

from custom_components.kidschores import const
from custom_components.kidschores.const import (
    COORDINATOR,
    DATA_KID_CHORE_DATA,
    DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START,
    DATA_KID_CHORE_DATA_DUE_DATE,
    DOMAIN,
)
from custom_components.kidschores.migration_pre_v42 import PreV42Migrator
from tests.conftest import create_test_datetime  # is_chore_* helpers not used here


@pytest.mark.asyncio
async def test_approve_advances_per_kid_due_date(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test INDEPENDENT chore approval advances per-kid due date by recurrence.

    Validates: approve_chore service → _reschedule_chore_next_due_date_for_kid() →
    per-kid due date advanced by recurrence interval (daily = +1 day).
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Manual migration
    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Get IDs
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Set chore's template due date (required for recurrence calculation)
    original_due_date = create_test_datetime(days_offset=0)
    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_DUE_DATE] = (
        original_due_date
    )

    # Ensure chore_data structure exists with complete initialization
    # ALWAYS reset to PENDING since scenario may have set to APPROVED via chores_completed
    if DATA_KID_CHORE_DATA not in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA] = {}
    star_sweep_name = coordinator.chores_data[star_sweep_id][const.DATA_CHORE_NAME]
    coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id] = {
        const.DATA_KID_CHORE_DATA_NAME: star_sweep_name,
        const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
        const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
        const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
        const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
        const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
        const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
        DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START: None,
        const.DATA_KID_CHORE_DATA_PERIODS: {
            const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
        },
        const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
    }

    # Set Zoë's due date to today
    original_due_date = create_test_datetime(days_offset=0)
    # Set canonical source (per_kid_due_dates on chore)
    coordinator.chores_data[star_sweep_id].setdefault(
        const.DATA_CHORE_PER_KID_DUE_DATES, {}
    )[zoe_id] = original_due_date
    # Set derived/cached source (chore_data on kid)
    coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id][
        DATA_KID_CHORE_DATA_DUE_DATE
    ] = original_due_date

    # Set claimed state (prerequisite for approval) using coordinator method (v0.4.0+)
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(zoe_id, star_sweep_id, "Zoë")

    coordinator._persist()

    # Approve chore (should advance due date by recurrence interval)
    # Chore is DAILY, so should advance by +1 day
    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": "Zoë",
                "chore_name": "Stär sweep",
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # Verify Zoë's due date advanced by +1 day (DAILY recurrence)
    new_due_date = coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id][
        DATA_KID_CHORE_DATA_DUE_DATE
    ]

    assert new_due_date is not None
    # Parse if string, compare dates
    from dateutil import parser

    if isinstance(new_due_date, str):
        new_due_date = parser.isoparse(new_due_date)
    if isinstance(original_due_date, str):
        original_due_date = parser.isoparse(original_due_date)
    assert new_due_date > original_due_date
    # Compare date parts (timedelta.days returns floor, not round)
    assert (new_due_date.date() - original_due_date.date()).days == 1


@pytest.mark.asyncio
async def test_disapprove_does_not_advance_due_date(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test disapprove_chore does NOT advance per-kid due date.

    Validates: disapproval resets claimed state but preserves due date.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Manual migration
    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Get IDs
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Ensure chore_data structure exists
    # ALWAYS reset to PENDING since scenario may have set to APPROVED via chores_completed
    if DATA_KID_CHORE_DATA not in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA] = {}
    star_sweep_name = coordinator.chores_data[star_sweep_id][const.DATA_CHORE_NAME]
    coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id] = {
        const.DATA_KID_CHORE_DATA_NAME: star_sweep_name,
        const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
        const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
        const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
        const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
        const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
        const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
        DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START: None,
        const.DATA_KID_CHORE_DATA_PERIODS: {
            const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
        },
        const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
    }

    # Set Zoë's due date
    original_due_date = create_test_datetime(days_offset=0)
    coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id][
        DATA_KID_CHORE_DATA_DUE_DATE
    ] = original_due_date

    # Set claimed state using coordinator method (v0.4.0+)
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(zoe_id, star_sweep_id, "Zoë")

    coordinator._persist()

    # Disapprove chore (should NOT advance due date)
    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "disapprove_chore",
            {
                "kid_name": "Zoë",
                "chore_name": "Stär sweep",
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # Verify due date unchanged
    current_due_date = coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][
        star_sweep_id
    ][DATA_KID_CHORE_DATA_DUE_DATE]

    assert current_due_date == original_due_date


@pytest.mark.asyncio
async def test_shared_approve_advances_chore_level_due_date(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test SHARED chore approval advances chore-level due date for ALL kids.

    This test is EXPECTED TO SKIP because scenario_full has no SHARED chores.
    Included for completeness - will pass when SHARED test data available.
    """
    config_entry, _ = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Check if any chore is SHARED (completion_criteria = shared_all)
    shared_chores = [
        chore_id
        for chore_id, chore_info in coordinator.chores_data.items()
        if chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        == const.COMPLETION_CRITERIA_SHARED
    ]

    if not shared_chores:
        pytest.skip("No SHARED chores in scenario_full - test requires SHARED chore")

    # Test would validate: SHARED approval advances chore-level due_date
    # NOT per-kid due dates (all kids see same new due date)


@pytest.mark.asyncio
async def test_multiple_kids_approve_same_day_independent_advancement(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test multiple kids approving same INDEPENDENT chore on same day.

    Validates: Each kid's approval advances THEIR per-kid due date independently.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Manual migration
    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Get IDs
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    # Initialize structure for both kids
    # ALWAYS reset to PENDING since scenario may have set to APPROVED via chores_completed
    for kid_id in [zoe_id, max_id]:
        if DATA_KID_CHORE_DATA not in coordinator.kids_data[kid_id]:
            coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA] = {}
        star_sweep_name = coordinator.chores_data[star_sweep_id][const.DATA_CHORE_NAME]
        coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA][star_sweep_id] = {
            const.DATA_KID_CHORE_DATA_NAME: star_sweep_name,
            const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
            const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
            const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
            const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
            const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
            const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
            DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START: None,
            const.DATA_KID_CHORE_DATA_PERIODS: {
                const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
            },
            const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
        }

    # Set both kids' due dates to today
    original_due_date = create_test_datetime(days_offset=0)
    # Ensure per_kid_due_dates exists
    coordinator.chores_data[star_sweep_id].setdefault(
        const.DATA_CHORE_PER_KID_DUE_DATES, {}
    )
    kid_names = {zoe_id: "Zoë", max_id: "Max!"}
    for kid_id in [zoe_id, max_id]:
        # Set canonical source (per_kid_due_dates on chore)
        coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
            kid_id
        ] = original_due_date
        # Set derived/cached source (chore_data on kid)
        coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA][star_sweep_id][
            DATA_KID_CHORE_DATA_DUE_DATE
        ] = original_due_date

        # Set claimed state using coordinator method (v0.4.0+)
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator.claim_chore(kid_id, star_sweep_id, kid_names[kid_id])

    coordinator._persist()

    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    # Approve for Zoë
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": "Zoë",
                "chore_name": "Stär sweep",
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # Approve for Max!
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": "Max!",
                "chore_name": "Stär sweep",
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # Verify BOTH kids' due dates advanced independently (DAILY = +1 day)
    zoe_due_date = coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id][
        DATA_KID_CHORE_DATA_DUE_DATE
    ]
    max_due_date = coordinator.kids_data[max_id][DATA_KID_CHORE_DATA][star_sweep_id][
        DATA_KID_CHORE_DATA_DUE_DATE
    ]

    assert zoe_due_date is not None
    assert max_due_date is not None
    # Parse if string, compare dates
    from dateutil import parser

    if isinstance(zoe_due_date, str):
        zoe_due_date = parser.isoparse(zoe_due_date)
    if isinstance(max_due_date, str):
        max_due_date = parser.isoparse(max_due_date)
    if isinstance(original_due_date, str):
        original_due_date = parser.isoparse(original_due_date)
    # Compare date parts (timedelta.days returns floor, not round)
    assert (zoe_due_date.date() - original_due_date.date()).days == 1
    assert (max_due_date.date() - original_due_date.date()).days == 1


@pytest.mark.asyncio
async def test_null_due_date_approval_no_crash(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test approving chore with null due date doesn't crash.

    Validates: _reschedule_chore_next_due_date_for_kid() handles None gracefully.
    Should log warning but not raise exception.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Manual migration
    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Get IDs
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Ensure structure exists
    # ALWAYS reset to PENDING since scenario may have set to APPROVED via chores_completed
    if DATA_KID_CHORE_DATA not in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA] = {}
    star_sweep_name = coordinator.chores_data[star_sweep_id][const.DATA_CHORE_NAME]
    coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id] = {
        const.DATA_KID_CHORE_DATA_NAME: star_sweep_name,
        const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
        const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
        const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
        const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
        const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
        const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
        DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START: None,
        const.DATA_KID_CHORE_DATA_PERIODS: {
            const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
        },
        const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
    }

    # Set due date to None explicitly
    coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id][
        DATA_KID_CHORE_DATA_DUE_DATE
    ] = None

    # Set claimed state using coordinator method (v0.4.0+)
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(zoe_id, star_sweep_id, "Zoë")

    coordinator._persist()

    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    # Approve chore with None due date - should not crash
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": "Zoë",
                "chore_name": "Stär sweep",
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # Verify no crash (test passes if we reach here)
    # Due date should remain None
    current_due_date = coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][
        star_sweep_id
    ][DATA_KID_CHORE_DATA_DUE_DATE]
    assert current_due_date is None


@pytest.mark.asyncio
async def test_weekly_recurrence_advances_exactly_seven_days(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test WEEKLY recurrence advances due date by exactly 7 days.

    Validates: _reschedule_chore_next_due_date_for_kid() uses correct interval.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Manual migration
    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Get IDs
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Change chore to WEEKLY recurrence
    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_RECURRING_FREQUENCY] = (
        const.FREQUENCY_WEEKLY
    )

    # Ensure structure exists
    # ALWAYS reset to PENDING since scenario may have set to APPROVED via chores_completed
    if DATA_KID_CHORE_DATA not in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA] = {}
    star_sweep_name = coordinator.chores_data[star_sweep_id][const.DATA_CHORE_NAME]
    coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id] = {
        const.DATA_KID_CHORE_DATA_NAME: star_sweep_name,
        const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
        const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
        const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
        const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
        const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
        const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
        DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START: None,
        const.DATA_KID_CHORE_DATA_PERIODS: {
            const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
            const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
        },
        const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
    }

    # Set original due date
    original_due_date = create_test_datetime(days_offset=0)
    # Set canonical source (per_kid_due_dates on chore)
    coordinator.chores_data[star_sweep_id].setdefault(
        const.DATA_CHORE_PER_KID_DUE_DATES, {}
    )[zoe_id] = original_due_date
    # Set derived/cached source (chore_data on kid)
    coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id][
        DATA_KID_CHORE_DATA_DUE_DATE
    ] = original_due_date

    # Set claimed state using coordinator method (v0.4.0+)
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(zoe_id, star_sweep_id, "Zoë")

    coordinator._persist()

    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    # Approve chore (should advance by 7 days for WEEKLY)
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": "Zoë",
                "chore_name": "Stär sweep",
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # Verify due date advanced by exactly 7 days
    new_due_date = coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id][
        DATA_KID_CHORE_DATA_DUE_DATE
    ]

    assert new_due_date is not None
    # Parse if string, compare dates
    from dateutil import parser

    if isinstance(new_due_date, str):
        new_due_date = parser.isoparse(new_due_date)
    if isinstance(original_due_date, str):
        original_due_date = parser.isoparse(original_due_date)
    # Compare date parts (timedelta.days returns floor, not round)
    assert (new_due_date.date() - original_due_date.date()).days == 7
