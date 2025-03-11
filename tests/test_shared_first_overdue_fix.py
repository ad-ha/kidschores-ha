"""Test SHARED_FIRST overdue logic fix.

This test module validates that SHARED_FIRST chores correctly handle overdue
states, particularly that completed chores don't show as overdue after restart.

Uses "Täke Öut Trash" (assigned to all 3 kids: Zoë, Max!, Lila) for comprehensive
SHARED_FIRST testing.
"""

# pylint: disable=protected-access

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.kidschores import const
from tests.conftest import create_test_datetime


@pytest.mark.asyncio
async def test_shared_first_completed_not_overdue(
    hass, scenario_full, mock_hass_users
) -> None:
    """Test that completed SHARED_FIRST chores don't show as overdue for anyone.

    Scenario: Zoë claims and gets approved for "Täke Öut Trash".
    Expected: No kids should be overdue, global state should be "approved".
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # Get kids from scenario_full using name_to_id_map
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    # Get SHARED_FIRST chore: "Täke Öut Trash" (assigned to all 3 kids)
    chore_id = name_to_id_map["chore:Täke Öut Trash"]

    # Set chore due date to yesterday (overdue)
    yesterday = create_test_datetime(days_offset=-1)
    coordinator._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_DUE_DATE] = (
        yesterday
    )

    # Mock notifications during testing
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        with patch.object(coordinator, "_notify_overdue_chore", new=MagicMock()):
            # Zoë claims the chore
            coordinator.claim_chore(zoe_id, chore_id, mock_hass_users["kid1"].id)

            # Verify global state is claimed after first claim
            chore_info = coordinator.chores_data[chore_id]
            assert chore_info[const.DATA_CHORE_STATE] == const.CHORE_STATE_CLAIMED, (
                f"Global state should be claimed after first claim, "
                f"got: {chore_info[const.DATA_CHORE_STATE]}"
            )

            # Approve Zoë's claim (parent_user_id, kid_id, chore_id)
            coordinator.approve_chore(mock_hass_users["parent1"].id, zoe_id, chore_id)

            # Run overdue check (async method)
            await coordinator._check_overdue_chores()

            # Verify: No one should be overdue for this chore
            zoe_info = coordinator.kids_data[zoe_id]
            max_info = coordinator.kids_data[max_id]
            lila_info = coordinator.kids_data[lila_id]

            assert chore_id not in zoe_info.get(const.DATA_KID_OVERDUE_CHORES, []), (
                "Zoë should not be overdue (she completed it)"
            )
            assert chore_id not in max_info.get(const.DATA_KID_OVERDUE_CHORES, []), (
                "Max! should not be overdue (completed by other)"
            )
            assert chore_id not in lila_info.get(const.DATA_KID_OVERDUE_CHORES, []), (
                "Lila should not be overdue (completed by other)"
            )

            # Verify global chore state is approved (not overdue)
            chore_info = coordinator.chores_data[chore_id]
            assert chore_info[const.DATA_CHORE_STATE] == const.CHORE_STATE_APPROVED, (
                f"Global state should be approved, got: {chore_info[const.DATA_CHORE_STATE]}"
            )


@pytest.mark.asyncio
async def test_shared_first_pending_claim_becomes_overdue(
    hass, scenario_full, mock_hass_users
) -> None:
    """Test that SHARED_FIRST chore with pending claim marks only claimant as overdue.

    Scenario: Zoë claims "Täke Öut Trash" but doesn't get approved, chore is past due.
    Expected: Only Zoë should be overdue; Max! and Lila should be completed_by_other.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # Get kids using name_to_id_map
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    # Get SHARED_FIRST chore: "Täke Öut Trash" (assigned to all 3 kids)
    chore_id = name_to_id_map["chore:Täke Öut Trash"]

    # Set chore due date to yesterday (overdue)
    yesterday = create_test_datetime(days_offset=-1)
    coordinator._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_DUE_DATE] = (
        yesterday
    )

    # Mock notifications during testing
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        with patch.object(coordinator, "_notify_overdue_chore", new=MagicMock()):
            # Zoë claims the chore but doesn't get approved
            coordinator.claim_chore(zoe_id, chore_id, mock_hass_users["kid1"].id)

            # Run overdue check (async method)
            await coordinator._check_overdue_chores()

            # Verify: Only Zoë (the claimant) should be overdue
            zoe_info = coordinator.kids_data[zoe_id]
            max_info = coordinator.kids_data[max_id]
            lila_info = coordinator.kids_data[lila_id]

            assert chore_id in zoe_info.get(const.DATA_KID_OVERDUE_CHORES, []), (
                "Zoë should be overdue (she claimed but wasn't approved in time)"
            )
            assert chore_id not in max_info.get(const.DATA_KID_OVERDUE_CHORES, []), (
                "Max! should not be overdue (completed_by_other state)"
            )
            assert chore_id not in lila_info.get(const.DATA_KID_OVERDUE_CHORES, []), (
                "Lila should not be overdue (completed_by_other state)"
            )

            # Verify Max! and Lila are in completed_by_other state
            assert chore_id in max_info.get(
                const.DATA_KID_COMPLETED_BY_OTHER_CHORES, []
            ), "Max! should be in completed_by_other list"
            assert chore_id in lila_info.get(
                const.DATA_KID_COMPLETED_BY_OTHER_CHORES, []
            ), "Lila should be in completed_by_other list"

            # Verify global chore state is claimed (claim wins over overdue for SHARED_FIRST)
            # The last_overdue timestamp tracks that overdue occurred, but claim takes priority
            chore_info = coordinator.chores_data[chore_id]
            assert chore_info[const.DATA_CHORE_STATE] == const.CHORE_STATE_CLAIMED, (
                f"Global state should be claimed (claim wins), got: {chore_info[const.DATA_CHORE_STATE]}"
            )


