"""Test migration of real production data samples from v3.x/v4.0beta1 to v4.2.

This test suite validates that migration correctly transforms legacy storage formats
to the v42 schema without data loss. Tests use actual production data snapshots to
ensure real-world compatibility.

Test Organization:
    - Fixtures: Load migration samples from files
    - Structural Validation: Required fields present post-migration
    - Data Preservation: Entity counts, points, assignments intact
    - Datetime Migration: UTC-aware ISO format conversion
    - Regression: Snapshot tests for structural changes

Migration Philosophy:
    Migration creates required STRUCTURES, not complete nested data.
    Nested statistics (period breakdowns, detailed stats) populate during runtime
    operations (chore completions, point adjustments). Tests validate structural
    integrity, not data completeness.
"""

# pylint: disable=protected-access  # Accessing _data for migration validation
# pylint: disable=redefined-outer-name  # Pytest fixture pattern

import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    COMPLETION_CRITERIA_INDEPENDENT,
    COMPLETION_CRITERIA_SHARED,
    CONF_POINTS_ICON,
    CONF_POINTS_LABEL,
    COORDINATOR,
    DATA_BADGE_ASSIGNED_TO,
    DATA_BADGE_AWARDS,
    DATA_BADGE_AWARDS_AWARD_ITEMS,
    DATA_BADGE_AWARDS_AWARD_POINTS,
    DATA_BADGE_AWARDS_POINT_MULTIPLIER,
    DATA_BADGE_RESET_SCHEDULE,
    DATA_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS,
    DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY,
    DATA_BADGE_TARGET,
    DATA_BADGE_TARGET_THRESHOLD_VALUE,
    DATA_BADGE_TARGET_TYPE,
    DATA_BADGE_TYPE,
    DATA_BADGES,
    DATA_CHORE_APPLICABLE_DAYS,
    DATA_CHORE_ASSIGNED_KIDS,
    DATA_CHORE_COMPLETION_CRITERIA,
    DATA_CHORE_DUE_DATE,
    DATA_CHORE_LAST_CLAIMED,
    DATA_CHORE_LAST_COMPLETED,
    DATA_CHORE_NAME,
    DATA_CHORE_NOTIFY_ON_APPROVAL,
    DATA_CHORE_NOTIFY_ON_CLAIM,
    DATA_CHORE_NOTIFY_ON_DISAPPROVAL,
    DATA_CHORES,
    DATA_KID_BADGES_EARNED,
    DATA_KID_CHORE_DATA,
    DATA_KID_CHORE_STATS,
    DATA_KID_CUMULATIVE_BADGE_PROGRESS,
    DATA_KID_OVERDUE_NOTIFICATIONS,
    DATA_KID_POINT_DATA,
    DATA_KID_POINTS,
    DATA_KIDS,
    DATA_META,
    DATA_META_SCHEMA_VERSION,
    DATA_REWARDS,
    DATA_SCHEMA_VERSION,
    DEFAULT_POINTS_ICON,
    DEFAULT_POINTS_LABEL,
    DOMAIN,
    SCHEMA_VERSION_STORAGE_ONLY,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def migration_sample_v30() -> dict[str, Any]:
    """Load kidschores_data_30 sample file (KC 3.0 production data)."""
    sample_path = Path(__file__).parent / "migration_samples" / "kidschores_data_30"
    with open(sample_path, encoding="utf-8") as f:
        raw_data = json.load(f)
    return raw_data["data"]  # Return just the data section


@pytest.fixture
def migration_sample_v31() -> dict[str, Any]:
    """Load kidschores_data_31 sample file (KC 3.1 production data)."""
    sample_path = Path(__file__).parent / "migration_samples" / "kidschores_data_31"
    with open(sample_path, encoding="utf-8") as f:
        raw_data = json.load(f)
    return raw_data["data"]


@pytest.fixture
def migration_sample_v40beta1() -> dict[str, Any]:
    """Load kidschores_data_40beta1 sample file (KC 4.0 beta data)."""
    sample_path = (
        Path(__file__).parent / "migration_samples" / "kidschores_data_40beta1"
    )
    with open(sample_path, encoding="utf-8") as f:
        raw_data = json.load(f)
    return raw_data["data"]


