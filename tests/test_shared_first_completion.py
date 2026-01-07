"""Test SHARED_FIRST completion criteria for chores.

Tests the "first kid to claim wins" behavior where:
1. First kid to claim gets points on approval
2. Second kid's claim is blocked with error
3. Non-claimant kids get 'completed_by_other' state
4. Disapproval resets ALL kids to pending state
5. Global state tracks SHARED_FIRST correctly
"""

# pylint: disable=protected-access
# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.kidschores import const
from custom_components.kidschores.const import (
    CHORE_STATE_APPROVED,
    CHORE_STATE_CLAIMED,
    COMPLETION_CRITERIA_SHARED_FIRST,
    COORDINATOR,
    DATA_CHORE_COMPLETION_CRITERIA,
    DATA_CHORE_NAME,
    DATA_CHORE_STATE,
    DATA_KID_COMPLETED_BY_OTHER_CHORES,
    DATA_KID_POINTS,
    DOMAIN,
)
from tests.conftest import (
    is_chore_approved_for_kid,
    is_chore_claimed_for_kid,
)


def get_shared_first_chore(
    coordinator: Any, kid_name_to_id: dict[str, str]
) -> tuple[str, list[str]] | None:
    """Find a SHARED_FIRST chore and its assigned kids.

    Args:
        coordinator: The KidsChores coordinator
        kid_name_to_id: Map of "kid:Name" to kid internal_id

    Returns:
        Tuple of (chore_id, list of assigned kid_ids) or None if not found
    """
    for chore_id, chore_info in coordinator.chores_data.items():
        if (
            chore_info.get(DATA_CHORE_COMPLETION_CRITERIA)
            == COMPLETION_CRITERIA_SHARED_FIRST
        ):
            assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
            if len(assigned_kids) >= 2:
                return chore_id, assigned_kids
    return None


@pytest.mark.asyncio
async def test_shared_first_first_kid_can_claim(
    hass: HomeAssistant, scenario_full: tuple, mock_hass_users: dict
) -> None:
    """Test that the first kid can successfully claim a SHARED_FIRST chore."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Find SHARED_FIRST chore
    result = get_shared_first_chore(coordinator, name_to_id_map)
    if not result:
        pytest.skip("No SHARED_FIRST chores with 2+ kids in scenario_full")

    chore_id, assigned_kids = result
    first_kid_id = assigned_kids[0]
    chore_name = coordinator.chores_data[chore_id][DATA_CHORE_NAME]

    # Get kid name for service call
    first_kid_name = coordinator.kids_data[first_kid_id][const.DATA_KID_NAME]

    # Mock notifications
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # First kid claims chore - should succeed
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {
                "kid_name": first_kid_name,
                "chore_name": chore_name,
            },
            blocking=True,
        )

    # Verify first kid has chore in claimed state
    assert is_chore_claimed_for_kid(coordinator, first_kid_id, chore_id), (
        "First kid should have chore in claimed state"
    )


@pytest.mark.asyncio
async def test_shared_first_second_kid_claim_blocked(
    hass: HomeAssistant, scenario_full: tuple, mock_hass_users: dict
) -> None:
    """Test that second kid's claim is blocked when first kid already claimed."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Find SHARED_FIRST chore
    result = get_shared_first_chore(coordinator, name_to_id_map)
    if not result:
        pytest.skip("No SHARED_FIRST chores with 2+ kids in scenario_full")

    chore_id, assigned_kids = result
    first_kid_id = assigned_kids[0]
    second_kid_id = assigned_kids[1]
    chore_name = coordinator.chores_data[chore_id][DATA_CHORE_NAME]

    first_kid_name = coordinator.kids_data[first_kid_id][const.DATA_KID_NAME]
    second_kid_name = coordinator.kids_data[second_kid_id][const.DATA_KID_NAME]

    # Mock notifications
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # First kid claims
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"kid_name": first_kid_name, "chore_name": chore_name},
            blocking=True,
        )

        # Second kid tries to claim - should be blocked
        with pytest.raises(HomeAssistantError) as exc_info:
            await hass.services.async_call(
                DOMAIN,
                "claim_chore",
                {"kid_name": second_kid_name, "chore_name": chore_name},
                blocking=True,
            )

    # Verify error message mentions the chore is already claimed
    assert (
        "already claimed" in str(exc_info.value).lower()
        or "claimed" in str(exc_info.value).lower()
    ), f"Error should mention chore is already claimed, got: {exc_info.value}"

    # Verify second kid does NOT have chore in claimed state
    assert not is_chore_claimed_for_kid(coordinator, second_kid_id, chore_id), (
        "Second kid should NOT have chore in claimed state"
    )


