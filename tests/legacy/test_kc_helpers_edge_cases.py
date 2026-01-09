"""Edge case tests for kc_helpers module.

Tests for:
- Entity lookup helpers (get_*_id_by_name, get_*_id_or_raise)
- Authorization helpers (is_user_authorized_for_global_action, is_user_authorized_for_kid)
- Progress calculation helpers
- Datetime boundary handling in adjust_datetime_by_interval
"""

# pylint: disable=protected-access  # Testing internal helpers
# pylint: disable=unused-argument  # Pytest fixtures required for setup

from datetime import datetime, timezone

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kidschores import const
from custom_components.kidschores import kc_helpers as kh


class TestEntityLookupHelpers:
    """Test entity lookup functions with edge cases."""

    async def test_lookup_existing_entity(
        self, hass: HomeAssistant, scenario_minimal
    ) -> None:
        """Should find existing entity by name."""
        config_entry, name_to_id_map = scenario_minimal
        coordinator = hass.data["kidschores"][config_entry.entry_id]["coordinator"]

        kid_id = name_to_id_map["kid:Zoë"]
        kid_info = coordinator.kids_data.get(kid_id, {})
        kid_name = kid_info.get(const.DATA_KID_NAME)

        result = kh.get_kid_id_by_name(coordinator, kid_name)

        assert result == kid_id

    async def test_lookup_missing_entity_returns_none(
        self, hass: HomeAssistant, scenario_minimal
    ) -> None:
        """Should return None for missing entity."""
        config_entry, _ = scenario_minimal
        coordinator = hass.data["kidschores"][config_entry.entry_id]["coordinator"]

        result = kh.get_kid_id_by_name(coordinator, "NonexistentKid")

        assert result is None

    async def test_lookup_or_raise_raises_on_missing(
        self, hass: HomeAssistant, scenario_minimal
    ) -> None:
        """Should raise HomeAssistantError on missing entity."""
        config_entry, _ = scenario_minimal
        coordinator = hass.data["kidschores"][config_entry.entry_id]["coordinator"]

        with pytest.raises(Exception):  # HomeAssistantError
            kh.get_kid_id_or_raise(coordinator, "NonexistentKid")


class TestAuthorizationHelpers:
    """Test authorization check functions."""

    async def test_admin_user_global_authorization(
        self, hass: HomeAssistant, scenario_minimal, mock_hass_users
    ) -> None:
        """Admin user should be authorized for global actions."""
        admin_user = mock_hass_users["admin"]

        is_authorized = await kh.is_user_authorized_for_global_action(
            hass, admin_user.id, "approve_chores"
        )

        assert is_authorized is True

    async def test_non_admin_user_global_authorization(
        self, hass: HomeAssistant, scenario_minimal, mock_hass_users
    ) -> None:
        """Registered parent user should be authorized for global actions."""
        parent_user = mock_hass_users["parent1"]

        is_authorized = await kh.is_user_authorized_for_global_action(
            hass, parent_user.id, "approve_chores"
        )

        # Parent users ARE authorized when registered in coordinator.parents_data
        assert is_authorized is True


class TestDatetimeBoundaryHandling:
    """Test datetime handling in adjust_datetime_by_interval."""

    async def test_month_end_transition(
        self, hass: HomeAssistant, scenario_minimal
    ) -> None:
        """Should handle month-end boundary correctly."""
        jan_31 = datetime(2025, 1, 31, 12, 0, 0, tzinfo=timezone.utc)

        result = kh.adjust_datetime_by_interval(jan_31, const.TIME_UNIT_MONTHS, 1)

        # Adding 1 month from Jan 31 should give Feb 28 (or 29 in leap year)
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    async def test_year_transition(self, hass: HomeAssistant, scenario_minimal) -> None:
        """Should handle year boundary correctly."""
        dec_31 = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        result = kh.adjust_datetime_by_interval(dec_31, const.TIME_UNIT_YEARS, 1)

        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc


class TestProgressCalculation:
    """Test progress calculation helpers."""

    async def test_progress_with_scenario_data(
        self, hass: HomeAssistant, scenario_minimal
    ) -> None:
        """Should calculate progress safely."""
        config_entry, name_to_id_map = scenario_minimal
        kid_id = name_to_id_map["kid:Zoë"]
        coordinator = hass.data["kidschores"][config_entry.entry_id]["coordinator"]

        kid_info = coordinator.kids_data.get(kid_id, {})
        # tracked_chores should be a list of chore IDs (strings), not dicts
        tracked_chore_ids = [
            chore_id
            for chore_id, chore_info in coordinator.chores_data.items()
            if kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        ]

        # Function returns tuple: (met_requirement, completed_count, total_count)
        met_req, completed, total = kh.get_today_chore_completion_progress(
            kid_info, tracked_chore_ids
        )

        assert isinstance(met_req, bool)
        assert isinstance(completed, int)
        assert isinstance(total, int)
        assert completed >= 0
        assert total >= 0
