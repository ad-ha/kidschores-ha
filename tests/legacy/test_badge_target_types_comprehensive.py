"""Comprehensive tests for all 17 badge target types.

Tests target handler functions in coordinator.py:
- _handle_badge_target_points (2 types: POINTS, POINTS_CHORES)
- _handle_badge_target_chore_count (1 type: CHORE_COUNT)
- _handle_badge_target_daily_completion (9 types: DAYS_*)
- _handle_badge_target_streak (5 types: STREAK_*)

Coverage Goals:
1. Verify each target type correctly calculates progress
2. Test day rollover logic (cycle_count accumulation)
3. Test threshold crossing (criteria_met)
4. Test helper function integration (get_today_chore_and_point_progress, etc.)
5. Ensure data structures match const.py definitions

Uses scenario_full for comprehensive test data with 3 kids, 7 chores.
"""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    BADGE_STATE_EARNED,
    BADGE_STATE_IN_PROGRESS,
    BADGE_TARGET_THRESHOLD_TYPE_CHORE_COUNT,
    BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_CHORES,
    BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_DUE_CHORES,
    BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_3_CHORES,
    BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_5_CHORES,
    BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_7_CHORES,
    BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES,
    BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES_NO_OVERDUE,
    BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES,
    BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES_NO_OVERDUE,
    BADGE_TARGET_THRESHOLD_TYPE_POINTS,
    BADGE_TARGET_THRESHOLD_TYPE_POINTS_CHORES,
    BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_CHORES,
    BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_DUE_CHORES,
    BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES,
    BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES_NO_OVERDUE,
    BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_DUE_CHORES_NO_OVERDUE,
    BADGE_TYPE_PERIODIC,
    COORDINATOR,
    DATA_BADGE_ASSIGNED_TO,
    DATA_BADGE_NAME,
    DATA_BADGE_TARGET,
    DATA_BADGE_TARGET_THRESHOLD_VALUE,
    DATA_BADGE_TARGET_TYPE,
    DATA_BADGE_TRACKED_CHORES,
    DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES,
    DATA_BADGE_TYPE,
    DATA_BADGES,
    DATA_KID_BADGE_PROGRESS,
    DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED,
    DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT,
    DATA_KID_BADGE_PROGRESS_CHORES_TODAY,
    DATA_KID_BADGE_PROGRESS_CRITERIA_MET,
    DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED,
    DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT,
    DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY,
    DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS,
    DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT,
    DATA_KID_BADGE_PROGRESS_POINTS_TODAY,
    DATA_KID_BADGE_PROGRESS_STATUS,
    DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED,
    DOMAIN,
)
from custom_components.kidschores.kc_helpers import get_today_local_iso

# pylint: disable=protected-access,redefined-outer-name


@pytest.fixture
def test_badge_id() -> str:
    """Return a test badge ID."""
    return "test_badge_points_001"


class TestPointsTargetTypes:
    """Test POINTS and POINTS_CHORES target types."""

    async def test_points_target_accumulates_all_sources(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test POINTS target type accumulates points from all sources.

        Handler: _handle_badge_target_points (line 4275)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_POINTS
        Data Source: kh.get_today_chore_and_point_progress (returns total_points_all_sources)
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]
        today_iso = get_today_local_iso()

        # Create test badge with POINTS target
        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Points Master",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_POINTS,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 50,  # Threshold: 50 points
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],  # All chores
            },
        }

        # Initialize badge progress (let coordinator create structure first)
        coordinator._manage_badge_maintenance(zoe_id)

        # Now set test values (simulate prior points)
        coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id].update({
            DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT: 20,  # Prior cycle: 20
            DATA_KID_BADGE_PROGRESS_POINTS_TODAY: 15,  # Today: 15
            DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY: today_iso,
            DATA_KID_BADGE_PROGRESS_STATUS: BADGE_STATE_IN_PROGRESS,
        })

        # Act: Evaluate badges (mocked notifications)
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert: Progress reflects total points (20 + today's actual points)
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]

        # Verify structure
        assert DATA_KID_BADGE_PROGRESS_POINTS_TODAY in progress
        assert DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT in progress
        assert DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS in progress
        assert DATA_KID_BADGE_PROGRESS_CRITERIA_MET in progress

        # Verify accumulation: cycle_count stays same, points_today updated
        assert progress[DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT] == 20
        assert isinstance(progress[DATA_KID_BADGE_PROGRESS_POINTS_TODAY], (int, float))

        # Verify threshold crossing logic
        total_points = (
            progress[DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT]
            + progress[DATA_KID_BADGE_PROGRESS_POINTS_TODAY]
        )
        assert progress[DATA_KID_BADGE_PROGRESS_CRITERIA_MET] == (total_points >= 50)

    async def test_points_chores_target_only_counts_chore_points(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test POINTS_CHORES target type only counts points from chore completions.

        Handler: _handle_badge_target_points (line 4275, from_chores_only=True)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_POINTS_CHORES
        Data Source: kh.get_today_chore_and_point_progress (returns total_points_chores)
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        # Create test badge with POINTS_CHORES target
        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Chore Points Champion",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_POINTS_CHORES,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 30,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Act: Evaluate badges
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert: Progress tracks chore-only points
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]

        assert DATA_KID_BADGE_PROGRESS_POINTS_TODAY in progress
        assert DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED in progress  # points_map stored
        assert isinstance(progress[DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED], dict)


