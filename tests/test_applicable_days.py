"""Test applicable_days behavior (Option C Testing - Category 7).

Tests weekday filtering behavior via applicable_days configuration:
- Due date snap-to-applicable-day logic
- Calendar event generation filtering
- Rescheduling respects applicable_days
- Edge cases: empty list, single day, weekend-only

Priority: P3 MEDIUM (Affects scheduling accuracy)
Coverage: coordinator._calculate_next_due_date_from_info, kc_helpers.get_next_applicable_day
"""

# pylint: disable=protected-access
# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.kidschores import const
from custom_components.kidschores.const import (
    COMPLETION_CRITERIA_INDEPENDENT,
    COORDINATOR,
    DATA_CHORE_APPLICABLE_DAYS,
    DATA_CHORE_COMPLETION_CRITERIA,
    DATA_CHORE_DUE_DATE,
    DATA_CHORE_PER_KID_DUE_DATES,
    DATA_CHORE_RECURRING_FREQUENCY,
    DOMAIN,
    FREQUENCY_DAILY,
    FREQUENCY_WEEKLY,
)
from custom_components.kidschores.migration_pre_v42 import PreV42Migrator
from tests.conftest import reset_chore_state_for_kid

# ============================================================================
# Test: Empty applicable_days (No Filtering)
# ============================================================================


