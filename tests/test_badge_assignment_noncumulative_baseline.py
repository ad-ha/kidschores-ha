"""Baseline tests for non-cumulative badge assigned_to logic in coordinator.

Tests target coordinator.py line 6480: assigned_to check for non-cumulative badges.
Covers daily, periodic, and special_occasion badge types.

Only tests assignment logic, does NOT test badge earning (threshold crossing).
Uses direct coordinator method calls with mocked notifications.
"""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    BADGE_TYPE_DAILY,
    BADGE_TYPE_PERIODIC,
    BADGE_TYPE_SPECIAL_OCCASION,
    COORDINATOR,
    DATA_BADGE_ASSIGNED_TO,
    DATA_BADGE_TYPE,
    DATA_BADGES,
    DATA_KID_BADGE_PROGRESS,
    DOMAIN,
)

# pylint: disable=protected-access,redefined-outer-name


async def test_daily_badge_empty_assigned_to_evaluates_for_all_kids(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test daily badge assigned to all kids is evaluated for all kids.

    Feature Change v4.2: Empty assigned_to now means NO kids.
    This test validates explicit assignment to multiple kids.
    Covers coordinator.py line 6480: kid_id in assigned_to check for daily badges.
    """
    # Arrange
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    # Find daily badge
    daily_badge_id = None
    for badge_id, badge_info in coordinator._data[DATA_BADGES].items():
        if badge_info[DATA_BADGE_TYPE] == BADGE_TYPE_DAILY:
            daily_badge_id = badge_id
            break

    if daily_badge_id is None:
        return  # Skip if no daily badge

    # Feature Change v4.2: Explicitly assign badge to both kids
    coordinator._data[DATA_BADGES][daily_badge_id][DATA_BADGE_ASSIGNED_TO] = [
        zoe_id,
        max_id,
    ]

    # Clear existing progress
    if DATA_KID_BADGE_PROGRESS in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS].pop(daily_badge_id, None)
    if DATA_KID_BADGE_PROGRESS in coordinator.kids_data[max_id]:
        coordinator.kids_data[max_id][DATA_KID_BADGE_PROGRESS].pop(daily_badge_id, None)

    # Act: Mock notifications and evaluate badges
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator._check_badges_for_kid(zoe_id)
        coordinator._check_badges_for_kid(max_id)

    # Assert: Both kids have badge progress entry
    zoe_progress = coordinator.kids_data[zoe_id].get(DATA_KID_BADGE_PROGRESS, {})
    max_progress = coordinator.kids_data[max_id].get(DATA_KID_BADGE_PROGRESS, {})

    assert daily_badge_id in zoe_progress, (
        "Zoë should have daily badge progress (explicitly assigned)"
    )
    assert daily_badge_id in max_progress, (
        "Max should have daily badge progress (explicitly assigned)"
    )


async def test_daily_badge_specific_kid_only_evaluates_for_that_kid(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test daily badge assigned to specific kid only evaluates for that kid.

    Covers coordinator.py line 6480: kid_id in assigned_to check for daily badges.
    """
    # Arrange
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    # Find daily badge
    daily_badge_id = None
    for badge_id, badge_info in coordinator._data[DATA_BADGES].items():
        if badge_info[DATA_BADGE_TYPE] == BADGE_TYPE_DAILY:
            daily_badge_id = badge_id
            break

    if daily_badge_id is None:
        return

    # Assign badge ONLY to Zoë
    coordinator._data[DATA_BADGES][daily_badge_id][DATA_BADGE_ASSIGNED_TO] = [zoe_id]

    # Clear existing progress
    if DATA_KID_BADGE_PROGRESS in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS].pop(daily_badge_id, None)
    if DATA_KID_BADGE_PROGRESS in coordinator.kids_data[max_id]:
        coordinator.kids_data[max_id][DATA_KID_BADGE_PROGRESS].pop(daily_badge_id, None)

    # Act: Mock notifications and evaluate badges
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator._check_badges_for_kid(zoe_id)
        coordinator._check_badges_for_kid(max_id)

    # Assert: Only Zoë has progress
    zoe_progress = coordinator.kids_data[zoe_id].get(DATA_KID_BADGE_PROGRESS, {})
    max_progress = coordinator.kids_data[max_id].get(DATA_KID_BADGE_PROGRESS, {})

    assert daily_badge_id in zoe_progress, (
        "Zoë should have daily badge progress (assigned to her)"
    )
    assert daily_badge_id not in max_progress, (
        "Max should NOT have daily badge progress (not assigned)"
    )


