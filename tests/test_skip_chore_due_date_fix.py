"""Test skip_chore_due_date service handling for post-migration chore structures.

This test validates the fix for the issue where skip_chore_due_date service
would fail for INDEPENDENT chores after migration because the service was
looking for a chore-level due_date that migration had deleted.

After migration:
- SHARED chores: Keep chore-level due_date
- INDEPENDENT chores: Delete chore-level due_date, use per-kid due dates
"""

# pylint: disable=protected-access  # Accessing _data for testing coordinator directly
# pylint: disable=redefined-outer-name  # Pytest fixture pattern
# pylint: disable=unused-argument  # Fixtures needed for test setup

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.kidschores.const import (
    COMPLETION_CRITERIA_INDEPENDENT,
    COMPLETION_CRITERIA_SHARED,
    COORDINATOR,
    DATA_CHORE_COMPLETION_CRITERIA,
    DATA_CHORE_DUE_DATE,
    DATA_CHORE_PER_KID_DUE_DATES,
    DATA_CHORE_RECURRING_FREQUENCY,
    DATA_KID_CHORE_DATA,
    DATA_KID_CHORE_DATA_DUE_DATE,
    DOMAIN,
    FREQUENCY_DAILY,
    SCHEMA_VERSION_STORAGE_ONLY,
)
from custom_components.kidschores.coordinator import KidsChoresDataCoordinator


@pytest.fixture
async def coordinator_with_post_migration_chores(
    hass: HomeAssistant,
    init_integration,
) -> KidsChoresDataCoordinator:
    """Set up coordinator with post-migration chore structures (SHARED vs INDEPENDENT)."""
    config_entry = init_integration
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Modify coordinator data to simulate post-migration state
    coordinator._data = {
        "meta": {"schema_version": SCHEMA_VERSION_STORAGE_ONLY},
        "kids": {
            "kid_1": {
                "name": "TestKid",
                "internal_id": "kid_1",
                "points": 100.0,
                DATA_KID_CHORE_DATA: {
                    "shared_chore": {
                        DATA_KID_CHORE_DATA_DUE_DATE: "2026-01-05T10:00:00+00:00"
                    },
                    "independent_chore": {
                        DATA_KID_CHORE_DATA_DUE_DATE: "2026-01-05T12:00:00+00:00"
                    },
                    "independent_no_due_date": {
                        # No due date in kid's data
                    },
                },
            }
        },
        "chores": {
            "shared_chore": {
                "name": "Shared Chore",
                "internal_id": "shared_chore",
                DATA_CHORE_COMPLETION_CRITERIA: COMPLETION_CRITERIA_SHARED,
                DATA_CHORE_RECURRING_FREQUENCY: FREQUENCY_DAILY,
                DATA_CHORE_DUE_DATE: "2026-01-05T10:00:00+00:00",  # Has chore-level due date
                "assigned_kids": ["kid_1"],
            },
            "independent_chore": {
                "name": "Independent Chore",
                "internal_id": "independent_chore",
                DATA_CHORE_COMPLETION_CRITERIA: COMPLETION_CRITERIA_INDEPENDENT,
                DATA_CHORE_RECURRING_FREQUENCY: FREQUENCY_DAILY,
                # No chore-level due_date (deleted by migration)
                DATA_CHORE_PER_KID_DUE_DATES: {"kid_1": "2026-01-05T12:00:00+00:00"},
                "assigned_kids": ["kid_1"],
            },
            "independent_no_due_date": {
                "name": "Independent No Due Date",
                "internal_id": "independent_no_due_date",
                DATA_CHORE_COMPLETION_CRITERIA: COMPLETION_CRITERIA_INDEPENDENT,
                DATA_CHORE_RECURRING_FREQUENCY: FREQUENCY_DAILY,
                # No chore-level due_date AND no per-kid due dates
                DATA_CHORE_PER_KID_DUE_DATES: {},
                "assigned_kids": ["kid_1"],
            },
        },
        "rewards": {},
        "badges": {},
        "parents": {},
        "bonuses": {},
        "penalties": {},
        "achievements": {},
        "challenges": {},
        "pending_chore_approvals": [],
        "pending_reward_approvals": [],
    }

    return coordinator


