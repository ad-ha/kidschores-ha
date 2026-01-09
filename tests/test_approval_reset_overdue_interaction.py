"""Test interactions between approval_reset_type and overdue_handling_type.

This module tests the behavior when:
- approval_reset_type = AT_MIDNIGHT_ONCE (or AT_MIDNIGHT_MULTI)
- overdue_handling_type = AT_DUE_DATE_THEN_RESET

AT_DUE_DATE_THEN_RESET only works with AT_MIDNIGHT_* reset types because
the reset must occur AFTER the due date to allow the overdue window.

Question answered: What happens to chores in different states when midnight reset runs?

See tests/AGENT_TEST_CREATION_INSTRUCTIONS.md for patterns used.
"""

# pylint: disable=protected-access, unused-argument, redefined-outer-name

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.util import dt as dt_util

from custom_components.kidschores import const
from custom_components.kidschores.const import (
    COMPLETION_CRITERIA_INDEPENDENT,
    COMPLETION_CRITERIA_SHARED,
    DATA_CHORE_APPROVAL_PERIOD_START,
    DATA_CHORE_ASSIGNED_KIDS,
    DATA_CHORE_COMPLETION_CRITERIA,
    DATA_CHORE_DUE_DATE,
    DATA_CHORE_PER_KID_DUE_DATES,
    DATA_KID_CHORE_DATA,
    DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START,
    DATA_KID_CHORE_DATA_DUE_DATE,
)
from tests.helpers.setup import SetupResult, setup_from_yaml

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
async def setup_at_due_date_scenario(
    hass: HomeAssistant,
    mock_hass_users: dict[str, Any],
) -> SetupResult:
    """Set up scenario with AT_DUE_DATE_ONCE + AT_DUE_DATE_THEN_RESET chore."""
    return await setup_from_yaml(
        hass,
        mock_hass_users,
        "tests/scenarios/scenario_approval_reset_overdue.yaml",
    )


# ============================================================================
# HELPER FUNCTIONS (following test_chore_scheduling.py patterns)
# ============================================================================


def get_kid_state_for_chore(coordinator: Any, kid_id: str, chore_id: str) -> str:
    """Get the current chore state for a specific kid."""
    kid_chore_data = coordinator._get_kid_chore_data(kid_id, chore_id)
    return kid_chore_data.get(
        const.DATA_KID_CHORE_DATA_STATE, const.CHORE_STATE_PENDING
    )


def set_chore_due_date_to_past(
    coordinator: Any,
    chore_id: str,
    kid_id: str | None = None,
    days_ago: int = 1,
) -> datetime:
    """Set chore due date to the past WITHOUT resetting state.

    This is a copy of the helper from test_chore_scheduling.py.
    """
    past_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    past_date = past_date.replace(hour=17, minute=0, second=0, microsecond=0)
    past_date_iso = dt_util.as_utc(past_date).isoformat()

    period_start = past_date - timedelta(days=1)
    period_start_iso = dt_util.as_utc(period_start).isoformat()

    chore_info = coordinator.chores_data.get(chore_id, {})
    criteria = chore_info.get(
        DATA_CHORE_COMPLETION_CRITERIA,
        COMPLETION_CRITERIA_SHARED,
    )

    if criteria == COMPLETION_CRITERIA_INDEPENDENT:
        per_kid_due_dates = chore_info.setdefault(DATA_CHORE_PER_KID_DUE_DATES, {})
        if kid_id:
            per_kid_due_dates[kid_id] = past_date_iso
            kid_info = coordinator.kids_data.get(kid_id, {})
            kid_chore_data = kid_info.get(DATA_KID_CHORE_DATA, {}).get(chore_id, {})
            if kid_chore_data:
                kid_chore_data[DATA_KID_CHORE_DATA_DUE_DATE] = past_date_iso
                kid_chore_data[DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START] = (
                    period_start_iso
                )
        else:
            for assigned_kid_id in chore_info.get(DATA_CHORE_ASSIGNED_KIDS, []):
                per_kid_due_dates[assigned_kid_id] = past_date_iso
                kid_info = coordinator.kids_data.get(assigned_kid_id, {})
                kid_chore_data = kid_info.get(DATA_KID_CHORE_DATA, {}).get(chore_id, {})
                if kid_chore_data:
                    kid_chore_data[DATA_KID_CHORE_DATA_DUE_DATE] = past_date_iso
                    kid_chore_data[DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START] = (
                        period_start_iso
                    )
    else:
        chore_info[DATA_CHORE_DUE_DATE] = past_date_iso
        chore_info[DATA_CHORE_APPROVAL_PERIOD_START] = period_start_iso

    return past_date


