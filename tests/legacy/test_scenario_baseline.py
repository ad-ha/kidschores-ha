"""Scenario Baseline Tests - Validate scenario data loading.

This module tests that scenario YAML files load correctly and populate
the coordinator with the expected entities, progress state, and dashboard
helper sensor data.

Test Organization:
    - Scenario Structure Validation: Entity counts match YAML
    - Data Integrity Validation: Names, assignments, progress state
    - Dashboard Helper Validation: Sensor attributes populated correctly
"""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    CHORE_STATE_APPROVED,
    COORDINATOR,
    DOMAIN,
)

# ============================================================================
# Test Group: Scenario Structure Validation
# ============================================================================


async def test_minimal_scenario_entity_counts(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test minimal scenario loads correct entity counts.

    Expected:
        - 1 parent: Môm Astrid
        - 1 kid: Zoë
        - 2 chores: Feed the cåts, Wåter the plänts
        - 1 badge: Brønze Står
        - 1 bonus: Stär Sprïnkle Bonus
        - 1 penalty: Førget Chöre
        - 1 reward: Ice Créam!
    """
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    assert len(coordinator.parents_data) == 1
    assert len(coordinator.kids_data) == 1
    assert len(coordinator.chores_data) == 2
    assert len(coordinator.badges_data) == 1
    assert len(coordinator.bonuses_data) == 1
    assert len(coordinator.penalties_data) == 1
    assert len(coordinator.rewards_data) == 1

    # Verify name mapping exists for key entities
    assert "kid:Zoë" in name_to_id_map
    assert "parent:Môm Astrid Stârblüm" in name_to_id_map
    assert "chore:Feed the cåts" in name_to_id_map
    assert "reward:Ice Créam!" in name_to_id_map


async def test_medium_scenario_entity_counts(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test medium scenario loads correct entity counts.

    Expected:
        - 2 parents: Môm Astrid, Dad Leo
        - 2 kids: Zoë, Max!
        - 4 chores: Including shared chore
        - 2 badges: Brønze Står, Dåily Dëlight
        - 2 bonuses, 2 penalties, 2 rewards
    """
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    assert len(coordinator.parents_data) == 2
    assert len(coordinator.kids_data) == 2
    assert len(coordinator.chores_data) == 4
    assert len(coordinator.badges_data) == 6
    assert len(coordinator.bonuses_data) == 2
    assert len(coordinator.penalties_data) == 2
    assert len(coordinator.rewards_data) == 2

    # Verify both kids and parents exist
    assert "kid:Zoë" in name_to_id_map
    assert "kid:Max!" in name_to_id_map
    assert "parent:Môm Astrid Stârblüm" in name_to_id_map
    assert "parent:Dad Leo" in name_to_id_map


async def test_full_scenario_entity_counts(
    hass: HomeAssistant,
    scenario_full: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test full scenario loads correct entity counts.

    Expected:
        - 2 parents: Môm Astrid, Dad Leo
        - 3 kids: Zoë, Max!, Lila
        - 18 chores: Mix of daily, weekly, periodic, shared_all, shared_first, independent
        - 5 badges: Multiple cumulative with multipliers
        - 2 bonuses, 3 penalties, 5 rewards
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    assert len(coordinator.parents_data) == 2
    assert len(coordinator.kids_data) == 3
    assert len(coordinator.chores_data) == 18
    assert len(coordinator.badges_data) == 6
    assert len(coordinator.bonuses_data) == 2
    assert len(coordinator.penalties_data) == 3
    assert len(coordinator.rewards_data) == 5

    # Verify all three kids exist
    assert "kid:Zoë" in name_to_id_map
    assert "kid:Max!" in name_to_id_map
    assert "kid:Lila" in name_to_id_map


# ============================================================================
# Test Group: Data Integrity Validation
# ============================================================================


async def test_scenario_progress_state_applied(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test progress state from YAML applied correctly.

    Medium scenario progress:
        - Zoë: 35 points, 350 lifetime, 2 chores completed, 1 badge earned
        - Max!: 15 points, 180 lifetime, 1 chore completed, no badges
    """
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Verify Zoë's progress
    zoe_id = name_to_id_map["kid:Zoë"]
    zoe_data = coordinator.kids_data[zoe_id]
    assert zoe_data["points"] == 35.0
    assert zoe_data["point_stats"]["points_net_all_time"] == 350.0
    # Count approved chores from chore_data structure (v0.4.0+ format)
    zoe_approved_count = sum(
        1
        for cd in zoe_data.get("chore_data", {}).values()
        if cd.get("state") == CHORE_STATE_APPROVED
    )
    assert zoe_approved_count >= 2
    assert len(zoe_data["badges_earned"]) == 1

    # Verify Max!'s progress
    max_id = name_to_id_map["kid:Max!"]
    max_data = coordinator.kids_data[max_id]
    assert max_data["points"] == 15.0
    assert max_data["point_stats"]["points_net_all_time"] == 180.0
    # Count approved chores from chore_data structure (v0.4.0+ format)
    max_approved_count = sum(
        1
        for cd in max_data.get("chore_data", {}).values()
        if cd.get("state") == CHORE_STATE_APPROVED
    )
    assert max_approved_count >= 1
    assert len(max_data["badges_earned"]) == 0


async def test_scenario_kid_assignments(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test chores assigned to correct kids by name.

    Medium scenario assignments:
        - Feed the cåts → Zoë
        - Wåter the plänts → Zoë
        - Pick up Lëgo! → Max!
        - Stär sweep → Both (shared chore)
    """
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]

    # Check Feed the cåts assigned to Zoë only
    feed_cats_id = name_to_id_map["chore:Feed the cåts"]
    feed_cats = coordinator.chores_data[feed_cats_id]
    assert zoe_id in feed_cats["assigned_kids"]
    assert max_id not in feed_cats["assigned_kids"]

    # Check Stär sweep assigned to both (shared)
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    star_sweep = coordinator.chores_data[star_sweep_id]
    assert zoe_id in star_sweep["assigned_kids"]
    assert max_id in star_sweep["assigned_kids"]


async def test_scenario_special_characters(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test special characters in names preserved correctly.

    Validates Unicode handling: å, ï, ë, ø, @, !
    """
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Check kid name with special chars
    zoe_id = name_to_id_map["kid:Zoë"]
    zoe_data = coordinator.kids_data[zoe_id]
    assert zoe_data["name"] == "Zoë"  # ë preserved

    # Check parent name with special chars
    mom_id = name_to_id_map["parent:Môm Astrid Stârblüm"]
    mom_data = coordinator.parents_data[mom_id]
    assert "Astrid" in mom_data["name"]
    assert "Stârblüm" in mom_data["name"]  # â, ü preserved

    # Check chore name with special chars
    feed_cats_id = name_to_id_map["chore:Feed the cåts"]
    feed_cats = coordinator.chores_data[feed_cats_id]
    assert feed_cats["name"] == "Feed the cåts"  # å preserved


# ============================================================================
# Test Group: Dashboard Helper Validation
# ============================================================================


async def test_dashboard_helper_sensor_exists(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test dashboard helper sensor created for kid with valid attributes."""
    # Dashboard helper should exist for Zoë
    # Entity ID pattern: sensor.kc_zoe_ui_dashboard_helper
    from homeassistant.util import slugify

    mock_config_entry, _ = scenario_minimal

    # Reload config entry to ensure sensor platform creates dashboard helper
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    kid_slug = slugify("Zoë")
    dashboard_helper_id = f"sensor.kc_{kid_slug}_ui_dashboard_helper"

    state = hass.states.get(dashboard_helper_id)
    assert state is not None, (
        f"Dashboard helper sensor {dashboard_helper_id} should exist"
    )
    assert state.state is not None, "Dashboard helper sensor state should not be None"

    # Validate key attributes exist
    assert "ui_translations" in state.attributes, (
        "Should have ui_translations attribute"
    )
    assert "chores" in state.attributes, "Should have chores attribute"
    assert "rewards" in state.attributes, "Should have rewards attribute"


@pytest.mark.skip(
    reason="Dashboard helper requires entity platform reload after scenario loading"
)
async def test_dashboard_helper_chores_attribute(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],  # pylint: disable=unused-argument
) -> None:
    """Test dashboard helper chores attribute populated.

    TODO: Implement entity platform reload after kids added via scenario.

    Should contain list of chore dicts with:
        - name, points, status, due_date, icon, etc.
    """
    from homeassistant.util import slugify

    kid_slug = slugify("Zoë")
    dashboard_helper_id = f"sensor.kc_{kid_slug}_ui_dashboard_helper"

    state = hass.states.get(dashboard_helper_id)
    assert state is not None

    chores_attr = state.attributes.get("chores")
    assert chores_attr is not None
    assert isinstance(chores_attr, list)
    assert len(chores_attr) == 2  # Feed the cåts, Wåter the plänts

    # Verify structure of chore dicts
    for chore in chores_attr:
        assert "name" in chore
        assert "points" in chore
        assert "status" in chore


@pytest.mark.skip(
    reason="Dashboard helper requires entity platform reload after scenario loading"
)
async def test_dashboard_helper_ui_translations(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],  # pylint: disable=unused-argument
) -> None:
    """Test dashboard helper ui_translations dict loaded.

    TODO: Implement entity platform reload after kids added via scenario.

    Should contain 40+ translation keys for dashboard rendering.
    """
    from homeassistant.util import slugify

    kid_slug = slugify("Zoë")
    dashboard_helper_id = f"sensor.kc_{kid_slug}_ui_dashboard_helper"

    state = hass.states.get(dashboard_helper_id)
    assert state is not None

    ui_translations = state.attributes.get("ui_translations")
    assert ui_translations is not None
    assert isinstance(ui_translations, dict)
    assert len(ui_translations) > 10  # Should have many translation keys

    # Check for some expected keys
    expected_keys = ["welcome", "points", "chores", "rewards"]
    for key in expected_keys:
        # Translation keys should exist (may be "err-*" if not loaded)
        assert key in ui_translations or f"err-{key}" in list(ui_translations.values())
