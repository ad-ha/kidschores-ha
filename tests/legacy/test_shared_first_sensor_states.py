"""Test SHARED_FIRST sensor states after claiming.

Validates that when a kid claims a SHARED_FIRST chore:
1. Global chore state sensor shows "claimed" (not "overdue")
2. Claiming kid's chore status sensor shows "claimed"
3. Other kids' chore status sensors show "completed_by_other" (not "pending")

This catches the bug where the sensor's native_value wasn't checking for
the completed_by_other state, causing non-claiming kids to show "pending".
"""

# pylint: disable=protected-access
# pylint: disable=redefined-outer-name

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from custom_components.kidschores import const
from tests.legacy.conftest import (
    create_test_datetime,
    reload_entity_platforms,
)


@pytest.mark.asyncio
async def test_shared_first_claim_updates_all_sensors(
    hass: HomeAssistant, scenario_full: tuple, mock_hass_users: dict
) -> None:
    """Test that claiming a SHARED_FIRST chore updates all sensor states correctly.

    Scenario: SHARED_FIRST chore is overdue, Zoë claims it.
    Expected:
      - Global sensor: "claimed" (not "overdue")
      - Zoë's sensor: "claimed"
      - Max!'s sensor: "completed_by_other" (not "pending")
      - Lila's sensor: "completed_by_other" (not "pending")
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # Get kids using name_to_id_map
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    # Get SHARED_FIRST chore: "Täke Öut Trash" (assigned to all 3 kids)
    chore_id = name_to_id_map["chore:Täke Öut Trash"]
    chore_name = coordinator.chores_data[chore_id][const.DATA_CHORE_NAME]

    # Set chore due date to yesterday (overdue)
    yesterday = create_test_datetime(days_offset=-1)
    coordinator._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_DUE_DATE] = (
        yesterday
    )

    # Build entity IDs
    # Global state sensor: sensor.kc_global_chore_status_take_out_trash
    chore_slug = slugify(chore_name)
    global_entity_id = f"sensor.kc_global_chore_status_{chore_slug}"

    # Kid chore status sensors
    zoe_entity_id = f"sensor.kc_{slugify('Zoë')}_chore_status_{chore_slug}"
    max_entity_id = f"sensor.kc_{slugify('Max!')}_chore_status_{chore_slug}"
    lila_entity_id = f"sensor.kc_{slugify('Lila')}_chore_status_{chore_slug}"

    # Reload entities to ensure all sensors exist
    await reload_entity_platforms(hass, config_entry)

    # Mock notifications during testing
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        with patch.object(coordinator, "_notify_overdue_chore", new=MagicMock()):
            # First check the overdue state before claiming
            await coordinator._check_overdue_chores()
            await hass.async_block_till_done()

            # Reload to pick up state changes
            coordinator.async_update_listeners()
            await hass.async_block_till_done()

            # Verify global state is overdue before claiming
            global_state = hass.states.get(global_entity_id)
            if global_state:
                assert global_state.state == const.CHORE_STATE_OVERDUE, (
                    f"Global state should be overdue before claim, got: {global_state.state}"
                )

            # Zoë claims the chore
            coordinator.claim_chore(zoe_id, chore_id, mock_hass_users["kid1"].id)
            coordinator.async_update_listeners()
            await hass.async_block_till_done()

            # Verify coordinator data directly first (sanity check)
            chore_info = coordinator.chores_data[chore_id]
            _zoe_info = coordinator.kids_data[zoe_id]  # noqa: F841
            max_info = coordinator.kids_data[max_id]
            lila_info = coordinator.kids_data[lila_id]

            # Verify global chore state in coordinator data
            assert chore_info[const.DATA_CHORE_STATE] == const.CHORE_STATE_CLAIMED, (
                f"Global chore state should be 'claimed', got: {chore_info[const.DATA_CHORE_STATE]}"
            )

            # Verify other kids are in completed_by_other list
            assert chore_id in max_info.get(
                const.DATA_KID_COMPLETED_BY_OTHER_CHORES, []
            ), "Max! should be in completed_by_other list"
            assert chore_id in lila_info.get(
                const.DATA_KID_COMPLETED_BY_OTHER_CHORES, []
            ), "Lila should be in completed_by_other list"

            # Now verify the SENSOR states
            # Global sensor
            global_state = hass.states.get(global_entity_id)
            assert global_state is not None, (
                f"Global sensor {global_entity_id} not found"
            )
            assert global_state.state == const.CHORE_STATE_CLAIMED, (
                f"Global sensor state should be 'claimed', got: {global_state.state}"
            )

            # Zoë's sensor
            zoe_state = hass.states.get(zoe_entity_id)
            assert zoe_state is not None, f"Zoë's sensor {zoe_entity_id} not found"
            assert zoe_state.state == const.CHORE_STATE_CLAIMED, (
                f"Zoë's sensor state should be 'claimed', got: {zoe_state.state}"
            )

            # Max!'s sensor - this should be completed_by_other, NOT pending
            max_state = hass.states.get(max_entity_id)
            assert max_state is not None, f"Max!'s sensor {max_entity_id} not found"
            assert max_state.state == const.CHORE_STATE_COMPLETED_BY_OTHER, (
                f"Max!'s sensor state should be 'completed_by_other', got: {max_state.state}"
            )

            # Lila's sensor - this should be completed_by_other, NOT pending
            lila_state = hass.states.get(lila_entity_id)
            assert lila_state is not None, f"Lila's sensor {lila_entity_id} not found"
            assert lila_state.state == const.CHORE_STATE_COMPLETED_BY_OTHER, (
                f"Lila's sensor state should be 'completed_by_other', got: {lila_state.state}"
            )


@pytest.mark.asyncio
async def test_shared_first_approval_updates_all_sensors(
    hass: HomeAssistant, scenario_full: tuple, mock_hass_users: dict
) -> None:
    """Test that approving a SHARED_FIRST chore updates all sensor states.

    Scenario: SHARED_FIRST chore claimed by Zoë, then approved.
    Expected:
      - Global sensor: "approved"
      - Zoë's sensor: "approved"
      - Max!'s sensor: "completed_by_other"
      - Lila's sensor: "completed_by_other"
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # Get kids
    zoe_id = name_to_id_map["kid:Zoë"]
    _max_id = name_to_id_map["kid:Max!"]  # noqa: F841
    _lila_id = name_to_id_map["kid:Lila"]  # noqa: F841

    # Get SHARED_FIRST chore
    chore_id = name_to_id_map["chore:Täke Öut Trash"]
    chore_name = coordinator.chores_data[chore_id][const.DATA_CHORE_NAME]

    # Build entity IDs
    chore_slug = slugify(chore_name)
    global_entity_id = f"sensor.kc_global_chore_status_{chore_slug}"
    zoe_entity_id = f"sensor.kc_{slugify('Zoë')}_chore_status_{chore_slug}"
    max_entity_id = f"sensor.kc_{slugify('Max!')}_chore_status_{chore_slug}"
    lila_entity_id = f"sensor.kc_{slugify('Lila')}_chore_status_{chore_slug}"

    # Reload entities
    await reload_entity_platforms(hass, config_entry)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Zoë claims then gets approved
        coordinator.claim_chore(zoe_id, chore_id, mock_hass_users["kid1"].id)
        coordinator.approve_chore(mock_hass_users["parent1"].id, zoe_id, chore_id)
        coordinator.async_update_listeners()
        await hass.async_block_till_done()

        # Verify sensor states
        global_state = hass.states.get(global_entity_id)
        assert global_state is not None, f"Global sensor {global_entity_id} not found"
        assert global_state.state == const.CHORE_STATE_APPROVED, (
            f"Global sensor should be 'approved', got: {global_state.state}"
        )

        zoe_state = hass.states.get(zoe_entity_id)
        assert zoe_state is not None, f"Zoë's sensor {zoe_entity_id} not found"
        assert zoe_state.state == const.CHORE_STATE_APPROVED, (
            f"Zoë's sensor should be 'approved', got: {zoe_state.state}"
        )

        max_state = hass.states.get(max_entity_id)
        assert max_state is not None, f"Max!'s sensor {max_entity_id} not found"
        assert max_state.state == const.CHORE_STATE_COMPLETED_BY_OTHER, (
            f"Max!'s sensor should be 'completed_by_other', got: {max_state.state}"
        )

        lila_state = hass.states.get(lila_entity_id)
        assert lila_state is not None, f"Lila's sensor {lila_entity_id} not found"
        assert lila_state.state == const.CHORE_STATE_COMPLETED_BY_OTHER, (
            f"Lila's sensor should be 'completed_by_other', got: {lila_state.state}"
        )


