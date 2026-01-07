"""Test chore global state computation (Option C Testing - Category 3).

Tests global state computation based on completion_criteria and per-kid states:
- Single kid assigned: Global state = kid's state (1:1)
- Multi-kid INDEPENDENT: Mixed states → "independent"
- Multi-kid SHARED: Partial states → "claimed_in_part" / "approved_in_part"

Priority: P1 CRITICAL (Core Option B validation)
Coverage: coordinator._process_chore_state() global state logic (lines 2962-3020)
"""

# pylint: disable=protected-access
# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kidschores import const
from custom_components.kidschores.const import (
    CHORE_STATE_APPROVED,
    CHORE_STATE_APPROVED_IN_PART,
    CHORE_STATE_CLAIMED,
    CHORE_STATE_CLAIMED_IN_PART,
    CHORE_STATE_INDEPENDENT,
    CHORE_STATE_PENDING,
    COMPLETION_CRITERIA_INDEPENDENT,
    COMPLETION_CRITERIA_SHARED,
    COORDINATOR,
    DATA_CHORE_COMPLETION_CRITERIA,
    DATA_CHORE_STATE,
    DOMAIN,
)
from custom_components.kidschores.migration_pre_v42 import PreV42Migrator
from tests.conftest import reset_chore_state_for_kid

# ============================================================================
# Test: Single Kid Assigned - Global State = Kid State (1:1)
# ============================================================================


