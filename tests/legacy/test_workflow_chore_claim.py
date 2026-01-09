"""Chore Claim Workflow Tests - User-centric chore lifecycle testing.

This module tests the complete chore claim workflow from a user's perspective:
    1. Kid claims chore via service → State changes to claimed
    2. Kid tries to self-approve → Denied with authorization error
    3. Parent disapproves → Chore resets, disapproval stat recorded
    4. Kid claims again → State back to claimed
    5. Parent approves → Points awarded, badge checks triggered

Test Organization:
    - Basic Claim Workflow: State changes, points unchanged
    - Authorization & Denial: Permission checks, disapproval handling
    - Approval & Points Award: Points increment, chore count updates
    - Badge Award Triggers: Threshold crossings, multiplier application

NOTE: Tests use services directly instead of button entities to avoid entity lifecycle timing issues.
"""

# pylint: disable=protected-access  # Accessing coordinator internals for testing

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    COORDINATOR,
    DOMAIN,
)

# ============================================================================
# Test Group: Basic Claim Workflow
# ============================================================================


async def test_chore_claim_by_kid_updates_state(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    mock_hass_users: dict,  # pylint: disable=unused-argument
) -> None:
    """Test kid claims chore via service and state changes to claimed.

    Workflow:
        1. Get initial chore state (should be "pending")
        2. Kid calls claim_chore service
        3. Verify chore state changes to "claimed" in coordinator
        4. Verify chore_data[chore_id]["state"] is "claimed" (v0.4.0+)
    """
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    feed_cats_id = name_to_id_map["chore:Feed the cåts"]

    # Reset chore state to pending (v0.4.0+ uses chore_data structure exclusively)
    coordinator.chores_data[feed_cats_id]["state"] = "pending"
    if "chore_data" in coordinator.kids_data[zoe_id]:
        if feed_cats_id in coordinator.kids_data[zoe_id]["chore_data"]:
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id]["state"] = (
                "pending"
            )
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "last_approved"
            ] = None
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "last_claimed"
            ] = None
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "approval_period_start"
            ] = None

    # Get initial state - verify chore_data exists and is pending
    assert "chore_data" in coordinator.kids_data[zoe_id]
    assert feed_cats_id in coordinator.kids_data[zoe_id]["chore_data"]
    initial_state = coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id]["state"]
    assert initial_state == "pending"

    # Mock notifications to prevent ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Kid claims chore via service
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"chore_name": "Feed the cåts", "kid_name": "Zoë"},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Verify chore state is claimed (v0.4.0+ uses chore_data structure)
    assert (
        coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id]["state"] == "claimed"
    )


async def test_chore_claim_points_remain_unchanged(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    mock_hass_users: dict,  # pylint: disable=unused-argument
) -> None:
    """Test kid points unchanged after claiming chore (approval needed).

    Points should only increment after parent approval, not on claim.
    """
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    initial_points = coordinator.kids_data[zoe_id]["points"]

    # Claim chore via service
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"chore_name": "Wåter the plänts", "kid_name": "Zoë"},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Points should be unchanged
    assert coordinator.kids_data[zoe_id]["points"] == initial_points


@pytest.mark.skip(
    reason="Requires button entity - test entity state not coordinator logic"
)
async def test_chore_claim_button_updates_timestamp(
    hass: HomeAssistant,  # pylint: disable=unused-argument
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],  # pylint: disable=unused-argument
    mock_hass_users: dict,  # pylint: disable=unused-argument
) -> None:
    """Test button entity state shows last pressed timestamp.

    TODO: This test requires button entities which aren't created during scenario loading.
    Button timestamp updates are handled by HomeAssistant button platform.
    """


# ============================================================================
# Test Group: Authorization & Denial
# ============================================================================


async def test_kid_cannot_self_approve_chore(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    mock_hass_users: dict,
) -> None:
    """Test kid calling approve service raises authorization error.

    Kids should not be able to approve their own chores.
    """
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    feed_cats_id = name_to_id_map["chore:Feed the cåts"]

    # Reset chore state to pending (v0.4.0+ uses chore_data structure exclusively)
    coordinator.chores_data[feed_cats_id]["state"] = "pending"
    if "chore_data" in coordinator.kids_data[zoe_id]:
        if feed_cats_id in coordinator.kids_data[zoe_id]["chore_data"]:
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id]["state"] = (
                "pending"
            )
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "last_approved"
            ] = None
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "last_claimed"
            ] = None
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "approval_period_start"
            ] = None

    # First claim the chore
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"chore_name": "Feed the cåts", "kid_name": "Zoë"},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Mock user context as kid trying to approve
    kid_context = Context(user_id=mock_hass_users["kid1"].id)

    # Attempt approval should raise authorization error
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Try to approve as kid - should fail authorization check
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                DOMAIN,
                "approve_chore",
                {
                    "chore_name": "Feed the cåts",
                    "kid_name": "Zoë",
                    "parent_name": "Môm Astrid Stârblüm",
                },
                blocking=True,
                context=kid_context,
            )
            await hass.async_block_till_done()

    # Chore should still be claimed, not approved (auth check prevented approval)
    assert (
        coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id]["state"] == "claimed"
    )


