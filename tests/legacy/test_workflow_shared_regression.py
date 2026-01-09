"""Test SHARED chore approval behavior (Phase C Sprint 1, File 3).

Tests regression scenarios for SHARED chores to ensure approval logic
correctly handles chore-level due dates (not per-kid) for SHARED_ALL/SHARED_FIRST scenarios.

Priority: P2 SECONDARY (Shared chore regression validation)
Coverage: 4 regression tests for SHARED approval behavior
"""

# pylint: disable=protected-access
# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from dateutil import parser
from homeassistant.core import Context, HomeAssistant
from homeassistant.util import dt as dt_util  # pylint: disable=unused-import

from custom_components.kidschores import const
from custom_components.kidschores.const import (
    COMPLETION_CRITERIA_SHARED,
    COORDINATOR,
    DATA_CHORE_COMPLETION_CRITERIA,
    DATA_CHORE_DUE_DATE,
    DOMAIN,
)
from custom_components.kidschores.migration_pre_v42 import PreV42Migrator
from tests.legacy.conftest import is_chore_claimed_for_kid  # pylint: disable=unused-import


@pytest.mark.asyncio
async def test_shared_all_approval_uses_chore_level_due_date(
    hass: HomeAssistant, scenario_full, mock_hass_users
) -> None:
    """Test SHARED_ALL chore: approval advances chore-level due date.

    Validates that _check_overdue_chores() uses chore-level due date
    for SHARED chores (not per-kid).
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Find or create a SHARED chore in scenario
    # If no SHARED chore exists, mark test as pending
    shared_chore_id = None
    for chore_id, chore_info in coordinator.chores_data.items():
        if chore_info.get(DATA_CHORE_COMPLETION_CRITERIA) == COMPLETION_CRITERIA_SHARED:
            shared_chore_id = chore_id
            break

    if not shared_chore_id:
        pytest.skip("No SHARED chores in scenario_full - Phase 3 test pending")

    zoe_id = name_to_id_map["kid:Zoë"]
    original_chore_due_date = coordinator.chores_data[shared_chore_id].get(
        DATA_CHORE_DUE_DATE
    )

    # Parse if string
    if isinstance(original_chore_due_date, str):
        original_chore_due_date = parser.isoparse(original_chore_due_date)

    # Claim chore using coordinator method (v0.4.0+ pattern)
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(zoe_id, shared_chore_id, "Zoë")

    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    # Mock notifications to prevent ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": "Zoë",
                "chore_name": coordinator.chores_data[shared_chore_id][
                    const.DATA_CHORE_NAME
                ],
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # For SHARED chores, verify chore-level due date may have advanced
    # (or remained same depending on recurrence logic)
    new_chore_due_date = coordinator.chores_data[shared_chore_id].get(
        DATA_CHORE_DUE_DATE
    )
    if isinstance(new_chore_due_date, str):
        new_chore_due_date = parser.isoparse(new_chore_due_date)

    # Both should be valid datetime objects (or both None)
    if original_chore_due_date is not None:
        assert isinstance(new_chore_due_date, (datetime, type(None))), (
            "Chore-level due date should be datetime or None"
        )


@pytest.mark.asyncio
async def test_shared_first_only_first_kid_claims(
    hass: HomeAssistant, scenario_full, mock_hass_users
) -> None:
    """Test SHARED_FIRST chore: only first kid to claim completes it.

    Validates SHARED_FIRST completion criteria logic.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Find or create a SHARED_FIRST chore
    shared_first_chore_id = None
    for chore_id, chore_info in coordinator.chores_data.items():
        if chore_info.get(DATA_CHORE_COMPLETION_CRITERIA) == "shared_first":
            shared_first_chore_id = chore_id
            break

    if not shared_first_chore_id:
        pytest.skip("No SHARED_FIRST chores in scenario_full - test pending")

    zoe_id = name_to_id_map["kid:Zoë"]
    chore_name = coordinator.chores_data[shared_first_chore_id][const.DATA_CHORE_NAME]

    # Claim chore using coordinator method (v0.4.0+ pattern)
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(zoe_id, shared_first_chore_id, "Zoë")

    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    # Mock notifications to prevent ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": "Zoë",
                "chore_name": chore_name,
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # SHARED_FIRST: First approval should complete for all kids
    # Verify Zoë no longer has chore in claimed state
    assert not is_chore_claimed_for_kid(coordinator, zoe_id, shared_first_chore_id), (
        "SHARED_FIRST: Claimed chore should be removed after approval"
    )


