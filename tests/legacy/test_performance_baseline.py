"""Performance baseline test for KidsChores coordinator.

Measures performance of instrumented coordinator methods to establish baseline
metrics before optimization work begins.
"""

# pylint: disable=protected-access  # Accessing coordinator internals for perf testing
# pylint: disable=unused-argument  # Fixtures needed for test setup

from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant

from custom_components.kidschores.const import (
    CHORE_STATE_APPROVED,
    CHORE_STATE_CLAIMED,
    COORDINATOR,
    DOMAIN,
)


async def test_performance_baseline_with_scenario_full(
    hass: HomeAssistant,
    scenario_full: tuple[Any, dict[str, str]],
) -> None:
    """Capture baseline performance with full scenario data.

    Uses scenario_full fixture: 3 kids, 7 chores, 5 badges, realistic data.

    Run with: pytest tests/test_performance_baseline.py -v -s
    """
    config_entry, _ = scenario_full  # name_to_id_map unused but needed for fixture
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    print("\n" + "=" * 80)
    print("PERFORMANCE BASELINE TEST - Full Scenario Dataset")
    print("=" * 80)
    print(
        f"Scale: {len(coordinator.kids_data)} kids, "
        f"{len(coordinator.chores_data)} chores, "
        f"{len(coordinator.badges_data)} badges, "
        f"{len(coordinator.parents_data)} parents"
    )
    print("=" * 80)

    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Test 1: Check overdue chores (O(chores × kids))
        print("\nTest 1: Overdue check scan...")
        await coordinator._check_overdue_chores()

        # Test 2: Persist operation
        print("\nTest 2: Storage persist...")
        coordinator._persist()

        # Test 3: Badge evaluation for each kid
        print(f"\nTest 3: Badge evaluation for {len(coordinator.kids_data)} kids...")
        for kid_id in coordinator.kids_data.keys():
            coordinator._check_badges_for_kid(kid_id)

        # Test 4: Parent notifications
        if coordinator.parents_data and coordinator.kids_data:
            print(
                f"\nTest 4: Parent notifications ({len(coordinator.parents_data)} parents)..."
            )
            first_kid_id = list(coordinator.kids_data.keys())[0]
            await coordinator._notify_parents_translated(
                first_kid_id,
                "notification_title_chore_claimed",
                "notification_message_chore_claimed",
                message_data={"kid_name": "Test", "chore_name": "Performance Test"},
            )

        # Test 5: Entity cleanup
        print("\nTest 5: Entity registry cleanup...")
        await coordinator._remove_orphaned_kid_chore_entities()

        # Test 6: Chore claim operation
        print("\nTest 6: Chore claim timing...")
        if coordinator.chores_data and coordinator.kids_data:
            # Find a claimable chore (one not already claimed/approved)
            kid_id = list(coordinator.kids_data.keys())[0]
            kid_info = coordinator.kids_data[kid_id]
            chore_data = kid_info.get("chore_data", {})

            # Find a chore assigned to this kid that isn't already claimed/approved
            claimable_chore_id = None
            for chore_id, chore_info in coordinator.chores_data.items():
                kid_chore_state = chore_data.get(chore_id, {}).get("state")
                if kid_id in chore_info.get(
                    "assigned_kids", []
                ) and kid_chore_state not in (
                    CHORE_STATE_CLAIMED,
                    CHORE_STATE_APPROVED,
                ):
                    claimable_chore_id = chore_id
                    break

            if claimable_chore_id:
                coordinator.claim_chore(kid_id, claimable_chore_id, "test_user")
                print(f"    Claimed chore {claimable_chore_id} for kid {kid_id}")

        # Test 7: Chore approval and point addition
        print("\nTest 7: Chore approval timing (includes point addition)...")
        if coordinator.chores_data and coordinator.kids_data:
            # Find a claimed chore to approve
            kid_id = list(coordinator.kids_data.keys())[0]
            kid_info = coordinator.kids_data[kid_id]
            chore_data = kid_info.get("chore_data", {})

            # Find a chore in claimed state
            chore_id_to_approve = None
            for chore_id, cd in chore_data.items():
                if cd.get("state") == CHORE_STATE_CLAIMED:
                    chore_id_to_approve = chore_id
                    break

            if chore_id_to_approve:
                coordinator.approve_chore("test_user", kid_id, chore_id_to_approve)
                print(f"    Approved chore {chore_id_to_approve} for kid {kid_id}")

        # Test 8: Bulk operations - approve multiple chores
        print("\nTest 8: Bulk chore operations (claim then approve)...")
        if len(coordinator.kids_data) >= 2 and len(coordinator.chores_data) >= 2:
            operations_count = 0
            for kid_id in list(coordinator.kids_data.keys())[:2]:  # Just first 2 kids
                kid_info = coordinator.kids_data[kid_id]
                chore_data = kid_info.get("chore_data", {})

                # Find up to 2 chores per kid we can work with
                for chore_id, chore_info in list(coordinator.chores_data.items())[:2]:
                    kid_chore_state = chore_data.get(chore_id, {}).get("state")
                    if kid_id in chore_info.get(
                        "assigned_kids", []
                    ) and kid_chore_state not in (
                        CHORE_STATE_CLAIMED,
                        CHORE_STATE_APPROVED,
                    ):
                        # Reset chore state to pending first
                        coordinator._process_chore_state(kid_id, chore_id, "pending")
                        # Claim it
                        coordinator.claim_chore(kid_id, chore_id, "test_user")
                        # Approve it
                        coordinator.approve_chore("test_user", kid_id, chore_id)
                        operations_count += 2
                        if (
                            operations_count >= 6
                        ):  # Limit to avoid test running too long
                            break
                if operations_count >= 6:
                    break
            print(
                f"    Completed {operations_count} bulk operations (claims + approvals)"
            )

    print("\n" + "=" * 80)
    print("BASELINE METRICS CAPTURED")
    print("=" * 80)
    print("\nCheck the PERF: log entries above for:")
    print("  - _persist() call frequency and timing")
    print("  - _check_overdue_chores() duration (chores × kids operations)")
    print("  - _check_badges_for_kid() per-kid timing")
    print("  - _notify_parents_translated() sequential notification latency")
    print("  - _remove_orphaned_kid_chore_entities() entity scan duration")
    print("  - claim_chore() timing")
    print("  - approve_chore() timing (includes point addition)")
    print("  - Bulk operation performance (multiple claims/approvals)")
    print("\n")
