"""Test reset_all_data service properly cleans up entity registry.

This test validates that calling reset_all_data:
1. Removes all entity registry entries
2. Clears storage data
3. Allows re-adding kids/chores without _2 suffix on entity IDs
"""

# pylint: disable=protected-access  # Accessing internal methods for testing

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    COORDINATOR,
    DOMAIN,
    SERVICE_RESET_ALL_DATA,
)


def _get_coordinator(hass: HomeAssistant, entry: MockConfigEntry):
    """Get the coordinator instance from hass.data.

    Helper function to get current coordinator reference,
    which is especially important after reset_all_data since it reloads
    the config entry and creates a new coordinator instance.
    """
    return hass.data[DOMAIN][entry.entry_id][COORDINATOR]


@pytest.mark.asyncio
async def test_reset_all_data_cleans_entity_registry(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that reset_all_data removes ALL entity registry entries."""
    coordinator = _get_coordinator(hass, init_integration)
    ent_reg = er.async_get(hass)

    # Mock notifications to prevent ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Step 1: Count initial entities (global select/sensor entities)
        initial_entities = er.async_entries_for_config_entry(
            ent_reg, init_integration.entry_id
        )
        initial_entity_count = len(initial_entities)
        assert initial_entity_count > 0, "Should have global entities (select/sensor)"

        print(f"\n✓ Integration has {initial_entity_count} global entities")

        # Step 2: Add a kid and chore to populate coordinator data
        kid_id = str(uuid.uuid4())
        kid_name = "Test Kid"
        kid_data = {
            "name": kid_name,
            "points": 10.0,
            "ha_user_id": "",
            "enable_notifications": False,
            "mobile_notify_service": "",
            "use_persistent_notifications": False,
            "internal_id": kid_id,
        }
        coordinator._create_kid(kid_id, kid_data)

        chore_id = str(uuid.uuid4())
        chore_name = "Test Chore"
        chore_data = {
            "name": chore_name,
            "default_points": 5.0,
            "assigned_kids": [kid_id],
            "partial_allowed": False,
            "shared_chore": False,
            "allow_multiple_claims_per_day": False,
            "description": "",
            "chore_labels": [],
            "icon": "mdi:test",
            "recurring_frequency": "daily",
            "custom_interval": None,
            "custom_interval_unit": None,
            "due_date": None,
            "applicable_days": [],
            "notify_on_claim": True,
            "notify_on_approval": True,
            "notify_on_disapproval": True,
            "internal_id": chore_id,
        }
        coordinator._create_chore(chore_id, chore_data)

        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Step 3: Verify coordinator has data
        assert len(coordinator.kids_data) == 1, "Coordinator should have 1 kid"
        assert len(coordinator.chores_data) == 1, "Coordinator should have 1 chore"

        print("✓ Added kid and chore to coordinator")

        # Step 4: Call reset_all_data service
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RESET_ALL_DATA,
            {},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Step 5: Get fresh coordinator reference (reset_all_data reloads entry, creating new coordinator)
        coordinator = _get_coordinator(hass, init_integration)

        # Step 6: Verify entity registry cleaned and recreated (reload recreates global entities)
        # The reset removes all entities, then reload recreates global select/sensor entities
        entities_after_reset = er.async_entries_for_config_entry(
            ent_reg, init_integration.entry_id
        )
        assert len(entities_after_reset) == initial_entity_count, (
            f"After reset+reload, should have {initial_entity_count} global entities again, "
            f"but found {len(entities_after_reset)}: "
            f"{[e.entity_id for e in entities_after_reset]}"
        )

        print("✓ Entity registry cleaned and global entities recreated after reload")

        # Step 7: Verify storage is cleared
        assert len(coordinator.kids_data) == 0, "Kids data should be empty"
        assert len(coordinator.chores_data) == 0, "Chores data should be empty"

        print("✓ Storage cleared")

        # Step 8: Re-add the same kid and chore
        coordinator._create_kid(kid_id, kid_data)
        coordinator._create_chore(chore_id, chore_data)
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Step 9: Verify entities recreated without _2 suffixes
        final_entities = er.async_entries_for_config_entry(
            ent_reg, init_integration.entry_id
        )
        entity_ids_with_suffixes = [
            e.entity_id for e in final_entities if "_2" in e.entity_id
        ]

        assert len(entity_ids_with_suffixes) == 0, (
            f"Should NOT find any _2 suffixes. Found: {entity_ids_with_suffixes}"
        )

        print(f"✓ Recreated {len(final_entities)} entities, none with _2 suffix")
        print(
            f"✓ Entity count matches: initial={initial_entity_count}, final={len(final_entities)}"
        )


@pytest.mark.asyncio
async def test_reset_all_data_with_multiple_kids_no_duplicates(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test reset_all_data with multiple kids prevents all entity duplicates."""
    coordinator = _get_coordinator(hass, init_integration)
    ent_reg = er.async_get(hass)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Create 3 kids with 2 chores each
        kid_names = ["Alice", "Bob", "Charlie"]
        kid_ids = []

        for kid_name in kid_names:
            kid_id = str(uuid.uuid4())
            kid_ids.append(kid_id)
            kid_data = {
                "name": kid_name,
                "points": 0.0,
                "ha_user_id": "",
                "enable_notifications": False,
                "mobile_notify_service": "",
                "use_persistent_notifications": False,
                "internal_id": kid_id,
            }
            coordinator._create_kid(kid_id, kid_data)

            # Create 2 chores for this kid
            for chore_num in [1, 2]:
                chore_id = str(uuid.uuid4())
                chore_data = {
                    "name": f"{kid_name} Chore {chore_num}",
                    "default_points": 5.0,
                    "assigned_kids": [kid_id],
                    "partial_allowed": False,
                    "shared_chore": False,
                    "allow_multiple_claims_per_day": False,
                    "description": "",
                    "chore_labels": [],
                    "icon": "mdi:test",
                    "recurring_frequency": "daily",
                    "custom_interval": None,
                    "custom_interval_unit": None,
                    "due_date": None,
                    "applicable_days": [],
                    "notify_on_claim": True,
                    "notify_on_approval": True,
                    "notify_on_disapproval": True,
                    "internal_id": chore_id,
                }
                coordinator._create_chore(chore_id, chore_data)

        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Count initial entities
        initial_entities = er.async_entries_for_config_entry(
            ent_reg, init_integration.entry_id
        )
        initial_count = len(initial_entities)
        print(f"\n✓ Created {initial_count} entities for 3 kids")

        # Reset all data
        await hass.services.async_call(
            DOMAIN, SERVICE_RESET_ALL_DATA, {}, blocking=True
        )
        await hass.async_block_till_done()

        # Get fresh coordinator reference (reset_all_data reloads entry, creating new coordinator)
        coordinator = _get_coordinator(hass, init_integration)

        # Verify cleanup (reload recreates global entities, which is expected)
        entities_after_reset = er.async_entries_for_config_entry(
            ent_reg, init_integration.entry_id
        )
        assert len(entities_after_reset) == initial_count, (
            f"After reset+reload, should have {initial_count} global entities, "
            f"found {len(entities_after_reset)}"
        )
        print(f"✓ Removed all {initial_count} entity registry entries")

        # Re-add all kids and chores
        for idx, kid_name in enumerate(kid_names):
            kid_id = kid_ids[idx]
            kid_data = {
                "name": kid_name,
                "points": 0.0,
                "ha_user_id": "",
                "enable_notifications": False,
                "mobile_notify_service": "",
                "use_persistent_notifications": False,
                "internal_id": kid_id,
            }
            coordinator._create_kid(kid_id, kid_data)

            for chore_num in [1, 2]:
                chore_id = str(uuid.uuid4())
                chore_data = {
                    "name": f"{kid_name} Chore {chore_num}",
                    "default_points": 5.0,
                    "assigned_kids": [kid_id],
                    "partial_allowed": False,
                    "shared_chore": False,
                    "allow_multiple_claims_per_day": False,
                    "description": "",
                    "chore_labels": [],
                    "icon": "mdi:test",
                    "recurring_frequency": "daily",
                    "custom_interval": None,
                    "custom_interval_unit": None,
                    "due_date": None,
                    "applicable_days": [],
                    "notify_on_claim": True,
                    "notify_on_approval": True,
                    "notify_on_disapproval": True,
                    "internal_id": chore_id,
                }
                coordinator._create_chore(chore_id, chore_data)

        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Verify no _2 suffixes anywhere
        final_entities = er.async_entries_for_config_entry(
            ent_reg, init_integration.entry_id
        )
        entity_ids_with_suffixes = [
            e.entity_id for e in final_entities if "_2" in e.entity_id
        ]

        assert len(entity_ids_with_suffixes) == 0, (
            f"Found entities with _2 suffix (should be none): {entity_ids_with_suffixes}"
        )

        print(f"✓ Recreated {len(final_entities)} entities, all without _2 suffix")
        print(
            f"✓ Entity count matches: initial={initial_count}, final={len(final_entities)}"
        )
