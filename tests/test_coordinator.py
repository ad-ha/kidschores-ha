"""Tests for KidsChores coordinator."""

import uuid
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores import const
from custom_components.kidschores.const import (
    CHORE_STATE_APPROVED,
    CHORE_STATE_CLAIMED,
    CHORE_STATE_PENDING,
    COORDINATOR,
    DOMAIN,
)

from .conftest import create_mock_chore_data, create_mock_kid_data


async def test_chore_lifecycle_complete_workflow(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test complete chore lifecycle: create, claim, approve, verify persistence."""
    # Get the coordinator
    coordinator = hass.data[DOMAIN][init_integration.entry_id][COORDINATOR]

    # Mock notifications to prevent ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Create a kid
        kid_id = str(uuid.uuid4())
        kid_name = "Test Kid"
        kid_data = create_mock_kid_data(name=kid_name, points=0.0)
        kid_data["internal_id"] = kid_id
        # pylint: disable=protected-access
        coordinator._create_kid(kid_id, kid_data)

        # Create a chore assigned to the kid (pass kid ID, not name)
        chore_id = str(uuid.uuid4())
        chore_data = create_mock_chore_data(
            name="Feed the cåts",
            default_points=int(5.0),
            assigned_kids=[kid_id],  # Pass UUID, not name
        )
        chore_data["internal_id"] = chore_id
        coordinator._create_chore(chore_id, chore_data)
        # pylint: enable=protected-access

        # Verify initial state
        assert coordinator.chores_data[chore_id]["state"] == CHORE_STATE_PENDING
        assert coordinator.kids_data[kid_id]["points"] == 0.0

        # Kid claims the chore
        coordinator.claim_chore(kid_id, chore_id, "Test User")

        # Verify claimed state - chore in kid's chore_data with claimed state
        assert coordinator.chores_data[chore_id]["state"] == CHORE_STATE_CLAIMED
        assert (
            coordinator.kids_data[kid_id]["chore_data"][chore_id]["state"]
            == CHORE_STATE_CLAIMED
        )

        # Approve the chore
        coordinator.approve_chore("Test User", kid_id, chore_id)

        # Verify approved state - chore in kid's chore_data with approved state
        assert coordinator.chores_data[chore_id]["state"] == CHORE_STATE_APPROVED
        assert (
            coordinator.kids_data[kid_id]["chore_data"][chore_id]["state"]
            == CHORE_STATE_APPROVED
        )
        assert coordinator.kids_data[kid_id]["points"] == 5.0


async def test_points_management_flow(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test comprehensive point management: chores, bonuses, penalties."""
    coordinator = hass.data[DOMAIN][init_integration.entry_id][COORDINATOR]

    # Mock notifications to prevent ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Create a kid
        kid_id = str(uuid.uuid4())
        kid_name = "Max! Stårblüm"
        kid_data = create_mock_kid_data(name=kid_name, points=0.0)
        kid_data["internal_id"] = kid_id
        # pylint: disable=protected-access
        coordinator._create_kid(kid_id, kid_data)

        # Create and approve a chore for points
        chore_id = str(uuid.uuid4())
        chore_data = create_mock_chore_data(
            name="Pick up Lëgo!",
            default_points=int(8.0),
            assigned_kids=[kid_id],  # Pass UUID, not name
        )
        chore_data["internal_id"] = chore_id
        coordinator._create_chore(chore_id, chore_data)
        # pylint: enable=protected-access
        coordinator.claim_chore(kid_id, chore_id, "Test User")
        coordinator.approve_chore("Test User", kid_id, chore_id)

        # Verify points from chore
        assert coordinator.kids_data[kid_id]["points"] == 8.0

        # Apply a penalty
        penalty_id = str(uuid.uuid4())
        penalty_data = {
            "internal_id": penalty_id,
            "name": "Førget Chöre",
            "points": -5.0,
            "assigned_kids": [kid_id],
        }
        # pylint: disable=protected-access
        coordinator._data["penalties"] = {penalty_id: penalty_data}
        # pylint: enable=protected-access
        coordinator.apply_penalty("Test User", kid_id, penalty_id)

        # Verify points after penalty (8 - 5 = 3)
        assert coordinator.kids_data[kid_id]["points"] == 3.0

        # Apply a bonus
        bonus_id = str(uuid.uuid4())
        bonus_data = {
            "internal_id": bonus_id,
            "name": "Stär Sprïnkle Bonus",
            "points": 15.0,
            "assigned_kids": [kid_id],
        }
        # pylint: disable=protected-access
        coordinator._data["bonuses"] = {bonus_id: bonus_data}
        # pylint: enable=protected-access
        coordinator.apply_bonus("Test User", kid_id, bonus_id)

        # Verify final points (3 + 15 = 18)
        assert coordinator.kids_data[kid_id]["points"] == 18.0


async def test_reward_approval_workflow(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test reward redemption with approval and disapproval workflows."""
    coordinator = hass.data[DOMAIN][init_integration.entry_id][COORDINATOR]

    # Mock notifications to prevent ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Create a kid with points
        kid_id = str(uuid.uuid4())
        kid_data = create_mock_kid_data(name="Lila Stårblüm", points=100.0)
        kid_data["internal_id"] = kid_id
        # pylint: disable=protected-access
        coordinator._create_kid(kid_id, kid_data)

        # Create a reward
        reward_id = str(uuid.uuid4())
        reward_data = {
            "internal_id": reward_id,
            "name": "Ice Créam!",
            "cost": 50.0,
            "assigned_kids": [kid_id],
        }
        coordinator._data["rewards"] = {reward_id: reward_data}
        # pylint: enable=protected-access

        # Redeem reward (adds to pending, doesn't deduct yet)
        coordinator.redeem_reward("Test User", kid_id, reward_id)

        # Verify points NOT yet deducted (still pending approval)
        assert coordinator.kids_data[kid_id]["points"] == 100.0

        # Approve reward (NOW deducts points)
        coordinator.approve_reward("Test User", kid_id, reward_id)

        # Verify points deducted after approval
        assert coordinator.kids_data[kid_id]["points"] == 50.0

        # Test disapproval workflow - redeem another reward
        coordinator.redeem_reward("Test User", kid_id, reward_id)
        assert (
            coordinator.kids_data[kid_id]["points"] == 50.0
        )  # Still 50, no deduction yet

        # Disapprove reward (removes from pending, no refund since nothing was deducted)
        coordinator.disapprove_reward("Test User", kid_id, reward_id)

        # Verify points unchanged (nothing was deducted in the first place)
        assert coordinator.kids_data[kid_id]["points"] == 50.0


async def test_kid_device_name_updates_immediately(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that kid device name updates immediately when changed via coordinator."""
    from homeassistant.helpers import device_registry as dr

    # Get the coordinator
    coordinator = hass.data[DOMAIN][init_integration.entry_id][COORDINATOR]

    # Add a kid to coordinator
    kid_id = str(uuid.uuid4())
    kid_data = create_mock_kid_data(name="Zoe", points=0.0)
    kid_data["internal_id"] = kid_id
    # pylint: disable=protected-access
    coordinator._create_kid(kid_id, kid_data)
    # pylint: enable=protected-access

    # Manually create the device (simulates what entities do during setup)
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=init_integration.entry_id,
        identifiers={(DOMAIN, kid_id)},
        name="Zoe (KidsChores)",
        manufacturer="KidsChores",
        model="Kid Profile",
    )

    # Verify device exists with initial name
    assert device is not None, "Kid device should exist in registry"
    initial_device_name = device.name
    assert "Zoe" in initial_device_name, (
        f"Device name should contain 'Zoe', got: {initial_device_name}"
    )

    # Update kid name via coordinator
    updated_kid_data = {
        const.DATA_KID_NAME: "Sarah",
        const.DATA_KID_HA_USER_ID: None,
    }
    coordinator.update_kid_entity(kid_id, updated_kid_data)
    await hass.async_block_till_done()

    # Verify device name updated immediately (without reload/reboot)
    device = device_registry.async_get_device(identifiers={(DOMAIN, kid_id)})
    updated_device_name = device.name

    assert "Sarah" in updated_device_name, (
        f"Device name should contain 'Sarah', got: {updated_device_name}"
    )
    assert "Zoe" not in updated_device_name, (
        f"Device name should not contain old name 'Zoe', got: {updated_device_name}"
    )


async def test_config_entry_title_updates_device_names(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that changing config entry title updates all kid device names."""
    from homeassistant.helpers import device_registry as dr

    # Get the coordinator
    coordinator = hass.data[DOMAIN][init_integration.entry_id][COORDINATOR]

    # Add two kids to coordinator
    kid1_id = str(uuid.uuid4())
    kid1_data = create_mock_kid_data(name="Alice", points=0.0)
    kid1_data["internal_id"] = kid1_id
    kid2_id = str(uuid.uuid4())
    kid2_data = create_mock_kid_data(name="Bob", points=0.0)
    kid2_data["internal_id"] = kid2_id
    # pylint: disable=protected-access
    coordinator._create_kid(kid1_id, kid1_data)
    coordinator._create_kid(kid2_id, kid2_data)
    # pylint: enable=protected-access

    # Manually create devices (simulates what entities do during setup)
    device_registry = dr.async_get(hass)
    device1 = device_registry.async_get_or_create(
        config_entry_id=init_integration.entry_id,
        identifiers={(DOMAIN, kid1_id)},
        name="Alice (KidsChores)",
        manufacturer="KidsChores",
        model="Kid Profile",
    )
    device2 = device_registry.async_get_or_create(
        config_entry_id=init_integration.entry_id,
        identifiers={(DOMAIN, kid2_id)},
        name="Bob (KidsChores)",
        manufacturer="KidsChores",
        model="Kid Profile",
    )

    # Verify initial device names
    assert "Alice (KidsChores)" in device1.name
    assert "Bob (KidsChores)" in device2.name

    # Change config entry title
    hass.config_entries.async_update_entry(init_integration, title="Family Chores")

    # Trigger update listener by calling async_update_options
    from custom_components.kidschores import async_update_options

    await async_update_options(hass, init_integration)
    await hass.async_block_till_done()

    # Verify device names updated with new title
    device1 = device_registry.async_get_device(identifiers={(DOMAIN, kid1_id)})
    device2 = device_registry.async_get_device(identifiers={(DOMAIN, kid2_id)})

    assert "Alice (Family Chores)" == device1.name, (
        f"Device 1 name should be 'Alice (Family Chores)', got: {device1.name}"
    )
    assert "Bob (Family Chores)" == device2.name, (
        f"Device 2 name should be 'Bob (Family Chores)', got: {device2.name}"
    )
    assert "KidsChores" not in device1.name, "Old title should not be in device1 name"
    assert "KidsChores" not in device2.name, "Old title should not be in device2 name"
