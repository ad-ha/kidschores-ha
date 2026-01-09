"""Test that all kid entities have kid_name attribute and display entity information."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.kidschores import const

pytestmark = pytest.mark.asyncio


async def test_all_kid_entities_have_kid_name_attribute(
    hass: HomeAssistant, scenario_medium
) -> None:
    """Verify all kid entities have kid_name attribute and display comprehensive info."""
    # Load the integration
    config_entry, _ = scenario_medium

    # Get registries
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)

    # Get all entities for kidschores integration
    entries = er.async_entries_for_config_entry(entity_reg, config_entry.entry_id)

    # Filter kid-related entities (exclude system/global entities)
    # Kid entities have a kid in their unique_id or entity_id
    kid_entities = []
    for entry in entries:
        # Skip global entities like reset buttons, admin entities, global sensors
        if any(
            keyword in entry.entity_id
            for keyword in [
                "_reset_",
                "_admin_",
                "select.kc_chores_",
                "select.kc_rewards_",
                "select.kc_parents_",
                "select.kc_all_",  # Skip global select entities
                "_global_",  # Skip global sensors (e.g., kc_global_chore_pending_approvals)
            ]
        ):
            continue

        # Include entities that belong to a kid
        if entry.entity_id.startswith("sensor.kc_") or entry.entity_id.startswith(
            "button.kc_"
        ):
            kid_entities.append(entry)
        elif entry.entity_id.startswith("calendar.kc_") or entry.entity_id.startswith(
            "datetime.kc_"
        ):
            kid_entities.append(entry)
        elif (
            entry.entity_id.startswith("select.kc_")
            and "_ui_dashboard_chore_list_helper" in entry.entity_id
        ):
            kid_entities.append(entry)

    print(f"\n{'=' * 80}")
    print(f"TESTING {len(kid_entities)} KID ENTITIES FOR kid_name ATTRIBUTE")
    print(f"{'=' * 80}\n")

    # Track results
    entities_with_kid_name = []
    entities_without_kid_name = []

    # Check each entity
    for entry in kid_entities:
        state = hass.states.get(entry.entity_id)
        if not state:
            continue

        # Get device info
        device_name = "Unknown"
        if entry.device_id:
            device = device_reg.async_get(entry.device_id)
            if device:
                device_name = device.name or "Unknown"

        # Extract entity info
        entity_id = entry.entity_id
        friendly_name = state.attributes.get("friendly_name", "Unknown")
        kid_name_attr = state.attributes.get(const.ATTR_KID_NAME)

        # Display entity info
        print(f"Entity: {entity_id}")
        print(f"  Device Name:    {device_name}")
        print(f"  Friendly Name:  {friendly_name}")
        print(f"  kid_name attr:  {kid_name_attr}")

        # Track if kid_name exists
        if kid_name_attr:
            entities_with_kid_name.append(entity_id)
            print("  ✅ Has kid_name attribute")
        else:
            entities_without_kid_name.append(entity_id)
            print("  ❌ MISSING kid_name attribute")

        print()

    # Summary
    print(f"{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total kid entities checked: {len(kid_entities)}")
    print(f"Entities WITH kid_name:     {len(entities_with_kid_name)}")
    print(f"Entities WITHOUT kid_name:  {len(entities_without_kid_name)}")

    if entities_without_kid_name:
        print("\n❌ MISSING kid_name attribute:")
        for entity_id in entities_without_kid_name:
            print(f"  - {entity_id}")

    print(f"{'=' * 80}\n")

    # Assert all kid entities have kid_name attribute
    assert len(entities_without_kid_name) == 0, (
        f"Found {len(entities_without_kid_name)} kid entities without kid_name attribute"
    )


async def test_specific_friendly_names(hass: HomeAssistant, scenario_medium) -> None:
    """Verify specific entities have correct friendly names."""
    _, _ = scenario_medium

    # Check UI Dashboard Helper (assuming Zoë is first kid in scenario_medium)
    dashboard_helper = hass.states.get("sensor.kc_zoe_ui_dashboard_helper")
    if dashboard_helper is None:
        pytest.skip("Dashboard helper entity not available in scenario_medium")

    assert dashboard_helper is not None
    assert "UI Dashboard Helper" in dashboard_helper.attributes.get(
        "friendly_name", ""
    ), "Dashboard helper should have 'UI Dashboard Helper' in friendly name"

    # Check UI Dashboard Date Helper
    date_helper = hass.states.get("datetime.kc_zoe_ui_dashboard_date_helper")
    assert date_helper is not None
    assert "UI Dashboard Date Helper" in date_helper.attributes.get(
        "friendly_name", ""
    ), "Date helper should have 'UI Dashboard Date Helper' in friendly name"

    # Check that datetime entity does NOT have kid_id attribute
    assert "kid_id" not in date_helper.attributes, (
        "Datetime entity should not have kid_id attribute"
    )
    assert const.ATTR_KID_NAME in date_helper.attributes, (
        "Datetime entity should have kid_name attribute"
    )

    print(f"\n{'=' * 80}")
    print("SPECIFIC FRIENDLY NAME CHECKS")
    print(f"{'=' * 80}")
    print(
        f"✅ Dashboard Helper: {dashboard_helper.attributes.get('friendly_name', 'Unknown')}"
    )
    print(f"✅ Date Helper: {date_helper.attributes.get('friendly_name', 'Unknown')}")
    print(
        f"✅ Date Helper kid_name: {date_helper.attributes.get(const.ATTR_KID_NAME, 'Unknown')}"
    )
    print("✅ Date Helper has NO kid_id attribute")
    print(f"{'=' * 80}\n")


async def test_chore_status_friendly_name(hass: HomeAssistant, scenario_medium) -> None:
    """Verify chore status sensors have 'Chore Status' in friendly name."""
    config_entry, _ = scenario_medium

    entity_reg = er.async_get(hass)
    entries = er.async_entries_for_config_entry(entity_reg, config_entry.entry_id)

    # Find chore status sensors
    chore_status_sensors = [
        entry
        for entry in entries
        if entry.entity_id.startswith("sensor.kc_")
        and "_chore_status_" in entry.entity_id
    ]

    print(f"\n{'=' * 80}")
    print(f"CHORE STATUS SENSOR NAME CHECKS ({len(chore_status_sensors)} found)")
    print(f"{'=' * 80}")

    for entry in chore_status_sensors:
        state = hass.states.get(entry.entity_id)
        if state:
            friendly_name = state.attributes.get("friendly_name", "Unknown")
            print(f"{entry.entity_id}")
            print(f"  Friendly Name: {friendly_name}")

            # Verify 'Chore Status' appears in friendly name
            assert "Chore Status" in friendly_name, (
                f"Chore status sensor {entry.entity_id} should have 'Chore Status' "
                f"in friendly name, got: {friendly_name}"
            )
            print("  ✅ Contains 'Chore Status'")

    print(f"{'=' * 80}\n")
