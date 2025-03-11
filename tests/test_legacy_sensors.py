"""Tests for legacy sensor toggle functionality."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.kidschores import const

pytestmark = pytest.mark.usefixtures("init_integration")


async def test_legacy_sensors_created_when_enabled(
    hass: HomeAssistant,
    mock_config_entry,  # pylint: disable=unused-argument
    mock_coordinator,  # pylint: disable=unused-argument
):
    """Test that legacy sensors are created when show_legacy_entities is True."""
    # The mock_config_entry fixture has show_legacy_entities = True by default
    entity_registry = er.async_get(hass)

    # Count legacy sensor entities
    legacy_sensors = []
    for entity in entity_registry.entities.values():
        if entity.domain == "sensor" and const.DOMAIN in entity.platform:
            # Legacy sensor patterns
            if any(
                pattern in entity.unique_id
                for pattern in [
                    const.SENSOR_KC_UID_SUFFIX_COMPLETED_TOTAL_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_COMPLETED_DAILY_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_COMPLETED_WEEKLY_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_COMPLETED_MONTHLY_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_PENDING_CHORE_APPROVALS_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_PENDING_REWARD_APPROVALS_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_DAILY_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_WEEKLY_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_MONTHLY_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_KID_HIGHEST_STREAK_SENSOR,
                ]
            ):
                legacy_sensors.append(entity.entity_id)

    # With no kids, expect only 2 global legacy sensors:
    # - pending_chore_approvals
    # - pending_reward_approvals
    # Per-kid legacy sensors only created when kids exist
    assert len(legacy_sensors) == 2, (
        f"Expected exactly 2 global legacy sensors (no kids configured), "
        f"found {len(legacy_sensors)}: {legacy_sensors}"
    )

    # Verify the specific sensors present
    assert any("pending" in s and "chore" in s for s in legacy_sensors), (
        "Missing pending chore approvals sensor"
    )
    assert any("pending" in s and "reward" in s for s in legacy_sensors), (
        "Missing pending reward approvals sensor"
    )


@pytest.mark.skip(reason="Need to implement fixture with disabled legacy sensors")
async def test_legacy_sensors_not_created_when_disabled(hass: HomeAssistant):
    """Test that legacy sensors are NOT created when show_legacy_entities is False."""
    entity_registry = er.async_get(hass)

    # Count legacy sensor entities
    legacy_sensors = []
    for entity in entity_registry.entities.values():
        if entity.domain == "sensor" and const.DOMAIN in entity.platform:
            # Legacy sensor patterns
            if any(
                pattern in entity.unique_id
                for pattern in [
                    const.SENSOR_KC_UID_SUFFIX_COMPLETED_TOTAL_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_COMPLETED_DAILY_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_COMPLETED_WEEKLY_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_COMPLETED_MONTHLY_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_PENDING_CHORE_APPROVALS_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_PENDING_REWARD_APPROVALS_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_DAILY_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_WEEKLY_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_MONTHLY_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_KID_HIGHEST_STREAK_SENSOR,
                ]
            ):
                legacy_sensors.append(entity.entity_id)

    assert len(legacy_sensors) == 0, (
        f"Expected 0 legacy sensors when disabled, "
        f"found {len(legacy_sensors)}: {legacy_sensors}"
    )


async def test_legacy_sensors_removed_when_option_changed(
    hass: HomeAssistant,
    mock_config_entry,
    init_integration,  # pylint: disable=unused-argument
):
    """Test that legacy sensors are removed when show_legacy_entities changes from True to False."""
    entity_registry = er.async_get(hass)

    # Verify legacy sensors exist initially (flag enabled by default in fixture)
    initial_legacy_sensors = []
    for entity in entity_registry.entities.values():
        if entity.domain == "sensor" and const.DOMAIN in entity.platform:
            if any(
                pattern in entity.unique_id
                for pattern in [
                    const.SENSOR_KC_UID_SUFFIX_PENDING_CHORE_APPROVALS_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_PENDING_REWARD_APPROVALS_SENSOR,
                ]
            ):
                initial_legacy_sensors.append(entity.entity_id)

    assert len(initial_legacy_sensors) == 2, (
        f"Expected 2 global legacy sensors initially, found {len(initial_legacy_sensors)}"
    )

    # Disable legacy entities via options
    new_options = dict(mock_config_entry.options)
    new_options[const.CONF_SHOW_LEGACY_ENTITIES] = False
    hass.config_entries.async_update_entry(mock_config_entry, options=new_options)

    # Reload config entry (should trigger cleanup)
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify legacy sensors are REMOVED from registry (not just unavailable)
    remaining_legacy_sensors = []
    for entity in entity_registry.entities.values():
        if entity.domain == "sensor" and const.DOMAIN in entity.platform:
            if any(
                pattern in entity.unique_id
                for pattern in [
                    const.SENSOR_KC_UID_SUFFIX_PENDING_CHORE_APPROVALS_SENSOR,
                    const.SENSOR_KC_UID_SUFFIX_PENDING_REWARD_APPROVALS_SENSOR,
                ]
            ):
                remaining_legacy_sensors.append(entity.entity_id)

    assert len(remaining_legacy_sensors) == 0, (
        f"Expected 0 legacy sensors after disabling flag, "
        f"found {len(remaining_legacy_sensors)}: {remaining_legacy_sensors}"
    )

    # Verify entities are not just unavailable - they should be GONE
    for entity_id in initial_legacy_sensors:
        entity_entry = entity_registry.async_get(entity_id)
        assert entity_entry is None, (
            f"Entity {entity_id} should be removed from registry, not just unavailable"
        )
