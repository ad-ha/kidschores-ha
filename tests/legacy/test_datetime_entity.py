"""Test datetime entity functionality."""

from datetime import datetime, timedelta

import pytest
from homeassistant.components.datetime import DOMAIN as DATETIME_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.kidschores import const


@pytest.mark.asyncio
async def test_datetime_entity_created_for_each_kid(
    hass: HomeAssistant, scenario_medium
) -> None:
    """Test that datetime helper entities are created for each kid."""
    config_entry, _ = scenario_medium  # Fixture sets up integration with kids

    # Reload datetime platform to create entities with scenario data
    await hass.config_entries.async_unload_platforms(config_entry, [DATETIME_DOMAIN])
    await hass.async_block_till_done()
    await hass.config_entries.async_forward_entry_setups(
        config_entry, [DATETIME_DOMAIN]
    )
    await hass.async_block_till_done()
    await hass.async_block_till_done()  # Extra wait for entity registration

    # Check datetime entities exist for both kids (names are slugified - ë becomes e)
    zoe_datetime = hass.states.get("datetime.kc_zoe_ui_dashboard_date_helper")
    max_datetime = hass.states.get("datetime.kc_max_ui_dashboard_date_helper")

    assert zoe_datetime is not None, "Zoë datetime entity should exist"
    assert max_datetime is not None, "Max! datetime entity should exist"

    # Verify friendly names (includes device name prefix from create_kid_device_info)
    assert "Zoë" in zoe_datetime.attributes.get("friendly_name", "")
    assert "UI Dashboard Date Helper" in zoe_datetime.attributes.get(
        "friendly_name", ""
    )
    assert "Max!" in max_datetime.attributes.get("friendly_name", "")
    assert "UI Dashboard Date Helper" in max_datetime.attributes.get(
        "friendly_name", ""
    )


@pytest.mark.asyncio
async def test_datetime_entity_has_device_info(
    hass: HomeAssistant, scenario_medium
) -> None:
    """Test that datetime entities are properly grouped under kid devices."""
    from homeassistant.helpers import entity_registry as er

    config_entry, _ = scenario_medium  # Fixture sets up integration with kids

    # Reload datetime platform to create entities with scenario data
    await hass.config_entries.async_unload_platforms(config_entry, [DATETIME_DOMAIN])
    await hass.async_block_till_done()
    await hass.config_entries.async_forward_entry_setups(
        config_entry, [DATETIME_DOMAIN]
    )
    await hass.async_block_till_done()

    # Get entity registry
    entity_registry = er.async_get(hass)

    # Check Zoë's datetime entity (slugified name: ë → e)
    zoe_datetime_entry = entity_registry.async_get(
        "datetime.kc_zoe_ui_dashboard_date_helper"
    )
    assert zoe_datetime_entry is not None
    assert zoe_datetime_entry.device_id is not None

    # Check Max's datetime entity
    max_datetime_entry = entity_registry.async_get(
        "datetime.kc_max_ui_dashboard_date_helper"
    )
    assert max_datetime_entry is not None
    assert max_datetime_entry.device_id is not None


@pytest.mark.asyncio
async def test_datetime_entity_default_value(
    hass: HomeAssistant, scenario_medium
) -> None:
    """Test that datetime entity has correct default value (tomorrow at noon)."""
    config_entry, _ = scenario_medium  # Fixture sets up integration with kids

    # Reload datetime platform to create entities with scenario data
    await hass.config_entries.async_unload_platforms(config_entry, [DATETIME_DOMAIN])
    await hass.async_block_till_done()
    await hass.config_entries.async_forward_entry_setups(
        config_entry, [DATETIME_DOMAIN]
    )
    await hass.async_block_till_done()

    # Get datetime entity state (slugified name: ë → e)
    zoe_datetime = hass.states.get("datetime.kc_zoe_ui_dashboard_date_helper")
    assert zoe_datetime is not None

    # Parse the state value
    state_value = dt_util.parse_datetime(zoe_datetime.state)
    assert state_value is not None

    # Should be approximately tomorrow at noon (within a few seconds tolerance)
    now = dt_util.now()
    expected = (now + timedelta(days=1)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )

    # Allow 5 second tolerance for test execution time
    time_diff = abs((state_value - expected).total_seconds())
    assert time_diff < 5, f"Default time should be tomorrow at noon, got {state_value}"


@pytest.mark.asyncio
async def test_datetime_entity_set_value(hass: HomeAssistant, scenario_medium) -> None:
    """Test that datetime entity value can be updated via service."""
    config_entry, _ = scenario_medium  # Fixture sets up integration with kids

    # Reload datetime platform to create entities with scenario data
    await hass.config_entries.async_unload_platforms(config_entry, [DATETIME_DOMAIN])
    await hass.async_block_till_done()
    await hass.config_entries.async_forward_entry_setups(
        config_entry, [DATETIME_DOMAIN]
    )
    await hass.async_block_till_done()

    # Create a specific datetime to set
    test_datetime = datetime(2025, 12, 25, 14, 30, 0)
    test_datetime = test_datetime.replace(tzinfo=dt_util.get_default_time_zone())

    # Call set_value service (slugified name: ë → e)
    await hass.services.async_call(
        DATETIME_DOMAIN,
        "set_value",
        {
            "entity_id": "datetime.kc_zoe_ui_dashboard_date_helper",
            "datetime": test_datetime.isoformat(),
        },
        blocking=True,
    )

    # Verify the value was updated
    zoe_datetime = hass.states.get("datetime.kc_zoe_ui_dashboard_date_helper")
    state_value = dt_util.parse_datetime(zoe_datetime.state)

    assert state_value == test_datetime, "Datetime value should be updated"


@pytest.mark.asyncio
async def test_datetime_entity_extra_attributes(
    hass: HomeAssistant, scenario_medium
) -> None:
    """Test that datetime entity includes kid_id and kid_name attributes."""
    config_entry, _ = scenario_medium  # Fixture sets up integration with kids

    # Reload datetime platform to create entities with scenario data
    await hass.config_entries.async_unload_platforms(config_entry, [DATETIME_DOMAIN])
    await hass.async_block_till_done()
    await hass.config_entries.async_forward_entry_setups(
        config_entry, [DATETIME_DOMAIN]
    )
    await hass.async_block_till_done()

    # Get datetime entity (slugified name: ë → e)
    zoe_datetime = hass.states.get("datetime.kc_zoe_ui_dashboard_date_helper")
    assert zoe_datetime is not None

    # Check extra attributes (using ATTR_KID_NAME which is "kid_name" attribute key)
    assert const.ATTR_KID_NAME in zoe_datetime.attributes
    assert zoe_datetime.attributes[const.ATTR_KID_NAME] == "Zoë"
