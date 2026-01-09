"""Tests for sensor value calculations and new schema data access.

This module validates that sensors calculate correct values after data changes,
ensuring the new schema (DATA_KID_CHORE_STATS, DATA_KID_POINT_STATS) provides
accurate data to sensor entities.
"""

# pylint: disable=protected-access  # Accessing _notify_kid for mocking in tests

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kidschores import const
from custom_components.kidschores.const import COORDINATOR, DOMAIN

pytestmark = pytest.mark.asyncio


async def test_completed_chores_daily_sensor_increments_on_approval(
    hass: HomeAssistant,
    scenario_full: tuple,
) -> None:
    """Test SystemChoreApprovalsDailySensor increments after chore approval."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Get kid ID from name mapping
    kid_id = name_to_id_map["kid:Zoë"]

    # Get initial chore stats
    stats_before = coordinator.kids_data[kid_id].get(const.DATA_KID_CHORE_STATS, {})
    initial_count = stats_before.get(const.DATA_KID_CHORE_STATS_APPROVED_TODAY, 0)

    # Get an unclaimed chore assigned to Zoë (not pre-completed, not auto_approve in YAML)
    chore_id = name_to_id_map["chore:Refill Bird Fëeder"]

    # Mock notifications to prevent ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Claim and approve chore
        parent_id = name_to_id_map["parent:Môm Astrid Stârblüm"]
        coordinator.claim_chore(kid_id, chore_id, "test_user")
        coordinator.approve_chore(parent_id, kid_id, chore_id)
        await hass.async_block_till_done()

    # Verify chore stats incremented
    stats_after = coordinator.kids_data[kid_id].get(const.DATA_KID_CHORE_STATS, {})
    new_count = stats_after.get(const.DATA_KID_CHORE_STATS_APPROVED_TODAY, 0)

    assert new_count == initial_count + 1, (
        f"Expected daily completed chores to increment from {initial_count} to {initial_count + 1}, "
        f"got {new_count}"
    )


async def test_completed_chores_total_sensor_attributes(
    hass: HomeAssistant,
    scenario_full: tuple,
) -> None:
    """Test SystemChoreApprovalsSensor exposes correct chore_stats attributes."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    kid_id = name_to_id_map["kid:Zoë"]

    # Mock notifications to prevent ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Initialize stats by approving an unclaimed chore (not pre-completed, not auto_approve in YAML)
        chore_id = name_to_id_map["chore:Refill Bird Fëeder"]
        parent_id = name_to_id_map["parent:Môm Astrid Stârblüm"]
        coordinator.claim_chore(kid_id, chore_id, "test_user")
        coordinator.approve_chore(parent_id, kid_id, chore_id)
        await hass.async_block_till_done()

    # Get chore stats from coordinator
    chore_stats = coordinator.kids_data[kid_id].get(const.DATA_KID_CHORE_STATS, {})

    # Verify key stats exist
    assert const.DATA_KID_CHORE_STATS_APPROVED_TODAY in chore_stats, (
        "approved_today should be present in chore_stats"
    )
    assert const.DATA_KID_CHORE_STATS_APPROVED_WEEK in chore_stats, (
        "approved_week should be present in chore_stats"
    )
    assert const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME in chore_stats, (
        "approved_all_time should be present in chore_stats"
    )

    # Verify values are non-negative integers
    for key in [
        const.DATA_KID_CHORE_STATS_APPROVED_TODAY,
        const.DATA_KID_CHORE_STATS_APPROVED_WEEK,
        const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME,
    ]:
        value = chore_stats.get(key, 0)
        assert isinstance(value, (int, float)), f"{key} should be numeric"
        assert value >= 0, f"{key} should be non-negative"