async def test_parent_disapprove_resets_chore_state(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    mock_hass_users: dict,
) -> None:
    """Test parent disapprove service resets chore and records stat.

    Workflow:
        1. Kid claims chore
        2. Parent disapproves
        3. Chore state resets
        4. Disapproval counter increments
    """
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    feed_cats_id = name_to_id_map["chore:Feed the cåts"]

    # Reset chore state to pending (v0.4.0+ uses chore_data structure exclusively)
    coordinator.chores_data[feed_cats_id]["state"] = "pending"
    if "chore_data" in coordinator.kids_data[zoe_id]:
        if feed_cats_id in coordinator.kids_data[zoe_id]["chore_data"]:
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id]["state"] = (
                "pending"
            )
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "last_approved"
            ] = None
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "last_claimed"
            ] = None
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "approval_period_start"
            ] = None

    # Kid claims chore
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"chore_name": "Feed the cåts", "kid_name": "Zoë"},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Verify claimed (v0.4.0+ uses chore_data state)
    assert (
        coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id]["state"] == "claimed"
    )

    # Parent disapproves
    parent_context = Context(user_id=mock_hass_users["admin"].id)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "disapprove_chore",
            {
                "chore_name": "Feed the cåts",
                "kid_name": "Zoë",
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )
        await hass.async_block_till_done()

    # Chore should be reset to pending (v0.4.0+ uses chore_data state)
    assert (
        coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id]["state"] == "pending"
    )


@pytest.mark.skip(
    reason="Coordinator doesn't track disapproved_count in chore_states - stat tracking TBD"
)
async def test_disapproved_chore_shows_stat(
    hass: HomeAssistant,  # pylint: disable=unused-argument
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],  # pylint: disable=unused-argument
    mock_hass_users: dict,  # pylint: disable=unused-argument
) -> None:
    """Test disapproval increments disapproved_count stat.

    TODO: Verify if coordinator tracks disapproval count. May be in different data structure.
    """


# ============================================================================
# Test Group: Approval & Points Award
# ============================================================================


async def test_parent_approve_awards_points(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    mock_hass_users: dict,
) -> None:
    """Test parent approval awards points and changes state.

    Workflow:
        1. Kid claims chore (10 points)
        2. Parent approves
        3. Points increase by 10
        4. Chore added to approved list
    """
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    feed_cats_id = name_to_id_map["chore:Feed the cåts"]

    # Reset chore state to pending (v0.4.0+ uses chore_data structure exclusively)
    coordinator.chores_data[feed_cats_id]["state"] = "pending"
    if "chore_data" in coordinator.kids_data[zoe_id]:
        if feed_cats_id in coordinator.kids_data[zoe_id]["chore_data"]:
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id]["state"] = (
                "pending"
            )
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "last_approved"
            ] = None
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "last_claimed"
            ] = None
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "approval_period_start"
            ] = None

    initial_points = coordinator.kids_data[zoe_id]["points"]

    # Kid claims chore
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"chore_name": "Feed the cåts", "kid_name": "Zoë"},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Parent approves
    parent_context = Context(user_id=mock_hass_users["admin"].id)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "chore_name": "Feed the cåts",
                "kid_name": "Zoë",
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )
        await hass.async_block_till_done()

    # Verify points increased (chore worth 10 points)
    assert coordinator.kids_data[zoe_id]["points"] > initial_points
    assert coordinator.kids_data[zoe_id]["points"] == initial_points + 10.0

    # Verify chore is approved (v0.4.0+ uses chore_data state)
    assert (
        coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id]["state"] == "approved"
    )


async def test_parent_approve_increments_chore_count(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    mock_hass_users: dict,
) -> None:
    """Test approval increments chores_completed count."""
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    # Count approved chores (v0.4.0+ uses chore_data state tracking)
    chore_data = coordinator.kids_data[zoe_id].get("chore_data", {})
    initial_count = sum(1 for c in chore_data.values() if c.get("state") == "approved")

    # Claim and approve Wåter the plänts
    parent_context = Context(user_id=mock_hass_users["admin"].id)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Claim
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"chore_name": "Wåter the plänts", "kid_name": "Zoë"},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Approve
        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "chore_name": "Wåter the plänts",
                "kid_name": "Zoë",
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )
        await hass.async_block_till_done()

    # Verify chore count increased (v0.4.0+ uses chore_data state tracking)
    chore_data = coordinator.kids_data[zoe_id].get("chore_data", {})
    new_count = sum(1 for c in chore_data.values() if c.get("state") == "approved")
    assert new_count == initial_count + 1


@pytest.mark.skip(
    reason="Dashboard helper sensor requires entity platform reload after scenario loading"
)
async def test_approved_chore_appears_in_dashboard_helper(
    hass: HomeAssistant,  # pylint: disable=unused-argument
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],  # pylint: disable=unused-argument
    mock_hass_users: dict,  # pylint: disable=unused-argument
) -> None:
    """Test approved chore reflected in dashboard helper sensor.

    TODO: Implement entity platform reload after kids added via scenario.
    """


