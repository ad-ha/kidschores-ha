"""Tests for KidsChores diagnostics module.

Tests diagnostics export returns raw storage data directly.
Validates byte-for-byte compatibility with storage file for paste recovery.
"""

# pylint: disable=redefined-outer-name  # Pytest fixtures shadow names
# pylint: disable=unused-argument  # Some fixtures needed for setup only

from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from custom_components.kidschores import const
from custom_components.kidschores.diagnostics import (
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_storage_data():
    """Create mock raw storage data (simulates kidschores_data file)."""
    return {
        const.DATA_KIDS: {
            "kid1": {
                const.DATA_KID_NAME: "Alice",
                const.DATA_KID_INTERNAL_ID: "kid1",
                const.DATA_KID_POINTS: 100,
            },
            "kid2": {
                const.DATA_KID_NAME: "Bob",
                const.DATA_KID_INTERNAL_ID: "kid2",
                const.DATA_KID_POINTS: 50,
            },
        },
        const.DATA_CHORES: {
            "chore1": {
                const.DATA_CHORE_NAME: "Clean Room",
                const.DATA_CHORE_INTERNAL_ID: "chore1",
            },
        },
        const.DATA_REWARDS: {},
        const.DATA_PENALTIES: {},
        const.DATA_BONUSES: {},
        const.DATA_BADGES: {},
        const.DATA_PARENTS: {},
        const.DATA_ACHIEVEMENTS: {},
        const.DATA_CHALLENGES: {},
        const.DATA_SCHEMA_VERSION: 0,
    }


@pytest.fixture
def mock_coordinator(mock_storage_data):
    """Create a mock coordinator with storage manager."""
    coordinator = MagicMock()

    # Mock storage manager with raw data
    storage_manager = MagicMock()
    storage_manager.data = mock_storage_data
    coordinator.storage_manager = storage_manager

    # Mock convenience accessors (point to same data)
    coordinator.kids_data = mock_storage_data[const.DATA_KIDS]

    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.version = 1
    entry.title = "KidsChores"
    return entry


@pytest.fixture
def mock_hass(mock_coordinator, mock_config_entry):
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {
        const.DOMAIN: {
            mock_config_entry.entry_id: {
                const.COORDINATOR: mock_coordinator,
            }
        }
    }
    return hass


@pytest.fixture
def mock_device_entry():
    """Create a mock device entry."""
    device = MagicMock(spec=DeviceEntry)
    device.identifiers = {(const.DOMAIN, "kid1")}
    return device


async def test_config_entry_diagnostics_returns_raw_storage(
    mock_hass, mock_config_entry, mock_coordinator, mock_storage_data
):
    """Test diagnostics returns raw storage data directly."""
    result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

    # Verify result is identical to storage data
    assert result == mock_storage_data
    assert result is mock_coordinator.storage_manager.data


async def test_config_entry_diagnostics_has_all_storage_keys(
    mock_hass, mock_config_entry, mock_coordinator
):
    """Test diagnostics includes all core storage keys."""
    result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

    # Verify all core storage keys are present
    assert const.DATA_KIDS in result
    assert const.DATA_CHORES in result
    assert const.DATA_REWARDS in result
    assert const.DATA_PENALTIES in result
    assert const.DATA_BONUSES in result
    assert const.DATA_BADGES in result
    assert const.DATA_PARENTS in result
    assert const.DATA_ACHIEVEMENTS in result
    assert const.DATA_CHALLENGES in result
    assert const.DATA_SCHEMA_VERSION in result


async def test_config_entry_diagnostics_byte_for_byte_compatibility(
    mock_hass, mock_config_entry, mock_coordinator, mock_storage_data
):
    """Test diagnostics export is byte-for-byte identical to storage file.

    This ensures the diagnostics JSON can be pasted directly during
    data recovery without any transformation.
    """
    result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

    # Verify it's the exact same dict object (no copying/reformatting)
    assert result is mock_storage_data

    # Verify kids data structure preserved exactly
    assert result[const.DATA_KIDS]["kid1"][const.DATA_KID_NAME] == "Alice"
    assert result[const.DATA_KIDS]["kid1"][const.DATA_KID_POINTS] == 100
    assert result[const.DATA_KIDS]["kid2"][const.DATA_KID_NAME] == "Bob"

    # Verify chores data structure preserved exactly
    assert result[const.DATA_CHORES]["chore1"][const.DATA_CHORE_NAME] == "Clean Room"


async def test_device_diagnostics_returns_kid_data(
    mock_hass, mock_config_entry, mock_device_entry, mock_coordinator
):
    """Test device diagnostics returns kid-specific data."""
    result = await async_get_device_diagnostics(
        mock_hass, mock_config_entry, mock_device_entry
    )

    # Verify structure
    assert "kid_id" in result
    assert "kid_data" in result

    # Verify kid data
    assert result["kid_id"] == "kid1"
    assert result["kid_data"][const.DATA_KID_NAME] == "Alice"
    assert result["kid_data"][const.DATA_KID_POINTS] == 100


async def test_device_diagnostics_missing_kid_id(
    mock_hass, mock_config_entry, mock_coordinator
):
    """Test device diagnostics error when kid_id cannot be determined."""
    # Create device with no identifiers
    device = MagicMock(spec=DeviceEntry)
    device.identifiers = set()

    result = await async_get_device_diagnostics(mock_hass, mock_config_entry, device)

    # Verify error response
    assert "error" in result
    assert "Could not determine kid_id" in result["error"]


async def test_device_diagnostics_kid_not_found(
    mock_hass, mock_config_entry, mock_coordinator
):
    """Test device diagnostics error when kid data not found."""
    # Create device with non-existent kid_id
    device = MagicMock(spec=DeviceEntry)
    device.identifiers = {(const.DOMAIN, "nonexistent_kid")}

    result = await async_get_device_diagnostics(mock_hass, mock_config_entry, device)

    # Verify error response
    assert "error" in result
    assert "Kid data not found for kid_id: nonexistent_kid" in result["error"]


async def test_diagnostics_simplicity():
    """Test that diagnostics implementation is simple and maintainable.

    The simplified approach:
    - Config entry diagnostics: Returns storage_manager.data directly
    - Device diagnostics: Returns kid_data snapshot only
    - No parsing, reformatting, or wrapper metadata
    - Byte-for-byte identical to storage file
    - Future-proof (all storage keys automatically included)
    - Coordinator migration handles schema differences
    """
    # This is a documentation test confirming the design decision.
    # The actual simplicity is validated by the implementation having:
    # - Single line return for config entry diagnostics
    # - Minimal processing for device diagnostics
    # - No custom data structures or transformations
    pass