@pytest.fixture
def mock_config_entry_for_migration() -> MockConfigEntry:
    """Create a config entry for migration testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="KidsChores Migration Test",
        data={},  # Empty data - schema_version comes from storage, not config_entry
        options={
            CONF_POINTS_LABEL: DEFAULT_POINTS_LABEL,
            CONF_POINTS_ICON: DEFAULT_POINTS_ICON,
        },
        entry_id="test_migration_entry",
        version=1,
        minor_version=1,
    )


async def setup_integration_with_migration_sample(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    sample_data: dict[str, Any],
) -> MockConfigEntry:
    """Set up integration with migration sample data.

    Args:
        hass: Home Assistant instance
        config_entry: Mock config entry
        sample_data: Storage data to migrate

    Returns:
        Config entry after setup
    """
    config_entry.add_to_hass(hass)

    # Note: With v43 meta section design, schema_version is nested in data.meta.schema_version
    # Test framework will no longer auto-inject at that location, so no stripping needed

    # Mock storage to return sample data (will trigger migration)
    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        return_value=sample_data,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    return config_entry


# ============================================================================
# Test Group: Entity Count Preservation
# ============================================================================


@pytest.mark.parametrize(
    "sample_fixture_name",
    ["migration_sample_v30", "migration_sample_v31", "migration_sample_v40beta1"],
)
async def test_migration_entity_counts_preserved(
    hass: HomeAssistant,
    mock_config_entry_for_migration: MockConfigEntry,
    sample_fixture_name: str,
    request,  # pytest request fixture to access other fixtures by name
) -> None:
    """Test that entity counts are preserved during migration.

    Validates:
        - Number of kids remains same
        - Number of chores remains same
        - Number of badges remains same
        - Number of rewards remains same
    """
    # Get the sample data fixture by name
    sample_data = request.getfixturevalue(sample_fixture_name)

    # Count entities before migration
    pre_kid_count = len(sample_data.get(DATA_KIDS, {}))
    pre_chore_count = len(sample_data.get(DATA_CHORES, {}))
    pre_badge_count = len(sample_data.get(DATA_BADGES, {}))
    pre_reward_count = len(sample_data.get(DATA_REWARDS, {}))

    # Setup integration (triggers migration)
    config_entry = await setup_integration_with_migration_sample(
        hass, mock_config_entry_for_migration, sample_data
    )

    # Access coordinator
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Validate counts preserved
    assert len(coordinator.kids_data) == pre_kid_count
    assert len(coordinator.chores_data) == pre_chore_count
    assert len(coordinator.badges_data) == pre_badge_count
    assert len(coordinator.rewards_data) == pre_reward_count


# ============================================================================
# Test Group: Schema Version Migration
# ============================================================================


@pytest.mark.parametrize(
    "sample_fixture_name",
    ["migration_sample_v30", "migration_sample_v31", "migration_sample_v40beta1"],
)
async def test_migration_schema_version_updated(
    hass: HomeAssistant,
    mock_config_entry_for_migration: MockConfigEntry,
    sample_fixture_name: str,
    request,
) -> None:
    """Test that schema_version is set to v42 after migration."""
    sample_data = request.getfixturevalue(sample_fixture_name)

    config_entry = await setup_integration_with_migration_sample(
        hass, mock_config_entry_for_migration, sample_data
    )

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Verify schema version updated to v43 in meta section
    assert DATA_META in coordinator._data
    assert (
        coordinator._data[DATA_META][DATA_META_SCHEMA_VERSION]
        == SCHEMA_VERSION_STORAGE_ONLY
    )
    # Verify old top-level schema_version removed
    assert DATA_SCHEMA_VERSION not in coordinator._data


# ============================================================================
# Test Group: Kid Structural Validation
# ============================================================================


@pytest.mark.parametrize(
    "sample_fixture_name",
    ["migration_sample_v30", "migration_sample_v31", "migration_sample_v40beta1"],
)
async def test_migration_kid_required_fields(
    hass: HomeAssistant,
    mock_config_entry_for_migration: MockConfigEntry,
    sample_fixture_name: str,
    request,
) -> None:
    """Test that all required kid fields exist post-migration.

    Validates presence of:
        - overdue_notifications (dict)
        - badges_earned (dict, not list)
        - cumulative_badge_progress (dict)
        - point_data (dict)
        - chore_data (dict)
        - chore_stats (dict)
    """
    sample_data = request.getfixturevalue(sample_fixture_name)

    config_entry = await setup_integration_with_migration_sample(
        hass, mock_config_entry_for_migration, sample_data
    )

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Check at least one kid exists
    assert len(coordinator.kids_data) > 0, "No kids found in migrated data"

    # Validate structure for each kid
    for kid_id, kid_data in coordinator.kids_data.items():
        # Required top-level fields
        assert DATA_KID_OVERDUE_NOTIFICATIONS in kid_data, (
            f"Kid {kid_id} missing overdue_notifications"
        )
        assert isinstance(kid_data[DATA_KID_OVERDUE_NOTIFICATIONS], dict), (
            f"Kid {kid_id} overdue_notifications not a dict"
        )

        assert DATA_KID_BADGES_EARNED in kid_data, f"Kid {kid_id} missing badges_earned"
        assert isinstance(kid_data[DATA_KID_BADGES_EARNED], dict), (
            f"Kid {kid_id} badges_earned not a dict (should not be list)"
        )

        # Point data structure (may be empty dict but must exist)
        assert DATA_KID_POINT_DATA in kid_data, f"Kid {kid_id} missing point_data"
        assert isinstance(kid_data[DATA_KID_POINT_DATA], dict), (
            f"Kid {kid_id} point_data not a dict"
        )

        # Chore data structure (may be empty dict but must exist)
        assert DATA_KID_CHORE_DATA in kid_data, f"Kid {kid_id} missing chore_data"
        assert isinstance(kid_data[DATA_KID_CHORE_DATA], dict), (
            f"Kid {kid_id} chore_data not a dict"
        )

        # Chore stats structure
        assert DATA_KID_CHORE_STATS in kid_data, f"Kid {kid_id} missing chore_stats"
        assert isinstance(kid_data[DATA_KID_CHORE_STATS], dict), (
            f"Kid {kid_id} chore_stats not a dict"
        )


@pytest.mark.parametrize(
    "sample_fixture_name",
    ["migration_sample_v30", "migration_sample_v31", "migration_sample_v40beta1"],
)
async def test_migration_kid_cumulative_badge_progress(
    hass: HomeAssistant,
    mock_config_entry_for_migration: MockConfigEntry,
    sample_fixture_name: str,
    request,
) -> None:
    """Test that kids with cumulative badges have progress tracking.

    For kids that had badges in legacy format, cumulative_badge_progress
    should be present (even if empty dict for kids without cumulative badges).
    """
    sample_data = request.getfixturevalue(sample_fixture_name)

    config_entry = await setup_integration_with_migration_sample(
        hass, mock_config_entry_for_migration, sample_data
    )

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    for kid_id, kid_data in coordinator.kids_data.items():
        # cumulative_badge_progress should exist (dict, may be empty)
        assert DATA_KID_CUMULATIVE_BADGE_PROGRESS in kid_data, (
            f"Kid {kid_id} missing cumulative_badge_progress"
        )
        assert isinstance(kid_data[DATA_KID_CUMULATIVE_BADGE_PROGRESS], dict), (
            f"Kid {kid_id} cumulative_badge_progress not a dict"
        )


# ============================================================================
# Test Group: Chore Structural Validation
# ============================================================================


@pytest.mark.parametrize(
    "sample_fixture_name",
    ["migration_sample_v30", "migration_sample_v31", "migration_sample_v40beta1"],
)
async def test_migration_chore_required_fields(
    hass: HomeAssistant,
    mock_config_entry_for_migration: MockConfigEntry,
    sample_fixture_name: str,
    request,
) -> None:
    """Test that all required chore fields exist post-migration.

    Validates presence of:
        - applicable_days (list)
        - notify_on_claim (boolean)
        - notify_on_approval (boolean)
        - notify_on_disapproval (boolean)
        - completion_criteria (string, converted from shared_chore boolean)
    """
    sample_data = request.getfixturevalue(sample_fixture_name)

    config_entry = await setup_integration_with_migration_sample(
        hass, mock_config_entry_for_migration, sample_data
    )

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Check at least one chore exists
    assert len(coordinator.chores_data) > 0, "No chores found in migrated data"

    # Validate structure for each chore
    for chore_id, chore_data in coordinator.chores_data.items():
        chore_name = chore_data.get(DATA_CHORE_NAME, f"chore_{chore_id}")

        assert DATA_CHORE_APPLICABLE_DAYS in chore_data, (
            f"Chore {chore_name} missing applicable_days"
        )
        assert isinstance(chore_data[DATA_CHORE_APPLICABLE_DAYS], list), (
            f"Chore {chore_name} applicable_days not a list"
        )

        assert DATA_CHORE_NOTIFY_ON_CLAIM in chore_data, (
            f"Chore {chore_name} missing notify_on_claim"
        )
        assert isinstance(chore_data[DATA_CHORE_NOTIFY_ON_CLAIM], bool), (
            f"Chore {chore_name} notify_on_claim not a boolean"
        )

        assert DATA_CHORE_NOTIFY_ON_APPROVAL in chore_data, (
            f"Chore {chore_name} missing notify_on_approval"
        )
        assert isinstance(chore_data[DATA_CHORE_NOTIFY_ON_APPROVAL], bool), (
            f"Chore {chore_name} notify_on_approval not a boolean"
        )

        assert DATA_CHORE_NOTIFY_ON_DISAPPROVAL in chore_data, (
            f"Chore {chore_name} missing notify_on_disapproval"
        )
        assert isinstance(chore_data[DATA_CHORE_NOTIFY_ON_DISAPPROVAL], bool), (
            f"Chore {chore_name} notify_on_disapproval not a boolean"
        )

        # NEW: Test completion_criteria field conversion
        assert DATA_CHORE_COMPLETION_CRITERIA in chore_data, (
            f"Chore {chore_name} missing completion_criteria (should be converted from shared_chore)"
        )
        completion_criteria = chore_data[DATA_CHORE_COMPLETION_CRITERIA]
        assert completion_criteria in [
            COMPLETION_CRITERIA_SHARED,
            COMPLETION_CRITERIA_INDEPENDENT,
        ], (
            f"Chore {chore_name} completion_criteria '{completion_criteria}' should be 'shared_all' or 'independent'"
        )

        # Ensure legacy shared_chore field is removed
        assert "shared_chore" not in chore_data, (
            f"Chore {chore_name} still has legacy 'shared_chore' field after migration"
        )


# ============================================================================
# Test Group: Badge Structural Validation
# ============================================================================


@pytest.mark.parametrize(
    "sample_fixture_name",
    ["migration_sample_v30", "migration_sample_v31", "migration_sample_v40beta1"],
)
async def test_migration_badge_required_fields(
    hass: HomeAssistant,
    mock_config_entry_for_migration: MockConfigEntry,
    sample_fixture_name: str,
    request,
) -> None:
    """Test that all required badge fields exist post-migration.

    Validates presence of:
        - type (e.g., cumulative, daily, periodic)
        - target (dict with type and threshold_value)
        - awards (dict with award_items, award_points, point_multiplier)
        - reset_schedule (dict with recurring_frequency, grace_period_days)
        - assigned_to (list)
    """
    sample_data = request.getfixturevalue(sample_fixture_name)

    config_entry = await setup_integration_with_migration_sample(
        hass, mock_config_entry_for_migration, sample_data
    )

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Check at least one badge exists
    assert len(coordinator.badges_data) > 0, "No badges found in migrated data"

    # Validate structure for each badge
    for badge_id, badge_data in coordinator.badges_data.items():
        # Type field
        assert DATA_BADGE_TYPE in badge_data, f"Badge {badge_id} missing type"
        assert isinstance(badge_data[DATA_BADGE_TYPE], str), (
            f"Badge {badge_id} type not a string"
        )

        # Target structure
        assert DATA_BADGE_TARGET in badge_data, f"Badge {badge_id} missing target"
        assert isinstance(badge_data[DATA_BADGE_TARGET], dict), (
            f"Badge {badge_id} target not a dict"
        )
        assert DATA_BADGE_TARGET_TYPE in badge_data[DATA_BADGE_TARGET], (
            f"Badge {badge_id} target missing type"
        )
        assert DATA_BADGE_TARGET_THRESHOLD_VALUE in badge_data[DATA_BADGE_TARGET], (
            f"Badge {badge_id} target missing threshold_value"
        )

        # Awards structure
        assert DATA_BADGE_AWARDS in badge_data, f"Badge {badge_id} missing awards"
        assert isinstance(badge_data[DATA_BADGE_AWARDS], dict), (
            f"Badge {badge_id} awards not a dict"
        )
        assert DATA_BADGE_AWARDS_AWARD_ITEMS in badge_data[DATA_BADGE_AWARDS], (
            f"Badge {badge_id} awards missing award_items"
        )
        assert DATA_BADGE_AWARDS_AWARD_POINTS in badge_data[DATA_BADGE_AWARDS], (
            f"Badge {badge_id} awards missing award_points"
        )
        assert DATA_BADGE_AWARDS_POINT_MULTIPLIER in badge_data[DATA_BADGE_AWARDS], (
            f"Badge {badge_id} awards missing point_multiplier"
        )

        # Reset schedule structure
        assert DATA_BADGE_RESET_SCHEDULE in badge_data, (
            f"Badge {badge_id} missing reset_schedule"
        )
        assert isinstance(badge_data[DATA_BADGE_RESET_SCHEDULE], dict), (
            f"Badge {badge_id} reset_schedule not a dict"
        )
        assert (
            DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY
            in badge_data[DATA_BADGE_RESET_SCHEDULE]
        ), f"Badge {badge_id} reset_schedule missing recurring_frequency"
        assert (
            DATA_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS
            in badge_data[DATA_BADGE_RESET_SCHEDULE]
        ), f"Badge {badge_id} reset_schedule missing grace_period_days"

        # Assigned to list
        assert DATA_BADGE_ASSIGNED_TO in badge_data, (
            f"Badge {badge_id} missing assigned_to"
        )
        assert isinstance(badge_data[DATA_BADGE_ASSIGNED_TO], list), (
            f"Badge {badge_id} assigned_to not a list"
        )


# ============================================================================
# Test Group: Data Preservation
# ============================================================================


@pytest.mark.parametrize(
    "sample_fixture_name",
    ["migration_sample_v30", "migration_sample_v31", "migration_sample_v40beta1"],
)
async def test_migration_kid_points_preserved(
    hass: HomeAssistant,
    mock_config_entry_for_migration: MockConfigEntry,
    sample_fixture_name: str,
    request,
) -> None:
    """Test that kid point values are preserved during migration."""
    sample_data = request.getfixturevalue(sample_fixture_name)

    # Capture pre-migration points
    pre_migration_points = {
        kid_id: kid_data.get(DATA_KID_POINTS, 0.0)
        for kid_id, kid_data in sample_data.get(DATA_KIDS, {}).items()
    }

    config_entry = await setup_integration_with_migration_sample(
        hass, mock_config_entry_for_migration, sample_data
    )

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Validate points preserved for each kid
    for kid_id, pre_points in pre_migration_points.items():
        assert kid_id in coordinator.kids_data, (
            f"Kid {kid_id} not found after migration"
        )
        post_points = coordinator.kids_data[kid_id].get(DATA_KID_POINTS, 0.0)
        assert abs(post_points - pre_points) < 0.01, (
            f"Kid {kid_id} points changed: {pre_points} -> {post_points}"
        )


@pytest.mark.parametrize(
    "sample_fixture_name",
    ["migration_sample_v30", "migration_sample_v31", "migration_sample_v40beta1"],
)
async def test_migration_chore_assignments_preserved(
    hass: HomeAssistant,
    mock_config_entry_for_migration: MockConfigEntry,
    sample_fixture_name: str,
    request,
) -> None:
    """Test that chore kid assignments are preserved during migration."""
    sample_data = request.getfixturevalue(sample_fixture_name)

    # Capture pre-migration assignments
    pre_migration_assignments = {
        chore_id: set(chore_data.get(DATA_CHORE_ASSIGNED_KIDS, []))
        for chore_id, chore_data in sample_data.get(DATA_CHORES, {}).items()
    }

    config_entry = await setup_integration_with_migration_sample(
        hass, mock_config_entry_for_migration, sample_data
    )

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Validate assignments preserved for each chore
    for chore_id, pre_kids in pre_migration_assignments.items():
        assert chore_id in coordinator.chores_data, (
            f"Chore {chore_id} not found after migration"
        )
        post_kids = set(
            coordinator.chores_data[chore_id].get(DATA_CHORE_ASSIGNED_KIDS, [])
        )
        assert post_kids == pre_kids, (
            f"Chore {chore_id} assignments changed: {pre_kids} -> {post_kids}"
        )


# ============================================================================
# Test Group: Datetime Migration
# ============================================================================


@pytest.mark.parametrize(
    "sample_fixture_name",
    ["migration_sample_v30", "migration_sample_v31", "migration_sample_v40beta1"],
)
async def test_migration_datetime_format(
    hass: HomeAssistant,
    mock_config_entry_for_migration: MockConfigEntry,
    sample_fixture_name: str,
    request,
) -> None:
    """Test that datetime fields are converted to UTC-aware ISO format.

    Pattern: YYYY-MM-DDTHH:MM:SS.ffffff±HH:MM
    Example: 2025-04-22T11:57:16.855704+00:00
    """
    sample_data = request.getfixturevalue(sample_fixture_name)

    config_entry = await setup_integration_with_migration_sample(
        hass, mock_config_entry_for_migration, sample_data
    )

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # UTC-aware ISO format regex (microseconds optional)
    utc_iso_pattern = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?[+-]\d{2}:\d{2}$"
    )

    # Check chore datetime fields
    for chore_id, chore_data in coordinator.chores_data.items():
        for field in [
            DATA_CHORE_DUE_DATE,
            DATA_CHORE_LAST_COMPLETED,
            DATA_CHORE_LAST_CLAIMED,
        ]:
            value = chore_data.get(field)
            if value:  # Only check non-None, non-empty values
                assert utc_iso_pattern.match(value), (
                    f"Chore {chore_id} {field} not UTC-aware ISO: {value}"
                )

    # Check kid overdue notification datetimes
    for kid_id, kid_data in coordinator.kids_data.items():
        overdue_notifs = kid_data.get(DATA_KID_OVERDUE_NOTIFICATIONS, {})
        for chore_id, timestamp in overdue_notifs.items():
            if timestamp:
                assert utc_iso_pattern.match(timestamp), (
                    f"Kid {kid_id} overdue notification for {chore_id} not UTC-aware ISO: {timestamp}"
                )


# ============================================================================
# Test Group: Legacy to New Mapping
# ============================================================================


async def test_migration_v30_badges_list_to_dict(
    hass: HomeAssistant,
    mock_config_entry_for_migration: MockConfigEntry,
    migration_sample_v30: dict[str, Any],
) -> None:
    """Test that v30 legacy 'badges' list migrates to 'badges_earned' dict.

    v3.0 structure:
        "badges": ["Bronze", "Silver"]  # List of badge names

    v4.2 structure:
        "badges_earned": {
            "badge-id-1": {
                "badge_name": "Bronze",
                "last_awarded_date": "2025-04-22",
                "award_count": 1
            }
        }
    """
    config_entry = await setup_integration_with_migration_sample(
        hass, mock_config_entry_for_migration, migration_sample_v30
    )

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Find a kid with legacy badges in v30 data
    for kid_id, kid_data in migration_sample_v30.get(DATA_KIDS, {}).items():
        legacy_badges = kid_data.get("badges", [])
        if legacy_badges:  # If kid had badges in v30
            # Check migrated structure
            migrated_kid = coordinator.kids_data[kid_id]
            assert DATA_KID_BADGES_EARNED in migrated_kid, (
                f"Kid {kid_id} missing badges_earned after migration"
            )
            assert isinstance(migrated_kid[DATA_KID_BADGES_EARNED], dict), (
                f"Kid {kid_id} badges_earned should be dict, not list"
            )
            # Structure exists (may be empty if no matching badges found)
            break


async def test_migration_v30_chore_streaks_to_chore_data(
    hass: HomeAssistant,
    mock_config_entry_for_migration: MockConfigEntry,
    migration_sample_v30: dict[str, Any],
) -> None:
    """Test that v30 'chore_streaks' dict migrates to 'chore_data' structure.

    v3.0 structure:
        "chore_streaks": {
            "chore-id-1": {
                "current_streak": 5,
                "max_streak": 10,
                "last_date": "2025-04-22"
            }
        }

    v4.2 structure:
        "chore_data": {
            "chore-id-1": {
                "name": "Feed cats",
                "periods": {
                    "daily": {},
                    "weekly": {},
                    "monthly": {},
                    "yearly": {},
                    "all_time": {}
                }
            }
        }
    """
    config_entry = await setup_integration_with_migration_sample(
        hass, mock_config_entry_for_migration, migration_sample_v30
    )

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Find a kid with legacy chore_streaks in v30 data
    for kid_id, kid_data in migration_sample_v30.get(DATA_KIDS, {}).items():
        legacy_streaks = kid_data.get("chore_streaks", {})
        if legacy_streaks:  # If kid had streaks in v30
            # Check migrated structure
            migrated_kid = coordinator.kids_data[kid_id]
            assert DATA_KID_CHORE_DATA in migrated_kid, (
                f"Kid {kid_id} missing chore_data after migration"
            )
            assert isinstance(migrated_kid[DATA_KID_CHORE_DATA], dict), (
                f"Kid {kid_id} chore_data should be dict"
            )
            # Structure exists (nested period data not validated - populates at runtime)
            break