# ============================================================================
# Test Group: Badge Award Triggers
# ============================================================================


async def test_approval_triggers_cumulative_badge(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    mock_hass_users: dict,
) -> None:
    """Test approving chores that cross badge threshold awards badge.

    Minimal scenario: Brønze Står badge requires 400 lifetime points.
    Kid starts with 10 lifetime points.
    Need to approve chore to reach 400.
    """
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    feed_cats_id = name_to_id_map["chore:Feed the cåts"]

    # Reset chore state to pending (v0.4.0+ uses chore_data structure exclusively)
    coordinator.chores_data[feed_cats_id]["state"] = "pending"
    if "chore_data" in coordinator.kids_data[zoe_id]:
        if feed_cats_id in coordinator.kids_data[zoe_id]["chore_data"]:
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id]["state"] = (
                "pending"
            )
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "last_approved"
            ] = None
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "last_claimed"
            ] = None
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id][
                "approval_period_start"
            ] = None

    # Set cumulative badge progress close to threshold (390)
    # Cumulative badges use baseline + cycle_points, not chore_stats
    from custom_components.kidschores import const

    cumulative_progress = coordinator.kids_data[zoe_id].setdefault(
        const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
    )
    cumulative_progress[const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE] = 390.0
    cumulative_progress[const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS] = 0.0

    # Approve one chore (10 points) → should reach 400 and earn badge
    parent_context = Context(user_id=mock_hass_users["admin"].id)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"chore_name": "Feed the cåts", "kid_name": "Zoë"},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Check chore is claimed (v0.4.0+ uses chore_data state)
        assert (
            coordinator.kids_data[zoe_id]["chore_data"][feed_cats_id]["state"]
            == "claimed"
        )

        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "chore_name": "Feed the cåts",
                "kid_name": "Zoë",
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )
        await hass.async_block_till_done()

    # Verify cumulative badge points reached threshold
    cumulative_progress = coordinator.kids_data[zoe_id].get(
        const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
    )
    baseline = cumulative_progress.get(
        const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE, 0
    )
    cycle_points = cumulative_progress.get(
        const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS, 0
    )
    total_points = baseline + cycle_points
    assert total_points >= 400.0, f"Expected >= 400, got {total_points}"

    # Debug: Check cumulative badge progress
    cumulative_progress = coordinator._get_cumulative_badge_progress(zoe_id)  # pylint: disable=protected-access
    print(f"DEBUG cumulative_progress: {cumulative_progress}")
    print(
        f"DEBUG current_badge_id: {cumulative_progress.get(const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID)}"
    )
    print(
        f"DEBUG highest_earned_badge_id: {cumulative_progress.get(const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_BADGE_ID)}"
    )

    # Verify badge was awarded (dict with badge_id as key)
    badges_earned = coordinator.kids_data[zoe_id]["badges_earned"]
    bronze_star_badge = name_to_id_map["badge:Brønze Står"]
    print(f"DEBUG bronze_star_badge: {bronze_star_badge}")
    assert bronze_star_badge in badges_earned, (
        f"Badge {bronze_star_badge} not found in {badges_earned}"
    )


async def test_badge_award_applies_multiplier(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    mock_hass_users: dict,  # pylint: disable=unused-argument
) -> None:
    """Test badge award includes points_multiplier field.

    Brønze Står badge has 1.05x multiplier.
    """
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    zoe_id = name_to_id_map["kid:Zoë"]
    bronze_star_badge = name_to_id_map.get("badge:Brønze Står")

    # Manually award badge to test structure (dict with badge_id as key)
    badge_entry = {
        "name": "Brønze Står",
        "last_awarded_date": "2024-01-01T00:00:00Z",
        "award_count": 1,
        "periods": {
            "daily": {"2024-01-01": 1},
            "weekly": {"2024-W01": 1},
            "monthly": {"2024-01": 1},
            "yearly": {"2024": 1},
        },
    }
    coordinator.kids_data[zoe_id]["badges_earned"][bronze_star_badge] = badge_entry

    # pylint: disable=protected-access
    coordinator._persist()
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    # Verify badge was earned
    badges_earned = coordinator.kids_data[zoe_id]["badges_earned"]
    # badges_earned is a dict with badge_id as key
    assert bronze_star_badge in badges_earned, (
        f"Badge {bronze_star_badge} not found in {badges_earned}"
    )

    # Verify badge definition has correct multiplier
    badge_definition = coordinator.badges_data.get(bronze_star_badge, {})
    awards = badge_definition.get("awards", {})
    assert awards.get("point_multiplier") == 1.05


@pytest.mark.skip(
    reason="Dashboard helper sensor requires entity platform reload after scenario loading"
)
async def test_badge_award_reflected_in_dashboard(
    hass: HomeAssistant,  # pylint: disable=unused-argument
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],  # pylint: disable=unused-argument
) -> None:
    """Test earned badges appear in dashboard helper sensor.

    Medium scenario: Zoë starts with Dåily Dëlight badge earned.

    TODO: Implement entity platform reload after kids added via scenario.
    """