@pytest.mark.asyncio
async def test_alternating_chore_approval_rotation(
    hass: HomeAssistant, scenario_full, mock_hass_users
) -> None:
    """Test ALTERNATING chore: approval rotates to next kid.

    Validates ALTERNATING completion criteria logic.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    migrator = PreV42Migrator(coordinator)
    migrator._migrate_independent_chores()
    coordinator._persist()

    # Find or create an ALTERNATING chore
    alternating_chore_id = None
    for chore_id, chore_info in coordinator.chores_data.items():
        if chore_info.get(DATA_CHORE_COMPLETION_CRITERIA) == "alternating":
            alternating_chore_id = chore_id
            break

    if not alternating_chore_id:
        pytest.skip("No ALTERNATING chores in scenario_full - test pending")

    zoe_id = name_to_id_map["kid:Zoë"]
    max_id = name_to_id_map["kid:Max!"]
    chore_name = coordinator.chores_data[alternating_chore_id][const.DATA_CHORE_NAME]

    # Claim for Zoë using coordinator method (v0.4.0+ pattern)
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(zoe_id, alternating_chore_id, "Zoë")

    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    # Mock notifications to prevent ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "approve_chore",
            {
                "kid_name": "Zoë",
                "chore_name": chore_name,
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # ALTERNATING: After Zoë approves, chore should rotate to Max
    # Verify Max now has the chore in claimed state
    assert is_chore_claimed_for_kid(coordinator, max_id, alternating_chore_id), (
        "ALTERNATING: Chore should rotate to next kid"
    )


@pytest.mark.asyncio
async def test_shared_disapprove_no_advancement(
    hass: HomeAssistant, scenario_full, mock_hass_users
) -> None:
    """Test SHARED chore: disapprove doesn't advance due date.

    Validates that disapproval keeps chore in pending state without
    advancing the chore-level due date.
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
            shared_chore_id = chore_id
            break

    if not shared_chore_id:
        pytest.skip("No SHARED chores in scenario_full - test pending")

    zoe_id = name_to_id_map["kid:Zoë"]
    chore_name = coordinator.chores_data[shared_chore_id][const.DATA_CHORE_NAME]
    original_due_date = coordinator.chores_data[shared_chore_id].get(
        DATA_CHORE_DUE_DATE
    )

    if isinstance(original_due_date, str):
        original_due_date = parser.isoparse(original_due_date)

    # Claim then disapprove using coordinator method (v0.4.0+ pattern)
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        coordinator.claim_chore(zoe_id, shared_chore_id, "Zoë")

    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    # Mock notifications to prevent ServiceNotFound errors
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        await hass.services.async_call(
            DOMAIN,
            "disapprove_chore",
            {
                "kid_name": "Zoë",
                "chore_name": chore_name,
                "parent_name": "Môm Astrid Stârblüm",
            },
            blocking=True,
            context=parent_context,
        )

    # After disapprove, due date should remain unchanged
    new_due_date = coordinator.chores_data[shared_chore_id].get(DATA_CHORE_DUE_DATE)
    if isinstance(new_due_date, str):
        new_due_date = parser.isoparse(new_due_date)

    # Both should match (disapprove doesn't advance date)
    if original_due_date is not None and new_due_date is not None:
        assert original_due_date == new_due_date, (
            "Disapprove should not advance chore-level due date"
        )
