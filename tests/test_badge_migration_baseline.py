"""Baseline tests for badge assigned_to field migration.

These tests validate that _migrate_badges() in coordinator.py (lines 512-513)
correctly adds the assigned_to field to badges during migration from older schemas.

Coverage targets:
    - coordinator.py lines 512-513: Migration adds DATA_BADGE_ASSIGNED_TO field

Test Strategy:
    Use actual migration sample files (kidschores_data_30, _31, _40beta1) to verify
    that real production data migrates correctly. Old schemas don't have assigned_to,
    so migration should add it as empty list [].
"""

# pylint: disable=protected-access  # Accessing coordinator._data for migration testing

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    CONF_POINTS_ICON,
    CONF_POINTS_LABEL,
    COORDINATOR,
    DATA_BADGE_ASSIGNED_TO,
    DATA_BADGES,
    DEFAULT_POINTS_ICON,
    DEFAULT_POINTS_LABEL,
    DOMAIN,
)


@pytest.fixture
def migration_sample_v30() -> dict[str, Any]:
    """Load kidschores_data_30 sample file (KC 3.0 production data - no assigned_to)."""
    sample_path = Path(__file__).parent / "migration_samples" / "kidschores_data_30"
    with open(sample_path, encoding="utf-8") as f:
        raw_data = json.load(f)
    return raw_data["data"]


@pytest.fixture
def mock_config_entry_for_migration() -> MockConfigEntry:
    """Create a config entry for migration testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="KidsChores Badge Migration Test",
        data={},
        options={
            CONF_POINTS_LABEL: DEFAULT_POINTS_LABEL,
            CONF_POINTS_ICON: DEFAULT_POINTS_ICON,
        },
        entry_id="test_badge_migration_entry",
        version=1,
        minor_version=1,
    )


@pytest.mark.parametrize(
    "sample_fixture_name",
    ["migration_sample_v30"],
)
async def test_migration_adds_assigned_to_field_as_empty_list(
    hass: HomeAssistant,
    mock_config_entry_for_migration: MockConfigEntry,  # pylint: disable=redefined-outer-name
    sample_fixture_name: str,
    request,
) -> None:
    """Test that migration adds assigned_to field as empty list to all badges.

    Validates coordinator.py lines 512-513:
        if DATA_BADGE_ASSIGNED_TO not in badge_data:
            badge_data[DATA_BADGE_ASSIGNED_TO] = []

    Uses real migration sample from KC 3.0 which doesn't have assigned_to field.
    """
    # Get the sample data fixture by name
    sample_data = request.getfixturevalue(sample_fixture_name)

    # Verify pre-migration state: badges exist but no assigned_to field
    assert DATA_BADGES in sample_data, "Test data should have badges"
    assert len(sample_data[DATA_BADGES]) > 0, "Test data should have at least one badge"

    # Verify NO badges have assigned_to (old schema)
    for badge_id, badge_data in sample_data[DATA_BADGES].items():
        assert DATA_BADGE_ASSIGNED_TO not in badge_data, (
            f"Badge {badge_id} should not have assigned_to in pre-migration data"
        )

    # Setup integration with old schema data (triggers migration)
    mock_config_entry_for_migration.add_to_hass(hass)

    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        return_value=sample_data,
    ):
        assert await hass.config_entries.async_setup(
            mock_config_entry_for_migration.entry_id
        )
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][mock_config_entry_for_migration.entry_id][
        COORDINATOR
    ]

    # Verify all badges now have assigned_to field as empty list
    for badge_id, badge_data in coordinator._data[DATA_BADGES].items():
        assert DATA_BADGE_ASSIGNED_TO in badge_data, (
            f"Badge {badge_id} missing assigned_to after migration"
        )
        assert badge_data[DATA_BADGE_ASSIGNED_TO] == [], (
            f"Badge {badge_id} assigned_to should be empty list, got {badge_data[DATA_BADGE_ASSIGNED_TO]}"
        )
        assert isinstance(badge_data[DATA_BADGE_ASSIGNED_TO], list), (
            f"Badge {badge_id} assigned_to should be a list"
        )
