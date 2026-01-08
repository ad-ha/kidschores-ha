# File: __init__.py
"""Initialization file for the KidsChores integration.

Handles setting up the integration, including loading configuration entries,
initializing data storage, and preparing the coordinator for data handling.

Key Features:
- Config entry setup and unload support.
- Coordinator initialization for data synchronization.
- Storage management for persistent data handling.
"""

# pylint: disable=protected-access  # Legitimate internal access to coordinator._persist()

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from . import const
from . import flow_helpers as fh
from .coordinator import KidsChoresDataCoordinator
from .notification_action_handler import async_handle_notification_action
from .services import async_setup_services, async_unload_services
from .storage_manager import KidsChoresStorageManager


async def _update_all_kid_device_names(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update all kid device names when config entry title changes.

    When the integration name (config entry title) changes, all kid device
    names need to be updated since they include the title in the format:
    "{kid_name} ({entry.title})".

    Args:
        hass: Home Assistant instance
        entry: Config entry with potentially new title

    """
    from homeassistant.helpers import device_registry as dr

    # Get coordinator to access kid data
    if const.DOMAIN not in hass.data or entry.entry_id not in hass.data[const.DOMAIN]:
        const.LOGGER.debug(
            "Coordinator not found for entry %s, skipping device name updates",
            entry.entry_id,
        )
        return

    coordinator = hass.data[const.DOMAIN][entry.entry_id].get(const.COORDINATOR)
    if not coordinator:
        return

    device_registry = dr.async_get(hass)
    updated_count = 0

    # Update device name for each kid
    for kid_id, kid_data in coordinator.kids_data.items():
        kid_name = kid_data.get(const.DATA_KID_NAME, "Unknown")
        device = device_registry.async_get_device(identifiers={(const.DOMAIN, kid_id)})

        if device:
            new_device_name = f"{kid_name} ({entry.title})"
            # Only update if name actually changed
            if device.name != new_device_name:
                device_registry.async_update_device(device.id, name=new_device_name)
                const.LOGGER.debug(
                    "Updated device name for kid '%s' (ID: %s) to '%s'",
                    kid_name,
                    kid_id,
                    new_device_name,
                )
                updated_count += 1

    if updated_count > 0:
        const.LOGGER.info(
            "Updated %d kid device names for new integration title: %s",
            updated_count,
            entry.title,
        )


async def _cleanup_legacy_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove legacy entities when show_legacy_entities is disabled.

    This function scans the entity registry for legacy sensor entities
    belonging to this config entry and removes them when the legacy
    flag is disabled. Prevents entities from appearing as "unavailable".

    Args:
        hass: Home Assistant instance
        entry: Config entry to check for legacy flag

    """
    from homeassistant.helpers import entity_registry as er

    show_legacy = entry.options.get(const.CONF_SHOW_LEGACY_ENTITIES, False)
    if show_legacy:
        const.LOGGER.debug("Legacy entities enabled, skipping cleanup")
        return  # Keep entities when flag is enabled

    entity_registry = er.async_get(hass)

    # Define legacy unique_id suffixes to clean up
    legacy_suffixes = [
        const.SENSOR_KC_UID_SUFFIX_COMPLETED_TOTAL_SENSOR,
        const.SENSOR_KC_UID_SUFFIX_COMPLETED_DAILY_SENSOR,
        const.SENSOR_KC_UID_SUFFIX_COMPLETED_WEEKLY_SENSOR,
        const.SENSOR_KC_UID_SUFFIX_COMPLETED_MONTHLY_SENSOR,
        const.SENSOR_KC_UID_SUFFIX_PENDING_CHORE_APPROVALS_SENSOR,
        const.SENSOR_KC_UID_SUFFIX_PENDING_REWARD_APPROVALS_SENSOR,
        const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_DAILY_SENSOR,
        const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_WEEKLY_SENSOR,
        const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_MONTHLY_SENSOR,
        const.SENSOR_KC_UID_SUFFIX_KID_HIGHEST_STREAK_SENSOR,
        const.SENSOR_KC_UID_SUFFIX_KID_MAX_POINTS_EVER_SENSOR,
        const.SENSOR_KC_UID_SUFFIX_PENALTY_APPLIES_SENSOR,
        const.SENSOR_KC_UID_SUFFIX_BONUS_APPLIES_SENSOR,
    ]

    # Scan and remove legacy entities for this config entry
    removed_count = 0
    for entity_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        if entity_entry.domain == "sensor":
            for suffix in legacy_suffixes:
                if entity_entry.unique_id.endswith(suffix):
                    const.LOGGER.debug(
                        "Removing legacy entity (flag disabled): %s (unique_id: %s)",
                        entity_entry.entity_id,
                        entity_entry.unique_id,
                    )
                    entity_registry.async_remove(entity_entry.entity_id)
                    removed_count += 1
                    break

    if removed_count > 0:
        const.LOGGER.info(
            "Removed %d legacy entities (show_legacy_entities=False)",
            removed_count,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    const.LOGGER.info("INFO: Starting setup for KidsChores entry: %s", entry.entry_id)

    # Set the home assistant configured timezone for date/time operations
    # Must be done early before any components that use datetime helpers
    const.set_default_timezone(hass)

    # Initialize the storage manager to handle persistent data.
    storage_manager = KidsChoresStorageManager(hass, const.STORAGE_KEY)
    # Initialize new file.
    await storage_manager.async_initialize()

    # DEBUG: Check what was loaded from storage
    loaded_data = storage_manager.data
    const.LOGGER.debug(
        "DEBUG: __init__ after storage load: %d kids, %d parents, %d chores, %d badges",
        len(loaded_data.get(const.DATA_KIDS, {})),
        len(loaded_data.get(const.DATA_PARENTS, {})),
        len(loaded_data.get(const.DATA_CHORES, {})),
        len(loaded_data.get(const.DATA_BADGES, {})),
    )

    # PHASE 2: Migrate entity data from config to storage (one-time hand-off) - LEGACY MIGRATION
    # This must happen BEFORE coordinator initialization to ensure coordinator
    # loads from storage-only mode (schema_version >= 42)
    from .migration_pre_v42 import migrate_config_to_storage

    await migrate_config_to_storage(hass, entry, storage_manager)

    # Create safety backup only on true first startup (not on reloads)
    # Use a persistent flag across reloads to prevent duplicate backups
    startup_backup_key = (
        f"{const.DOMAIN}{const.RUNTIME_KEY_STARTUP_BACKUP_CREATED}{entry.entry_id}"
    )

    # Check if we've already created a startup backup for this entry in this HA session
    if not hass.data.get(startup_backup_key, False):
        # Mark that we're creating the backup (before the actual creation)
        # This prevents race conditions if multiple reloads happen simultaneously
        hass.data[startup_backup_key] = True

        backup_name = await fh.create_timestamped_backup(
            hass, storage_manager, const.BACKUP_TAG_RECOVERY
        )
        if backup_name:
            const.LOGGER.info(
                "Created startup recovery backup: %s (automatic safety backup)",
                backup_name,
            )
        else:
            const.LOGGER.warning(
                "Failed to create startup backup - continuing with setup"
            )
    else:
        const.LOGGER.debug("Skipping startup backup on settings reload")

    # Always cleanup old backups based on current retention setting
    # This ensures changes to max_backups are applied immediately
    max_backups = int(
        entry.options.get(
            const.CONF_BACKUPS_MAX_RETAINED, const.DEFAULT_BACKUPS_MAX_RETAINED
        )
    )
    await fh.cleanup_old_backups(hass, storage_manager, max_backups)

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

    # Cleanup legacy entities if flag is disabled (after platform setup)
    await _cleanup_legacy_entities(hass, entry)

    # Register update listener for config entry changes (e.g., title changes)
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # Listen for notification actions from the companion app.
    async def handle_notification_event(event):
        """Handle notification action events."""
        await async_handle_notification_action(hass, event)

    hass.bus.async_listen(const.NOTIFICATION_EVENT, handle_notification_event)

    const.LOGGER.info("INFO: KidsChores setup complete for entry: %s", entry.entry_id)
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update (e.g., integration name change).

    This is called when the config entry is updated, including when the user
    changes the integration name in the UI. We need to update all kid device
    names to reflect the new title.

    Args:
        hass: Home Assistant instance
        entry: Updated config entry

    """
    const.LOGGER.debug(
        "Config entry updated for %s, checking for device name updates", entry.entry_id
    )

    # Update all kid device names in case title changed
    await _update_all_kid_device_names(hass, entry)

    # Reload the config entry to apply changes
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    const.LOGGER.info("INFO: Unloading KidsChores entry: %s", entry.entry_id)

    # Force immediate save of any pending changes before unload
    if const.DOMAIN in hass.data and entry.entry_id in hass.data[const.DOMAIN]:
        coordinator = hass.data[const.DOMAIN][entry.entry_id][const.COORDINATOR]
        coordinator._persist()
        const.LOGGER.debug("Forced immediate persist before unload")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, const.PLATFORMS)

    if unload_ok:
        hass.data[const.DOMAIN].pop(entry.entry_id)

        # Await service unloading
        await async_unload_services(hass)

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of a config entry.

    Creates a backup before deletion to allow data recovery if integration
    is re-added. Backup is tagged with 'removal' for easy identification.

    Args:
        hass: Home Assistant instance
        entry: Config entry being removed

    """
    const.LOGGER.info("INFO: Removing KidsChores entry: %s", entry.entry_id)

    # Safely check if data exists before attempting to access it
    if const.DOMAIN in hass.data and entry.entry_id in hass.data[const.DOMAIN]:
        storage_manager: KidsChoresStorageManager = hass.data[const.DOMAIN][
            entry.entry_id
        ][const.STORAGE_MANAGER]

        # Create backup before deletion (allows data recovery on re-add)
        backup_name = await fh.create_timestamped_backup(
            hass, storage_manager, const.BACKUP_TAG_REMOVAL
        )
        if backup_name:
            const.LOGGER.info(
                "Created removal backup: %s (integration can be re-added to restore data)",
                backup_name,
            )
        else:
            const.LOGGER.warning(
                "Failed to create removal backup - data will be permanently deleted"
            )

        # Delete active storage file
        await storage_manager.async_delete_storage()
        const.LOGGER.info(
            "KidsChores storage file deleted for entry: %s", entry.entry_id
        )
    else:
        const.LOGGER.info(
            "No storage data found for entry %s - nothing to remove", entry.entry_id
        )
