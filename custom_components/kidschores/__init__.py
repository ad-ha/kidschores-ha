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


async def _migrate_config_to_storage(
    hass: HomeAssistant, entry: ConfigEntry, storage_manager: KidsChoresStorageManager
) -> None:
    """One-time migration: Move entity data from config_entry.options to storage.

    This migration runs once to transition from the legacy KC 3.x "config as source of truth"
    architecture to the new KC 4.x "storage as source of truth" architecture.

    System settings (points_label, points_icon, update_interval) remain in config.
    All entity definitions (kids, chores, badges, etc.) move to storage.

    Args:
        hass: Home Assistant instance
        entry: Config entry to migrate
        storage_manager: Initialized storage manager

    """
    storage_data = storage_manager.data

    # Check schema version - support both v41 (top-level) and v42+ (meta section)
    # v41 format: {"schema_version": 41, "kids": {...}}
    # v42+ format: {"meta": {"schema_version": 42}, "kids": {...}}
    meta_section = storage_data.get(const.DATA_META, {})
    storage_version = meta_section.get(
        const.DATA_META_SCHEMA_VERSION,
        storage_data.get(const.DATA_SCHEMA_VERSION, const.DEFAULT_ZERO),
    )

    # Check if migration is needed
    if storage_version >= const.SCHEMA_VERSION_STORAGE_ONLY:
        const.LOGGER.info(
            "INFO: Storage schema version %s already >= %s, skipping config→storage migration",
            storage_version,
            const.SCHEMA_VERSION_STORAGE_ONLY,
        )
        return

    # Check if config has entity data to migrate
    config_has_entities = any(
        key in entry.options
        for key in [
            const.CONF_KIDS,
            const.CONF_CHORES,
            const.CONF_BADGES,
            const.CONF_REWARDS,
            const.CONF_PARENTS,
            const.CONF_PENALTIES,
            const.CONF_BONUSES,
            const.CONF_ACHIEVEMENTS,
            const.CONF_CHALLENGES,
        ]
    )

    # Also check if storage already has entity data (handles storage-based v3.x installations)
    storage_has_entities = any(
        len(storage_data.get(key, {})) > 0
        for key in [
            const.DATA_KIDS,
            const.DATA_CHORES,
            const.DATA_BADGES,
            const.DATA_REWARDS,
        ]
    )

    # Only treat as clean install if BOTH config and storage are empty
    if not config_has_entities and not storage_has_entities:
        const.LOGGER.info(
            "INFO: No entity data in config or storage, setting storage version to %s (clean install)",
            const.SCHEMA_VERSION_STORAGE_ONLY,
        )
        # Clean install - set version in meta section and save
        from homeassistant.util import dt as dt_util

        storage_data[const.DATA_META] = {
            const.DATA_META_SCHEMA_VERSION: const.SCHEMA_VERSION_STORAGE_ONLY,
            const.DATA_META_LAST_MIGRATION_DATE: dt_util.utcnow().isoformat(),
            const.DATA_META_MIGRATIONS_APPLIED: [],
        }
        storage_manager.set_data(storage_data)
        await storage_manager.async_save()
        return

    # Storage-only data (Config Flow import path): let coordinator handle all migrations
    if not config_has_entities and storage_has_entities:
        const.LOGGER.info(
            "INFO: Storage has data but config is empty (schema v%s). Coordinator will handle migrations.",
            storage_version,
        )
        return

    # Migration needed: config has entities and storage version < 42
    const.LOGGER.info("INFO: ========================================")
    const.LOGGER.info(
        "INFO: Starting config→storage migration (schema version %s → %s)",
        storage_version,
        const.SCHEMA_VERSION_STORAGE_ONLY,
    )

    # Create backup of storage data before migration
    try:
        backup_name = await fh.create_timestamped_backup(
            hass, storage_manager, const.BACKUP_TAG_PRE_MIGRATION
        )
        if backup_name:
            const.LOGGER.info("INFO: Created pre-migration backup: %s", backup_name)
        else:
            const.LOGGER.warning("WARNING: No data available for pre-migration backup")
    except Exception as err:  # pylint: disable=broad-exception-caught
        const.LOGGER.warning("WARNING: Failed to create pre-migration backup: %s", err)

    # Define fields that should NOT be migrated from config (relational/runtime fields)
    # IMPORTANT: These fields in OLD config data may have stale/incorrect data:
    # - Relational fields may contain entity NAMES instead of INTERNAL_IDS
    # - Runtime state fields should never come from config
    # By excluding these fields, we preserve the correct data already in storage
    excluded_fields_by_type = {
        const.DATA_CHORES: {
            "assigned_kids",  # May contain names instead of internal_ids
            "state",
            "last_completed",
            "last_claimed",
        },
        const.DATA_PARENTS: {
            "associated_kids",  # May contain names instead of internal_ids
        },
        const.DATA_BADGES: {
            "assigned_to",  # May contain names instead of internal_ids
        },
        const.DATA_ACHIEVEMENTS: {
            "assigned_kids",  # May contain names instead of internal_ids
            "selected_chore_id",  # May contain name instead of internal_id
            "progress",  # Runtime data
        },
        const.DATA_CHALLENGES: {
            "assigned_kids",  # May contain names instead of internal_ids
            "selected_chore_id",  # May contain name instead of internal_id
            "progress",  # Runtime data
        },
    }

    # Merge entity data from config into storage (preserving existing state)
    entity_sections = [
        (const.CONF_KIDS, const.DATA_KIDS),
        (const.CONF_PARENTS, const.DATA_PARENTS),
        (const.CONF_CHORES, const.DATA_CHORES),
        (const.CONF_BADGES, const.DATA_BADGES),
        (const.CONF_REWARDS, const.DATA_REWARDS),
        (const.CONF_PENALTIES, const.DATA_PENALTIES),
        (const.CONF_BONUSES, const.DATA_BONUSES),
        (const.CONF_ACHIEVEMENTS, const.DATA_ACHIEVEMENTS),
        (const.CONF_CHALLENGES, const.DATA_CHALLENGES),
    ]

    for config_key, data_key in entity_sections:
        config_entities = entry.options.get(config_key, {})
        if config_entities:
            # Merge config entities into storage (config is source of truth for definitions)
            if data_key not in storage_data:
                storage_data[data_key] = {}

            # Get excluded fields for this entity type
            excluded_fields = excluded_fields_by_type.get(data_key, set())

            # For each entity from config, merge with existing storage data
            # Preserve all existing runtime data, only update definition fields
            for entity_id, config_entity_data in config_entities.items():
                if entity_id in storage_data[data_key]:
                    # Entity exists in storage - update only definition fields, preserve runtime data
                    existing_entity = storage_data[data_key][entity_id]
                    # Only update fields that are not excluded
                    for field, value in config_entity_data.items():
                        if field not in excluded_fields:
                            existing_entity[field] = value
                else:
                    # New entity - add from config
                    storage_data[data_key][entity_id] = config_entity_data

                # For kids, ensure each kid has the required v42 fields
                if config_key == const.CONF_KIDS:
                    # Add overdue_notifications field if missing
                    if (
                        const.DATA_KID_OVERDUE_NOTIFICATIONS
                        not in storage_data[data_key][entity_id]
                    ):
                        storage_data[data_key][entity_id][
                            const.DATA_KID_OVERDUE_NOTIFICATIONS
                        ] = {}

            const.LOGGER.debug(
                "DEBUG: Migrated %s %s from config to storage",
                len(config_entities),
                config_key,
            )

    # Set new schema version in meta section
    from homeassistant.util import dt as dt_util

    storage_data[const.DATA_META] = {
        const.DATA_META_SCHEMA_VERSION: const.SCHEMA_VERSION_STORAGE_ONLY,
        const.DATA_META_LAST_MIGRATION_DATE: dt_util.utcnow().isoformat(),
        const.DATA_META_MIGRATIONS_APPLIED: ["config_to_storage"],
    }
    # Remove old top-level schema_version if present
    storage_data.pop(const.DATA_SCHEMA_VERSION, None)

    # Save merged data to storage
    storage_manager.set_data(storage_data)
    await storage_manager.async_save()

    # Build new config with ONLY system settings
    new_options = {
        const.CONF_POINTS_LABEL: entry.options.get(
            const.CONF_POINTS_LABEL, const.DEFAULT_POINTS_LABEL
        ),
        const.CONF_POINTS_ICON: entry.options.get(
            const.CONF_POINTS_ICON, const.DEFAULT_POINTS_ICON
        ),
        const.CONF_UPDATE_INTERVAL: entry.options.get(
            const.CONF_UPDATE_INTERVAL, const.DEFAULT_UPDATE_INTERVAL
        ),
        const.CONF_POINTS_ADJUST_VALUES: entry.options.get(
            const.CONF_POINTS_ADJUST_VALUES, const.DEFAULT_POINTS_ADJUST_VALUES
        ),
        const.CONF_CALENDAR_SHOW_PERIOD: entry.options.get(
            const.CONF_CALENDAR_SHOW_PERIOD, const.DEFAULT_CALENDAR_SHOW_PERIOD
        ),
        const.CONF_RETENTION_DAILY: entry.options.get(
            const.CONF_RETENTION_DAILY, const.DEFAULT_RETENTION_DAILY
        ),
        const.CONF_RETENTION_WEEKLY: entry.options.get(
            const.CONF_RETENTION_WEEKLY, const.DEFAULT_RETENTION_WEEKLY
        ),
        const.CONF_RETENTION_MONTHLY: entry.options.get(
            const.CONF_RETENTION_MONTHLY, const.DEFAULT_RETENTION_MONTHLY
        ),
        const.CONF_RETENTION_YEARLY: entry.options.get(
            const.CONF_RETENTION_YEARLY, const.DEFAULT_RETENTION_YEARLY
        ),
        const.CONF_SCHEMA_VERSION: const.SCHEMA_VERSION_STORAGE_ONLY,
    }

    # Update config entry with cleaned options
    hass.config_entries.async_update_entry(entry, options=new_options)

    const.LOGGER.info(
        "INFO: ✓ Config→storage migration complete! Entity data now in storage, system settings in config."
    )
    const.LOGGER.info("INFO: ========================================")


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

    # PHASE 2: Migrate entity data from config to storage (one-time hand-off)
    # This must happen BEFORE coordinator initialization to ensure coordinator
    # loads from storage-only mode (schema_version >= 42)
    await _migrate_config_to_storage(hass, entry, storage_manager)

    # Create safety backup only on true first startup (not on reloads)
    # Use a persistent flag across reloads to prevent duplicate backups
    startup_backup_key = f"{const.DOMAIN}_startup_backup_created_{entry.entry_id}"

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