async def test_skip_chore_due_date_shared_chore_with_due_date(
    hass: HomeAssistant,
    coordinator_with_post_migration_chores: KidsChoresDataCoordinator,
) -> None:
    """Test skip_chore_due_date works for SHARED chore with chore-level due date."""
    coordinator = coordinator_with_post_migration_chores

    # Should work - SHARED chore with chore-level due date
    coordinator.skip_chore_due_date("shared_chore", "kid_1")

    # Verify the due date was moved forward
    chore_info = coordinator.chores_data["shared_chore"]
    assert DATA_CHORE_DUE_DATE in chore_info
    # Due date should be moved forward by 1 day


async def test_skip_chore_due_date_independent_chore_with_per_kid_due_date(
    hass: HomeAssistant,
    coordinator_with_post_migration_chores: KidsChoresDataCoordinator,
) -> None:
    """Test skip_chore_due_date works for INDEPENDENT chore with per-kid due date."""
    coordinator = coordinator_with_post_migration_chores

    # Should work - INDEPENDENT chore with per-kid due date
    coordinator.skip_chore_due_date("independent_chore", "kid_1")

    # Verify the chore doesn't have chore-level due_date (deleted by migration)
    chore_info = coordinator.chores_data["independent_chore"]
    assert DATA_CHORE_DUE_DATE not in chore_info

    # But it has per-kid due dates
    assert DATA_CHORE_PER_KID_DUE_DATES in chore_info
    assert "kid_1" in chore_info[DATA_CHORE_PER_KID_DUE_DATES]


async def test_skip_chore_due_date_independent_chore_no_due_dates_noop(
    hass: HomeAssistant,
    coordinator_with_post_migration_chores: KidsChoresDataCoordinator,
) -> None:
    """Test skip_chore_due_date returns early for INDEPENDENT chore with no due dates."""
    coordinator = coordinator_with_post_migration_chores

    # Should return early (no-op) - INDEPENDENT chore with no due dates anywhere
    # This should not raise an exception
    coordinator.skip_chore_due_date("independent_no_due_date", "kid_1")

    # Verify chore data unchanged (no due dates should still be no due dates)
    chore_info = coordinator.chores_data["independent_no_due_date"]
    per_kid_due_dates = chore_info.get(DATA_CHORE_PER_KID_DUE_DATES, {})
    assert per_kid_due_dates.get("kid_1") is None


async def test_skip_chore_due_date_shared_chore_no_due_date_fails(
    hass: HomeAssistant,
    coordinator_with_post_migration_chores: KidsChoresDataCoordinator,
) -> None:
    """Test skip_chore_due_date fails for SHARED chore with no chore-level due date."""
    coordinator = coordinator_with_post_migration_chores

    # Remove the due date from shared chore to simulate corrupted data
    coordinator.chores_data["shared_chore"].pop(DATA_CHORE_DUE_DATE, None)

    # Should fail - SHARED chore needs chore-level due date
    with pytest.raises(HomeAssistantError, match="Required field due_date is missing"):
        coordinator.skip_chore_due_date("shared_chore", "kid_1")


async def test_skip_chore_due_date_independent_with_kid_chore_data_due_date(
    hass: HomeAssistant,
    coordinator_with_post_migration_chores: KidsChoresDataCoordinator,
) -> None:
    """Test skip_chore_due_date works when due date is in kid's chore_data."""
    coordinator = coordinator_with_post_migration_chores

    # Remove per-kid due dates but keep kid's chore data due date
    coordinator.chores_data["independent_chore"][DATA_CHORE_PER_KID_DUE_DATES] = {}

    # Should work - INDEPENDENT chore with due date in kid's chore_data
    coordinator.skip_chore_due_date("independent_chore", "kid_1")

    # Kid's chore data should still have due date
    kid_chore_data = coordinator.kids_data["kid_1"][DATA_KID_CHORE_DATA][
        "independent_chore"
    ]
    assert DATA_KID_CHORE_DATA_DUE_DATE in kid_chore_data
