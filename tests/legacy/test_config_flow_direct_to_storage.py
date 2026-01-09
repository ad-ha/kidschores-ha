"""Test config flow direct-to-storage functionality.

Validates that fresh installations (KC 4.0) write entities directly to
.storage/kidschores_data with schema_version 42, bypassing migration.

Uses scenario_minimal fixture (testdata_scenario_minimal.yaml) character names (Zoë, Môm Astrid, "Feed the cåts").
"""

# pylint: disable=protected-access  # Accessing internal methods for testing

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kidschores.const import (
    COORDINATOR,
    DATA_CHORES,
    DATA_KIDS,
    DATA_META,
    DATA_META_SCHEMA_VERSION,
    DATA_PARENTS,
    DOMAIN,
    SCHEMA_VERSION_STORAGE_ONLY,
)


@pytest.mark.asyncio
async def test_direct_storage_creates_one_parent_one_kid_one_chore(
    hass: HomeAssistant, scenario_minimal
) -> None:
    """Test that direct-to-storage creates exactly 1 parent, 1 kid, 1 chore.

    Uses scenario_minimal fixture which loads testdata_scenario_minimal.yaml:
    - 1 parent: Môm Astrid Stârblüm
    - 1 kid: Zoë
    - 2 chores: Feed the cåts, Wåter the plänts

    Validates entities are in storage (not config entry) and schema_version is 41.
    """
    config_entry, name_to_id_map = scenario_minimal

    # Scenario fixture loads from YAML which may have minimal config data
    # In KC 4.0+, config_entry.data should be empty or only have schema_version
    # Entity data (kids, parents, chores) should NOT be in config entry
    assert "kids" not in config_entry.data
    assert "parents" not in config_entry.data
    assert "chores" not in config_entry.data

    # Check options also has no entity data
    assert "kids" not in config_entry.options
    assert "parents" not in config_entry.options
    assert "chores" not in config_entry.options

    # Verify coordinator loaded the data from storage
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Check schema version is 42 (storage-only mode) - stored in meta section
    meta = coordinator.data.get(DATA_META, {})
    assert meta.get(DATA_META_SCHEMA_VERSION) == SCHEMA_VERSION_STORAGE_ONLY
    assert SCHEMA_VERSION_STORAGE_ONLY == 42

    # Verify exactly 1 parent from storyline
    parents = coordinator.data[DATA_PARENTS]
    assert len(parents) == 1
    parent_id = name_to_id_map["parent:Môm Astrid Stârblüm"]
    assert parent_id in parents
    assert parents[parent_id]["name"] == "Môm Astrid Stârblüm"

    # Verify exactly 1 kid from storyline
    kids = coordinator.data[DATA_KIDS]
    assert len(kids) == 1
    kid_id = name_to_id_map["kid:Zoë"]
    assert kid_id in kids
    assert kids[kid_id]["name"] == "Zoë"

    # Verify chores exist from storyline (scenario_minimal has 2)
    chores = coordinator.data[DATA_CHORES]
    assert len(chores) == 2
    chore_id = name_to_id_map["chore:Feed the cåts"]
    assert chore_id in chores
    assert chores[chore_id]["name"] == "Feed the cåts"
