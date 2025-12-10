# File: __init__.py
"""Initialization file for the KidsChores integration.

Handles setting up the integration, including loading configuration entries,
initializing data storage, and preparing the coordinator for data handling.

Key Features:
- Config entry setup and unload support.
- Coordinator initialization for data synchronization.
- Storage management for persistent data handling.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from . import const
from .coordinator import KidsChoresDataCoordinator
from .notification_action_handler import async_handle_notification_action
from .services import async_setup_services, async_unload_services
from .storage_manager import KidsChoresStorageManager


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    const.LOGGER.info("INFO: Starting setup for KidsChores entry: %s", entry.entry_id)

    # Initialize the storage manager to handle persistent data.
    storage_manager = KidsChoresStorageManager(hass, const.STORAGE_KEY)
    # Initialize new file.
    await storage_manager.async_initialize()

    # Create the data coordinator for managing updates and synchronization.
    coordinator = KidsChoresDataCoordinator(hass, entry, storage_manager)

    try:
        # Perform the first refresh to load data.
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady as e:
        const.LOGGER.error("ERROR: Failed to refresh coordinator data: %s", e)
        raise ConfigEntryNotReady from e

    # Store the coordinator and data manager in hass.data.
    hass.data.setdefault(const.DOMAIN, {})[entry.entry_id] = {
        const.COORDINATOR: coordinator,
        const.STORAGE_MANAGER: storage_manager,
    }

    # Set up services required by the integration.
    async_setup_services(hass)

    # Forward the setup to supported platforms (sensors, buttons, etc.).
    await hass.config_entries.async_forward_entry_setups(entry, const.PLATFORMS)

    # Listen for notification actions from the companion app.
    async def handle_notification_event(event):
        """Handle notification action events."""
        await async_handle_notification_action(hass, event)

    hass.bus.async_listen(const.NOTIFICATION_EVENT, handle_notification_event)

    # Set the home assistant configured timezone for date/time operations
    const.set_default_timezone(hass)

    const.LOGGER.info("INFO: KidsChores setup complete for entry: %s", entry.entry_id)
    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    const.LOGGER.info("INFO: Unloading KidsChores entry: %s", entry.entry_id)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, const.PLATFORMS)

    if unload_ok:
        hass.data[const.DOMAIN].pop(entry.entry_id)

        # Await service unloading
        await async_unload_services(hass)

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of a config entry."""
    const.LOGGER.info("INFO: Removing KidsChores entry: %s", entry.entry_id)

    # Safely check if data exists before attempting to access it
    if const.DOMAIN in hass.data and entry.entry_id in hass.data[const.DOMAIN]:
        storage_manager: KidsChoresStorageManager = hass.data[const.DOMAIN][
            entry.entry_id
        ][const.STORAGE_MANAGER]
        await storage_manager.async_delete_storage()

    const.LOGGER.info("INFO: KidsChores entry data cleared: %s", entry.entry_id)