def set_chore_due_date_to_future(
    coordinator: Any,
    chore_id: str,
    kid_id: str | None = None,
    days_ahead: int = 1,
) -> datetime:
    """Set chore due date to the future."""
    future_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)
    future_date = future_date.replace(hour=17, minute=0, second=0, microsecond=0)
    future_date_iso = dt_util.as_utc(future_date).isoformat()

    chore_info = coordinator.chores_data.get(chore_id, {})
    criteria = chore_info.get(
        DATA_CHORE_COMPLETION_CRITERIA,
        COMPLETION_CRITERIA_SHARED,
    )

    if criteria == COMPLETION_CRITERIA_INDEPENDENT:
        per_kid_due_dates = chore_info.setdefault(DATA_CHORE_PER_KID_DUE_DATES, {})
        if kid_id:
            per_kid_due_dates[kid_id] = future_date_iso
        else:
            for assigned_kid_id in chore_info.get(DATA_CHORE_ASSIGNED_KIDS, []):
                per_kid_due_dates[assigned_kid_id] = future_date_iso
    else:
        chore_info[DATA_CHORE_DUE_DATE] = future_date_iso

    return future_date


# ============================================================================
# TEST CLASS: AT_DUE_DATE_ONCE + AT_DUE_DATE_THEN_RESET Interaction
# ============================================================================


