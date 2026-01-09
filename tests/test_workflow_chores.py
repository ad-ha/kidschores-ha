"""Chore workflow tests using YAML scenarios.

These tests verify the complete claim → approve → points cycle
for all chore types using real config flow setup.

Test Organization:
- TestIndependentChores: Single-kid and multi-kid independent chores
- TestSharedFirstChores: Race-to-complete chores
- TestSharedAllChores: All-must-complete chores
- TestAutoApprove: Instant approval on claim

Coordinator API Reference:
- claim_chore(kid_id, chore_id, user_name)
- approve_chore(parent_name, kid_id, chore_id, points_awarded=None)
- disapprove_chore(parent_name, kid_id, chore_id)
"""

# pylint: disable=protected-access
# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument  # hass fixture required for HA test setup

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kidschores import const
from tests.helpers.setup import setup_from_yaml, SetupResult


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
async def scenario_minimal(
    hass: HomeAssistant,
    mock_hass_users: dict[str, Any],
) -> SetupResult:
    """Load minimal scenario: 1 kid, 1 parent, 5 chores."""
    return await setup_from_yaml(
        hass,
        mock_hass_users,
        "tests/scenarios/scenario_minimal.yaml",
    )


@pytest.fixture
async def scenario_shared(
    hass: HomeAssistant,
    mock_hass_users: dict[str, Any],
) -> SetupResult:
    """Load shared scenario: 3 kids, 1 parent, 8 shared chores."""
    return await setup_from_yaml(
        hass,
        mock_hass_users,
        "tests/scenarios/scenario_shared.yaml",
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


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
        State string (e.g., 'pending', 'claimed', 'approved')
    """
    kid_data = coordinator.kids_data.get(kid_id, {})
    chore_data = kid_data.get(const.DATA_KID_CHORE_DATA, {})
    per_chore = chore_data.get(chore_id, {})
    return per_chore.get(const.DATA_KID_CHORE_DATA_STATE, const.CHORE_STATE_PENDING)


def get_kid_points(coordinator: Any, kid_id: str) -> float:
    """Get a kid's current point balance."""
    kid_data = coordinator.kids_data.get(kid_id, {})
    return kid_data.get(const.DATA_KID_POINTS, 0.0)


# =============================================================================
# INDEPENDENT CHORE TESTS
# =============================================================================


class TestIndependentChores:
    """Tests for chores with completion_criteria='independent'."""

    @pytest.mark.asyncio
    async def test_claim_changes_state_to_claimed(
        self,
        hass: HomeAssistant,
        scenario_minimal: SetupResult,
    ) -> None:
        """Claiming a chore changes state from pending to claimed."""
        coordinator = scenario_minimal.coordinator
        kid_id = scenario_minimal.kid_ids["Zoë"]
        chore_id = scenario_minimal.chore_ids["Make bed"]

        # Initial state should be pending
        initial_state = get_kid_chore_state(coordinator, kid_id, chore_id)
        assert initial_state == const.CHORE_STATE_PENDING

        # Mock notifications to avoid side effects
        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            # Claim the chore (API: kid_id, chore_id, user_name)
            coordinator.claim_chore(kid_id, chore_id, "Zoë")

        # State should now be claimed
        new_state = get_kid_chore_state(coordinator, kid_id, chore_id)
        assert new_state == const.CHORE_STATE_CLAIMED

    @pytest.mark.asyncio
    async def test_approve_grants_points(
        self,
        hass: HomeAssistant,
        scenario_minimal: SetupResult,
    ) -> None:
        """Approving a claimed chore grants points to the kid."""
        coordinator = scenario_minimal.coordinator
        kid_id = scenario_minimal.kid_ids["Zoë"]
        chore_id = scenario_minimal.chore_ids["Make bed"]  # 5 points

        initial_points = get_kid_points(coordinator, kid_id)

        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            # Claim the chore (API: kid_id, chore_id, user_name)
            coordinator.claim_chore(kid_id, chore_id, "Zoë")

            # Approve the chore (API: parent_name, kid_id, chore_id)
            coordinator.approve_chore("Mom", kid_id, chore_id)

        # Points should increase by chore value (5 points)
        final_points = get_kid_points(coordinator, kid_id)
        assert final_points == initial_points + 5.0

        # State should be approved
        state = get_kid_chore_state(coordinator, kid_id, chore_id)
        assert state == const.CHORE_STATE_APPROVED

    @pytest.mark.asyncio
    async def test_disapprove_resets_to_pending(
        self,
        hass: HomeAssistant,
        scenario_minimal: SetupResult,
    ) -> None:
        """Disapproving a claimed chore resets it to pending state."""
        coordinator = scenario_minimal.coordinator
        kid_id = scenario_minimal.kid_ids["Zoë"]
        chore_id = scenario_minimal.chore_ids["Make bed"]

        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            # Claim the chore
            coordinator.claim_chore(kid_id, chore_id, "Zoë")

            # Verify claimed
            assert get_kid_chore_state(coordinator, kid_id, chore_id) == const.CHORE_STATE_CLAIMED

            # Disapprove (API: parent_name, kid_id, chore_id)
            coordinator.disapprove_chore("Mom", kid_id, chore_id)

        # State should be reset to pending
        state = get_kid_chore_state(coordinator, kid_id, chore_id)
        assert state == const.CHORE_STATE_PENDING

    @pytest.mark.asyncio
    async def test_disapprove_does_not_grant_points(
        self,
        hass: HomeAssistant,
        scenario_minimal: SetupResult,
    ) -> None:
        """Disapproving a chore does not change point balance."""
        coordinator = scenario_minimal.coordinator
        kid_id = scenario_minimal.kid_ids["Zoë"]
        chore_id = scenario_minimal.chore_ids["Make bed"]

        initial_points = get_kid_points(coordinator, kid_id)

        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            coordinator.claim_chore(kid_id, chore_id, "Zoë")
            coordinator.disapprove_chore("Mom", kid_id, chore_id)

        # Points should be unchanged
        final_points = get_kid_points(coordinator, kid_id)
        assert final_points == initial_points


# =============================================================================
# AUTO-APPROVE TESTS
# =============================================================================


class TestAutoApprove:
    """Tests for chores with auto_approve=True."""

    @pytest.mark.asyncio
    async def test_claim_triggers_instant_approval(
        self,
        hass: HomeAssistant,
        scenario_minimal: SetupResult,
    ) -> None:
        """Claiming an auto-approve chore immediately grants approval and points."""
        coordinator = scenario_minimal.coordinator
        kid_id = scenario_minimal.kid_ids["Zoë"]
        chore_id = scenario_minimal.chore_ids["Brush teeth"]  # auto_approve=true, 3 points

        initial_points = get_kid_points(coordinator, kid_id)

        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            # Claim the auto-approve chore
            coordinator.claim_chore(kid_id, chore_id, "Zoë")

        # State should be approved (skipped claimed)
        state = get_kid_chore_state(coordinator, kid_id, chore_id)
        assert state == const.CHORE_STATE_APPROVED

        # Points should have increased
        final_points = get_kid_points(coordinator, kid_id)
        assert final_points == initial_points + 3.0


# =============================================================================
# SHARED_FIRST CHORE TESTS
# =============================================================================


class TestSharedFirstChores:
    """Tests for chores with completion_criteria='shared_first'.

    In shared_first chores:
    1. When one kid claims, all others immediately get 'completed_by_other'
    2. Only the claiming kid can be approved for points
    3. On disapproval, everyone resets to pending
    """

    @pytest.mark.asyncio
    async def test_claim_blocks_other_kids(
        self,
        hass: HomeAssistant,
        scenario_shared: SetupResult,
    ) -> None:
        """First kid to claim blocks all other kids immediately."""
        coordinator = scenario_shared.coordinator
        zoe_id = scenario_shared.kid_ids["Zoë"]
        max_id = scenario_shared.kid_ids["Max"]
        lila_id = scenario_shared.kid_ids["Lila"]
        chore_id = scenario_shared.chore_ids["Take out trash"]  # shared_first, 3 kids

        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            # Zoë claims first
            coordinator.claim_chore(zoe_id, chore_id, "Zoë")

        # Zoë should be claimed
        assert get_kid_chore_state(coordinator, zoe_id, chore_id) == const.CHORE_STATE_CLAIMED

        # Max and Lila should immediately be completed_by_other
        assert get_kid_chore_state(coordinator, max_id, chore_id) == const.CHORE_STATE_COMPLETED_BY_OTHER
        assert get_kid_chore_state(coordinator, lila_id, chore_id) == const.CHORE_STATE_COMPLETED_BY_OTHER

    @pytest.mark.asyncio
    async def test_approve_grants_points_to_claimer_only(
        self,
        hass: HomeAssistant,
        scenario_shared: SetupResult,
    ) -> None:
        """Approving the claimer grants them points, others remain blocked."""
        coordinator = scenario_shared.coordinator
        zoe_id = scenario_shared.kid_ids["Zoë"]
        max_id = scenario_shared.kid_ids["Max"]
        lila_id = scenario_shared.kid_ids["Lila"]
        chore_id = scenario_shared.chore_ids["Take out trash"]  # shared_first, 5 points

        initial_zoe_points = get_kid_points(coordinator, zoe_id)
        initial_max_points = get_kid_points(coordinator, max_id)
        initial_lila_points = get_kid_points(coordinator, lila_id)

        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            # Zoë claims and gets approved
            coordinator.claim_chore(zoe_id, chore_id, "Zoë")
            coordinator.approve_chore("Mom", zoe_id, chore_id)

        # Zoë should be approved with points
        assert get_kid_chore_state(coordinator, zoe_id, chore_id) == const.CHORE_STATE_APPROVED
        assert get_kid_points(coordinator, zoe_id) == initial_zoe_points + 5.0

        # Max and Lila remain completed_by_other, no points
        assert get_kid_chore_state(coordinator, max_id, chore_id) == const.CHORE_STATE_COMPLETED_BY_OTHER
        assert get_kid_points(coordinator, max_id) == initial_max_points

        assert get_kid_chore_state(coordinator, lila_id, chore_id) == const.CHORE_STATE_COMPLETED_BY_OTHER
        assert get_kid_points(coordinator, lila_id) == initial_lila_points

    @pytest.mark.asyncio
    async def test_disapprove_resets_all_kids(
        self,
        hass: HomeAssistant,
        scenario_shared: SetupResult,
    ) -> None:
        """Disapproving the claimer resets ALL kids to pending."""
        coordinator = scenario_shared.coordinator
        zoe_id = scenario_shared.kid_ids["Zoë"]
        max_id = scenario_shared.kid_ids["Max"]
        chore_id = scenario_shared.chore_ids["Organize garage"]  # shared_first, Zoë + Max only

        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            # Zoë claims (Max becomes completed_by_other)
            coordinator.claim_chore(zoe_id, chore_id, "Zoë")
            assert get_kid_chore_state(coordinator, max_id, chore_id) == const.CHORE_STATE_COMPLETED_BY_OTHER

            # Disapprove Zoë
            coordinator.disapprove_chore("Mom", zoe_id, chore_id)

        # Both should be reset to pending
        assert get_kid_chore_state(coordinator, zoe_id, chore_id) == const.CHORE_STATE_PENDING
        assert get_kid_chore_state(coordinator, max_id, chore_id) == const.CHORE_STATE_PENDING


# =============================================================================
# SHARED_ALL CHORE TESTS
# =============================================================================


class TestSharedAllChores:
    """Tests for chores with completion_criteria='shared_all'.

    In shared_all chores:
    - Each kid can claim and be approved independently
    - Each kid gets their own points when approved
    - All kids share the same global state tracking
    """

    @pytest.mark.asyncio
    async def test_each_kid_gets_points_on_approval(
        self,
        hass: HomeAssistant,
        scenario_shared: SetupResult,
    ) -> None:
        """Each kid gets points when they individually get approved."""
        coordinator = scenario_shared.coordinator
        zoe_id = scenario_shared.kid_ids["Zoë"]
        max_id = scenario_shared.kid_ids["Max"]
        chore_id = scenario_shared.chore_ids["Walk the dog"]  # shared_all, Zoë + Max, 8 pts

        initial_zoe = get_kid_points(coordinator, zoe_id)
        initial_max = get_kid_points(coordinator, max_id)

        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            # Zoë claims and gets approved
            coordinator.claim_chore(zoe_id, chore_id, "Zoë")
            coordinator.approve_chore("Mom", zoe_id, chore_id)

            # Zoë gets points immediately
            assert get_kid_points(coordinator, zoe_id) == initial_zoe + 8.0

            # Max claims and gets approved
            coordinator.claim_chore(max_id, chore_id, "Max")
            coordinator.approve_chore("Mom", max_id, chore_id)

            # Max gets points
            assert get_kid_points(coordinator, max_id) == initial_max + 8.0

    @pytest.mark.asyncio
    async def test_three_kid_shared_all(
        self,
        hass: HomeAssistant,
        scenario_shared: SetupResult,
    ) -> None:
        """Three-kid shared_all chore - each gets points independently."""
        coordinator = scenario_shared.coordinator
        zoe_id = scenario_shared.kid_ids["Zoë"]
        max_id = scenario_shared.kid_ids["Max"]
        lila_id = scenario_shared.kid_ids["Lila"]
        chore_id = scenario_shared.chore_ids["Family dinner cleanup"]  # shared_all, 10 pts

        initial_zoe = get_kid_points(coordinator, zoe_id)
        initial_max = get_kid_points(coordinator, max_id)
        initial_lila = get_kid_points(coordinator, lila_id)

        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            # All three claim and get approved one by one
            coordinator.claim_chore(zoe_id, chore_id, "Zoë")
            coordinator.approve_chore("Mom", zoe_id, chore_id)
            assert get_kid_points(coordinator, zoe_id) == initial_zoe + 10.0

            coordinator.claim_chore(max_id, chore_id, "Max")
            coordinator.approve_chore("Mom", max_id, chore_id)
            assert get_kid_points(coordinator, max_id) == initial_max + 10.0

            coordinator.claim_chore(lila_id, chore_id, "Lila")
            coordinator.approve_chore("Mom", lila_id, chore_id)
            assert get_kid_points(coordinator, lila_id) == initial_lila + 10.0

    @pytest.mark.asyncio
    async def test_approved_state_tracked_per_kid(
        self,
        hass: HomeAssistant,
        scenario_shared: SetupResult,
    ) -> None:
        """Each kid has independent state tracking."""
        coordinator = scenario_shared.coordinator
        zoe_id = scenario_shared.kid_ids["Zoë"]
        max_id = scenario_shared.kid_ids["Max"]
        lila_id = scenario_shared.kid_ids["Lila"]
        chore_id = scenario_shared.chore_ids["Family dinner cleanup"]  # shared_all, 3 kids

        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            # Only Zoë completes the chore
            coordinator.claim_chore(zoe_id, chore_id, "Zoë")
            coordinator.approve_chore("Mom", zoe_id, chore_id)

        # Zoë is approved
        assert get_kid_chore_state(coordinator, zoe_id, chore_id) == const.CHORE_STATE_APPROVED

        # Max and Lila are still pending
        assert get_kid_chore_state(coordinator, max_id, chore_id) == const.CHORE_STATE_PENDING
        assert get_kid_chore_state(coordinator, lila_id, chore_id) == const.CHORE_STATE_PENDING
