"""Test set_chore_due_date service data consistency for SHARED vs INDEPENDENT chores.

This test validates that set_chore_due_date maintains proper data structure:
- SHARED chores: Should have chore-level due_date
- INDEPENDENT chores: Should NOT have chore-level due_date, only per-kid due dates
"""

# pylint: disable=protected-access  # Accessing _data for testing coordinator directly
# pylint: disable=redefined-outer-name  # Pytest fixture pattern
# pylint: disable=unused-argument  # Fixtures needed for test setup

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


async def test_set_chore_due_date_shared_chore_adds_chore_level_due_date(
    hass: HomeAssistant,
    coordinator_with_post_migration_chores: KidsChoresDataCoordinator,
) -> None:
    """Test set_chore_due_date adds chore-level due_date for SHARED chores (correct)."""
    coordinator = coordinator_with_post_migration_chores

    # Remove chore-level due_date to test adding it
    coordinator.chores_data["shared_chore"].pop(DATA_CHORE_DUE_DATE, None)

    # Set due date
    new_due_date = dt_util.utcnow().replace(hour=15, minute=0, second=0, microsecond=0)
    coordinator.set_chore_due_date("shared_chore", new_due_date)

    # Should have chore-level due_date (correct for SHARED)
    chore_info = coordinator.chores_data["shared_chore"]
    assert DATA_CHORE_DUE_DATE in chore_info
    assert chore_info[DATA_CHORE_DUE_DATE] == new_due_date.isoformat()


async def test_set_chore_due_date_independent_chore_correctly_avoids_chore_level_due_date(
    hass: HomeAssistant,
    coordinator_with_post_migration_chores: KidsChoresDataCoordinator,
) -> None:
    """Test set_chore_due_date correctly avoids adding chore-level due_date for INDEPENDENT chores."""
    coordinator = coordinator_with_post_migration_chores

    # Ensure INDEPENDENT chore has no chore-level due_date (post-migration state)
    chore_info = coordinator.chores_data["independent_chore"]
    chore_info.pop(DATA_CHORE_DUE_DATE, None)
    assert DATA_CHORE_DUE_DATE not in chore_info
    assert chore_info[DATA_CHORE_COMPLETION_CRITERIA] == COMPLETION_CRITERIA_INDEPENDENT

    # Set due date
    new_due_date = dt_util.utcnow().replace(hour=16, minute=0, second=0, microsecond=0)
    coordinator.set_chore_due_date("independent_chore", new_due_date, "kid_1")

    # CORRECT: set_chore_due_date should NOT add chore-level due_date for INDEPENDENT chores
    assert (
        DATA_CHORE_DUE_DATE not in chore_info
    )  # Should maintain post-migration structure

    # But it should correctly update per-kid structures
    assert DATA_CHORE_PER_KID_DUE_DATES in chore_info
    assert chore_info[DATA_CHORE_PER_KID_DUE_DATES]["kid_1"] == new_due_date.isoformat()

    kid_chore_data = coordinator.kids_data["kid_1"][DATA_KID_CHORE_DATA][
        "independent_chore"
    ]
    assert kid_chore_data[DATA_KID_CHORE_DATA_DUE_DATE] == new_due_date.isoformat()


async def test_set_chore_due_date_independent_all_kids_correctly_avoids_chore_level_due_date(
    hass: HomeAssistant,
    coordinator_with_post_migration_chores: KidsChoresDataCoordinator,
) -> None:
    """Test set_chore_due_date for all kids in INDEPENDENT chore correctly avoids chore-level due_date."""
    coordinator = coordinator_with_post_migration_chores

    # Ensure INDEPENDENT chore has no chore-level due_date (post-migration state)
    chore_info = coordinator.chores_data["independent_chore"]
    chore_info.pop(DATA_CHORE_DUE_DATE, None)
    assert DATA_CHORE_DUE_DATE not in chore_info

    # Set due date for all kids (kid_id=None)
    new_due_date = dt_util.utcnow().replace(hour=17, minute=0, second=0, microsecond=0)
    coordinator.set_chore_due_date(
        "independent_chore", new_due_date
    )  # No kid_id = all kids

    # CORRECT: set_chore_due_date should NOT add chore-level due_date for INDEPENDENT chores
    assert (
        DATA_CHORE_DUE_DATE not in chore_info
    )  # Should maintain post-migration structure