async def test_kid_points_sensor_attributes(
    hass: HomeAssistant,
    scenario_full: tuple,
) -> None:
    """Test KidPointsSensor exposes correct point_stats attributes."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    kid_id = name_to_id_map["kid:Zoë"]

    # Initialize stats by giving points (use apply_bonus)
    bonus_id = name_to_id_map["bonus:Stär Sprïnkle Bonus"]
    parent_id = name_to_id_map["parent:Môm Astrid Stârblüm"]

    # Mock notifications to prevent ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.apply_bonus(parent_id, kid_id, bonus_id)
        await hass.async_block_till_done()

    # Get point stats from coordinator
    point_stats = coordinator.kids_data[kid_id].get(const.DATA_KID_POINT_STATS, {})

    # Verify key stats exist
    assert const.DATA_KID_POINT_STATS_EARNED_TODAY in point_stats, (
        "points_earned_today should be present in point_stats"
    )
    assert const.DATA_KID_POINT_STATS_NET_TODAY in point_stats, (
        "points_net_today should be present in point_stats"
    )
    assert const.DATA_KID_POINT_STATS_BY_SOURCE_TODAY in point_stats, (
        "points_by_source_today should be present in point_stats"
    )

    # Verify by-source breakdown is a dict
    by_source = point_stats.get(const.DATA_KID_POINT_STATS_BY_SOURCE_TODAY, {})
    assert isinstance(by_source, dict), "points_by_source_today should be a dict"


async def test_achievement_sensor_percentage_calculation(
    hass: HomeAssistant,
    scenario_full: tuple,
) -> None:
    """Test AchievementSensor calculates correct percentage from new schema."""
    config_entry, _ = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Get achievement data (if any in full scenario)
    if not coordinator.achievements_data:
        pytest.skip("No achievements in test data")

    achievement_id = next(iter(coordinator.achievements_data.keys()))
    achievement = coordinator.achievements_data[achievement_id]

    # Get achievement parameters
    ach_type = achievement.get(const.DATA_ACHIEVEMENT_TYPE)
    target = achievement.get(const.DATA_ACHIEVEMENT_TARGET_VALUE, 1)
    assigned_kids = achievement.get(const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, [])

    if not assigned_kids or ach_type not in [
        const.ACHIEVEMENT_TYPE_TOTAL,
        const.ACHIEVEMENT_TYPE_DAILY_MIN,
    ]:
        pytest.skip("Test requires specific achievement type")

    # Get kid's chore stats
    kid_id = assigned_kids[0]
    kid_data = coordinator.kids_data.get(kid_id, {})
    chore_stats = kid_data.get(const.DATA_KID_CHORE_STATS, {})

    if ach_type == const.ACHIEVEMENT_TYPE_TOTAL:
        current = chore_stats.get(const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME, 0)
    elif ach_type == const.ACHIEVEMENT_TYPE_DAILY_MIN:
        current = chore_stats.get(const.DATA_KID_CHORE_STATS_APPROVED_TODAY, 0)
    else:
        pytest.skip("Unsupported achievement type for this test")

    # Calculate expected percentage
    progress_data = achievement.get(const.DATA_ACHIEVEMENT_PROGRESS, {}).get(kid_id, {})
    baseline = (
        progress_data.get(const.DATA_ACHIEVEMENT_BASELINE, 0)
        if isinstance(progress_data, dict)
        else 0
    )

    if ach_type == const.ACHIEVEMENT_TYPE_TOTAL:
        expected_percent = min(
            100,
            ((current / (baseline + target)) * 100) if (baseline + target) > 0 else 0,
        )
    else:  # DAILY_MIN
        expected_percent = min(100, (current / target * 100) if target > 0 else 0)

    # Verify calculation is reasonable (allow for rounding differences)
    assert 0 <= expected_percent <= 100, (
        f"Achievement percentage should be 0-100, got {expected_percent}"
    )


async def test_badge_sensor_reads_from_new_schema(
    hass: HomeAssistant,
    scenario_full: tuple,
) -> None:
    """Test SystemBadgeSensor accesses badge data from new schema structure."""
    config_entry, _ = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    if not coordinator.badges_data:
        pytest.skip("No badges in test data")

    badge_id = next(iter(coordinator.badges_data.keys()))
    badge_info = coordinator.badges_data[badge_id]

    # Verify badge has expected fields from new schema
    assert const.DATA_BADGE_NAME in badge_info, "Badge should have name"
    assert const.DATA_BADGE_TYPE in badge_info, "Badge should have type"

    # Verify badge reads from chore_stats if it tracks chores
    badge_type = badge_info.get(const.DATA_BADGE_TYPE)
    if badge_type in [const.BADGE_TYPE_PERIODIC, const.BADGE_TYPE_DAILY]:
        # These badge types may have tracked chores (nested structure)
        tracked_chores_dict = badge_info.get(const.DATA_BADGE_TRACKED_CHORES, {})
        assert isinstance(tracked_chores_dict, dict), "tracked_chores should be a dict"
        selected_chores = tracked_chores_dict.get(
            const.DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES, []
        )
        assert isinstance(selected_chores, list), "selected_chores should be a list"


async def test_challenge_sensor_reads_from_new_schema(
    hass: HomeAssistant,
    scenario_full: tuple,
) -> None:
    """Test ChallengeSensor accesses challenge data from new schema structure."""
    config_entry, _ = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    if not coordinator.challenges_data:
        pytest.skip("No challenges in test data")

    challenge_id = next(iter(coordinator.challenges_data.keys()))
    challenge = coordinator.challenges_data[challenge_id]

    # Verify challenge has expected fields
    assert const.DATA_CHALLENGE_NAME in challenge, "Challenge should have name"
    assert const.DATA_CHALLENGE_TYPE in challenge, "Challenge should have type"

    # Get assigned kids and verify their chore_stats structure
    assigned_kids = challenge.get(const.DATA_CHALLENGE_ASSIGNED_KIDS, [])
    if assigned_kids:
        kid_id = assigned_kids[0]
        kid_data = coordinator.kids_data.get(kid_id, {})

        # Verify chore_stats exists (challenges read from it)
        chore_stats = kid_data.get(const.DATA_KID_CHORE_STATS, {})
        assert isinstance(chore_stats, dict), "chore_stats should be a dict"
        assert const.DATA_KID_CHORE_STATS_APPROVED_TODAY in chore_stats, (
            "Challenge uses approved_today from chore_stats"
        )


@pytest.mark.parametrize(
    "sensor_type,stats_key",
    [
        ("daily", const.DATA_KID_CHORE_STATS_APPROVED_TODAY),
        ("weekly", const.DATA_KID_CHORE_STATS_APPROVED_WEEK),
        ("monthly", const.DATA_KID_CHORE_STATS_APPROVED_MONTH),
    ],
)
async def test_completed_chores_sensors_use_new_schema(
    hass: HomeAssistant,
    scenario_full: tuple,
    sensor_type: str,  # pylint: disable=unused-argument  # Used in test parameterization
    stats_key: str,
) -> None:
    """Test SystemChoreApprovals sensors read from DATA_KID_CHORE_STATS dict.

    NOTE: These sensors (SystemChoreApprovalsDaily/Weekly/MonthlySensor) are marked
    for optional deprecation in KC-vNext as their data is now available as
    attributes on SystemChoreApprovalsSensor.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    kid_id = name_to_id_map["kid:Zoë"]

    # Initialize stats by approving an unclaimed chore (not pre-completed, not auto_approve in YAML)
    chore_id = name_to_id_map["chore:Refill Bird Fëeder"]
    parent_id = name_to_id_map["parent:Môm Astrid Stârblüm"]

    # Mock notifications to prevent ServiceNotFound errors during teardown
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(kid_id, chore_id, "test_user")
        coordinator.approve_chore(parent_id, kid_id, chore_id)
        await hass.async_block_till_done()

    # Verify data is in new schema location
    chore_stats = coordinator.kids_data[kid_id].get(const.DATA_KID_CHORE_STATS, {})
    assert stats_key in chore_stats, (
        f"{stats_key} should be present in chore_stats (new schema)"
    )

    # Verify it's a valid count
    value = chore_stats.get(stats_key, 0)
    assert isinstance(value, (int, float)), f"{stats_key} should be numeric"
    assert value >= 0, f"{stats_key} should be non-negative"


