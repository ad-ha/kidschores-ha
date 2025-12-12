# File: storage_manager.py
"""Handles persistent data storage for the KidsChores integration.

Uses Home Assistant's Storage helper to save and load chore-related data, ensuring
the state is preserved across restarts. This includes data for kids, chores,
badges, rewards, penalties, and their statuses.
"""

import os

from homeassistant.helpers.storage import Store

from . import const


class KidsChoresStorageManager:
    """Manages loading, saving, and accessing data from Home Assistant's storage.

    Utilizes internal_id as the primary key for all entities.
    """

    def __init__(self, hass, storage_key=const.STORAGE_KEY):
        """Initialize the storage manager.

        Args:
            hass: Home Assistant core object.
            storage_key: Key to identify storage location (default: const.STORAGE_KEY).

        """
        self.hass = hass
        self._storage_key = storage_key
        self._store = Store(hass, const.STORAGE_VERSION, storage_key)
        self._data = {}  # In-memory data cache for quick access.

    async def async_initialize(self):
        """Load data from storage during startup.

        If no data exists, initializes with an empty structure.
        """
        const.LOGGER.debug("DEBUG: KidsChoresStorageManager: Loading data from storage")
        existing_data = await self._store.async_load()

        if existing_data is None:
            # No existing data, create a new default structure.
            const.LOGGER.info("INFO: No existing storage found. Initializing new data")
            self._data = {
                const.DATA_KIDS: {},
                const.DATA_CHORES: {},
                const.DATA_BADGES: {},
                const.DATA_REWARDS: {},
                const.DATA_PENALTIES: {},
                const.DATA_BONUSES: {},
                const.DATA_PARENTS: {},
                const.DATA_ACHIEVEMENTS: {},
                const.DATA_CHALLENGES: {},
                const.DATA_PENDING_CHORE_APPROVALS: [],
                const.DATA_PENDING_REWARD_APPROVALS: [],
            }
        else:
            # Load existing data into memory.
            self._data = existing_data
            const.LOGGER.info("INFO: Storage data loaded successfully")

    @property
    def data(self):
        """Retrieve the in-memory data cache."""
        return self._data

    def get_data(self):
        """Retrieve the data structure (alternative getter)."""
        return self._data

    def set_data(self, new_data: dict):
        """Replace the entire in-memory data structure."""
        self._data = new_data

    def get_kids(self):
        """Retrieve the kids data."""
        return self._data.get(const.DATA_KIDS, {})

    def get_parents(self):
        """Retrieve the parents data."""
        return self._data.get(const.DATA_PARENTS, {})

    def get_chores(self):
        """Retrieve the chores data."""
        return self._data.get(const.DATA_CHORES, {})

    def get_badges(self):
        """Retrieve the badges data."""
        return self._data.get(const.DATA_BADGES, {})

    def get_rewards(self):
        """Retrieve the rewards data."""
        return self._data.get(const.DATA_REWARDS, {})

    def get_penalties(self):
        """Retrieve the penalties data."""
        return self._data.get(const.DATA_PENALTIES, {})

    def get_bonuses(self):
        """Retrieve the bonuses data."""
        return self._data.get(const.DATA_BONUSES, {})

    def get_achievements(self):
        """Retrieve the achievements data."""
        return self._data.get(const.DATA_ACHIEVEMENTS, {})

    def get_challenges(self):
        """Retrieve the challenges data."""
        return self._data.get(const.DATA_CHALLENGES, {})

    def get_pending_chore_approvals(self):
        """Retrieve the pending chore approvals data."""
        return self._data.get(const.DATA_PENDING_CHORE_APPROVALS, [])

    def get_pending_reward_aprovals(self):
        """Retrieve the pending reward approvals data."""
        return self._data.get(const.DATA_PENDING_REWARD_APPROVALS, [])

    async def link_user_to_kid(self, user_id, kid_id):
        """Link a Home Assistant user ID to a specific kid by internal_id."""

        if "linked_users" not in self._data:
            self._data["linked_users"] = {}
        self._data["linked_users"][user_id] = kid_id
        await self.async_save()

    async def unlink_user(self, user_id):
        """Unlink a Home Assistant user ID from any kid."""

        if "linked_users" in self._data and user_id in self._data["linked_users"]:
            del self._data["linked_users"][user_id]
            await self.async_save()

    async def get_linked_kids(self):
        """Get all linked users and their associated kids."""

        return self._data.get("linked_users", {})

    async def async_save(self):
        """Save the current data structure to storage asynchronously."""
        try:
            await self._store.async_save(self._data)
            const.LOGGER.debug("DEBUG: Data saved successfully to storage")
        except Exception as e:
            const.LOGGER.error("ERROR: Failed to save data to storage: %s", e)

    async def async_clear_data(self):
        """Clear all stored data and reset to default structure."""

        const.LOGGER.warning(
            "WARNING: Clearing all KidsChores data and resetting storage"
        )
        # Completely clear any existing data.
        self._data.clear()

        # Set the default empty structure
        self._data = {
            const.DATA_KIDS: {},
            const.DATA_CHORES: {},
            const.DATA_BADGES: {},
            const.DATA_REWARDS: {},
            const.DATA_PARENTS: {},
            const.DATA_PENALTIES: {},
            const.DATA_BONUSES: {},
            const.DATA_ACHIEVEMENTS: {},
            const.DATA_CHALLENGES: {},
            const.DATA_PENDING_REWARD_APPROVALS: [],
            const.DATA_PENDING_CHORE_APPROVALS: [],
        }
        await self.async_save()

    async def async_delete_storage(self) -> None:
        """Delete the storage file completely from disk."""

        # First clear in-memory data
        await self.async_clear_data()

        # Remove the file if it exists
        if os.path.isfile(self._store.path):
            try:
                os.remove(self._store.path)
                const.LOGGER.info("INFO: Storage file removed: %s", self._store.path)
            except Exception as e:
                const.LOGGER.error("ERROR: Failed to remove storage file: %s", e)
        else:
            const.LOGGER.info("INFO: Storage file not found: %s", self._store.path)

    async def async_update_data(self, key, value):
        """Update a specific section of the data structure."""

        if key in self._data:
            const.LOGGER.debug("DEBUG: Updating data for key: %s", key)
            self._data[key] = value
            await self.async_save()
        else:
            const.LOGGER.warning(
                "WARNING: Attempted to update unknown data key: %s", key
            )