@pytest.mark.asyncio
async def test_shared_first_approval_only_awards_first_kid(
    hass: HomeAssistant, scenario_full: tuple, mock_hass_users: dict
) -> None:
    """Test that only the first kid gets points when SHARED_FIRST chore approved."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Find SHARED_FIRST chore
    result = get_shared_first_chore(coordinator, name_to_id_map)
    if not result:
        pytest.skip("No SHARED_FIRST chores with 2+ kids in scenario_full")

    chore_id, assigned_kids = result
    first_kid_id = assigned_kids[0]
    second_kid_id = assigned_kids[1]
    chore_name = coordinator.chores_data[chore_id][DATA_CHORE_NAME]

    first_kid_name = coordinator.kids_data[first_kid_id][const.DATA_KID_NAME]

    # Record initial points
    first_kid_initial_points = coordinator.kids_data[first_kid_id].get(
        DATA_KID_POINTS, 0
    )
    second_kid_initial_points = coordinator.kids_data[second_kid_id].get(
        DATA_KID_POINTS, 0
    )

    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # First kid claims
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"kid_name": first_kid_name, "chore_name": chore_name},
            blocking=True,
        )

        # Parent approves
        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": first_kid_name,
                "chore_name": chore_name,
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # Verify first kid got points
    first_kid_final_points = coordinator.kids_data[first_kid_id].get(DATA_KID_POINTS, 0)
    assert first_kid_final_points > first_kid_initial_points, (
        f"First kid should have gained points: {first_kid_initial_points} -> {first_kid_final_points}"
    )

    # Verify second kid did NOT get points
    second_kid_final_points = coordinator.kids_data[second_kid_id].get(
        DATA_KID_POINTS, 0
    )
    assert second_kid_final_points == second_kid_initial_points, (
        f"Second kid should NOT have gained points: {second_kid_initial_points} -> {second_kid_final_points}"
    )


@pytest.mark.asyncio
async def test_shared_first_other_kids_get_completed_by_other_state(
    hass: HomeAssistant, scenario_full: tuple, mock_hass_users: dict
) -> None:
    """Test that non-claimant kids get completed_by_other state after approval."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Find SHARED_FIRST chore with at least 2 kids
    result = get_shared_first_chore(coordinator, name_to_id_map)
    if not result:
        pytest.skip("No SHARED_FIRST chores with 2+ kids in scenario_full")

    chore_id, assigned_kids = result
    first_kid_id = assigned_kids[0]
    other_kid_ids = assigned_kids[1:]
    chore_name = coordinator.chores_data[chore_id][DATA_CHORE_NAME]
    first_kid_name = coordinator.kids_data[first_kid_id][const.DATA_KID_NAME]

    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # First kid claims and gets approved
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"kid_name": first_kid_name, "chore_name": chore_name},
            blocking=True,
        )

        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": first_kid_name,
                "chore_name": chore_name,
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # Verify other kids have chore in completed_by_other list
    for other_kid_id in other_kid_ids:
        completed_by_other = coordinator.kids_data[other_kid_id].get(
            DATA_KID_COMPLETED_BY_OTHER_CHORES, []
        )
        assert chore_id in completed_by_other, (
            f"Kid {other_kid_id} should have chore in completed_by_other list"
        )


