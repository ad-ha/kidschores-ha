"""Shared entity validation helpers for Data Recovery and Migration testing.

Provides reusable functions for:
- Counting entities by platform (hardcoded to KidsChores domain)
- Generating expected entity ID prefixes
- Verifying kid entity creation (sensors, buttons, calendar, select)
- Checking entity states and attributes
- Getting summary counts for baseline comparison

Note: All entity counting functions are scoped to DOMAIN (kidschores) automatically.
No need to pass domain as an argument.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from custom_components.kidschores.const import DOMAIN


def count_entities_by_platform(
    hass: HomeAssistant,
    platform: str,
) -> int:
    """Count entities for a specific platform in KidsChores domain.

    Args:
        hass: Home Assistant instance
        platform: Platform name (sensor, button, calendar, select)

    Returns:
        Number of entities on the specified platform
    """
    entity_reg = er.async_get(hass)
    count = 0
    for entity in entity_reg.entities.values():
        # entity.domain is the platform (sensor, button, etc.)
        # entity.platform is the integration domain (kidschores)
        if entity.domain == platform and entity.platform == DOMAIN:
            count += 1
    return count


def get_kid_entity_prefix(kid_name: str) -> str:
    """Generate expected entity ID prefix for a kid.

    Follows pattern: kc_{slugified_name}_

    Args:
        kid_name: Human-readable kid name (e.g., "Zoë")

    Returns:
        Entity ID prefix (e.g., "kc_zoe_")
    """
    slug = slugify(kid_name)
    return f"kc_{slug}_"


def verify_kid_entities(
    hass: HomeAssistant,
    kid_name: str,
    expected_chore_count: int,
    verify_sensors: bool = True,
    verify_buttons: bool = True,
    verify_calendar: bool = True,
    verify_select: bool = True,
) -> dict[str, bool]:
    """Verify entity creation for one kid.

    Checks:
    - Sensors: Points, current chores (count), pending approvals (count)
    - Buttons: Claim/approve/disapprove for each chore (count)
    - Calendar: One calendar per kid
    - Select: Language select per kid

    Args:
        hass: Home Assistant instance
        kid_name: Kid name to verify entities for
        expected_chore_count: Expected number of assigned chores
        verify_sensors: Whether to verify sensor entities
        verify_buttons: Whether to verify button entities
        verify_calendar: Whether to verify calendar entity
        verify_select: Whether to verify select entity

    Returns:
        Dict with verification results:
        {
            "sensors": bool,
            "buttons": bool,
            "calendar": bool,
            "select": bool,
            "details": {
                "sensor_count": int,
                "button_count": int,
                "calendar_count": int,
                "select_count": int,
            }
        }
    """
    entity_reg = er.async_get(hass)
    prefix = get_kid_entity_prefix(kid_name)

    # Count entities for this kid
    sensor_count = 0
    button_count = 0
    calendar_count = 0
    select_count = 0

    for entity in entity_reg.entities.values():
        # entity.domain is the platform (sensor, button, etc.)
        # entity.platform is the integration domain (kidschores)
        # entity_id format is "domain.unique_id" e.g. "sensor.kc_zoe_points"
        # Check if the part after the dot starts with our prefix
        if entity.platform == DOMAIN:
            # Split entity_id into domain and unique_id parts
            entity_id_parts = entity.entity_id.split(".", 1)
            if len(entity_id_parts) == 2:
                unique_id = entity_id_parts[1]
                # Calendar entity is just "kc_zoe" without trailing underscore
                # Other entities are "kc_zoe_*" with trailing underscore
                prefix_match = unique_id.startswith(
                    prefix
                ) or unique_id == prefix.rstrip("_")
                if prefix_match:
                    if entity.domain == "sensor":
                        sensor_count += 1
                    elif entity.domain == "button":
                        button_count += 1
                    elif entity.domain == "calendar":
                        calendar_count += 1
                    elif entity.domain == "select":
                        select_count += 1

    # Verify counts
    results = {
        "sensors": True,
        "buttons": True,
        "calendar": True,
        "select": True,
        "details": {
            "sensor_count": sensor_count,
            "button_count": button_count,
            "calendar_count": calendar_count,
            "select_count": select_count,
        },
    }

    if verify_sensors:
        # Expect: points sensor + pending chores sensor + pending approvals sensor
        # = minimum 3 sensors per kid
        results["sensors"] = sensor_count >= 3

    if verify_buttons:
        # Expect: 3 buttons per chore (claim, approve, disapprove)
        # = minimum 3 * expected_chore_count buttons
        results["buttons"] = button_count >= (3 * expected_chore_count)

    if verify_calendar:
        # Expect: exactly 1 calendar per kid
        results["calendar"] = calendar_count == 1

    if verify_select:
        # Expect: exactly 1 language select per kid
        results["select"] = select_count == 1

    return results


def verify_entity_state(
    hass: HomeAssistant,
    entity_id: str,
    expected_state: str | None = None,
    check_attributes: dict | None = None,
) -> bool:
    """Verify entity state and optional attributes.

    Args:
        hass: Home Assistant instance
        entity_id: Full entity ID to check (e.g., sensor.kc_zoe_points)
        expected_state: Expected state value (optional)
        check_attributes: Dict of attributes to verify (optional)

    Returns:
        True if entity exists and matches expectations, False otherwise
    """
    state = hass.states.get(entity_id)

    if not state:
        return False

    if expected_state is not None and state.state != expected_state:
        return False

    if check_attributes:
        for attr_name, attr_value in check_attributes.items():
            if state.attributes.get(attr_name) != attr_value:
                return False

    return True


def get_entity_counts_summary(hass: HomeAssistant) -> dict[str, int]:
    """Get summary of all KidsChores entities by platform.

    Returns:
        Dict with entity counts:
        {
            "sensors": int,
            "buttons": int,
            "calendars": int,
            "selects": int,
        }
    """
    return {
        "sensors": count_entities_by_platform(hass, "sensor"),
        "buttons": count_entities_by_platform(hass, "button"),
        "calendars": count_entities_by_platform(hass, "calendar"),
        "selects": count_entities_by_platform(hass, "select"),
    }