async def test_periodic_badge_empty_assigned_to_evaluates_for_all_kids(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test periodic badge assigned to all kids is evaluated for all kids.

    Feature Change v4.2: Empty assigned_to now means NO kids.
    This test validates explicit assignment to multiple kids.
    Covers coordinator.py line 6480: kid_id in assigned_to check for periodic badges.
    """
    # Arrange
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    # Find periodic badge
    periodic_badge_id = None
    for badge_id, badge_info in coordinator._data[DATA_BADGES].items():
        if badge_info[DATA_BADGE_TYPE] == BADGE_TYPE_PERIODIC:
            periodic_badge_id = badge_id
            break

    if periodic_badge_id is None:
        return

    # Feature Change v4.2: Explicitly assign badge to both kids
    coordinator._data[DATA_BADGES][periodic_badge_id][DATA_BADGE_ASSIGNED_TO] = [
        zoe_id,
        max_id,
    ]

    # Clear existing progress
    if DATA_KID_BADGE_PROGRESS in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS].pop(
            periodic_badge_id, None
        )
    if DATA_KID_BADGE_PROGRESS in coordinator.kids_data[max_id]:
        coordinator.kids_data[max_id][DATA_KID_BADGE_PROGRESS].pop(
            periodic_badge_id, None
        )

    # Act: Mock notifications and evaluate badges
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator._check_badges_for_kid(zoe_id)
        coordinator._check_badges_for_kid(max_id)

    # Assert: Both kids have badge progress entry
    zoe_progress = coordinator.kids_data[zoe_id].get(DATA_KID_BADGE_PROGRESS, {})
    max_progress = coordinator.kids_data[max_id].get(DATA_KID_BADGE_PROGRESS, {})

    assert periodic_badge_id in zoe_progress, (
        "Zoë should have periodic badge progress (explicitly assigned)"
    )
    assert periodic_badge_id in max_progress, (
        "Max should have periodic badge progress (explicitly assigned)"
    )


async def test_periodic_badge_specific_kid_only_evaluates_for_that_kid(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test periodic badge assigned to specific kid only evaluates for that kid.

    Covers coordinator.py line 6480: kid_id in assigned_to check for periodic badges.
    """
    # Arrange
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    # Find periodic badge
    periodic_badge_id = None
    for badge_id, badge_info in coordinator._data[DATA_BADGES].items():
        if badge_info[DATA_BADGE_TYPE] == BADGE_TYPE_PERIODIC:
            periodic_badge_id = badge_id
            break

    if periodic_badge_id is None:
        return

    # Assign badge ONLY to Zoë
    coordinator._data[DATA_BADGES][periodic_badge_id][DATA_BADGE_ASSIGNED_TO] = [zoe_id]

    # Clear existing progress
    if DATA_KID_BADGE_PROGRESS in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS].pop(
            periodic_badge_id, None
        )
    if DATA_KID_BADGE_PROGRESS in coordinator.kids_data[max_id]:
        coordinator.kids_data[max_id][DATA_KID_BADGE_PROGRESS].pop(
            periodic_badge_id, None
        )

    # Act: Mock notifications and evaluate badges
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator._check_badges_for_kid(zoe_id)
        coordinator._check_badges_for_kid(max_id)

    # Assert: Only Zoë has progress
    zoe_progress = coordinator.kids_data[zoe_id].get(DATA_KID_BADGE_PROGRESS, {})
    max_progress = coordinator.kids_data[max_id].get(DATA_KID_BADGE_PROGRESS, {})

    assert periodic_badge_id in zoe_progress, (
        "Zoë should have periodic badge progress (assigned to her)"
    )
    assert periodic_badge_id not in max_progress, (
        "Max should NOT have periodic badge progress (not assigned)"
    )