@pytest.mark.asyncio
async def test_shared_first_disapproval_resets_all_kids(
    hass: HomeAssistant, scenario_full: tuple, mock_hass_users: dict
) -> None:
    """Test that disapproval resets ALL kids to pending state."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Find SHARED_FIRST chore
    result = get_shared_first_chore(coordinator, name_to_id_map)
    if not result:
        pytest.skip("No SHARED_FIRST chores with 2+ kids in scenario_full")

    chore_id, assigned_kids = result
    first_kid_id = assigned_kids[0]
    other_kid_ids = assigned_kids[1:]
    chore_name = coordinator.chores_data[chore_id][DATA_CHORE_NAME]
    first_kid_name = coordinator.kids_data[first_kid_id][const.DATA_KID_NAME]

    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # First kid claims and gets approved
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"kid_name": first_kid_name, "chore_name": chore_name},
            blocking=True,
        )

        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": first_kid_name,
                "chore_name": chore_name,
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

        # Now disapprove
        await hass.services.async_call(
            DOMAIN,
            "disapprove_chore",
            {
                "kid_name": first_kid_name,
                "chore_name": chore_name,
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # Verify first kid is reset
    assert not is_chore_claimed_for_kid(coordinator, first_kid_id, chore_id), (
        "First kid should not have chore in claimed state after disapproval"
    )
    assert not is_chore_approved_for_kid(coordinator, first_kid_id, chore_id), (
        "First kid should not have chore in approved state after disapproval"
    )

    # Verify other kids are reset - no longer in completed_by_other
    for other_kid_id in other_kid_ids:
        completed_by_other = coordinator.kids_data[other_kid_id].get(
            DATA_KID_COMPLETED_BY_OTHER_CHORES, []
        )
        assert chore_id not in completed_by_other, (
            f"Kid {other_kid_id} should not have chore in completed_by_other after disapproval"
        )


@pytest.mark.asyncio
async def test_shared_first_reclaim_after_disapproval(
    hass: HomeAssistant, scenario_full: tuple, mock_hass_users: dict
) -> None:
    """Test that any kid can claim after disapproval resets the chore."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Find SHARED_FIRST chore
    result = get_shared_first_chore(coordinator, name_to_id_map)
    if not result:
        pytest.skip("No SHARED_FIRST chores with 2+ kids in scenario_full")

    chore_id, assigned_kids = result
    first_kid_id = assigned_kids[0]
    second_kid_id = assigned_kids[1]
    chore_name = coordinator.chores_data[chore_id][DATA_CHORE_NAME]
    first_kid_name = coordinator.kids_data[first_kid_id][const.DATA_KID_NAME]
    second_kid_name = coordinator.kids_data[second_kid_id][const.DATA_KID_NAME]

    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # First kid claims and gets approved
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"kid_name": first_kid_name, "chore_name": chore_name},
            blocking=True,
        )

        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": first_kid_name,
                "chore_name": chore_name,
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

        # Disapprove
        await hass.services.async_call(
            DOMAIN,
            "disapprove_chore",
            {
                "kid_name": first_kid_name,
                "chore_name": chore_name,
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

        # Second kid should now be able to claim
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"kid_name": second_kid_name, "chore_name": chore_name},
            blocking=True,
        )

    # Verify second kid now has chore in claimed state
    assert is_chore_claimed_for_kid(coordinator, second_kid_id, chore_id), (
        "Second kid should be able to claim after disapproval reset"
    )


@pytest.mark.asyncio
async def test_shared_first_global_state_pending_to_claimed(
    hass: HomeAssistant, scenario_full: tuple, mock_hass_users: dict
) -> None:
    """Test global chore state transitions from pending to claimed for SHARED_FIRST."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Find SHARED_FIRST chore
    result = get_shared_first_chore(coordinator, name_to_id_map)
    if not result:
        pytest.skip("No SHARED_FIRST chores with 2+ kids in scenario_full")

    chore_id, assigned_kids = result
    first_kid_id = assigned_kids[0]
    chore_name = coordinator.chores_data[chore_id][DATA_CHORE_NAME]
    first_kid_name = coordinator.kids_data[first_kid_id][const.DATA_KID_NAME]

    # Note: Initial state might not be set, which is valid for pending state

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # First kid claims
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"kid_name": first_kid_name, "chore_name": chore_name},
            blocking=True,
        )

    # Global state should now be CLAIMED
    claimed_state = coordinator.chores_data[chore_id].get(DATA_CHORE_STATE)
    assert claimed_state == CHORE_STATE_CLAIMED, (
        f"Global state should be 'claimed' after first kid claims, got: {claimed_state}"
    )


@pytest.mark.asyncio
async def test_shared_first_global_state_claimed_to_approved(
    hass: HomeAssistant, scenario_full: tuple, mock_hass_users: dict
) -> None:
    """Test global chore state transitions from claimed to approved for SHARED_FIRST."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Find SHARED_FIRST chore
    result = get_shared_first_chore(coordinator, name_to_id_map)
    if not result:
        pytest.skip("No SHARED_FIRST chores with 2+ kids in scenario_full")

    chore_id, assigned_kids = result
    first_kid_id = assigned_kids[0]
    chore_name = coordinator.chores_data[chore_id][DATA_CHORE_NAME]
    first_kid_name = coordinator.kids_data[first_kid_id][const.DATA_KID_NAME]

    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # First kid claims
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"kid_name": first_kid_name, "chore_name": chore_name},
            blocking=True,
        )

        # Parent approves
        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": first_kid_name,
                "chore_name": chore_name,
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # Global state should now be APPROVED
    approved_state = coordinator.chores_data[chore_id].get(DATA_CHORE_STATE)
    assert approved_state == CHORE_STATE_APPROVED, (
        f"Global state should be 'approved' after approval, got: {approved_state}"
    )