@pytest.mark.asyncio
async def test_empty_applicable_days_no_filtering(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test empty applicable_days list means no weekday filtering.

    Validates: With no applicable_days, due date advances normally without weekday snapping.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Get a daily recurring chore
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # Ensure no applicable_days (empty list)
    chore_info[DATA_CHORE_APPLICABLE_DAYS] = []
    chore_info[DATA_CHORE_RECURRING_FREQUENCY] = FREQUENCY_DAILY

    # Set initial due date (known weekday: e.g., Monday)
    # Using a Monday at noon UTC
    monday = dt_util.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:  # Advance to Monday
        monday += timedelta(days=1)

    per_kid_due_dates = chore_info.setdefault(DATA_CHORE_PER_KID_DUE_DATES, {})
    per_kid_due_dates[zoe_id] = monday.isoformat()
    coordinator._persist()

    # Clear state using v0.4.0+ timestamp-based approach
    reset_chore_state_for_kid(coordinator, zoe_id, star_sweep_id)
    coordinator._persist()

    # Mock notifications and approve
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.approve_chore("parent", zoe_id, star_sweep_id)

    # Verify due date advanced without weekday snapping
    # Daily recurring should advance to next day (Tuesday, or future based on now)
    new_due_str = per_kid_due_dates.get(zoe_id)
    assert new_due_str is not None, "Due date should be set"
    new_due = dt_util.parse_datetime(new_due_str)
    assert new_due > dt_util.utcnow(), "New due date should be in the future"


# ============================================================================
# Test: Single applicable_day (Specific Weekday Only)
# ============================================================================


@pytest.mark.asyncio
async def test_single_applicable_day_snaps_to_weekday(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test single applicable_day snaps due date to that weekday.

    Validates: If applicable_days=[0] (Monday only), rescheduling always lands on Monday.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # Configure Monday-only applicable days (weekday 0 = Monday)
    chore_info[DATA_CHORE_APPLICABLE_DAYS] = [0]
    chore_info[DATA_CHORE_RECURRING_FREQUENCY] = FREQUENCY_DAILY

    # Set initial due date to a Wednesday
    wednesday = dt_util.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
    while wednesday.weekday() != 2:  # Advance to Wednesday
        wednesday += timedelta(days=1)
    wednesday = wednesday - timedelta(days=7)  # Go back a week (past)

    per_kid_due_dates = chore_info.setdefault(DATA_CHORE_PER_KID_DUE_DATES, {})
    per_kid_due_dates[zoe_id] = wednesday.isoformat()
    coordinator._persist()

    # Clear state using v0.4.0+ timestamp-based approach
    reset_chore_state_for_kid(coordinator, zoe_id, star_sweep_id)
    coordinator._persist()

    # Mock notifications and approve
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.approve_chore("parent", zoe_id, star_sweep_id)

    # Verify due date landed on Monday
    new_due_str = per_kid_due_dates.get(zoe_id)
    assert new_due_str is not None, "Due date should be set"
    new_due = dt_util.parse_datetime(new_due_str)
    assert new_due is not None
    assert new_due.weekday() == 0, (
        f"New due date should be Monday, got weekday {new_due.weekday()}"
    )


# ============================================================================
# Test: Weekend-Only applicable_days
# ============================================================================


@pytest.mark.asyncio
async def test_weekend_only_applicable_days(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test weekend-only (Sat/Sun) applicable_days filtering.

    Validates: Chore only scheduled for weekdays 5 (Sat) or 6 (Sun).
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # Configure weekend-only: Saturday (5) and Sunday (6)
    chore_info[DATA_CHORE_APPLICABLE_DAYS] = [5, 6]
    chore_info[DATA_CHORE_RECURRING_FREQUENCY] = FREQUENCY_WEEKLY

    # Set initial due date to a weekday (Tuesday)
    tuesday = dt_util.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
    while tuesday.weekday() != 1:  # Advance to Tuesday
        tuesday += timedelta(days=1)
    tuesday = tuesday - timedelta(days=14)  # Go back 2 weeks (past)

    per_kid_due_dates = chore_info.setdefault(DATA_CHORE_PER_KID_DUE_DATES, {})
    per_kid_due_dates[zoe_id] = tuesday.isoformat()
    coordinator._persist()

    # Clear state using v0.4.0+ timestamp-based approach
    reset_chore_state_for_kid(coordinator, zoe_id, star_sweep_id)
    coordinator._persist()

    # Mock notifications and approve
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.approve_chore("parent", zoe_id, star_sweep_id)

    # Verify due date landed on a weekend day
    new_due_str = per_kid_due_dates.get(zoe_id)
    assert new_due_str is not None, "Due date should be set"
    new_due = dt_util.parse_datetime(new_due_str)
    assert new_due is not None
    assert new_due.weekday() in [5, 6], (
        f"Due should be weekend, got weekday {new_due.weekday()}"
    )


# ============================================================================
# Test: String-Based applicable_days Conversion
# ============================================================================


@pytest.mark.asyncio
async def test_string_based_applicable_days_conversion(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test string-based applicable_days (e.g., ['monday', 'friday']) are converted.

    Validates: WEEKDAY_OPTIONS mapping converts strings to integers correctly.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # Configure string-based weekday names using short format (from const.WEEKDAY_OPTIONS)
    # "mon"=0, "fri"=4 in WEEKDAY_OPTIONS.keys() order
    chore_info[DATA_CHORE_APPLICABLE_DAYS] = ["mon", "fri"]
    chore_info[DATA_CHORE_RECURRING_FREQUENCY] = FREQUENCY_DAILY

    # Set initial due date to a Wednesday in the past
    wednesday = dt_util.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
    while wednesday.weekday() != 2:
        wednesday += timedelta(days=1)
    wednesday = wednesday - timedelta(days=7)  # Past

    per_kid_due_dates = chore_info.setdefault(DATA_CHORE_PER_KID_DUE_DATES, {})
    per_kid_due_dates[zoe_id] = wednesday.isoformat()
    coordinator._persist()

    # Clear state using v0.4.0+ timestamp-based approach
    reset_chore_state_for_kid(coordinator, zoe_id, star_sweep_id)
    coordinator._persist()

    # Mock notifications and approve
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.approve_chore("parent", zoe_id, star_sweep_id)

    # Verify due date landed on Monday (0) or Friday (4)
    new_due_str = per_kid_due_dates.get(zoe_id)
    assert new_due_str is not None, "Due date should be set"
    new_due = dt_util.parse_datetime(new_due_str)
    assert new_due is not None
    assert new_due.weekday() in [0, 4], (
        f"Due should be Monday(0) or Friday(4), got weekday {new_due.weekday()}"
    )


# ============================================================================
# Test: Weekday Filter with INDEPENDENT Per-Kid Due Dates
# ============================================================================


@pytest.mark.asyncio
async def test_applicable_days_independent_per_kid_isolation(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test applicable_days filtering applies per-kid for INDEPENDENT chores.

    Validates: Each kid's due date snaps independently based on their approval time.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # Configure Tuesday-only (weekday 1)
    chore_info[DATA_CHORE_APPLICABLE_DAYS] = [1]  # Tuesday
    chore_info[DATA_CHORE_RECURRING_FREQUENCY] = FREQUENCY_DAILY
    assert (
        chore_info.get(DATA_CHORE_COMPLETION_CRITERIA)
        == COMPLETION_CRITERIA_INDEPENDENT
    )

    # Set different initial due dates for each kid
    monday = dt_util.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:
        monday += timedelta(days=1)
    past_monday = monday - timedelta(days=7)

    per_kid_due_dates = chore_info.setdefault(DATA_CHORE_PER_KID_DUE_DATES, {})
    per_kid_due_dates[zoe_id] = past_monday.isoformat()
    per_kid_due_dates[max_id] = past_monday.isoformat()
    coordinator._persist()

    # Clear state for both kids using timestamp-based reset
    for kid_id in [zoe_id, max_id]:
        reset_chore_state_for_kid(coordinator, kid_id, star_sweep_id)
    coordinator._persist()

    # Approve only Zoë
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.approve_chore("parent", zoe_id, star_sweep_id)

    # Verify Zoë's due date snapped to Tuesday
    zoe_due_str = per_kid_due_dates.get(zoe_id)
    assert zoe_due_str is not None
    zoe_due = dt_util.parse_datetime(zoe_due_str)
    assert zoe_due is not None
    assert zoe_due.weekday() == 1, (
        f"Zoë should have Tuesday, got weekday {zoe_due.weekday()}"
    )

    # Verify Max's due date is unchanged (still past Monday)
    max_due_str = per_kid_due_dates.get(max_id)
    assert max_due_str == past_monday.isoformat(), "Max's due date should be unchanged"


# ============================================================================
# Test: get_next_applicable_day Helper Function
# ============================================================================


@pytest.mark.asyncio
async def test_get_next_applicable_day_same_day(
    hass: HomeAssistant,
    scenario_full,
) -> None:
    """Test get_next_applicable_day returns same day if already applicable.

    Validates: If input weekday is in applicable_days, no advancement needed.
    """
    from custom_components.kidschores import kc_helpers as kh

    # Monday input, applicable_days includes Monday
    monday = datetime(2025, 1, 6, 12, 0, tzinfo=dt_util.UTC)  # 2025-01-06 is Monday
    assert monday.weekday() == 0

    result = kh.get_next_applicable_day(
        monday,
        applicable_days=[0, 2, 4],  # Mon, Wed, Fri
        return_type=const.HELPER_RETURN_DATETIME,
    )

    # Should return same day since Monday is in applicable list
    assert result.weekday() == 0
    assert result.date() == monday.date()


@pytest.mark.asyncio
async def test_get_next_applicable_day_advances_to_next(
    hass: HomeAssistant,
    scenario_full,
) -> None:
    """Test get_next_applicable_day advances to next applicable day.

    Validates: Tuesday input with Monday-only applicable → advances to next Monday.
    """
    from custom_components.kidschores import kc_helpers as kh

    # Tuesday input, applicable_days is Monday only
    tuesday = datetime(2025, 1, 7, 12, 0, tzinfo=dt_util.UTC)  # 2025-01-07 is Tuesday
    assert tuesday.weekday() == 1

    result = kh.get_next_applicable_day(
        tuesday,
        applicable_days=[0],  # Monday only
        return_type=const.HELPER_RETURN_DATETIME,
    )

    # Should advance to Monday (6 days later)
    assert result.weekday() == 0  # Monday
    assert result > tuesday  # Must be in the future


@pytest.mark.asyncio
async def test_get_next_applicable_day_weekend_skip(
    hass: HomeAssistant,
    scenario_full,
) -> None:
    """Test get_next_applicable_day skips weekends for weekday-only chores.

    Validates: Friday input with Mon-Fri applicable → returns same Friday.
              Saturday input with Mon-Fri applicable → advances to Monday.
    """
    from custom_components.kidschores import kc_helpers as kh

    # Friday input, weekdays only (Mon-Fri = 0-4)
    friday = datetime(2025, 1, 10, 12, 0, tzinfo=dt_util.UTC)  # 2025-01-10 is Friday
    assert friday.weekday() == 4

    result = kh.get_next_applicable_day(
        friday,
        applicable_days=[0, 1, 2, 3, 4],  # Mon-Fri
        return_type=const.HELPER_RETURN_DATETIME,
    )
    assert result.weekday() == 4  # Still Friday

    # Saturday input, weekdays only
    saturday = datetime(
        2025, 1, 11, 12, 0, tzinfo=dt_util.UTC
    )  # 2025-01-11 is Saturday
    assert saturday.weekday() == 5

    result = kh.get_next_applicable_day(
        saturday,
        applicable_days=[0, 1, 2, 3, 4],  # Mon-Fri
        return_type=const.HELPER_RETURN_DATETIME,
    )
    assert result.weekday() == 0  # Advances to Monday
    assert result > saturday


# ============================================================================
# Test: Integration with Rescheduling Logic
# ============================================================================


@pytest.mark.asyncio
async def test_calculate_next_due_date_with_applicable_days(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test _calculate_next_due_date_from_info applies applicable_days snapping.

    Validates: The coordinator method correctly integrates weekday filtering.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    star_sweep_id = name_to_id_map["chore:Stär sweep"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # Configure Thursday-only (weekday 3)
    chore_info[DATA_CHORE_APPLICABLE_DAYS] = [3]  # Thursday
    chore_info[DATA_CHORE_RECURRING_FREQUENCY] = FREQUENCY_DAILY

    # Find the next Monday from now (use future dates to avoid require_future issues)
    monday = dt_util.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:  # Advance to Monday
        monday += timedelta(days=1)
    chore_info[DATA_CHORE_DUE_DATE] = monday.isoformat()

    # Call the internal method directly (current_due_utc, chore_info)
    result = coordinator._calculate_next_due_date_from_info(monday, chore_info)

    # Result should be Thursday (next applicable day after daily advance)
    assert result is not None
    assert result.weekday() == 3, (
        f"Expected Thursday (3), got weekday {result.weekday()}"
    )
    assert result > monday


@pytest.mark.asyncio
async def test_weekly_frequency_with_applicable_days_override(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test weekly frequency combined with applicable_days produces correct snapping.

    Validates: Weekly advance + applicable_days snap = correct final date.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    star_sweep_id = name_to_id_map["chore:Stär sweep"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # Configure Wednesday-only (weekday 2) with weekly frequency
    chore_info[DATA_CHORE_APPLICABLE_DAYS] = [2]  # Wednesday
    chore_info[DATA_CHORE_RECURRING_FREQUENCY] = FREQUENCY_WEEKLY

    # Find the next Monday from now (use future dates)
    monday = dt_util.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:  # Advance to Monday
        monday += timedelta(days=1)
    chore_info[DATA_CHORE_DUE_DATE] = monday.isoformat()

    # Calculate next due date (current_due_utc, chore_info)
    result = coordinator._calculate_next_due_date_from_info(monday, chore_info)

    # Weekly advance from Monday → next Monday
    # Then snap to Wednesday
    assert result is not None
    assert result.weekday() == 2, (
        f"Expected Wednesday (2), got weekday {result.weekday()}"
    )
    assert result > monday


# ============================================================================
# Test: Edge Case - All Days Applicable (Full Week)
# ============================================================================


@pytest.mark.asyncio
async def test_all_days_applicable_no_snapping(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test all weekdays applicable results in no snapping needed.

    Validates: applicable_days=[0,1,2,3,4,5,6] behaves like empty list.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    star_sweep_id = name_to_id_map["chore:Stär sweep"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # All days applicable
    chore_info[DATA_CHORE_APPLICABLE_DAYS] = [0, 1, 2, 3, 4, 5, 6]
    chore_info[DATA_CHORE_RECURRING_FREQUENCY] = FREQUENCY_DAILY

    # Find the next Monday from now (use future dates)
    monday = dt_util.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:  # Advance to Monday
        monday += timedelta(days=1)
    chore_info[DATA_CHORE_DUE_DATE] = monday.isoformat()

    # Calculate next due date (current_due_utc, chore_info)
    result = coordinator._calculate_next_due_date_from_info(monday, chore_info)

    # Daily advance should go to Tuesday (next day), no snapping needed
    assert result is not None
    assert result.weekday() == 1, (
        f"Expected Tuesday (1), got weekday {result.weekday()}"
    )
    assert (result - monday).days >= 1  # At least 1 day advance