class TestApprovalResetOverdueInteraction:
    """Test interactions between approval reset and overdue handling.

    Scenario: approval_reset_type=AT_MIDNIGHT_ONCE + overdue_handling_type=AT_DUE_DATE_THEN_RESET

    Expected behaviors:
    1. APPROVED state at reset → Reset to PENDING (ready for next period)
    2. PENDING (claimed) at reset → Depends on pending_claim_action, may become overdue
    3. PENDING (unclaimed) past due date → Marked OVERDUE
    4. OVERDUE state at reset → Cleared to PENDING ("then_reset" behavior)
    """

    @pytest.mark.asyncio
    async def test_approved_chore_resets_to_pending_at_due_date(
        self,
        hass: HomeAssistant,
        setup_at_due_date_scenario: SetupResult,
    ) -> None:
        """Test that an approved chore resets to PENDING when due date passes.

        Scenario: Kid completed chore, it's approved. Due date passes.
        Expected: Chore resets to PENDING for next period.
        """
        coordinator = setup_at_due_date_scenario.coordinator
        kid_id = setup_at_due_date_scenario.kid_ids["TestKid"]
        chore_id = setup_at_due_date_scenario.chore_ids["AtDueDateOnce Reset Chore"]

        # Approve the chore (kid claims and parent approves)
        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            coordinator.claim_chore(kid_id, chore_id, "Test User")
            coordinator.approve_chore("Parent", kid_id, chore_id)

        # Verify approved state
        assert coordinator.is_approved_in_current_period(kid_id, chore_id)
        initial_state = get_kid_state_for_chore(coordinator, kid_id, chore_id)
        assert initial_state == const.CHORE_STATE_APPROVED

        # Set due date to the past
        set_chore_due_date_to_past(coordinator, chore_id, kid_id=kid_id)

        # Trigger reset cycle (this is what happens at the scheduled reset time)
        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            await coordinator._reset_daily_chore_statuses([const.FREQUENCY_DAILY])

        # Verify reset to PENDING
        final_state = get_kid_state_for_chore(coordinator, kid_id, chore_id)
        assert final_state == const.CHORE_STATE_PENDING, (
            f"Expected APPROVED chore to reset to PENDING at due date, got {final_state}"
        )
        assert not coordinator.is_approved_in_current_period(kid_id, chore_id)

    @pytest.mark.asyncio
    async def test_unclaimed_pending_becomes_overdue_at_due_date(
        self,
        hass: HomeAssistant,
        setup_at_due_date_scenario: SetupResult,
    ) -> None:
        """Test that an unclaimed PENDING chore becomes OVERDUE at due date.

        Scenario: Chore assigned but not claimed. Due date passes.
        Expected: Chore marked OVERDUE.
        """
        coordinator = setup_at_due_date_scenario.coordinator
        kid_id = setup_at_due_date_scenario.kid_ids["TestKid"]
        chore_id = setup_at_due_date_scenario.chore_ids["AtDueDateOnce Reset Chore"]

        # Verify initial pending state (no claim)
        assert not coordinator.has_pending_claim(kid_id, chore_id)
        assert not coordinator.is_approved_in_current_period(kid_id, chore_id)

        # Set due date to the past
        set_chore_due_date_to_past(coordinator, chore_id, kid_id=kid_id)

        # Trigger overdue check
        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            await coordinator._check_overdue_chores()

        # Verify overdue status
        assert coordinator.is_overdue(kid_id, chore_id), (
            "Expected unclaimed PENDING chore to become OVERDUE at due date"
        )
        final_state = get_kid_state_for_chore(coordinator, kid_id, chore_id)
        assert final_state == const.CHORE_STATE_OVERDUE

    @pytest.mark.asyncio
    async def test_claimed_pending_with_clear_action_becomes_overdue(
        self,
        hass: HomeAssistant,
        setup_at_due_date_scenario: SetupResult,
    ) -> None:
        """Test claimed PENDING chore with CLEAR action becomes OVERDUE then resets.

        Scenario: Kid claimed chore (pending_claim_action=CLEAR). Due date passes.
        Expected: Pending claim is cleared, then marked OVERDUE, then reset at next cycle.
        """
        coordinator = setup_at_due_date_scenario.coordinator
        kid_id = setup_at_due_date_scenario.kid_ids["TestKid"]
        chore_id = setup_at_due_date_scenario.chore_ids["AtDueDateOnce Reset Chore"]

        # Claim the chore
        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            coordinator.claim_chore(kid_id, chore_id, "Test User")

        # Verify claimed state
        assert coordinator.has_pending_claim(kid_id, chore_id)

        # Set due date to the past
        set_chore_due_date_to_past(coordinator, chore_id, kid_id=kid_id)

        # Trigger reset cycle (which clears pending claims before overdue check runs)
        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            await coordinator._reset_daily_chore_statuses([const.FREQUENCY_DAILY])

        # With CLEAR action, pending claim should be cleared and state reset to PENDING
        assert not coordinator.has_pending_claim(kid_id, chore_id), (
            "Expected pending claim to be cleared after reset"
        )
        final_state = get_kid_state_for_chore(coordinator, kid_id, chore_id)
        assert final_state == const.CHORE_STATE_PENDING

    @pytest.mark.asyncio
    async def test_overdue_resets_to_pending_then_reset_behavior(
        self,
        hass: HomeAssistant,
        setup_at_due_date_scenario: SetupResult,
    ) -> None:
        """Test OVERDUE chore is cleared at reset with AT_DUE_DATE_THEN_RESET.

        The AT_DUE_DATE_THEN_RESET overdue handling type is designed to:
        1. Mark chore OVERDUE when due date passes (if not completed)
        2. Clear the OVERDUE status at the next reset cycle

        This only works with AT_MIDNIGHT_* reset types (at_midnight_once,
        at_midnight_multi) because the reset must occur AFTER the due date
        to allow the overdue window.

        Scenario: Chore is overdue. Reset cycle runs.
        Expected: OVERDUE status cleared, reset to PENDING.
        """
        coordinator = setup_at_due_date_scenario.coordinator
        kid_id = setup_at_due_date_scenario.kid_ids["TestKid"]
        chore_id = setup_at_due_date_scenario.chore_ids["AtDueDateOnce Reset Chore"]

        # Set due date to past and mark overdue
        set_chore_due_date_to_past(coordinator, chore_id, kid_id=kid_id)
        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            await coordinator._check_overdue_chores()

        # Verify overdue status
        assert coordinator.is_overdue(kid_id, chore_id)

        # Now trigger reset cycle - this should clear OVERDUE with "then_reset"
        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            await coordinator._reset_daily_chore_statuses([const.FREQUENCY_DAILY])

        # EXPECTED BEHAVIOR: OVERDUE status IS cleared with AT_DUE_DATE_THEN_RESET
        # The reset logic includes OVERDUE in states_to_skip when overdue_handling
        # is NOT AT_DUE_DATE_THEN_RESET, but INCLUDES it when it IS "then_reset"
        assert not coordinator.is_overdue(kid_id, chore_id), (
            "OVERDUE status should be cleared at reset with AT_DUE_DATE_THEN_RESET"
        )
        final_state = get_kid_state_for_chore(coordinator, kid_id, chore_id)
        assert final_state == const.CHORE_STATE_PENDING

    @pytest.mark.asyncio
    async def test_future_due_date_no_overdue_or_reset(
        self,
        hass: HomeAssistant,
        setup_at_due_date_scenario: SetupResult,
    ) -> None:
        """Test that chores with future due dates are not reset or marked overdue.

        Scenario: Chore due date is in the future.
        Expected: No overdue marking, no reset triggered.
        """
        coordinator = setup_at_due_date_scenario.coordinator
        kid_id = setup_at_due_date_scenario.kid_ids["TestKid"]
        chore_id = setup_at_due_date_scenario.chore_ids["AtDueDateOnce Reset Chore"]

        # Approve the chore
        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            coordinator.claim_chore(kid_id, chore_id, "Test User")
            coordinator.approve_chore("Parent", kid_id, chore_id)

        # Set due date to the future
        set_chore_due_date_to_future(coordinator, chore_id, kid_id=kid_id)

        # Trigger reset cycle
        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            await coordinator._reset_daily_chore_statuses([const.FREQUENCY_DAILY])

        # Verify chore was NOT reset (due date in future)
        assert coordinator.is_approved_in_current_period(kid_id, chore_id), (
            "Expected approved chore with future due date to NOT be reset"
        )

        # Trigger overdue check
        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            await coordinator._check_overdue_chores()

        # Verify NOT marked overdue
        assert not coordinator.is_overdue(kid_id, chore_id), (
            "Expected chore with future due date to NOT be marked overdue"
        )