async def test_special_occasion_badge_empty_assigned_to_evaluates_for_all_kids(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test special_occasion badge assigned to all kids is evaluated for all kids.

    Feature Change v4.2: Empty assigned_to now means NO kids.
    This test validates explicit assignment to multiple kids.
    Covers coordinator.py line 6480: kid_id in assigned_to check for special_occasion badges.
    """
    # Arrange
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    # Find special_occasion badge
    special_badge_id = None
    for badge_id, badge_info in coordinator._data[DATA_BADGES].items():
        if badge_info[DATA_BADGE_TYPE] == BADGE_TYPE_SPECIAL_OCCASION:
            special_badge_id = badge_id
            break

    if special_badge_id is None:
        return

    # Feature Change v4.2: Explicitly assign badge to both kids
    coordinator._data[DATA_BADGES][special_badge_id][DATA_BADGE_ASSIGNED_TO] = [
        zoe_id,
        max_id,
    ]

    # Clear existing progress
    if DATA_KID_BADGE_PROGRESS in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS].pop(
            special_badge_id, None
        )
    if DATA_KID_BADGE_PROGRESS in coordinator.kids_data[max_id]:
        coordinator.kids_data[max_id][DATA_KID_BADGE_PROGRESS].pop(
            special_badge_id, None
        )

    # Act: Mock notifications and evaluate badges
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator._check_badges_for_kid(zoe_id)
        coordinator._check_badges_for_kid(max_id)

    # Assert: Both kids have badge progress entry
    zoe_progress = coordinator.kids_data[zoe_id].get(DATA_KID_BADGE_PROGRESS, {})
    max_progress = coordinator.kids_data[max_id].get(DATA_KID_BADGE_PROGRESS, {})

    assert special_badge_id in zoe_progress, (
        "Zoë should have special_occasion badge progress (explicitly assigned)"
    )
    assert special_badge_id in max_progress, (
        "Max should have special_occasion badge progress (explicitly assigned)"
    )


async def test_special_occasion_badge_specific_kid_only_evaluates_for_that_kid(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test special_occasion badge assigned to specific kid only evaluates for that kid.

    Covers coordinator.py line 6480: kid_id in assigned_to check for special_occasion badges.
    """
    # Arrange
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    # Find special_occasion badge
    special_badge_id = None
    for badge_id, badge_info in coordinator._data[DATA_BADGES].items():
        if badge_info[DATA_BADGE_TYPE] == BADGE_TYPE_SPECIAL_OCCASION:
            special_badge_id = badge_id
            break

    if special_badge_id is None:
        return

    # Assign badge ONLY to Zoë
    coordinator._data[DATA_BADGES][special_badge_id][DATA_BADGE_ASSIGNED_TO] = [zoe_id]

    # Clear existing progress
    if DATA_KID_BADGE_PROGRESS in coordinator.kids_data[zoe_id]:
        coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS].pop(
            special_badge_id, None
        )
    if DATA_KID_BADGE_PROGRESS in coordinator.kids_data[max_id]:
        coordinator.kids_data[max_id][DATA_KID_BADGE_PROGRESS].pop(
            special_badge_id, None
        )

    # Act: Mock notifications and evaluate badges
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator._check_badges_for_kid(zoe_id)
        coordinator._check_badges_for_kid(max_id)

    # Assert: Only Zoë has progress
    zoe_progress = coordinator.kids_data[zoe_id].get(DATA_KID_BADGE_PROGRESS, {})
    max_progress = coordinator.kids_data[max_id].get(DATA_KID_BADGE_PROGRESS, {})

    assert special_badge_id in zoe_progress, (
        "Zoë should have special_occasion badge progress (assigned to her)"
    )
    assert special_badge_id not in max_progress, (
        "Max should NOT have special_occasion badge progress (not assigned)"
    )
