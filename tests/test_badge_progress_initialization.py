"""
Tests for badge_progress initialization Phase 4.

Validates that badge_progress is proactively initialized when badges are assigned
to kids, ensuring KidBadgeSensor entities are always created.
"""

# pylint: disable=protected-access

from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.kidschores import const
from custom_components.kidschores.const import (
    COORDINATOR,
    DATA_BADGE_ASSIGNED_TO,
    DATA_BADGE_NAME,
    DATA_BADGE_TYPE,
    DATA_BADGES,
    DATA_KID_BADGE_PROGRESS,
    DOMAIN,
)


def test_badge_progress_initialized_on_assignment(
    hass: HomeAssistant,
    scenario_medium: tuple[Any, dict[str, str]],
) -> None:
    """Test that badge_progress is initialized when badge is assigned to a kid."""
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Get Weekly Wizard badge (periodic type) and Zoë kid IDs
    wizard_badge_id = name_to_id_map["badge:Wëekly Wïzard"]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Verify badge exists and is periodic type
    badge_data = coordinator._data[DATA_BADGES][wizard_badge_id]
    assert badge_data[DATA_BADGE_NAME] == "Wëekly Wïzard"
    assert badge_data[DATA_BADGE_TYPE] == const.BADGE_TYPE_PERIODIC

    # Initial state: badge not assigned, badge_progress should not exist
    zoe_progress = coordinator.kids_data[zoe_id].get(DATA_KID_BADGE_PROGRESS, {})
    assert wizard_badge_id not in zoe_progress, (
        "Badge progress should not exist before assignment"
    )

    # Assign badge to Zoë via direct data modification
    coordinator._data[DATA_BADGES][wizard_badge_id][DATA_BADGE_ASSIGNED_TO] = [zoe_id]

    # Call update_badge_entity to trigger badge_progress initialization
    coordinator.update_badge_entity(wizard_badge_id, badge_data)

    # Verify badge_progress was initialized
    zoe_progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS]
    assert wizard_badge_id in zoe_progress, (
        "badge_progress should be initialized for assigned badge"
    )


def test_badge_progress_cleaned_on_unassignment(
    hass: HomeAssistant,
    scenario_medium: tuple[Any, dict[str, str]],
) -> None:
    """Test that badge_progress is cleaned when badge is unassigned from a kid."""
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Get Daily Delight badge (daily type) and both kids
    daily_badge_id = name_to_id_map["badge:Dåily Dëlight"]
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    # Get badge data
    badge_data = coordinator._data[DATA_BADGES][daily_badge_id]
    assert badge_data[DATA_BADGE_NAME] == "Dåily Dëlight"
    assert badge_data[DATA_BADGE_TYPE] == const.BADGE_TYPE_DAILY

    # Assign to both kids
    coordinator._data[DATA_BADGES][daily_badge_id][DATA_BADGE_ASSIGNED_TO] = [
        zoe_id,
        max_id,
    ]
    coordinator.update_badge_entity(daily_badge_id, badge_data)

    # Verify both have badge_progress
    zoe_progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS]
    max_progress = coordinator.kids_data[max_id][DATA_KID_BADGE_PROGRESS]
    assert daily_badge_id in zoe_progress
    assert daily_badge_id in max_progress

    # Now reassign to only Zoë (remove Max)
    coordinator._data[DATA_BADGES][daily_badge_id][DATA_BADGE_ASSIGNED_TO] = [zoe_id]
    coordinator.update_badge_entity(daily_badge_id, badge_data)

    # Verify Max's badge_progress was removed, Zoë's remains
    zoe_progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS]
    max_progress = coordinator.kids_data[max_id][DATA_KID_BADGE_PROGRESS]
    assert daily_badge_id in zoe_progress, "Zoë should still have badge_progress"
    assert daily_badge_id not in max_progress, "Max's badge_progress should be removed"


def test_badge_progress_removed_on_badge_deletion(
    hass: HomeAssistant,
    scenario_medium: tuple[Any, dict[str, str]],
) -> None:
    """Test that badge_progress is removed when badge is deleted."""
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Get Special Occasion badge (special_occasion type) and both kids
    special_badge_id = name_to_id_map["badge:Spëcial Öccasion"]
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    # Get badge data
    badge_data = coordinator._data[DATA_BADGES][special_badge_id]
    assert badge_data[DATA_BADGE_NAME] == "Spëcial Öccasion"
    assert badge_data[DATA_BADGE_TYPE] == const.BADGE_TYPE_SPECIAL_OCCASION

    # Assign badge to both kids
    coordinator._data[DATA_BADGES][special_badge_id][DATA_BADGE_ASSIGNED_TO] = [
        zoe_id,
        max_id,
    ]
    coordinator.update_badge_entity(special_badge_id, badge_data)

    # Verify both have badge_progress
    zoe_progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS]
    max_progress = coordinator.kids_data[max_id][DATA_KID_BADGE_PROGRESS]
    assert special_badge_id in zoe_progress
    assert special_badge_id in max_progress

    # Delete the badge
    coordinator.delete_badge_entity(special_badge_id)

    # Verify badge_progress removed from both kids
    zoe_progress = coordinator.kids_data[zoe_id][DATA_KID_BADGE_PROGRESS]
    max_progress = coordinator.kids_data[max_id][DATA_KID_BADGE_PROGRESS]
    assert special_badge_id not in zoe_progress, (
        "Zoë's badge_progress should be removed after badge deletion"
    )
    assert special_badge_id not in max_progress, (
        "Max's badge_progress should be removed after badge deletion"
    )