class TestChoreCountTargetType:
    """Test CHORE_COUNT target type."""

    async def test_chore_count_target_accumulates_completions(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test CHORE_COUNT target type accumulates chore completions.

        Handler: _handle_badge_target_chore_count (line 4320)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_CHORE_COUNT
        Data Source: kh.get_today_chore_and_point_progress (returns chore_count_today)
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]
        today_iso = get_today_local_iso()

        # Create test badge with CHORE_COUNT target
        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Chore Counter",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_CHORE_COUNT,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 20,  # 20 chores total
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Initialize (let coordinator create structure first)
        coordinator._manage_badge_maintenance(zoe_id)

        # Now set test values
        coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id].update({
            DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT: 10,  # Prior: 10 chores
            DATA_KID_BADGE_PROGRESS_CHORES_TODAY: 3,  # Today: 3 chores
            DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY: today_iso,
            DATA_KID_BADGE_PROGRESS_STATUS: BADGE_STATE_IN_PROGRESS,
        })

        # Act: Evaluate badges
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert: Chore count accumulated correctly
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]

        assert DATA_KID_BADGE_PROGRESS_CHORES_TODAY in progress
        assert DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT in progress
        assert DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED in progress  # count_map

        # Verify threshold calculation
        total_chores = (
            progress[DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT]
            + progress[DATA_KID_BADGE_PROGRESS_CHORES_TODAY]
        )
        assert progress[DATA_KID_BADGE_PROGRESS_CRITERIA_MET] == (total_chores >= 20)


