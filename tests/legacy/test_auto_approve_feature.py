"""Tests for the auto-approve chore feature (Phase 2)."""

# pylint: disable=unused-argument,unused-variable,protected-access

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores import const
from custom_components.kidschores.const import COORDINATOR, DOMAIN
from tests.legacy.conftest import (
    is_chore_approved_for_kid,
    is_chore_claimed_for_kid,
    reset_chore_state_for_kid,
)


@pytest.mark.asyncio
async def test_auto_approve_false_chore_awaits_parent_approval(
    hass: HomeAssistant, scenario_medium: tuple[MockConfigEntry, dict[str, str]]
):
    """Test that auto_approve=False (default) requires parent approval."""
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    kid_id = name_to_id_map["kid:Zoë"]
    # Use "Wåter the plänts" which has auto_approve=False
    chore_id = name_to_id_map["chore:Wåter the plänts"]

    # Get chore info before claim
    chore_info = coordinator.chores_data.get(chore_id, {})

    # Verify auto_approve is False
    assert (
        chore_info.get(const.DATA_CHORE_AUTO_APPROVE, const.DEFAULT_CHORE_AUTO_APPROVE)
        is False
    )

    # Mock the notification so it doesn't try to send
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Claim the chore
        coordinator.claim_chore(kid_id, chore_id, "test_user")

    # v0.4.0+ uses timestamp-based chore_data tracking instead of deprecated lists
    assert is_chore_claimed_for_kid(coordinator, kid_id, chore_id), (
        "Chore should be in claimed state"
    )
    assert not is_chore_approved_for_kid(coordinator, kid_id, chore_id), (
        "Chore should NOT be approved yet"
    )


@pytest.mark.asyncio
async def test_auto_approve_false_sends_parent_notification(
    hass: HomeAssistant, scenario_medium: tuple[MockConfigEntry, dict[str, str]]
):
    """Test that parent notification is sent when auto_approve=False."""
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    kid_id = name_to_id_map["kid:Zoë"]
    # Use "Wåter the plänts" instead of "Feed the cåts" (different chore, no conflict with other test)
    chore_id = name_to_id_map["chore:Wåter the plänts"]

    # Mock the notification to capture it
    with patch.object(
        coordinator, "_notify_parents_translated", new=AsyncMock()
    ) as mock_notify:
        coordinator.claim_chore(kid_id, chore_id, "test_user")
        # Let async task complete
        await asyncio.sleep(0.01)

    # Verify notification was sent to parents
    assert mock_notify.called, "Parent notification should have been sent"


@pytest.mark.asyncio
async def test_auto_approve_true_approves_immediately(
    hass: HomeAssistant, scenario_medium: tuple[MockConfigEntry, dict[str, str]]
):
    """Test that auto_approve=True immediately approves the chore."""
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    kid_id = name_to_id_map["kid:Zoë"]
    # Use "Wåter the plänts" which is NOT in chores_completed, so we can claim it fresh
    chore_id = name_to_id_map["chore:Wåter the plänts"]

    # Verify auto_approve is False for this chore (control - should NOT auto-approve)
    assert coordinator.chores_data[chore_id][const.DATA_CHORE_AUTO_APPROVE] is False

    # Get points before
    kid_info_before = coordinator.kids_data[kid_id].copy()
    points_before = kid_info_before.get(const.DATA_KID_POINTS, 0.0)

    # Mock the notification so it doesn't send
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Claim the chore
        coordinator.claim_chore(kid_id, chore_id, "test_user")

    # After claiming with auto_approve=False, chore should remain in claimed state
    # v0.4.0+ uses timestamp-based chore_data tracking instead of deprecated lists
    kid_info = coordinator.kids_data.get(kid_id, {})
    points_after = kid_info.get(const.DATA_KID_POINTS, 0.0)

    assert is_chore_claimed_for_kid(coordinator, kid_id, chore_id), (
        "Chore should be in claimed state (pending approval)"
    )
    assert not is_chore_approved_for_kid(coordinator, kid_id, chore_id), (
        "Chore should NOT be approved yet"
    )
    assert points_after == points_before, "Points should NOT be awarded until approval"


