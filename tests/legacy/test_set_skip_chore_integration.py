"""Integration test demonstrating correct interaction between set_chore_due_date and skip_chore_due_date.

This test validates that:
1. set_chore_due_date maintains proper data structure (SHARED vs INDEPENDENT)
2. skip_chore_due_date works correctly with the proper data structure
3. Both services work together without data consistency issues
"""

# pylint: disable=protected-access  # Accessing _data for testing coordinator directly
# pylint: disable=redefined-outer-name  # Pytest fixture pattern
# pylint: disable=unused-argument  # Fixtures needed for test setup

from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

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
async def coordinator_with_clean_post_migration_chores(
    hass: HomeAssistant,
    init_integration,
) -> KidsChoresDataCoordinator:
    """Set up coordinator with clean post-migration chore structures (no chore-level due_date for INDEPENDENT)."""
    config_entry = init_integration
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Modify coordinator data to simulate clean post-migration state
    coordinator._data = {
        "meta": {"schema_version": SCHEMA_VERSION_STORAGE_ONLY},
        "kids": {
            "kid_1": {
                "name": "TestKid",
                "internal_id": "kid_1",
                "points": 100.0,
                DATA_KID_CHORE_DATA: {
                    "shared_chore": {},  # No due date initially
                    "independent_chore": {},  # No due date initially
                },
            }
        },
        "chores": {
            "shared_chore": {
                "name": "Shared Chore",
                "internal_id": "shared_chore",
                DATA_CHORE_COMPLETION_CRITERIA: COMPLETION_CRITERIA_SHARED,
                DATA_CHORE_RECURRING_FREQUENCY: FREQUENCY_DAILY,
                # No chore-level due_date initially
                "assigned_kids": ["kid_1"],
            },
            "independent_chore": {
                "name": "Independent Chore",
                "internal_id": "independent_chore",
                DATA_CHORE_COMPLETION_CRITERIA: COMPLETION_CRITERIA_INDEPENDENT,
                DATA_CHORE_RECURRING_FREQUENCY: FREQUENCY_DAILY,
                # No chore-level due_date (correct post-migration state)
                DATA_CHORE_PER_KID_DUE_DATES: {},  # Empty initially
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


async def test_set_and_skip_shared_chore_integration(
    hass: HomeAssistant,
    coordinator_with_clean_post_migration_chores: KidsChoresDataCoordinator,
) -> None:
    """Test that set_chore_due_date and skip_chore_due_date work correctly together for SHARED chores."""
    coordinator = coordinator_with_clean_post_migration_chores

    # 1. Set due date for SHARED chore
    initial_due_date = dt_util.utcnow().replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    coordinator.set_chore_due_date("shared_chore", initial_due_date)

    # Verify SHARED chore has chore-level due_date (correct structure)
    chore_info = coordinator.chores_data["shared_chore"]
    assert DATA_CHORE_DUE_DATE in chore_info
    assert chore_info[DATA_CHORE_DUE_DATE] == initial_due_date.isoformat()

    # 2. Skip the due date (should work without error)
    coordinator.skip_chore_due_date("shared_chore", "kid_1")

    # Verify due date was advanced
    updated_due_date = dt_util.parse_datetime(chore_info[DATA_CHORE_DUE_DATE])
    assert updated_due_date is not None
    assert updated_due_date > initial_due_date


async def test_set_and_skip_independent_chore_integration(
    hass: HomeAssistant,
    coordinator_with_clean_post_migration_chores: KidsChoresDataCoordinator,
) -> None:
    """Test that set_chore_due_date and skip_chore_due_date work correctly together for INDEPENDENT chores."""
    coordinator = coordinator_with_clean_post_migration_chores

    # 1. Set due date for INDEPENDENT chore (specific kid)
    initial_due_date = dt_util.utcnow().replace(
        hour=14, minute=0, second=0, microsecond=0
    )
    coordinator.set_chore_due_date("independent_chore", initial_due_date, "kid_1")

    # Verify INDEPENDENT chore has correct structure (no chore-level due_date)
    chore_info = coordinator.chores_data["independent_chore"]
    assert DATA_CHORE_DUE_DATE not in chore_info  # Should NOT have chore-level due_date
    assert DATA_CHORE_PER_KID_DUE_DATES in chore_info
    assert (
        chore_info[DATA_CHORE_PER_KID_DUE_DATES]["kid_1"]
        == initial_due_date.isoformat()
    )

    # Kid's chore data should also be updated
    kid_chore_data = coordinator.kids_data["kid_1"][DATA_KID_CHORE_DATA][
        "independent_chore"
    ]
    assert kid_chore_data[DATA_KID_CHORE_DATA_DUE_DATE] == initial_due_date.isoformat()

    # 2. Skip the due date (should work without error using per-kid due_date)
    coordinator.skip_chore_due_date("independent_chore", "kid_1")

    # Verify per-kid due date was advanced (chore_info doesn't have chore-level due_date)
    updated_per_kid_due_date = dt_util.parse_datetime(
        chore_info[DATA_CHORE_PER_KID_DUE_DATES]["kid_1"]
    )
    assert updated_per_kid_due_date is not None
    assert updated_per_kid_due_date > initial_due_date


async def test_data_structure_consistency_after_multiple_operations(
    hass: HomeAssistant,
    coordinator_with_clean_post_migration_chores: KidsChoresDataCoordinator,
) -> None:
    """Test that data structure remains consistent after multiple set/skip operations."""
    coordinator = coordinator_with_clean_post_migration_chores

    # Multiple operations on SHARED chore
    shared_due_date = dt_util.utcnow().replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    coordinator.set_chore_due_date("shared_chore", shared_due_date)
    coordinator.skip_chore_due_date("shared_chore", "kid_1")
    coordinator.set_chore_due_date("shared_chore", shared_due_date + timedelta(hours=1))
    coordinator.skip_chore_due_date("shared_chore", "kid_1")

    # SHARED chore should always have chore-level due_date
    shared_chore_info = coordinator.chores_data["shared_chore"]
    assert DATA_CHORE_DUE_DATE in shared_chore_info

    # Multiple operations on INDEPENDENT chore
    independent_due_date = dt_util.utcnow().replace(
        hour=15, minute=0, second=0, microsecond=0
    )
    coordinator.set_chore_due_date("independent_chore", independent_due_date, "kid_1")
    coordinator.skip_chore_due_date("independent_chore", "kid_1")
    coordinator.set_chore_due_date(
        "independent_chore", independent_due_date + timedelta(hours=1), "kid_1"
    )
    coordinator.skip_chore_due_date("independent_chore", "kid_1")

    # INDEPENDENT chore should NEVER have chore-level due_date
    independent_chore_info = coordinator.chores_data["independent_chore"]
    assert DATA_CHORE_DUE_DATE not in independent_chore_info
    assert DATA_CHORE_PER_KID_DUE_DATES in independent_chore_info
    assert "kid_1" in independent_chore_info[DATA_CHORE_PER_KID_DUE_DATES]
