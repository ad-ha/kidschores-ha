# File: storage_manager.py
"""Handles persistent data storage for the KidsChores integration.

Uses Home Assistant's Storage helper to save and load chore-related data, ensuring
the state is preserved across restarts. This includes data for kids, chores,
badges, rewards, penalties, and their statuses.
"""

import os

from homeassistant.helpers.storage import Store
from .const import (
    DATA_ACHIEVEMENTS,
    DATA_BADGES,
    DATA_BONUSES,
    DATA_CHALLENGES,
    DATA_CHORES,
    DATA_KIDS,
    DATA_PARENTS,
    DATA_PENALTIES,
    DATA_PENDING_CHORE_APPROVALS,
    DATA_PENDING_REWARD_APPROVALS,
    DATA_REWARDS,
    LOGGER,
    STORAGE_KEY,
    STORAGE_VERSION,
)


class KidsChoresStorageManager:
    """Manages loading, saving, and accessing data from Home Assistant's storage.

    Utilizes internal_id as the primary key for all entities.
    """

    def __init__(self, hass, storage_key=STORAGE_KEY):
        """Initialize the storage manager.

        Args:
            hass: Home Assistant core object.
            storage_key: Key to identify storage location (default: STORAGE_KEY).

        """
        self.hass = hass
        self._storage_key = storage_key
        self._store = Store(hass, STORAGE_VERSION, storage_key)
        self._data = {}  # In-memory data cache for quick access.

    async def async_initialize(self):
        """Load data from storage during startup.

        If no data exists, initializes with an empty structure.
        """
        LOGGER.debug("KidsChoresStorageManager: Loading data from storage")
        existing_data = await self._store.async_load()

        if existing_data is None:
            # No existing data, create a new default structure.
            LOGGER.info("No existing storage found; initializing new data")
            self._data = {
                DATA_KIDS: {},  # Dictionary of kids keyed by internal_id.
                DATA_CHORES: {},  # Dictionary of chores keyed by internal_id.
                DATA_BADGES: {},  # Dictionary of badges keyed by internal_id.
                DATA_REWARDS: {},  # Dictionary of rewards keyed by internal_id.
                DATA_PENALTIES: {},  # Dictionary of penalties keyed by internal_id.
                DATA_BONUSES: {},  # Dictionary of bonuses keyed by internal_id.
                DATA_PARENTS: {},  # Dictionary of parents keyed by internal_id.
                DATA_ACHIEVEMENTS: {},  # Dictionary of achievements keyed by internal_id.
                DATA_CHALLENGES: {},  # Dictionary of challenges keyed by internal_id.
                DATA_PENDING_CHORE_APPROVALS: [],  # List of pending chore approvals keyed by internal_id.
                DATA_PENDING_REWARD_APPROVALS: [],  # List of pending rewar approvals keyed by internal_id.
            }
        else:
            # Load existing data into memory.
            self._data = existing_data
            LOGGER.info("Storage data loaded successfully")

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
        return self._data.get(DATA_KIDS, {})

    def get_parents(self):
        """Retrieve the parents data."""
        return self._data.get(DATA_PARENTS, {})

    def get_chores(self):
        """Retrieve the chores data."""
        return self._data.get(DATA_CHORES, {})

    def get_badges(self):
        """Retrieve the badges data."""
        return self._data.get(DATA_BADGES, {})

    def get_rewards(self):
        """Retrieve the rewards data."""
        return self._data.get(DATA_REWARDS, {})

    def get_penalties(self):
        """Retrieve the penalties data."""
        return self._data.get(DATA_PENALTIES, {})

    def get_bonuses(self):
        """Retrieve the bonuses data."""
        return self._data.get(DATA_BONUSES, {})

    def get_achievements(self):
        """Retrieve the achievements data."""
        return self._data.get(DATA_ACHIEVEMENTS, {})

    def get_challenges(self):
        """Retrieve the challenges data."""
        return self._data.get(DATA_CHALLENGES, {})

    def get_pending_chore_approvals(self):
        """Retrieve the pending chore approvals data."""
        return self._data.get(DATA_PENDING_CHORE_APPROVALS, [])

    def get_pending_reward_aprovals(self):
        """Retrieve the pending reward approvals data."""
        return self._data.get(DATA_PENDING_REWARD_APPROVALS, [])

    async def link_user_to_kid(self, user_id, kid_id):
        """Link a Home Assistant user ID to a specific kid by internal_id."""

        if "linked_users" not in self._data:
            self._data["linked_users"] = {}
        self._data["linked_users"][user_id] = kid_id
        await self._save()

    async def unlink_user(self, user_id):
        """Unlink a Home Assistant user ID from any kid."""

        if "linked_users" in self._data and user_id in self._data["linked_users"]:
            del self._data["linked_users"][user_id]
            await self._save()

    async def get_linked_kids(self):
        """Get all linked users and their associated kids."""

        return self._data.get("linked_users", {})

    async def async_save(self):
        """Save the current data structure to storage asynchronously."""
        try:
            await self._store.async_save(self._data)
            LOGGER.info("Data saved successfully to storage")
        except Exception as e:
            LOGGER.error("Failed to save data to storage: %s", e)

    async def async_clear_data(self):
        """Clear all stored data and reset to default structure."""

        LOGGER.warning("Clearing all KidsChores data and resetting storage")
        self._data = {
            DATA_KIDS: {},
            DATA_CHORES: {},
            DATA_BADGES: {},
            DATA_REWARDS: {},
            DATA_PARENTS: {},
            DATA_PENALTIES: {},
            DATA_BONUSES: {},
            DATA_ACHIEVEMENTS: {},
            DATA_CHALLENGES: {},
            DATA_PENDING_REWARD_APPROVALS: [],
            DATA_PENDING_CHORE_APPROVALS: [],
        }
        await self.async_save()

    async def async_delete_storage(self) -> None:
        """Delete the storage file completely from disk."""

        # First clear in-memory data
        await self.async_clear_data()

        # Remove the file if it exists
        if os.path.isfile(self._store._path):
            try:
                os.remove(self._store._path)
                LOGGER.info("Storage file removed: %s", self._store._path)
            except Exception as e:
                LOGGER.error("Failed to remove storage file: %s", e)
        else:
            LOGGER.info("Storage file not found: %s", self._store._path)

    async def async_update_data(self, key, value):
        """Update a specific section of the data structure."""

        if key in self._data:
            LOGGER.debug("Updating data for key: %s", key)
            self._data[key] = value
            await self.async_save()
        else:
            LOGGER.warning("Attempted to update unknown data key: %s", key)