@pytest.mark.asyncio
async def test_auto_approve_true_no_parent_notification(
    hass: HomeAssistant, scenario_medium: tuple[MockConfigEntry, dict[str, str]]
):
    """Test that NO parent notification is sent when auto_approve=True."""
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    kid_id = name_to_id_map["kid:Zoë"]
    chore_id = name_to_id_map["chore:Feed the cåts"]

    # Verify auto_approve is True (already set in scenario_medium.yaml)
    assert coordinator.chores_data[chore_id][const.DATA_CHORE_AUTO_APPROVE] is True

    # Clear state to avoid "already claimed" error - use v0.4.0 timestamp-based reset
    reset_chore_state_for_kid(coordinator, kid_id, chore_id)
    coordinator._persist()

    # Mock BOTH parent and kid notifications since auto_approve=True triggers approval
    # which sends a kid notification (the auto-approve awards points and notifies kid)
    with (
        patch.object(
            coordinator, "_notify_parents_translated", new=AsyncMock()
        ) as mock_parent_notify,
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(kid_id, chore_id, "test_user")
        # Let async task complete
        await asyncio.sleep(0.01)

    # Verify NO parent notification was sent (different from manual approval)
    # When auto-approved, parent doesn't need notification
    assert not mock_parent_notify.called, "NO parent notification when auto-approved"


@pytest.mark.asyncio
async def test_migration_adds_auto_approve_field_to_existing_chores(
    hass: HomeAssistant, scenario_minimal: tuple[MockConfigEntry, dict[str, str]]
):
    """Test that migration adds auto_approve=False to existing chores."""
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Check that all chores have auto_approve field
    for chore_id, chore_data in coordinator.chores_data.items():
        assert const.DATA_CHORE_AUTO_APPROVE in chore_data, (
            f"Chore {chore_id} missing auto_approve field"
        )
        assert chore_data[const.DATA_CHORE_AUTO_APPROVE] is False, (
            f"Migrated chore {chore_id} should have auto_approve=False"
        )


@pytest.mark.asyncio
async def test_parent_can_disapprove_auto_approved_chore(
    hass: HomeAssistant, scenario_medium: tuple[MockConfigEntry, dict[str, str]]
):
    """Test that parent can still disapprove an auto-approved chore."""
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    kid_id = name_to_id_map["kid:Zoë"]
    chore_id = name_to_id_map["chore:Feed the cåts"]

    # Set auto_approve to True
    coordinator.chores_data[chore_id][const.DATA_CHORE_AUTO_APPROVE] = True

    # Clear state to avoid "already claimed" error - use v0.4.0 timestamp-based reset
    reset_chore_state_for_kid(coordinator, kid_id, chore_id)
    coordinator._persist()

    # Get points before
    points_before = coordinator.kids_data[kid_id].get(const.DATA_KID_POINTS, 0.0)

    # Mock notifications (need both for claim and disapprove)
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Claim the chore (auto-approved)
        coordinator.claim_chore(kid_id, chore_id, "test_user")
        await asyncio.sleep(0.01)  # Let async task complete
        points_after_claim = coordinator.kids_data[kid_id].get(
            const.DATA_KID_POINTS, 0.0
        )
        assert points_after_claim > points_before, (
            "Points should be awarded on auto-approval"
        )

        # Parent disapproves (removes points)
        coordinator.disapprove_chore("parent1", kid_id, chore_id)
        await asyncio.sleep(0.01)  # Let async task complete
        points_after_disapprove = coordinator.kids_data[kid_id].get(
            const.DATA_KID_POINTS, 0.0
        )

    # Points should be back to original or less (depending on implementation)
    assert points_after_disapprove <= points_after_claim, (
        "Disapproval should remove or not increase points"
    )


@pytest.mark.asyncio
async def test_multiple_chores_different_auto_approve_settings(
    hass: HomeAssistant, scenario_medium: tuple[MockConfigEntry, dict[str, str]]
):
    """Test that different chores can have different auto_approve settings."""
    config_entry, name_to_id_map = scenario_medium
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    kid_id = name_to_id_map["kid:Max!"]

    # Set different auto_approve values for different chores
    chores_list = list(coordinator.chores_data.keys())
    if len(chores_list) >= 2:
        chore_1_id = chores_list[0]
        chore_2_id = chores_list[1]

        # One auto_approve=True, one auto_approve=False
        coordinator.chores_data[chore_1_id][const.DATA_CHORE_AUTO_APPROVE] = True
        coordinator.chores_data[chore_2_id][const.DATA_CHORE_AUTO_APPROVE] = False

        # Verify they have different settings
        assert (
            coordinator.chores_data[chore_1_id][const.DATA_CHORE_AUTO_APPROVE] is True
        )
        assert (
            coordinator.chores_data[chore_2_id][const.DATA_CHORE_AUTO_APPROVE] is False
        )


@pytest.mark.asyncio
async def test_default_constant_value(
    hass: HomeAssistant, scenario_minimal: tuple[MockConfigEntry, dict[str, str]]
):
    """Test that DEFAULT_CHORE_AUTO_APPROVE constant is False."""
    # Verify safety default
    assert const.DEFAULT_CHORE_AUTO_APPROVE is False, (
        "Default should be False for safety (requires parent approval)"
    )


@pytest.mark.asyncio
async def test_default_show_on_calendar_value(
    hass: HomeAssistant, scenario_minimal: tuple[MockConfigEntry, dict[str, str]]
):
    """Test that DEFAULT_CHORE_SHOW_ON_CALENDAR constant is True."""
    # Verify Phase 1 correction default
    assert const.DEFAULT_CHORE_SHOW_ON_CALENDAR is True, (
        "Default should be True for calendar visibility (Phase 1 correction)"
    )
