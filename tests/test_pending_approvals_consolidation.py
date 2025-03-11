"""Test pending approvals consolidation in dashboard helper sensor.

Tests that pending approvals data is correctly built and included in
dashboard helper sensor attributes with proper button entity ID lookups.
"""

# pylint: disable=redefined-outer-name  # Fixtures reuse names

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores import const


async def test_dashboard_helper_includes_pending_approvals(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test that dashboard helper sensor includes pending_approvals attribute."""
    _, _ = scenario_minimal

    # Get the dashboard helper sensor (Zoë from minimal scenario)
    dashboard_helper = hass.states.get("sensor.kc_zoe_ui_dashboard_helper")
    assert dashboard_helper is not None

    # Check that pending_approvals attribute exists
    assert "pending_approvals" in dashboard_helper.attributes
    pending = dashboard_helper.attributes["pending_approvals"]

    # Should have chores and rewards keys
    assert "chores" in pending
    assert "rewards" in pending
    assert isinstance(pending["chores"], list)
    assert isinstance(pending["rewards"], list)


async def test_pending_approvals_structure(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test pending approvals structure with chore claim."""
    config_entry, _ = scenario_minimal

    # Mock notifications to avoid errors
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Claim a chore to create pending approval (using Zoë from minimal scenario)
        # Use "Wåter the plänts" which is pending (not already claimed like "Feed the cåts")
        await hass.services.async_call(
            const.DOMAIN,
            const.SERVICE_CLAIM_CHORE,
            {const.ATTR_KID_NAME: "Zoë", const.ATTR_CHORE_NAME: "Wåter the plänts"},
            blocking=True,
        )

    # Get updated dashboard helper state (Zoë from minimal scenario)
    dashboard_helper = hass.states.get("sensor.kc_zoe_ui_dashboard_helper")
    assert dashboard_helper is not None
    pending = dashboard_helper.attributes["pending_approvals"]

    # Should have one pending chore approval for Zoë
    assert len(pending["chores"]) == 1
    chore_approval = pending["chores"][0]

    # Verify structure
    assert "chore_id" in chore_approval
    assert "chore_name" in chore_approval
    assert chore_approval["chore_name"] == "Wåter the plänts"
    assert "timestamp" in chore_approval
    assert "approve_button_eid" in chore_approval
    assert "disapprove_button_eid" in chore_approval

    # Button entity IDs should be populated
    assert chore_approval["approve_button_eid"] is not None
    assert chore_approval["disapprove_button_eid"] is not None
    assert chore_approval["approve_button_eid"].startswith("button.kc_zoe_")
    assert "approval" in chore_approval["approve_button_eid"]


async def test_pending_approvals_updated_after_claim(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test that pending approvals list updates when chore is claimed."""
    config_entry, _ = scenario_minimal
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # Initial state - no pending approvals
    dashboard_helper = hass.states.get("sensor.kc_zoe_ui_dashboard_helper")
    assert dashboard_helper is not None
    pending = dashboard_helper.attributes["pending_approvals"]
    initial_count = len(pending["chores"])

    # Mock notifications and claim a chore
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            const.DOMAIN,
            const.SERVICE_CLAIM_CHORE,
            {const.ATTR_KID_NAME: "Zoë", const.ATTR_CHORE_NAME: "Wåter the plänts"},
            blocking=True,
        )

    # Verify pending approvals list was updated
    dashboard_helper = hass.states.get("sensor.kc_zoe_ui_dashboard_helper")
    assert dashboard_helper is not None
    pending = dashboard_helper.attributes["pending_approvals"]
    assert len(pending["chores"]) == initial_count + 1


async def test_pending_approval_cleared_on_approve(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test that pending approval is removed after approval."""
    config_entry, _ = scenario_minimal
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Claim a chore (use unclaimed chore)
        await hass.services.async_call(
            const.DOMAIN,
            const.SERVICE_CLAIM_CHORE,
            {const.ATTR_KID_NAME: "Zoë", const.ATTR_CHORE_NAME: "Wåter the plänts"},
            blocking=True,
        )

        # Verify pending approval exists
        dashboard_helper = hass.states.get("sensor.kc_zoe_ui_dashboard_helper")
        assert dashboard_helper is not None
        pending = dashboard_helper.attributes["pending_approvals"]
        assert len(pending["chores"]) == 1

        # Approve the chore
        await hass.services.async_call(
            const.DOMAIN,
            const.SERVICE_APPROVE_CHORE,
            {
                "parent_name": "Môm Astrid Stârblüm",
                const.ATTR_KID_NAME: "Zoë",
                const.ATTR_CHORE_NAME: "Wåter the plänts",
            },
            blocking=True,
        )

        # Verify pending approval is cleared
        dashboard_helper = hass.states.get("sensor.kc_zoe_ui_dashboard_helper")
        assert dashboard_helper is not None
        pending = dashboard_helper.attributes["pending_approvals"]
        assert len(pending["chores"]) == 0