@pytest.mark.asyncio
async def test_shared_first_no_claims_all_can_be_overdue(hass, scenario_full) -> None:
    """Test that SHARED_FIRST chore with no claims allows all kids to be overdue.

    Scenario: No one claims "Täke Öut Trash" and it's past due.
    Expected: All 3 kids (Zoë, Max!, Lila) should be overdue.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # Get kids using name_to_id_map
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    # Get SHARED_FIRST chore: "Täke Öut Trash" (assigned to all 3 kids)
    chore_id = name_to_id_map["chore:Täke Öut Trash"]

    # Set chore due date to yesterday (overdue)
    yesterday = create_test_datetime(days_offset=-1)
    coordinator._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_DUE_DATE] = (
        yesterday
    )

    # Mock notifications during testing
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        with patch.object(coordinator, "_notify_overdue_chore", new=MagicMock()):
            # No one claims the chore - run overdue check (async method)
            await coordinator._check_overdue_chores()

            # Verify: All kids should be overdue for this chore
            zoe_info = coordinator.kids_data[zoe_id]
            max_info = coordinator.kids_data[max_id]
            lila_info = coordinator.kids_data[lila_id]

            assert chore_id in zoe_info.get(const.DATA_KID_OVERDUE_CHORES, []), (
                "Zoë should be overdue (no one claimed)"
            )
            assert chore_id in max_info.get(const.DATA_KID_OVERDUE_CHORES, []), (
                "Max! should be overdue (no one claimed)"
            )
            assert chore_id in lila_info.get(const.DATA_KID_OVERDUE_CHORES, []), (
                "Lila should be overdue (no one claimed)"
            )

            # Verify global chore state is overdue
            chore_info = coordinator.chores_data[chore_id]
            assert chore_info[const.DATA_CHORE_STATE] == const.CHORE_STATE_OVERDUE, (
                f"Global state should be overdue, got: {chore_info[const.DATA_CHORE_STATE]}"
            )


@pytest.mark.asyncio
async def test_shared_first_persistence_across_restart(
    hass, scenario_full, mock_hass_users
) -> None:
    """Test that SHARED_FIRST chore approval persists correctly across restart.

    This reproduces the issue where after restart, all kids assigned to
    the shared first chore show as pending even though it was approved by one.

    Scenario: Zoë claims and gets approved for "Täke Öut Trash", then coordinator refreshes.
    Expected: Zoë remains approved, Max! and Lila remain completed_by_other, global stays approved.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # Get kids using name_to_id_map
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    # Get SHARED_FIRST chore: "Täke Öut Trash" (assigned to all 3 kids)
    chore_id = name_to_id_map["chore:Täke Öut Trash"]

    # Mock notifications during testing
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        with patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()):
            # Zoë claims and gets approved (parent_user_id, kid_id, chore_id)
            coordinator.claim_chore(zoe_id, chore_id, mock_hass_users["kid1"].id)
            coordinator.approve_chore(mock_hass_users["parent1"].id, zoe_id, chore_id)

            # Verify initial state after approval
            assert coordinator.is_approved_in_current_period(zoe_id, chore_id), (
                "Zoë should be approved in current period"
            )

            # Check Max!'s state - should be completed_by_other
            max_chore_data = coordinator._get_kid_chore_data(max_id, chore_id)
            max_state = max_chore_data.get(const.DATA_KID_CHORE_DATA_STATE)
            assert max_state == const.CHORE_STATE_COMPLETED_BY_OTHER, (
                f"Max!'s state should be completed_by_other, got: {max_state}"
            )

            # Check Lila's state - should be completed_by_other
            lila_chore_data = coordinator._get_kid_chore_data(lila_id, chore_id)
            lila_state = lila_chore_data.get(const.DATA_KID_CHORE_DATA_STATE)
            assert lila_state == const.CHORE_STATE_COMPLETED_BY_OTHER, (
                f"Lila's state should be completed_by_other, got: {lila_state}"
            )

            # Verify global state is approved before refresh
            chore_info = coordinator.chores_data[chore_id]
            assert chore_info[const.DATA_CHORE_STATE] == const.CHORE_STATE_APPROVED, (
                f"Global state should be approved before refresh, "
                f"got: {chore_info[const.DATA_CHORE_STATE]}"
            )

            # Simulate coordinator refresh (like after restart)
            await coordinator.async_refresh()

            # Verify state persists after refresh
            assert coordinator.is_approved_in_current_period(zoe_id, chore_id), (
                "Zoë's approval should persist after refresh"
            )

            # Check Max!'s state still completed_by_other after refresh
            max_chore_data_after = coordinator._get_kid_chore_data(max_id, chore_id)
            max_state_after = max_chore_data_after.get(const.DATA_KID_CHORE_DATA_STATE)
            assert max_state_after == const.CHORE_STATE_COMPLETED_BY_OTHER, (
                f"Max!'s state should remain completed_by_other after refresh, "
                f"got: {max_state_after}"
            )

            # Check Lila's state still completed_by_other after refresh
            lila_chore_data_after = coordinator._get_kid_chore_data(lila_id, chore_id)
            lila_state_after = lila_chore_data_after.get(
                const.DATA_KID_CHORE_DATA_STATE
            )
            assert lila_state_after == const.CHORE_STATE_COMPLETED_BY_OTHER, (
                f"Lila's state should remain completed_by_other after refresh, "
                f"got: {lila_state_after}"
            )

            # Global chore state should remain approved
            chore_info_after = coordinator.chores_data[chore_id]
            assert (
                chore_info_after[const.DATA_CHORE_STATE] == const.CHORE_STATE_APPROVED
            ), (
                f"Global state should remain approved after refresh, "
                f"got: {chore_info_after[const.DATA_CHORE_STATE]}"
            )
