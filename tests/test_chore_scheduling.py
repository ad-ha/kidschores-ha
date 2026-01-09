"""Chore scheduling tests - due dates, overdue detection, and frequency behavior. CLS

This module tests:
1. Due date loading from YAML scenario (with relative past/future dates)
2. Overdue state detection based on due dates and overdue_handling_type
3. Frequency effects on due date behavior (once vs recurring)
4. Due date changes after chore approval (rescheduling behavior)

Phase 3 of the Chore Workflow Testing initiative.
See: docs/in-process/CHORE_WORKFLOW_TESTING_IN-PROCESS.md

Test Organization:
- TestDueDateLoading: Verify due dates load correctly from YAML
- TestOverdueDetection: Verify overdue state based on due date and handling type
- TestFrequencyEffects: Verify once vs daily/weekly behavior
"""

# pylint: disable=protected-access
# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument

from datetime import datetime, timezone
from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kidschores import kc_helpers as kh
from tests.helpers import (
    APPROVAL_RESET_AT_DUE_DATE_MULTI,
    APPROVAL_RESET_AT_DUE_DATE_ONCE,
    APPROVAL_RESET_AT_MIDNIGHT_MULTI,
    # Approval reset types
    APPROVAL_RESET_AT_MIDNIGHT_ONCE,
    APPROVAL_RESET_PENDING_CLAIM_AUTO_APPROVE,
    APPROVAL_RESET_PENDING_CLAIM_CLEAR,
    # Pending claim actions
    APPROVAL_RESET_PENDING_CLAIM_HOLD,
    APPROVAL_RESET_UPON_COMPLETION,
    # Chore states
    CHORE_STATE_APPROVED,
    CHORE_STATE_CLAIMED,
    CHORE_STATE_OVERDUE,
    CHORE_STATE_PENDING,
    # Completion criteria
    COMPLETION_CRITERIA_INDEPENDENT,
    COMPLETION_CRITERIA_SHARED,
    DATA_CHORE_APPROVAL_PERIOD_START,
    DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION,
    DATA_CHORE_APPROVAL_RESET_TYPE,
    DATA_CHORE_ASSIGNED_KIDS,
    DATA_CHORE_COMPLETION_CRITERIA,
    DATA_CHORE_DEFAULT_POINTS,
    DATA_CHORE_DUE_DATE,
    # Data keys - chore
    DATA_CHORE_NAME,
    DATA_CHORE_OVERDUE_HANDLING_TYPE,
    DATA_CHORE_PER_KID_DUE_DATES,
    DATA_CHORE_RECURRING_FREQUENCY,
    DATA_KID_CHORE_DATA,
    DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START,
    DATA_KID_CHORE_DATA_DUE_DATE,
    DATA_KID_CHORE_DATA_STATE,
    # Data keys - kid
    DATA_KID_NAME,
    DATA_KID_POINTS,
    # Frequencies
    FREQUENCY_DAILY,
    FREQUENCY_NONE,
    FREQUENCY_WEEKLY,
    # Overdue handling types
    OVERDUE_HANDLING_AT_DUE_DATE,
    OVERDUE_HANDLING_AT_DUE_DATE_THEN_RESET,
    OVERDUE_HANDLING_NEVER_OVERDUE,
    # Translation keys
    TRANS_KEY_ERROR_CHORE_ALREADY_APPROVED,
    # Setup
    SetupResult,
    setup_from_yaml,
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def set_chore_due_date_to_past(
    coordinator: Any,
    chore_id: str,
    kid_id: str | None = None,
    days_ago: int = 1,
) -> datetime:
    """Set a chore's due date to a past date for testing overdue behavior.

    ╔══════════════════════════════════════════════════════════════════════════╗
    ║  WHY THIS HELPER EXISTS                                                  ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║  coordinator.set_chore_due_date() INTENTIONALLY:                         ║
    ║    1. Resets chore state to PENDING                                      ║
    ║    2. Clears pending_claim_count to 0                                    ║
    ║    3. Resets approval_period_start to now                                ║
    ║                                                                          ║
    ║  This is correct behavior for production (changing due date = new period)║
    ║  but breaks tests that need to simulate "time passing" while PRESERVING  ║
    ║  current claim/approval state (e.g., testing claimed chores don't        ║
    ║  become overdue).                                                        ║
    ║                                                                          ║
    ║  This helper directly modifies the data structures to:                   ║
    ║    - Set due date to the past                                            ║
    ║    - Set approval_period_start BEFORE the past due date                  ║
    ║    - NOT touch state or pending_claim_count                              ║
    ╚══════════════════════════════════════════════════════════════════════════╝

    Storage locations by completion_criteria:
      SHARED:      due_date at chore level, approval_period_start at chore level
      INDEPENDENT: due_date per-kid, approval_period_start per-kid in kid_chore_data

    Args:
        coordinator: KidsChoresDataCoordinator
        chore_id: The chore's internal UUID
        kid_id: For independent chores, the kid's UUID (or None to set all)
        days_ago: How many days in the past (default: 1 = yesterday)

    Returns:
        The past datetime that was set
    """
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    # Calculate past due date
    past_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    past_date = past_date.replace(hour=17, minute=0, second=0, microsecond=0)
    past_date_iso = dt_util.as_utc(past_date).isoformat()

    # Approval period start must be BEFORE the past due date
    # (so any claims made "now" are valid for this period)
    period_start = past_date - timedelta(days=1)
    period_start_iso = dt_util.as_utc(period_start).isoformat()

    chore_info = coordinator.chores_data.get(chore_id, {})
    criteria = chore_info.get(
        DATA_CHORE_COMPLETION_CRITERIA,
        COMPLETION_CRITERIA_SHARED,
    )

    # Update due date and approval_period_start WITHOUT resetting state
    if criteria == COMPLETION_CRITERIA_INDEPENDENT:
        # INDEPENDENT: due date and approval_period_start are per-kid
        per_kid_due_dates = chore_info.setdefault(DATA_CHORE_PER_KID_DUE_DATES, {})
        if kid_id:
            # Single kid
            per_kid_due_dates[kid_id] = past_date_iso
            kid_info = coordinator.kids_data.get(kid_id, {})
            kid_chore_data = kid_info.get(DATA_KID_CHORE_DATA, {}).get(chore_id, {})
            if kid_chore_data:
                kid_chore_data[DATA_KID_CHORE_DATA_DUE_DATE] = past_date_iso
                kid_chore_data[DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START] = (
                    period_start_iso
                )
        else:
            # All assigned kids
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
        # SHARED: due date and approval_period_start are at chore level
        chore_info[DATA_CHORE_DUE_DATE] = past_date_iso
        chore_info[DATA_CHORE_APPROVAL_PERIOD_START] = period_start_iso

    return past_date


def get_chore_due_date(
    coordinator: Any,
    chore_id: str,
) -> datetime | None:
    """Get the due date for a chore (global/template level).

    For INDEPENDENT chores, this is the template; per-kid dates are in per_kid_due_dates.
    For SHARED chores, this is the authoritative due date.

    Args:
        coordinator: KidsChoresDataCoordinator
        chore_id: The chore's internal UUID

    Returns:
        datetime object if due date exists, None otherwise
    """
    chore_info = coordinator.chores_data.get(chore_id, {})
    due_str = chore_info.get(DATA_CHORE_DUE_DATE)
    if not due_str:
        return None
    return kh.parse_datetime_to_utc(due_str)


def get_kid_due_date(
    coordinator: Any,
    kid_id: str,
    chore_id: str,
) -> datetime | None:
    """Get the due date for a chore for a specific kid.

    For INDEPENDENT chores, reads from per_kid_due_dates.
    For SHARED chores, falls back to chore-level due date.

    Args:
        coordinator: KidsChoresDataCoordinator
        kid_id: The kid's internal UUID
        chore_id: The chore's internal UUID

    Returns:
        datetime object if due date exists, None otherwise
    """
    chore_info = coordinator.chores_data.get(chore_id, {})

    # Check per-kid due dates first (INDEPENDENT chores)
    per_kid_due_dates = chore_info.get(DATA_CHORE_PER_KID_DUE_DATES, {})
    if kid_id in per_kid_due_dates:
        due_str = per_kid_due_dates[kid_id]
        if due_str:
            return kh.parse_datetime_to_utc(due_str)

    # Fall back to chore-level due date (SHARED chores or template)
    due_str = chore_info.get(DATA_CHORE_DUE_DATE)
    if not due_str:
        return None
    return kh.parse_datetime_to_utc(due_str)


def get_kid_chore_state(
    coordinator: Any,
    kid_id: str,
    chore_id: str,
) -> str:
    """Get the current state of a chore for a specific kid.

    Args:
        coordinator: KidsChoresDataCoordinator
        kid_id: The kid's internal UUID
        chore_id: The chore's internal UUID

    Returns:
        State string (e.g., 'pending', 'claimed', 'approved', 'overdue')
    """
    kid_data = coordinator.kids_data.get(kid_id, {})
    chore_data = kid_data.get(DATA_KID_CHORE_DATA, {})
    per_chore = chore_data.get(chore_id, {})
    return per_chore.get(DATA_KID_CHORE_DATA_STATE, CHORE_STATE_PENDING)


def get_chore_by_name(
    coordinator: Any,
    name: str,
) -> tuple[str, dict[str, Any]] | None:
    """Find a chore by name.

    Args:
        coordinator: KidsChoresDataCoordinator
        name: Chore name to find

    Returns:
        Tuple of (chore_id, chore_info) or None if not found
    """
    for chore_id, chore_info in coordinator.chores_data.items():
        if chore_info.get(DATA_CHORE_NAME) == name:
            return chore_id, chore_info
    return None


def get_kid_by_name(
    coordinator: Any,
    name: str,
) -> tuple[str, dict[str, Any]] | None:
    """Find a kid by name.

    Args:
        coordinator: KidsChoresDataCoordinator
        name: Kid name to find

    Returns:
        Tuple of (kid_id, kid_info) or None if not found
    """
    for kid_id, kid_info in coordinator.kids_data.items():
        if kid_info.get(DATA_KID_NAME) == name:
            return kid_id, kid_info
    return None


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
async def scheduling_scenario(
    hass: HomeAssistant,
    mock_hass_users: dict[str, Any],
) -> SetupResult:
    """Load scheduling scenario using modern setup_from_yaml().

    Returns:
        SetupResult with config_entry, coordinator, kid_ids, chore_ids maps
    """
    return await setup_from_yaml(
        hass,
        mock_hass_users,
        "tests/scenarios/scenario_scheduling.yaml",
    )


# =============================================================================
# TEST CLASS: Due Date Loading
# =============================================================================


class TestDueDateLoading:
    """Test that due dates load correctly from YAML scenario."""

    @pytest.mark.asyncio
    async def test_future_due_date_is_in_future(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test that chores with due_date_relative='future' have future due dates."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        # "Reset Midnight Once" has due_date_relative: "future"
        chore_id = chore_map["Reset Midnight Once"]
        due_date = get_kid_due_date(coordinator, zoe_id, chore_id)

        assert due_date is not None, "Due date should be set"
        now_utc = datetime.now(timezone.utc)
        assert due_date > now_utc, f"Due date {due_date} should be in the future"

    @pytest.mark.asyncio
    async def test_past_due_date_is_in_past(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test that we can set a due date to the past via coordinator."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        # "Overdue At Due Date" - set due date to past via coordinator
        # (Config flow rejects past dates, so we modify after setup)
        chore_id = chore_map["Overdue At Due Date"]
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        due_date = get_kid_due_date(coordinator, zoe_id, chore_id)

        assert due_date is not None, "Due date should be set"
        now_utc = datetime.now(timezone.utc)
        assert due_date < now_utc, f"Due date {due_date} should be in the past"

    @pytest.mark.asyncio
    async def test_all_scheduling_chores_have_due_dates(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test that all chores in scheduling scenario have due dates set."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        for chore_name, chore_id in chore_map.items():
            due_date = get_kid_due_date(coordinator, zoe_id, chore_id)
            assert due_date is not None, f"Chore '{chore_name}' should have a due date"

    @pytest.mark.asyncio
    async def test_due_date_is_timezone_aware(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test that due dates are timezone-aware (UTC)."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Reset Midnight Once"]
        due_date = get_kid_due_date(coordinator, zoe_id, chore_id)

        assert due_date is not None
        assert due_date.tzinfo is not None, "Due date should be timezone-aware"


# =============================================================================
# TEST CLASS: Overdue Detection
# =============================================================================


class TestOverdueDetection:
    """Test overdue state detection based on due dates and overdue_handling_type."""

    @pytest.mark.asyncio
    async def test_past_due_at_due_date_is_overdue(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: overdue_handling_type='at_due_date' with past due date → OVERDUE state.

        "Overdue At Due Date" - set due date to past via coordinator, then check overdue.
        """
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Overdue At Due Date"]

        # Set due date to past (config flow rejects past dates)
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Trigger overdue check by calling the coordinator's check method
        await coordinator._check_overdue_chores()

        # Verify state is OVERDUE
        state = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state == CHORE_STATE_OVERDUE, (
            f"Chore with past due date and at_due_date handling should be OVERDUE, got {state}"
        )

        # Also verify using coordinator's is_overdue method
        assert coordinator.is_overdue(zoe_id, chore_id) is True

    @pytest.mark.asyncio
    async def test_past_due_never_overdue_stays_pending(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: overdue_handling_type='never_overdue' with past due date → stays PENDING.

        "Overdue Never" - set to past but should NOT become overdue.
        """
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Overdue Never"]

        # Set due date to past (config flow rejects past dates)
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Trigger overdue check
        await coordinator._check_overdue_chores()

        # Verify state is still PENDING (not overdue)
        state = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state == CHORE_STATE_PENDING, (
            f"Chore with never_overdue should stay PENDING, got {state}"
        )

        # Also verify using coordinator's is_overdue method
        assert coordinator.is_overdue(zoe_id, chore_id) is False

    @pytest.mark.asyncio
    async def test_future_due_not_overdue(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: Future due date should NOT be overdue."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Reset Midnight Once"]

        # Trigger overdue check
        await coordinator._check_overdue_chores()

        # Verify state is PENDING (not overdue)
        state = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state == CHORE_STATE_PENDING, (
            f"Chore with future due date should be PENDING, got {state}"
        )

        assert coordinator.is_overdue(zoe_id, chore_id) is False

    @pytest.mark.asyncio
    async def test_weekly_overdue_is_detected(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: Weekly chore with past due date becomes overdue.

        "Weekly Overdue" - set to past and verify it becomes overdue.
        """
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Weekly Overdue"]

        # Set due date to past (config flow rejects past dates)
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=3)

        # Trigger overdue check
        await coordinator._check_overdue_chores()

        # Verify state is OVERDUE
        state = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state == CHORE_STATE_OVERDUE, (
            f"Weekly chore with past due date should be OVERDUE, got {state}"
        )


# =============================================================================
# TEST CLASS: Frequency Effects
# =============================================================================


class TestFrequencyEffects:
    """Test frequency-specific behavior for due dates and chore lifecycle."""

    @pytest.mark.asyncio
    async def test_one_time_chore_has_due_date(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: One-time chore has a due date set."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["One Time Task"]

        # Verify due date exists
        due_date = get_kid_due_date(coordinator, zoe_id, chore_id)
        assert due_date is not None, "One-time chore should have a due date"

        # Verify frequency (recurring_frequency: "none" for one-time chores)
        chore_info = coordinator.chores_data.get(chore_id, {})
        frequency = chore_info.get(DATA_CHORE_RECURRING_FREQUENCY)
        assert frequency == FREQUENCY_NONE, (
            f"One-time chore should have 'none' frequency, got {frequency}"
        )

    @pytest.mark.asyncio
    async def test_daily_chore_frequency(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: Daily chores have correct frequency setting."""
        coordinator = scheduling_scenario.coordinator
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Reset Midnight Once"]
        chore_info = coordinator.chores_data.get(chore_id, {})

        frequency = chore_info.get(DATA_CHORE_RECURRING_FREQUENCY)
        assert frequency == FREQUENCY_DAILY, (
            f"Daily chore should have 'daily' frequency, got {frequency}"
        )

    @pytest.mark.asyncio
    async def test_weekly_chore_frequency(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: Weekly chores have correct frequency setting."""
        coordinator = scheduling_scenario.coordinator
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Reset Due Date Once"]
        chore_info = coordinator.chores_data.get(chore_id, {})

        frequency = chore_info.get(DATA_CHORE_RECURRING_FREQUENCY)
        assert frequency == FREQUENCY_WEEKLY


# =============================================================================
# TEST CLASS: Chore Configuration Verification
# =============================================================================


class TestChoreConfigurationVerification:
    """Verify that scheduling scenario chores have correct configuration."""

    @pytest.mark.asyncio
    async def test_approval_reset_types_loaded(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: All 5 approval reset types are loaded from scenario."""
        coordinator = scheduling_scenario.coordinator
        chore_map = scheduling_scenario.chore_ids

        expected = {
            "Reset Midnight Once": APPROVAL_RESET_AT_MIDNIGHT_ONCE,
            "Reset Midnight Multi": APPROVAL_RESET_AT_MIDNIGHT_MULTI,
            "Reset Due Date Once": APPROVAL_RESET_AT_DUE_DATE_ONCE,
            "Reset Due Date Multi": APPROVAL_RESET_AT_DUE_DATE_MULTI,
            "Reset Upon Completion": APPROVAL_RESET_UPON_COMPLETION,
        }

        for chore_name, expected_type in expected.items():
            chore_id = chore_map[chore_name]
            chore_info = coordinator.chores_data.get(chore_id, {})
            actual_type = chore_info.get(DATA_CHORE_APPROVAL_RESET_TYPE)
            assert actual_type == expected_type, (
                f"'{chore_name}' should have approval_reset_type={expected_type}, got {actual_type}"
            )

    @pytest.mark.asyncio
    async def test_overdue_handling_types_loaded(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: All 3 overdue handling types are loaded from scenario."""
        coordinator = scheduling_scenario.coordinator
        chore_map = scheduling_scenario.chore_ids

        expected = {
            "Overdue At Due Date": OVERDUE_HANDLING_AT_DUE_DATE,
            "Overdue Never": OVERDUE_HANDLING_NEVER_OVERDUE,
            "Overdue Then Reset": OVERDUE_HANDLING_AT_DUE_DATE_THEN_RESET,
        }

        for chore_name, expected_type in expected.items():
            chore_id = chore_map[chore_name]
            chore_info = coordinator.chores_data.get(chore_id, {})
            actual_type = chore_info.get(DATA_CHORE_OVERDUE_HANDLING_TYPE)
            assert actual_type == expected_type, (
                f"'{chore_name}' should have overdue_handling_type={expected_type}, got {actual_type}"
            )

    @pytest.mark.asyncio
    async def test_pending_claim_actions_loaded(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: All 3 pending claim actions are loaded from scenario."""
        coordinator = scheduling_scenario.coordinator
        chore_map = scheduling_scenario.chore_ids

        expected = {
            "Pending Hold": APPROVAL_RESET_PENDING_CLAIM_HOLD,
            "Pending Clear": APPROVAL_RESET_PENDING_CLAIM_CLEAR,
            "Pending Auto Approve": APPROVAL_RESET_PENDING_CLAIM_AUTO_APPROVE,
        }

        for chore_name, expected_type in expected.items():
            chore_id = chore_map[chore_name]
            chore_info = coordinator.chores_data.get(chore_id, {})
            actual_type = chore_info.get(DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION)
            assert actual_type == expected_type, (
                f"'{chore_name}' should have pending_claim_action={expected_type}, got {actual_type}"
            )

    @pytest.mark.asyncio
    async def test_scenario_has_14_chores(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: Scheduling scenario has exactly 14 chores."""
        coordinator = scheduling_scenario.coordinator
        chore_map = scheduling_scenario.chore_ids

        assert len(chore_map) == 14, f"Expected 14 chores, got {len(chore_map)}"
        assert len(coordinator.chores_data) == 14

    @pytest.mark.asyncio
    async def test_all_chores_assigned_to_zoe(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: All chores in scheduling scenario are assigned to Zoë."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        for chore_name, chore_id in chore_map.items():
            chore_info = coordinator.chores_data.get(chore_id, {})
            assigned = chore_info.get(DATA_CHORE_ASSIGNED_KIDS, [])
            assert zoe_id in assigned, f"'{chore_name}' should be assigned to Zoë"


# =============================================================================
# TEST CLASS: Approval Reset Tests (Phase 4)
# =============================================================================


class TestApprovalResetAtMidnightOnce:
    """Test AT_MIDNIGHT_ONCE approval reset behavior.

    Expected behavior:
    - Only ONE approval allowed per approval period (midnight-to-midnight)
    - Due date should NOT change on approval
    - Due date should be rescheduled at midnight reset
    - State should remain APPROVED until midnight reset

    KNOWN BUG: Currently, approval reschedules due date immediately.
    These tests document expected behavior and will reveal the bug.
    """

    @pytest.mark.asyncio
    async def test_at_midnight_once_due_date_unchanged_on_approval(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """BUG REPRODUCTION: AT_MIDNIGHT_ONCE should NOT reschedule due date on approval.

        Expected: Approval → state=APPROVED, due_date unchanged
        Bug: Due date is rescheduled immediately on approval
        """
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Reset Midnight Once"]
        chore_info = coordinator.chores_data.get(chore_id, {})

        # Verify chore has correct reset type
        assert (
            chore_info.get(DATA_CHORE_APPROVAL_RESET_TYPE)
            == APPROVAL_RESET_AT_MIDNIGHT_ONCE
        )

        # Get due date before approval
        due_date_before = get_kid_due_date(coordinator, zoe_id, chore_id)
        assert due_date_before is not None, "Chore should have a due date"

        # Claim and approve the chore
        coordinator.claim_chore(zoe_id, chore_id, "Test User")
        coordinator.approve_chore("parent", zoe_id, chore_id)

        # Verify state is APPROVED
        state = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state == CHORE_STATE_APPROVED

        # Get due date after approval
        due_date_after = get_kid_due_date(coordinator, zoe_id, chore_id)

        # BUG: Due date should NOT change on approval for AT_MIDNIGHT_ONCE
        # This assertion documents expected behavior - it may fail due to the bug
        assert due_date_after == due_date_before, (
            f"AT_MIDNIGHT_ONCE: Due date should NOT change on approval. "
            f"Before: {due_date_before}, After: {due_date_after}"
        )

    @pytest.mark.asyncio
    async def test_at_midnight_once_blocks_second_approval(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: AT_MIDNIGHT_ONCE should block second approval in same period."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Reset Midnight Once"]

        # First claim and approve
        coordinator.claim_chore(zoe_id, chore_id, "Test User")
        coordinator.approve_chore("parent", zoe_id, chore_id)

        # Verify state is APPROVED
        state = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state == CHORE_STATE_APPROVED

        # Verify is_approved_in_current_period returns True
        assert coordinator.is_approved_in_current_period(zoe_id, chore_id), (
            "Should be approved in current period"
        )

        # Verify cannot approve again (_can_approve_chore should return False)
        can_approve, error_key = coordinator._can_approve_chore(zoe_id, chore_id)
        assert not can_approve, "Should not be able to approve again"
        assert error_key == TRANS_KEY_ERROR_CHORE_ALREADY_APPROVED, (
            f"Error should be already_approved, got {error_key}"
        )


class TestApprovalResetAtMidnightMulti:
    """Test AT_MIDNIGHT_MULTI approval reset behavior.

    Expected behavior:
    - MULTIPLE approvals allowed per approval period
    - Due date should NOT change on approval
    - Due date should be rescheduled at midnight reset
    - State resets to PENDING immediately after approval (allowing re-claim)
    """

    @pytest.mark.asyncio
    async def test_at_midnight_multi_allows_multiple_approvals(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: AT_MIDNIGHT_MULTI allows multiple claim-approve cycles in same period."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Reset Midnight Multi"]
        chore_info = coordinator.chores_data.get(chore_id, {})

        # Verify chore has correct reset type
        assert (
            chore_info.get(DATA_CHORE_APPROVAL_RESET_TYPE)
            == APPROVAL_RESET_AT_MIDNIGHT_MULTI
        )

        # First claim and approve
        coordinator.claim_chore(zoe_id, chore_id, "Test User")
        coordinator.approve_chore("parent", zoe_id, chore_id)

        # MULTI should allow another claim immediately
        # _can_claim_chore should return True for MULTI types
        can_claim, _ = coordinator._can_claim_chore(zoe_id, chore_id)
        assert can_claim, "AT_MIDNIGHT_MULTI should allow re-claim after approval"


class TestApprovalResetUponCompletion:
    """Test UPON_COMPLETION approval reset behavior.

    Expected behavior:
    - This is the only type that SHOULD reschedule due date on approval
    - State resets to PENDING immediately after approval
    - Due date advances to next recurrence
    """

    @pytest.mark.asyncio
    async def test_upon_completion_reschedules_due_date(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: UPON_COMPLETION should reschedule due date immediately on approval."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Reset Upon Completion"]
        chore_info = coordinator.chores_data.get(chore_id, {})

        # Verify chore has correct reset type
        assert (
            chore_info.get(DATA_CHORE_APPROVAL_RESET_TYPE)
            == APPROVAL_RESET_UPON_COMPLETION
        )

        # Get due date before approval
        due_date_before = get_kid_due_date(coordinator, zoe_id, chore_id)
        assert due_date_before is not None, "Chore should have a due date"

        # Claim and approve the chore
        coordinator.claim_chore(zoe_id, chore_id, "Test User")
        coordinator.approve_chore("parent", zoe_id, chore_id)

        # Get due date after approval
        due_date_after = get_kid_due_date(coordinator, zoe_id, chore_id)

        # UPON_COMPLETION SHOULD reschedule due date on approval
        assert due_date_after is not None, "Due date should still exist"
        assert due_date_after > due_date_before, (
            f"UPON_COMPLETION: Due date SHOULD advance on approval. "
            f"Before: {due_date_before}, After: {due_date_after}"
        )

    @pytest.mark.asyncio
    async def test_upon_completion_resets_to_pending(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: UPON_COMPLETION should reset state to PENDING immediately."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Reset Upon Completion"]

        # Claim and approve the chore
        coordinator.claim_chore(zoe_id, chore_id, "Test User")
        coordinator.approve_chore("parent", zoe_id, chore_id)

        # State should be PENDING (not APPROVED) because UPON_COMPLETION resets immediately
        state = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state == CHORE_STATE_PENDING, (
            f"UPON_COMPLETION should reset to PENDING, got {state}"
        )


class TestApprovalResetAtDueDateOnce:
    """Test AT_DUE_DATE_ONCE approval reset behavior.

    Expected behavior:
    - Only ONE approval allowed until due date passes
    - Due date should NOT change on approval
    - Due date should be rescheduled when it passes (at due date reset)
    """

    @pytest.mark.asyncio
    async def test_at_due_date_once_due_date_unchanged_on_approval(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: AT_DUE_DATE_ONCE should NOT reschedule due date on approval."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Reset Due Date Once"]
        chore_info = coordinator.chores_data.get(chore_id, {})

        # Verify chore has correct reset type
        assert (
            chore_info.get(DATA_CHORE_APPROVAL_RESET_TYPE)
            == APPROVAL_RESET_AT_DUE_DATE_ONCE
        )

        # Get due date before approval
        due_date_before = get_kid_due_date(coordinator, zoe_id, chore_id)
        assert due_date_before is not None, "Chore should have a due date"

        # Claim and approve the chore
        coordinator.claim_chore(zoe_id, chore_id, "Test User")
        coordinator.approve_chore("parent", zoe_id, chore_id)

        # Verify state is APPROVED
        state = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state == CHORE_STATE_APPROVED

        # Get due date after approval - should be unchanged
        due_date_after = get_kid_due_date(coordinator, zoe_id, chore_id)

        # Like AT_MIDNIGHT_ONCE, due date should NOT change on approval
        assert due_date_after == due_date_before, (
            f"AT_DUE_DATE_ONCE: Due date should NOT change on approval. "
            f"Before: {due_date_before}, After: {due_date_after}"
        )

    @pytest.mark.asyncio
    async def test_at_due_date_once_blocks_second_approval(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: AT_DUE_DATE_ONCE should block second approval before due date."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Reset Due Date Once"]

        # First claim and approve
        coordinator.claim_chore(zoe_id, chore_id, "Test User")
        coordinator.approve_chore("parent", zoe_id, chore_id)

        # Verify cannot approve again
        can_approve, error_key = coordinator._can_approve_chore(zoe_id, chore_id)
        assert not can_approve, "Should not be able to approve again before due date"
        assert error_key == TRANS_KEY_ERROR_CHORE_ALREADY_APPROVED, (
            f"Error should be already_approved, got {error_key}"
        )


# =============================================================================
# PHASE 5: OVERDUE HANDLING TESTS
# Tests for overdue_handling_type: at_due_date, never_overdue, at_due_date_then_reset
# =============================================================================


class TestOverdueAtDueDate:
    """Tests for overdue_handling_type: at_due_date (default behavior)."""

    @pytest.mark.asyncio
    async def test_at_due_date_becomes_overdue_when_past(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: Chore with at_due_date becomes OVERDUE when past due date."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Overdue At Due Date"]

        # Set due date to past (config flow rejects past dates)
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Run the overdue check
        await coordinator._check_overdue_chores()

        # Verify state is now OVERDUE
        kid_chore_data = coordinator._get_kid_chore_data(zoe_id, chore_id)
        current_state = kid_chore_data.get(DATA_KID_CHORE_DATA_STATE)

        assert current_state == CHORE_STATE_OVERDUE, (
            f"at_due_date chore with past due date should be OVERDUE, got {current_state}"
        )

        # Verify is_overdue helper returns True
        assert coordinator.is_overdue(zoe_id, chore_id), (
            "is_overdue() should return True for OVERDUE state"
        )

    @pytest.mark.asyncio
    async def test_at_due_date_future_not_overdue(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: Chore with at_due_date and future due date is NOT overdue."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        # Use a chore with future due date
        chore_id = chore_map["Reset Midnight Once"]  # Has due_date_relative: "future"

        # Run overdue check
        await coordinator._check_overdue_chores()

        # Verify state is NOT overdue
        assert not coordinator.is_overdue(zoe_id, chore_id), (
            "Chore with future due date should not be overdue"
        )


class TestOverdueNeverOverdue:
    """Tests for overdue_handling_type: never_overdue."""

    @pytest.mark.asyncio
    async def test_never_overdue_stays_pending_when_past_due(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: Chore with never_overdue stays PENDING even when past due date."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Overdue Never"]

        # Verify chore has never_overdue setting
        chore_info = coordinator.chores_data.get(chore_id, {})
        overdue_type = chore_info.get(DATA_CHORE_OVERDUE_HANDLING_TYPE)
        assert overdue_type == OVERDUE_HANDLING_NEVER_OVERDUE, (
            f"Test chore should have never_overdue handling, got {overdue_type}"
        )

        # Get initial state - should be PENDING or None (not yet initialized)
        kid_chore_data = coordinator._get_kid_chore_data(zoe_id, chore_id)
        initial_state_value = kid_chore_data.get(DATA_KID_CHORE_DATA_STATE)
        assert initial_state_value in (None, CHORE_STATE_PENDING), (
            f"Initial state should be None or PENDING, got {initial_state_value}"
        )

        # Set due date to past (config flow rejects past dates)
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Run overdue check
        await coordinator._check_overdue_chores()

        # Verify state is STILL PENDING or None (not overdue despite past due date)
        kid_chore_data = coordinator._get_kid_chore_data(zoe_id, chore_id)
        current_state = kid_chore_data.get(DATA_KID_CHORE_DATA_STATE)

        assert current_state in (None, CHORE_STATE_PENDING), (
            f"never_overdue chore should stay PENDING/None, got {current_state}"
        )

        # Verify is_overdue helper returns False
        assert not coordinator.is_overdue(zoe_id, chore_id), (
            "is_overdue() should return False for never_overdue chore"
        )


class TestOverdueThenReset:
    """Tests for overdue_handling_type: at_due_date_then_reset."""

    @pytest.mark.asyncio
    async def test_at_due_date_then_reset_becomes_overdue(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: Chore with at_due_date_then_reset becomes OVERDUE when past due."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Overdue Then Reset"]

        # Verify chore has at_due_date_then_reset setting
        chore_info = coordinator.chores_data.get(chore_id, {})
        overdue_type = chore_info.get(DATA_CHORE_OVERDUE_HANDLING_TYPE)
        assert overdue_type == OVERDUE_HANDLING_AT_DUE_DATE_THEN_RESET, (
            f"Test chore should have at_due_date_then_reset handling, got {overdue_type}"
        )

        # Set due date to past (config flow rejects past dates)
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Run overdue check
        await coordinator._check_overdue_chores()

        # Verify state is OVERDUE
        kid_chore_data = coordinator._get_kid_chore_data(zoe_id, chore_id)
        current_state = kid_chore_data.get(DATA_KID_CHORE_DATA_STATE)

        assert current_state == CHORE_STATE_OVERDUE, (
            f"at_due_date_then_reset chore should be OVERDUE, got {current_state}"
        )

        # Verify is_overdue helper returns True
        assert coordinator.is_overdue(zoe_id, chore_id), (
            "is_overdue() should return True for OVERDUE state"
        )


class TestOverdueClaimedChoreNotOverdue:
    """Tests to ensure claimed chores are not marked overdue."""

    @pytest.mark.asyncio
    async def test_claimed_chore_not_marked_overdue(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: A claimed chore should NOT be marked as overdue."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        # Use a chore with at_due_date handling
        chore_id = chore_map["Overdue At Due Date"]

        # Claim the chore first
        coordinator.claim_chore(zoe_id, chore_id, "Test User")

        # Verify state is CLAIMED
        kid_chore_data = coordinator._get_kid_chore_data(zoe_id, chore_id)
        state_before = kid_chore_data.get(DATA_KID_CHORE_DATA_STATE)
        assert state_before == CHORE_STATE_CLAIMED, (
            f"State should be CLAIMED after claim, got {state_before}"
        )

        # Set due date to past AFTER claiming (config flow rejects past dates)
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Run overdue check
        await coordinator._check_overdue_chores()

        # Verify state is STILL CLAIMED (not overdue)
        kid_chore_data = coordinator._get_kid_chore_data(zoe_id, chore_id)
        state_after = kid_chore_data.get(DATA_KID_CHORE_DATA_STATE)

        assert state_after == CHORE_STATE_CLAIMED, (
            f"Claimed chore should stay CLAIMED, not become overdue. Got {state_after}"
        )


class TestIsOverdueHelper:
    """Tests for the coordinator.is_overdue() helper method."""

    @pytest.mark.asyncio
    async def test_is_overdue_returns_true_for_overdue_state(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: is_overdue() returns True when chore state is OVERDUE."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Overdue At Due Date"]

        # Set due date to past (config flow rejects past dates)
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Run overdue check to mark chore as overdue
        await coordinator._check_overdue_chores()

        # Verify is_overdue returns True
        result = coordinator.is_overdue(zoe_id, chore_id)
        assert result is True, "is_overdue() should return True for OVERDUE chore"

    @pytest.mark.asyncio
    async def test_is_overdue_returns_false_for_pending_state(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: is_overdue() returns False when chore state is PENDING."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        # Use a chore with future due date (won't be overdue)
        chore_id = chore_map["Reset Midnight Once"]

        # Run overdue check
        await coordinator._check_overdue_chores()

        # Verify is_overdue returns False
        result = coordinator.is_overdue(zoe_id, chore_id)
        assert result is False, "is_overdue() should return False for PENDING chore"

    @pytest.mark.asyncio
    async def test_is_overdue_returns_false_for_nonexistent_chore(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: is_overdue() returns False for non-existent chore."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]

        # Use a fake chore ID
        fake_chore_id = "nonexistent-chore-id-12345"

        # Verify is_overdue returns False (not an error)
        result = coordinator.is_overdue(zoe_id, fake_chore_id)
        assert result is False, (
            "is_overdue() should return False for non-existent chore"
        )


# =============================================================================
# TEST CLASS: Pending Claim Action Tests (Phase 6)
# These tests verify what happens to claimed-but-not-approved chores at reset.
# =============================================================================


class TestPendingClaimHold:
    """Tests for approval_reset_pending_claim_action: hold_pending.

    When reset occurs, claimed chores with HOLD action should retain their claim.
    """

    @pytest.mark.asyncio
    async def test_pending_hold_retains_claim_after_reset(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: HOLD pending claim is retained after reset."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Pending Hold"]

        # Verify chore has correct pending claim action
        chore_info = coordinator.chores_data.get(chore_id, {})
        assert (
            chore_info.get(DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION)
            == APPROVAL_RESET_PENDING_CLAIM_HOLD
        )

        # Claim the chore (but don't approve)
        coordinator.claim_chore(zoe_id, chore_id, "Test User")

        # Verify state is CLAIMED
        state_before = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state_before == CHORE_STATE_CLAIMED

        # Verify has pending claim
        assert coordinator.has_pending_claim(zoe_id, chore_id), (
            "Should have pending claim before reset"
        )

        # Trigger reset (simulate midnight reset)
        await coordinator._reset_daily_chore_statuses([FREQUENCY_DAILY])

        # Verify state is STILL CLAIMED (hold action keeps the claim)
        state_after = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state_after == CHORE_STATE_CLAIMED, (
            f"HOLD action should retain claimed state, got {state_after}"
        )

        # Verify still has pending claim
        assert coordinator.has_pending_claim(zoe_id, chore_id), (
            "Should still have pending claim after reset with HOLD action"
        )

    @pytest.mark.asyncio
    async def test_pending_hold_no_points_awarded(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: HOLD pending claim does NOT award points on reset."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Pending Hold"]

        # Get points before
        kid_info = coordinator.kids_data.get(zoe_id, {})
        points_before = kid_info.get(DATA_KID_POINTS, 0)

        # Claim the chore
        coordinator.claim_chore(zoe_id, chore_id, "Test User")

        # Trigger reset
        await coordinator._reset_daily_chore_statuses([FREQUENCY_DAILY])

        # Verify points unchanged (no auto-approval)
        kid_info = coordinator.kids_data.get(zoe_id, {})
        points_after = kid_info.get(DATA_KID_POINTS, 0)

        assert points_after == points_before, (
            f"HOLD action should NOT award points. Before: {points_before}, After: {points_after}"
        )


class TestPendingClaimClear:
    """Tests for approval_reset_pending_claim_action: clear_pending.

    When reset occurs, claimed chores with CLEAR action should be reset to PENDING.
    """

    @pytest.mark.asyncio
    async def test_pending_clear_resets_to_pending(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: CLEAR pending claim resets state to PENDING."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Pending Clear"]

        # Verify chore has correct pending claim action
        chore_info = coordinator.chores_data.get(chore_id, {})
        assert (
            chore_info.get(DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION)
            == APPROVAL_RESET_PENDING_CLAIM_CLEAR
        )

        # Claim the chore
        coordinator.claim_chore(zoe_id, chore_id, "Test User")

        # Verify state is CLAIMED
        state_before = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state_before == CHORE_STATE_CLAIMED

        # Set due date to past so reset will process the chore
        # (reset checks if now > due_date before processing)
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Trigger reset
        await coordinator._reset_daily_chore_statuses([FREQUENCY_DAILY])

        # Verify state is PENDING (claim was cleared)
        state_after = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state_after == CHORE_STATE_PENDING, (
            f"CLEAR action should reset to PENDING, got {state_after}"
        )

    @pytest.mark.asyncio
    async def test_pending_clear_removes_pending_claim(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: CLEAR pending claim removes pending claim status."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Pending Clear"]

        # Claim the chore
        coordinator.claim_chore(zoe_id, chore_id, "Test User")

        # Verify has pending claim before reset
        assert coordinator.has_pending_claim(zoe_id, chore_id), (
            "Should have pending claim before reset"
        )

        # Set due date to past so reset will process the chore
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Trigger reset
        await coordinator._reset_daily_chore_statuses([FREQUENCY_DAILY])

        # Verify pending claim is cleared
        assert not coordinator.has_pending_claim(zoe_id, chore_id), (
            "Should NOT have pending claim after reset with CLEAR action"
        )

    @pytest.mark.asyncio
    async def test_pending_clear_no_points_awarded(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: CLEAR pending claim does NOT award points on reset."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Pending Clear"]

        # Get points before
        kid_info = coordinator.kids_data.get(zoe_id, {})
        points_before = kid_info.get(DATA_KID_POINTS, 0)

        # Claim the chore
        coordinator.claim_chore(zoe_id, chore_id, "Test User")

        # Set due date to past so reset will process the chore
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Trigger reset
        await coordinator._reset_daily_chore_statuses([FREQUENCY_DAILY])

        # Verify points unchanged
        kid_info = coordinator.kids_data.get(zoe_id, {})
        points_after = kid_info.get(DATA_KID_POINTS, 0)

        assert points_after == points_before, (
            f"CLEAR action should NOT award points. Before: {points_before}, After: {points_after}"
        )


class TestPendingClaimAutoApprove:
    """Tests for approval_reset_pending_claim_action: auto_approve_pending.

    When reset occurs, claimed chores with AUTO_APPROVE action should be
    automatically approved (awarding points) before reset.
    """

    @pytest.mark.asyncio
    async def test_pending_auto_approve_awards_points(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: AUTO_APPROVE pending claim awards points on reset."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Pending Auto Approve"]

        # Verify chore has correct pending claim action
        chore_info = coordinator.chores_data.get(chore_id, {})
        assert (
            chore_info.get(DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION)
            == APPROVAL_RESET_PENDING_CLAIM_AUTO_APPROVE
        )

        # Get chore points value
        chore_points = chore_info.get(DATA_CHORE_DEFAULT_POINTS, 0)
        assert chore_points > 0, "Test chore should have points defined"

        # Get points before
        kid_info = coordinator.kids_data.get(zoe_id, {})
        points_before = kid_info.get(DATA_KID_POINTS, 0)

        # Claim the chore
        coordinator.claim_chore(zoe_id, chore_id, "Test User")

        # Set due date to past so reset will process the chore
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Trigger reset
        await coordinator._reset_daily_chore_statuses([FREQUENCY_DAILY])

        # Verify points awarded (auto-approval happened)
        kid_info = coordinator.kids_data.get(zoe_id, {})
        points_after = kid_info.get(DATA_KID_POINTS, 0)

        assert points_after == points_before + chore_points, (
            f"AUTO_APPROVE should award {chore_points} points. "
            f"Before: {points_before}, After: {points_after}, Expected: {points_before + chore_points}"
        )

    @pytest.mark.asyncio
    async def test_pending_auto_approve_then_resets_to_pending(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: AUTO_APPROVE pending claim resets to PENDING after auto-approval."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Pending Auto Approve"]

        # Claim the chore
        coordinator.claim_chore(zoe_id, chore_id, "Test User")

        # Verify state is CLAIMED before reset
        state_before = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state_before == CHORE_STATE_CLAIMED

        # Set due date to past so reset will process the chore
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Trigger reset
        await coordinator._reset_daily_chore_statuses([FREQUENCY_DAILY])

        # Verify state is PENDING after reset (auto-approval + reset)
        state_after = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state_after == CHORE_STATE_PENDING, (
            f"AUTO_APPROVE should reset to PENDING after approval, got {state_after}"
        )

    @pytest.mark.asyncio
    async def test_pending_auto_approve_removes_pending_claim(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: AUTO_APPROVE pending claim removes pending claim status."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Pending Auto Approve"]

        # Claim the chore
        coordinator.claim_chore(zoe_id, chore_id, "Test User")

        # Verify has pending claim before reset
        assert coordinator.has_pending_claim(zoe_id, chore_id), (
            "Should have pending claim before reset"
        )

        # Set due date to past so reset will process the chore
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Trigger reset
        await coordinator._reset_daily_chore_statuses([FREQUENCY_DAILY])

        # Verify pending claim is cleared after auto-approval and reset
        assert not coordinator.has_pending_claim(zoe_id, chore_id), (
            "Should NOT have pending claim after auto-approval"
        )


class TestPendingClaimEdgeCases:
    """Edge case tests for pending claim actions."""

    @pytest.mark.asyncio
    async def test_approved_chore_not_affected_by_pending_claim_action(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: Already approved chores are not affected by pending claim action."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        chore_id = chore_map["Pending Hold"]

        # Claim and approve the chore normally
        coordinator.claim_chore(zoe_id, chore_id, "Test User")
        coordinator.approve_chore("parent", zoe_id, chore_id)

        # Verify state is APPROVED
        state_before = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state_before == CHORE_STATE_APPROVED

        # Verify no pending claim (already approved)
        assert not coordinator.has_pending_claim(zoe_id, chore_id), (
            "Approved chore should not have pending claim"
        )

        # Set due date to past so reset will process the chore
        set_chore_due_date_to_past(coordinator, chore_id, zoe_id, days_ago=1)

        # Trigger reset
        await coordinator._reset_daily_chore_statuses([FREQUENCY_DAILY])

        # State should be PENDING after reset (normal reset behavior)
        state_after = get_kid_chore_state(coordinator, zoe_id, chore_id)
        assert state_after == CHORE_STATE_PENDING, (
            f"Approved chore should reset to PENDING, got {state_after}"
        )

    @pytest.mark.asyncio
    async def test_unclaimed_chore_not_affected_by_pending_claim_action(
        self,
        hass: HomeAssistant,
        scheduling_scenario: SetupResult,
    ) -> None:
        """Test: Unclaimed chores are not affected by pending claim action settings."""
        coordinator = scheduling_scenario.coordinator
        zoe_id = scheduling_scenario.kid_ids["Zoë"]
        chore_map = scheduling_scenario.chore_ids

        _chore_id = chore_map[
            "Pending Auto Approve"
        ]  # Keep for clarity, intentionally unused

        # Get points before (no claim, no approval)
        kid_info = coordinator.kids_data.get(zoe_id, {})
        points_before = kid_info.get(DATA_KID_POINTS, 0)

        # Don't claim - just trigger reset
        await coordinator._reset_daily_chore_statuses([FREQUENCY_DAILY])

        # Verify points unchanged (no pending claim to auto-approve)
        kid_info = coordinator.kids_data.get(zoe_id, {})
        points_after = kid_info.get(DATA_KID_POINTS, 0)

        assert points_after == points_before, (
            f"Unclaimed chore should NOT award points on reset. "
            f"Before: {points_before}, After: {points_after}"
        )