@pytest.mark.asyncio
async def test_single_kid_global_state_pending(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test single-kid chore: global state = pending when kid is pending.

    Validates: When only one kid is assigned, global state mirrors kid's state exactly.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Migrate to use completion_criteria
    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Find single-kid chore: "Feed the cåts" assigned only to Zoë
    feed_cats_id = name_to_id_map["chore:Feed the cåts"]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Verify single assignment
    chore_info = coordinator.chores_data[feed_cats_id]
    assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
    assert len(assigned_kids) == 1, "Feed the cåts should be assigned to 1 kid"
    assert zoe_id in assigned_kids

    # Clear any existing state using v0.4.0 helper
    reset_chore_state_for_kid(coordinator, zoe_id, feed_cats_id)

    # Process pending state
    coordinator._process_chore_state(zoe_id, feed_cats_id, CHORE_STATE_PENDING)

    # Verify global state = pending (1:1)
    assert chore_info[DATA_CHORE_STATE] == CHORE_STATE_PENDING


@pytest.mark.asyncio
async def test_single_kid_global_state_claimed(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test single-kid chore: global state = claimed when kid claims.

    Validates: Single kid claimed → global state becomes "claimed".
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    feed_cats_id = name_to_id_map["chore:Feed the cåts"]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Mock notifications
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Process claimed state
        coordinator._process_chore_state(zoe_id, feed_cats_id, CHORE_STATE_CLAIMED)

    # Verify global state = claimed (1:1)
    chore_info = coordinator.chores_data[feed_cats_id]
    assert chore_info[DATA_CHORE_STATE] == CHORE_STATE_CLAIMED


@pytest.mark.asyncio
async def test_single_kid_global_state_approved(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test single-kid chore: global state = approved when kid is approved.

    Validates: Single kid approved → global state becomes "approved".
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    feed_cats_id = name_to_id_map["chore:Feed the cåts"]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Mock notifications
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Process approved state
        coordinator._process_chore_state(
            zoe_id, feed_cats_id, CHORE_STATE_APPROVED, points_awarded=10
        )

    # Verify global state = approved (1:1)
    chore_info = coordinator.chores_data[feed_cats_id]
    assert chore_info[DATA_CHORE_STATE] == CHORE_STATE_APPROVED


# ============================================================================
# Test: Multi-Kid INDEPENDENT - Mixed States → "independent"
# ============================================================================


@pytest.mark.asyncio
async def test_independent_multi_kid_all_pending(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test INDEPENDENT multi-kid: all pending → global state = pending.

    Validates: When all kids are in same state, global state = that state.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # "Stär sweep" is assigned to Zoë, Max!, Lila (multi-kid)
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    # Verify INDEPENDENT and multi-assignment
    chore_info = coordinator.chores_data[star_sweep_id]
    assert (
        chore_info.get(DATA_CHORE_COMPLETION_CRITERIA)
        == COMPLETION_CRITERIA_INDEPENDENT
    )
    assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
    assert len(assigned_kids) >= 3, "Stär sweep should be assigned to 3 kids"

    # Clear all states to pending using v0.4.0 helper
    for kid_id in [zoe_id, max_id, lila_id]:
        reset_chore_state_for_kid(coordinator, kid_id, star_sweep_id)

    # Process pending for one kid (triggers global state recompute)
    coordinator._process_chore_state(zoe_id, star_sweep_id, CHORE_STATE_PENDING)

    # Verify: all pending → global state = pending
    assert chore_info[DATA_CHORE_STATE] == CHORE_STATE_PENDING


@pytest.mark.asyncio
async def test_independent_multi_kid_one_claimed(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test INDEPENDENT multi-kid: one claimed → global state = "independent".

    Validates: Mixed states on INDEPENDENT chore → global state = "independent".
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    chore_info = coordinator.chores_data[star_sweep_id]
    assert (
        chore_info.get(DATA_CHORE_COMPLETION_CRITERIA)
        == COMPLETION_CRITERIA_INDEPENDENT
    )

    # Clear all states to pending
    for kid_id in [zoe_id, max_id, lila_id]:
        reset_chore_state_for_kid(coordinator, kid_id, star_sweep_id)

    # Mock notifications
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Set pending_claim_count BEFORE _process_chore_state (it recomputes global state internally)
        zoe_chore_data = coordinator.kids_data[zoe_id][const.DATA_KID_CHORE_DATA][
            star_sweep_id
        ]
        zoe_chore_data[const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT] = 1
        # Only Zoë claims
        coordinator._process_chore_state(zoe_id, star_sweep_id, CHORE_STATE_CLAIMED)

    # Verify: mixed states (1 claimed, 2 pending) → global state = "independent"
    assert chore_info[DATA_CHORE_STATE] == CHORE_STATE_INDEPENDENT


@pytest.mark.asyncio
async def test_independent_multi_kid_all_approved(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test INDEPENDENT multi-kid: all approved → global state = "approved".

    Validates: All kids in same state → global state = that state (even for INDEPENDENT).
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # Clear all states first using v0.4.0 helper
    for kid_id in [zoe_id, max_id, lila_id]:
        reset_chore_state_for_kid(coordinator, kid_id, star_sweep_id)

    # Mock notifications
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # All kids approve
        for kid_id in [zoe_id, max_id, lila_id]:
            coordinator._process_chore_state(
                kid_id, star_sweep_id, CHORE_STATE_APPROVED, points_awarded=20
            )

    # Verify: all approved → global state = "approved"
    assert chore_info[DATA_CHORE_STATE] == CHORE_STATE_APPROVED


# ============================================================================
# Test: Multi-Kid SHARED - Partial States → "claimed_in_part" / "approved_in_part"
# ============================================================================


@pytest.mark.asyncio
async def test_shared_multi_kid_none_claimed(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test SHARED multi-kid: none claimed → global state = pending.

    Validates: All kids pending on SHARED chore → global state = pending.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Find or create a SHARED chore
    shared_chore_id = None
    for chore_id, chore_info in coordinator.chores_data.items():
        if chore_info.get(DATA_CHORE_COMPLETION_CRITERIA) == COMPLETION_CRITERIA_SHARED:
            assigned = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
            if len(assigned) >= 2:
                shared_chore_id = chore_id
                break

    # If no SHARED chore exists, convert Stär sweep to SHARED for this test
    if shared_chore_id is None:
        star_sweep_id = name_to_id_map["chore:Stär sweep"]
        coordinator.chores_data[star_sweep_id][DATA_CHORE_COMPLETION_CRITERIA] = (
            COMPLETION_CRITERIA_SHARED
        )
        shared_chore_id = star_sweep_id
        coordinator._persist()

    chore_info = coordinator.chores_data[shared_chore_id]
    assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])

    # Clear all states to pending
    for kid_id in assigned_kids:
        reset_chore_state_for_kid(coordinator, kid_id, shared_chore_id)

    # Process pending for first kid
    coordinator._process_chore_state(
        assigned_kids[0], shared_chore_id, CHORE_STATE_PENDING
    )

    # Verify: all pending → global state = pending
    assert chore_info[DATA_CHORE_STATE] == CHORE_STATE_PENDING


@pytest.mark.asyncio
async def test_shared_multi_kid_partial_claimed(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test SHARED multi-kid: partial claimed → global state = "claimed_in_part".

    Validates: Some kids claimed on SHARED chore → global state = "claimed_in_part".
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Convert Stär sweep to SHARED for this test
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    coordinator.chores_data[star_sweep_id][DATA_CHORE_COMPLETION_CRITERIA] = (
        COMPLETION_CRITERIA_SHARED
    )
    coordinator._persist()

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # Clear all states to pending
    for kid_id in [zoe_id, max_id, lila_id]:
        reset_chore_state_for_kid(coordinator, kid_id, star_sweep_id)

    # Mock notifications
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Set pending_claim_count BEFORE _process_chore_state (it recomputes global state internally)
        zoe_chore_data = coordinator.kids_data[zoe_id][const.DATA_KID_CHORE_DATA][
            star_sweep_id
        ]
        zoe_chore_data[const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT] = 1
        # Only Zoë claims (partial)
        coordinator._process_chore_state(zoe_id, star_sweep_id, CHORE_STATE_CLAIMED)

    # Verify: partial claimed → global state = "claimed_in_part"
    assert chore_info[DATA_CHORE_STATE] == CHORE_STATE_CLAIMED_IN_PART


@pytest.mark.asyncio
async def test_shared_multi_kid_all_claimed(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test SHARED multi-kid: all claimed → global state = "claimed".

    Validates: All kids claimed on SHARED chore → global state = "claimed".
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Convert Stär sweep to SHARED
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    coordinator.chores_data[star_sweep_id][DATA_CHORE_COMPLETION_CRITERIA] = (
        COMPLETION_CRITERIA_SHARED
    )
    coordinator._persist()

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # Clear all states
    for kid_id in [zoe_id, max_id, lila_id]:
        reset_chore_state_for_kid(coordinator, kid_id, star_sweep_id)

    # Mock notifications
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # All kids claim
        for kid_id in [zoe_id, max_id, lila_id]:
            coordinator._process_chore_state(kid_id, star_sweep_id, CHORE_STATE_CLAIMED)

    # Verify: all claimed → global state = "claimed"
    assert chore_info[DATA_CHORE_STATE] == CHORE_STATE_CLAIMED


@pytest.mark.asyncio
async def test_shared_multi_kid_partial_approved(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test SHARED multi-kid: partial approved → global state = "approved_in_part".

    Validates: Some kids approved on SHARED chore → global state = "approved_in_part".
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Convert Stär sweep to SHARED
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    coordinator.chores_data[star_sweep_id][DATA_CHORE_COMPLETION_CRITERIA] = (
        COMPLETION_CRITERIA_SHARED
    )
    coordinator._persist()

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # Clear all states
    for kid_id in [zoe_id, max_id, lila_id]:
        reset_chore_state_for_kid(coordinator, kid_id, star_sweep_id)

    # Mock notifications
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Only Zoë approved (partial)
        coordinator._process_chore_state(
            zoe_id, star_sweep_id, CHORE_STATE_APPROVED, points_awarded=20
        )

    # Verify: partial approved → global state = "approved_in_part"
    assert chore_info[DATA_CHORE_STATE] == CHORE_STATE_APPROVED_IN_PART


@pytest.mark.asyncio
async def test_shared_multi_kid_all_approved(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test SHARED multi-kid: all approved → global state = "approved".

    Validates: All kids approved on SHARED chore → global state = "approved".
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Convert Stär sweep to SHARED
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    coordinator.chores_data[star_sweep_id][DATA_CHORE_COMPLETION_CRITERIA] = (
        COMPLETION_CRITERIA_SHARED
    )
    coordinator._persist()

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # Clear all states
    for kid_id in [zoe_id, max_id, lila_id]:
        reset_chore_state_for_kid(coordinator, kid_id, star_sweep_id)

    # Mock notifications
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # All kids approve
        for kid_id in [zoe_id, max_id, lila_id]:
            coordinator._process_chore_state(
                kid_id, star_sweep_id, CHORE_STATE_APPROVED, points_awarded=20
            )

    # Verify: all approved → global state = "approved"
    assert chore_info[DATA_CHORE_STATE] == CHORE_STATE_APPROVED


# ============================================================================
# Test: State Transitions - INDEPENDENT vs SHARED behavior
# ============================================================================


@pytest.mark.asyncio
async def test_independent_mixed_approved_and_claimed(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test INDEPENDENT: one approved + one claimed → global state = "independent".

    Validates: Any mixed states on INDEPENDENT → global state = "independent".
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    chore_info = coordinator.chores_data[star_sweep_id]
    assert (
        chore_info.get(DATA_CHORE_COMPLETION_CRITERIA)
        == COMPLETION_CRITERIA_INDEPENDENT
    )

    # Clear all states
    for kid_id in [zoe_id, max_id, lila_id]:
        reset_chore_state_for_kid(coordinator, kid_id, star_sweep_id)

    # Mock notifications
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Zoë approves
        coordinator._process_chore_state(
            zoe_id, star_sweep_id, CHORE_STATE_APPROVED, points_awarded=20
        )
        # Max! claims
        coordinator._process_chore_state(max_id, star_sweep_id, CHORE_STATE_CLAIMED)
        # Lila pending (default)

    # Verify: mixed states (approved, claimed, pending) → global = "independent"
    assert chore_info[DATA_CHORE_STATE] == CHORE_STATE_INDEPENDENT


@pytest.mark.asyncio
async def test_shared_mixed_approved_and_claimed(
    hass: HomeAssistant,
    scenario_full,
    mock_hass_users,
) -> None:
    """Test SHARED: one approved + one claimed → global state = "approved_in_part".

    Validates: Mixed states with approval on SHARED → "approved_in_part".
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Convert to SHARED
    star_sweep_id = name_to_id_map["chore:Stär sweep"]
    coordinator.chores_data[star_sweep_id][DATA_CHORE_COMPLETION_CRITERIA] = (
        COMPLETION_CRITERIA_SHARED
    )
    coordinator._persist()

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    lila_id = name_to_id_map["kid:Lila"]

    chore_info = coordinator.chores_data[star_sweep_id]

    # Clear all states
    for kid_id in [zoe_id, max_id, lila_id]:
        reset_chore_state_for_kid(coordinator, kid_id, star_sweep_id)

    # Mock notifications
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Zoë approves
        coordinator._process_chore_state(
            zoe_id, star_sweep_id, CHORE_STATE_APPROVED, points_awarded=20
        )
        # Max! claims
        coordinator._process_chore_state(max_id, star_sweep_id, CHORE_STATE_CLAIMED)
        # Lila pending (default)

    # Verify: mixed with approval on SHARED → "approved_in_part"
    assert chore_info[DATA_CHORE_STATE] == CHORE_STATE_APPROVED_IN_PART