@pytest.mark.asyncio
async def test_shared_first_with_three_kids(
    hass: HomeAssistant, scenario_full: tuple, mock_hass_users: dict
) -> None:
    """Test SHARED_FIRST with 3 kids - only first gets points, other two blocked."""
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Use dedicated 3-kid SHARED_FIRST chore (isolated from other tests)
    three_kid_chore_id = name_to_id_map.get("chore:Måil Pickup Race")
    if not three_kid_chore_id:
        pytest.skip("Måil Pickup Race chore not found in scenario_full")

    chore_info = coordinator.chores_data[three_kid_chore_id]
    three_kid_ids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
    if len(three_kid_ids) < 3:
        pytest.skip("Måil Pickup Race doesn't have 3 kids assigned")

    first_kid_id, second_kid_id, third_kid_id = three_kid_ids[:3]
    chore_name = coordinator.chores_data[three_kid_chore_id][DATA_CHORE_NAME]

    first_kid_name = coordinator.kids_data[first_kid_id][const.DATA_KID_NAME]
    second_kid_name = coordinator.kids_data[second_kid_id][const.DATA_KID_NAME]
    third_kid_name = coordinator.kids_data[third_kid_id][const.DATA_KID_NAME]

    # Record initial points
    first_initial = coordinator.kids_data[first_kid_id].get(DATA_KID_POINTS, 0)
    second_initial = coordinator.kids_data[second_kid_id].get(DATA_KID_POINTS, 0)
    third_initial = coordinator.kids_data[third_kid_id].get(DATA_KID_POINTS, 0)

    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # First kid claims
        await hass.services.async_call(
            DOMAIN,
            "claim_chore",
            {"kid_name": first_kid_name, "chore_name": chore_name},
            blocking=True,
        )

        # Second kid tries to claim - should be blocked
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                DOMAIN,
                "claim_chore",
                {"kid_name": second_kid_name, "chore_name": chore_name},
                blocking=True,
            )

        # Third kid tries to claim - should also be blocked
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                DOMAIN,
                "claim_chore",
                {"kid_name": third_kid_name, "chore_name": chore_name},
                blocking=True,
            )

        # Parent approves first kid
        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": first_kid_name,
                "chore_name": chore_name,
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # Verify points
    first_final = coordinator.kids_data[first_kid_id].get(DATA_KID_POINTS, 0)
    second_final = coordinator.kids_data[second_kid_id].get(DATA_KID_POINTS, 0)
    third_final = coordinator.kids_data[third_kid_id].get(DATA_KID_POINTS, 0)

    assert first_final > first_initial, "First kid should have gained points"
    assert second_final == second_initial, "Second kid should NOT have gained points"
    assert third_final == third_initial, "Third kid should NOT have gained points"

    # Verify both other kids are in completed_by_other state
    assert three_kid_chore_id in coordinator.kids_data[second_kid_id].get(
        DATA_KID_COMPLETED_BY_OTHER_CHORES, []
    ), "Second kid should be in completed_by_other state"
    assert three_kid_chore_id in coordinator.kids_data[third_kid_id].get(
        DATA_KID_COMPLETED_BY_OTHER_CHORES, []
    ), "Third kid should be in completed_by_other state"