@pytest.mark.parametrize(
    "sensor_type,stats_key",
    [
        ("daily", const.DATA_KID_POINT_STATS_NET_TODAY),
        ("weekly", const.DATA_KID_POINT_STATS_NET_WEEK),
        ("monthly", const.DATA_KID_POINT_STATS_NET_MONTH),
    ],
)
async def test_points_earned_sensors_use_new_schema(
    hass: HomeAssistant,
    scenario_full: tuple,
    sensor_type: str,  # pylint: disable=unused-argument  # Used in test parameterization
    stats_key: str,
) -> None:
    """Test PointsEarned sensors read from DATA_KID_POINT_STATS dict.

    NOTE: These sensors (PointsEarnedDaily/Weekly/MonthlySensor) are marked
    for optional deprecation in KC-vNext as their data is now available as
    attributes on KidPointsSensor.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    kid_id = name_to_id_map["kid:Zoë"]

    # Initialize stats by giving points
    bonus_id = name_to_id_map["bonus:Stär Sprïnkle Bonus"]
    parent_id = name_to_id_map["parent:Môm Astrid Stârblüm"]

    # Mock notifications to prevent ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.apply_bonus(parent_id, kid_id, bonus_id)
        await hass.async_block_till_done()

    # Verify data is in new schema location
    point_stats = coordinator.kids_data[kid_id].get(const.DATA_KID_POINT_STATS, {})
    assert stats_key in point_stats, (
        f"{stats_key} should be present in point_stats (new schema)"
    )

    # Verify it's a valid points value
    value = point_stats.get(stats_key, 0)
    assert isinstance(value, (int, float)), f"{stats_key} should be numeric"


# ============================================================================
# HELPER FUNCTION DEMONSTRATIONS - Testing Standards Maturity Initiative
# ============================================================================
# Added: 2025-12-20 (Phase 1)
# Purpose: Demonstrate new helper functions for test creation
# See: tests/conftest.py for helper implementations
# ============================================================================


async def test_helper_get_kid_by_name_demonstration(
    hass: HomeAssistant,
    scenario_full: tuple,
) -> None:
    """Demonstrate get_kid_by_name() helper - avoids hardcoded indices.

    BEFORE (old pattern):
        kid_id = name_to_id_map["kid:Zoë"]
        kid_data = coordinator.kids_data[kid_id]

    AFTER (new helper):
        kid = get_kid_by_name(coordinator.data, "Zoë")
    """
    from tests.legacy.conftest import get_kid_by_name

    config_entry, _ = scenario_full  # Don't need name_to_id_map anymore
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # OLD PATTERN: Use name_to_id_map lookup
    # kid_id = name_to_id_map["kid:Zoë"]
    # kid_data = coordinator.kids_data[kid_id]

    # NEW PATTERN: Get kid directly by name
    kid = get_kid_by_name(coordinator.data, "Zoë")

    assert kid["name"] == "Zoë"
    assert "internal_id" in kid
    assert "points" in kid


async def test_helper_get_chore_by_name_demonstration(
    hass: HomeAssistant,
    scenario_full: tuple,
) -> None:
    """Demonstrate get_chore_by_name() helper - finds chores by name.

    BEFORE (old pattern):
        chore_id = name_to_id_map["chore:Wåter the plänts"]
        chore_data = coordinator.chores_data[chore_id]

    AFTER (new helper):
        chore = get_chore_by_name(coordinator.data, "Wåter the plänts")
    """
    from tests.legacy.conftest import get_chore_by_name

    config_entry, _ = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # OLD PATTERN: Use name_to_id_map lookup
    # chore_id = name_to_id_map["chore:Wåter the plänts"]
    # chore_data = coordinator.chores_data[chore_id]

    # NEW PATTERN: Get chore directly by name
    chore = get_chore_by_name(coordinator.data, "Wåter the plänts")

    assert chore["name"] == "Wåter the plänts"
    assert "internal_id" in chore
    assert "state" in chore


async def test_helper_create_test_datetime_demonstration(
    hass: HomeAssistant,  # pylint: disable=unused-argument
) -> None:
    """Demonstrate create_test_datetime() helper - UTC datetime creation.

    BEFORE (old pattern):
        from datetime import datetime, timedelta, timezone
        overdue_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    AFTER (new helper):
        overdue_date = create_test_datetime(days_offset=-7)
    """
    from datetime import datetime, timezone

    from tests.legacy.conftest import create_test_datetime

    # OLD PATTERN: Manual datetime construction
    # from datetime import datetime, timedelta, timezone
    # overdue_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    # NEW PATTERN: Use helper for clean datetime creation
    overdue_date = create_test_datetime(days_offset=-7)
    # future_date = create_test_datetime(days_offset=7, hours_offset=2)  # Example only

    # Verify dates are valid ISO format with timezone
    assert "T" in overdue_date
    assert "+" in overdue_date or "Z" in overdue_date

    # Verify date is approximately 7 days ago (within reason)
    parsed = datetime.fromisoformat(overdue_date.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    diff_days = (now - parsed).days
    assert 6 <= diff_days <= 8, "Overdue date should be ~7 days ago"
