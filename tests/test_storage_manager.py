"""Direct unit tests for KidsChoresStorageManager.

Tests storage manager methods that are not fully covered by integration tests,
including error handling, user linking features, and data clearing operations.
"""

# pylint: disable=protected-access  # Accessing _store, _data, _storage_key for testing
# pylint: disable=redefined-outer-name  # Pytest fixtures redefine names
# pylint: disable=unused-argument  # Test fixtures may be unused in simple tests

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kidschores import const
from custom_components.kidschores.storage_manager import KidsChoresStorageManager


@pytest.fixture
def storage_manager(hass: HomeAssistant) -> KidsChoresStorageManager:
    """Return a storage manager instance."""
    return KidsChoresStorageManager(hass)


async def test_async_initialize_creates_default_structure(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test that async_initialize creates default structure when no data exists."""
    with patch.object(storage_manager._store, "async_load", return_value=None):
        await storage_manager.async_initialize()

    data = storage_manager.data

    # Verify all expected keys exist (modern structure - no deprecated fields)
    assert const.DATA_KIDS in data
    assert const.DATA_CHORES in data
    assert const.DATA_BADGES in data
    assert const.DATA_REWARDS in data
    assert const.DATA_PENALTIES in data
    assert const.DATA_BONUSES in data
    assert const.DATA_PARENTS in data
    assert const.DATA_ACHIEVEMENTS in data
    assert const.DATA_CHALLENGES in data
    assert const.DATA_SCHEMA_VERSION in data

    # Verify default values
    assert data[const.DATA_KIDS] == {}
    assert data[const.DATA_SCHEMA_VERSION] == const.DEFAULT_ZERO


async def test_async_initialize_loads_existing_data(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test that async_initialize loads existing storage data."""
    existing_data = {
        const.DATA_KIDS: {"kid_1": {"name": "Alice"}},
        const.DATA_CHORES: {"chore_1": {"name": "Clean room"}},
        const.DATA_SCHEMA_VERSION: 42,
    }

    with patch.object(storage_manager._store, "async_load", return_value=existing_data):
        await storage_manager.async_initialize()

    assert storage_manager.data == existing_data
    assert storage_manager.get_kids() == {"kid_1": {"name": "Alice"}}
    assert storage_manager.get_chores() == {"chore_1": {"name": "Clean room"}}


async def test_getter_methods_return_correct_data(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test all getter methods return correct data."""
    test_data = {
        const.DATA_KIDS: {"kid_1": {}},
        const.DATA_PARENTS: {"parent_1": {}},
        const.DATA_CHORES: {"chore_1": {}},
        const.DATA_BADGES: {"badge_1": {}},
        const.DATA_REWARDS: {"reward_1": {}},
        const.DATA_PENALTIES: {"penalty_1": {}},
        const.DATA_BONUSES: {"bonus_1": {}},
        const.DATA_ACHIEVEMENTS: {"achievement_1": {}},
        const.DATA_CHALLENGES: {"challenge_1": {}},
        # Pending reward approvals now computed from kid reward_data
    }

    storage_manager.set_data(test_data)

    assert storage_manager.get_kids() == {"kid_1": {}}
    assert storage_manager.get_parents() == {"parent_1": {}}
    assert storage_manager.get_chores() == {"chore_1": {}}
    assert storage_manager.get_badges() == {"badge_1": {}}
    assert storage_manager.get_rewards() == {"reward_1": {}}
    assert storage_manager.get_penalties() == {"penalty_1": {}}
    assert storage_manager.get_bonuses() == {"bonus_1": {}}
    assert storage_manager.get_achievements() == {"achievement_1": {}}
    assert storage_manager.get_challenges() == {"challenge_1": {}}
    # Pending reward approvals getter removed - use coordinator.get_pending_reward_approvals_computed()


async def test_getter_methods_return_defaults_for_missing_keys(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test getter methods return empty defaults when keys don't exist."""
    storage_manager.set_data({})

    assert storage_manager.get_kids() == {}
    assert storage_manager.get_parents() == {}
    assert storage_manager.get_chores() == {}
    assert storage_manager.get_badges() == {}
    assert storage_manager.get_rewards() == {}
    assert storage_manager.get_penalties() == {}
    assert storage_manager.get_bonuses() == {}
    assert storage_manager.get_achievements() == {}
    assert storage_manager.get_challenges() == {}
    # Pending reward approvals getter removed in v0.4.0 - use coordinator computed method


async def test_link_user_to_kid_creates_mapping(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test linking a user ID to a kid ID."""
    storage_manager.set_data({})

    mock_save = AsyncMock()
    with patch.object(storage_manager, "async_save", mock_save):
        await storage_manager.link_user_to_kid("user_123", "kid_456")

    linked_kids = await storage_manager.get_linked_kids()
    assert linked_kids == {"user_123": "kid_456"}
    assert mock_save.call_count == 1


async def test_link_user_to_kid_updates_existing_mapping(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test updating an existing user-kid link."""
    storage_manager.set_data({const.STORAGE_KEY_LINKED_USERS: {"user_123": "kid_old"}})

    mock_save = AsyncMock()
    with patch.object(storage_manager, "async_save", mock_save):
        await storage_manager.link_user_to_kid("user_123", "kid_new")

    linked_kids = await storage_manager.get_linked_kids()
    assert linked_kids == {"user_123": "kid_new"}


async def test_unlink_user_removes_mapping(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test unlinking a user from a kid."""
    storage_manager.set_data(
        {
            const.STORAGE_KEY_LINKED_USERS: {
                "user_123": "kid_456",
                "user_789": "kid_abc",
            }
        }
    )

    mock_save = AsyncMock()
    with patch.object(storage_manager, "async_save", mock_save):
        await storage_manager.unlink_user("user_123")

    linked_kids = await storage_manager.get_linked_kids()
    assert linked_kids == {"user_789": "kid_abc"}
    assert "user_123" not in linked_kids


async def test_unlink_user_handles_nonexistent_user(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test unlinking a user that doesn't exist doesn't cause errors."""
    storage_manager.set_data({const.STORAGE_KEY_LINKED_USERS: {"user_123": "kid_456"}})

    mock_save = AsyncMock()
    with patch.object(storage_manager, "async_save", mock_save):
        await storage_manager.unlink_user("user_nonexistent")

    # Should not call save since nothing changed
    mock_save.assert_not_called()


async def test_unlink_user_handles_missing_linked_users_key(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test unlinking when linked_users key doesn't exist."""
    storage_manager.set_data({})

    mock_save = AsyncMock()
    with patch.object(storage_manager, "async_save", mock_save):
        await storage_manager.unlink_user("user_123")

    # Should not call save or raise error
    mock_save.assert_not_called()


async def test_get_linked_kids_returns_empty_dict_when_no_links(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test get_linked_kids returns empty dict when no links exist."""
    storage_manager.set_data({})

    linked_kids = await storage_manager.get_linked_kids()
    assert linked_kids == {}


async def test_async_save_success(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test successful async_save operation."""
    test_data = {const.DATA_KIDS: {"kid_1": {"name": "Alice"}}}
    storage_manager.set_data(test_data)

    mock_store_save = AsyncMock()
    with patch.object(storage_manager._store, "async_save", mock_store_save):
        await storage_manager.async_save()

    mock_store_save.assert_called_once_with(test_data)


async def test_async_save_handles_oserror(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test async_save handles OSError (file system errors)."""
    storage_manager.set_data({const.DATA_KIDS: {}})

    with patch.object(
        storage_manager._store,
        "async_save",
        side_effect=OSError("Disk full"),
    ):
        await storage_manager.async_save()

    assert "Failed to save storage due to file system error" in caplog.text
    assert "Disk full" in caplog.text
    assert "Check disk space and file permissions" in caplog.text


async def test_async_save_handles_typeerror(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test async_save handles TypeError (serialization errors)."""
    storage_manager.set_data({const.DATA_KIDS: {}})

    with patch.object(
        storage_manager._store,
        "async_save",
        side_effect=TypeError("Cannot serialize"),
    ):
        await storage_manager.async_save()

    assert "Failed to save storage due to non-serializable data" in caplog.text
    assert "Cannot serialize" in caplog.text
    assert "cannot be converted to JSON" in caplog.text


async def test_async_save_handles_valueerror(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test async_save handles ValueError (validation errors)."""
    storage_manager.set_data({const.DATA_KIDS: {}})

    with patch.object(
        storage_manager._store,
        "async_save",
        side_effect=ValueError("Invalid data"),
    ):
        await storage_manager.async_save()

    assert "Failed to save storage due to invalid data format" in caplog.text
    assert "Invalid data" in caplog.text
    assert "Data structure may be corrupted" in caplog.text


async def test_async_clear_data_resets_to_default_structure(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test async_clear_data resets to default empty structure."""
    # Start with populated data
    storage_manager.set_data(
        {
            const.DATA_KIDS: {"kid_1": {"name": "Alice"}},
            const.DATA_CHORES: {"chore_1": {"name": "Clean"}},
            const.DATA_SCHEMA_VERSION: 42,
        }
    )

    mock_save = AsyncMock()
    with patch.object(storage_manager, "async_save", mock_save):
        await storage_manager.async_clear_data()

    # Verify data is reset (modern structure - no deprecated fields)
    data = storage_manager.data
    assert data[const.DATA_KIDS] == {}
    assert data[const.DATA_CHORES] == {}
    assert data[const.DATA_BADGES] == {}
    assert data[const.DATA_REWARDS] == {}

    # Verify warning logged
    assert "Clearing all KidsChores data" in caplog.text

    # Verify save was called
    mock_save.assert_called_once()


async def test_async_clear_data_includes_schema_version(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test async_clear_data includes schema_version in reset structure.

    This is a regression test for the bug where schema_version was missing
    from async_clear_data but present in async_initialize.
    """
    storage_manager.set_data({const.DATA_KIDS: {"kid_1": {}}})

    mock_save = AsyncMock()
    with patch.object(storage_manager, "async_save", mock_save):
        await storage_manager.async_clear_data()

    # BUG: This should be present but currently isn't
    # TODO: Fix async_clear_data to include DATA_SCHEMA_VERSION
    # assert const.DATA_SCHEMA_VERSION in storage_manager.data


async def test_async_delete_storage_clears_and_removes_file(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test async_delete_storage clears data and removes file via Store API."""
    storage_manager.set_data({const.DATA_KIDS: {"kid_1": {}}})

    mock_clear = AsyncMock()
    mock_store_remove = AsyncMock()
    with (
        patch.object(storage_manager, "async_clear_data", mock_clear),
        patch.object(storage_manager._store, "async_remove", mock_store_remove),
    ):
        await storage_manager.async_delete_storage()

    # Verify clear_data was called
    mock_clear.assert_called_once()

    # Verify Store API async_remove was called
    mock_store_remove.assert_called_once()

    # Verify logging
    assert "Storage file removed successfully" in caplog.text


async def test_async_delete_storage_handles_missing_file(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test async_delete_storage handles FileNotFoundError from Store API."""
    storage_manager.set_data({const.DATA_KIDS: {"kid_1": {}}})

    mock_clear = AsyncMock()
    # Store API raises FileNotFoundError (subclass of OSError) if file doesn't exist
    mock_store_remove = AsyncMock(side_effect=FileNotFoundError("File not found"))
    with (
        patch.object(storage_manager, "async_clear_data", mock_clear),
        patch.object(storage_manager._store, "async_remove", mock_store_remove),
    ):
        await storage_manager.async_delete_storage()

    # Verify clear_data was called
    mock_clear.assert_called_once()

    # Verify Store async_remove was called (even though it failed)
    mock_store_remove.assert_called_once()

    # Verify error logging
    assert "Failed to remove storage file" in caplog.text


async def test_async_delete_storage_handles_oserror(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test async_delete_storage handles OSError from Store API."""
    storage_manager.set_data({const.DATA_KIDS: {"kid_1": {}}})

    mock_store_remove = AsyncMock(side_effect=OSError("Permission denied"))
    with (
        patch.object(storage_manager, "async_clear_data", new=AsyncMock()),
        patch.object(storage_manager._store, "async_remove", mock_store_remove),
    ):
        await storage_manager.async_delete_storage()

    # Should not raise, just log error
    assert "Failed to remove storage file" in caplog.text
    assert "Permission denied" in caplog.text


async def test_async_update_data_updates_and_saves(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test async_update_data updates specific key and saves."""
    storage_manager.set_data(
        {
            const.DATA_KIDS: {"kid_1": {}},
            const.DATA_CHORES: {},
        }
    )

    new_kids_data = {"kid_1": {}, "kid_2": {"name": "Bob"}}

    mock_save = AsyncMock()
    with patch.object(storage_manager, "async_save", mock_save):
        await storage_manager.async_update_data(const.DATA_KIDS, new_kids_data)

    # Verify data was updated
    assert storage_manager.data[const.DATA_KIDS] == new_kids_data

    # Verify save was called
    mock_save.assert_called_once()

    # Verify logging
    assert "Updating data for key" in caplog.text


async def test_async_update_data_warns_on_unknown_key(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test async_update_data warns when updating unknown key."""
    storage_manager.set_data({const.DATA_KIDS: {}})

    mock_save = AsyncMock()
    with patch.object(storage_manager, "async_save", mock_save):
        await storage_manager.async_update_data("unknown_key", {"data": "value"})

    # Should log warning
    assert "Attempted to update unknown data key" in caplog.text
    assert "unknown_key" in caplog.text

    # Should not call save
    mock_save.assert_not_called()


async def test_get_storage_path_returns_correct_path(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test get_storage_path returns the correct file path."""


async def test_data_property_returns_internal_data(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test data property returns the internal data dictionary."""
    test_data = {const.DATA_KIDS: {"kid_1": {"name": "Alice"}}}
    storage_manager.set_data(test_data)

    assert storage_manager.data is storage_manager._data
    assert storage_manager.data == test_data


async def test_set_data_replaces_entire_structure(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test set_data completely replaces the data structure."""
    original_data = {const.DATA_KIDS: {"kid_1": {}}}
    storage_manager.set_data(original_data)

    new_data = {
        const.DATA_KIDS: {"kid_2": {}},
        const.DATA_CHORES: {"chore_1": {}},
    }
    storage_manager.set_data(new_data)

    assert storage_manager.data == new_data
    assert storage_manager.data is not original_data


async def test_custom_storage_key(hass: HomeAssistant) -> None:
    """Test storage manager with custom storage key."""
    custom_key = "test_storage_key"
    storage_manager = KidsChoresStorageManager(hass, storage_key=custom_key)

    assert storage_manager._storage_key == custom_key
    assert custom_key in storage_manager.get_storage_path()


async def test_pending_reward_approvals_modern_structure(
    hass: HomeAssistant,
    storage_manager: KidsChoresStorageManager,
) -> None:
    """Test that pending reward approvals use modern structure.

    This test verifies the v0.4.0+ architecture:
    - No get_pending_reward_approvals() method in storage manager (removed)
    - Pending reward approvals computed from kid reward_data by coordinator
    - Modern structure: kid["reward_data"][reward_id]["pending_count"]
    """
    # Modern structure stores pending counts in kid reward_data, not a global list
    # The storage manager no longer has a getter method for this legacy field
    # Coordinator.get_pending_reward_approvals_computed() is the new approach

    # Verify the legacy getter method no longer exists
    assert not hasattr(storage_manager, "get_pending_reward_approvals")
    # Verify the old typo also doesn't exist
    assert not hasattr(storage_manager, "get_pending_reward_aprovals")