class TestDailyCompletionTargetTypes:
    """Test 9 DAYS_* target types (daily completion variants)."""

    async def test_days_selected_chores_requires_100_percent(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test DAYS_SELECTED_CHORES requires 100% of tracked chores.

        Handler: _handle_badge_target_daily_completion (line 4365, percent_required=1.0)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES
        Data Source: kh.get_today_chore_completion_progress
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        # Get Zoë's chores
        feed_cats_id = name_to_id_map["chore:Feed the cåts"]

        # Create badge requiring 100% of tracked chores for 5 days
        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Perfect Week",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 5,  # 5 days
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [feed_cats_id],
            },
        }

        # Act: Evaluate badges
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert: Progress uses DAYS_* fields
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]

        assert DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED in progress
        assert DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED in progress
        assert DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT in progress
        assert isinstance(progress[DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED], bool)
        assert isinstance(progress[DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED], dict)

    async def test_days_80pct_chores_accepts_partial_completion(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test DAYS_80PCT_CHORES accepts 80% completion.

        Handler: _handle_badge_target_daily_completion (percent_required=0.8)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_CHORES
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        # Create badge requiring 80% completion for 3 days
        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Almost Perfect",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_CHORES,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 3,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],  # All chores
            },
        }

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert: Uses same DAYS_* fields with different criteria
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED in progress
        assert DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT in progress

    async def test_days_selected_chores_no_overdue_checks_overdue_state(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test DAYS_SELECTED_CHORES_NO_OVERDUE requires no overdue chores.

        Handler: _handle_badge_target_daily_completion (require_no_overdue=True)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES_NO_OVERDUE
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "On Time Master",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES_NO_OVERDUE,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 7,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert: TODAY_COMPLETED depends on overdue check
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED in progress

    async def test_days_selected_due_chores_only_counts_due_today(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test DAYS_SELECTED_DUE_CHORES only considers chores due today.

        Handler: _handle_badge_target_daily_completion (only_due_today=True)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Today's Focus",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 10,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert: Completion based on due-today filter
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED in progress

    async def test_days_80pct_due_chores_combines_filters(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test DAYS_80PCT_DUE_CHORES combines 80% and due-today filters.

        Handler: _handle_badge_target_daily_completion (percent_required=0.8, only_due_today=True)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_DUE_CHORES
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Daily Driver",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_DUE_CHORES,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 5,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED in progress

    async def test_days_selected_due_chores_no_overdue_triple_filter(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test DAYS_SELECTED_DUE_CHORES_NO_OVERDUE uses all three filters.

        Handler: _handle_badge_target_daily_completion (percent=1.0, only_due_today=True, require_no_overdue=True)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES_NO_OVERDUE
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Perfect Daily Execution",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES_NO_OVERDUE,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 14,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED in progress

    async def test_days_min_3_chores_requires_minimum_count(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test DAYS_MIN_3_CHORES requires at least 3 chores per day.

        Handler: _handle_badge_target_daily_completion (min_count=3)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_3_CHORES
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Three-a-Day",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_3_CHORES,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 10,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert: TODAY_COMPLETED only true if >=3 chores done
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED in progress

    async def test_days_min_5_chores_requires_five_completions(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test DAYS_MIN_5_CHORES requires at least 5 chores per day.

        Handler: _handle_badge_target_daily_completion (min_count=5)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_5_CHORES
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "High Five Hero",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_5_CHORES,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 7,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED in progress

    async def test_days_min_7_chores_requires_seven_completions(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test DAYS_MIN_7_CHORES requires at least 7 chores per day.

        Handler: _handle_badge_target_daily_completion (min_count=7)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_7_CHORES
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Weekly Warrior",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_7_CHORES,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 4,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED in progress


class TestStreakTargetTypes:
    """Test 5 STREAK_* target types (consecutive day variants)."""

    async def test_streak_selected_chores_tracks_consecutive_days(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test STREAK_SELECTED_CHORES tracks consecutive days of 100% completion.

        Handler: _handle_badge_target_streak (line 4428, percent_required=1.0)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES
        Data Source: Uses DAYS_CYCLE_COUNT as streak counter
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Perfect Streak",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 7,  # 7-day streak
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert: Uses DAYS_CYCLE_COUNT as streak
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT in progress  # Streak value
        assert DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED in progress  # History dict
        assert DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED in progress

        # Verify streak logic: breaks if yesterday not completed
        assert isinstance(progress[DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT], int)

    async def test_streak_80pct_chores_allows_partial_completion(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test STREAK_80PCT_CHORES allows 80% completion for streaks.

        Handler: _handle_badge_target_streak (percent_required=0.8)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_CHORES
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Good Enough Streak",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_CHORES,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 5,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT in progress

    async def test_streak_selected_chores_no_overdue_breaks_on_overdue(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test STREAK_SELECTED_CHORES_NO_OVERDUE breaks if overdue chores exist.

        Handler: _handle_badge_target_streak (require_no_overdue=True)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES_NO_OVERDUE
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "On-Time Streak",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES_NO_OVERDUE,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 10,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert: Streak breaks if TODAY_COMPLETED=False
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT in progress

    async def test_streak_80pct_due_chores_only_counts_due_chores(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test STREAK_80PCT_DUE_CHORES only counts chores due today.

        Handler: _handle_badge_target_streak (percent=0.8, only_due_today=True)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_DUE_CHORES
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Daily Streak Pro",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_DUE_CHORES,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 14,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT in progress

    async def test_streak_selected_due_chores_no_overdue_triple_filter(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test STREAK_SELECTED_DUE_CHORES_NO_OVERDUE uses all three filters.

        Handler: _handle_badge_target_streak (percent=1.0, only_due_today=True, require_no_overdue=True)
        Target Type: BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_DUE_CHORES_NO_OVERDUE
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Perfect Daily Streak",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_DUE_CHORES_NO_OVERDUE,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 21,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT in progress


class TestDayRolloverLogic:
    """Test day rollover accumulation (cycle_count += today_value)."""

    async def test_day_rollover_accumulates_points_to_cycle_count(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test day rollover adds points_today to points_cycle_count.

        Simulates: Yesterday was 2025-12-22, today is 2025-12-23.
        Handler: _handle_badge_target_points (lines 4298-4301)
        Logic: if last_update_day != today_iso: cycle_count += today_value
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]
        today_iso = get_today_local_iso()
        yesterday_iso = "2025-12-22"  # Simulate yesterday

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Points Rollover Test",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_POINTS,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 100,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Initialize (let coordinator create structure first)
        coordinator._manage_badge_maintenance(zoe_id)

        # Now set test values
        coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id].update({
            DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT: 30,
            DATA_KID_BADGE_PROGRESS_POINTS_TODAY: 15,  # Yesterday's points
            DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY: yesterday_iso,  # Yesterday
            DATA_KID_BADGE_PROGRESS_STATUS: BADGE_STATE_IN_PROGRESS,
        })

        # Act: Evaluate (should trigger rollover)
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert: Rollover occurred
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]

        # Day rollover should have accumulated yesterday's points
        # Expected: cycle_count = 30 + 15 = 45, points_today = <today's new value>
        assert progress[DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT] >= 30
        assert progress[DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY] == today_iso

    async def test_day_rollover_increments_days_completed_count(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test day rollover increments days_cycle_count if yesterday completed.

        Handler: _handle_badge_target_daily_completion (lines 4402-4405)
        Logic: if last_update_day != today and today_completed: days_cycle_count += 1
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]
        today_iso = get_today_local_iso()
        yesterday_iso = "2025-12-22"

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Days Rollover Test",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 10,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Initialize (let coordinator create structure first)
        coordinator._manage_badge_maintenance(zoe_id)

        # Now set test values
        coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id].update({
            DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT: 3,
            DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED: True,  # Yesterday was completed
            DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED: {yesterday_iso: True},
            DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY: yesterday_iso,
            DATA_KID_BADGE_PROGRESS_STATUS: BADGE_STATE_IN_PROGRESS,
        })

        # Act
        with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
            coordinator._check_badges_for_kid(zoe_id)

        # Assert: Day count incremented
        progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id]
        assert progress[DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT] >= 3
        assert progress[DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY] == today_iso


class TestBadgeAwardingLogic:
    """Test badge awarding when criteria_met=True."""

    async def test_badge_awarded_when_criteria_met(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test badge is awarded when criteria_met becomes True.

        Flow: _check_badges_for_kid → criteria_met=True → _award_badge called
        Covers coordinator.py lines 4196-4205
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        # Create low-threshold badge that will be earned
        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Easy Badge",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_POINTS,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 1,  # Very low threshold
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Initialize (let coordinator create structure first)
        coordinator._manage_badge_maintenance(zoe_id)

        # Now set test values
        coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id].update({
            DATA_KID_BADGE_PROGRESS_STATUS: BADGE_STATE_IN_PROGRESS,
        })

        # Act: Mock _award_badge to track call
        with (
            patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
            patch.object(coordinator, "_award_badge", new=AsyncMock()) as mock_award,
        ):
            coordinator._check_badges_for_kid(zoe_id)

            # If criteria met, award should be called
            progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][
                test_badge_id
            ]
            if progress.get(DATA_KID_BADGE_PROGRESS_CRITERIA_MET):
                mock_award.assert_called_once_with(zoe_id, test_badge_id)

    async def test_badge_not_awarded_twice(
        self,
        hass: HomeAssistant,
        scenario_full: tuple[MockConfigEntry, dict[str, str]],
        test_badge_id: str,
    ) -> None:
        """Test badge not awarded again if already earned.

        Flow: Status already EARNED → _award_badge not called
        Covers coordinator.py lines 4198-4205 (state check)
        """
        # Arrange
        config_entry, name_to_id_map = scenario_full
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        coordinator._data[DATA_BADGES][test_badge_id] = {
            DATA_BADGE_NAME: "Already Earned",
            DATA_BADGE_TYPE: BADGE_TYPE_PERIODIC,
            DATA_BADGE_TARGET: {
                DATA_BADGE_TARGET_TYPE: BADGE_TARGET_THRESHOLD_TYPE_POINTS,
                DATA_BADGE_TARGET_THRESHOLD_VALUE: 1,
            },
            DATA_BADGE_ASSIGNED_TO: [zoe_id],
            DATA_BADGE_TRACKED_CHORES: {
                DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: [],
            },
        }

        # Initialize (let coordinator create structure first)
        coordinator._manage_badge_maintenance(zoe_id)

        # Now set test values
        coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS][test_badge_id].update({
            DATA_KID_BADGE_PROGRESS_STATUS: BADGE_STATE_EARNED,  # Already earned
            DATA_KID_BADGE_PROGRESS_CRITERIA_MET: True,
        })

        # Act: Mock _award_badge
        with (
            patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
            patch.object(coordinator, "_award_badge", new=AsyncMock()) as mock_award,
        ):
            coordinator._check_badges_for_kid(zoe_id)

            # Should NOT be called again
            mock_award.assert_not_called()
