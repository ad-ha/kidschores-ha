# File: storage_manager.py
"""Handles persistent data storage for the KidsChores integration.

Uses Home Assistant's Storage helper to save and load chore-related data, ensuring
the state is preserved across restarts. This includes data for kids, chores,
badges, rewards, penalties, and their statuses.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from . import const


class KidsChoresStorageManager:
    """Manages loading, saving, and accessing data from Home Assistant's storage.

    Utilizes internal_id as the primary key for all entities.
    """

    def __init__(
        self, hass: HomeAssistant, storage_key: str = const.STORAGE_KEY
    ) -> None:
        """Initialize the storage manager.

        Args:
            hass: Home Assistant core object.
            storage_key: Key to identify storage location (default: const.STORAGE_KEY).

        """
        self.hass = hass
        self._storage_key = storage_key
        self._store: Store = Store(hass, const.STORAGE_VERSION, storage_key)
        self._data: dict[str, Any] = {}  # In-memory data cache for quick access.

    def _get_default_structure(self) -> dict[str, Any]:
        """Get the default empty data structure.

        Returns:
            dict: Default structure with all data keys initialized.
        """
        from datetime import datetime

        from homeassistant.util import dt as dt_util

        return {
            const.DATA_META: {
                const.DATA_META_SCHEMA_VERSION: const.DEFAULT_ZERO,  # Will be set by migration
                const.DATA_META_LAST_MIGRATION_DATE: datetime.now(
                    dt_util.UTC
                ).isoformat(),
                const.DATA_META_MIGRATIONS_APPLIED: [],
            },
            const.DATA_SCHEMA_VERSION: const.DEFAULT_ZERO,  # Top-level schema version for backward compatibility
            const.DATA_KIDS: {},
            const.DATA_CHORES: {},
            const.DATA_BADGES: {},
            const.DATA_REWARDS: {},
            const.DATA_PENALTIES: {},
            const.DATA_BONUSES: {},
            const.DATA_PARENTS: {},
            const.DATA_ACHIEVEMENTS: {},
            const.DATA_CHALLENGES: {},
            # Legacy queues removed in v0.4.0 - computed from timestamps/reward_data
        }

    async def async_initialize(self) -> None:
        """Load data from storage during startup.

        If no data exists, initializes with an empty structure.
        """
        const.LOGGER.debug("DEBUG: KidsChoresStorageManager: Loading data from storage")
        existing_data = await self._store.async_load()

        # DEBUG: Check what async_load returned
        if existing_data:
            const.LOGGER.debug(
                "DEBUG: async_load() returned keys: %s", list(existing_data.keys())[:5]
            )

        if existing_data is None:
            # No existing data, create a new default structure.
            const.LOGGER.info("INFO: No existing storage found. Initializing new data")
            self._data = self._get_default_structure()
            const.LOGGER.debug(
                "DEBUG: Initialized with default structure: %s keys",
                len(self._data.keys()),
            )
        else:
            # Load existing data into memory.
            self._data = existing_data
            const.LOGGER.debug(
                "DEBUG: Loaded existing data from storage: %s entities",
                {
                    "kids": len(self._data.get(const.DATA_KIDS, {})),
                    "chores": len(self._data.get(const.DATA_CHORES, {})),
                    "badges": len(self._data.get(const.DATA_BADGES, {})),
                    "total_keys": len(self._data.keys()),
                },
            )

    @property
    def data(self) -> dict[str, Any]:
        """Retrieve the in-memory data cache."""
        const.LOGGER.debug(
            "DEBUG: Storage manager data property accessed: %s entities",
            {
                "kids": len(self._data.get(const.DATA_KIDS, {})),
                "chores": len(self._data.get(const.DATA_CHORES, {})),
                "badges": len(self._data.get(const.DATA_BADGES, {})),
                "total_keys": len(self._data.keys()),
            },
        )
        return self._data

    def get_storage_path(self) -> str:
        """Get the storage file path.

        Returns:
            str: The absolute path to the storage file.
        """
        return self._store.path

    def set_data(self, new_data: dict[str, Any]) -> None:
        """Replace the entire in-memory data structure."""
        const.LOGGER.debug(
            "DEBUG: Storage manager set_data called with: %s entities",
            {
                "kids": len(new_data.get(const.DATA_KIDS, {})),
                "chores": len(new_data.get(const.DATA_CHORES, {})),
                "badges": len(new_data.get(const.DATA_BADGES, {})),
                "total_keys": len(new_data.keys()),
            },
        )
        self._data = new_data

    def get_kids(self) -> dict[str, Any]:
        """Retrieve the kids data."""
        return self._data.get(const.DATA_KIDS, {})

    def get_parents(self) -> dict[str, Any]:
        """Retrieve the parents data."""
        return self._data.get(const.DATA_PARENTS, {})

    def get_chores(self) -> dict[str, Any]:
        """Retrieve the chores data."""
        return self._data.get(const.DATA_CHORES, {})

    def get_badges(self) -> dict[str, Any]:
        """Retrieve the badges data."""
        return self._data.get(const.DATA_BADGES, {})

    def get_rewards(self) -> dict[str, Any]:
        """Retrieve the rewards data."""
        return self._data.get(const.DATA_REWARDS, {})

    def get_penalties(self) -> dict[str, Any]:
        """Retrieve the penalties data."""
        return self._data.get(const.DATA_PENALTIES, {})

    def get_bonuses(self) -> dict[str, Any]:
        """Retrieve the bonuses data."""
        return self._data.get(const.DATA_BONUSES, {})

    def get_achievements(self) -> dict[str, Any]:
        """Retrieve the achievements data."""
        return self._data.get(const.DATA_ACHIEVEMENTS, {})

    def get_challenges(self) -> dict[str, Any]:
        """Retrieve the challenges data."""
        return self._data.get(const.DATA_CHALLENGES, {})

    # get_pending_chore_approvals removed - use coordinator.pending_chore_approvals
    # which computes from timestamps dynamically

    # get_pending_reward_approvals removed - use coordinator.pending_reward_approvals
    # which computes from reward_data dynamically

    async def link_user_to_kid(self, user_id: str, kid_id: str) -> None:
        """Link a Home Assistant user ID to a specific kid by internal_id."""

        if const.STORAGE_KEY_LINKED_USERS not in self._data:
            self._data[const.STORAGE_KEY_LINKED_USERS] = {}
        self._data[const.STORAGE_KEY_LINKED_USERS][user_id] = kid_id
        await self.async_save()

    async def unlink_user(self, user_id: str) -> None:
        """Unlink a Home Assistant user ID from any kid."""

        if (
            const.STORAGE_KEY_LINKED_USERS in self._data
            and user_id in self._data[const.STORAGE_KEY_LINKED_USERS]
        ):
            del self._data[const.STORAGE_KEY_LINKED_USERS][user_id]
            await self.async_save()

    async def get_linked_kids(self) -> dict[str, str]:
        """Get all linked users and their associated kids."""

        return self._data.get(const.STORAGE_KEY_LINKED_USERS, {})

    async def async_save(self) -> None:
        """Save the current data structure to storage asynchronously.

        Raises:
            No exceptions raised - errors are logged but do not stop execution.
            OSError: Logged when file system issues prevent saving.
            TypeError: Logged when data contains non-serializable types.
            ValueError: Logged when data is invalid for JSON serialization.
        """
        try:
            await self._store.async_save(self._data)
            const.LOGGER.debug("DEBUG: Data saved successfully to storage")
        except OSError as err:
            const.LOGGER.error(
                "ERROR: Failed to save storage due to file system error: %s. "
                "Check disk space and file permissions for %s",
                err,
                self._store.path,
            )
        except TypeError as err:
            const.LOGGER.error(
                "ERROR: Failed to save storage due to non-serializable data: %s. "
                "Data contains types that cannot be converted to JSON",
                err,
            )
        except ValueError as err:
            const.LOGGER.error(
                "ERROR: Failed to save storage due to invalid data format: %s. "
                "Data structure may be corrupted",
                err,
            )

    async def async_clear_data(self) -> None:
        """Clear all stored data and reset to default structure."""

        const.LOGGER.warning(
            "WARNING: Clearing all KidsChores data and resetting storage"
        )
        # Completely clear any existing data.
        self._data.clear()

        # Set the default empty structure
        self._data = self._get_default_structure()
        await self.async_save()

    async def async_delete_storage(self) -> None:
        """Delete the storage file completely from disk.

        This clears all in-memory data and removes the storage file using
        Home Assistant's Store API for proper file handling.
        """
        # First clear in-memory data
        await self.async_clear_data()

        # Remove the file using Store API
        try:
            await self._store.async_remove()
            const.LOGGER.info(
                "INFO: Storage file removed successfully: %s",
                self._store.path,
            )
        except OSError as err:
            const.LOGGER.error(
                "ERROR: Failed to remove storage file %s: %s. Check file permissions",
                self._store.path,
                err,
            )

    async def async_update_data(self, key: str, value: Any) -> None:
        """Update a specific section of the data structure.

        Args:
            key: The data key to update (e.g., const.DATA_KIDS, const.DATA_CHORES).
            value: The new value for the specified key.

        Note:
            If the key doesn't exist, a warning is logged and no update occurs.
            Valid keys are defined in const.py (DATA_KIDS, DATA_CHORES, etc.).
        """
        if key in self._data:
            const.LOGGER.debug("DEBUG: Updating data for key: %s", key)
            self._data[key] = value
            await self.async_save()
        else:
            const.LOGGER.warning(
                "WARNING: Attempted to update unknown data key '%s'. Valid keys: %s",
                key,
                ", ".join(self._data.keys()),
            )