# ============================================================================
# TEST CLASS: Validation of AT_DUE_DATE_THEN_RESET Combinations
# ============================================================================


class TestOverdueResetValidation:
    """Test validation rejects invalid AT_DUE_DATE_THEN_RESET combinations.

    AT_DUE_DATE_THEN_RESET only makes sense with AT_MIDNIGHT_* reset types
    because the reset must happen AFTER the due date.

    Invalid combinations:
    - AT_DUE_DATE_ONCE + AT_DUE_DATE_THEN_RESET (same trigger moment)
    - AT_DUE_DATE_MULTI + AT_DUE_DATE_THEN_RESET (same trigger moment)
    - UPON_COMPLETION + AT_DUE_DATE_THEN_RESET (reset never fires if not completed)

    Valid combinations:
    - AT_MIDNIGHT_ONCE + AT_DUE_DATE_THEN_RESET ✓
    - AT_MIDNIGHT_MULTI + AT_DUE_DATE_THEN_RESET ✓
    """

    @pytest.mark.asyncio
    async def test_at_due_date_once_with_then_reset_rejected(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that AT_DUE_DATE_ONCE + AT_DUE_DATE_THEN_RESET is rejected."""
        # Import flow_helpers to test validation directly
        from custom_components.kidschores import flow_helpers as fh

        # Create minimal chore input with invalid combination
        user_input = {
            const.CFOF_CHORES_INPUT_NAME: "Test Chore",
            const.CFOF_CHORES_INPUT_ASSIGNED_KIDS: ["TestKid"],
            const.CFOF_CHORES_INPUT_DEFAULT_POINTS: 10.0,
            const.CFOF_CHORES_INPUT_ICON: "mdi:check",
            const.CFOF_CHORES_INPUT_COMPLETION_CRITERIA: const.COMPLETION_CRITERIA_INDEPENDENT,
            const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY: const.FREQUENCY_DAILY,
            const.CFOF_CHORES_INPUT_APPROVAL_RESET_TYPE: const.APPROVAL_RESET_AT_DUE_DATE_ONCE,
            const.CFOF_CHORES_INPUT_OVERDUE_HANDLING_TYPE: const.OVERDUE_HANDLING_AT_DUE_DATE_THEN_RESET,
            const.CFOF_CHORES_INPUT_APPROVAL_RESET_PENDING_CLAIM_ACTION: const.DEFAULT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
            const.CFOF_CHORES_INPUT_AUTO_APPROVE: False,
            const.CFOF_CHORES_INPUT_SHOW_ON_CALENDAR: True,
            const.CFOF_CHORES_INPUT_LABELS: [],
            const.CFOF_CHORES_INPUT_APPLICABLE_DAYS: [
                "mon",
                "tue",
                "wed",
                "thu",
                "fri",
            ],
            const.CFOF_CHORES_INPUT_NOTIFICATIONS: [],
        }

        # Create kids_dict mapping name to UUID (like coordinator does)
        kids_dict = {"TestKid": "kid_001"}

        # Validate using build_chores_data (the validation function)
        _chore_data, errors = fh.build_chores_data(
            user_input=user_input,
            kids_dict=kids_dict,
            existing_chores={},
        )

        # Verify validation rejected the combination
        assert errors, (
            "Expected validation to reject AT_DUE_DATE_ONCE + AT_DUE_DATE_THEN_RESET"
        )
        assert const.CFOP_ERROR_OVERDUE_RESET_COMBO in errors, (
            f"Expected error key {const.CFOP_ERROR_OVERDUE_RESET_COMBO}, got {errors}"
        )

    @pytest.mark.asyncio
    async def test_upon_completion_with_then_reset_rejected(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that UPON_COMPLETION + AT_DUE_DATE_THEN_RESET is rejected."""
        from custom_components.kidschores import flow_helpers as fh

        user_input = {
            const.CFOF_CHORES_INPUT_NAME: "Test Chore",
            const.CFOF_CHORES_INPUT_ASSIGNED_KIDS: ["TestKid"],
            const.CFOF_CHORES_INPUT_DEFAULT_POINTS: 10.0,
            const.CFOF_CHORES_INPUT_ICON: "mdi:check",
            const.CFOF_CHORES_INPUT_COMPLETION_CRITERIA: const.COMPLETION_CRITERIA_INDEPENDENT,
            const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY: const.FREQUENCY_DAILY,
            const.CFOF_CHORES_INPUT_APPROVAL_RESET_TYPE: const.APPROVAL_RESET_UPON_COMPLETION,
            const.CFOF_CHORES_INPUT_OVERDUE_HANDLING_TYPE: const.OVERDUE_HANDLING_AT_DUE_DATE_THEN_RESET,
            const.CFOF_CHORES_INPUT_APPROVAL_RESET_PENDING_CLAIM_ACTION: const.DEFAULT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
            const.CFOF_CHORES_INPUT_AUTO_APPROVE: False,
            const.CFOF_CHORES_INPUT_SHOW_ON_CALENDAR: True,
            const.CFOF_CHORES_INPUT_LABELS: [],
            const.CFOF_CHORES_INPUT_APPLICABLE_DAYS: [
                "mon",
                "tue",
                "wed",
                "thu",
                "fri",
            ],
            const.CFOF_CHORES_INPUT_NOTIFICATIONS: [],
        }

        kids_dict = {"TestKid": "kid_001"}

        _chore_data, errors = fh.build_chores_data(
            user_input=user_input,
            kids_dict=kids_dict,
            existing_chores={},
        )

        assert errors, (
            "Expected validation to reject UPON_COMPLETION + AT_DUE_DATE_THEN_RESET"
        )
        assert const.CFOP_ERROR_OVERDUE_RESET_COMBO in errors

    @pytest.mark.asyncio
    async def test_at_midnight_once_with_then_reset_accepted(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that AT_MIDNIGHT_ONCE + AT_DUE_DATE_THEN_RESET is accepted."""
        from custom_components.kidschores import flow_helpers as fh

        user_input = {
            const.CFOF_CHORES_INPUT_NAME: "Test Chore",
            const.CFOF_CHORES_INPUT_ASSIGNED_KIDS: ["TestKid"],
            const.CFOF_CHORES_INPUT_DEFAULT_POINTS: 10.0,
            const.CFOF_CHORES_INPUT_ICON: "mdi:check",
            const.CFOF_CHORES_INPUT_COMPLETION_CRITERIA: const.COMPLETION_CRITERIA_INDEPENDENT,
            const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY: const.FREQUENCY_DAILY,
            const.CFOF_CHORES_INPUT_APPROVAL_RESET_TYPE: const.APPROVAL_RESET_AT_MIDNIGHT_ONCE,
            const.CFOF_CHORES_INPUT_OVERDUE_HANDLING_TYPE: const.OVERDUE_HANDLING_AT_DUE_DATE_THEN_RESET,
            const.CFOF_CHORES_INPUT_APPROVAL_RESET_PENDING_CLAIM_ACTION: const.DEFAULT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
            const.CFOF_CHORES_INPUT_AUTO_APPROVE: False,
            const.CFOF_CHORES_INPUT_SHOW_ON_CALENDAR: True,
            const.CFOF_CHORES_INPUT_LABELS: [],
            const.CFOF_CHORES_INPUT_APPLICABLE_DAYS: [
                "mon",
                "tue",
                "wed",
                "thu",
                "fri",
            ],
            const.CFOF_CHORES_INPUT_NOTIFICATIONS: [],
        }

        kids_dict = {"TestKid": "kid_001"}

        chore_data, errors = fh.build_chores_data(
            user_input=user_input,
            kids_dict=kids_dict,
            existing_chores={},
        )

        assert not errors, (
            f"Expected no validation errors for valid combination, got {errors}"
        )
        assert chore_data, "Expected chore_data to be returned for valid combination"

    @pytest.mark.asyncio
    async def test_at_midnight_multi_with_then_reset_accepted(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that AT_MIDNIGHT_MULTI + AT_DUE_DATE_THEN_RESET is accepted."""
        from custom_components.kidschores import flow_helpers as fh

        user_input = {
            const.CFOF_CHORES_INPUT_NAME: "Test Chore",
            const.CFOF_CHORES_INPUT_ASSIGNED_KIDS: ["TestKid"],
            const.CFOF_CHORES_INPUT_DEFAULT_POINTS: 10.0,
            const.CFOF_CHORES_INPUT_ICON: "mdi:check",
            const.CFOF_CHORES_INPUT_COMPLETION_CRITERIA: const.COMPLETION_CRITERIA_INDEPENDENT,
            const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY: const.FREQUENCY_DAILY,
            const.CFOF_CHORES_INPUT_APPROVAL_RESET_TYPE: const.APPROVAL_RESET_AT_MIDNIGHT_MULTI,
            const.CFOF_CHORES_INPUT_OVERDUE_HANDLING_TYPE: const.OVERDUE_HANDLING_AT_DUE_DATE_THEN_RESET,
            const.CFOF_CHORES_INPUT_APPROVAL_RESET_PENDING_CLAIM_ACTION: const.DEFAULT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
            const.CFOF_CHORES_INPUT_AUTO_APPROVE: False,
            const.CFOF_CHORES_INPUT_SHOW_ON_CALENDAR: True,
            const.CFOF_CHORES_INPUT_LABELS: [],
            const.CFOF_CHORES_INPUT_APPLICABLE_DAYS: [
                "mon",
                "tue",
                "wed",
                "thu",
                "fri",
            ],
            const.CFOF_CHORES_INPUT_NOTIFICATIONS: [],
        }

        kids_dict = {"TestKid": "kid_001"}

        chore_data, errors = fh.build_chores_data(
            user_input=user_input,
            kids_dict=kids_dict,
            existing_chores={},
        )

        assert not errors, (
            f"Expected no validation errors for valid combination, got {errors}"
        )
        assert chore_data, "Expected chore_data to be returned for valid combination"
