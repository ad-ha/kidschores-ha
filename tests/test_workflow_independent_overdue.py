"""Test INDEPENDENT chore overdue detection (per-kid due dates).

Tests Phase 3 Sprint 1 Phase C: INDEPENDENT mode per-kid overdue checking.
Validates that _check_overdue_chores() correctly branches based on completion_criteria.

Priority: P1 CRITICAL
Coverage: Overdue detection for INDEPENDENT chores with per-kid due dates
"""

# pylint: disable=protected-access  # Accessing coordinator._check_overdue_chores()
# pylint: disable=redefined-outer-name  # Pytest fixtures redefine names
# pylint: disable=unused-argument  # Fixtures needed for test setup
# pylint: disable=unused-variable  # name_to_id_map unpacking

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kidschores import const
from custom_components.kidschores.const import (
    COMPLETION_CRITERIA_INDEPENDENT,
    COORDINATOR,
    DATA_CHORE_COMPLETION_CRITERIA,
    DATA_CHORE_DUE_DATE,
    DATA_KID_CHORE_DATA,
    DATA_KID_OVERDUE_CHORES,
    DOMAIN,
)
from custom_components.kidschores.migration_pre_v42 import PreV42Migrator
from tests.conftest import create_test_datetime


@pytest.mark.asyncio
async def test_independent_one_kid_overdue_others_not(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test INDEPENDENT chore: one kid overdue, others not.

    Validates that _check_overdue_chores() correctly uses per-kid due dates
    and only marks Zoë as overdue (past due date), not Max! or Lila (future).
    """
    # Load data via config flow
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Manual migration: Convert is_shared → completion_criteria
    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Get IDs by name (never by index)
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    # Verify chore is INDEPENDENT
    chore_info = coordinator.chores_data[star_sweep_id]
    assert chore_info[DATA_CHORE_COMPLETION_CRITERIA] == COMPLETION_CRITERIA_INDEPENDENT

    # Get chore name for structure initialization
    star_sweep_name = coordinator.chores_data[star_sweep_id][const.DATA_CHORE_NAME]

    # Ensure chore_data structure exists for all kids with complete initialization
    # (Migration creates it, but be defensive)
    for kid_id in [zoe_id, max_id, lila_id]:
        if DATA_KID_CHORE_DATA not in coordinator.kids_data[kid_id]:
            coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA] = {}
        if star_sweep_id not in coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA]:
            coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA][star_sweep_id] = {
                const.DATA_KID_CHORE_DATA_NAME: star_sweep_name,
                const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
                const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
                const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
                const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
                const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
                const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
                const.DATA_KID_CHORE_DATA_PERIODS: {
                    const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
                },
                const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
            }

        # CRITICAL FIX: Clear claimed/approved timestamps to prevent early-return in _check_overdue_chores
        # v0.4.0+: Uses timestamp-based tracking instead of deprecated lists
        # The overdue check skips chores if kid has last_claimed or last_approved timestamps
        # For overdue tests, we need chores in PENDING state (not claimed/approved)
        # Note: Must modify in place - .get() chains return copies!
        kid_chore_data = coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA]
        kid_chore_data[star_sweep_id][const.DATA_KID_CHORE_DATA_LAST_CLAIMED] = None
        kid_chore_data[star_sweep_id][const.DATA_KID_CHORE_DATA_LAST_APPROVED] = None

    # Set per-kid due dates in the chore-level DATA_CHORE_PER_KID_DUE_DATES structure
    # This is the SOURCE OF TRUTH for INDEPENDENT chores (Option A: Chore-Centric)
    if const.DATA_CHORE_PER_KID_DUE_DATES not in coordinator.chores_data[star_sweep_id]:
        coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES] = {}

    # Zoë: overdue (2 days ago)
    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        zoe_id
    ] = create_test_datetime(days_offset=-2)

    # Max!: future (tomorrow)
    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        max_id
    ] = create_test_datetime(days_offset=1)

    # Lila: future (5 days from now)
    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        lila_id
    ] = create_test_datetime(days_offset=5)

    coordinator._persist()

    # Mock notification to verify only Zoë notified
    with (
        patch.object(
            coordinator, "_notify_kid_translated", new=AsyncMock()
        ) as mock_notify,
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Trigger overdue check
        await coordinator._check_overdue_chores()

        # Verify only Zoë marked overdue
        assert star_sweep_id in coordinator.kids_data[zoe_id].get(
            DATA_KID_OVERDUE_CHORES, []
        )
        assert star_sweep_id not in coordinator.kids_data[max_id].get(
            DATA_KID_OVERDUE_CHORES, []
        )
        assert star_sweep_id not in coordinator.kids_data[lila_id].get(
            DATA_KID_OVERDUE_CHORES, []
        )

        # Verify notification sent to Zoë only
        assert mock_notify.call_count == 1
        # Get the kid_id from the first call
        notified_kid_id = mock_notify.call_args_list[0][0][0]
        assert notified_kid_id == zoe_id


@pytest.mark.asyncio
async def test_independent_all_kids_overdue(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test INDEPENDENT chore: all kids overdue.

    Validates that all kids are marked overdue when all per-kid due dates
    have passed.
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
    lila_id = name_to_id_map["kid:Lila"]

    # Ensure chore_data structure exists with complete initialization
    for kid_id in [zoe_id, max_id, lila_id]:
        if DATA_KID_CHORE_DATA not in coordinator.kids_data[kid_id]:
            coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA] = {}
        if star_sweep_id not in coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA]:
            star_sweep_name = coordinator.chores_data[star_sweep_id][
                const.DATA_CHORE_NAME
            ]
            coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA][star_sweep_id] = {
                const.DATA_KID_CHORE_DATA_NAME: star_sweep_name,
                const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
                const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
                const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
                const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
                const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
                const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
                const.DATA_KID_CHORE_DATA_PERIODS: {
                    const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
                },
                const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
            }

        # CRITICAL FIX: Clear claimed/approved timestamps to prevent early-return in _check_overdue_chores
        # v0.4.0+: Uses timestamp-based tracking instead of deprecated lists
        # Note: Must modify in place - .get() chains return copies!
        kid_chore_data = coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA]
        kid_chore_data[star_sweep_id][const.DATA_KID_CHORE_DATA_LAST_CLAIMED] = None
        kid_chore_data[star_sweep_id][const.DATA_KID_CHORE_DATA_LAST_APPROVED] = None

    # Set all per-kid due dates in the past (chore-level DATA_CHORE_PER_KID_DUE_DATES)
    if const.DATA_CHORE_PER_KID_DUE_DATES not in coordinator.chores_data[star_sweep_id]:
        coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES] = {}

    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        zoe_id
    ] = create_test_datetime(days_offset=-1)

    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        max_id
    ] = create_test_datetime(days_offset=-2)

    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        lila_id
    ] = create_test_datetime(days_offset=-3)

    coordinator._persist()

    # Mock notifications
    with (
        patch.object(
            coordinator, "_notify_kid_translated", new=AsyncMock()
        ) as mock_notify,
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await coordinator._check_overdue_chores()

        # Verify ALL kids marked overdue
        assert star_sweep_id in coordinator.kids_data[zoe_id].get(
            DATA_KID_OVERDUE_CHORES, []
        )
        assert star_sweep_id in coordinator.kids_data[max_id].get(
            DATA_KID_OVERDUE_CHORES, []
        )
        assert star_sweep_id in coordinator.kids_data[lila_id].get(
            DATA_KID_OVERDUE_CHORES, []
        )

        # Verify 3 notifications sent (one per kid)
        assert mock_notify.call_count == 3


@pytest.mark.asyncio
async def test_independent_null_due_date_never_overdue(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test INDEPENDENT chore: null due dates never become overdue.

    Validates that chores with no due date are never marked overdue.
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
    lila_id = name_to_id_map["kid:Lila"]

    # Ensure chore_data structure exists
    for kid_id in [zoe_id, max_id, lila_id]:
        if DATA_KID_CHORE_DATA not in coordinator.kids_data[kid_id]:
            coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA] = {}
        if star_sweep_id not in coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA]:
            coordinator.kids_data[kid_id][DATA_KID_CHORE_DATA][star_sweep_id] = {}

    # Set all per-kid due dates to None (null) in chore-level per_kid_due_dates
    if const.DATA_CHORE_PER_KID_DUE_DATES not in coordinator.chores_data[star_sweep_id]:
        coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES] = {}

    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        zoe_id
    ] = None
    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        max_id
    ] = None
    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        lila_id
    ] = None

    coordinator._persist()

    # Mock notifications
    with (
        patch.object(
            coordinator, "_notify_kid_translated", new=AsyncMock()
        ) as mock_notify,
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await coordinator._check_overdue_chores()

        # Verify NO kids marked overdue (null = no deadline)
        assert star_sweep_id not in coordinator.kids_data[zoe_id].get(
            DATA_KID_OVERDUE_CHORES, []
        )
        assert star_sweep_id not in coordinator.kids_data[max_id].get(
            DATA_KID_OVERDUE_CHORES, []
        )
        assert star_sweep_id not in coordinator.kids_data[lila_id].get(
            DATA_KID_OVERDUE_CHORES, []
        )

        # Verify zero notifications
        assert mock_notify.call_count == 0


@pytest.mark.asyncio
async def test_shared_chore_all_kids_same_due_date(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test SHARED chore uses chore-level due date (not per-kid).

    Validates that SHARED chores correctly use chore-level due date
    affecting all assigned kids.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Manual migration (converts INDEPENDENT chores, leaves SHARED alone)
    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Find a SHARED chore (scenario_full should have one)
    shared_chore_id = None
    for chore_id, chore_info in coordinator.chores_data.items():
        completion_criteria = chore_info.get(DATA_CHORE_COMPLETION_CRITERIA, "")
        if completion_criteria in ["shared_all", "shared_first", "alternating"]:
            shared_chore_id = chore_id
            break

    if shared_chore_id is None:
        pytest.skip("No SHARED chore found in scenario_full")

    # Get assigned kids
    chore_info = coordinator.chores_data[shared_chore_id]
    assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])

    if len(assigned_kids) < 2:
        pytest.skip("SHARED chore must have at least 2 assigned kids")

    # Set chore-level due date to past (overdue)
    coordinator.chores_data[shared_chore_id][DATA_CHORE_DUE_DATE] = (
        create_test_datetime(days_offset=-1)
    )
    coordinator._persist()

    # Mock notifications
    with (
        patch.object(
            coordinator, "_notify_kid_translated", new=AsyncMock()
        ) as mock_notify,
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await coordinator._check_overdue_chores()

        # Verify ALL assigned kids marked overdue (SHARED = chore-level date)
        for kid_id in assigned_kids:
            overdue_list = coordinator.kids_data[kid_id].get(
                DATA_KID_OVERDUE_CHORES, []
            )
            assert shared_chore_id in overdue_list

        # Verify notifications sent to ALL assigned kids
        assert mock_notify.call_count == len(assigned_kids)


@pytest.mark.asyncio
async def test_independent_overdue_clears_when_date_advances(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test overdue status clears when per-kid due date advances to future.

    Validates that overdue status is removed when due date is updated.
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

    # Ensure chore_data structure exists with complete initialization
    if DATA_KID_CHORE_DATA not in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA] = {}
    if star_sweep_id not in coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA]:
        star_sweep_name = coordinator.chores_data[star_sweep_id][const.DATA_CHORE_NAME]
        coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id] = {
            const.DATA_KID_CHORE_DATA_NAME: star_sweep_name,
            const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
            const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
            const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
            const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
            const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
            const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
            const.DATA_KID_CHORE_DATA_PERIODS: {
                const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
            },
            const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
        }

    # CRITICAL FIX: Clear claimed/approved timestamps to prevent early-return in _check_overdue_chores
    # v0.4.0+: Uses timestamp-based tracking instead of deprecated lists
    # The overdue check skips chores if kid has last_claimed or last_approved timestamps
    # For overdue tests, we need chores in PENDING state (not claimed/approved)
    # Note: Must modify in place - .get() chains return copies!
    kid_chore_data = coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA]
    kid_chore_data[star_sweep_id][const.DATA_KID_CHORE_DATA_LAST_CLAIMED] = None
    kid_chore_data[star_sweep_id][const.DATA_KID_CHORE_DATA_LAST_APPROVED] = None

    # Set Zoë's due date to past (overdue) in chore-level per_kid_due_dates
    if const.DATA_CHORE_PER_KID_DUE_DATES not in coordinator.chores_data[star_sweep_id]:
        coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES] = {}
    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        zoe_id
    ] = create_test_datetime(days_offset=-2)
    coordinator._persist()

    # Trigger overdue check - Zoë should be marked overdue
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await coordinator._check_overdue_chores()

    # Verify Zoë marked overdue
    assert star_sweep_id in coordinator.kids_data[zoe_id].get(
        DATA_KID_OVERDUE_CHORES, []
    )

    # Update Zoë's due date to future (no longer overdue) in chore-level per_kid_due_dates
    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        zoe_id
    ] = create_test_datetime(days_offset=1)
    coordinator._persist()

    # Trigger overdue check again
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await coordinator._check_overdue_chores()

    # Verify Zoë NO LONGER overdue
    assert star_sweep_id not in coordinator.kids_data[zoe_id].get(
        DATA_KID_OVERDUE_CHORES, []
    )


@pytest.mark.asyncio
async def test_independent_skip_claimed_chores(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test overdue checking skips chores already claimed by kid.

    Validates that claimed chores are excluded from overdue detection.
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

    # Ensure chore_data structure exists with complete initialization
    if DATA_KID_CHORE_DATA not in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA] = {}
    if star_sweep_id not in coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA]:
        star_sweep_name = coordinator.chores_data[star_sweep_id][const.DATA_CHORE_NAME]
        coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id] = {
            const.DATA_KID_CHORE_DATA_NAME: star_sweep_name,
            const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
            const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
            const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
            const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
            const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
            const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
            const.DATA_KID_CHORE_DATA_PERIODS: {
                const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
            },
            const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
        }

    # Set Zoë's due date to past (would be overdue) in chore-level per_kid_due_dates
    if const.DATA_CHORE_PER_KID_DUE_DATES not in coordinator.chores_data[star_sweep_id]:
        coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES] = {}
    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        zoe_id
    ] = create_test_datetime(days_offset=-2)

    # Mark chore as claimed by Zoë (v0.4.0+ timestamp-based tracking)
    if const.DATA_KID_CHORE_DATA not in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][const.DATA_KID_CHORE_DATA] = {}
    if star_sweep_id not in coordinator.kids_data[zoe_id][const.DATA_KID_CHORE_DATA]:
        coordinator.kids_data[zoe_id][const.DATA_KID_CHORE_DATA][star_sweep_id] = {}
    coordinator.kids_data[zoe_id][const.DATA_KID_CHORE_DATA][star_sweep_id][
        const.DATA_KID_CHORE_DATA_LAST_CLAIMED
    ] = create_test_datetime(days_offset=0)  # Claimed now

    coordinator._persist()

    # Mock notifications
    with (
        patch.object(
            coordinator, "_notify_kid_translated", new=AsyncMock()
        ) as mock_notify,
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await coordinator._check_overdue_chores()

        # Verify Zoë NOT marked overdue (claimed chores excluded)
        assert star_sweep_id not in coordinator.kids_data[zoe_id].get(
            DATA_KID_OVERDUE_CHORES, []
        )

        # Verify no notification sent
        assert mock_notify.call_count == 0


@pytest.mark.asyncio
async def test_independent_skip_approved_chores(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test overdue checking skips chores already approved for kid.

    Validates that approved chores are excluded from overdue detection.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Manual migration
    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Get IDs
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    max_id = name_to_id_map["kid:Max!"]

    # Ensure chore_data structure exists with complete initialization
    if DATA_KID_CHORE_DATA not in coordinator.kids_data[max_id]:
        coordinator.kids_data[max_id][DATA_KID_CHORE_DATA] = {}
    if star_sweep_id not in coordinator.kids_data[max_id][DATA_KID_CHORE_DATA]:
        star_sweep_name = coordinator.chores_data[star_sweep_id][const.DATA_CHORE_NAME]
        coordinator.kids_data[max_id][DATA_KID_CHORE_DATA][star_sweep_id] = {
            const.DATA_KID_CHORE_DATA_NAME: star_sweep_name,
            const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
            const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
            const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
            const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
            const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
            const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
            const.DATA_KID_CHORE_DATA_PERIODS: {
                const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
            },
            const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
        }

    # Set Max!'s due date to past (would be overdue) in chore-level per_kid_due_dates
    if const.DATA_CHORE_PER_KID_DUE_DATES not in coordinator.chores_data[star_sweep_id]:
        coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES] = {}
    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        max_id
    ] = create_test_datetime(days_offset=-2)

    # Mark chore as approved for Max! (v0.4.0+ timestamp-based tracking)
    if const.DATA_KID_CHORE_DATA not in coordinator.kids_data[max_id]:
        coordinator.kids_data[max_id][const.DATA_KID_CHORE_DATA] = {}
    if star_sweep_id not in coordinator.kids_data[max_id][const.DATA_KID_CHORE_DATA]:
        coordinator.kids_data[max_id][const.DATA_KID_CHORE_DATA][star_sweep_id] = {}
    coordinator.kids_data[max_id][const.DATA_KID_CHORE_DATA][star_sweep_id][
        const.DATA_KID_CHORE_DATA_LAST_APPROVED
    ] = create_test_datetime(days_offset=0)  # Approved now
    # Also set approval_period_start to make it valid for current period
    coordinator.kids_data[max_id][const.DATA_KID_CHORE_DATA][star_sweep_id][
        const.DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START
    ] = create_test_datetime(days_offset=-1)  # Period started yesterday

    coordinator._persist()

    # Mock notifications
    with (
        patch.object(
            coordinator, "_notify_kid_translated", new=AsyncMock()
        ) as mock_notify,
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await coordinator._check_overdue_chores()

        # Verify Max! NOT marked overdue (approved chores excluded)
        assert star_sweep_id not in coordinator.kids_data[max_id].get(
            DATA_KID_OVERDUE_CHORES, []
        )

        # Verify no notification sent
        assert mock_notify.call_count == 0


@pytest.mark.asyncio
async def test_mixed_independent_and_shared_chores(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test overdue checking with both INDEPENDENT and SHARED chores.

    Validates that branching logic correctly handles mixed chore types.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Manual migration
    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Get INDEPENDENT chore
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Ensure chore_data structure exists with complete initialization
    if DATA_KID_CHORE_DATA not in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA] = {}
    if star_sweep_id not in coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA]:
        star_sweep_name = coordinator.chores_data[star_sweep_id][const.DATA_CHORE_NAME]
        coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][star_sweep_id] = {
            const.DATA_KID_CHORE_DATA_NAME: star_sweep_name,
            const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
            const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
            const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
            const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
            const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
            const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
            const.DATA_KID_CHORE_DATA_PERIODS: {
                const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
            },
            const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
        }

    # Find SHARED chore
    shared_chore_id = None
    for chore_id, chore_info in coordinator.chores_data.items():
        completion_criteria = chore_info.get(DATA_CHORE_COMPLETION_CRITERIA, "")
        if completion_criteria in ["shared_all", "shared_first", "alternating"]:
            shared_chore_id = chore_id
            break

    if shared_chore_id is None:
        pytest.skip("No SHARED chore found in scenario_full")

    # Clear approved/claimed status for Zoë (so chore can be marked overdue)
    # v0.4.0: Use timestamp-based chore_data instead of deprecated lists
    if DATA_KID_CHORE_DATA in coordinator.kids_data[zoe_id]:
        if star_sweep_id in coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA]:
            chore_entry = coordinator.kids_data[zoe_id][DATA_KID_CHORE_DATA][
                star_sweep_id
            ]
            # Clear timestamps to indicate not claimed/approved
            chore_entry[const.DATA_KID_CHORE_DATA_LAST_CLAIMED] = None
            chore_entry[const.DATA_KID_CHORE_DATA_LAST_APPROVED] = None
            chore_entry[const.DATA_KID_CHORE_DATA_STATE] = const.CHORE_STATE_PENDING

    # Set INDEPENDENT chore overdue for Zoë only (per-kid date in chore-level structure)
    if const.DATA_CHORE_PER_KID_DUE_DATES not in coordinator.chores_data[star_sweep_id]:
        coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES] = {}
    coordinator.chores_data[star_sweep_id][const.DATA_CHORE_PER_KID_DUE_DATES][
        zoe_id
    ] = create_test_datetime(days_offset=-1)

    # Set SHARED chore overdue (chore-level date affects all)
    coordinator.chores_data[shared_chore_id][DATA_CHORE_DUE_DATE] = (
        create_test_datetime(days_offset=-1)
    )

    coordinator._persist()

    # Mock notifications
    with (
        patch.object(
            coordinator, "_notify_kid_translated", new=AsyncMock()
        ) as mock_notify,
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await coordinator._check_overdue_chores()

        # Verify INDEPENDENT uses per-kid date (Zoë only)
        assert star_sweep_id in coordinator.kids_data[zoe_id].get(
            DATA_KID_OVERDUE_CHORES, []
        )

        # Verify SHARED uses chore-level date (all assigned kids)
        shared_assigned_kids = coordinator.chores_data[shared_chore_id].get(
            const.DATA_CHORE_ASSIGNED_KIDS, []
        )
        for kid_id in shared_assigned_kids:
            assert shared_chore_id in coordinator.kids_data[kid_id].get(
                DATA_KID_OVERDUE_CHORES, []
            )

        # Verify notifications sent (1 for Zoë's INDEPENDENT + N for SHARED kids)
        expected_count = 1 + len(shared_assigned_kids)
        assert mock_notify.call_count == expected_count
