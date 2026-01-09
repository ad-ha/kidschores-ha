"""Baseline tests for badge assigned_to logic in coordinator.

Tests target critical coverage gaps in coordinator.py badge assignment:
- Line 4957: Badge assigned_to check (cumulative badges)
- Line 6480: Badge assigned_to check (non-cumulative badges)

Only tests assignment logic, does NOT test badge earning (threshold crossing).
Uses direct coordinator method calls with mocked notifications.
"""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    BADGE_TYPE_CUMULATIVE,
    COORDINATOR,
    DATA_BADGE_ASSIGNED_TO,
    DATA_BADGE_TYPE,
    DATA_BADGES,
    DATA_KID_CUMULATIVE_BADGE_PROGRESS,
    DOMAIN,
)

# pylint: disable=protected-access,redefined-outer-name


async def test_cumulative_badge_empty_assigned_to_evaluates_for_all_kids(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test cumulative badge assigned to all kids is evaluated for all kids.

    Feature Change v4.2: Empty assigned_to now means NO kids.
    This test validates explicit assignment to multiple kids.
    Covers coordinator.py line 4957: kid_id in assigned_to check.
    """
    # Arrange
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    # Find cumulative badge
    cumulative_badge_id = None
    for badge_id, badge_info in coordinator._data[DATA_BADGES].items():
        if badge_info[DATA_BADGE_TYPE] == BADGE_TYPE_CUMULATIVE:
            cumulative_badge_id = badge_id
            break

    if cumulative_badge_id is None:
        # Skip if no cumulative badge in scenario
        return

    # Feature Change v4.2: Explicitly assign badge to both kids
    coordinator._data[DATA_BADGES][cumulative_badge_id][DATA_BADGE_ASSIGNED_TO] = [
        zoe_id,
        max_id,
    ]

    # Clear existing progress
    coordinator.kids_data[zoe_id][DATA_KID_CUMULATIVE_BADGE_PROGRESS] = {}
    coordinator.kids_data[max_id][DATA_KID_CUMULATIVE_BADGE_PROGRESS] = {}

    # Act: Mock notifications and evaluate badges
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator._check_badges_for_kid(zoe_id)
        coordinator._check_badges_for_kid(max_id)

    # Assert: Both kids have progress (explicitly assigned to both)
    zoe_progress = coordinator.kids_data[zoe_id].get(
        DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
    )
    max_progress = coordinator.kids_data[max_id].get(
        DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
    )

    assert bool(zoe_progress), "Zoë should have badge progress (explicitly assigned)"
    assert bool(max_progress), "Max should have badge progress (explicitly assigned)"


async def test_cumulative_badge_specific_kid_only_evaluates_for_that_kid(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test cumulative badge assigned to specific kid only evaluates for that kid.

    Covers coordinator.py line 4957: kid_id in assigned_to check.
    """
    # Arrange
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    # Find cumulative badge
    cumulative_badge_id = None
    for badge_id, badge_info in coordinator._data[DATA_BADGES].items():
        if badge_info[DATA_BADGE_TYPE] == BADGE_TYPE_CUMULATIVE:
            cumulative_badge_id = badge_id
            break

    if cumulative_badge_id is None:
        return

    # Assign badge ONLY to Zoë
    coordinator._data[DATA_BADGES][cumulative_badge_id][DATA_BADGE_ASSIGNED_TO] = [
        zoe_id
    ]

    # Clear existing progress
    coordinator.kids_data[zoe_id][DATA_KID_CUMULATIVE_BADGE_PROGRESS] = {}
    coordinator.kids_data[max_id][DATA_KID_CUMULATIVE_BADGE_PROGRESS] = {}

    # Act: Mock notifications and evaluate badges
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator._check_badges_for_kid(zoe_id)
        coordinator._check_badges_for_kid(max_id)

    # Assert: Only Zoë has progress
    zoe_progress = coordinator.kids_data[zoe_id].get(
        DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
    )
    max_progress = coordinator.kids_data[max_id].get(
        DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
    )

    assert bool(zoe_progress), "Zoë should have progress (assigned to her)"
    assert not max_progress, "Max should NOT have progress (not assigned to him)"
