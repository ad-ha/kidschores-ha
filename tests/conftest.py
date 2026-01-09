"""Modern test fixtures for KidsChores integration tests.

This conftest provides ONLY the core fixtures needed for modern testing:
1. pytest_plugins for HA test framework
2. auto_enable_custom_integrations autouse fixture
3. mock_hass_users for authorization testing
4. mock_config_entry for basic integration setup
5. init_integration for full integration setup

Modern tests get entity IDs from the dashboard helper sensor - NEVER construct them.
See tests/AGENT_TEST_CREATION_INSTRUCTIONS.md for the proper pattern.

For legacy tests using direct coordinator manipulation, see tests/legacy/conftest.py.
"""

# pylint: disable=redefined-outer-name

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import DOMAIN

# ---------------------------------------------------------------------------
# Core pytest plugin registration (REQUIRED at top-level)
# ---------------------------------------------------------------------------

pytest_plugins = "pytest_homeassistant_custom_component"


# ---------------------------------------------------------------------------
# Autouse fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: Any,  # noqa: ARG001  # Required fixture dependency
) -> Any:
    """Enable custom integrations in all tests."""
    yield


# ---------------------------------------------------------------------------
# User fixtures for authorization testing
# ---------------------------------------------------------------------------


@pytest.fixture
async def mock_hass_users(hass: HomeAssistant) -> dict[str, Any]:
    """Create mock Home Assistant users for testing.

    User keys match ha_user_name values expected in test YAML files:
    - parent1, parent2: Parent users (can approve chores)
    - kid1, kid2, kid3: Kid users (can claim chores)
    - admin: System admin

    Usage in tests:
        from homeassistant.core import Context
        kid_context = Context(user_id=mock_hass_users["kid1"].id)
        parent_context = Context(user_id=mock_hass_users["parent1"].id)
    """
    admin_user = await hass.auth.async_create_user(
        "Admin User",
        group_ids=["system-admin"],
    )

    parent1_user = await hass.auth.async_create_user(
        "Parent One",
        group_ids=["system-users"],
    )
    parent2_user = await hass.auth.async_create_user(
        "Parent Two",
        group_ids=["system-users"],
    )

    kid1_user = await hass.auth.async_create_user(
        "Kid One",
        group_ids=["system-users"],
    )
    kid2_user = await hass.auth.async_create_user(
        "Kid Two",
        group_ids=["system-users"],
    )
    kid3_user = await hass.auth.async_create_user(
        "Kid Three",
        group_ids=["system-users"],
    )

    return {
        "admin": admin_user,
        "parent1": parent1_user,
        "parent2": parent2_user,
        "kid1": kid1_user,
        "kid2": kid2_user,
        "kid3": kid3_user,
    }


# ---------------------------------------------------------------------------
# Config entry fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a minimal config entry for KidsChores.

    Note: KidsChores v4.2+ stores entity data in .storage/kidschores_data,
    NOT in config_entry.data. The config_entry only holds system settings.
    """
    return MockConfigEntry(
        domain=DOMAIN,
        title="KidsChores",
        data={},  # Empty - data lives in storage
        options={},
        unique_id=None,
    )


@pytest.fixture
def mock_storage_data() -> dict[str, dict]:
    """Provide empty storage structure for testing initialization."""
    return {
        "meta": {"schema_version": 42},
        "kids": {},
        "parents": {},
        "chores": {},
        "badges": {},
        "rewards": {},
        "bonuses": {},
        "penalties": {},
        "achievements": {},
        "challenges": {},
        "pending_approvals": {"chores": {}, "rewards": {}},
    }


@pytest.fixture
def mock_storage_manager(mock_storage_data: dict) -> MagicMock:
    """Provide a mocked storage manager for unit testing without file I/O."""
    manager = MagicMock()
    manager.async_load.return_value = mock_storage_data
    manager.get_data.return_value = mock_storage_data
    manager.async_save.return_value = None
    return manager


# ---------------------------------------------------------------------------
# Integration setup fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> MockConfigEntry:
    """Set up KidsChores integration with empty data.

    This loads the integration fully (coordinator + all entity platforms)
    but with no kids, chores, etc. Use scenario fixtures for populated data.

    Returns the config entry after successful setup.
    """
    mock_config_entry.add_to_hass(hass)

    # Patch storage to avoid filesystem access (using HA's Store directly)
    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        return_value={
            "meta": {"schema_version": 42},
            "kids": {},
            "parents": {},
            "chores": {},
            "badges": {},
            "rewards": {},
            "bonuses": {},
            "penalties": {},
            "achievements": {},
            "challenges": {},
            "pending_approvals": {"chores": {}, "rewards": {}},
        },
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    return mock_config_entry