@pytest.mark.asyncio
async def test_shared_first_disapproval_resets_sensors(
    hass: HomeAssistant, scenario_full: tuple, mock_hass_users: dict
) -> None:
    """Test that disapproving a SHARED_FIRST chore resets all sensors.

    Scenario: SHARED_FIRST chore claimed by Zoë, then disapproved.
    Expected: All sensors return to "pending" state.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # Get kids
    zoe_id = name_to_id_map["kid:Zoë"]
    _max_id = name_to_id_map["kid:Max!"]  # noqa: F841

    # Get SHARED_FIRST chore
    chore_id = name_to_id_map["chore:Täke Öut Trash"]
    chore_name = coordinator.chores_data[chore_id][const.DATA_CHORE_NAME]

    # Build entity IDs
    chore_slug = slugify(chore_name)
    global_entity_id = f"sensor.kc_global_chore_status_{chore_slug}"
    zoe_entity_id = f"sensor.kc_{slugify('Zoë')}_chore_status_{chore_slug}"
    max_entity_id = f"sensor.kc_{slugify('Max!')}_chore_status_{chore_slug}"

    # Reload entities
    await reload_entity_platforms(hass, config_entry)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Zoë claims
        coordinator.claim_chore(zoe_id, chore_id, mock_hass_users["kid1"].id)
        coordinator.async_update_listeners()
        await hass.async_block_till_done()

        # Verify claimed state first
        max_state = hass.states.get(max_entity_id)
        assert max_state.state == const.CHORE_STATE_COMPLETED_BY_OTHER

        # Disapprove
        coordinator.disapprove_chore(mock_hass_users["parent1"].id, zoe_id, chore_id)
        coordinator.async_update_listeners()
        await hass.async_block_till_done()

        # All should be back to pending
        global_state = hass.states.get(global_entity_id)
        assert global_state.state == const.CHORE_STATE_PENDING, (
            f"Global sensor should be 'pending' after disapproval, got: {global_state.state}"
        )

        zoe_state = hass.states.get(zoe_entity_id)
        assert zoe_state.state == const.CHORE_STATE_PENDING, (
            f"Zoë's sensor should be 'pending' after disapproval, got: {zoe_state.state}"
        )

        max_state = hass.states.get(max_entity_id)
        assert max_state.state == const.CHORE_STATE_PENDING, (
            f"Max!'s sensor should be 'pending' after disapproval, got: {max_state.state}"
        )
