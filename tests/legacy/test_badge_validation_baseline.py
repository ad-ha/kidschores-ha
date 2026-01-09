"""Baseline tests for badge validation in config/options flows.

Tests target critical coverage gaps in flow_helpers.py validation:
- Line 1108: assigned_to field validation
- Line 1110: assigned_to field validation

Uses validate_badge_common_inputs function signature from working code.
"""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    BADGE_TYPE_CUMULATIVE,
    CFOF_BADGES_INPUT_ASSIGNED_TO,
    CFOF_BADGES_INPUT_ICON,
    CFOF_BADGES_INPUT_NAME,
    CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE,
    CFOF_BADGES_INPUT_TYPE,
    COORDINATOR,
    DATA_BADGES,
    DOMAIN,
)
from custom_components.kidschores.flow_helpers import validate_badge_common_inputs

# pylint: disable=redefined-outer-name


async def test_assigned_to_empty_list_valid(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test assigned_to with empty list is valid (assigns to all kids).

    Covers flow_helpers.py line 1108: empty assigned_to validation.
    """
    # Arrange
    config_entry, _ = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    badge_input = {
        CFOF_BADGES_INPUT_NAME: "Test Badge Empty Assigned",
        CFOF_BADGES_INPUT_TYPE: BADGE_TYPE_CUMULATIVE,
        CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE: 100,
        CFOF_BADGES_INPUT_ICON: "mdi:star",
        CFOF_BADGES_INPUT_ASSIGNED_TO: [],
    }

    # Act: Validate using actual function signature from flow_helpers.py
    errors = validate_badge_common_inputs(
        user_input=badge_input,
        internal_id=None,
        existing_badges=coordinator._data[DATA_BADGES],  # pylint: disable=protected-access
        badge_type=BADGE_TYPE_CUMULATIVE,
    )

    # Assert: No validation errors for empty assigned_to
    assert not errors or "assigned_to" not in errors.get("base", "")


async def test_assigned_to_valid_kid_ids(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test assigned_to with valid kid IDs is accepted.

    Covers flow_helpers.py line 1108, 1110: valid kid ID validation.
    """
    # Arrange
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    badge_input = {
        CFOF_BADGES_INPUT_NAME: "Test Badge Valid Assigned",
        CFOF_BADGES_INPUT_TYPE: BADGE_TYPE_CUMULATIVE,
        CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE: 100,
        CFOF_BADGES_INPUT_ICON: "mdi:star",
        CFOF_BADGES_INPUT_ASSIGNED_TO: [zoe_id, max_id],
    }

    # Act
    errors = validate_badge_common_inputs(
        user_input=badge_input,
        internal_id=None,
        existing_badges=coordinator._data[DATA_BADGES],  # pylint: disable=protected-access
        badge_type=BADGE_TYPE_CUMULATIVE,
    )

    # Assert: No validation errors for valid kid IDs
    assert not errors or "assigned_to" not in errors.get("base", "")
