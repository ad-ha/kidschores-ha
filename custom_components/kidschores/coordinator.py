# File: coordinator.py
"""Coordinator for the KidsChores integration.

Handles data synchronization, chore claiming and approval, badge tracking,
reward redemption, penalty application, and recurring chore handling.
Manages entities primarily using internal_id for consistency.
"""

# Pylint suppressions for valid coordinator architectural patterns:
# - too-many-lines: Complex coordinators legitimately need comprehensive logic
# - too-many-public-methods: Each service/feature requires its own public method
# pylint: disable=too-many-lines,too-many-public-methods

import asyncio
import sys
import time
import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any, Optional, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import const
from . import kc_helpers as kh
from .notification_helper import async_send_notification
from .storage_manager import KidsChoresStorageManager


class KidsChoresDataCoordinator(DataUpdateCoordinator):
    """Coordinator for KidsChores integration.

    Manages data primarily using internal_id for entities.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        storage_manager: KidsChoresStorageManager,
    ):
        """Initialize the KidsChoresDataCoordinator."""
        update_interval_minutes = config_entry.options.get(
            const.CONF_UPDATE_INTERVAL, const.DEFAULT_UPDATE_INTERVAL
        )

        super().__init__(
            hass,
            const.LOGGER,
            name=f"{const.DOMAIN}{const.COORDINATOR_SUFFIX}",
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.config_entry = config_entry
        self.storage_manager = storage_manager
        self._data: dict[str, Any] = {}

        # Test mode detection for reminder delays
        self._test_mode = "pytest" in sys.modules
        const.LOGGER.debug(
            "Coordinator initialized in %s mode",
            "TEST" if self._test_mode else "PRODUCTION",
        )

        # Change tracking for pending approvals (for dashboard helper optimization)
        self._pending_chore_changed: bool = True  # True on first load
        self._pending_reward_changed: bool = True  # True on first load

        # Debounced persist tracking (Phase 2 optimization)
        self._persist_task: asyncio.Task | None = None
        self._persist_debounce_seconds = 5

    # -------------------------------------------------------------------------------------
    # Migrate Data and Converters
    # -------------------------------------------------------------------------------------

    def _run_pre_v42_migrations(self) -> None:
        """Run pre-v42 schema migrations if needed.

        Lazy-loads the migration module to avoid any cost for v42+ users.
        All migration methods are encapsulated in the PreV42Migrator class.
        """
        from .migration_pre_v42 import PreV42Migrator

        migrator = PreV42Migrator(self)
        migrator.run_all_migrations()

    def _assign_kid_to_independent_chores(self, kid_id: str) -> None:
        """Assign kid to all INDEPENDENT chores they're added to.

        When a kid is added, they inherit the template due date for all
        INDEPENDENT chores they're assigned to.
        """
        chores_data = self._data.get(const.DATA_CHORES, {})
        for _, chore_info in chores_data.items():
            # Only process INDEPENDENT chores
            if (
                chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
                != const.COMPLETION_CRITERIA_INDEPENDENT
            ):
                continue

            # If kid is assigned to this chore, add their per-kid due date
            assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
            if kid_id in assigned_kids:
                per_kid_due_dates = chore_info.setdefault(
                    const.DATA_CHORE_PER_KID_DUE_DATES, {}
                )
                template_due_date = chore_info.get(const.DATA_CHORE_DUE_DATE)
                if kid_id not in per_kid_due_dates:
                    per_kid_due_dates[kid_id] = template_due_date
                    const.LOGGER.debug(
                        "Added kid '%s' to INDEPENDENT chore '%s' with due date: %s",
                        kid_id,
                        chore_info.get(const.DATA_CHORE_NAME),
                        template_due_date,
                    )

    def _remove_kid_from_independent_chores(self, kid_id: str) -> None:
        """Remove kid from per-kid due dates when they're removed.

        Template due date remains unchanged; only per-kid entry is deleted.
        """
        chores_data = self._data.get(const.DATA_CHORES, {})
        for _, chore_info in chores_data.items():
            # Only process INDEPENDENT chores
            if (
                chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
                != const.COMPLETION_CRITERIA_INDEPENDENT
            ):
                continue

            # Remove kid from per-kid due dates if present
            per_kid_due_dates = chore_info.get(const.DATA_CHORE_PER_KID_DUE_DATES, {})
            if kid_id in per_kid_due_dates:
                del per_kid_due_dates[kid_id]
                const.LOGGER.debug(
                    "Removed kid '%s' from INDEPENDENT chore '%s' per-kid dates",
                    kid_id,
                    chore_info.get(const.DATA_CHORE_NAME),
                )

    # Note: Migration methods (_migrate_datetime, _migrate_stored_datetimes, etc.)
    # have been extracted to migration_pre_v42.py and are no longer defined here.
    # They are now methods of the PreV42Migrator class.
    # This section previously contained 781 lines of migration code.
    # All migration methods have been extracted to migration_pre_v42.py.

    # -------------------------------------------------------------------------------------
    # Normalize Data Structures
    # -------------------------------------------------------------------------------------

    def _normalize_kid_reward_data(self, kid_info: dict[str, Any]) -> None:
        """Ensure reward_data dict is properly initialized.

        Modern reward tracking uses reward_data dict with period-based counters.
        Legacy lists (pending_rewards, redeemed_rewards) are no longer used.
        """
        if not isinstance(kid_info.get(const.DATA_KID_REWARD_DATA), dict):
            kid_info[const.DATA_KID_REWARD_DATA] = {}

    # -------------------------------------------------------------------------------------
    # Periodic + First Refresh
    # -------------------------------------------------------------------------------------

    async def _async_update_data(self):
        """Periodic update."""
        try:
            # Check overdue chores
            await self._check_overdue_chores()

            # Notify entities of changes
            self.async_update_listeners()

            return self._data
        except Exception as err:  # pylint: disable=broad-exception-caught
            raise UpdateFailed(f"Error updating KidsChores data: {err}") from err

    async def async_config_entry_first_refresh(self):
        """Load from storage and merge config options."""
        const.LOGGER.debug(
            "DEBUG: Coordinator first refresh - requesting data from storage manager"
        )
        stored_data = self.storage_manager.data
        const.LOGGER.debug(
            "DEBUG: Coordinator received data from storage manager: %s entities",
            {
                "kids": len(stored_data.get(const.DATA_KIDS, {})),
                "chores": len(stored_data.get(const.DATA_CHORES, {})),
                "badges": len(stored_data.get(const.DATA_BADGES, {})),
                "schema_version": stored_data.get(const.DATA_META, {}).get(
                    const.DATA_META_SCHEMA_VERSION,
                    stored_data.get(const.DATA_SCHEMA_VERSION, "missing"),
                ),
            },
        )
        if stored_data:
            self._data = stored_data

            # Get schema version from meta section (v43+) or top-level (v42-)
            meta = self._data.get(const.DATA_META, {})
            storage_schema_version = meta.get(
                const.DATA_META_SCHEMA_VERSION,
                self._data.get(const.DATA_SCHEMA_VERSION, const.DEFAULT_ZERO),
            )

            if storage_schema_version < const.SCHEMA_VERSION_STORAGE_ONLY:
                const.LOGGER.info(
                    "INFO: Storage schema version %s < %s, running pre-v42 migrations",
                    storage_schema_version,
                    const.SCHEMA_VERSION_STORAGE_ONLY,
                )
                self._run_pre_v42_migrations()

                # Update to current schema version in meta section
                # Use module-level datetime and dt_util imports

                # DEBUG: Check DEFAULT_MIGRATIONS_APPLIED value
                const.LOGGER.debug(
                    "DEFAULT_MIGRATIONS_APPLIED constant: %s (type: %s, len: %d)",
                    const.DEFAULT_MIGRATIONS_APPLIED,
                    type(const.DEFAULT_MIGRATIONS_APPLIED),
                    len(const.DEFAULT_MIGRATIONS_APPLIED),
                )

                self._data[const.DATA_META] = {
                    const.DATA_META_SCHEMA_VERSION: const.SCHEMA_VERSION_STORAGE_ONLY,
                    const.DATA_META_LAST_MIGRATION_DATE: datetime.now(
                        dt_util.UTC
                    ).isoformat(),
                    const.DATA_META_MIGRATIONS_APPLIED: const.DEFAULT_MIGRATIONS_APPLIED,
                }

                # DEBUG: Verify what got assigned
                const.LOGGER.debug(
                    "migrations_applied after assignment: %s (len: %d)",
                    self._data[const.DATA_META][const.DATA_META_MIGRATIONS_APPLIED],
                    len(
                        self._data[const.DATA_META][const.DATA_META_MIGRATIONS_APPLIED]
                    ),
                )

                # Remove old top-level schema_version if present (v42 → v43 migration)
                self._data.pop(const.DATA_SCHEMA_VERSION, None)

                const.LOGGER.info(
                    "Migrated storage from schema version %s to %s",
                    storage_schema_version,
                    const.SCHEMA_VERSION_STORAGE_ONLY,
                )
            else:
                const.LOGGER.debug(
                    "Storage already at schema version %s, skipping migration",
                    storage_schema_version,
                )

            # Clean up legacy migration keys from KC 4.x beta (schema v41)
            # These keys are redundant with schema_version and should be removed
            if const.MIGRATION_PERFORMED in self._data:
                const.LOGGER.debug("Cleaning up legacy key: migration_performed")
                del self._data[const.MIGRATION_PERFORMED]
            if const.MIGRATION_KEY_VERSION in self._data:
                const.LOGGER.debug("Cleaning up legacy key: migration_key_version")
                del self._data[const.MIGRATION_KEY_VERSION]

            # NOTE: Field migrations (show_on_calendar, auto_approve, overdue_handling_type,
            # approval_reset_pending_claim_action) are now handled in migration_pre_v42.py
            # via _add_chore_optional_fields(). For v42+ data, these fields are already
            # set by flow_helpers.py during entity creation via the UI.

        else:
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
                # Chore and reward queues now computed dynamically from timestamps
                # Legacy fields DATA_PENDING_*_APPROVALS_DEPRECATED removed - computed from timestamps
            }
            self._data[const.DATA_SCHEMA_VERSION] = const.SCHEMA_VERSION_STORAGE_ONLY

        # Register daily/weekly/monthly resets
        async_track_time_change(
            self.hass, self._reset_all_chore_counts, **const.DEFAULT_DAILY_RESET_TIME
        )

        # Note: KC 3.x config sync is now handled by _run_pre_v42_migrations() above
        # (called when storage_schema_version < 42). No separate config sync needed here.

        # Normalize all kids list fields
        for kid in self._data.get(const.DATA_KIDS, {}).values():
            self._normalize_kid_reward_data(kid)

        # Initialize badge references in kid chore tracking
        self._update_chore_badge_references_for_kid()

        # Initialize chore and point stats
        for kid_id, _ in self.kids_data.items():
            self._recalculate_chore_stats_for_kid(kid_id)
            self._recalculate_point_stats_for_kid(kid_id)

        self._persist(immediate=True)  # Startup persist should be immediate
        await super().async_config_entry_first_refresh()

    # -------------------------------------------------------------------------------------
    # Data Initialization from Config
    # -------------------------------------------------------------------------------------
    # NOTE: KC 3.x config sync code (~175 lines) has been extracted to migration_pre_v42.py
    # This includes:
    # - _initialize_data_from_config() - Main config sync wrapper
    # - _ensure_minimal_structure() - Data structure initialization
    # - _initialize_kids/parents/chores/etc() - Entity type wrappers (9 methods)
    # - _sync_entities() - Core sync engine comparing config vs storage
    #
    # These methods are ONLY used for v41→v42 migration (KC 3.x→4.x upgrade).
    # For v4.2+ users, entity data is already in storage; config contains only system settings.
    #
    # CRUD methods (_create_kid, _update_chore, etc.) remain below as they are actively
    # used by options_flow.py for v4.2+ entity management through the UI.

    # -------------------------------------------------------------------------------------
    # Entity CRUD Methods (Active Use by options_flow.py)
    # -------------------------------------------------------------------------------------

    def _remove_entities_in_ha(self, item_id: str):
        """Remove all platform entities whose unique_id references the given item_id."""
        ent_reg = er.async_get(self.hass)
        for entity_entry in list(ent_reg.entities.values()):
            if str(item_id) in str(entity_entry.unique_id):
                ent_reg.async_remove(entity_entry.entity_id)
                const.LOGGER.debug(
                    "DEBUG: Auto-removed entity '%s' with UID '%s'",
                    entity_entry.entity_id,
                    entity_entry.unique_id,
                )

    async def _remove_orphaned_shared_chore_sensors(self):
        """Remove SystemChoreSharedStateSensor entities for chores no longer marked as shared."""
        ent_reg = er.async_get(self.hass)
        prefix = f"{self.config_entry.entry_id}_"
        suffix = const.DATA_GLOBAL_STATE_SUFFIX
        for entity_entry in list(ent_reg.entities.values()):
            unique_id = str(entity_entry.unique_id)
            if (
                entity_entry.domain == const.Platform.SENSOR
                and unique_id.startswith(prefix)
                and unique_id.endswith(suffix)
            ):
                chore_id = unique_id[len(prefix) : -len(suffix)]
                chore_info = self.chores_data.get(chore_id)
                if (
                    not chore_info
                    or chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
                    != const.COMPLETION_CRITERIA_SHARED
                ):
                    ent_reg.async_remove(entity_entry.entity_id)
                    const.LOGGER.debug(
                        "DEBUG: Removed orphaned Shared Chore Global State Sensor: %s",
                        entity_entry.entity_id,
                    )

    async def _remove_orphaned_kid_chore_entities(self) -> None:
        """Remove kid-chore entities (sensors/buttons) for kids no longer assigned to chores."""
        # PERF: Measure entity registry cleanup duration
        perf_start = time.perf_counter()

        ent_reg = er.async_get(self.hass)
        prefix = f"{self.config_entry.entry_id}_"

        # Build a set of valid kid-chore combinations
        valid_combinations = set()
        for chore_id, chore_info in self.chores_data.items():
            assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
            for kid_id in assigned_kids:
                valid_combinations.add((kid_id, chore_id))

        # Check all entities for orphaned kid-chore entities
        for entity_entry in list(ent_reg.entities.values()):
            # Only check our integration's entities
            if entity_entry.platform != const.DOMAIN:
                continue

            unique_id = str(entity_entry.unique_id)
            if not unique_id.startswith(prefix):
                continue

            # Extract the core part after entry_id prefix
            core = unique_id[len(prefix) :]

            # Check if this is a kid-chore entity by looking for kid_id and chore_id
            # Format is: {kid_id}_{chore_id}{suffix} where suffix could be various things
            # We need to check each chore to see if this entity matches
            is_kid_chore_entity = False
            entity_kid_id = None
            entity_chore_id = None

            for chore_id in self.chores_data.keys():
                if chore_id in core:
                    # Found chore_id, now extract kid_id
                    parts = core.split(f"_{chore_id}")
                    if len(parts) >= 1 and parts[0]:
                        potential_kid_id = parts[0]
                        # Check if this is a valid kid
                        if potential_kid_id in self.kids_data:
                            is_kid_chore_entity = True
                            entity_kid_id = potential_kid_id
                            entity_chore_id = chore_id
                            break

            # If this is a kid-chore entity, check if it's still valid
            if is_kid_chore_entity:
                if (entity_kid_id, entity_chore_id) not in valid_combinations:
                    const.LOGGER.debug(
                        "DEBUG: Removing orphaned kid-chore entity '%s' (unique_id: %s) - Kid '%s' no longer assigned to Chore '%s'",
                        entity_entry.entity_id,
                        entity_entry.unique_id,
                        entity_kid_id,
                        entity_chore_id,
                    )
                    ent_reg.async_remove(entity_entry.entity_id)

        # PERF: Log entity registry cleanup duration
        perf_duration = time.perf_counter() - perf_start
        entity_count = len(ent_reg.entities)
        const.LOGGER.debug(
            "PERF: _remove_orphaned_kid_chore_entities() scanned %d entities in %.3fs",
            entity_count,
            perf_duration,
        )

    async def _remove_orphaned_achievement_entities(self) -> None:
        """Remove achievement progress entities for kids that are no longer assigned."""
        ent_reg = er.async_get(self.hass)
        prefix = f"{self.config_entry.entry_id}_"
        suffix = const.DATA_ACHIEVEMENT_PROGRESS_SUFFIX
        for entity_entry in list(ent_reg.entities.values()):
            unique_id = str(entity_entry.unique_id)
            if (
                entity_entry.domain == const.Platform.SENSOR
                and unique_id.startswith(prefix)
                and unique_id.endswith(suffix)
            ):
                core_id = unique_id[len(prefix) : -len(suffix)]
                parts = core_id.split("_", 1)
                if len(parts) != 2:
                    continue

                kid_id, achievement_id = parts
                achievement_info = self._data.get(const.DATA_ACHIEVEMENTS, {}).get(
                    achievement_id
                )
                if not achievement_info or kid_id not in achievement_info.get(
                    const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, []
                ):
                    ent_reg.async_remove(entity_entry.entity_id)
                    const.LOGGER.debug(
                        "DEBUG: Removed orphaned Achievement Progress sensor '%s'. Kid ID '%s' is not assigned to Achievement '%s'",
                        entity_entry.entity_id,
                        kid_id,
                        achievement_id,
                    )

    async def _remove_orphaned_challenge_entities(self) -> None:
        """Remove challenge progress sensor entities for kids no longer assigned."""
        ent_reg = er.async_get(self.hass)
        prefix = f"{self.config_entry.entry_id}_"
        suffix = const.DATA_CHALLENGE_PROGRESS_SUFFIX
        for entity_entry in list(ent_reg.entities.values()):
            unique_id = str(entity_entry.unique_id)
            if (
                entity_entry.domain == const.Platform.SENSOR
                and unique_id.startswith(prefix)
                and unique_id.endswith(suffix)
            ):
                core_id = unique_id[len(prefix) : -len(suffix)]
                parts = core_id.split("_", 1)
                if len(parts) != 2:
                    continue

                kid_id, challenge_id = parts
                challenge_info = self._data.get(const.DATA_CHALLENGES, {}).get(
                    challenge_id
                )
                if not challenge_info or kid_id not in challenge_info.get(
                    const.DATA_CHALLENGE_ASSIGNED_KIDS, []
                ):
                    ent_reg.async_remove(entity_entry.entity_id)
                    const.LOGGER.debug(
                        "DEBUG: Removed orphaned Challenge Progress sensor '%s'. Kid ID '%s' is not assigned to Challenge '%s'",
                        entity_entry.entity_id,
                        kid_id,
                        challenge_id,
                    )

    def _remove_kid_chore_entities(self, kid_id: str, chore_id: str) -> None:
        """Remove all kid-specific chore entities for a given kid and chore."""
        ent_reg = er.async_get(self.hass)
        for entity_entry in list(ent_reg.entities.values()):
            # Only process entities from our integration
            if entity_entry.platform != const.DOMAIN:
                continue

            # Check if this entity belongs to this kid and chore
            # The unique_id format is: {entry_id}_{kid_id}_{chore_id}{suffix}
            if (kid_id in entity_entry.unique_id) and (
                chore_id in entity_entry.unique_id
            ):
                const.LOGGER.debug(
                    "DEBUG: Removing kid-chore entity '%s' (unique_id: %s) for Kid ID '%s' and Chore '%s'",
                    entity_entry.entity_id,
                    entity_entry.unique_id,
                    kid_id,
                    chore_id,
                )
                ent_reg.async_remove(entity_entry.entity_id)

    def _cleanup_chore_from_kid(self, kid_id: str, chore_id: str) -> None:
        """Remove references to a specific chore from a kid's data."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # Remove from kid_chore_data (timestamp-based tracking v0.4.0+)
        if const.DATA_KID_CHORE_DATA in kid_info:
            if chore_id in kid_info[const.DATA_KID_CHORE_DATA]:
                del kid_info[const.DATA_KID_CHORE_DATA][chore_id]
                const.LOGGER.debug(
                    "DEBUG: Removed Chore '%s' from Kid ID '%s' kid_chore_data",
                    chore_id,
                    kid_id,
                )

        # Remove from dictionary fields if present
        dict_key = const.DATA_KID_CHORE_CLAIMS_LEGACY
        if chore_id in kid_info.get(dict_key, {}):
            kid_info[dict_key].pop(chore_id)
            const.LOGGER.debug(
                "DEBUG: Removed Chore '%s' from Kid ID '%s' dict '%s'",
                chore_id,
                kid_id,
                dict_key,
            )

        # Remove from chore streaks if present
        if (
            const.DATA_KID_CHORE_STREAKS_LEGACY in kid_info
            and chore_id in kid_info[const.DATA_KID_CHORE_STREAKS_LEGACY]
        ):
            kid_info[const.DATA_KID_CHORE_STREAKS_LEGACY].pop(chore_id)
            const.LOGGER.debug(
                "DEBUG: Removed Chore Streak for Chore '%s' from Kid ID '%s'",
                chore_id,
                kid_id,
            )
        # Queue filter removed - pending approvals now computed from timestamps
        # Chore data is already cleaned above via DATA_KID_CHORE_DATA removal
        self._pending_chore_changed = True

    def _cleanup_pending_reward_approvals(self) -> None:
        """Remove reward_data entries for rewards that no longer exist."""
        valid_reward_ids = set(self._data.get(const.DATA_REWARDS, {}).keys())
        cleaned = False
        for kid_info in self.kids_data.values():
            reward_data = kid_info.get(const.DATA_KID_REWARD_DATA, {})
            invalid_ids = [rid for rid in reward_data if rid not in valid_reward_ids]
            for rid in invalid_ids:
                reward_data.pop(rid, None)
                cleaned = True
        if cleaned:
            self._pending_reward_changed = True

    def _cleanup_deleted_kid_references(self) -> None:
        """Remove references to kids that no longer exist from other sections."""
        valid_kid_ids = set(self.kids_data.keys())

        # Remove deleted kid IDs from all chore assignments
        for chore_info in self._data.get(const.DATA_CHORES, {}).values():
            if const.DATA_CHORE_ASSIGNED_KIDS in chore_info:
                original = chore_info[const.DATA_CHORE_ASSIGNED_KIDS]
                filtered = [kid for kid in original if kid in valid_kid_ids]
                if filtered != original:
                    chore_info[const.DATA_CHORE_ASSIGNED_KIDS] = filtered
                    const.LOGGER.debug(
                        "DEBUG: Removed Assigned Kids in Chore '%s'",
                        chore_info.get(const.DATA_CHORE_NAME),
                    )

        # Remove progress in achievements and challenges
        for section in [const.DATA_ACHIEVEMENTS, const.DATA_CHALLENGES]:
            for entity in self._data.get(section, {}).values():
                progress = entity.get(const.DATA_PROGRESS, {})
                keys_to_remove = [kid for kid in progress if kid not in valid_kid_ids]
                for kid in keys_to_remove:
                    del progress[kid]
                    const.LOGGER.debug(
                        "DEBUG: Removed Progress for deleted Kid ID '%s' in '%s'",
                        kid,
                        section,
                    )
                if const.DATA_ASSIGNED_KIDS in entity:
                    original_assigned = entity[const.DATA_ASSIGNED_KIDS]
                    filtered_assigned = [
                        kid for kid in original_assigned if kid in valid_kid_ids
                    ]
                    if filtered_assigned != original_assigned:
                        entity[const.DATA_ASSIGNED_KIDS] = filtered_assigned
                        const.LOGGER.debug(
                            "DEBUG: Removed Assigned Kids in '%s', '%s'",
                            section,
                            entity.get(const.DATA_NAME),
                        )

    def _cleanup_deleted_chore_references(self) -> None:
        """Remove references to chores that no longer exist from kid data."""
        valid_chore_ids = set(self.chores_data.keys())
        for kid_info in self.kids_data.values():
            # Clean up kid_chore_data (timestamp-based tracking v0.4.0+)
            if const.DATA_KID_CHORE_DATA in kid_info:
                kid_info[const.DATA_KID_CHORE_DATA] = {
                    chore: data
                    for chore, data in kid_info[const.DATA_KID_CHORE_DATA].items()
                    if chore in valid_chore_ids
                }

            # Clean up dictionary fields
            dict_key = const.DATA_KID_CHORE_CLAIMS_LEGACY
            if dict_key in kid_info:
                kid_info[dict_key] = {
                    chore: count
                    for chore, count in kid_info[dict_key].items()
                    if chore in valid_chore_ids
                }

            # Clean up chore streaks
            if const.DATA_KID_CHORE_STREAKS_LEGACY in kid_info:
                for chore in list(kid_info[const.DATA_KID_CHORE_STREAKS_LEGACY].keys()):
                    if chore not in valid_chore_ids:
                        del kid_info[const.DATA_KID_CHORE_STREAKS_LEGACY][chore]
                        const.LOGGER.debug(
                            "DEBUG: Removed Chore Streak for deleted Chore '%s'", chore
                        )

    def _cleanup_parent_assignments(self) -> None:
        """Remove any kid IDs from parent's 'associated_kids' that no longer exist."""
        valid_kid_ids = set(self.kids_data.keys())
        for parent_info in self._data.get(const.DATA_PARENTS, {}).values():
            original = parent_info.get(const.DATA_PARENT_ASSOCIATED_KIDS, [])
            filtered = [kid_id for kid_id in original if kid_id in valid_kid_ids]
            if filtered != original:
                parent_info[const.DATA_PARENT_ASSOCIATED_KIDS] = filtered
                const.LOGGER.debug(
                    "DEBUG: Removed Associated Kids for Parent '%s'. Current Associated Kids: %s",
                    parent_info.get(const.DATA_PARENT_NAME),
                    filtered,
                )

    def _cleanup_deleted_chore_in_achievements(self) -> None:
        """Clear selected_chore_id in achievements if the chore no longer exists."""
        valid_chore_ids = set(self.chores_data.keys())
        for achievement_info in self._data.get(const.DATA_ACHIEVEMENTS, {}).values():
            selected = achievement_info.get(const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID)
            if selected and selected not in valid_chore_ids:
                achievement_info[const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID] = ""
                const.LOGGER.debug(
                    "DEBUG: Removed Selected Chore ID in Achievement '%s'",
                    achievement_info.get(const.DATA_ACHIEVEMENT_NAME),
                )

    def _cleanup_deleted_chore_in_challenges(self) -> None:
        """Clear selected_chore_id in challenges if the chore no longer exists."""
        valid_chore_ids = set(self.chores_data.keys())
        for challenge_info in self._data.get(const.DATA_CHALLENGES, {}).values():
            selected = challenge_info.get(const.DATA_CHALLENGE_SELECTED_CHORE_ID)
            if selected and selected not in valid_chore_ids:
                challenge_info[const.DATA_CHALLENGE_SELECTED_CHORE_ID] = (
                    const.SENTINEL_EMPTY
                )
                const.LOGGER.debug(
                    "DEBUG: Removed Selected Chore ID in Challenge '%s'",
                    challenge_info.get(const.DATA_CHALLENGE_NAME),
                )

    async def remove_deprecated_entities(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Remove old/deprecated sensor entities from the entity registry that are no longer used."""

        ent_reg = er.async_get(hass)

        for entity_id, entity_entry in list(ent_reg.entities.items()):
            if not entity_entry.unique_id.startswith(f"{entry.entry_id}_"):
                continue
            if any(
                entity_entry.unique_id.endswith(suffix)
                for suffix in const.DEPRECATED_SUFFIXES
            ):
                ent_reg.async_remove(entity_id)
                const.LOGGER.debug(
                    "DEBUG: Removed deprecated Entity '%s', UID '%s'",
                    entity_id,
                    entity_entry.unique_id,
                )

    # pylint: disable=too-many-locals,too-many-branches
    def remove_deprecated_button_entities(self) -> None:
        """Remove dynamic button entities that are not present in the current configuration."""
        ent_reg = er.async_get(self.hass)

        # Build the set of expected unique_ids ("whitelist")
        allowed_uids = set()

        # --- Chore Buttons ---
        # For each chore, create expected unique IDs for claim, approve, and disapprove buttons
        for chore_id, chore_info in self.chores_data.items():
            for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                # Expected unique_id formats:
                uid_claim = f"{self.config_entry.entry_id}_{kid_id}_{chore_id}{const.BUTTON_KC_UID_SUFFIX_CLAIM}"
                uid_approve = f"{self.config_entry.entry_id}_{kid_id}_{chore_id}{const.BUTTON_KC_UID_SUFFIX_APPROVE}"
                uid_disapprove = f"{self.config_entry.entry_id}_{kid_id}_{chore_id}{const.BUTTON_KC_UID_SUFFIX_DISAPPROVE}"
                allowed_uids.update({uid_claim, uid_approve, uid_disapprove})

        # --- Reward Buttons ---
        # For each kid and reward, add expected unique IDs for reward claim, approve, and disapprove buttons.
        for kid_id in self.kids_data.keys():
            for reward_id in self.rewards_data.keys():
                # The reward claim button might be built with a dedicated prefix:
                uid_claim = f"{self.config_entry.entry_id}_{const.BUTTON_REWARD_PREFIX}{kid_id}_{reward_id}"
                uid_approve = f"{self.config_entry.entry_id}_{kid_id}_{reward_id}{const.BUTTON_KC_UID_SUFFIX_APPROVE_REWARD}"
                uid_disapprove = f"{self.config_entry.entry_id}_{kid_id}_{reward_id}{const.BUTTON_KC_UID_SUFFIX_DISAPPROVE_REWARD}"
                allowed_uids.update({uid_claim, uid_approve, uid_disapprove})

        # --- Penalty Buttons ---
        for kid_id in self.kids_data.keys():
            for penalty_id in self.penalties_data.keys():
                uid = f"{self.config_entry.entry_id}_{const.BUTTON_PENALTY_PREFIX}{kid_id}_{penalty_id}"
                allowed_uids.add(uid)

        # --- Bonus Buttons ---
        for kid_id in self.kids_data.keys():
            for bonus_id in self.bonuses_data.keys():
                uid = f"{self.config_entry.entry_id}_{const.BUTTON_BONUS_PREFIX}{kid_id}_{bonus_id}"
                allowed_uids.add(uid)

        # --- Points Adjust Buttons ---
        # Determine the list of adjustment delta values from configuration or defaults.
        raw_values = self.config_entry.options.get(const.CONF_POINTS_ADJUST_VALUES)
        if not raw_values:
            points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES
        elif isinstance(raw_values, str):
            points_adjust_values = kh.parse_points_adjust_values(raw_values)
            if not points_adjust_values:
                points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES
        elif isinstance(raw_values, list):
            try:
                points_adjust_values = [float(v) for v in raw_values]
            except (ValueError, TypeError):
                points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES
        else:
            points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES

        for kid_id in self.kids_data.keys():
            for delta in points_adjust_values:
                uid = f"{self.config_entry.entry_id}_{kid_id}{const.BUTTON_KC_UID_MIDFIX_ADJUST_POINTS}{delta}"
                allowed_uids.add(uid)

        # --- Now remove any button entity whose unique_id is not in allowed_uids ---
        for entity_entry in list(ent_reg.entities.values()):
            # Only check buttons from our platform (kidschores)
            if entity_entry.platform != const.DOMAIN or entity_entry.domain != "button":
                continue

            # If this button doesn't match our whitelist, remove it
            # This catches old entities from previous configs, migrations, or different entry_ids
            if entity_entry.unique_id not in allowed_uids:
                const.LOGGER.info(
                    "INFO: Removing orphaned/deprecated Button '%s' with unique_id '%s'",
                    entity_entry.entity_id,
                    entity_entry.unique_id,
                )
                ent_reg.async_remove(entity_entry.entity_id)

    def remove_deprecated_sensor_entities(self) -> None:
        """Remove dynamic sensor entities that are not present in the current configuration."""
        ent_reg = er.async_get(self.hass)

        # Build the set of expected unique_ids ("whitelist")
        allowed_uids = set()

        # --- Chore Status Sensors ---
        # For each chore, create expected unique IDs for chore status sensors
        for chore_id, chore_info in self.chores_data.items():
            for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                uid = f"{self.config_entry.entry_id}_{kid_id}_{chore_id}{const.SENSOR_KC_UID_SUFFIX_CHORE_STATUS_SENSOR}"
                allowed_uids.add(uid)

        # --- Shared Chore Global State Sensors ---
        for chore_id, chore_info in self.chores_data.items():
            if (
                chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
                == const.COMPLETION_CRITERIA_SHARED
            ):
                uid = f"{self.config_entry.entry_id}_{chore_id}{const.DATA_GLOBAL_STATE_SUFFIX}"
                allowed_uids.add(uid)

        # --- Reward Status Sensors ---
        for reward_id in self.rewards_data.keys():
            for kid_id in self.kids_data.keys():
                uid = f"{self.config_entry.entry_id}_{kid_id}_{reward_id}{const.SENSOR_KC_UID_SUFFIX_REWARD_STATUS_SENSOR}"
                allowed_uids.add(uid)

        # --- Penalty/Bonus Apply Sensors ---
        for kid_id in self.kids_data.keys():
            for penalty_id in self.penalties_data.keys():
                uid = f"{self.config_entry.entry_id}_{kid_id}_{penalty_id}{const.SENSOR_KC_UID_SUFFIX_PENALTY_APPLIES_SENSOR}"
                allowed_uids.add(uid)
            for bonus_id in self.bonuses_data.keys():
                uid = f"{self.config_entry.entry_id}_{kid_id}_{bonus_id}{const.SENSOR_KC_UID_SUFFIX_BONUS_APPLIES_SENSOR}"
                allowed_uids.add(uid)

        # --- Achievement Progress Sensors ---
        for achievement_id, achievement in self.achievements_data.items():
            for kid_id in achievement.get(const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, []):
                uid = f"{self.config_entry.entry_id}_{kid_id}_{achievement_id}{const.SENSOR_KC_UID_SUFFIX_ACHIEVEMENT_PROGRESS_SENSOR}"
                allowed_uids.add(uid)

        # --- Challenge Progress Sensors ---
        for challenge_id, challenge in self.challenges_data.items():
            for kid_id in challenge.get(const.DATA_CHALLENGE_ASSIGNED_KIDS, []):
                uid = f"{self.config_entry.entry_id}_{kid_id}_{challenge_id}{const.SENSOR_KC_UID_SUFFIX_CHALLENGE_PROGRESS_SENSOR}"
                allowed_uids.add(uid)

        # --- Kid-specific sensors (not dynamic based on chores/rewards) ---
        # These are created once per kid and don't need validation against dynamic data
        for kid_id in self.kids_data.keys():
            # Standard kid sensors
            allowed_uids.add(
                f"{self.config_entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_POINTS_SENSOR}"
            )
            allowed_uids.add(
                f"{self.config_entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_COMPLETED_TOTAL_SENSOR}"
            )
            allowed_uids.add(
                f"{self.config_entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_COMPLETED_DAILY_SENSOR}"
            )
            allowed_uids.add(
                f"{self.config_entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_COMPLETED_WEEKLY_SENSOR}"
            )
            allowed_uids.add(
                f"{self.config_entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_COMPLETED_MONTHLY_SENSOR}"
            )
            allowed_uids.add(
                f"{self.config_entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_BADGES_SENSOR}"
            )
            allowed_uids.add(
                f"{self.config_entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_DAILY_SENSOR}"
            )
            allowed_uids.add(
                f"{self.config_entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_WEEKLY_SENSOR}"
            )
            allowed_uids.add(
                f"{self.config_entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_MONTHLY_SENSOR}"
            )
            allowed_uids.add(
                f"{self.config_entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_MAX_POINTS_EVER_SENSOR}"
            )
            allowed_uids.add(
                f"{self.config_entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_HIGHEST_STREAK_SENSOR}"
            )
            allowed_uids.add(
                f"{self.config_entry.entry_id}_{kid_id}_ui_dashboard_helper"
            )  # Hardcoded in sensor.py

            # Badge progress sensors
            badge_progress_data = self.kids_data[kid_id].get(
                const.DATA_KID_BADGE_PROGRESS, {}
            )
            for badge_id, progress_info in badge_progress_data.items():
                badge_type = progress_info.get(const.DATA_KID_BADGE_PROGRESS_TYPE)
                if badge_type != const.BADGE_TYPE_CUMULATIVE:
                    uid = f"{self.config_entry.entry_id}_{kid_id}_{badge_id}{const.SENSOR_KC_UID_SUFFIX_BADGE_PROGRESS_SENSOR}"
                    allowed_uids.add(uid)

        # --- Global sensors (not kid-specific) ---
        allowed_uids.add(
            f"{self.config_entry.entry_id}{const.SENSOR_KC_UID_SUFFIX_PENDING_CHORE_APPROVALS_SENSOR}"
        )
        allowed_uids.add(
            f"{self.config_entry.entry_id}{const.SENSOR_KC_UID_SUFFIX_PENDING_REWARD_APPROVALS_SENSOR}"
        )

        # --- Now remove any sensor entity whose unique_id is not in allowed_uids ---
        for entity_entry in list(ent_reg.entities.values()):
            # Only check sensors from our platform (kidschores)
            if entity_entry.platform != const.DOMAIN or entity_entry.domain != "sensor":
                continue

            # If this sensor doesn't match our whitelist, remove it
            # This catches old entities from previous configs, migrations, or different entry_ids
            if entity_entry.unique_id not in allowed_uids:
                const.LOGGER.info(
                    "INFO: Removing orphaned/deprecated Sensor '%s' with unique_id '%s'",
                    entity_entry.entity_id,
                    entity_entry.unique_id,
                )
                ent_reg.async_remove(entity_entry.entity_id)

    # -------------------------------------------------------------------------------------
    # Create/Update Entities
    # (Kids, Parents, Chores, Badges, Rewards, Penalties, Bonus, Achievements and Challenges)
    # -------------------------------------------------------------------------------------

    # -- Kids
    def _create_kid(self, kid_id: str, kid_data: dict[str, Any]):
        self._data[const.DATA_KIDS][kid_id] = {
            const.DATA_KID_NAME: kid_data.get(
                const.DATA_KID_NAME, const.SENTINEL_EMPTY
            ),
            const.DATA_KID_POINTS: kid_data.get(
                const.DATA_KID_POINTS, const.DEFAULT_ZERO
            ),
            const.DATA_KID_BADGES_EARNED: kid_data.get(
                const.DATA_KID_BADGES_EARNED, {}
            ),
            # Note: claimed_chores and approved_chores lists removed in v0.4.0
            # Now using timestamp-based tracking (last_approved, approval_period_start)
            # Chore tracking now uses timestamps in kid_chore_data
            # Deprecated completed_chores counters removed - using chore_stats only
            const.DATA_KID_HA_USER_ID: kid_data.get(const.DATA_KID_HA_USER_ID),
            const.DATA_KID_INTERNAL_ID: kid_id,
            const.DATA_KID_POINTS_MULTIPLIER: kid_data.get(
                const.DATA_KID_POINTS_MULTIPLIER, const.DEFAULT_KID_POINTS_MULTIPLIER
            ),
            # Legacy reward fields (reward_claims, reward_approvals) removed - use reward_data
            const.DATA_KID_CHORE_CLAIMS_LEGACY: kid_data.get(
                const.DATA_KID_CHORE_CLAIMS_LEGACY, {}
            ),
            const.DATA_KID_PENALTY_APPLIES: kid_data.get(
                const.DATA_KID_PENALTY_APPLIES, {}
            ),
            const.DATA_KID_BONUS_APPLIES: kid_data.get(
                const.DATA_KID_BONUS_APPLIES, {}
            ),
            # Modern reward tracking (v0.5.0+) - timestamp-based with multi-claim support
            # Legacy fields (pending_rewards, redeemed_rewards, reward_claims, reward_approvals)
            # have been removed - all reward tracking now uses reward_data structure
            const.DATA_KID_REWARD_DATA: kid_data.get(const.DATA_KID_REWARD_DATA, {}),
            # NOTE: max_points_ever is removed - use point_stats.highest_balance instead
            const.DATA_KID_ENABLE_NOTIFICATIONS: kid_data.get(
                const.DATA_KID_ENABLE_NOTIFICATIONS, True
            ),
            const.DATA_KID_MOBILE_NOTIFY_SERVICE: kid_data.get(
                const.DATA_KID_MOBILE_NOTIFY_SERVICE, const.SENTINEL_EMPTY
            ),
            const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS: kid_data.get(
                const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS, True
            ),
            const.DATA_KID_CHORE_STREAKS_LEGACY: {},
            const.DATA_KID_OVERDUE_CHORES: [],
            const.DATA_KID_OVERDUE_NOTIFICATIONS: {},
        }

        self._normalize_kid_reward_data(self._data[const.DATA_KIDS][kid_id])

        const.LOGGER.debug(
            "DEBUG: Kid Added - '%s', ID '%s'",
            self._data[const.DATA_KIDS][kid_id][const.DATA_KID_NAME],
            kid_id,
        )

    def _update_kid(self, kid_id: str, kid_data: dict[str, Any]):
        """Update an existing kid entity, only updating fields present in kid_data."""

        kids = self._data.setdefault(const.DATA_KIDS, {})
        existing = kids.get(kid_id, {})
        # Only update fields present in kid_data, preserving all others
        existing.update(kid_data)
        kids[kid_id] = existing

        kid_name = existing.get(const.DATA_KID_NAME, const.SENTINEL_EMPTY)
        const.LOGGER.debug(
            "DEBUG: Kid Updated - '%s', ID '%s'",
            kid_name,
            kid_id,
        )

    # -- Parents
    def _create_parent(self, parent_id: str, parent_data: dict[str, Any]):
        associated_kids_ids = []
        for kid_id in parent_data.get(const.DATA_PARENT_ASSOCIATED_KIDS, []):
            if kid_id in self.kids_data:
                associated_kids_ids.append(kid_id)
            else:
                const.LOGGER.warning(
                    "WARNING: Parent '%s': Kid ID '%s' not found. Skipping assignment to parent",
                    parent_data.get(const.DATA_PARENT_NAME, parent_id),
                    kid_id,
                )

        self._data[const.DATA_PARENTS][parent_id] = {
            const.DATA_PARENT_NAME: parent_data.get(
                const.DATA_PARENT_NAME, const.SENTINEL_EMPTY
            ),
            const.DATA_PARENT_HA_USER_ID: parent_data.get(
                const.DATA_PARENT_HA_USER_ID, const.SENTINEL_EMPTY
            ),
            const.DATA_PARENT_ASSOCIATED_KIDS: associated_kids_ids,
            const.DATA_PARENT_ENABLE_NOTIFICATIONS: parent_data.get(
                const.DATA_PARENT_ENABLE_NOTIFICATIONS, True
            ),
            const.DATA_PARENT_MOBILE_NOTIFY_SERVICE: parent_data.get(
                const.DATA_PARENT_MOBILE_NOTIFY_SERVICE, const.SENTINEL_EMPTY
            ),
            const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS: parent_data.get(
                const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS, True
            ),
            const.DATA_PARENT_INTERNAL_ID: parent_id,
        }
        const.LOGGER.debug(
            "DEBUG: Parent Added - '%s', ID '%s'",
            self._data[const.DATA_PARENTS][parent_id][const.DATA_PARENT_NAME],
            parent_id,
        )

    def _update_parent(self, parent_id: str, parent_data: dict[str, Any]):
        parent_info = self._data[const.DATA_PARENTS][parent_id]
        parent_info[const.DATA_PARENT_NAME] = parent_data.get(
            const.DATA_PARENT_NAME, parent_info[const.DATA_PARENT_NAME]
        )
        parent_info[const.DATA_PARENT_HA_USER_ID] = parent_data.get(
            const.DATA_PARENT_HA_USER_ID, parent_info[const.DATA_PARENT_HA_USER_ID]
        )

        # Update associated_kids
        updated_kids = []
        for kid_id in parent_data.get(const.DATA_PARENT_ASSOCIATED_KIDS, []):
            if kid_id in self.kids_data:
                updated_kids.append(kid_id)
            else:
                const.LOGGER.warning(
                    "WARNING: Parent '%s': Kid ID '%s' not found. Skipping assignment to parent",
                    parent_info[const.DATA_PARENT_NAME],
                    kid_id,
                )
        parent_info[const.DATA_PARENT_ASSOCIATED_KIDS] = updated_kids
        parent_info[const.DATA_PARENT_ENABLE_NOTIFICATIONS] = parent_data.get(
            const.DATA_PARENT_ENABLE_NOTIFICATIONS,
            parent_info.get(const.DATA_PARENT_ENABLE_NOTIFICATIONS, True),
        )
        parent_info[const.DATA_PARENT_MOBILE_NOTIFY_SERVICE] = parent_data.get(
            const.DATA_PARENT_MOBILE_NOTIFY_SERVICE,
            parent_info.get(
                const.DATA_PARENT_MOBILE_NOTIFY_SERVICE, const.SENTINEL_EMPTY
            ),
        )
        parent_info[const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS] = parent_data.get(
            const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS,
            parent_info.get(const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS, True),
        )

        const.LOGGER.debug(
            "DEBUG: Parent Updated - '%s', ID '%s'",
            parent_info[const.DATA_PARENT_NAME],
            parent_id,
        )

    # -- Chores
    def _create_chore(self, chore_id: str, chore_data: dict[str, Any]):
        # assigned_kids now contains UUIDs directly from flow helpers (no conversion needed)
        assigned_kids_ids = chore_data.get(const.DATA_CHORE_ASSIGNED_KIDS, [])

        # If chore is recurring, set due_date to creation date if not set
        # CLS 20251110 Due date no longer required for recurring
        # freq = chore_data.get(
        #    const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
        # )
        # if freq != const.FREQUENCY_NONE and not chore_data.get(
        #    const.DATA_CHORE_DUE_DATE
        # ):
        #    now_local = kh.get_now_local_time()
        # Force the time to 23:59:00 (and zero microseconds)
        #    default_due = now_local.replace(**const.DEFAULT_DUE_TIME)
        #    chore_data[const.DATA_CHORE_DUE_DATE] = default_due.isoformat()
        #    const.LOGGER.debug(
        #        "DEBUG: Chore '%s' has frequency set to '%s' but no due date. Defaulting to 23:59 local time: %s",
        #        chore_data.get(const.DATA_CHORE_NAME, chore_id),
        #        freq,
        #        chore_data[const.DATA_CHORE_DUE_DATE],
        #    )

        self._data[const.DATA_CHORES][chore_id] = {
            const.DATA_CHORE_NAME: chore_data.get(
                const.DATA_CHORE_NAME, const.SENTINEL_EMPTY
            ),
            const.DATA_CHORE_STATE: chore_data.get(
                const.DATA_CHORE_STATE, const.CHORE_STATE_PENDING
            ),
            const.DATA_CHORE_DEFAULT_POINTS: chore_data.get(
                const.DATA_CHORE_DEFAULT_POINTS, const.DEFAULT_POINTS
            ),
            const.DATA_CHORE_APPROVAL_RESET_TYPE: chore_data.get(
                const.DATA_CHORE_APPROVAL_RESET_TYPE,
                const.DEFAULT_APPROVAL_RESET_TYPE,
            ),
            const.DATA_CHORE_DESCRIPTION: chore_data.get(
                const.DATA_CHORE_DESCRIPTION, const.SENTINEL_EMPTY
            ),
            const.DATA_CHORE_LABELS: chore_data.get(const.DATA_CHORE_LABELS, []),
            const.DATA_CHORE_ICON: chore_data.get(
                const.DATA_CHORE_ICON, const.DEFAULT_ICON
            ),
            const.DATA_CHORE_ASSIGNED_KIDS: assigned_kids_ids,
            const.DATA_CHORE_RECURRING_FREQUENCY: chore_data.get(
                const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
            ),
            const.DATA_CHORE_CUSTOM_INTERVAL: chore_data.get(
                const.DATA_CHORE_CUSTOM_INTERVAL
            )
            if chore_data.get(const.DATA_CHORE_RECURRING_FREQUENCY)
            == const.FREQUENCY_CUSTOM
            else None,
            const.DATA_CHORE_CUSTOM_INTERVAL_UNIT: chore_data.get(
                const.DATA_CHORE_CUSTOM_INTERVAL_UNIT
            )
            if chore_data.get(const.DATA_CHORE_RECURRING_FREQUENCY)
            == const.FREQUENCY_CUSTOM
            else None,
            const.DATA_CHORE_DUE_DATE: chore_data.get(const.DATA_CHORE_DUE_DATE),
            const.DATA_CHORE_LAST_COMPLETED: chore_data.get(
                const.DATA_CHORE_LAST_COMPLETED
            ),
            const.DATA_CHORE_LAST_CLAIMED: chore_data.get(
                const.DATA_CHORE_LAST_CLAIMED
            ),
            const.DATA_CHORE_APPLICABLE_DAYS: chore_data.get(
                const.DATA_CHORE_APPLICABLE_DAYS, []
            ),
            const.DATA_CHORE_NOTIFY_ON_CLAIM: chore_data.get(
                const.DATA_CHORE_NOTIFY_ON_CLAIM, const.DEFAULT_NOTIFY_ON_CLAIM
            ),
            const.DATA_CHORE_NOTIFY_ON_APPROVAL: chore_data.get(
                const.DATA_CHORE_NOTIFY_ON_APPROVAL, const.DEFAULT_NOTIFY_ON_APPROVAL
            ),
            const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL: chore_data.get(
                const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL,
                const.DEFAULT_NOTIFY_ON_DISAPPROVAL,
            ),
            const.DATA_CHORE_SHOW_ON_CALENDAR: chore_data.get(
                const.DATA_CHORE_SHOW_ON_CALENDAR, const.DEFAULT_CHORE_SHOW_ON_CALENDAR
            ),
            const.DATA_CHORE_AUTO_APPROVE: chore_data.get(
                const.DATA_CHORE_AUTO_APPROVE, const.DEFAULT_CHORE_AUTO_APPROVE
            ),
            const.DATA_CHORE_INTERNAL_ID: chore_id,
            # Option B: completion_criteria for SHARED vs INDEPENDENT chores
            const.DATA_CHORE_COMPLETION_CRITERIA: chore_data.get(
                const.DATA_CHORE_COMPLETION_CRITERIA,
                const.COMPLETION_CRITERIA_INDEPENDENT,
            ),
            # Phase 4: approval_period_start (None until first approval)
            const.DATA_CHORE_APPROVAL_PERIOD_START: chore_data.get(
                const.DATA_CHORE_APPROVAL_PERIOD_START
            ),
            # Per-kid due dates for INDEPENDENT chores
            const.DATA_CHORE_PER_KID_DUE_DATES: chore_data.get(
                const.DATA_CHORE_PER_KID_DUE_DATES, {}
            ),
        }
        const.LOGGER.debug(
            "DEBUG: Chore Added - '%s', ID '%s'",
            self._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_NAME],
            chore_id,
        )

        # Notify Kids of new chore
        new_name = self._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_NAME]
        due_date = self._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_DUE_DATE]
        for kid_id in assigned_kids_ids:
            due_str = due_date if due_date else const.TRANS_KEY_NO_DUE_DATE
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHORE_ID: chore_id}
            self.hass.async_create_task(
                self._notify_kid_translated(
                    kid_id,
                    title_key=const.TRANS_KEY_NOTIF_TITLE_CHORE_ASSIGNED,
                    message_key=const.TRANS_KEY_NOTIF_MESSAGE_CHORE_ASSIGNED,
                    message_data={"chore_name": new_name, "due_date": due_str},
                    extra_data=extra_data,
                )
            )

    def _update_chore(self, chore_id: str, chore_data: dict[str, Any]) -> bool:
        """Update chore data. Returns True if assigned kids changed (requiring reload)."""
        chore_info = self._data[const.DATA_CHORES][chore_id]
        chore_info[const.DATA_CHORE_NAME] = chore_data.get(
            const.DATA_CHORE_NAME, chore_info[const.DATA_CHORE_NAME]
        )
        chore_info[const.DATA_CHORE_STATE] = chore_data.get(
            const.DATA_CHORE_STATE, chore_info[const.DATA_CHORE_STATE]
        )
        chore_info[const.DATA_CHORE_DEFAULT_POINTS] = chore_data.get(
            const.DATA_CHORE_DEFAULT_POINTS, chore_info[const.DATA_CHORE_DEFAULT_POINTS]
        )
        chore_info[const.DATA_CHORE_APPROVAL_RESET_TYPE] = chore_data.get(
            const.DATA_CHORE_APPROVAL_RESET_TYPE,
            chore_info.get(
                const.DATA_CHORE_APPROVAL_RESET_TYPE,
                const.DEFAULT_APPROVAL_RESET_TYPE,
            ),
        )
        chore_info[const.DATA_CHORE_DESCRIPTION] = chore_data.get(
            const.DATA_CHORE_DESCRIPTION, chore_info[const.DATA_CHORE_DESCRIPTION]
        )
        chore_info[const.DATA_CHORE_LABELS] = chore_data.get(
            const.DATA_CHORE_LABELS,
            chore_info.get(const.DATA_CHORE_LABELS, []),
        )
        chore_info[const.DATA_CHORE_ICON] = chore_data.get(
            const.DATA_CHORE_ICON, chore_info[const.DATA_CHORE_ICON]
        )

        # assigned_kids now contains UUIDs directly from flow helpers (no conversion needed)
        assigned_kids_ids = chore_data.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        old_assigned = set(chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []))
        new_assigned = set(assigned_kids_ids)

        # Check if kids were ADDED (reload needed to create new entities)
        # Removed kids don't need reload - we just remove their entities
        added_kids = new_assigned - old_assigned
        assignments_changed = len(added_kids) > 0

        removed_kids = old_assigned - new_assigned
        for kid in removed_kids:
            self._remove_kid_chore_entities(kid, chore_id)
            self._cleanup_chore_from_kid(kid, chore_id)

        # Update the chore's assigned kids list with the new assignments
        chore_info[const.DATA_CHORE_ASSIGNED_KIDS] = list(new_assigned)
        chore_info[const.DATA_CHORE_RECURRING_FREQUENCY] = chore_data.get(
            const.DATA_CHORE_RECURRING_FREQUENCY,
            chore_info[const.DATA_CHORE_RECURRING_FREQUENCY],
        )

        # Handle due_date based on completion criteria to avoid KeyError
        completion_criteria = chore_info.get(
            const.DATA_CHORE_COMPLETION_CRITERIA,
            const.COMPLETION_CRITERIA_INDEPENDENT,  # Legacy default
        )
        if completion_criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
            # For INDEPENDENT chores: chore-level due_date should remain None
            # (per_kid_due_dates are authoritative)
            chore_info[const.DATA_CHORE_DUE_DATE] = None
        else:
            # For SHARED chores: update chore-level due_date normally
            chore_info[const.DATA_CHORE_DUE_DATE] = chore_data.get(
                const.DATA_CHORE_DUE_DATE, chore_info.get(const.DATA_CHORE_DUE_DATE)
            )

        chore_info[const.DATA_CHORE_LAST_COMPLETED] = chore_data.get(
            const.DATA_CHORE_LAST_COMPLETED,
            chore_info.get(const.DATA_CHORE_LAST_COMPLETED),
        )
        chore_info[const.DATA_CHORE_LAST_CLAIMED] = chore_data.get(
            const.DATA_CHORE_LAST_CLAIMED, chore_info.get(const.DATA_CHORE_LAST_CLAIMED)
        )
        chore_info[const.DATA_CHORE_APPLICABLE_DAYS] = chore_data.get(
            const.DATA_CHORE_APPLICABLE_DAYS,
            chore_info.get(const.DATA_CHORE_APPLICABLE_DAYS, []),
        )
        chore_info[const.DATA_CHORE_NOTIFY_ON_CLAIM] = chore_data.get(
            const.DATA_CHORE_NOTIFY_ON_CLAIM,
            chore_info.get(
                const.DATA_CHORE_NOTIFY_ON_CLAIM, const.DEFAULT_NOTIFY_ON_CLAIM
            ),
        )
        chore_info[const.DATA_CHORE_NOTIFY_ON_APPROVAL] = chore_data.get(
            const.DATA_CHORE_NOTIFY_ON_APPROVAL,
            chore_info.get(
                const.DATA_CHORE_NOTIFY_ON_APPROVAL, const.DEFAULT_NOTIFY_ON_APPROVAL
            ),
        )
        chore_info[const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL] = chore_data.get(
            const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL,
            chore_info.get(
                const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL,
                const.DEFAULT_NOTIFY_ON_DISAPPROVAL,
            ),
        )

        if chore_info[const.DATA_CHORE_RECURRING_FREQUENCY] == const.FREQUENCY_CUSTOM:
            chore_info[const.DATA_CHORE_CUSTOM_INTERVAL] = chore_data.get(
                const.DATA_CHORE_CUSTOM_INTERVAL
            )
            chore_info[const.DATA_CHORE_CUSTOM_INTERVAL_UNIT] = chore_data.get(
                const.DATA_CHORE_CUSTOM_INTERVAL_UNIT
            )
        else:
            chore_info[const.DATA_CHORE_CUSTOM_INTERVAL] = None
            chore_info[const.DATA_CHORE_CUSTOM_INTERVAL_UNIT] = None

        # Component 8: Handle completion_criteria changes (INDEPENDENT ↔ SHARED)
        old_criteria = chore_info.get(
            const.DATA_CHORE_COMPLETION_CRITERIA,
            const.COMPLETION_CRITERIA_INDEPENDENT,  # Legacy default
        )
        new_criteria = chore_data.get(
            const.DATA_CHORE_COMPLETION_CRITERIA,
            old_criteria,  # Keep existing if not provided
        )

        # Detect criteria change and convert data accordingly
        if new_criteria != old_criteria:
            const.LOGGER.info(
                "INFO: Chore '%s' completion criteria changed: %s → %s",
                chore_info[const.DATA_CHORE_NAME],
                old_criteria,
                new_criteria,
            )
            if (
                old_criteria == const.COMPLETION_CRITERIA_INDEPENDENT
                and new_criteria == const.COMPLETION_CRITERIA_SHARED
            ):
                # INDEPENDENT → SHARED: Remove per_kid_due_dates
                self._convert_independent_to_shared(chore_id, chore_info, chore_data)
            elif (
                old_criteria == const.COMPLETION_CRITERIA_SHARED
                and new_criteria == const.COMPLETION_CRITERIA_INDEPENDENT
            ):
                # SHARED → INDEPENDENT: Populate per_kid_due_dates from template
                self._convert_shared_to_independent(chore_id, chore_info, chore_data)

        # Update completion_criteria
        chore_info[const.DATA_CHORE_COMPLETION_CRITERIA] = new_criteria

        # Update per_kid_due_dates if provided in chore_data (from flow)
        if const.DATA_CHORE_PER_KID_DUE_DATES in chore_data:
            chore_info[const.DATA_CHORE_PER_KID_DUE_DATES] = chore_data[
                const.DATA_CHORE_PER_KID_DUE_DATES
            ]

        const.LOGGER.debug(
            "DEBUG: Chore Updated - '%s', ID '%s'",
            chore_info[const.DATA_CHORE_NAME],
            chore_id,
        )

        self.hass.async_create_task(self._check_overdue_chores())
        return assignments_changed

    def _convert_independent_to_shared(
        self,
        chore_id: str,
        chore_info: dict[str, Any],
        chore_data: dict[str, Any],
    ) -> None:
        """Convert chore from INDEPENDENT to SHARED mode.

        Component 8: Handles data transformation when user changes completion_criteria.

        Scenario A (INDEPENDENT → SHARED):
        - Remove per_kid_due_dates (no longer needed)
        - Keep chore-level due_date as the single source of truth
        - The chore-level due_date already exists (template), no change needed
        """
        chore_name = chore_info.get(const.DATA_CHORE_NAME, chore_id)
        const.LOGGER.debug(
            "DEBUG: Converting chore '%s' from INDEPENDENT to SHARED mode",
            chore_name,
        )

        # Clear per_kid_due_dates - no longer needed in SHARED mode
        if const.DATA_CHORE_PER_KID_DUE_DATES in chore_info:
            del chore_info[const.DATA_CHORE_PER_KID_DUE_DATES]

        # Also remove from incoming chore_data if present (prevent re-adding)
        if const.DATA_CHORE_PER_KID_DUE_DATES in chore_data:
            del chore_data[const.DATA_CHORE_PER_KID_DUE_DATES]

        const.LOGGER.debug(
            "DEBUG: Chore '%s' converted to SHARED - per_kid_due_dates removed",
            chore_name,
        )

    def _convert_shared_to_independent(
        self,
        chore_id: str,
        chore_info: dict[str, Any],
        chore_data: dict[str, Any],
    ) -> None:
        """Convert chore from SHARED to INDEPENDENT mode.

        Component 8: Handles data transformation when user changes completion_criteria.

        Scenario B (SHARED → INDEPENDENT):
        - Populate per_kid_due_dates from the chore-level template due_date
        - Each assigned kid gets the same initial due date (from template)
        - Future rescheduling will handle per-kid due dates independently
        """
        chore_name = chore_info.get(const.DATA_CHORE_NAME, chore_id)
        const.LOGGER.debug(
            "DEBUG: Converting chore '%s' from SHARED to INDEPENDENT mode",
            chore_name,
        )

        # Get template due_date from chore_data (new value) or chore_info (existing)
        template_due_date = chore_data.get(
            const.DATA_CHORE_DUE_DATE,
            chore_info.get(const.DATA_CHORE_DUE_DATE),
        )

        # Get assigned kids from chore_data (new) or chore_info (existing)
        assigned_kids = chore_data.get(
            const.DATA_CHORE_ASSIGNED_KIDS,
            chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []),
        )

        # Build per_kid_due_dates with template for all assigned kids
        per_kid_due_dates: dict[str, str | None] = {}
        for kid_id in assigned_kids:
            per_kid_due_dates[kid_id] = template_due_date

        # Set per_kid_due_dates on chore_info
        chore_info[const.DATA_CHORE_PER_KID_DUE_DATES] = per_kid_due_dates

        # Also update chore_data so the later update loop doesn't overwrite
        chore_data[const.DATA_CHORE_PER_KID_DUE_DATES] = per_kid_due_dates

        const.LOGGER.debug(
            "DEBUG: Chore '%s' converted to INDEPENDENT - per_kid_due_dates "
            "populated from template for %d kids",
            chore_name,
            len(per_kid_due_dates),
        )

    # -- Badges
    def _create_badge(self, badge_id: str, badge_data: dict[str, Any]):
        """Create a new badge entity."""

        # --- Simplified Logic ---
        # Directly assign badge_data to badge_info.
        # This assumes badge_data is already validated and contains all necessary fields.
        self._data.setdefault(const.DATA_BADGES, {})[badge_id] = badge_data

        badge_info = self._data[const.DATA_BADGES][badge_id]
        badge_name = badge_info.get(const.DATA_BADGE_NAME, const.SENTINEL_EMPTY)

        const.LOGGER.debug(
            "DEBUG: Badge Updated - '%s', ID '%s'",
            badge_name,
            badge_id,
        )

    def _update_badge(self, badge_id: str, badge_data: dict[str, Any]):
        """Update an existing badge entity, only updating fields present in badge_data."""

        badges = self._data.setdefault(const.DATA_BADGES, {})
        existing = badges.get(badge_id, {})
        # Only update fields present in badge_data, preserving all others
        existing.update(badge_data)
        badges[badge_id] = existing

        badge_name = existing.get(const.DATA_BADGE_NAME, const.SENTINEL_EMPTY)
        const.LOGGER.debug(
            "DEBUG: Badge Updated - '%s', ID '%s'",
            badge_name,
            badge_id,
        )

    # -- Rewards
    def _create_reward(self, reward_id: str, reward_data: dict[str, Any]):
        self._data[const.DATA_REWARDS][reward_id] = {
            const.DATA_REWARD_NAME: reward_data.get(
                const.DATA_REWARD_NAME, const.SENTINEL_EMPTY
            ),
            const.DATA_REWARD_COST: reward_data.get(
                const.DATA_REWARD_COST, const.DEFAULT_REWARD_COST
            ),
            const.DATA_REWARD_DESCRIPTION: reward_data.get(
                const.DATA_REWARD_DESCRIPTION, const.SENTINEL_EMPTY
            ),
            const.DATA_REWARD_LABELS: reward_data.get(const.DATA_REWARD_LABELS, []),
            const.DATA_REWARD_ICON: reward_data.get(
                const.DATA_REWARD_ICON, const.DEFAULT_REWARD_ICON
            ),
            const.DATA_REWARD_INTERNAL_ID: reward_id,
        }
        const.LOGGER.debug(
            "DEBUG: Reward Added - '%s', ID '%s'",
            self._data[const.DATA_REWARDS][reward_id][const.DATA_REWARD_NAME],
            reward_id,
        )

    def _update_reward(self, reward_id: str, reward_data: dict[str, Any]):
        reward_info = self._data[const.DATA_REWARDS][reward_id]

        reward_info[const.DATA_REWARD_NAME] = reward_data.get(
            const.DATA_REWARD_NAME, reward_info[const.DATA_REWARD_NAME]
        )
        reward_info[const.DATA_REWARD_COST] = reward_data.get(
            const.DATA_REWARD_COST, reward_info[const.DATA_REWARD_COST]
        )
        reward_info[const.DATA_REWARD_DESCRIPTION] = reward_data.get(
            const.DATA_REWARD_DESCRIPTION, reward_info[const.DATA_REWARD_DESCRIPTION]
        )
        reward_info[const.DATA_REWARD_LABELS] = reward_data.get(
            const.DATA_REWARD_LABELS, reward_info.get(const.DATA_REWARD_LABELS, [])
        )
        reward_info[const.DATA_REWARD_ICON] = reward_data.get(
            const.DATA_REWARD_ICON, reward_info[const.DATA_REWARD_ICON]
        )
        const.LOGGER.debug(
            "DEBUG: Reward Updated - '%s', ID '%s'",
            reward_info[const.DATA_REWARD_NAME],
            reward_id,
        )

    # -- Bonuses
    def _create_bonus(self, bonus_id: str, bonus_data: dict[str, Any]):
        self._data[const.DATA_BONUSES][bonus_id] = {
            const.DATA_BONUS_NAME: bonus_data.get(
                const.DATA_BONUS_NAME, const.SENTINEL_EMPTY
            ),
            const.DATA_BONUS_POINTS: bonus_data.get(
                const.DATA_BONUS_POINTS, const.DEFAULT_BONUS_POINTS
            ),
            const.DATA_BONUS_DESCRIPTION: bonus_data.get(
                const.DATA_BONUS_DESCRIPTION, const.SENTINEL_EMPTY
            ),
            const.DATA_BONUS_LABELS: bonus_data.get(const.DATA_BONUS_LABELS, []),
            const.DATA_BONUS_ICON: bonus_data.get(
                const.DATA_BONUS_ICON, const.DEFAULT_BONUS_ICON
            ),
            const.DATA_BONUS_INTERNAL_ID: bonus_id,
        }
        const.LOGGER.debug(
            "DEBUG: Bonus Added - '%s', ID '%s'",
            self._data[const.DATA_BONUSES][bonus_id][const.DATA_BONUS_NAME],
            bonus_id,
        )

    def _update_bonus(self, bonus_id: str, bonus_data: dict[str, Any]):
        bonus_info = self._data[const.DATA_BONUSES][bonus_id]
        bonus_info[const.DATA_BONUS_NAME] = bonus_data.get(
            const.DATA_BONUS_NAME, bonus_info[const.DATA_BONUS_NAME]
        )
        bonus_info[const.DATA_BONUS_POINTS] = bonus_data.get(
            const.DATA_BONUS_POINTS, bonus_info[const.DATA_BONUS_POINTS]
        )
        bonus_info[const.DATA_BONUS_DESCRIPTION] = bonus_data.get(
            const.DATA_BONUS_DESCRIPTION, bonus_info[const.DATA_BONUS_DESCRIPTION]
        )
        bonus_info[const.DATA_BONUS_LABELS] = bonus_data.get(
            const.DATA_BONUS_LABELS, bonus_info.get(const.DATA_BONUS_LABELS, [])
        )
        bonus_info[const.DATA_BONUS_ICON] = bonus_data.get(
            const.DATA_BONUS_ICON, bonus_info[const.DATA_BONUS_ICON]
        )
        const.LOGGER.debug(
            "DEBUG: Bonus Updated - '%s', ID '%s'",
            bonus_info[const.DATA_BONUS_NAME],
            bonus_id,
        )

    # -- Penalties
    def _create_penalty(self, penalty_id: str, penalty_data: dict[str, Any]):
        self._data[const.DATA_PENALTIES][penalty_id] = {
            const.DATA_PENALTY_NAME: penalty_data.get(
                const.DATA_PENALTY_NAME, const.SENTINEL_EMPTY
            ),
            const.DATA_PENALTY_POINTS: penalty_data.get(
                const.DATA_PENALTY_POINTS, -const.DEFAULT_PENALTY_POINTS
            ),
            const.DATA_PENALTY_DESCRIPTION: penalty_data.get(
                const.DATA_PENALTY_DESCRIPTION, const.SENTINEL_EMPTY
            ),
            const.DATA_PENALTY_LABELS: penalty_data.get(const.DATA_PENALTY_LABELS, []),
            const.DATA_PENALTY_ICON: penalty_data.get(
                const.DATA_PENALTY_ICON, const.DEFAULT_PENALTY_ICON
            ),
            const.DATA_PENALTY_INTERNAL_ID: penalty_id,
        }
        const.LOGGER.debug(
            "DEBUG: Penalty Added - '%s', ID '%s'",
            self._data[const.DATA_PENALTIES][penalty_id][const.DATA_PENALTY_NAME],
            penalty_id,
        )

    def _update_penalty(self, penalty_id: str, penalty_data: dict[str, Any]):
        penalty_info = self._data[const.DATA_PENALTIES][penalty_id]
        penalty_info[const.DATA_PENALTY_NAME] = penalty_data.get(
            const.DATA_PENALTY_NAME, penalty_info[const.DATA_PENALTY_NAME]
        )
        penalty_info[const.DATA_PENALTY_POINTS] = penalty_data.get(
            const.DATA_PENALTY_POINTS, penalty_info[const.DATA_PENALTY_POINTS]
        )
        penalty_info[const.DATA_PENALTY_DESCRIPTION] = penalty_data.get(
            const.DATA_PENALTY_DESCRIPTION, penalty_info[const.DATA_PENALTY_DESCRIPTION]
        )
        penalty_info[const.DATA_PENALTY_LABELS] = penalty_data.get(
            const.DATA_PENALTY_LABELS, penalty_info.get(const.DATA_PENALTY_LABELS, [])
        )
        penalty_info[const.DATA_PENALTY_ICON] = penalty_data.get(
            const.DATA_PENALTY_ICON, penalty_info[const.DATA_PENALTY_ICON]
        )
        const.LOGGER.debug(
            "DEBUG: Penalty Updated - '%s', ID '%s'",
            penalty_info[const.DATA_PENALTY_NAME],
            penalty_id,
        )

    # -- Achievements
    def _create_achievement(
        self, achievement_id: str, achievement_data: dict[str, Any]
    ):
        self._data[const.DATA_ACHIEVEMENTS][achievement_id] = {
            const.DATA_ACHIEVEMENT_NAME: achievement_data.get(
                const.DATA_ACHIEVEMENT_NAME, const.SENTINEL_EMPTY
            ),
            const.DATA_ACHIEVEMENT_DESCRIPTION: achievement_data.get(
                const.DATA_ACHIEVEMENT_DESCRIPTION, const.SENTINEL_EMPTY
            ),
            const.DATA_ACHIEVEMENT_LABELS: achievement_data.get(
                const.DATA_ACHIEVEMENT_LABELS, []
            ),
            const.DATA_ACHIEVEMENT_ICON: achievement_data.get(
                const.DATA_ACHIEVEMENT_ICON, const.SENTINEL_EMPTY
            ),
            const.DATA_ACHIEVEMENT_ASSIGNED_KIDS: achievement_data.get(
                const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, []
            ),
            const.DATA_ACHIEVEMENT_TYPE: achievement_data.get(
                const.DATA_ACHIEVEMENT_TYPE, const.ACHIEVEMENT_TYPE_STREAK
            ),
            const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID: achievement_data.get(
                const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID, const.SENTINEL_EMPTY
            ),
            const.DATA_ACHIEVEMENT_CRITERIA: achievement_data.get(
                const.DATA_ACHIEVEMENT_CRITERIA, const.SENTINEL_EMPTY
            ),
            const.DATA_ACHIEVEMENT_TARGET_VALUE: achievement_data.get(
                const.DATA_ACHIEVEMENT_TARGET_VALUE, const.DEFAULT_ACHIEVEMENT_TARGET
            ),
            const.DATA_ACHIEVEMENT_REWARD_POINTS: achievement_data.get(
                const.DATA_ACHIEVEMENT_REWARD_POINTS,
                const.DEFAULT_ACHIEVEMENT_REWARD_POINTS,
            ),
            const.DATA_ACHIEVEMENT_PROGRESS: achievement_data.get(
                const.DATA_ACHIEVEMENT_PROGRESS, {}
            ),
            const.DATA_ACHIEVEMENT_INTERNAL_ID: achievement_id,
        }
        const.LOGGER.debug(
            "DEBUG: Achievement Added - '%s', ID '%s'",
            self._data[const.DATA_ACHIEVEMENTS][achievement_id][
                const.DATA_ACHIEVEMENT_NAME
            ],
            achievement_id,
        )

    def _update_achievement(
        self, achievement_id: str, achievement_data: dict[str, Any]
    ):
        achievement_info = self._data[const.DATA_ACHIEVEMENTS][achievement_id]
        achievement_info[const.DATA_ACHIEVEMENT_NAME] = achievement_data.get(
            const.DATA_ACHIEVEMENT_NAME, achievement_info[const.DATA_ACHIEVEMENT_NAME]
        )
        achievement_info[const.DATA_ACHIEVEMENT_DESCRIPTION] = achievement_data.get(
            const.DATA_ACHIEVEMENT_DESCRIPTION,
            achievement_info[const.DATA_ACHIEVEMENT_DESCRIPTION],
        )
        achievement_info[const.DATA_ACHIEVEMENT_LABELS] = achievement_data.get(
            const.DATA_ACHIEVEMENT_LABELS,
            achievement_info.get(const.DATA_ACHIEVEMENT_LABELS, []),
        )
        achievement_info[const.DATA_ACHIEVEMENT_ICON] = achievement_data.get(
            const.DATA_ACHIEVEMENT_ICON, achievement_info[const.DATA_ACHIEVEMENT_ICON]
        )
        achievement_info[const.DATA_ACHIEVEMENT_ASSIGNED_KIDS] = achievement_data.get(
            const.DATA_ACHIEVEMENT_ASSIGNED_KIDS,
            achievement_info[const.DATA_ACHIEVEMENT_ASSIGNED_KIDS],
        )
        achievement_info[const.DATA_ACHIEVEMENT_TYPE] = achievement_data.get(
            const.DATA_ACHIEVEMENT_TYPE, achievement_info[const.DATA_ACHIEVEMENT_TYPE]
        )
        achievement_info[const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID] = (
            achievement_data.get(
                const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID,
                achievement_info.get(
                    const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID, const.SENTINEL_EMPTY
                ),
            )
        )
        achievement_info[const.DATA_ACHIEVEMENT_CRITERIA] = achievement_data.get(
            const.DATA_ACHIEVEMENT_CRITERIA,
            achievement_info[const.DATA_ACHIEVEMENT_CRITERIA],
        )
        achievement_info[const.DATA_ACHIEVEMENT_TARGET_VALUE] = achievement_data.get(
            const.DATA_ACHIEVEMENT_TARGET_VALUE,
            achievement_info[const.DATA_ACHIEVEMENT_TARGET_VALUE],
        )
        achievement_info[const.DATA_ACHIEVEMENT_REWARD_POINTS] = achievement_data.get(
            const.DATA_ACHIEVEMENT_REWARD_POINTS,
            achievement_info[const.DATA_ACHIEVEMENT_REWARD_POINTS],
        )
        const.LOGGER.debug(
            "DEBUG: Achievement Updated - '%s', ID '%s'",
            achievement_info[const.DATA_ACHIEVEMENT_NAME],
            achievement_id,
        )

    # -- Challenges
    def _create_challenge(self, challenge_id: str, challenge_data: dict[str, Any]):
        self._data[const.DATA_CHALLENGES][challenge_id] = {
            const.DATA_CHALLENGE_NAME: challenge_data.get(
                const.DATA_CHALLENGE_NAME, const.SENTINEL_EMPTY
            ),
            const.DATA_CHALLENGE_DESCRIPTION: challenge_data.get(
                const.DATA_CHALLENGE_DESCRIPTION, const.SENTINEL_EMPTY
            ),
            const.DATA_CHALLENGE_LABELS: challenge_data.get(
                const.DATA_CHALLENGE_LABELS, []
            ),
            const.DATA_CHALLENGE_ICON: challenge_data.get(
                const.DATA_CHALLENGE_ICON, const.SENTINEL_EMPTY
            ),
            const.DATA_CHALLENGE_ASSIGNED_KIDS: challenge_data.get(
                const.DATA_CHALLENGE_ASSIGNED_KIDS, []
            ),
            const.DATA_CHALLENGE_TYPE: challenge_data.get(
                const.DATA_CHALLENGE_TYPE, const.CHALLENGE_TYPE_DAILY_MIN
            ),
            const.DATA_CHALLENGE_SELECTED_CHORE_ID: challenge_data.get(
                const.DATA_CHALLENGE_SELECTED_CHORE_ID, const.SENTINEL_EMPTY
            ),
            const.DATA_CHALLENGE_CRITERIA: challenge_data.get(
                const.DATA_CHALLENGE_CRITERIA, const.SENTINEL_EMPTY
            ),
            const.DATA_CHALLENGE_TARGET_VALUE: challenge_data.get(
                const.DATA_CHALLENGE_TARGET_VALUE, const.DEFAULT_CHALLENGE_TARGET
            ),
            const.DATA_CHALLENGE_REWARD_POINTS: challenge_data.get(
                const.DATA_CHALLENGE_REWARD_POINTS,
                const.DEFAULT_CHALLENGE_REWARD_POINTS,
            ),
            const.DATA_CHALLENGE_START_DATE: (
                challenge_data.get(const.DATA_CHALLENGE_START_DATE)
                if challenge_data.get(const.DATA_CHALLENGE_START_DATE) not in [None, {}]
                else None
            ),
            const.DATA_CHALLENGE_END_DATE: (
                challenge_data.get(const.DATA_CHALLENGE_END_DATE)
                if challenge_data.get(const.DATA_CHALLENGE_END_DATE) not in [None, {}]
                else None
            ),
            const.DATA_CHALLENGE_PROGRESS: challenge_data.get(
                const.DATA_CHALLENGE_PROGRESS, {}
            ),
            const.DATA_CHALLENGE_INTERNAL_ID: challenge_id,
        }
        const.LOGGER.debug(
            "DEBUG: Challenge Added - '%s', ID '%s'",
            self._data[const.DATA_CHALLENGES][challenge_id][const.DATA_CHALLENGE_NAME],
            challenge_id,
        )

    def _update_challenge(self, challenge_id: str, challenge_data: dict[str, Any]):
        challenge_info = self._data[const.DATA_CHALLENGES][challenge_id]
        challenge_info[const.DATA_CHALLENGE_NAME] = challenge_data.get(
            const.DATA_CHALLENGE_NAME, challenge_info[const.DATA_CHALLENGE_NAME]
        )
        challenge_info[const.DATA_CHALLENGE_DESCRIPTION] = challenge_data.get(
            const.DATA_CHALLENGE_DESCRIPTION,
            challenge_info[const.DATA_CHALLENGE_DESCRIPTION],
        )
        challenge_info[const.DATA_CHALLENGE_LABELS] = challenge_data.get(
            const.DATA_CHALLENGE_LABELS,
            challenge_info.get(const.DATA_CHALLENGE_LABELS, []),
        )
        challenge_info[const.DATA_CHALLENGE_ICON] = challenge_data.get(
            const.DATA_CHALLENGE_ICON, challenge_info[const.DATA_CHALLENGE_ICON]
        )
        challenge_info[const.DATA_CHALLENGE_ASSIGNED_KIDS] = challenge_data.get(
            const.DATA_CHALLENGE_ASSIGNED_KIDS,
            challenge_info[const.DATA_CHALLENGE_ASSIGNED_KIDS],
        )
        challenge_info[const.DATA_CHALLENGE_TYPE] = challenge_data.get(
            const.DATA_CHALLENGE_TYPE, challenge_info[const.DATA_CHALLENGE_TYPE]
        )
        challenge_info[const.DATA_CHALLENGE_SELECTED_CHORE_ID] = challenge_data.get(
            const.DATA_CHALLENGE_SELECTED_CHORE_ID,
            challenge_info.get(
                const.DATA_CHALLENGE_SELECTED_CHORE_ID, const.SENTINEL_EMPTY
            ),
        )
        challenge_info[const.DATA_CHALLENGE_CRITERIA] = challenge_data.get(
            const.DATA_CHALLENGE_CRITERIA, challenge_info[const.DATA_CHALLENGE_CRITERIA]
        )
        challenge_info[const.DATA_CHALLENGE_TARGET_VALUE] = challenge_data.get(
            const.DATA_CHALLENGE_TARGET_VALUE,
            challenge_info[const.DATA_CHALLENGE_TARGET_VALUE],
        )
        challenge_info[const.DATA_CHALLENGE_REWARD_POINTS] = challenge_data.get(
            const.DATA_CHALLENGE_REWARD_POINTS,
            challenge_info[const.DATA_CHALLENGE_REWARD_POINTS],
        )
        challenge_info[const.DATA_CHALLENGE_START_DATE] = (
            challenge_data.get(const.DATA_CHALLENGE_START_DATE)
            if challenge_data.get(const.DATA_CHALLENGE_START_DATE) not in [None, {}]
            else None
        )
        challenge_info[const.DATA_CHALLENGE_END_DATE] = (
            challenge_data.get(const.DATA_CHALLENGE_END_DATE)
            if challenge_data.get(const.DATA_CHALLENGE_END_DATE) not in [None, {}]
            else None
        )
        const.LOGGER.debug(
            "DEBUG: Challenge Updated - '%s', ID '%s'",
            challenge_info[const.DATA_CHALLENGE_NAME],
            challenge_id,
        )

    # -------------------------------------------------------------------------------------
    # Public Entity Management Methods (for Options Flow - Phase 3)
    # These methods provide direct storage updates without triggering config reloads
    # -------------------------------------------------------------------------------------

    def _update_kid_device_name(self, kid_id: str, kid_name: str) -> None:
        """Update kid device name in device registry.

        When a kid's name changes, this function updates the corresponding
        device registry entry so the device name reflects immediately without
        requiring a reboot. This also cascades to entity friendly names.

        Args:
            kid_id: Internal UUID of the kid
            kid_name: New name for the kid

        """
        from homeassistant.helpers import device_registry as dr

        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(identifiers={(const.DOMAIN, kid_id)})

        if device:
            new_device_name = f"{kid_name} ({self.config_entry.title})"
            device_registry.async_update_device(device.id, name=new_device_name)
            const.LOGGER.debug(
                "Updated device name for kid '%s' (ID: %s) to '%s'",
                kid_name,
                kid_id,
                new_device_name,
            )
        else:
            const.LOGGER.warning(
                "Device not found for kid '%s' (ID: %s), cannot update name",
                kid_name,
                kid_id,
            )

    def update_kid_entity(self, kid_id: str, kid_data: dict[str, Any]) -> None:
        """Update kid entity in storage (Options Flow - no reload).

        Args:
            kid_id: Internal ID of the kid
            kid_data: Dictionary with kid fields to update
        """
        if kid_id not in self._data.get(const.DATA_KIDS, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_KID,
                    "name": kid_id,
                },
            )

        # Check if name is changing
        old_name = self._data[const.DATA_KIDS][kid_id].get(const.DATA_KID_NAME)
        new_name = kid_data.get(const.DATA_KID_NAME)

        self._update_kid(kid_id, kid_data)
        self._persist()

        # Update device registry if name changed
        if new_name and new_name != old_name:
            self._update_kid_device_name(kid_id, new_name)

        self.async_update_listeners()

    def delete_kid_entity(self, kid_id: str) -> None:
        """Delete kid from storage and cleanup references.

        Args:
            kid_id: Internal ID of the kid to delete
        """
        if kid_id not in self._data.get(const.DATA_KIDS, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_KID,
                    "name": kid_id,
                },
            )

        kid_name = self._data[const.DATA_KIDS][kid_id].get(const.DATA_KID_NAME, kid_id)
        del self._data[const.DATA_KIDS][kid_id]

        # Remove HA entities
        self._remove_entities_in_ha(kid_id)

        # Cleanup references
        self._cleanup_deleted_kid_references()
        self._cleanup_parent_assignments()
        self._cleanup_pending_reward_approvals()

        self._persist()
        self.async_update_listeners()
        const.LOGGER.info("INFO: Deleted kid '%s' (ID: %s)", kid_name, kid_id)

    def update_parent_entity(self, parent_id: str, parent_data: dict[str, Any]) -> None:
        """Update parent entity in storage (Options Flow - no reload)."""
        if parent_id not in self._data.get(const.DATA_PARENTS, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_PARENT,
                    "name": parent_id,
                },
            )
        self._update_parent(parent_id, parent_data)
        self._persist()
        self.async_update_listeners()

    def delete_parent_entity(self, parent_id: str) -> None:
        """Delete parent from storage."""
        if parent_id not in self._data.get(const.DATA_PARENTS, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_PARENT,
                    "name": parent_id,
                },
            )

        parent_name = self._data[const.DATA_PARENTS][parent_id].get(
            const.DATA_PARENT_NAME, parent_id
        )
        del self._data[const.DATA_PARENTS][parent_id]

        self._persist()
        self.async_update_listeners()
        const.LOGGER.info("INFO: Deleted parent '%s' (ID: %s)", parent_name, parent_id)

    def update_chore_entity(self, chore_id: str, chore_data: dict[str, Any]) -> bool:
        """Update chore entity in storage (Options Flow).

        Returns True if assigned kids changed (indicating reload is needed).
        """
        if chore_id not in self._data.get(const.DATA_CHORES, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_CHORE,
                    "name": chore_id,
                },
            )
        assignments_changed = self._update_chore(chore_id, chore_data)
        # Recalculate badges affected by chore changes
        self._recalculate_all_badges()
        self._persist()
        self.async_update_listeners()
        # Clean up any orphaned kid-chore entities after assignment changes
        self.hass.async_create_task(self._remove_orphaned_kid_chore_entities())
        return assignments_changed

    def delete_chore_entity(self, chore_id: str) -> None:
        """Delete chore from storage and cleanup references."""
        if chore_id not in self._data.get(const.DATA_CHORES, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_CHORE,
                    "name": chore_id,
                },
            )

        chore_name = self._data[const.DATA_CHORES][chore_id].get(
            const.DATA_CHORE_NAME, chore_id
        )
        del self._data[const.DATA_CHORES][chore_id]

        # Remove HA entities
        self._remove_entities_in_ha(chore_id)

        # Cleanup references
        self._cleanup_deleted_chore_references()
        self._cleanup_deleted_chore_in_achievements()
        self._cleanup_deleted_chore_in_challenges()

        # Remove orphaned shared chore sensors
        self.hass.async_create_task(self._remove_orphaned_shared_chore_sensors())

        self._persist()
        self.async_update_listeners()
        const.LOGGER.info("INFO: Deleted chore '%s' (ID: %s)", chore_name, chore_id)

    def update_badge_entity(self, badge_id: str, badge_data: dict[str, Any]) -> None:
        """Update badge entity in storage (Options Flow - no reload)."""
        if badge_id not in self._data.get(const.DATA_BADGES, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_BADGE,
                    "name": badge_id,
                },
            )
        self._update_badge(badge_id, badge_data)
        # Phase 4: Sync badge_progress after badge update (handles assignment changes)
        for kid_id in self.kids_data:
            self._sync_badge_progress_for_kid(kid_id)
        # Recalculate badge progress for all kids
        self._recalculate_all_badges()
        self._persist()
        self.async_update_listeners()

    def delete_badge_entity(self, badge_id: str) -> None:
        """Delete badge from storage and cleanup references."""
        if badge_id not in self._data.get(const.DATA_BADGES, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_BADGE,
                    "name": badge_id,
                },
            )

        badge_name = self._data[const.DATA_BADGES][badge_id].get(
            const.DATA_BADGE_NAME, badge_id
        )
        del self._data[const.DATA_BADGES][badge_id]

        # Remove awarded badges from kids
        self._remove_awarded_badges_by_id(badge_id=badge_id)

        # Phase 4: Clean up badge_progress from all kids after badge deletion
        # Also recalculate cumulative badge progress since a cumulative badge may have been deleted
        for kid_id in self.kids_data:
            self._sync_badge_progress_for_kid(kid_id)
            # Refresh cumulative badge progress (handles case when cumulative badge is deleted)
            cumulative_progress = self._get_cumulative_badge_progress(kid_id)
            self.kids_data[kid_id][const.DATA_KID_CUMULATIVE_BADGE_PROGRESS] = (
                cumulative_progress
            )

        # Remove badge-related entities from Home Assistant registry
        self._remove_entities_in_ha(badge_id)

        self._persist()
        self.async_update_listeners()
        const.LOGGER.info("INFO: Deleted badge '%s' (ID: %s)", badge_name, badge_id)

    def update_reward_entity(self, reward_id: str, reward_data: dict[str, Any]) -> None:
        """Update reward entity in storage (Options Flow - no reload)."""
        if reward_id not in self._data.get(const.DATA_REWARDS, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_REWARD,
                    "name": reward_id,
                },
            )
        self._update_reward(reward_id, reward_data)
        self._persist()
        self.async_update_listeners()

    def delete_reward_entity(self, reward_id: str) -> None:
        """Delete reward from storage and cleanup references."""
        if reward_id not in self._data.get(const.DATA_REWARDS, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_REWARD,
                    "name": reward_id,
                },
            )

        reward_name = self._data[const.DATA_REWARDS][reward_id].get(
            const.DATA_REWARD_NAME, reward_id
        )
        del self._data[const.DATA_REWARDS][reward_id]

        # Remove HA entities
        self._remove_entities_in_ha(reward_id)

        # Cleanup pending reward approvals
        self._cleanup_pending_reward_approvals()

        self._persist()
        self.async_update_listeners()
        const.LOGGER.info("INFO: Deleted reward '%s' (ID: %s)", reward_name, reward_id)

    def update_penalty_entity(
        self, penalty_id: str, penalty_data: dict[str, Any]
    ) -> None:
        """Update penalty entity in storage (Options Flow - no reload)."""
        if penalty_id not in self._data.get(const.DATA_PENALTIES, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_PENALTY,
                    "name": penalty_id,
                },
            )
        self._update_penalty(penalty_id, penalty_data)
        self._persist()
        self.async_update_listeners()

    def delete_penalty_entity(self, penalty_id: str) -> None:
        """Delete penalty from storage."""
        if penalty_id not in self._data.get(const.DATA_PENALTIES, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_PENALTY,
                    "name": penalty_id,
                },
            )

        penalty_name = self._data[const.DATA_PENALTIES][penalty_id].get(
            const.DATA_PENALTY_NAME, penalty_id
        )
        del self._data[const.DATA_PENALTIES][penalty_id]

        # Remove HA entities
        self._remove_entities_in_ha(penalty_id)

        self._persist()
        self.async_update_listeners()
        const.LOGGER.info(
            "INFO: Deleted penalty '%s' (ID: %s)", penalty_name, penalty_id
        )

    def update_bonus_entity(self, bonus_id: str, bonus_data: dict[str, Any]) -> None:
        """Update bonus entity in storage (Options Flow - no reload)."""
        if bonus_id not in self._data.get(const.DATA_BONUSES, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_BONUS,
                    "name": bonus_id,
                },
            )
        self._update_bonus(bonus_id, bonus_data)
        self._persist()
        self.async_update_listeners()

    def delete_bonus_entity(self, bonus_id: str) -> None:
        """Delete bonus from storage."""
        if bonus_id not in self._data.get(const.DATA_BONUSES, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_BONUS,
                    "name": bonus_id,
                },
            )

        bonus_name = self._data[const.DATA_BONUSES][bonus_id].get(
            const.DATA_BONUS_NAME, bonus_id
        )
        del self._data[const.DATA_BONUSES][bonus_id]

        # Remove HA entities
        self._remove_entities_in_ha(bonus_id)

        self._persist()
        self.async_update_listeners()
        const.LOGGER.info("INFO: Deleted bonus '%s' (ID: %s)", bonus_name, bonus_id)

    def update_achievement_entity(
        self, achievement_id: str, achievement_data: dict[str, Any]
    ) -> None:
        """Update achievement entity in storage (Options Flow - no reload)."""
        if achievement_id not in self._data.get(const.DATA_ACHIEVEMENTS, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_ACHIEVEMENT,
                    "name": achievement_id,
                },
            )
        self._update_achievement(achievement_id, achievement_data)
        self._persist()
        self.async_update_listeners()

    def delete_achievement_entity(self, achievement_id: str) -> None:
        """Delete achievement from storage and cleanup references."""
        if achievement_id not in self._data.get(const.DATA_ACHIEVEMENTS, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_ACHIEVEMENT,
                    "name": achievement_id,
                },
            )

        achievement_name = self._data[const.DATA_ACHIEVEMENTS][achievement_id].get(
            const.DATA_ACHIEVEMENT_NAME, achievement_id
        )
        del self._data[const.DATA_ACHIEVEMENTS][achievement_id]

        # Remove orphaned achievement entities
        self.hass.async_create_task(self._remove_orphaned_achievement_entities())

        self._persist()
        self.async_update_listeners()
        const.LOGGER.info(
            "INFO: Deleted achievement '%s' (ID: %s)", achievement_name, achievement_id
        )

    def update_challenge_entity(
        self, challenge_id: str, challenge_data: dict[str, Any]
    ) -> None:
        """Update challenge entity in storage (Options Flow - no reload)."""
        if challenge_id not in self._data.get(const.DATA_CHALLENGES, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_CHALLENGE,
                    "name": challenge_id,
                },
            )
        self._update_challenge(challenge_id, challenge_data)
        self._persist()
        self.async_update_listeners()

    def delete_challenge_entity(self, challenge_id: str) -> None:
        """Delete challenge from storage and cleanup references."""
        if challenge_id not in self._data.get(const.DATA_CHALLENGES, {}):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_CHALLENGE,
                    "name": challenge_id,
                },
            )

        challenge_name = self._data[const.DATA_CHALLENGES][challenge_id].get(
            const.DATA_CHALLENGE_NAME, challenge_id
        )
        del self._data[const.DATA_CHALLENGES][challenge_id]

        # Remove orphaned challenge entities
        self.hass.async_create_task(self._remove_orphaned_challenge_entities())

        self._persist()
        self.async_update_listeners()
        const.LOGGER.info(
            "INFO: Deleted challenge '%s' (ID: %s)", challenge_name, challenge_id
        )

    # -------------------------------------------------------------------------------------
    # Properties for Easy Access
    # -------------------------------------------------------------------------------------

    @property
    def kids_data(self) -> dict[str, Any]:
        """Return the kids data."""
        return self._data.get(const.DATA_KIDS, {})

    @property
    def parents_data(self) -> dict[str, Any]:
        """Return the parents data."""
        return self._data.get(const.DATA_PARENTS, {})

    @property
    def chores_data(self) -> dict[str, Any]:
        """Return the chores data."""
        return self._data.get(const.DATA_CHORES, {})

    @property
    def badges_data(self) -> dict[str, Any]:
        """Return the badges data."""
        return self._data.get(const.DATA_BADGES, {})

    @property
    def rewards_data(self) -> dict[str, Any]:
        """Return the rewards data."""
        return self._data.get(const.DATA_REWARDS, {})

    @property
    def penalties_data(self) -> dict[str, Any]:
        """Return the penalties data."""
        return self._data.get(const.DATA_PENALTIES, {})

    @property
    def achievements_data(self) -> dict[str, Any]:
        """Return the achievements data."""
        return self._data.get(const.DATA_ACHIEVEMENTS, {})

    @property
    def challenges_data(self) -> dict[str, Any]:
        """Return the challenges data."""
        return self._data.get(const.DATA_CHALLENGES, {})

    @property
    def bonuses_data(self) -> dict[str, Any]:
        """Return the bonuses data."""
        return self._data.get(const.DATA_BONUSES, {})

    @property
    def pending_chore_approvals(self) -> list[dict[str, Any]]:
        """Return the list of pending chore approvals (computed from timestamps).

        Uses timestamp-based tracking instead of legacy queue. A chore is pending
        if it has been claimed but not yet approved or disapproved in the current
        approval period.
        """
        return self.get_pending_chore_approvals_computed()

    @property
    def pending_reward_approvals(self) -> list[dict[str, Any]]:
        """Return the list of pending reward approvals (computed from modern structure)."""
        return self.get_pending_reward_approvals_computed()

    @property
    def pending_chore_changed(self) -> bool:
        """Return whether pending chore approvals have changed since last reset."""
        return self._pending_chore_changed

    @property
    def pending_reward_changed(self) -> bool:
        """Return whether pending reward approvals have changed since last reset."""
        return self._pending_reward_changed

    def reset_pending_change_flags(self) -> None:
        """Reset the pending change flags after UI has processed the changes.

        Called by dashboard helper sensor after rebuilding attributes.
        """
        self._pending_chore_changed = False
        self._pending_reward_changed = False

    # -------------------------------------------------------------------------------------
    # Chores: Claim, Approve, Disapprove, Compute Global State for Shared Chores
    # -------------------------------------------------------------------------------------

    def claim_chore(self, kid_id: str, chore_id: str, user_name: str):  # pylint: disable=unused-argument
        """Kid claims chore => state=claimed; parent must then approve."""
        perf_start = time.perf_counter()
        if chore_id not in self.chores_data:
            const.LOGGER.warning(
                "WARNING: Claim Chore - Chore ID '%s' not found", chore_id
            )
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_CHORE,
                    "name": chore_id,
                },
            )

        chore_info = self.chores_data[chore_id]
        if kid_id not in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            const.LOGGER.warning(
                "WARNING: Claim Chore - Chore ID '%s' not assigned to kid ID '%s'",
                chore_id,
                kid_id,
            )
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_ASSIGNED,
                translation_placeholders={
                    "entity": chore_info.get(const.DATA_CHORE_NAME),
                    "kid": self.kids_data[kid_id][const.DATA_KID_NAME],
                },
            )

        if kid_id not in self.kids_data:
            const.LOGGER.warning("Kid ID '%s' not found", kid_id)
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_KID,
                    "name": kid_id,
                },
            )

        kid_info = self.kids_data[kid_id]

        self._normalize_kid_reward_data(kid_info)

        # Phase 4: Use timestamp-based helpers instead of deprecated lists
        # This checks: completed_by_other, pending_claim, already_approved
        can_claim, error_key = self._can_claim_chore(kid_id, chore_id)
        if not can_claim:
            chore_name = chore_info[const.DATA_CHORE_NAME]
            const.LOGGER.warning(
                "WARNING: Claim Chore - Chore '%s' cannot be claimed by kid '%s': %s",
                chore_name,
                kid_info.get(const.DATA_KID_NAME),
                error_key,
            )

            # Determine the appropriate error message based on the error key
            if error_key == const.TRANS_KEY_ERROR_CHORE_COMPLETED_BY_OTHER:
                # Get the name of who completed the chore
                kid_chore_data = self._get_kid_chore_data(kid_id, chore_id)
                claimed_by = kid_chore_data.get(
                    const.DATA_CHORE_CLAIMED_BY, "another kid"
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_CHORE_CLAIMED_BY_OTHER,
                    translation_placeholders={"claimed_by": claimed_by},
                )
            if error_key == const.TRANS_KEY_ERROR_CHORE_PENDING_CLAIM:
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_CHORE_PENDING_CLAIM,
                    translation_placeholders={"entity": chore_name},
                )
            # else: TRANS_KEY_ERROR_CHORE_ALREADY_APPROVED
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_ALREADY_CLAIMED,
                translation_placeholders={"entity": chore_name},
            )

        # Increment pending_count counter BEFORE _process_chore_state so has_pending_claim()
        # returns the correct value during global state computation (v0.4.0+ counter-based tracking)
        # Use _update_chore_data_for_kid to ensure proper initialization
        chore_info = self.chores_data[chore_id]
        chore_name = chore_info.get(const.DATA_CHORE_NAME, chore_id)
        self._update_chore_data_for_kid(kid_id, chore_id, 0.0)  # Initialize properly
        kid_chores_data = kid_info.setdefault(const.DATA_KID_CHORE_DATA, {})
        kid_chore_data_entry = kid_chores_data[chore_id]  # Now guaranteed to exist
        current_count = kid_chore_data_entry.get(
            const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT, 0
        )
        kid_chore_data_entry[const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT] = (
            current_count + 1
        )

        self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_CLAIMED)

        # SHARED_FIRST: Set all other assigned kids to completed_by_other
        completion_criteria = chore_info.get(
            const.DATA_CHORE_COMPLETION_CRITERIA, const.SENTINEL_EMPTY
        )
        if completion_criteria == const.COMPLETION_CRITERIA_SHARED_FIRST:
            claiming_kid_name = kid_info.get(const.DATA_KID_NAME, "Unknown")
            for other_kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                if other_kid_id == kid_id:
                    continue  # Skip the claiming kid
                # Set other kids to completed_by_other state using _process_chore_state
                # This properly updates their lists and recomputes global state
                self._process_chore_state(
                    other_kid_id, chore_id, const.CHORE_STATE_COMPLETED_BY_OTHER
                )
                # Store who claimed it for display purposes
                other_kid_info = self.kids_data.get(other_kid_id, {})
                # Ensure proper initialization of chore data
                self._update_chore_data_for_kid(other_kid_id, chore_id, 0.0)
                chore_data = other_kid_info.setdefault(const.DATA_KID_CHORE_DATA, {})
                chore_entry = chore_data[chore_id]  # Now guaranteed to exist
                chore_entry[const.DATA_CHORE_CLAIMED_BY] = claiming_kid_name
                const.LOGGER.debug(
                    "SHARED_FIRST: Set kid '%s' to completed_by_other for chore '%s' (claimed by '%s')",
                    other_kid_info.get(const.DATA_KID_NAME),
                    chore_info.get(const.DATA_CHORE_NAME),
                    claiming_kid_name,
                )

        # Check if auto_approve is enabled for this chore
        auto_approve = chore_info.get(
            const.DATA_CHORE_AUTO_APPROVE, const.DEFAULT_CHORE_AUTO_APPROVE
        )

        if auto_approve:
            # Auto-approve the chore immediately
            self.approve_chore("auto_approve", kid_id, chore_id)
        else:
            # Send a notification to the parents that a kid claimed a chore (awaiting approval)
            if chore_info.get(
                const.DATA_CHORE_NOTIFY_ON_CLAIM, const.DEFAULT_NOTIFY_ON_CLAIM
            ):
                actions = [
                    {
                        const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_CHORE}|{kid_id}|{chore_id}",
                        const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_APPROVE,
                    },
                    {
                        const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_CHORE}|{kid_id}|{chore_id}",
                        const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_DISAPPROVE,
                    },
                    {
                        const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{chore_id}",
                        const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_REMIND_30,
                    },
                ]
                # Pass extra context so the event handler can route the action.
                extra_data = {
                    const.DATA_KID_ID: kid_id,
                    const.DATA_CHORE_ID: chore_id,
                }
                self.hass.async_create_task(
                    self._notify_parents_translated(
                        kid_id,
                        title_key=const.TRANS_KEY_NOTIF_TITLE_CHORE_CLAIMED,
                        message_key=const.TRANS_KEY_NOTIF_MESSAGE_CHORE_CLAIMED,
                        message_data={
                            "kid_name": self.kids_data[kid_id][const.DATA_KID_NAME],
                            "chore_name": self.chores_data[chore_id][
                                const.DATA_CHORE_NAME
                            ],
                        },
                        actions=actions,
                        extra_data=extra_data,
                    )
                )

        self._persist()
        self.async_set_updated_data(self._data)

        perf_duration = time.perf_counter() - perf_start
        const.LOGGER.debug(
            "PERF: claim_chore() took %.3fs for kid '%s' chore '%s'",
            perf_duration,
            kid_id,
            chore_id,
        )

    # pylint: disable=too-many-locals,too-many-branches,unused-argument
    def approve_chore(
        self,
        parent_name: str,  # Reserved for future feature
        kid_id: str,
        chore_id: str,
        points_awarded: Optional[float] = None,  # Reserved for future feature
    ):
        """Approve a chore for kid_id if assigned."""
        perf_start = time.perf_counter()
        if chore_id not in self.chores_data:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_CHORE,
                    "name": chore_id,
                },
            )

        chore_info = self.chores_data[chore_id]
        if kid_id not in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_ASSIGNED,
                translation_placeholders={
                    "entity": chore_info.get(const.DATA_CHORE_NAME),
                    "kid": self.kids_data[kid_id][const.DATA_KID_NAME],
                },
            )

        if kid_id not in self.kids_data:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_KID,
                    "name": kid_id,
                },
            )

        kid_info = self.kids_data[kid_id]

        # Phase 4: Use timestamp-based helpers instead of deprecated lists
        # This checks: completed_by_other, already_approved
        can_approve, error_key = self._can_approve_chore(kid_id, chore_id)
        if not can_approve:
            chore_name = chore_info[const.DATA_CHORE_NAME]
            const.LOGGER.warning(
                "Approve Chore: Cannot approve '%s' for kid '%s': %s",
                chore_name,
                kid_info[const.DATA_KID_NAME],
                error_key,
            )
            # Determine the appropriate error message based on the error key
            if error_key == const.TRANS_KEY_ERROR_CHORE_COMPLETED_BY_OTHER:
                kid_chore_data = self._get_kid_chore_data(kid_id, chore_id)
                claimed_by = kid_chore_data.get(
                    const.DATA_CHORE_CLAIMED_BY, "another kid"
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_CHORE_COMPLETED_BY_OTHER,
                    translation_placeholders={
                        "chore_name": chore_name,
                        "claimed_by": claimed_by,
                    },
                )
            # else: TRANS_KEY_ERROR_CHORE_ALREADY_APPROVED
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_CHORE_ALREADY_APPROVED,
            )

        default_points = chore_info.get(
            const.DATA_CHORE_DEFAULT_POINTS, const.DEFAULT_POINTS
        )

        # Note - multiplier will be added in the _update_kid_points method called from _process_chore_state
        self._process_chore_state(
            kid_id, chore_id, const.CHORE_STATE_APPROVED, points_awarded=default_points
        )

        # Decrement pending_count counter after approval (v0.4.0+ counter-based tracking)
        kid_chores_data = kid_info.setdefault(const.DATA_KID_CHORE_DATA, {})
        # Use get() to avoid overwriting existing data that _process_chore_state just created
        kid_chore_data_entry = kid_chores_data[
            chore_id
        ]  # Should exist from _process_chore_state
        current_count = kid_chore_data_entry.get(
            const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT, 0
        )
        kid_chore_data_entry[const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT] = max(
            0, current_count - 1
        )

        # SHARED_FIRST: Update completed_by for other kids (they remain in completed_by_other state)
        completion_criteria = chore_info.get(
            const.DATA_CHORE_COMPLETION_CRITERIA, const.SENTINEL_EMPTY
        )
        if completion_criteria == const.COMPLETION_CRITERIA_SHARED_FIRST:
            completing_kid_name = kid_info.get(const.DATA_KID_NAME, "Unknown")
            for other_kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                if other_kid_id == kid_id:
                    continue  # Skip the completing kid
                # Update the completed_by attribute
                other_kid_info = self.kids_data.get(other_kid_id, {})
                chore_data = other_kid_info.setdefault(const.DATA_KID_CHORE_DATA, {})
                # Ensure proper chore data initialization
                if chore_id not in chore_data:
                    self._update_chore_data_for_kid(other_kid_id, chore_id, 0.0)
                chore_entry = chore_data[chore_id]
                chore_entry[const.DATA_CHORE_COMPLETED_BY] = completing_kid_name
                const.LOGGER.debug(
                    "SHARED_FIRST: Updated completed_by='%s' for kid '%s' on chore '%s'",
                    completing_kid_name,
                    other_kid_info.get(const.DATA_KID_NAME),
                    chore_info.get(const.DATA_CHORE_NAME),
                )

        # Manage Achievements
        today_local = kh.get_today_local_date()
        for _, achievement_info in self.achievements_data.items():
            if (
                achievement_info.get(const.DATA_ACHIEVEMENT_TYPE)
                == const.ACHIEVEMENT_TYPE_STREAK
            ):
                selected_chore_id = achievement_info.get(
                    const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID
                )
                if selected_chore_id == chore_id:
                    # Get or create the progress dict for this kid
                    progress = achievement_info.setdefault(
                        const.DATA_ACHIEVEMENT_PROGRESS, {}
                    ).setdefault(
                        kid_id,
                        {
                            const.DATA_KID_CURRENT_STREAK: const.DEFAULT_ZERO,
                            const.DATA_KID_LAST_STREAK_DATE: None,
                            const.DATA_ACHIEVEMENT_AWARDED: False,
                        },
                    )
                    self._update_streak_progress(progress, today_local)

        # Manage Challenges
        today_local_iso = kh.get_today_local_iso()
        for _, challenge_info in self.challenges_data.items():
            challenge_type = challenge_info.get(const.DATA_CHALLENGE_TYPE)

            if challenge_type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                selected_chore = challenge_info.get(
                    const.DATA_CHALLENGE_SELECTED_CHORE_ID
                )
                if selected_chore and selected_chore != chore_id:
                    continue

                start_date_utc = kh.parse_datetime_to_utc(
                    challenge_info.get(const.DATA_CHALLENGE_START_DATE)
                )

                end_date_utc = kh.parse_datetime_to_utc(
                    challenge_info.get(const.DATA_CHALLENGE_END_DATE)
                )

                now_utc = dt_util.utcnow()

                if (
                    start_date_utc
                    and end_date_utc
                    and start_date_utc <= now_utc <= end_date_utc
                ):
                    progress = challenge_info.setdefault(
                        const.DATA_CHALLENGE_PROGRESS, {}
                    ).setdefault(
                        kid_id,
                        {
                            const.DATA_CHALLENGE_COUNT: const.DEFAULT_ZERO,
                            const.DATA_CHALLENGE_AWARDED: False,
                        },
                    )
                    progress[const.DATA_CHALLENGE_COUNT] += 1

            elif challenge_type == const.CHALLENGE_TYPE_DAILY_MIN:
                selected_chore = challenge_info.get(
                    const.DATA_CHALLENGE_SELECTED_CHORE_ID
                )
                if not selected_chore:
                    const.LOGGER.warning(
                        "WARNING: Challenge '%s' of type daily minimum has no selected chore id. Skipping progress update.",
                        challenge_info.get(const.DATA_CHALLENGE_NAME),
                    )
                    continue

                if selected_chore != chore_id:
                    continue

                if kid_id in challenge_info.get(const.DATA_CHALLENGE_ASSIGNED_KIDS, []):
                    progress = challenge_info.setdefault(
                        const.DATA_CHALLENGE_PROGRESS, {}
                    ).setdefault(
                        kid_id,
                        {
                            const.DATA_CHALLENGE_DAILY_COUNTS: {},
                            const.DATA_CHALLENGE_AWARDED: False,
                        },
                    )
                    progress[const.DATA_CHALLENGE_DAILY_COUNTS][today_local_iso] = (
                        progress[const.DATA_CHALLENGE_DAILY_COUNTS].get(
                            today_local_iso, const.DEFAULT_ZERO
                        )
                        + 1
                    )

        # For INDEPENDENT chores, reschedule per-kid due date after approval
        if (
            chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
            == const.COMPLETION_CRITERIA_INDEPENDENT
        ):
            self._reschedule_chore_next_due_date_for_kid(chore_info, chore_id, kid_id)

        # Send a notification to the kid that chore was approved
        if chore_info.get(
            const.DATA_CHORE_NOTIFY_ON_APPROVAL, const.DEFAULT_NOTIFY_ON_APPROVAL
        ):
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHORE_ID: chore_id}
            self.hass.async_create_task(
                self._notify_kid_translated(
                    kid_id,
                    title_key=const.TRANS_KEY_NOTIF_TITLE_CHORE_APPROVED,
                    message_key=const.TRANS_KEY_NOTIF_MESSAGE_CHORE_APPROVED,
                    message_data={
                        "chore_name": chore_info[const.DATA_CHORE_NAME],
                        "points": default_points,
                    },
                    extra_data=extra_data,
                )
            )

        self._persist()
        self.async_set_updated_data(self._data)

        perf_duration = time.perf_counter() - perf_start
        const.LOGGER.debug(
            "PERF: approve_chore() took %.3fs for kid '%s' chore '%s' (includes %.1f points addition)",
            perf_duration,
            kid_id,
            chore_id,
            default_points,
        )

    def disapprove_chore(self, parent_name: str, kid_id: str, chore_id: str):  # pylint: disable=unused-argument
        """Disapprove a chore for kid_id."""
        chore_info = self.chores_data.get(chore_id)
        if not chore_info:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_CHORE,
                    "name": chore_id,
                },
            )

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_KID,
                    "name": kid_id,
                },
            )

        # Decrement pending_count for the claimant ONLY (v0.4.0+ counter-based tracking)
        # This happens regardless of completion criteria - only the kid who claimed is affected
        kid_chores_data = kid_info.setdefault(const.DATA_KID_CHORE_DATA, {})
        # Ensure proper chore data initialization
        if chore_id not in kid_chores_data:
            self._update_chore_data_for_kid(kid_id, chore_id, 0.0)
        kid_chore_data_entry = kid_chores_data[chore_id]
        current_count = kid_chore_data_entry.get(
            const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT, 0
        )
        kid_chore_data_entry[const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT] = max(
            0, current_count - 1
        )

        # SHARED_FIRST: Reset ALL kids to pending (everyone gets another chance)
        completion_criteria = chore_info.get(
            const.DATA_CHORE_COMPLETION_CRITERIA, const.SENTINEL_EMPTY
        )
        if completion_criteria == const.COMPLETION_CRITERIA_SHARED_FIRST:
            const.LOGGER.info(
                "SHARED_FIRST: Disapproval - resetting all kids to pending for chore '%s'",
                chore_info.get(const.DATA_CHORE_NAME),
            )
            for other_kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                self._process_chore_state(
                    other_kid_id, chore_id, const.CHORE_STATE_PENDING
                )
                # Clear claimed_by/completed_by attributes
                other_kid_info = self.kids_data.get(other_kid_id, {})
                chore_data = other_kid_info.get(const.DATA_KID_CHORE_DATA, {})
                if chore_id in chore_data:
                    chore_data[chore_id].pop(const.DATA_CHORE_CLAIMED_BY, None)
                    chore_data[chore_id].pop(const.DATA_CHORE_COMPLETED_BY, None)
        else:
            # Normal behavior: only reset the disapproved kid
            self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)

        # Send a notification to the kid that chore was disapproved
        if chore_info.get(
            const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL, const.DEFAULT_NOTIFY_ON_DISAPPROVAL
        ):
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHORE_ID: chore_id}
            self.hass.async_create_task(
                self._notify_kid_translated(
                    kid_id,
                    title_key=const.TRANS_KEY_NOTIF_TITLE_CHORE_DISAPPROVED,
                    message_key=const.TRANS_KEY_NOTIF_MESSAGE_CHORE_DISAPPROVED,
                    message_data={"chore_name": chore_info[const.DATA_CHORE_NAME]},
                    extra_data=extra_data,
                )
            )

        self._persist()
        self.async_set_updated_data(self._data)

    def update_chore_state(self, chore_id: str, state: str):
        """Manually override a chore's state."""
        chore_info = self.chores_data.get(chore_id)
        if not chore_info:
            const.LOGGER.warning(
                "WARNING: Update Chore State -  Chore ID '%s' not found", chore_id
            )
            return
        # Set state for all kids assigned to the chore:
        for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            if kid_id:
                self._process_chore_state(kid_id, chore_id, state)
        self._persist()
        self.async_set_updated_data(self._data)
        const.LOGGER.debug(
            "DEBUG: Chore ID '%s' manually updated to '%s'", chore_id, state
        )

    # -------------------------------------------------------------------------------------
    # Claim & Approval Eligibility Helpers (Phase 4: Approval Reset Timing)
    # These helpers use timestamp-based logic from kid_chore_data instead of the deprecated
    # deprecated claimed_chores/approved_chores lists (removed v0.4.0). They determine whether a kid can claim or
    # have a chore approved based on:
    # - Whether they have a pending claim (claimed but not yet approved/disapproved)
    # - Whether the chore was already approved in the current approval period
    # - Whether another kid completed the chore (SHARED_FIRST mode: completed_by_other)
    # -------------------------------------------------------------------------------------

    def _get_kid_chore_data(self, kid_id: str, chore_id: str) -> dict[str, Any]:
        """Get the chore data dict for a specific kid+chore combination.

        Returns an empty dict if the kid or chore data doesn't exist.
        """
        kid_info = self.kids_data.get(kid_id, {})
        return kid_info.get(const.DATA_KID_CHORE_DATA, {}).get(chore_id, {})

    def _get_kid_reward_data(
        self, kid_id: str, reward_id: str, create: bool = False
    ) -> dict[str, Any]:
        """Get the reward data dict for a specific kid+reward combination.

        Args:
            kid_id: The kid's internal ID
            reward_id: The reward's internal ID
            create: If True, create the entry if it doesn't exist

        Returns an empty dict if the kid or reward data doesn't exist and create=False.
        """
        kid_info = self.kids_data.get(kid_id, {})
        reward_data = kid_info.setdefault(const.DATA_KID_REWARD_DATA, {})
        if create and reward_id not in reward_data:
            reward_data[reward_id] = {
                const.DATA_KID_REWARD_DATA_NAME: self.rewards_data.get(
                    reward_id, {}
                ).get(const.DATA_REWARD_NAME, ""),
                const.DATA_KID_REWARD_DATA_PENDING_COUNT: 0,
                const.DATA_KID_REWARD_DATA_NOTIFICATION_IDS: [],
                const.DATA_KID_REWARD_DATA_LAST_CLAIMED: None,
                const.DATA_KID_REWARD_DATA_LAST_APPROVED: None,
                const.DATA_KID_REWARD_DATA_LAST_DISAPPROVED: None,
                const.DATA_KID_REWARD_DATA_TOTAL_CLAIMS: 0,
                const.DATA_KID_REWARD_DATA_TOTAL_APPROVED: 0,
                const.DATA_KID_REWARD_DATA_TOTAL_DISAPPROVED: 0,
                const.DATA_KID_REWARD_DATA_TOTAL_POINTS_SPENT: 0,
                const.DATA_KID_REWARD_DATA_PERIODS: {
                    const.DATA_KID_REWARD_DATA_PERIODS_DAILY: {},
                    const.DATA_KID_REWARD_DATA_PERIODS_WEEKLY: {},
                    const.DATA_KID_REWARD_DATA_PERIODS_MONTHLY: {},
                    const.DATA_KID_REWARD_DATA_PERIODS_YEARLY: {},
                },
            }
        return reward_data.get(reward_id, {})

    def _increment_reward_period_counter(
        self,
        reward_entry: dict[str, Any],
        counter_key: str,
        amount: int = 1,
    ) -> None:
        """Increment a period counter for a reward entry across all period buckets.

        Args:
            reward_entry: The reward_data[reward_id] dict
            counter_key: Which counter to increment (claimed/approved/disapproved/points)
            amount: Amount to add (default 1)
        """
        now = dt_util.now()  # Local time for period keys

        # Get period IDs using same format as chore_data and point_data
        daily_key = now.strftime("%Y-%m-%d")
        weekly_key = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
        monthly_key = now.strftime("%Y-%m")
        yearly_key = now.strftime("%Y")

        # Ensure periods structure exists
        periods = reward_entry.setdefault(
            const.DATA_KID_REWARD_DATA_PERIODS,
            {
                const.DATA_KID_REWARD_DATA_PERIODS_DAILY: {},
                const.DATA_KID_REWARD_DATA_PERIODS_WEEKLY: {},
                const.DATA_KID_REWARD_DATA_PERIODS_MONTHLY: {},
                const.DATA_KID_REWARD_DATA_PERIODS_YEARLY: {},
            },
        )

        # Helper to get or create period entry with all counters
        def _get_period_entry(bucket: dict, period_id: str) -> dict:
            if period_id not in bucket:
                bucket[period_id] = {
                    const.DATA_KID_REWARD_DATA_PERIOD_CLAIMED: 0,
                    const.DATA_KID_REWARD_DATA_PERIOD_APPROVED: 0,
                    const.DATA_KID_REWARD_DATA_PERIOD_DISAPPROVED: 0,
                    const.DATA_KID_REWARD_DATA_PERIOD_POINTS: 0,
                }
            return bucket[period_id]

        # Increment counter in each period bucket
        daily = periods.setdefault(const.DATA_KID_REWARD_DATA_PERIODS_DAILY, {})
        _get_period_entry(daily, daily_key)[counter_key] = (
            _get_period_entry(daily, daily_key).get(counter_key, 0) + amount
        )

        weekly = periods.setdefault(const.DATA_KID_REWARD_DATA_PERIODS_WEEKLY, {})
        _get_period_entry(weekly, weekly_key)[counter_key] = (
            _get_period_entry(weekly, weekly_key).get(counter_key, 0) + amount
        )

        monthly = periods.setdefault(const.DATA_KID_REWARD_DATA_PERIODS_MONTHLY, {})
        _get_period_entry(monthly, monthly_key)[counter_key] = (
            _get_period_entry(monthly, monthly_key).get(counter_key, 0) + amount
        )

        yearly = periods.setdefault(const.DATA_KID_REWARD_DATA_PERIODS_YEARLY, {})
        _get_period_entry(yearly, yearly_key)[counter_key] = (
            _get_period_entry(yearly, yearly_key).get(counter_key, 0) + amount
        )

    def has_pending_claim(self, kid_id: str, chore_id: str) -> bool:
        """Check if a chore has a pending claim (claimed but not yet approved/disapproved).

        Uses the pending_count counter which is incremented on claim and
        decremented on approve/disapprove.

        Returns:
            True if there's a pending claim (pending_claim_count > 0), False otherwise.
        """
        kid_chore_data = self._get_kid_chore_data(kid_id, chore_id)
        if not kid_chore_data:
            return False

        pending_claim_count = kid_chore_data.get(
            const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT, 0
        )
        return pending_claim_count > 0

    def get_pending_chore_approvals_computed(self) -> list[dict[str, Any]]:
        """Compute pending chore approvals dynamically from timestamp data.

        This replaces the legacy queue-based approach with dynamic computation
        from kid_chore_data timestamps. A chore has a pending approval if:
        - last_claimed timestamp exists AND
        - last_claimed > last_approved (or no approval) AND
        - last_claimed > last_disapproved (or no disapproval)

        Returns:
            List of dicts with keys: kid_id, chore_id, timestamp
            Format matches the legacy queue structure for compatibility.
        """
        pending: list[dict[str, Any]] = []
        for kid_id, kid_info in self.kids_data.items():
            chore_data = kid_info.get(const.DATA_KID_CHORE_DATA, {})
            for chore_id, chore_entry in chore_data.items():
                # Skip chores that no longer exist
                if chore_id not in self.chores_data:
                    continue
                if self.has_pending_claim(kid_id, chore_id):
                    pending.append(
                        {
                            const.DATA_KID_ID: kid_id,
                            const.DATA_CHORE_ID: chore_id,
                            const.DATA_CHORE_TIMESTAMP: chore_entry.get(
                                const.DATA_KID_CHORE_DATA_LAST_CLAIMED, ""
                            ),
                        }
                    )
        return pending

    def get_pending_reward_approvals_computed(self) -> list[dict[str, Any]]:
        """Compute pending reward approvals dynamically from kid_reward_data.

        Unlike chores (which allow only one pending claim at a time), rewards
        support multiple pending claims via the pending_count field.

        Returns:
            List of dicts with keys: kid_id, reward_id, pending_count, timestamp
            One entry per kid+reward combination with pending_count > 0.
        """
        pending: list[dict[str, Any]] = []
        for kid_id, kid_info in self.kids_data.items():
            reward_data = kid_info.get(const.DATA_KID_REWARD_DATA, {})
            for reward_id, entry in reward_data.items():
                # Skip rewards that no longer exist
                if reward_id not in self.rewards_data:
                    continue
                pending_count = entry.get(const.DATA_KID_REWARD_DATA_PENDING_COUNT, 0)
                if pending_count > 0:
                    pending.append(
                        {
                            const.DATA_KID_ID: kid_id,
                            const.DATA_REWARD_ID: reward_id,
                            "pending_count": pending_count,
                            const.DATA_REWARD_TIMESTAMP: entry.get(
                                const.DATA_KID_REWARD_DATA_LAST_CLAIMED, ""
                            ),
                        }
                    )
        return pending

    def _get_approval_period_start(self, kid_id: str, chore_id: str) -> str | None:
        """Get the start of the current approval period for this kid+chore.

        For SHARED chores: Uses chore-level approval_period_start
        For INDEPENDENT chores: Uses per-kid approval_period_start in kid_chore_data

        Returns:
            ISO timestamp string of period start, or None if not set.
        """
        chore_info = self.chores_data.get(chore_id)
        if not chore_info:
            return None

        # Default to INDEPENDENT if completion_criteria not set (backward compatibility)
        # This ensures pre-migration chores without completion_criteria are treated as INDEPENDENT
        completion_criteria = chore_info.get(
            const.DATA_CHORE_COMPLETION_CRITERIA, const.COMPLETION_CRITERIA_INDEPENDENT
        )

        if completion_criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
            # INDEPENDENT: Period start is per-kid in kid_chore_data
            kid_chore_data = self._get_kid_chore_data(kid_id, chore_id)
            return kid_chore_data.get(const.DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START)
        else:
            # SHARED/SHARED_FIRST/etc.: Period start is at chore level
            return chore_info.get(const.DATA_CHORE_APPROVAL_PERIOD_START)

    def is_approved_in_current_period(self, kid_id: str, chore_id: str) -> bool:
        """Check if a chore is already approved in the current approval period.

        A chore is considered approved in the current period if:
        - last_approved timestamp exists, AND EITHER:
          a. approval_period_start doesn't exist (chore was never reset, approval is valid), OR
          b. last_approved >= approval_period_start

        Returns:
            True if approved in current period, False otherwise.
        """
        kid_chore_data = self._get_kid_chore_data(kid_id, chore_id)
        if not kid_chore_data:
            return False

        last_approved = kid_chore_data.get(const.DATA_KID_CHORE_DATA_LAST_APPROVED)
        if not last_approved:
            return False

        period_start = self._get_approval_period_start(kid_id, chore_id)
        if not period_start:
            # No period_start means chore was never reset after being created.
            # Since last_approved exists (checked above), the approval is still valid.
            return True

        approved_dt = kh.parse_datetime_to_utc(last_approved)
        period_start_dt = kh.parse_datetime_to_utc(period_start)

        if approved_dt is None or period_start_dt is None:
            return False

        return approved_dt >= period_start_dt

    def _can_claim_chore(self, kid_id: str, chore_id: str) -> tuple[bool, str | None]:
        """Check if a kid can claim a specific chore.

        This helper is dual-purpose: used for claim validation AND for providing
        status information to the dashboard helper sensor.

        Checks (in order):
        1. completed_by_other - Another kid already completed (SHARED_FIRST mode)
        2. pending_claim - Already has a claim awaiting approval
        3. already_approved - Already approved in current period (if not multi-claim)

        Returns:
            Tuple of (can_claim: bool, error_key: str | None)
            - (True, None) if claim is allowed
            - (False, translation_key) if claim is blocked
        """
        # Get current state for this kid+chore
        kid_chore_data = self._get_kid_chore_data(kid_id, chore_id)
        current_state = kid_chore_data.get(
            const.DATA_KID_CHORE_DATA_STATE, const.CHORE_STATE_PENDING
        )

        # Check 1: completed_by_other blocks all claims
        if current_state == const.CHORE_STATE_COMPLETED_BY_OTHER:
            return (False, const.TRANS_KEY_ERROR_CHORE_COMPLETED_BY_OTHER)

        # Determine if this is a multi-claim mode (needed for checks 2 and 3)
        chore_info = self.chores_data.get(chore_id, {})
        approval_reset_type = chore_info.get(
            const.DATA_CHORE_APPROVAL_RESET_TYPE,
            const.APPROVAL_RESET_AT_MIDNIGHT_ONCE,  # Fixed: was _SINGLE
        )
        allow_multiple_claims = approval_reset_type in (
            const.APPROVAL_RESET_AT_MIDNIGHT_MULTI,
            const.APPROVAL_RESET_AT_DUE_DATE_MULTI,
            const.APPROVAL_RESET_UPON_COMPLETION,
        )

        # Check 2: pending claim blocks new claims (unless multi-claim allowed)
        # For MULTI modes, re-claiming is allowed even with a pending claim
        if not allow_multiple_claims and self.has_pending_claim(kid_id, chore_id):
            return (False, const.TRANS_KEY_ERROR_CHORE_PENDING_CLAIM)

        # Check 3: already approved in current period (unless multi-claim allowed)
        if not allow_multiple_claims and self.is_approved_in_current_period(
            kid_id, chore_id
        ):
            return (False, const.TRANS_KEY_ERROR_CHORE_ALREADY_APPROVED)

        return (True, None)

    def _can_approve_chore(self, kid_id: str, chore_id: str) -> tuple[bool, str | None]:
        """Check if a chore can be approved for a specific kid.

        This helper is dual-purpose: used for approval validation AND for providing
        status information to the dashboard helper sensor.

        Checks (in order):
        1. completed_by_other - Another kid already completed (SHARED_FIRST mode)
        2. already_approved - Already approved in current period (if not multi-claim)

        Note: Unlike _can_claim_chore, this does NOT check for pending claims because
        we're checking if approval is possible, not if a new claim can be made.

        Returns:
            Tuple of (can_approve: bool, error_key: str | None)
            - (True, None) if approval is allowed
            - (False, translation_key) if approval is blocked
        """
        # Get current state for this kid+chore
        kid_chore_data = self._get_kid_chore_data(kid_id, chore_id)
        current_state = kid_chore_data.get(
            const.DATA_KID_CHORE_DATA_STATE, const.CHORE_STATE_PENDING
        )

        # Check 1: completed_by_other blocks all approvals
        if current_state == const.CHORE_STATE_COMPLETED_BY_OTHER:
            return (False, const.TRANS_KEY_ERROR_CHORE_COMPLETED_BY_OTHER)

        # Check 2: already approved in current period (unless multi-claim allowed)
        chore_info = self.chores_data.get(chore_id, {})
        approval_reset_type = chore_info.get(
            const.DATA_CHORE_APPROVAL_RESET_TYPE,
            const.APPROVAL_RESET_AT_MIDNIGHT_ONCE,  # Fixed: was _SINGLE
        )
        allow_multiple_claims = approval_reset_type in (
            const.APPROVAL_RESET_AT_MIDNIGHT_MULTI,
            const.APPROVAL_RESET_AT_DUE_DATE_MULTI,
            const.APPROVAL_RESET_UPON_COMPLETION,
        )

        if not allow_multiple_claims and self.is_approved_in_current_period(
            kid_id, chore_id
        ):
            return (False, const.TRANS_KEY_ERROR_CHORE_ALREADY_APPROVED)

        return (True, None)

    # -------------------------------------------------------------------------------------
    # Chore State Processing: Centralized Function
    # The most critical thing to understand when working on this function is that
    # chore_info[const.DATA_CHORE_STATE] is actually the global state of the chore. The individual chore
    # state per kid is always calculated based on whether they have any claimed, approved, or
    # overdue chores listed for them.
    #
    # Global state will only match if a single kid is assigned to the chore, or all kids
    # assigned are in the same state.
    # -------------------------------------------------------------------------------------

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    def _process_chore_state(
        self,
        kid_id: str,
        chore_id: str,
        new_state: str,
        *,
        points_awarded: Optional[float] = None,
    ) -> None:
        """Centralized function to update a chore’s state for a given kid."""

        # Add a flag to control debug messages
        debug_enabled = False

        if debug_enabled:
            const.LOGGER.debug(
                "DEBUG: Chore State - Processing - Kid ID '%s', Chore ID '%s', State '%s', Points Awarded '%s'",
                kid_id,
                chore_id,
                new_state,
                points_awarded,
            )

        kid_info = self.kids_data.get(kid_id)
        chore_info = self.chores_data.get(chore_id)

        if not kid_info or not chore_info:
            const.LOGGER.warning(
                "WARNING: Chore State - Change skipped. Kid ID '%s' or Chore ID '%s' not found",
                kid_id,
                chore_id,
            )
            return

        # Update kid chore tracking data
        # Pass 0 for points_awarded if None and not in APPROVED state
        actual_points = points_awarded if points_awarded is not None else 0.0

        # Get due date to pass to kid chore data
        # For INDEPENDENT chores, use per-kid due date; for SHARED, use chore-level
        completion_criteria = chore_info.get(
            const.DATA_CHORE_COMPLETION_CRITERIA, const.SENTINEL_EMPTY
        )
        if completion_criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
            per_kid_due_dates = chore_info.get(const.DATA_CHORE_PER_KID_DUE_DATES, {})
            due_date = per_kid_due_dates.get(kid_id)
        else:
            due_date = chore_info.get(const.DATA_CHORE_DUE_DATE)

        # Update the kid's chore history
        self._update_chore_data_for_kid(
            kid_id=kid_id,
            chore_id=chore_id,
            points_awarded=actual_points,
            state=new_state,
            due_date=due_date,
        )

        # Clear any overdue tracking.
        kid_info.setdefault(const.DATA_KID_OVERDUE_CHORES, [])
        # kid_info.setdefault(const.DATA_KID_OVERDUE_NOTIFICATIONS, {})

        # Remove all instances of the chore from overdue lists.
        kid_info[const.DATA_KID_OVERDUE_CHORES] = [
            entry
            for entry in kid_info.get(const.DATA_KID_OVERDUE_CHORES, [])
            if entry != chore_id
        ]

        # Clear any overdue tracking *only* when not processing an overdue state.
        if new_state != const.CHORE_STATE_OVERDUE:
            kid_info.setdefault(const.DATA_KID_OVERDUE_NOTIFICATIONS, {})
            if chore_id in kid_info[const.DATA_KID_OVERDUE_NOTIFICATIONS]:
                kid_info[const.DATA_KID_OVERDUE_NOTIFICATIONS].pop(chore_id)

        if new_state == const.CHORE_STATE_CLAIMED:
            # Update kid_chore_data with claim timestamp (v0.4.0+ timestamp-based tracking)
            now_iso = dt_util.utcnow().isoformat()
            # Use _update_chore_data_for_kid to ensure proper initialization
            self._update_chore_data_for_kid(
                kid_id, chore_id, 0.0
            )  # No points awarded for claim
            kid_chores_data = kid_info.setdefault(const.DATA_KID_CHORE_DATA, {})
            kid_chore_data_entry = kid_chores_data[
                chore_id
            ]  # Now guaranteed to exist and be properly initialized
            kid_chore_data_entry[const.DATA_KID_CHORE_DATA_LAST_CLAIMED] = now_iso

            chore_info[const.DATA_CHORE_LAST_CLAIMED] = now_iso
            # Queue write removed - pending approvals now computed from timestamps
            self._pending_chore_changed = True

        elif new_state == const.CHORE_STATE_APPROVED:
            # Update kid_chore_data with approval timestamp (v0.4.0+ timestamp-based tracking)
            now_iso = dt_util.utcnow().isoformat()
            # Use _update_chore_data_for_kid to ensure proper initialization
            self._update_chore_data_for_kid(kid_id, chore_id, points_awarded or 0.0)
            kid_chores_data = kid_info.setdefault(const.DATA_KID_CHORE_DATA, {})
            kid_chore_data_entry = kid_chores_data[
                chore_id
            ]  # Now guaranteed to exist and be properly initialized
            kid_chore_data_entry[const.DATA_KID_CHORE_DATA_LAST_APPROVED] = now_iso
            # NOTE: last_claimed is intentionally preserved after approval
            # to maintain consistent behavior with other last_* fields

            chore_info[const.DATA_CHORE_LAST_COMPLETED] = now_iso

            if points_awarded is not None:
                self.update_kid_points(
                    kid_id, delta=points_awarded, source=const.POINTS_SOURCE_CHORES
                )
            # Queue filter removed - pending approvals now computed from timestamps
            self._pending_chore_changed = True

        elif new_state == const.CHORE_STATE_PENDING:
            # Remove the chore from claimed, approved, and completed_by_other lists.
            # Clear from completed_by_other list
            kid_info[const.DATA_KID_COMPLETED_BY_OTHER_CHORES] = [
                c
                for c in kid_info.get(const.DATA_KID_COMPLETED_BY_OTHER_CHORES, [])
                if c != chore_id
            ]

            # NOTE: last_approved is intentionally NEVER removed - it's for historical
            # tracking. Period-based approval validation uses approval_period_start
            # to determine if approval is valid for the current period.
            # is_approved_in_current_period() checks: last_approved >= approval_period_start

            kid_chores_data = kid_info.setdefault(const.DATA_KID_CHORE_DATA, {})

            # Set approval_period_start to mark the beginning of a new approval period
            # This timestamp is used to determine if a chore was already approved
            # in the current period (Phase 4: Approval Reset Timing)
            now_iso = dt_util.utcnow().isoformat()
            if completion_criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
                # INDEPENDENT: Store per-kid approval_period_start in kid_chore_data
                # Ensure proper chore data initialization
                if chore_id not in kid_chores_data:
                    self._update_chore_data_for_kid(kid_id, chore_id, 0.0)
                kid_chore_data_entry = kid_chores_data[chore_id]
                kid_chore_data_entry[
                    const.DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START
                ] = now_iso
            else:
                # SHARED/SHARED_FIRST: Store at chore level
                chore_info[const.DATA_CHORE_APPROVAL_PERIOD_START] = now_iso
            # Queue filter removed - pending approvals now computed from timestamps
            self._pending_chore_changed = True

        elif new_state == const.CHORE_STATE_OVERDUE:
            # Mark as overdue.
            kid_info.setdefault(const.DATA_KID_OVERDUE_CHORES, [])

            if chore_id not in kid_info[const.DATA_KID_OVERDUE_CHORES]:
                kid_info[const.DATA_KID_OVERDUE_CHORES].append(chore_id)

        elif new_state == const.CHORE_STATE_COMPLETED_BY_OTHER:
            # SHARED_FIRST: This kid didn't complete the chore, another kid did
            # Clear last_claimed in kid_chore_data (v0.4.0+ timestamp-based tracking)
            # NOTE: last_approved is intentionally NEVER removed - historical tracking
            kid_chores_data = kid_info.setdefault(const.DATA_KID_CHORE_DATA, {})
            if chore_id in kid_chores_data:
                kid_chores_data[chore_id].pop(
                    const.DATA_KID_CHORE_DATA_LAST_CLAIMED, None
                )

            # Also clear from overdue since it's been completed by someone else
            kid_info[const.DATA_KID_OVERDUE_CHORES] = [
                c
                for c in kid_info.get(const.DATA_KID_OVERDUE_CHORES, [])
                if c != chore_id
            ]
            # Add to completed_by_other list to track this state
            kid_info.setdefault(const.DATA_KID_COMPLETED_BY_OTHER_CHORES, [])
            if chore_id not in kid_info[const.DATA_KID_COMPLETED_BY_OTHER_CHORES]:
                kid_info[const.DATA_KID_COMPLETED_BY_OTHER_CHORES].append(chore_id)

        # Compute and update the chore's global state.
        # Given the process above is handling everything properly for each kid, computing the global state straightforward.
        # This process needs run every time a chore state changes, so it no longer warrants a separate function.
        assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        completion_criteria = chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)

        if len(assigned_kids) == 1:
            # if only one kid is assigned to the chore, update the chore state to new state 1:1
            chore_info[const.DATA_CHORE_STATE] = new_state
        elif len(assigned_kids) > 1:
            # For chores assigned to multiple kids, you have to figure out the global state
            count_pending = count_claimed = count_approved = count_overdue = (
                const.DEFAULT_ZERO
            )
            count_completed_by_other = const.DEFAULT_ZERO
            for kid_id_iter in assigned_kids:
                kid_info_iter = self.kids_data.get(kid_id_iter, {})

                # For SHARED_FIRST: claims always win over overdue
                # Once someone claims, they're "claimed", others are "completed_by_other"
                # Overdue only applies when NO ONE has claimed yet
                if completion_criteria == const.COMPLETION_CRITERIA_SHARED_FIRST:
                    if self.is_approved_in_current_period(kid_id_iter, chore_id):
                        count_approved += 1
                    elif self.has_pending_claim(kid_id_iter, chore_id):
                        count_claimed += 1
                    elif chore_id in kid_info_iter.get(
                        const.DATA_KID_COMPLETED_BY_OTHER_CHORES, []
                    ):
                        count_completed_by_other += 1
                    elif chore_id in kid_info_iter.get(
                        const.DATA_KID_OVERDUE_CHORES, []
                    ):
                        count_overdue += 1
                    else:
                        count_pending += 1
                else:
                    # For non-SHARED_FIRST: original priority (overdue checked first)
                    if chore_id in kid_info_iter.get(const.DATA_KID_OVERDUE_CHORES, []):
                        count_overdue += 1
                    elif self.is_approved_in_current_period(kid_id_iter, chore_id):
                        count_approved += 1
                    elif self.has_pending_claim(kid_id_iter, chore_id):
                        count_claimed += 1
                    elif chore_id in kid_info_iter.get(
                        const.DATA_KID_COMPLETED_BY_OTHER_CHORES, []
                    ):
                        count_completed_by_other += 1
                    else:
                        count_pending += 1
            total = len(assigned_kids)

            # If all kids are in the same state, update the chore state to new state 1:1
            if (
                count_pending == total
                or count_claimed == total
                or count_approved == total
                or count_overdue == total
            ):
                chore_info[const.DATA_CHORE_STATE] = new_state

            # For SHARED_FIRST chores, global state follows the single claimant's state
            # Other kids are in completed_by_other state but don't affect progression
            elif (
                chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
                == const.COMPLETION_CRITERIA_SHARED_FIRST
            ):
                # SHARED_FIRST: global state tracks the claimant's progression
                # Once any kid claims/approves, their state drives the global state
                # Other kids' states (pending/overdue/completed_by_other) don't affect it
                if count_approved > const.DEFAULT_ZERO:
                    # Someone completed it - chore is done
                    chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_APPROVED
                elif count_claimed > const.DEFAULT_ZERO:
                    # Someone claimed it - waiting for approval
                    chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_CLAIMED
                elif count_overdue > const.DEFAULT_ZERO:
                    # No one claimed yet, chore is overdue
                    chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_OVERDUE
                else:
                    # No one claimed yet, chore is pending
                    chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_PENDING

            # For shared chores, recompute global state of a partial if they aren't all in the same state as checked above
            elif (
                chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
                == const.COMPLETION_CRITERIA_SHARED
            ):
                if count_overdue > const.DEFAULT_ZERO:
                    chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_OVERDUE
                elif count_approved > const.DEFAULT_ZERO:
                    chore_info[const.DATA_CHORE_STATE] = (
                        const.CHORE_STATE_APPROVED_IN_PART
                    )
                elif count_claimed > const.DEFAULT_ZERO:
                    chore_info[const.DATA_CHORE_STATE] = (
                        const.CHORE_STATE_CLAIMED_IN_PART
                    )
                else:
                    chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_UNKNOWN

            # For independent chores assigned to multiple kids, set state to INDEPENDENT if not all in same state
            else:
                chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_INDEPENDENT

        else:
            chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_UNKNOWN

        if debug_enabled:
            const.LOGGER.debug(
                "DEBUG: Chore State - Chore ID '%s' Global State changed to '%s'",
                chore_id,
                chore_info[const.DATA_CHORE_STATE],
            )

    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches,too-many-statements
    def _update_chore_data_for_kid(
        self,
        kid_id: str,
        chore_id: str,
        points_awarded: float,
        state: Optional[str] = None,
        due_date: Optional[str] = None,
    ):
        """
        Update a kid's chore data when a state change or completion occurs.

        Args:
            kid_id: The ID of the kid
            chore_id: The ID of the chore
            points_awarded: Points awarded for this chore
            state: New chore state (if state is changing)
            due_date: New due date (if due date is changing)
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # Get chore name for reference
        chore_info = self.chores_data.get(chore_id, {})
        chore_name = chore_info.get(const.DATA_CHORE_NAME, chore_id)

        # Initialize chore data structure if needed
        kid_chores_data = kid_info.setdefault(const.DATA_KID_CHORE_DATA, {})

        # Initialize this chore's data if it doesn't exist yet
        kid_chore_data = kid_chores_data.setdefault(
            chore_id,
            {
                const.DATA_KID_CHORE_DATA_NAME: chore_name,
                const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
                const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT: 0,
                const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
                const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
                const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
                const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
                const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
                const.DATA_KID_CHORE_DATA_PERIODS: {
                    const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
                    const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
                },
                const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
            },
        )

        # --- Use a consistent default dict for all period stats ---
        period_default = {
            const.DATA_KID_CHORE_DATA_PERIOD_APPROVED: 0,
            const.DATA_KID_CHORE_DATA_PERIOD_POINTS: 0.0,
            const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED: 0,
            const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE: 0,
            const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED: 0,
            const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK: 0,
        }

        # Get period keys using constants
        now_utc = dt_util.utcnow()
        now_iso = now_utc.isoformat()
        now_local = kh.get_now_local_time()
        today_local = kh.get_today_local_date()
        today_local_iso = today_local.isoformat()
        week_local_iso = now_local.strftime("%Y-W%V")
        month_local_iso = now_local.strftime("%Y-%m")
        year_local_iso = now_local.strftime("%Y")

        # For updating period stats - use setdefault to handle partial structures
        periods_data = kid_chore_data.setdefault(
            const.DATA_KID_CHORE_DATA_PERIODS,
            {
                const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
            },
        )
        period_keys = [
            (const.DATA_KID_CHORE_DATA_PERIODS_DAILY, today_local_iso),
            (const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY, week_local_iso),
            (const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY, month_local_iso),
            (const.DATA_KID_CHORE_DATA_PERIODS_YEARLY, year_local_iso),
            (const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME, const.PERIOD_ALL_TIME),
        ]

        previous_state = kid_chore_data.get(const.DATA_KID_CHORE_DATA_STATE)
        points_awarded = (
            round(points_awarded, const.DATA_FLOAT_PRECISION)
            if points_awarded is not None
            else 0.0
        )

        # --- All-time stats update helpers ---
        chore_stats = kid_info.setdefault(const.DATA_KID_CHORE_STATS, {})

        def inc_stat(key, amount):
            chore_stats[key] = chore_stats.get(key, 0) + amount

        # Helper to update period stats safely for all periods
        def update_periods(increments: dict, periods: list):
            for period_key, period_id in periods:
                period_data_dict = periods_data[period_key].setdefault(
                    period_id, period_default.copy()
                )
                for key, val in period_default.items():
                    period_data_dict.setdefault(key, val)
                for inc_key, inc_val in increments.items():
                    period_data_dict[inc_key] += inc_val

        if state is not None:
            kid_chore_data[const.DATA_KID_CHORE_DATA_STATE] = state

            # --- Handle CLAIMED state ---
            if state == const.CHORE_STATE_CLAIMED:
                kid_chore_data[const.DATA_KID_CHORE_DATA_LAST_CLAIMED] = now_iso
                update_periods(
                    {const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED: 1},
                    period_keys,
                )
                # Increment all-time claimed count
                inc_stat(const.DATA_KID_CHORE_STATS_CLAIMED_ALL_TIME, 1)

            # --- Handle APPROVED state ---
            elif state == const.CHORE_STATE_APPROVED:
                # Deprecated counters removed - using chore_stats only

                kid_chore_data[const.DATA_KID_CHORE_DATA_LAST_APPROVED] = now_iso

                inc_stat(const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME, 1)
                inc_stat(
                    const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_ALL_TIME,
                    points_awarded,
                )

                # Update period stats for count and points
                update_periods(
                    {
                        const.DATA_KID_CHORE_DATA_PERIOD_APPROVED: 1,
                        const.DATA_KID_CHORE_DATA_PERIOD_POINTS: points_awarded,
                    },
                    period_keys,
                )

                # Calculate today's streak based on yesterday's daily period data
                yesterday_local_iso = kh.adjust_datetime_by_interval(
                    today_local_iso,
                    interval_unit=const.TIME_UNIT_DAYS,
                    delta=-1,
                    require_future=False,
                    return_type=const.HELPER_RETURN_ISO_DATE,
                )
                yesterday_chore_data = periods_data[
                    const.DATA_KID_CHORE_DATA_PERIODS_DAILY
                ].get(yesterday_local_iso, {})
                yesterday_streak = yesterday_chore_data.get(
                    const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, 0
                )
                today_streak = yesterday_streak + 1 if yesterday_streak > 0 else 1

                # Store today's streak as the daily longest streak
                daily_data = periods_data[
                    const.DATA_KID_CHORE_DATA_PERIODS_DAILY
                ].setdefault(today_local_iso, period_default.copy())
                daily_data[const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK] = (
                    today_streak
                )

                # --- All-time longest streak update (per-chore and per-kid) ---
                all_time_data = periods_data[
                    const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME
                ].setdefault(const.PERIOD_ALL_TIME, period_default.copy())
                prev_all_time_streak = all_time_data.get(
                    const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, 0
                )
                if today_streak > prev_all_time_streak:
                    all_time_data[const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK] = (
                        today_streak
                    )
                    kid_chore_data[
                        const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME
                    ] = today_local_iso

                # Update streak for higher periods if needed (excluding all_time, already handled above)
                for period_key, period_id in [
                    (const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY, week_local_iso),
                    (const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY, month_local_iso),
                    (const.DATA_KID_CHORE_DATA_PERIODS_YEARLY, year_local_iso),
                ]:
                    period_data_dict = periods_data[period_key].setdefault(
                        period_id, period_default.copy()
                    )
                    if today_streak > period_data_dict.get(
                        const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, 0
                    ):
                        period_data_dict[
                            const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK
                        ] = today_streak

                # Still update the kid's global all-time longest streak if this is a new record
                longest_streak_all_time = chore_stats.get(
                    const.DATA_KID_CHORE_STATS_LONGEST_STREAK_ALL_TIME, 0
                )
                if today_streak > longest_streak_all_time:
                    chore_stats[const.DATA_KID_CHORE_STATS_LONGEST_STREAK_ALL_TIME] = (
                        today_streak
                    )

            # --- Handle OVERDUE state ---
            elif state == const.CHORE_STATE_OVERDUE:
                kid_chore_data[const.DATA_KID_CHORE_DATA_LAST_OVERDUE] = now_iso
                daily_data = periods_data[
                    const.DATA_KID_CHORE_DATA_PERIODS_DAILY
                ].setdefault(today_local_iso, period_default.copy())
                for key, val in period_default.items():
                    daily_data.setdefault(key, val)
                first_overdue_today = (
                    daily_data.get(const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE, 0) < 1
                )
                if first_overdue_today:
                    daily_data[const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE] = 1
                    # Only increment higher periods if this is the first overdue for today
                    update_periods(
                        {const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE: 1},
                        period_keys[1:],  # skip daily
                    )
                    inc_stat(const.DATA_KID_CHORE_STATS_OVERDUE_ALL_TIME, 1)

            # --- Handle DISAPPROVED (claimed -> pending) state ---
            elif (
                state == const.CHORE_STATE_PENDING
                and previous_state == const.CHORE_STATE_CLAIMED
            ):
                kid_chore_data[const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED] = now_iso
                daily_data = periods_data[
                    const.DATA_KID_CHORE_DATA_PERIODS_DAILY
                ].setdefault(today_local_iso, period_default.copy())
                for key, val in period_default.items():
                    daily_data.setdefault(key, val)
                first_disapproved_today = (
                    daily_data.get(const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED, 0) < 1
                )
                if first_disapproved_today:
                    daily_data[const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED] = 1
                    update_periods(
                        {const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED: 1},
                        period_keys[1:],  # skip daily
                    )
                    inc_stat(const.DATA_KID_CHORE_STATS_DISAPPROVED_ALL_TIME, 1)

        # Update due date if provided
        if due_date is not None:
            kid_chore_data[const.DATA_KID_CHORE_DATA_DUE_DATE] = due_date

        # Clean up old period data to keep storage manageable
        kh.cleanup_period_data(
            self,
            periods_data=periods_data,
            period_keys={
                const.FREQUENCY_DAILY: const.DATA_KID_CHORE_DATA_PERIODS_DAILY,
                const.FREQUENCY_WEEKLY: const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY,
                const.FREQUENCY_MONTHLY: const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY,
                const.FREQUENCY_YEARLY: const.DATA_KID_CHORE_DATA_PERIODS_YEARLY,
            },
            retention_daily=self.config_entry.options.get(
                const.CONF_RETENTION_DAILY, const.DEFAULT_RETENTION_DAILY
            ),
            retention_weekly=self.config_entry.options.get(
                const.CONF_RETENTION_WEEKLY, const.DEFAULT_RETENTION_WEEKLY
            ),
            retention_monthly=self.config_entry.options.get(
                const.CONF_RETENTION_MONTHLY, const.DEFAULT_RETENTION_MONTHLY
            ),
            retention_yearly=self.config_entry.options.get(
                const.CONF_RETENTION_YEARLY, const.DEFAULT_RETENTION_YEARLY
            ),
        )

        # --- Update kid_chore_stats after all per-chore updates ---
        self._recalculate_chore_stats_for_kid(kid_id)

    # pylint: disable=too-many-locals,too-many-statements
    def _recalculate_chore_stats_for_kid(self, kid_id: str):
        """Aggregate and update all kid_chore_stats for a given kid.

        This function always resets all stat keys to zero/default and then
        aggregates from the current state of all chore data. This ensures
        stats are never double-counted, even if this function is called
        multiple times per state change.

        Note: All-time stats (completed_all_time, total_points_all_time, longest_streak_all_time)
        must be stored incrementally and not reset here, since old period data may be pruned.
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # --- Reset all stat keys (prevents double counting) Exception for All-time stats which are always kept and updated as necessary---
        # --- All-time stats could be calculated from individual chore all-time stats, but then deleted chore data would also need to be stored.
        stats = {
            const.DATA_KID_CHORE_STATS_APPROVED_TODAY: 0,
            const.DATA_KID_CHORE_STATS_APPROVED_WEEK: 0,
            const.DATA_KID_CHORE_STATS_APPROVED_MONTH: 0,
            const.DATA_KID_CHORE_STATS_APPROVED_YEAR: 0,
            # All-time stats are loaded from persistent storage, not recalculated
            const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME: kid_info.get(
                const.DATA_KID_CHORE_STATS, {}
            ).get(const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME, 0),
            # --- Claimed counts ---
            const.DATA_KID_CHORE_STATS_CLAIMED_TODAY: 0,
            const.DATA_KID_CHORE_STATS_CLAIMED_WEEK: 0,
            const.DATA_KID_CHORE_STATS_CLAIMED_MONTH: 0,
            const.DATA_KID_CHORE_STATS_CLAIMED_YEAR: 0,
            # All-time stats are loaded from persistent storage, not recalculated
            const.DATA_KID_CHORE_STATS_CLAIMED_ALL_TIME: kid_info.get(
                const.DATA_KID_CHORE_STATS, {}
            ).get(const.DATA_KID_CHORE_STATS_CLAIMED_ALL_TIME, 0),
            # --- Overdue counts ---
            const.DATA_KID_CHORE_STATS_OVERDUE_TODAY: 0,
            const.DATA_KID_CHORE_STATS_OVERDUE_WEEK: 0,
            const.DATA_KID_CHORE_STATS_OVERDUE_MONTH: 0,
            const.DATA_KID_CHORE_STATS_OVERDUE_YEAR: 0,
            const.DATA_KID_CHORE_STATS_OVERDUE_ALL_TIME: kid_info.get(
                const.DATA_KID_CHORE_STATS, {}
            ).get(const.DATA_KID_CHORE_STATS_OVERDUE_ALL_TIME, 0),
            # --- Disapproved counts ---
            const.DATA_KID_CHORE_STATS_DISAPPROVED_TODAY: 0,
            const.DATA_KID_CHORE_STATS_DISAPPROVED_WEEK: 0,
            const.DATA_KID_CHORE_STATS_DISAPPROVED_MONTH: 0,
            const.DATA_KID_CHORE_STATS_DISAPPROVED_YEAR: 0,
            # All-time stats are loaded from persistent storage, not recalculated
            const.DATA_KID_CHORE_STATS_DISAPPROVED_ALL_TIME: kid_info.get(
                const.DATA_KID_CHORE_STATS, {}
            ).get(const.DATA_KID_CHORE_STATS_DISAPPROVED_ALL_TIME, 0),
            # --- Longest streaks ---
            const.DATA_KID_CHORE_STATS_LONGEST_STREAK_WEEK: 0,
            const.DATA_KID_CHORE_STATS_LONGEST_STREAK_MONTH: 0,
            const.DATA_KID_CHORE_STATS_LONGEST_STREAK_YEAR: 0,
            const.DATA_KID_CHORE_STATS_LONGEST_STREAK_ALL_TIME: kid_info.get(
                const.DATA_KID_CHORE_STATS, {}
            ).get(const.DATA_KID_CHORE_STATS_LONGEST_STREAK_ALL_TIME, 0),
            # --- Most completed chore ---
            const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_ALL_TIME: None,
            const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_WEEK: None,
            const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_MONTH: None,
            const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_YEAR: None,
            # --- Total points from chores ---
            const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_TODAY: 0.0,
            const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_WEEK: 0.0,
            const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_MONTH: 0.0,
            const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_YEAR: 0.0,
            # All-time stats are loaded from persistent storage, not recalculated
            const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_ALL_TIME: kid_info.get(
                const.DATA_KID_CHORE_STATS, {}
            ).get(const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_ALL_TIME, 0.0),
            # --- Average points per day ---
            const.DATA_KID_CHORE_STATS_AVG_PER_DAY_WEEK: 0.0,
            const.DATA_KID_CHORE_STATS_AVG_PER_DAY_MONTH: 0.0,
            # --- Current status stats ---
            const.DATA_KID_CHORE_STATS_CURRENT_DUE_TODAY: 0,
            const.DATA_KID_CHORE_STATS_CURRENT_OVERDUE: 0,
            const.DATA_KID_CHORE_STATS_CURRENT_CLAIMED: 0,
            const.DATA_KID_CHORE_STATS_CURRENT_APPROVED: 0,
        }

        # Get current period keys
        now_local = kh.get_now_local_time()
        today_local_iso = kh.get_today_local_date().isoformat()
        week_local_iso = now_local.strftime("%Y-W%V")
        month_local_iso = now_local.strftime("%Y-%m")
        year_local_iso = now_local.strftime("%Y")

        # For most completed chore
        most_completed = {}
        most_completed_week = {}
        most_completed_month = {}
        most_completed_year = {}

        # For longest streaks
        max_streak_week = 0
        max_streak_month = 0
        max_streak_year = 0

        # --- Aggregate stats from all chores (no double counting) ---
        for chore_id, chore_data in kid_info.get(const.DATA_KID_CHORE_DATA, {}).items():
            # All-time stats are incremented at event time, not recalculated here

            # Period stats
            periods = chore_data.get(const.DATA_KID_CHORE_DATA_PERIODS, {})

            # Most completed chore (all time)
            all_time = periods.get(const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME, {})
            total_count = all_time.get(const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0)
            most_completed[chore_id] = total_count

            # Daily
            daily = periods.get(const.DATA_KID_CHORE_DATA_PERIODS_DAILY, {})
            today_stats = daily.get(today_local_iso, {})
            stats[const.DATA_KID_CHORE_STATS_APPROVED_TODAY] += today_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_TODAY] += (
                today_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_POINTS, 0.0)
            )
            stats[const.DATA_KID_CHORE_STATS_OVERDUE_TODAY] += today_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE, 0
            )
            stats[const.DATA_KID_CHORE_STATS_DISAPPROVED_TODAY] += today_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_CLAIMED_TODAY] += today_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED, 0
            )

            # Weekly
            weekly = periods.get(const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY, {})
            week_stats = weekly.get(week_local_iso, {})
            stats[const.DATA_KID_CHORE_STATS_APPROVED_WEEK] += week_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_WEEK] += (
                week_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_POINTS, 0.0)
            )
            stats[const.DATA_KID_CHORE_STATS_OVERDUE_WEEK] += week_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE, 0
            )
            stats[const.DATA_KID_CHORE_STATS_DISAPPROVED_WEEK] += week_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_CLAIMED_WEEK] += week_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED, 0
            )
            most_completed_week[chore_id] = week_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            max_streak_week = max(
                max_streak_week,
                week_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, 0),
            )

            # Monthly
            monthly = periods.get(const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY, {})
            month_stats = monthly.get(month_local_iso, {})
            stats[const.DATA_KID_CHORE_STATS_APPROVED_MONTH] += month_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_MONTH] += (
                month_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_POINTS, 0.0)
            )
            stats[const.DATA_KID_CHORE_STATS_OVERDUE_MONTH] += month_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE, 0
            )
            stats[const.DATA_KID_CHORE_STATS_DISAPPROVED_MONTH] += month_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_CLAIMED_MONTH] += month_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED, 0
            )
            most_completed_month[chore_id] = month_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            max_streak_month = max(
                max_streak_month,
                month_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, 0),
            )

            # Yearly
            yearly = periods.get(const.DATA_KID_CHORE_DATA_PERIODS_YEARLY, {})
            year_stats = yearly.get(year_local_iso, {})
            stats[const.DATA_KID_CHORE_STATS_APPROVED_YEAR] += year_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_YEAR] += (
                year_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_POINTS, 0.0)
            )
            stats[const.DATA_KID_CHORE_STATS_OVERDUE_YEAR] += year_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE, 0
            )
            stats[const.DATA_KID_CHORE_STATS_DISAPPROVED_YEAR] += year_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED, 0
            )
            stats[const.DATA_KID_CHORE_STATS_CLAIMED_YEAR] += year_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED, 0
            )
            most_completed_year[chore_id] = year_stats.get(
                const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
            )
            max_streak_year = max(
                max_streak_year,
                year_stats.get(const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, 0),
            )

            # --- Current status counts ---
            state = chore_data.get(const.DATA_KID_CHORE_DATA_STATE)

            # Get due date based on completion_criteria:
            # - INDEPENDENT: read from per_kid_due_dates (source of truth)
            # - SHARED_*: read from chore-level due_date
            chore_info = self.chores_data.get(chore_id, {})
            completion_criteria = chore_info.get(
                const.DATA_CHORE_COMPLETION_CRITERIA,
                const.COMPLETION_CRITERIA_INDEPENDENT,  # Default for legacy
            )
            if completion_criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
                per_kid_due_dates = chore_info.get(
                    const.DATA_CHORE_PER_KID_DUE_DATES, {}
                )
                due_datetime_iso = per_kid_due_dates.get(kid_id)
            else:
                # SHARED_ALL, SHARED_FIRST, ALTERNATING
                due_datetime_iso = chore_info.get(const.DATA_CHORE_DUE_DATE)

            due_date_local = kh.normalize_datetime_input(
                due_datetime_iso, return_type=const.HELPER_RETURN_DATETIME_LOCAL
            )
            if due_date_local:
                try:
                    today_local = kh.get_today_local_date()
                    # due_date_local is a datetime, convert to date for comparison
                    if (
                        isinstance(due_date_local, datetime)
                        and due_date_local.date() == today_local
                    ):
                        stats[const.DATA_KID_CHORE_STATS_CURRENT_DUE_TODAY] += 1
                except (AttributeError, TypeError):
                    pass
            if state == const.CHORE_STATE_OVERDUE:
                stats[const.DATA_KID_CHORE_STATS_CURRENT_OVERDUE] += 1
            elif state == const.CHORE_STATE_CLAIMED:
                stats[const.DATA_KID_CHORE_STATS_CURRENT_CLAIMED] += 1
            elif state in (
                const.CHORE_STATE_APPROVED,
                const.CHORE_STATE_APPROVED_IN_PART,
            ):
                stats[const.DATA_KID_CHORE_STATS_CURRENT_APPROVED] += 1

        # --- Derived stats (no double counting, just pick max or calculate) ---
        if most_completed:
            most_completed_chore_id = max(
                most_completed, key=lambda x: most_completed.get(x, 0)
            )
            chore_name = self.chores_data.get(most_completed_chore_id, {}).get(
                const.DATA_CHORE_NAME, most_completed_chore_id
            )
            stats[const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_ALL_TIME] = chore_name
        if most_completed_week:
            most_completed_week_id = max(
                most_completed_week, key=lambda x: most_completed_week.get(x, 0)
            )
            chore_name = self.chores_data.get(most_completed_week_id, {}).get(
                const.DATA_CHORE_NAME, most_completed_week_id
            )
            stats[const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_WEEK] = chore_name
        if most_completed_month:
            most_completed_month_id = max(
                most_completed_month, key=lambda x: most_completed_month.get(x, 0)
            )
            chore_name = self.chores_data.get(most_completed_month_id, {}).get(
                const.DATA_CHORE_NAME, most_completed_month_id
            )
            stats[const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_MONTH] = chore_name
        if most_completed_year:
            most_completed_year_id = max(
                most_completed_year, key=lambda x: most_completed_year.get(x, 0)
            )
            chore_name = self.chores_data.get(most_completed_year_id, {}).get(
                const.DATA_CHORE_NAME, most_completed_year_id
            )
            stats[const.DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_YEAR] = chore_name

        stats[const.DATA_KID_CHORE_STATS_LONGEST_STREAK_WEEK] = max_streak_week
        stats[const.DATA_KID_CHORE_STATS_LONGEST_STREAK_MONTH] = max_streak_month
        stats[const.DATA_KID_CHORE_STATS_LONGEST_STREAK_YEAR] = max_streak_year

        # Averages (no double counting, just divide)
        stats[const.DATA_KID_CHORE_STATS_AVG_PER_DAY_WEEK] = round(
            (
                stats[const.DATA_KID_CHORE_STATS_APPROVED_WEEK] / 7.0
                if stats[const.DATA_KID_CHORE_STATS_APPROVED_WEEK]
                else 0.0
            ),
            const.DATA_FLOAT_PRECISION,
        )
        now = kh.get_now_local_time()
        days_in_month = monthrange(now.year, now.month)[1]
        stats[const.DATA_KID_CHORE_STATS_AVG_PER_DAY_MONTH] = round(
            (
                stats[const.DATA_KID_CHORE_STATS_APPROVED_MONTH] / days_in_month
                if stats[const.DATA_KID_CHORE_STATS_APPROVED_MONTH]
                else 0.0
            ),
            const.DATA_FLOAT_PRECISION,
        )

        # --- Save back to kid_info ---
        kid_info[const.DATA_KID_CHORE_STATS] = stats

    # -------------------------------------------------------------------------------------
    # Kids: Update Points
    # -------------------------------------------------------------------------------------

    def update_kid_points(
        self, kid_id: str, delta: float, *, source: str = const.POINTS_SOURCE_OTHER
    ):
        """
        Adjust a kid's points by delta (±), track by-source, update legacy stats,
        record into new point_data history, then recheck badges/achievements/challenges.
        Also updates all-time and highest balance stats using constants.
        If the source is chores, applies the kid's multiplier.
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            const.LOGGER.warning(
                "WARNING: Update Kid Points - Kid ID '%s' not found", kid_id
            )
            return

        # 1) Sanitize delta
        try:
            delta_value = round(float(delta), const.DATA_FLOAT_PRECISION)
        except (ValueError, TypeError):
            const.LOGGER.warning(
                "WARNING: Update Kid Points - Invalid delta '%s' for Kid ID '%s'.",
                delta,
                kid_id,
            )
            return
        if delta_value == 0:
            const.LOGGER.debug(
                "DEBUG: Update Kid Points - No change (delta=0) for Kid ID '%s'", kid_id
            )
            return

        # If source is chores, apply multiplier
        if source == const.POINTS_SOURCE_CHORES:
            multiplier = kid_info.get(const.DATA_KID_POINTS_MULTIPLIER, 1.0)
            delta_value = round(
                delta_value * float(multiplier), const.DATA_FLOAT_PRECISION
            )

        # 2) Compute new balance
        try:
            old = round(
                float(kid_info.get(const.DATA_KID_POINTS, 0.0)),
                const.DATA_FLOAT_PRECISION,
            )
        except (ValueError, TypeError):
            const.LOGGER.warning(
                "WARNING: Update Kid Points - Invalid old_points for Kid ID '%s'. Defaulting to 0.0.",
                kid_id,
            )
            old = 0.0
        new = old + delta_value
        kid_info[const.DATA_KID_POINTS] = new

        # 3) Legacy cumulative badge logic
        progress = kid_info.get(const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {})
        if delta_value > 0:
            progress.setdefault(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS, 0.0
            )
            progress[const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS] += (
                delta_value
            )
            progress[const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS] = round(
                progress[const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS],
                const.DATA_FLOAT_PRECISION,
            )

        # 5) All-time and highest balance stats (handled incrementally)
        point_stats = kid_info.setdefault(const.DATA_KID_POINT_STATS, {})
        point_stats.setdefault(const.DATA_KID_POINT_STATS_EARNED_ALL_TIME, 0.0)
        point_stats.setdefault(const.DATA_KID_POINT_STATS_SPENT_ALL_TIME, 0.0)
        point_stats.setdefault(const.DATA_KID_POINT_STATS_NET_ALL_TIME, 0.0)
        point_stats.setdefault(const.DATA_KID_POINT_STATS_BY_SOURCE_ALL_TIME, {})
        point_stats.setdefault(const.DATA_KID_POINT_STATS_HIGHEST_BALANCE, 0.0)

        if delta_value > 0:
            point_stats[const.DATA_KID_POINT_STATS_EARNED_ALL_TIME] += delta_value
            point_stats[const.DATA_KID_POINT_STATS_EARNED_ALL_TIME] = round(
                point_stats[const.DATA_KID_POINT_STATS_EARNED_ALL_TIME],
                const.DATA_FLOAT_PRECISION,
            )
        elif delta_value < 0:
            point_stats[const.DATA_KID_POINT_STATS_SPENT_ALL_TIME] += delta_value
            point_stats[const.DATA_KID_POINT_STATS_SPENT_ALL_TIME] = round(
                point_stats[const.DATA_KID_POINT_STATS_SPENT_ALL_TIME],
                const.DATA_FLOAT_PRECISION,
            )
        point_stats[const.DATA_KID_POINT_STATS_NET_ALL_TIME] += delta_value
        point_stats[const.DATA_KID_POINT_STATS_NET_ALL_TIME] = round(
            point_stats[const.DATA_KID_POINT_STATS_NET_ALL_TIME],
            const.DATA_FLOAT_PRECISION,
        )

        # 6) Record into new point_data history (use same date logic as chore_data)
        periods_data = kid_info.setdefault(const.DATA_KID_POINT_DATA, {}).setdefault(
            const.DATA_KID_POINT_DATA_PERIODS, {}
        )

        now_local = kh.get_now_local_time()
        today_local_iso = kh.get_today_local_date().isoformat()
        week_local_iso = now_local.strftime("%Y-W%V")
        month_local_iso = now_local.strftime("%Y-%m")
        year_local_iso = now_local.strftime("%Y")

        for period_key, period_id in [
            (const.DATA_KID_POINT_DATA_PERIODS_DAILY, today_local_iso),
            (const.DATA_KID_POINT_DATA_PERIODS_WEEKLY, week_local_iso),
            (const.DATA_KID_POINT_DATA_PERIODS_MONTHLY, month_local_iso),
            (const.DATA_KID_POINT_DATA_PERIODS_YEARLY, year_local_iso),
        ]:
            bucket = periods_data.setdefault(period_key, {})
            entry = bucket.setdefault(period_id, {})
            # Safely initialize fields if missing
            if const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL not in entry:
                entry[const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL] = 0.0
            if (
                const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE not in entry
                or not isinstance(
                    entry[const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE], dict
                )
            ):
                entry[const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE] = {}
            entry[const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL] += delta_value
            entry[const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL] = round(
                entry[const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL],
                const.DATA_FLOAT_PRECISION,
            )
            entry[const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE].setdefault(source, 0.0)
            entry[const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE][source] += delta_value
            entry[const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE][source] = round(
                entry[const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE][source],
                const.DATA_FLOAT_PRECISION,
            )

        # 7) Re‑evaluate everything and persist
        # Note: Call _recalculate_point_stats_for_kid BEFORE updating all-time stats
        # so that it preserves the incrementally-tracked all-time values
        self._recalculate_point_stats_for_kid(kid_id)

        # 8) Update all-time by-source stats (must be done AFTER recalculate to avoid being overwritten)
        point_stats = kid_info[const.DATA_KID_POINT_STATS]
        by_source_all_time = point_stats[const.DATA_KID_POINT_STATS_BY_SOURCE_ALL_TIME]
        by_source_all_time.setdefault(source, 0.0)
        by_source_all_time[source] += delta_value
        by_source_all_time[source] = round(
            by_source_all_time[source], const.DATA_FLOAT_PRECISION
        )

        if new > point_stats[const.DATA_KID_POINT_STATS_HIGHEST_BALANCE]:
            point_stats[const.DATA_KID_POINT_STATS_HIGHEST_BALANCE] = new
        kh.cleanup_period_data(
            self,
            periods_data=periods_data,
            period_keys={
                "daily": const.DATA_KID_POINT_DATA_PERIODS_DAILY,
                "weekly": const.DATA_KID_POINT_DATA_PERIODS_WEEKLY,
                "monthly": const.DATA_KID_POINT_DATA_PERIODS_MONTHLY,
                "yearly": const.DATA_KID_POINT_DATA_PERIODS_YEARLY,
            },
            retention_daily=self.config_entry.options.get(
                const.CONF_RETENTION_DAILY, const.DEFAULT_RETENTION_DAILY
            ),
            retention_weekly=self.config_entry.options.get(
                const.CONF_RETENTION_WEEKLY, const.DEFAULT_RETENTION_WEEKLY
            ),
            retention_monthly=self.config_entry.options.get(
                const.CONF_RETENTION_MONTHLY, const.DEFAULT_RETENTION_MONTHLY
            ),
            retention_yearly=self.config_entry.options.get(
                const.CONF_RETENTION_YEARLY, const.DEFAULT_RETENTION_YEARLY
            ),
        )
        self._check_badges_for_kid(kid_id)
        self._check_achievements_for_kid(kid_id)
        self._check_challenges_for_kid(kid_id)

        self._persist()
        self.async_set_updated_data(self._data)

        const.LOGGER.debug(
            "DEBUG: Update Kid Points - Kid ID '%s': delta=%.2f, old=%.2f, new=%.2f, source=%s",
            kid_id,
            delta_value,
            old,
            new,
            source,
        )

    def _recalculate_point_stats_for_kid(self, kid_id: str):
        """Aggregate and update all kid_point_stats for a given kid.

        This function always resets all stat keys to zero/default and then
        aggregates from the current state of all point data. This ensures
        stats are never double-counted, even if this function is called
        multiple times per state change.

        Note: All-time stats (earned_all_time, spent_all_time, net_all_time, by_source_all_time, highest_balance)
        must be stored incrementally and not reset here, since old period data may be pruned.
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        point_stats = kid_info.get(const.DATA_KID_POINT_STATS, {})

        stats = {
            # Per-period stats
            const.DATA_KID_POINT_STATS_EARNED_TODAY: 0.0,
            const.DATA_KID_POINT_STATS_EARNED_WEEK: 0.0,
            const.DATA_KID_POINT_STATS_EARNED_MONTH: 0.0,
            const.DATA_KID_POINT_STATS_EARNED_YEAR: 0.0,
            # All-time stats (handled incrementally in update_kid_points, not recalculated here)
            const.DATA_KID_POINT_STATS_EARNED_ALL_TIME: point_stats.get(
                const.DATA_KID_POINT_STATS_EARNED_ALL_TIME, 0.0
            ),
            # By-source breakdowns
            const.DATA_KID_POINT_STATS_BY_SOURCE_TODAY: {},
            const.DATA_KID_POINT_STATS_BY_SOURCE_WEEK: {},
            const.DATA_KID_POINT_STATS_BY_SOURCE_MONTH: {},
            const.DATA_KID_POINT_STATS_BY_SOURCE_YEAR: {},
            # All-time by-source (handled incrementally)
            const.DATA_KID_POINT_STATS_BY_SOURCE_ALL_TIME: point_stats.get(
                const.DATA_KID_POINT_STATS_BY_SOURCE_ALL_TIME, {}
            ).copy(),
            # Spent (negative deltas)
            const.DATA_KID_POINT_STATS_SPENT_TODAY: 0.0,
            const.DATA_KID_POINT_STATS_SPENT_WEEK: 0.0,
            const.DATA_KID_POINT_STATS_SPENT_MONTH: 0.0,
            const.DATA_KID_POINT_STATS_SPENT_YEAR: 0.0,
            # All-time spent (handled incrementally)
            const.DATA_KID_POINT_STATS_SPENT_ALL_TIME: point_stats.get(
                const.DATA_KID_POINT_STATS_SPENT_ALL_TIME, 0.0
            ),
            # Net (earned - spent)
            const.DATA_KID_POINT_STATS_NET_TODAY: 0.0,
            const.DATA_KID_POINT_STATS_NET_WEEK: 0.0,
            const.DATA_KID_POINT_STATS_NET_MONTH: 0.0,
            const.DATA_KID_POINT_STATS_NET_YEAR: 0.0,
            # All-time net (This is calculated even though it is an all time stat)
            const.DATA_KID_POINT_STATS_NET_ALL_TIME: 0.0,
            # Highest balance ever (handled incrementally)
            const.DATA_KID_POINT_STATS_HIGHEST_BALANCE: point_stats.get(
                const.DATA_KID_POINT_STATS_HIGHEST_BALANCE, 0.0
            ),
            # Averages (calculated below)
            const.DATA_KID_POINT_STATS_AVG_PER_DAY_WEEK: 0.0,
            const.DATA_KID_POINT_STATS_AVG_PER_DAY_MONTH: 0.0,
            # Streaks and avg per chore are optional, not implemented here
            # const.DATA_KID_POINT_STATS_EARNING_STREAK_CURRENT: 0,
            # const.DATA_KID_POINT_STATS_EARNING_STREAK_LONGEST: 0,
            # const.DATA_KID_POINT_STATS_AVG_PER_CHORE: 0.0,
        }

        pts_periods = kid_info.get(const.DATA_KID_POINT_DATA, {}).get(
            const.DATA_KID_POINT_DATA_PERIODS, {}
        )

        now_local = kh.get_now_local_time()
        today_local_iso = kh.get_today_local_date().isoformat()
        week_local_iso = now_local.strftime("%Y-W%V")
        month_local_iso = now_local.strftime("%Y-%m")
        year_local_iso = now_local.strftime("%Y")

        def get_period(period_key, period_id):
            period = pts_periods.get(period_key, {})
            entry = period.get(period_id, {})
            by_source = entry.get(const.DATA_KID_POINT_DATA_PERIOD_BY_SOURCE, {})
            earned = round(
                sum(v for v in by_source.values() if v > 0),
                const.DATA_FLOAT_PRECISION,
            )
            spent = round(
                sum(v for v in by_source.values() if v < 0),
                const.DATA_FLOAT_PRECISION,
            )
            net = round(
                entry.get(const.DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL, 0.0),
                const.DATA_FLOAT_PRECISION,
            )
            return earned, spent, net, by_source.copy()

        # Daily
        earned, spent, net, by_source = get_period(
            const.DATA_KID_POINT_DATA_PERIODS_DAILY, today_local_iso
        )
        stats[const.DATA_KID_POINT_STATS_EARNED_TODAY] = earned
        stats[const.DATA_KID_POINT_STATS_SPENT_TODAY] = spent
        stats[const.DATA_KID_POINT_STATS_NET_TODAY] = net
        stats[const.DATA_KID_POINT_STATS_BY_SOURCE_TODAY] = by_source

        # Weekly
        earned, spent, net, by_source = get_period(
            const.DATA_KID_POINT_DATA_PERIODS_WEEKLY, week_local_iso
        )
        stats[const.DATA_KID_POINT_STATS_EARNED_WEEK] = earned
        stats[const.DATA_KID_POINT_STATS_SPENT_WEEK] = spent
        stats[const.DATA_KID_POINT_STATS_NET_WEEK] = net
        stats[const.DATA_KID_POINT_STATS_BY_SOURCE_WEEK] = by_source

        # Monthly
        earned, spent, net, by_source = get_period(
            const.DATA_KID_POINT_DATA_PERIODS_MONTHLY, month_local_iso
        )
        stats[const.DATA_KID_POINT_STATS_EARNED_MONTH] = earned
        stats[const.DATA_KID_POINT_STATS_SPENT_MONTH] = spent
        stats[const.DATA_KID_POINT_STATS_NET_MONTH] = net
        stats[const.DATA_KID_POINT_STATS_BY_SOURCE_MONTH] = by_source

        # Yearly
        earned, spent, net, by_source = get_period(
            const.DATA_KID_POINT_DATA_PERIODS_YEARLY, year_local_iso
        )
        stats[const.DATA_KID_POINT_STATS_EARNED_YEAR] = earned
        stats[const.DATA_KID_POINT_STATS_SPENT_YEAR] = spent
        stats[const.DATA_KID_POINT_STATS_NET_YEAR] = net
        stats[const.DATA_KID_POINT_STATS_BY_SOURCE_YEAR] = by_source

        # --- All-time Net stats ---
        stats[const.DATA_KID_POINT_STATS_NET_ALL_TIME] = round(
            stats[const.DATA_KID_POINT_STATS_EARNED_ALL_TIME]
            + stats[const.DATA_KID_POINT_STATS_SPENT_ALL_TIME],
            const.DATA_FLOAT_PRECISION,
        )

        # --- Averages ---
        stats[const.DATA_KID_POINT_STATS_AVG_PER_DAY_WEEK] = (
            round(
                stats[const.DATA_KID_POINT_STATS_EARNED_WEEK] / 7.0,
                const.DATA_FLOAT_PRECISION,
            )
            if stats[const.DATA_KID_POINT_STATS_EARNED_WEEK]
            else 0.0
        )
        now = kh.get_now_local_time()
        days_in_month = monthrange(now.year, now.month)[1]
        stats[const.DATA_KID_POINT_STATS_AVG_PER_DAY_MONTH] = (
            round(
                stats[const.DATA_KID_POINT_STATS_EARNED_MONTH] / days_in_month,
                const.DATA_FLOAT_PRECISION,
            )
            if stats[const.DATA_KID_POINT_STATS_EARNED_MONTH]
            else 0.0
        )

        # --- Save back to kid_info ---
        kid_info[const.DATA_KID_POINT_STATS] = stats

    # -------------------------------------------------------------------------------------
    # Rewards: Redeem, Approve, Disapprove
    # -------------------------------------------------------------------------------------

    def redeem_reward(self, parent_name: str, kid_id: str, reward_id: str):  # pylint: disable=unused-argument
        """Kid claims a reward => mark as pending approval (no deduction yet)."""
        reward_info = self.rewards_data.get(reward_id)
        if not reward_info:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_REWARD,
                    "name": reward_id,
                },
            )

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_KID,
                    "name": kid_id,
                },
            )

        cost = reward_info.get(const.DATA_REWARD_COST, const.DEFAULT_ZERO)
        if kid_info[const.DATA_KID_POINTS] < cost:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_INSUFFICIENT_POINTS,
                translation_placeholders={
                    "kid": kid_info[const.DATA_KID_NAME],
                    "current": str(kid_info[const.DATA_KID_POINTS]),
                    "required": str(cost),
                },
            )

        # Update kid_reward_data structure
        reward_entry = self._get_kid_reward_data(kid_id, reward_id, create=True)
        reward_entry[const.DATA_KID_REWARD_DATA_PENDING_COUNT] = (
            reward_entry.get(const.DATA_KID_REWARD_DATA_PENDING_COUNT, 0) + 1
        )
        reward_entry[const.DATA_KID_REWARD_DATA_LAST_CLAIMED] = (
            dt_util.utcnow().isoformat()
        )
        reward_entry[const.DATA_KID_REWARD_DATA_TOTAL_CLAIMS] = (
            reward_entry.get(const.DATA_KID_REWARD_DATA_TOTAL_CLAIMS, 0) + 1
        )

        # Update period-based tracking for claimed
        self._increment_reward_period_counter(
            reward_entry, const.DATA_KID_REWARD_DATA_PERIOD_CLAIMED
        )

        # Generate a unique notification ID for this claim.
        notif_id = uuid.uuid4().hex

        # Track notification ID for this claim
        reward_entry.setdefault(const.DATA_KID_REWARD_DATA_NOTIFICATION_IDS, []).append(
            notif_id
        )

        # Send a notification to the parents that a kid claimed a reward
        actions = [
            {
                const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_REWARD}|{kid_id}|{reward_id}|{notif_id}",
                const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_APPROVE,
            },
            {
                const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_REWARD}|{kid_id}|{reward_id}|{notif_id}",
                const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_DISAPPROVE,
            },
            {
                const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{reward_id}|{notif_id}",
                const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_REMIND_30,
            },
        ]
        extra_data = {
            const.DATA_KID_ID: kid_id,
            const.DATA_REWARD_ID: reward_id,
            const.DATA_REWARD_NOTIFICATION_ID: notif_id,
        }
        self.hass.async_create_task(
            self._notify_parents_translated(
                kid_id,
                title_key=const.TRANS_KEY_NOTIF_TITLE_REWARD_CLAIMED,
                message_key=const.TRANS_KEY_NOTIF_MESSAGE_REWARD_CLAIMED_PARENT,
                message_data={
                    "kid_name": kid_info[const.DATA_KID_NAME],
                    "reward_name": reward_info[const.DATA_REWARD_NAME],
                    "points": reward_info[const.DATA_REWARD_COST],
                },
                actions=actions,
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    def approve_reward(  # pylint: disable=unused-argument
        self,
        parent_name: str,  # Reserved for future feature
        kid_id: str,
        reward_id: str,
        notif_id: Optional[str] = None,
    ):
        """Parent approves the reward => deduct points."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_KID,
                    "name": kid_id,
                },
            )

        reward_info = self.rewards_data.get(reward_id)
        if not reward_info:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_REWARD,
                    "name": reward_id,
                },
            )

        cost = reward_info.get(const.DATA_REWARD_COST, const.DEFAULT_ZERO)

        # Get pending_count from kid_reward_data
        reward_entry = self._get_kid_reward_data(kid_id, reward_id, create=False)
        pending_count = reward_entry.get(const.DATA_KID_REWARD_DATA_PENDING_COUNT, 0)

        if pending_count > 0:
            if kid_info[const.DATA_KID_POINTS] < cost:
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_INSUFFICIENT_POINTS,
                    translation_placeholders={
                        "kid": kid_info[const.DATA_KID_NAME],
                        "current": str(kid_info[const.DATA_KID_POINTS]),
                        "required": str(cost),
                    },
                )

            # Deduct points for one claim.
            if cost is not None:
                self.update_kid_points(
                    kid_id, delta=-cost, source=const.POINTS_SOURCE_REWARDS
                )

            # Update kid_reward_data structure
            if reward_entry:
                reward_entry[const.DATA_KID_REWARD_DATA_PENDING_COUNT] = max(
                    0, reward_entry.get(const.DATA_KID_REWARD_DATA_PENDING_COUNT, 0) - 1
                )
                reward_entry[const.DATA_KID_REWARD_DATA_LAST_APPROVED] = (
                    dt_util.utcnow().isoformat()
                )
                reward_entry[const.DATA_KID_REWARD_DATA_TOTAL_APPROVED] = (
                    reward_entry.get(const.DATA_KID_REWARD_DATA_TOTAL_APPROVED, 0) + 1
                )
                reward_entry[const.DATA_KID_REWARD_DATA_TOTAL_POINTS_SPENT] = (
                    reward_entry.get(const.DATA_KID_REWARD_DATA_TOTAL_POINTS_SPENT, 0)
                    + cost
                )

                # Update period-based tracking for approved + points
                self._increment_reward_period_counter(
                    reward_entry, const.DATA_KID_REWARD_DATA_PERIOD_APPROVED
                )
                self._increment_reward_period_counter(
                    reward_entry, const.DATA_KID_REWARD_DATA_PERIOD_POINTS, amount=cost
                )

                # Remove notification ID if provided
                if notif_id:
                    notif_ids = reward_entry.get(
                        const.DATA_KID_REWARD_DATA_NOTIFICATION_IDS, []
                    )
                    if notif_id in notif_ids:
                        notif_ids.remove(notif_id)

                # Cleanup old period data using retention settings
                kh.cleanup_period_data(
                    self,
                    periods_data=reward_entry.get(
                        const.DATA_KID_REWARD_DATA_PERIODS, {}
                    ),
                    period_keys={
                        "daily": const.DATA_KID_REWARD_DATA_PERIODS_DAILY,
                        "weekly": const.DATA_KID_REWARD_DATA_PERIODS_WEEKLY,
                        "monthly": const.DATA_KID_REWARD_DATA_PERIODS_MONTHLY,
                        "yearly": const.DATA_KID_REWARD_DATA_PERIODS_YEARLY,
                    },
                    retention_daily=self.config_entry.options.get(
                        const.CONF_RETENTION_DAILY, const.DEFAULT_RETENTION_DAILY
                    ),
                    retention_weekly=self.config_entry.options.get(
                        const.CONF_RETENTION_WEEKLY, const.DEFAULT_RETENTION_WEEKLY
                    ),
                    retention_monthly=self.config_entry.options.get(
                        const.CONF_RETENTION_MONTHLY, const.DEFAULT_RETENTION_MONTHLY
                    ),
                    retention_yearly=self.config_entry.options.get(
                        const.CONF_RETENTION_YEARLY, const.DEFAULT_RETENTION_YEARLY
                    ),
                )

        else:
            # Direct approval (no pending claim present).
            if kid_info[const.DATA_KID_POINTS] < cost:
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_INSUFFICIENT_POINTS,
                    translation_placeholders={
                        "kid": kid_info[const.DATA_KID_NAME],
                        "current": str(kid_info[const.DATA_KID_POINTS]),
                        "required": str(cost),
                    },
                )
            kid_info[const.DATA_KID_POINTS] -= cost

            # Update kid_reward_data structure for direct approval
            direct_entry = self._get_kid_reward_data(kid_id, reward_id, create=True)
            direct_entry[const.DATA_KID_REWARD_DATA_LAST_APPROVED] = (
                dt_util.utcnow().isoformat()
            )
            direct_entry[const.DATA_KID_REWARD_DATA_TOTAL_APPROVED] = (
                direct_entry.get(const.DATA_KID_REWARD_DATA_TOTAL_APPROVED, 0) + 1
            )
            direct_entry[const.DATA_KID_REWARD_DATA_TOTAL_POINTS_SPENT] = (
                direct_entry.get(const.DATA_KID_REWARD_DATA_TOTAL_POINTS_SPENT, 0)
                + cost
            )

            # Update period-based tracking for approved + points
            self._increment_reward_period_counter(
                direct_entry, const.DATA_KID_REWARD_DATA_PERIOD_APPROVED
            )
            self._increment_reward_period_counter(
                direct_entry, const.DATA_KID_REWARD_DATA_PERIOD_POINTS, amount=cost
            )

            # Cleanup old period data using retention settings
            kh.cleanup_period_data(
                self,
                periods_data=direct_entry.get(const.DATA_KID_REWARD_DATA_PERIODS, {}),
                period_keys={
                    "daily": const.DATA_KID_REWARD_DATA_PERIODS_DAILY,
                    "weekly": const.DATA_KID_REWARD_DATA_PERIODS_WEEKLY,
                    "monthly": const.DATA_KID_REWARD_DATA_PERIODS_MONTHLY,
                    "yearly": const.DATA_KID_REWARD_DATA_PERIODS_YEARLY,
                },
                retention_daily=self.config_entry.options.get(
                    const.CONF_RETENTION_DAILY, const.DEFAULT_RETENTION_DAILY
                ),
                retention_weekly=self.config_entry.options.get(
                    const.CONF_RETENTION_WEEKLY, const.DEFAULT_RETENTION_WEEKLY
                ),
                retention_monthly=self.config_entry.options.get(
                    const.CONF_RETENTION_MONTHLY, const.DEFAULT_RETENTION_MONTHLY
                ),
                retention_yearly=self.config_entry.options.get(
                    const.CONF_RETENTION_YEARLY, const.DEFAULT_RETENTION_YEARLY
                ),
            )

        # Check badges
        self._check_badges_for_kid(kid_id)

        # Notify the kid that the reward has been approved
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_REWARD_ID: reward_id}
        self.hass.async_create_task(
            self._notify_kid_translated(
                kid_id,
                title_key=const.TRANS_KEY_NOTIF_TITLE_REWARD_APPROVED,
                message_key=const.TRANS_KEY_NOTIF_MESSAGE_REWARD_APPROVED,
                message_data={"reward_name": reward_info[const.DATA_REWARD_NAME]},
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    def disapprove_reward(self, parent_name: str, kid_id: str, reward_id: str):  # pylint: disable=unused-argument
        """Disapprove a reward for kid_id."""

        reward_info = self.rewards_data.get(reward_id)
        if not reward_info:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_REWARD,
                    "name": reward_id,
                },
            )

        kid_info = self.kids_data.get(kid_id)

        # Update kid_reward_data structure
        if kid_info:
            reward_entry = self._get_kid_reward_data(kid_id, reward_id, create=False)
            if reward_entry:
                reward_entry[const.DATA_KID_REWARD_DATA_PENDING_COUNT] = max(
                    0, reward_entry.get(const.DATA_KID_REWARD_DATA_PENDING_COUNT, 0) - 1
                )
                reward_entry[const.DATA_KID_REWARD_DATA_LAST_DISAPPROVED] = (
                    dt_util.utcnow().isoformat()
                )
                reward_entry[const.DATA_KID_REWARD_DATA_TOTAL_DISAPPROVED] = (
                    reward_entry.get(const.DATA_KID_REWARD_DATA_TOTAL_DISAPPROVED, 0)
                    + 1
                )

                # Update period-based tracking for disapproved
                self._increment_reward_period_counter(
                    reward_entry, const.DATA_KID_REWARD_DATA_PERIOD_DISAPPROVED
                )

        # Send a notification to the kid that reward was disapproved
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_REWARD_ID: reward_id}
        self.hass.async_create_task(
            self._notify_kid_translated(
                kid_id,
                title_key=const.TRANS_KEY_NOTIF_TITLE_REWARD_DISAPPROVED,
                message_key=const.TRANS_KEY_NOTIF_MESSAGE_REWARD_DISAPPROVED,
                message_data={"reward_name": reward_info[const.DATA_REWARD_NAME]},
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------------------
    # Badges: Check, Award
    # -------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------
    # Badge Data vs. Kid Badge Progress Data
    # -----------------------------------------------------------------------------
    # Badge data (badge_info): stores static configuration for each badge (name, type,
    # thresholds, tracked chores, reset schedule, etc.).
    # Kid badge progress data (progress): stores per-kid, per-badge progress (state,
    # cycle counts, points, start/end dates, etc.).
    # Always use badge data for config lookups and kid progress data for runtime state.
    # This separation ensures config changes are reflected and progress is tracked per kid.
    # -----------------------------------------------------------------------------

    def _check_badges_for_kid(self, kid_id: str):
        """Evaluate all badge thresholds for kid and update progress.

        This function:
        - Respects badge start/end dates.
        - Tracks daily progress and rolls it into the cycle count on day change.
        - Updates an overall progress field (DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS) for UI/logic.
        - Awards badges if criteria are met.
        """
        # PERF: Measure badge evaluation duration per kid
        perf_start = time.perf_counter()

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # Maintenance cycles to ensure badge progress is initialized and up-to-date
        self._manage_badge_maintenance(kid_id)
        self._manage_cumulative_badge_maintenance(kid_id)

        # OPTIMIZATION: Calculate today_local_iso once per kid instead of per badge
        today_local_iso = kh.get_today_local_iso()

        # OPTIMIZATION: Pre-compute kid's assigned chores once instead of per badge
        kid_assigned_chores = []
        for chore_id, chore_info in self.chores_data.items():
            chore_assigned_to = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
            if not chore_assigned_to or kid_id in chore_assigned_to:
                kid_assigned_chores.append(chore_id)

        # Mapping of target_type to handler and parameters
        target_type_handlers = {
            const.BADGE_TARGET_THRESHOLD_TYPE_POINTS: (
                self._handle_badge_target_points,
                {},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_POINTS_CHORES: (
                self._handle_badge_target_points,
                {const.BADGE_HANDLER_PARAM_FROM_CHORES_ONLY: True},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_CHORE_COUNT: (
                self._handle_badge_target_chore_count,
                {},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES: (
                self._handle_badge_target_daily_completion,
                {const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_CHORES: (
                self._handle_badge_target_daily_completion,
                {const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 0.8},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES_NO_OVERDUE: (
                self._handle_badge_target_daily_completion,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0,
                    const.BADGE_HANDLER_PARAM_REQUIRE_NO_OVERDUE: True,
                },
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES: (
                self._handle_badge_target_daily_completion,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0,
                    const.BADGE_HANDLER_PARAM_ONLY_DUE_TODAY: True,
                },
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_DUE_CHORES: (
                self._handle_badge_target_daily_completion,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 0.8,
                    const.BADGE_HANDLER_PARAM_ONLY_DUE_TODAY: True,
                },
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES_NO_OVERDUE: (
                self._handle_badge_target_daily_completion,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0,
                    const.BADGE_HANDLER_PARAM_ONLY_DUE_TODAY: True,
                    const.BADGE_HANDLER_PARAM_REQUIRE_NO_OVERDUE: True,
                },
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_3_CHORES: (
                self._handle_badge_target_daily_completion,
                {const.BADGE_HANDLER_PARAM_MIN_COUNT: 3},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_5_CHORES: (
                self._handle_badge_target_daily_completion,
                {const.BADGE_HANDLER_PARAM_MIN_COUNT: 5},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_7_CHORES: (
                self._handle_badge_target_daily_completion,
                {const.BADGE_HANDLER_PARAM_MIN_COUNT: 7},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES: (
                self._handle_badge_target_streak,
                {const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_CHORES: (
                self._handle_badge_target_streak,
                {const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 0.8},
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES_NO_OVERDUE: (
                self._handle_badge_target_streak,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0,
                    const.BADGE_HANDLER_PARAM_REQUIRE_NO_OVERDUE: True,
                },
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_DUE_CHORES: (
                self._handle_badge_target_streak,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 0.8,
                    const.BADGE_HANDLER_PARAM_ONLY_DUE_TODAY: True,
                },
            ),
            const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_DUE_CHORES_NO_OVERDUE: (
                self._handle_badge_target_streak,
                {
                    const.BADGE_HANDLER_PARAM_PERCENT_REQUIRED: 1.0,
                    const.BADGE_HANDLER_PARAM_ONLY_DUE_TODAY: True,
                    const.BADGE_HANDLER_PARAM_REQUIRE_NO_OVERDUE: True,
                },
            ),
        }

        for badge_id, badge_info in self.badges_data.items():
            badge_type = badge_info.get(const.DATA_BADGE_TYPE)

            # Feature Change v4.2: Badges now require explicit assignment.
            # Empty assigned_to means badge is not assigned to any kid.
            assigned_to_list = badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
            is_assigned_to = kid_id in assigned_to_list
            if not is_assigned_to:
                continue

            # Note this process will only award a cumulative badge the first time.  Once
            # the badge is awarded, any future maintenance and awards associated with
            # maintenance periods will be handled by the _manage_cumulative_badge_maintenance
            # function.
            if badge_type == const.BADGE_TYPE_CUMULATIVE:
                if kid_id in badge_info.get(const.DATA_BADGE_EARNED_BY, []):
                    # This badge has already been awarded, so skip it
                    continue

                cumulative_badge_progress = self._get_cumulative_badge_progress(kid_id)
                if cumulative_badge_progress:
                    stored_cumulative_badge_progress = self.kids_data[kid_id].get(
                        const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
                    )
                    stored_cumulative_badge_progress.update(cumulative_badge_progress)
                    self.kids_data[kid_id][const.DATA_KID_CUMULATIVE_BADGE_PROGRESS] = (
                        stored_cumulative_badge_progress
                    )
                effective_badge_id = cumulative_badge_progress.get(
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID, None
                )
                if effective_badge_id and effective_badge_id == badge_id:
                    # This badge matches with the calculated effective badge ID, so it should be awarded
                    progress = kid_info.get(
                        const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
                    )
                    try:
                        baseline_points = float(
                            progress.get(
                                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE,
                                const.DEFAULT_ZERO,
                            )
                        )
                        cycle_points = float(
                            progress.get(
                                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS,
                                const.DEFAULT_ZERO,
                            )
                        )
                    except (ValueError, TypeError) as err:
                        const.LOGGER.error(
                            "ERROR: Award Badge - Non-numeric values for cumulative points for kid '%s': %s",
                            kid_info.get(const.DATA_KID_NAME, kid_id),
                            err,
                        )
                        return
                    progress[const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE] = (
                        baseline_points + cycle_points
                    )
                    progress[const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS] = (
                        const.DEFAULT_ZERO
                    )

                    self._award_badge(kid_id, badge_id)

                # OPTIMIZATION: Defer persist to end (removed mid-loop persist)
                continue

            # Respect badge start/end dates
            badge_progress = kid_info.get(const.DATA_KID_BADGE_PROGRESS, {}).get(
                badge_id, {}
            )
            start_date_iso = badge_progress.get(
                const.DATA_KID_BADGE_PROGRESS_START_DATE
            )
            end_date_iso = badge_progress.get(const.DATA_KID_BADGE_PROGRESS_END_DATE)
            # today_local_iso calculated once per kid (see line ~3973)
            in_effect = (not start_date_iso or today_local_iso >= start_date_iso) and (
                not end_date_iso or today_local_iso <= end_date_iso
            )
            const.LOGGER.debug(
                "DEBUG: Badge Progress - Badge '%s' for kid '%s': today_local_iso=%s, start_date_iso=%s, end_date_iso=%s, in_effect=%s",
                badge_info.get(const.DATA_BADGE_NAME, badge_id),
                kid_info.get(const.DATA_KID_NAME, "Unknown Kid"),
                today_local_iso,
                start_date_iso,
                end_date_iso,
                in_effect,
            )

            if not in_effect:
                continue

            # Get chores tracked by this badge (using pre-computed kid chores)
            tracked_chores = self._get_badge_in_scope_chores_list(
                badge_info, kid_id, kid_assigned_chores
            )
            target_type = badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                const.DATA_BADGE_TARGET_TYPE
            )
            threshold_value = float(
                badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                    const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                )
            )

            # Copy progress dict for updates
            progress = badge_progress.copy() if badge_progress else {}

            handler_tuple = target_type_handlers.get(target_type)
            if handler_tuple:
                handler, handler_kwargs = handler_tuple
                progress = handler(
                    kid_info,
                    badge_info,
                    badge_id,
                    tracked_chores,
                    progress,
                    today_local_iso,
                    threshold_value,
                    **handler_kwargs,
                )
            else:
                # Fallback for unknown types (could log or skip)
                continue

            # Store the updated progress data for this badge
            kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id] = progress

            # Award the badge if criteria are met and not already earned
            if progress.get(const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET, False):
                current_state = progress.get(
                    const.DATA_KID_BADGE_PROGRESS_STATUS,
                    const.BADGE_STATE_IN_PROGRESS,
                )
                if current_state != const.BADGE_STATE_EARNED:
                    kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id][
                        const.DATA_KID_BADGE_PROGRESS_STATUS
                    ] = const.BADGE_STATE_EARNED
                    kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id][
                        const.DATA_KID_BADGE_PROGRESS_LAST_AWARDED
                    ] = kh.get_today_local_iso()
                    self._award_badge(kid_id, badge_id)

        # Update badge references to reflect current badge tracking settings
        self._update_chore_badge_references_for_kid()

        self._persist()
        self.async_set_updated_data(self._data)

        # PERF: Log badge evaluation duration
        perf_duration = time.perf_counter() - perf_start
        badge_count = len(self.badges_data)
        const.LOGGER.debug(
            "PERF: _check_badges_for_kid() evaluated %d badges in %.3fs for kid '%s'",
            badge_count,
            perf_duration,
            kid_id,
        )

    def _get_badge_in_scope_chores_list(
        self, badge_info: dict, kid_id: str, kid_assigned_chores: list | None = None
    ) -> list:
        """
        Get the list of chore IDs that are in-scope for this badge evaluation.

        For badges with tracked chores:
        - Returns only those specific chore IDs that are also assigned to the kid
        For badges without tracked chores:
        - Returns all chore IDs assigned to the kid

        Args:
            badge_info: Badge configuration dictionary
            kid_id: Kid's internal ID
            kid_assigned_chores: Optional pre-computed list of chores assigned to kid
                                (optimization to avoid re-iterating all chores)
        """

        badge_type = badge_info.get(const.DATA_BADGE_TYPE, const.BADGE_TYPE_PERIODIC)
        include_tracked_chores = badge_type in const.INCLUDE_TRACKED_CHORES_BADGE_TYPES

        # OPTIMIZATION: Use pre-computed list if provided, otherwise compute
        if kid_assigned_chores is None:
            kid_assigned_chores = []
            # Get all chores assigned to this kid
            for chore_id, chore_info in self.chores_data.items():
                chore_assigned_to = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
                if not chore_assigned_to or kid_id in chore_assigned_to:
                    kid_assigned_chores.append(chore_id)

        # If badge does not include tracked chores, return empty list
        if include_tracked_chores:
            tracked_chores = badge_info.get(const.DATA_BADGE_TRACKED_CHORES, {})
            tracked_chore_ids = tracked_chores.get(
                const.DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES, []
            )

            if tracked_chore_ids:
                # Badge has specific tracked chores, return only those that are also assigned to the kid
                return [
                    chore_id
                    for chore_id in tracked_chore_ids
                    if chore_id in kid_assigned_chores
                ]
            # Badge considers all chores, return all chores assigned to the kid
            return kid_assigned_chores
        # Badge does not include tracked chores component, return empty list
        return []

    def _handle_badge_target_points(  # pylint: disable=unused-argument
        self,
        kid_info,
        badge_info,  # Reserved for future feature
        badge_id,  # Reserved for future feature
        tracked_chores,
        progress,
        today_local_iso,
        threshold_value,
        from_chores_only=False,
    ):
        """Handle points-based badge targets (all points or from chores only)."""
        total_points_all_sources, total_points_chores, _, _, points_map, _, _ = (
            kh.get_today_chore_and_point_progress(kid_info, tracked_chores)
        )
        points_today = (
            total_points_chores if from_chores_only else total_points_all_sources
        )
        last_update_day = progress.get(const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY)
        points_cycle_count = progress.get(
            const.DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT, 0
        )

        if last_update_day and last_update_day != today_local_iso:
            points_cycle_count += progress.get(
                const.DATA_KID_BADGE_PROGRESS_POINTS_TODAY, 0
            )
            progress[const.DATA_KID_BADGE_PROGRESS_POINTS_TODAY] = 0

        progress[const.DATA_KID_BADGE_PROGRESS_POINTS_TODAY] = points_today
        progress[const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY] = today_local_iso
        progress[const.DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT] = points_cycle_count
        progress[const.DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED] = points_map
        progress[const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES] = tracked_chores

        progress[const.DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS] = round(
            min(
                (points_cycle_count + points_today) / threshold_value
                if threshold_value
                else 0,
                1.0,
            ),
            const.DATA_FLOAT_PRECISION,
        )
        progress[const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET] = (
            points_cycle_count + points_today
        ) >= threshold_value
        return progress

    def _handle_badge_target_chore_count(  # pylint: disable=unused-argument
        self,
        kid_info,
        badge_info,  # Reserved for future feature
        badge_id,  # Reserved for future feature
        tracked_chores,
        progress,
        today_local_iso,
        threshold_value,
        min_count=None,
    ):
        """Handle chore count-based badge targets (optionally with a minimum count per day)."""
        _, _, chore_count_today, _, _, count_map, _ = (
            kh.get_today_chore_and_point_progress(kid_info, tracked_chores)
        )
        if min_count is not None and chore_count_today < min_count:
            chore_count_today = 0  # Only count days meeting the minimum

        last_update_day = progress.get(const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY)
        chores_cycle_count = progress.get(
            const.DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT, 0
        )

        if last_update_day and last_update_day != today_local_iso:
            chores_cycle_count += progress.get(
                const.DATA_KID_BADGE_PROGRESS_CHORES_TODAY, 0
            )
            progress[const.DATA_KID_BADGE_PROGRESS_CHORES_TODAY] = 0

        progress[const.DATA_KID_BADGE_PROGRESS_CHORES_TODAY] = chore_count_today
        progress[const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY] = today_local_iso
        progress[const.DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT] = chores_cycle_count
        progress[const.DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED] = count_map
        progress[const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES] = tracked_chores

        progress[const.DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS] = round(
            min(
                (chores_cycle_count + chore_count_today) / threshold_value
                if threshold_value
                else 0,
                1.0,
            ),
            const.DATA_FLOAT_PRECISION,
        )
        progress[const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET] = (
            chores_cycle_count + chore_count_today
        ) >= threshold_value
        return progress

    def _handle_badge_target_daily_completion(  # pylint: disable=unused-argument
        self,
        kid_info,
        badge_info,  # Reserved for future feature
        badge_id,  # Reserved for future feature
        tracked_chores,
        progress,
        today_local_iso,
        threshold_value,
        percent_required=1.0,
        only_due_today=False,
        require_no_overdue=False,
        min_count=None,
    ):
        """Handle daily completion-based badge targets (all, percent, due, no overdue, min N)."""
        criteria_met, approved_count, total_count = (
            kh.get_today_chore_completion_progress(
                kid_info,
                tracked_chores,
                percent_required=percent_required,
                require_no_overdue=require_no_overdue,
                only_due_today=only_due_today,
                count_required=min_count,
            )
        )
        days_completed = progress.get(const.DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED, {})
        last_update_day = progress.get(const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY)
        days_cycle_count = progress.get(
            const.DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT, 0
        )

        if last_update_day and last_update_day != today_local_iso:
            if progress.get(const.DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED, False):
                days_cycle_count += 1
            progress[const.DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED] = False

        progress[const.DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED] = criteria_met
        progress[const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY] = today_local_iso

        if criteria_met:
            days_completed[today_local_iso] = True
        progress[const.DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED] = days_completed
        progress[const.DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT] = days_cycle_count
        progress[const.DATA_KID_BADGE_PROGRESS_APPROVED_COUNT] = approved_count
        progress[const.DATA_KID_BADGE_PROGRESS_TOTAL_COUNT] = total_count
        progress[const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES] = tracked_chores

        progress[const.DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS] = round(
            min(
                (days_cycle_count + (1 if criteria_met else 0)) / threshold_value
                if threshold_value
                else 0,
                1.0,
            ),
            const.DATA_FLOAT_PRECISION,
        )
        progress[const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET] = (
            days_cycle_count + (1 if criteria_met else 0)
        ) >= threshold_value
        return progress

    def _handle_badge_target_streak(  # pylint: disable=unused-argument
        self,
        kid_info,
        badge_info,  # Reserved for future feature
        badge_id,  # Reserved for future feature
        tracked_chores,
        progress,
        today_local_iso,
        threshold_value,
        percent_required=1.0,
        only_due_today=False,
        require_no_overdue=False,
        min_count=None,
    ):
        """Handle streak-based badge targets (consecutive days meeting criteria).

        Uses the same fields as daily completion, but interprets DAYS_CYCLE_COUNT as the current streak.
        """
        criteria_met, approved_count, total_count = (
            kh.get_today_chore_completion_progress(
                kid_info,
                tracked_chores,
                percent_required=percent_required,
                require_no_overdue=require_no_overdue,
                only_due_today=only_due_today,
                count_required=min_count,
            )
        )
        last_update_day = progress.get(const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY)
        streak = progress.get(const.DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT, 0)
        days_completed = progress.get(const.DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED, {})

        if last_update_day and last_update_day != today_local_iso:
            if progress.get(const.DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED, False):
                # Only increment streak if yesterday was completed
                yesterday_iso = kh.adjust_datetime_by_interval(
                    today_local_iso,
                    interval_unit=const.TIME_UNIT_DAYS,
                    delta=-1,
                    require_future=False,
                    return_type=const.HELPER_RETURN_ISO_DATE,
                )
                if days_completed.get(yesterday_iso):
                    streak += 1
                else:
                    streak = 1 if criteria_met else 0
            else:
                streak = 0
            progress[const.DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED] = False

        # Update today's completion status and last_update_day
        progress[const.DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED] = criteria_met
        progress[const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY] = today_local_iso

        if criteria_met:
            days_completed[today_local_iso] = True
        progress[const.DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED] = days_completed
        progress[const.DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT] = streak
        progress[const.DATA_KID_BADGE_PROGRESS_APPROVED_COUNT] = approved_count
        progress[const.DATA_KID_BADGE_PROGRESS_TOTAL_COUNT] = total_count
        progress[const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES] = tracked_chores

        progress[const.DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS] = round(
            min(
                streak / threshold_value if threshold_value else 0,
                1.0,
            ),
            const.DATA_FLOAT_PRECISION,
        )
        progress[const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET] = streak >= threshold_value
        return progress

    def _award_badge(self, kid_id: str, badge_id: str):
        """Add the badge to kid's 'earned_by' and kid's 'badges' list."""
        badge_info = self.badges_data.get(badge_id)
        kid_info = self.kids_data.get(kid_id, {})
        if not kid_info:
            const.LOGGER.error("Award Badge - Kid ID '%s' not found.", kid_id)
            return
        if not badge_info:
            const.LOGGER.error(
                "ERROR: Award Badge - Badge ID '%s' not found. Cannot be awarded to Kid ID '%s'",
                badge_id,
                kid_id,
            )
            return

        badge_type = badge_info.get(const.DATA_BADGE_TYPE, const.BADGE_TYPE_CUMULATIVE)
        badge_name = badge_info.get(const.DATA_BADGE_NAME)
        kid_name = kid_info[const.DATA_KID_NAME]

        # Award the badge (for all types, including special occasion).
        const.LOGGER.info(
            "INFO: Award Badge - Awarding badge '%s' (%s) to kid '%s' (%s).",
            badge_id,
            badge_name,
            kid_id,
            kid_name,
        )
        earned_by_list = badge_info.setdefault(const.DATA_BADGE_EARNED_BY, [])
        if kid_id not in earned_by_list:
            earned_by_list.append(kid_id)
        self._update_badges_earned_for_kid(kid_id, badge_id)

        # --- Unified Award Items Logic ---
        award_data = badge_info.get(const.DATA_BADGE_AWARDS, {})
        award_items = award_data.get(const.DATA_BADGE_AWARDS_AWARD_ITEMS, [])
        points_awarded = award_data.get(
            const.DATA_BADGE_AWARDS_AWARD_POINTS, const.DEFAULT_ZERO
        )
        multiplier = award_data.get(
            const.DATA_BADGE_AWARDS_POINT_MULTIPLIER,
            const.DEFAULT_KID_POINTS_MULTIPLIER,
        )

        # Process award_items using helper
        to_award, _ = self.process_award_items(
            award_items,
            self.rewards_data,
            self.bonuses_data,
            self.penalties_data,
        )

        # 1. Points
        if any(
            item == const.AWARD_ITEMS_KEY_POINTS
            or item.startswith(const.AWARD_ITEMS_PREFIX_POINTS)
            for item in award_items
        ):
            if points_awarded > const.DEFAULT_ZERO:
                const.LOGGER.info(
                    "INFO: Award Badge - Awarding points: %s for kid '%s'.",
                    points_awarded,
                    kid_name,
                )
                self.update_kid_points(
                    kid_id,
                    delta=points_awarded,
                    source=const.POINTS_SOURCE_BADGES,
                )

        # 2. Multiplier (only for cumulative badges)
        if any(
            item == const.AWARD_ITEMS_KEY_POINTS_MULTIPLIER
            or item.startswith(const.AWARD_ITEMS_PREFIX_POINTS_MULTIPLIER)
            for item in award_items
        ):
            if multiplier > const.DEFAULT_ZERO:
                kid_info[const.DATA_KID_POINTS_MULTIPLIER] = multiplier
                const.LOGGER.info(
                    "INFO: Award Badge - Set points multiplier to %.2f for kid '%s'.",
                    multiplier,
                    kid_name,
                )
            else:
                kid_info[const.DATA_KID_POINTS_MULTIPLIER] = (
                    const.DEFAULT_POINTS_MULTIPLIER
                )

        # 3. Rewards (multiple) - Badge awards grant rewards directly (no claim/approval flow)
        for reward_id in to_award.get(const.AWARD_ITEMS_KEY_REWARDS, []):
            if reward_id in self.rewards_data:
                # Update modern reward_data tracking
                reward_data = self._get_kid_reward_data(kid_id, reward_id)
                reward_data[const.DATA_KID_REWARD_DATA_TOTAL_APPROVED] = (
                    reward_data.get(const.DATA_KID_REWARD_DATA_TOTAL_APPROVED, 0) + 1
                )
                # Increment period counter for this approval
                self._increment_reward_period_counter(
                    reward_data, const.DATA_KID_REWARD_DATA_PERIOD_APPROVED
                )
                const.LOGGER.info(
                    "INFO: Award Badge - Granted reward '%s' to kid '%s'.",
                    self.rewards_data[reward_id].get(const.DATA_REWARD_NAME, reward_id),
                    kid_name,
                )

        # 4. Bonuses (multiple)
        for bonus_id in to_award.get(const.AWARD_ITEMS_KEY_BONUSES, []):
            if bonus_id in self.bonuses_data:
                self.apply_bonus(kid_name, kid_id, bonus_id)

        # --- Notification ---
        message = f"You earned a new badge: '{badge_name}'!"
        if to_award.get(const.AWARD_ITEMS_KEY_REWARDS):
            reward_names = [
                self.rewards_data[rid].get(const.DATA_REWARD_NAME, rid)
                for rid in to_award[const.AWARD_ITEMS_KEY_REWARDS]
            ]
            message += f" Rewards: {', '.join(reward_names)}."
        if to_award.get(const.AWARD_ITEMS_KEY_BONUSES):
            bonus_names = [
                self.bonuses_data[bid].get(const.DATA_BONUS_NAME, bid)
                for bid in to_award[const.AWARD_ITEMS_KEY_BONUSES]
            ]
            message += f" Bonuses: {', '.join(bonus_names)}."
        if any(
            item == const.AWARD_ITEMS_KEY_POINTS
            or item.startswith(const.AWARD_ITEMS_PREFIX_POINTS)
            for item in award_items
        ):
            message += f" Points: {points_awarded}."
        if badge_type == const.BADGE_TYPE_CUMULATIVE and any(
            item == const.AWARD_ITEMS_KEY_POINTS_MULTIPLIER
            or item.startswith(const.AWARD_ITEMS_PREFIX_POINTS_MULTIPLIER)
            for item in award_items
        ):
            message += f" Multiplier: {multiplier}x."

        parent_message = f"'{kid_name}' earned a new badge: '{badge_name}'."
        if to_award.get(const.AWARD_ITEMS_KEY_REWARDS):
            reward_names = [
                self.rewards_data[rid].get(const.DATA_REWARD_NAME, rid)
                for rid in to_award[const.AWARD_ITEMS_KEY_REWARDS]
            ]
            parent_message += f" Rewards: {', '.join(reward_names)}."
        if to_award.get(const.AWARD_ITEMS_KEY_BONUSES):
            bonus_names = [
                self.bonuses_data[bid].get(const.DATA_BONUS_NAME, bid)
                for bid in to_award[const.AWARD_ITEMS_KEY_BONUSES]
            ]
            parent_message += f" Bonuses: {', '.join(bonus_names)}."
        if any(
            item == const.AWARD_ITEMS_KEY_POINTS
            or item.startswith(const.AWARD_ITEMS_PREFIX_POINTS)
            for item in award_items
        ):
            parent_message += f" Points: {points_awarded}."
        if badge_type == const.BADGE_TYPE_CUMULATIVE and any(
            item == const.AWARD_ITEMS_KEY_POINTS_MULTIPLIER
            or item.startswith(const.AWARD_ITEMS_PREFIX_POINTS_MULTIPLIER)
            for item in award_items
        ):
            parent_message += f" Multiplier: {multiplier}x."

        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_BADGE_ID: badge_id}
        self.hass.async_create_task(
            self._notify_kid_translated(
                kid_id,
                title_key=const.TRANS_KEY_NOTIF_TITLE_BADGE_EARNED,
                message_key=const.TRANS_KEY_NOTIF_MESSAGE_BADGE_EARNED_KID,
                message_data={"badge_name": badge_info.get(const.DATA_BADGE_NAME)},
                extra_data=extra_data,
            )
        )
        self.hass.async_create_task(
            self._notify_parents_translated(
                kid_id,
                title_key=const.TRANS_KEY_NOTIF_TITLE_BADGE_EARNED,
                message_key=const.TRANS_KEY_NOTIF_MESSAGE_BADGE_EARNED_PARENT,
                message_data={
                    "kid_name": self.kids_data[kid_id][const.DATA_KID_NAME],
                    "badge_name": badge_info.get(const.DATA_BADGE_NAME),
                },
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)
        self._check_badges_for_kid(kid_id)

    def process_award_items(
        self, award_items, rewards_dict, bonuses_dict, penalties_dict
    ):
        """Process award_items and return dicts of items to award or penalize."""
        to_award = {
            const.AWARD_ITEMS_KEY_REWARDS: [],
            const.AWARD_ITEMS_KEY_BONUSES: [],
        }
        to_penalize = []
        for item in award_items:
            if item.startswith(const.AWARD_ITEMS_PREFIX_REWARD):
                reward_id = item.split(":", 1)[1]
                if reward_id in rewards_dict:
                    to_award[const.AWARD_ITEMS_KEY_REWARDS].append(reward_id)
            elif item.startswith(const.AWARD_ITEMS_PREFIX_BONUS):
                bonus_id = item.split(":", 1)[1]
                if bonus_id in bonuses_dict:
                    to_award[const.AWARD_ITEMS_KEY_BONUSES].append(bonus_id)
            elif item.startswith(const.AWARD_ITEMS_PREFIX_PENALTY):
                penalty_id = item.split(":", 1)[1]
                if penalty_id in penalties_dict:
                    to_penalize.append(penalty_id)
        return to_award, to_penalize

    def _update_point_multiplier_for_kid(self, kid_id: str):
        """Update the kid's points multiplier based on the current (effective) cumulative badge only."""

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        progress = kid_info.get(const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {})
        current_badge_id = progress.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID
        )

        if current_badge_id:
            current_badge_info = self.badges_data.get(current_badge_id, {})
            badge_awards = current_badge_info.get(const.DATA_BADGE_AWARDS, {})
            multiplier = badge_awards.get(
                const.DATA_BADGE_AWARDS_POINT_MULTIPLIER,
                const.DEFAULT_KID_POINTS_MULTIPLIER,
            )
        else:
            multiplier = const.DEFAULT_KID_POINTS_MULTIPLIER

        kid_info[const.DATA_KID_POINTS_MULTIPLIER] = multiplier

    def _update_badges_earned_for_kid(self, kid_id: str, badge_id: str) -> None:
        """Update the kid's badges-earned tracking for the given badge, including period stats."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            const.LOGGER.error(
                "ERROR: Update Kid Badges Earned - Kid ID '%s' not found.", kid_id
            )
            return

        badge_info = self.badges_data.get(badge_id)
        if not badge_info:
            const.LOGGER.error(
                "ERROR: Update Kid Badges Earned - Badge ID '%s' not found.", badge_id
            )
            return

        today_local_iso = kh.get_today_local_iso()
        now = kh.get_now_local_time()
        week = now.strftime("%Y-W%V")
        month = now.strftime("%Y-%m")
        year = now.strftime("%Y")

        badges_earned = kid_info.setdefault(const.DATA_KID_BADGES_EARNED, {})

        # Use new constants for periods
        periods_key = const.DATA_KID_BADGES_EARNED_PERIODS
        period_daily = const.DATA_KID_BADGES_EARNED_PERIODS_DAILY
        period_weekly = const.DATA_KID_BADGES_EARNED_PERIODS_WEEKLY
        period_monthly = const.DATA_KID_BADGES_EARNED_PERIODS_MONTHLY
        period_yearly = const.DATA_KID_BADGES_EARNED_PERIODS_YEARLY

        if badge_id not in badges_earned:
            badges_earned[badge_id] = {
                const.DATA_KID_BADGES_EARNED_NAME: badge_info.get(
                    const.DATA_BADGE_NAME
                ),
                const.DATA_KID_BADGES_EARNED_LAST_AWARDED: today_local_iso,
                const.DATA_KID_BADGES_EARNED_AWARD_COUNT: 1,
                periods_key: {
                    period_daily: {today_local_iso: 1},
                    period_weekly: {week: 1},
                    period_monthly: {month: 1},
                    period_yearly: {year: 1},
                },
            }
            const.LOGGER.info(
                "INFO: Update Kid Badges Earned - Created new tracking for badge '%s' for kid '%s'.",
                badge_info.get(const.DATA_BADGE_NAME, badge_id),
                kid_info.get(const.DATA_KID_NAME, kid_id),
            )
        else:
            tracking_entry = badges_earned[badge_id]
            tracking_entry[const.DATA_KID_BADGES_EARNED_NAME] = badge_info.get(
                const.DATA_BADGE_NAME
            )
            tracking_entry[const.DATA_KID_BADGES_EARNED_LAST_AWARDED] = today_local_iso
            tracking_entry[const.DATA_KID_BADGES_EARNED_AWARD_COUNT] = (
                tracking_entry.get(const.DATA_KID_BADGES_EARNED_AWARD_COUNT, 0) + 1
            )
            # Ensure periods and sub-dicts exist
            periods = tracking_entry.setdefault(periods_key, {})
            periods.setdefault(period_daily, {})
            periods.setdefault(period_weekly, {})
            periods.setdefault(period_monthly, {})
            periods.setdefault(period_yearly, {})
            periods[period_daily][today_local_iso] = (
                periods[period_daily].get(today_local_iso, 0) + 1
            )
            periods[period_weekly][week] = periods[period_weekly].get(week, 0) + 1
            periods[period_monthly][month] = periods[period_monthly].get(month, 0) + 1
            periods[period_yearly][year] = periods[period_yearly].get(year, 0) + 1

            const.LOGGER.info(
                "INFO: Update Kid Badges Earned - Updated tracking for badge '%s' for kid '%s'.",
                badge_info.get(const.DATA_BADGE_NAME, badge_id),
                kid_info.get(const.DATA_KID_NAME, kid_id),
            )
            # Cleanup old period data
            kh.cleanup_period_data(
                self,
                periods_data=periods,
                period_keys={
                    "daily": const.DATA_KID_BADGES_EARNED_PERIODS_DAILY,
                    "weekly": const.DATA_KID_BADGES_EARNED_PERIODS_WEEKLY,
                    "monthly": const.DATA_KID_BADGES_EARNED_PERIODS_MONTHLY,
                    "yearly": const.DATA_KID_BADGES_EARNED_PERIODS_YEARLY,
                },
                retention_daily=self.config_entry.options.get(
                    const.CONF_RETENTION_DAILY, const.DEFAULT_RETENTION_DAILY
                ),
                retention_weekly=self.config_entry.options.get(
                    const.CONF_RETENTION_WEEKLY, const.DEFAULT_RETENTION_WEEKLY
                ),
                retention_monthly=self.config_entry.options.get(
                    const.CONF_RETENTION_MONTHLY, const.DEFAULT_RETENTION_MONTHLY
                ),
                retention_yearly=self.config_entry.options.get(
                    const.CONF_RETENTION_YEARLY, const.DEFAULT_RETENTION_YEARLY
                ),
            )

        self._persist()
        self.async_set_updated_data(self._data)

    def _update_chore_badge_references_for_kid(
        self, include_cumulative_badges: bool = False
    ):
        """Update badge reference lists in kid chore data.

        This maintains a list of which badges reference each chore,
        useful for quick lookups when evaluating badges.

        Args:
            include_cumulative_badges: Whether to include cumulative badges in the references.
                                    Default is False which excludes them since they are currently points only
        """
        # Clear existing badge references
        for kid_id, kid_info in self.kids_data.items():
            if const.DATA_KID_CHORE_DATA not in kid_info:
                continue

            for chore_data in kid_info[const.DATA_KID_CHORE_DATA].values():
                chore_data[const.DATA_KID_CHORE_DATA_BADGE_REFS] = []

        # Add badge references to relevant chores
        for badge_id, badge_info in self.badges_data.items():
            # Skip cumulative badges if not explicitly included
            if (
                not include_cumulative_badges
                and badge_info.get(const.DATA_BADGE_TYPE) == const.BADGE_TYPE_CUMULATIVE
            ):
                continue

            # For each kid this badge is assigned to
            assigned_to = badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
            for kid_id in (
                assigned_to or self.kids_data.keys()
            ):  # If empty, apply to all kids
                kid_info = self.kids_data.get(kid_id)
                if not kid_info or const.DATA_KID_CHORE_DATA not in kid_info:
                    continue

                # Use the helper function to get the correct in-scope chores for this badge and kid
                in_scope_chores_list = self._get_badge_in_scope_chores_list(
                    badge_info, kid_id
                )

                # Add badge reference to each tracked chore
                for chore_id in in_scope_chores_list:
                    if chore_id in kid_info[const.DATA_KID_CHORE_DATA]:
                        if (
                            badge_id
                            not in kid_info[const.DATA_KID_CHORE_DATA][chore_id][
                                const.DATA_KID_CHORE_DATA_BADGE_REFS
                            ]
                        ):
                            kid_info[const.DATA_KID_CHORE_DATA][chore_id][
                                const.DATA_KID_CHORE_DATA_BADGE_REFS
                            ].append(badge_id)

    # -------------------------------------------------------------------------------------
    # Badges: Remove Awarded Badges
    # Removes awarded badges from kids based on provided kid name and/or badge name.
    # Converts kid name to kid ID and badge name to badge ID for targeted removal using
    # the _remove_awarded_badges_by_id method.
    # If badge_id is not found, it assumes the badge was deleted and removes it from the kid's data.
    # If neither is provided, it globally removes all awarded badges from all kids.
    # -------------------------------------------------------------------------------------
    def remove_awarded_badges(
        self, kid_name: Optional[str] = None, badge_name: Optional[str] = None
    ) -> None:
        """Remove awarded badges based on provided kid_name and badge_name."""
        # Convert kid_name to kid_id if provided.
        kid_id = None
        if kid_name:
            kid_id = kh.get_kid_id_by_name(self, kid_name)
            if kid_id is None:
                const.LOGGER.error(
                    "ERROR: Remove Awarded Badges - Kid name '%s' not found.", kid_name
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                    translation_placeholders={
                        "entity_type": const.LABEL_KID,
                        "name": kid_name,
                    },
                )
        else:
            kid_id = None

        # If badge_name is provided, try to find its corresponding badge_id.
        if badge_name:
            badge_id = kh.get_badge_id_by_name(self, badge_name)
            if not badge_id:
                # If the badge isn't found, assume the actual badge was deleted but still listed in kid data
                const.LOGGER.warning(
                    "WARNING: Remove Awarded Badges - Badge name '%s' not found in badges_data. Removing from kid data only.",
                    badge_name,
                )
                # Remove badge name from a specific kid if kid_id is provided,
                # or from all kids if not.
                if kid_id:
                    kid_info = self.kids_data.get(kid_id)
                    if kid_info:
                        # Remove badge from the kid's earned badges
                        badges_earned = kid_info.get(const.DATA_KID_BADGES_EARNED, {})
                        to_remove = [
                            badge_id
                            for badge_id, entry in badges_earned.items()
                            if entry.get(const.DATA_KID_BADGES_EARNED_NAME)
                            == badge_name
                        ]
                        for badge_id in to_remove:
                            del badges_earned[badge_id]
                else:
                    for kid_info in self.kids_data.values():
                        # Remove badge from the kid's earned badges
                        badges_earned = kid_info.get(const.DATA_KID_BADGES_EARNED, {})
                        to_remove = [
                            badge_id
                            for badge_id, entry in badges_earned.items()
                            if entry.get(const.DATA_KID_BADGES_EARNED_NAME)
                            == badge_name
                        ]
                        for badge_id in to_remove:
                            del badges_earned[badge_id]

                self._persist()
                self.async_set_updated_data(self._data)
                return
        else:
            badge_id = None

        self._remove_awarded_badges_by_id(kid_id, badge_id)

    def _remove_awarded_badges_by_id(
        self, kid_id: Optional[str] = None, badge_id: Optional[str] = None
    ) -> None:
        """Removes awarded badges based on provided kid_id and badge_id."""

        const.LOGGER.info("Remove Awarded Badges - Starting removal process.")
        found = False

        if badge_id and kid_id:
            # Reset a specific badge for a specific kid.
            kid_info = self.kids_data.get(kid_id)
            badge_info = self.badges_data.get(badge_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Remove Awarded Badges - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                    translation_placeholders={
                        "entity_type": const.LABEL_KID,
                        "name": kid_id,
                    },
                )
            if not badge_info:
                const.LOGGER.error(
                    "ERROR: Remove Awarded Badges - Badge ID '%s' not found.", badge_id
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                    translation_placeholders={
                        "entity_type": const.LABEL_BADGE,
                        "name": badge_id,
                    },
                )
            badge_name = badge_info.get(const.DATA_BADGE_NAME, badge_id)
            kid_name = kid_info.get(const.DATA_KID_NAME, kid_id)
            # Remove the badge from the kid's badges_earned.
            badges_earned = kid_info.setdefault(const.DATA_KID_BADGES_EARNED, {})
            if badge_id in badges_earned:
                found = True
                const.LOGGER.warning(
                    "WARNING: Remove Awarded Badges - Removing badge '%s' from kid '%s'.",
                    badge_name,
                    kid_name,
                )
                del badges_earned[badge_id]

            # Remove the kid from the badge earned_by list.
            earned_by_list = badge_info.get(const.DATA_BADGE_EARNED_BY, [])
            if kid_id in earned_by_list:
                earned_by_list.remove(kid_id)

            if not found:
                const.LOGGER.warning(
                    "WARNING: Remove Awarded Badges - Badge '%s' ('%s') not found in kid '%s' ('%s') data.",
                    badge_id,
                    badge_name,
                    kid_id,
                    kid_name,
                )

        elif badge_id:
            # Remove a specific awarded badge for all kids.
            badge_info = self.badges_data.get(badge_id)
            if not badge_info:
                const.LOGGER.warning(
                    "WARNING: Remove Awarded Badges - Badge ID '%s' not found in badges data.",
                    badge_id,
                )
            else:
                badge_name = badge_info.get(const.DATA_BADGE_NAME, badge_id)
                for kid_id, kid_info in self.kids_data.items():
                    kid_name = kid_info.get(const.DATA_KID_NAME, "Unknown Kid")
                    # Remove the badge from the kid's badges_earned.
                    badges_earned = kid_info.setdefault(
                        const.DATA_KID_BADGES_EARNED, {}
                    )
                    if badge_id in badges_earned:
                        found = True
                        const.LOGGER.warning(
                            "WARNING: Remove Awarded Badges - Removing badge '%s' from kid '%s'.",
                            badge_name,
                            kid_name,
                        )
                        del badges_earned[badge_id]

                    # Remove the kid from the badge earned_by list.
                    earned_by_list = badge_info.get(const.DATA_BADGE_EARNED_BY, [])
                    if kid_id in earned_by_list:
                        earned_by_list.remove(kid_id)

                # All kids should already be removed from the badge earned_by list, but in case of orphans, clear those fields
                if const.DATA_BADGE_EARNED_BY in badge_info:
                    badge_info[const.DATA_BADGE_EARNED_BY].clear()

                if not found:
                    const.LOGGER.warning(
                        "WARNING: Remove Awarded Badges - Badge '%s' ('%s') not found in any kid's data.",
                        badge_id,
                        badge_name,
                    )

        elif kid_id:
            # Remove all awarded badges for a specific kid.
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Remove Awarded Badges - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                    translation_placeholders={
                        "entity_type": const.LABEL_KID,
                        "name": kid_id,
                    },
                )
            kid_name = kid_info.get(const.DATA_KID_NAME, "Unknown Kid")
            for badge_id, badge_info in self.badges_data.items():
                badge_name = badge_info.get(const.DATA_BADGE_NAME)
                earned_by_list = badge_info.get(const.DATA_BADGE_EARNED_BY, [])
                badges_earned = kid_info.setdefault(const.DATA_KID_BADGES_EARNED, {})
                if kid_id in earned_by_list:
                    found = True
                    # Remove kid from badge earned_by list
                    earned_by_list.remove(kid_id)
                    # Remove the badge from the kid's badges_earned.
                    if badge_id in badges_earned:
                        found = True
                        const.LOGGER.warning(
                            "WARNING: Remove Awarded Badges - Removing badge '%s' from kid '%s'.",
                            badge_name,
                            kid_name,
                        )
                        del badges_earned[badge_id]

            # All badges should already be removed from the kid's badges list, but in case of orphans, clear those fields
            if const.DATA_KID_BADGES_EARNED in kid_info:
                kid_info[const.DATA_KID_BADGES_EARNED].clear()
            # CLS Should also clear all extra fields for all badge types later

            if not found:
                const.LOGGER.warning(
                    "WARNING: Remove Awarded Badges - No badge found for kid '%s'.",
                    kid_info.get(const.DATA_KID_NAME, kid_id),
                )

        else:
            # Remove Awarded Badges for all kids.
            const.LOGGER.info(
                "INFO: Remove Awarded Badges - Removing all awarded badges for all kids."
            )
            for badge_id, badge_info in self.badges_data.items():
                badge_name = badge_info.get(const.DATA_BADGE_NAME)
                for kid_id, kid_info in self.kids_data.items():
                    kid_name = kid_info.get(const.DATA_KID_NAME, "Unknown Kid")
                    # Remove the badge from the kid's badges_earned.
                    badges_earned = kid_info.setdefault(
                        const.DATA_KID_BADGES_EARNED, {}
                    )
                    if badge_id in badges_earned:
                        found = True
                        const.LOGGER.warning(
                            "WARNING: Remove Awarded Badges - Removing badge '%s' from kid '%s'.",
                            badge_name,
                            kid_name,
                        )
                        del badges_earned[badge_id]

                    # Remove the kid from the badge earned_by list.
                    earned_by_list = badge_info.get(const.DATA_BADGE_EARNED_BY, [])
                    if kid_id in earned_by_list:
                        earned_by_list.remove(kid_id)

                    # All badges should already be removed from the kid's badges list, but in case of orphans, clear those fields
                    if const.DATA_KID_BADGES_EARNED in kid_info:
                        kid_info[const.DATA_KID_BADGES_EARNED].clear()
                    # CLS Should also clear all extra fields for all badge types later

                # All kids should already be removed from the badge earned_by list, but in case of orphans, clear those fields
                if const.DATA_BADGE_EARNED_BY in badge_info:
                    badge_info[const.DATA_BADGE_EARNED_BY].clear()

            if not found:
                const.LOGGER.warning(
                    "WARNING: Remove Awarded Badges - No awarded badges found in any kid's data."
                )

        const.LOGGER.info(
            "INFO: Remove Awarded Badges - Badge removal process completed."
        )
        self._persist()
        self.async_set_updated_data(self._data)

    def _recalculate_all_badges(self):
        """Global re-check of all badges for all kids."""
        const.LOGGER.info("Recalculate All Badges - Starting Recalculation")

        # Re-evaluate badge criteria for each kid.
        for kid_id in self.kids_data.keys():
            self._check_badges_for_kid(kid_id)

        self._persist()
        self.async_set_updated_data(self._data)
        const.LOGGER.info("Recalculate All Badges - Recalculation Complete")

    def _get_cumulative_badge_progress(self, kid_id: str) -> dict[str, Any]:
        """
        Builds and returns the full cumulative badge progress block for a kid.
        Uses badge level logic, progress tracking, and next-tier metadata.
        Does not mutate state.
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return {}

        # Make a copy of the existing progress so that we don't modify the stored data.
        stored_progress = kid_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
        ).copy()

        # Compute values from badge level logic.
        (highest_earned, next_higher, next_lower, baseline, cycle_points) = (
            self._get_cumulative_badge_levels(kid_id)
        )
        total_points = baseline + cycle_points

        # Determine which badge should be considered current.
        # If the stored status is "demoted", then set current badge to next_lower; otherwise, use highest_earned.
        current_status = stored_progress.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS,
            const.CUMULATIVE_BADGE_STATE_ACTIVE,
        )
        if current_status == const.CUMULATIVE_BADGE_STATE_DEMOTED:
            current_badge_info = next_lower
        else:
            current_badge_info = highest_earned

        # Build a new dictionary with computed values.
        computed_progress = {
            # Maintenance tracking (we'll merge stored values below)
            # For keys like status we prefer the stored value, or the default.
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS: stored_progress.get(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS,
                const.CUMULATIVE_BADGE_STATE_ACTIVE,
            ),
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE: baseline,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS: cycle_points,
            # Highest earned badge
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_BADGE_ID: highest_earned.get(
                const.DATA_BADGE_INTERNAL_ID
            )
            if highest_earned
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_BADGE_NAME: highest_earned.get(
                const.DATA_BADGE_NAME
            )
            if highest_earned
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_THRESHOLD: float(
                highest_earned.get(const.DATA_BADGE_TARGET, {}).get(
                    const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                )
            )
            if highest_earned
            else None,
            # Current badge in effect
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID: current_badge_info.get(
                const.DATA_BADGE_INTERNAL_ID
            )
            if current_badge_info
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_NAME: current_badge_info.get(
                const.DATA_BADGE_NAME
            )
            if current_badge_info
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_THRESHOLD: float(
                current_badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                    const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                )
            )
            if current_badge_info
            else None,
            # Next higher tier
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_BADGE_ID: next_higher.get(
                const.DATA_BADGE_INTERNAL_ID
            )
            if next_higher
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_BADGE_NAME: next_higher.get(
                const.DATA_BADGE_NAME
            )
            if next_higher
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_THRESHOLD: float(
                next_higher.get(const.DATA_BADGE_TARGET, {}).get(
                    const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                )
            )
            if next_higher
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_POINTS_NEEDED: (
                max(
                    0.0,
                    float(
                        next_higher.get(const.DATA_BADGE_TARGET, {}).get(
                            const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                        )
                    )
                    - total_points,
                )
                if next_higher
                else None
            ),
            # Next lower tier
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_LOWER_BADGE_ID: next_lower.get(
                const.DATA_BADGE_INTERNAL_ID
            )
            if next_lower
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_LOWER_BADGE_NAME: next_lower.get(
                const.DATA_BADGE_NAME
            )
            if next_lower
            else None,
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_LOWER_THRESHOLD: float(
                next_lower.get(const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0)
            )
            if next_lower
            else None,
        }

        # Merge the computed values over the stored progress.
        stored_progress.update(computed_progress)

        # Return the merged dictionary without modifying the underlying stored data.
        return stored_progress

    def _manage_badge_maintenance(self, kid_id: str) -> None:
        """
        Manages badge maintenance for a kid:
        - Initializes badge progress data for badges that don't have it yet
        - Checks if badges have reached their end dates
        - Resets progress for badges that have passed their end_date
        - Updates badge states based on the reset
        - Sets up new cycle dates for recurring badges
        - Ensures all required fields exist in badge progress data
        - Synchronizes badge configuration changes with progress data
        """
        # ===============================================================
        # SECTION 1: INITIALIZATION - Basic setup and validation
        # ===============================================================
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # First, ensure all badge progress entries have all required fields
        badge_progress = kid_info.setdefault(const.DATA_KID_BADGE_PROGRESS, {})
        today_local_iso = kh.get_today_local_iso()

        # ===============================================================
        # SECTION 2: BADGE INITIALIZATION & SYNC - Create or update badge progress data
        # ===============================================================
        self._sync_badge_progress_for_kid(kid_id)

        # ===============================================================
        # SECTION 3: BADGE RESET CYCLE - Manage recurring badges that reached end date
        # ===============================================================
        # Now perform badge reset maintenance
        for badge_id, progress in list(badge_progress.items()):
            badge_info = self.badges_data.get(badge_id)
            if not badge_info:
                continue

            recurring_frequency = progress.get(
                const.DATA_KID_BADGE_PROGRESS_RECURRING_FREQUENCY
            )

            # ---------------------------------------------------------------
            # Check if badge has reached its end date
            # ---------------------------------------------------------------
            # Kid badge progress end date should always be populated for recurring badges.
            # If the user does not set a date, it will default to today.
            end_date_iso = progress.get(
                const.DATA_KID_BADGE_PROGRESS_END_DATE, today_local_iso
            )
            if not end_date_iso or today_local_iso <= end_date_iso:
                continue

            # --- Apply penalties if badge was NOT earned by end date, and not already applied ---
            if not progress.get(
                const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET, False
            ) and not progress.get(
                const.DATA_KID_BADGE_PROGRESS_PENALTY_APPLIED, False
            ):
                # Mark the penalty as applied to avoid reapplying it
                progress[const.DATA_KID_BADGE_PROGRESS_PENALTY_APPLIED] = True
                award_data = badge_info.get(const.DATA_BADGE_AWARDS, {})
                award_items = award_data.get(const.DATA_BADGE_AWARDS_AWARD_ITEMS, [])
                _, to_penalize = self.process_award_items(
                    award_items,
                    self.rewards_data,
                    self.bonuses_data,
                    self.penalties_data,
                )
                for penalty_id in to_penalize:
                    if penalty_id in self.penalties_data:
                        self.apply_penalty("system", kid_id, penalty_id)
                        const.LOGGER.info(
                            "INFO: Penalty Applied - Badge '%s' not earned by kid '%s'. Penalty '%s' applied.",
                            badge_info.get(const.DATA_BADGE_NAME, badge_id),
                            kid_info.get(const.DATA_KID_NAME, kid_id),
                            self.penalties_data[penalty_id].get(
                                const.DATA_PENALTY_NAME, penalty_id
                            ),
                        )

            # Now skip further reset logic if not recurring
            if recurring_frequency == const.FREQUENCY_NONE:
                continue

            # Debug: Log when the reset logic is triggered for this badge
            const.LOGGER.debug(
                "DEBUG: Badge Reset Triggered - Badge '%s' for kid '%s': today_local_iso=%s, end_date_iso=%s (reset logic will run)",
                badge_info.get(const.DATA_BADGE_NAME, badge_id),
                kid_info.get(const.DATA_KID_NAME, kid_id),
                today_local_iso,
                end_date_iso,
            )

            # Increment the cycle count for this badge
            progress[const.DATA_KID_BADGE_PROGRESS_CYCLE_COUNT] = (
                progress.get(const.DATA_KID_BADGE_PROGRESS_CYCLE_COUNT, 0) + 1
            )

            # ---------------------------------------------------------------
            # Calculate new dates for next badge cycle
            # ---------------------------------------------------------------
            # Get reset schedule from badge configuration
            reset_schedule = badge_info.get(const.DATA_BADGE_RESET_SCHEDULE, {})
            # Use the end date from the badge first, but if that isn't available, use the badge progress
            # from kid data which should always be populated for a recurring badge.
            prior_end_date_iso = badge_info.get(
                const.DATA_BADGE_RESET_SCHEDULE_END_DATE, end_date_iso
            )

            # The following require special handling because resets will not happen until after the end date passes
            # Since the scheduling functions will always look for a future date, it would end up with an end date
            # for tomorrow (2 days) instead of just rescheduling the end date by 1 day.
            is_daily = recurring_frequency == const.FREQUENCY_DAILY
            is_custom_1_day = (
                recurring_frequency == const.FREQUENCY_CUSTOM
                and reset_schedule.get(const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL)
                == 1
                and reset_schedule.get(
                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT
                )
                == const.TIME_UNIT_DAYS
            )

            if is_daily or is_custom_1_day:
                # Use PERIOD_DAY_END to set end date to end of today - See detail above.
                new_end_date_iso = kh.get_next_scheduled_datetime(
                    prior_end_date_iso,
                    interval_type=const.PERIOD_DAY_END,
                    require_future=True,
                    return_type=const.HELPER_RETURN_ISO_DATE,
                )

            # Calculate new end date based on recurring frequency
            elif recurring_frequency == const.FREQUENCY_CUSTOM:
                # Handle custom frequency
                custom_interval = reset_schedule.get(
                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL
                )
                custom_interval_unit = reset_schedule.get(
                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT
                )

                if custom_interval and custom_interval_unit:
                    new_end_date_iso = kh.adjust_datetime_by_interval(
                        prior_end_date_iso,
                        interval_unit=custom_interval_unit,
                        delta=custom_interval,
                        require_future=True,
                        return_type=const.HELPER_RETURN_ISO_DATE,
                    )
                else:
                    # Default fallback to weekly
                    new_end_date_iso = kh.adjust_datetime_by_interval(
                        prior_end_date_iso,
                        interval_unit=const.TIME_UNIT_WEEKS,
                        delta=1,
                        require_future=True,
                        return_type=const.HELPER_RETURN_ISO_DATE,
                    )
            else:
                # Use standard frequency helper
                new_end_date_iso = kh.get_next_scheduled_datetime(
                    prior_end_date_iso,
                    interval_type=recurring_frequency,
                    require_future=True,
                    return_type=const.HELPER_RETURN_ISO_DATE,
                )

            # ---------------------------------------------------------------
            # Calculate new start date based on badge type and previous cycle
            # ---------------------------------------------------------------
            # If there was no previous start date, don't set one (immediately effective)
            # If there was a previous start date, calculate the new one based on the duration
            existing_start_date_iso = progress.get(
                const.DATA_KID_BADGE_PROGRESS_START_DATE
            )

            if existing_start_date_iso:
                try:
                    # Handle special case where start and end dates are the same
                    if existing_start_date_iso == end_date_iso:
                        # For badges where start date equals end date (like special occasions)
                        # set the new start date equal to the new end date
                        new_start_date_iso = new_end_date_iso
                    else:
                        # Convert ISO dates to datetime objects
                        start_dt_utc = kh.parse_datetime_to_utc(existing_start_date_iso)
                        end_dt_utc = kh.parse_datetime_to_utc(end_date_iso)

                        if start_dt_utc and end_dt_utc:
                            # Calculate duration in days
                            duration = (end_dt_utc - start_dt_utc).days

                            # Set new start date by subtracting the same duration from new end date
                            new_start_date_iso = str(
                                kh.adjust_datetime_by_interval(
                                    new_end_date_iso,
                                    interval_unit=const.TIME_UNIT_DAYS,
                                    delta=-duration,
                                    require_future=False,  # Allow past dates for calculation
                                    return_type=const.HELPER_RETURN_ISO_DATE,
                                )
                            )

                            # If new start date is in the past, use today
                            if new_start_date_iso < today_local_iso:
                                new_start_date_iso = today_local_iso
                        else:
                            # Fallback to today if date parsing fails
                            new_start_date_iso = today_local_iso
                except (ValueError, TypeError, AttributeError):
                    # Fallback to today if calculation fails
                    new_start_date_iso = today_local_iso
            else:
                # No existing start date - keep it unset (None)
                new_start_date_iso = None

            # ---------------------------------------------------------------
            # Reset badge progress for the new cycle
            # ---------------------------------------------------------------

            # Update badge state to active_cycle (working on next iteration)
            progress[const.DATA_KID_BADGE_PROGRESS_STATUS] = (
                const.BADGE_STATE_ACTIVE_CYCLE
            )
            progress[const.DATA_KID_BADGE_PROGRESS_START_DATE] = new_start_date_iso
            progress[const.DATA_KID_BADGE_PROGRESS_END_DATE] = new_end_date_iso

            # Reset fenalty applied flag
            progress[const.DATA_KID_BADGE_PROGRESS_PENALTY_APPLIED] = False

            # Reset all known progress tracking fields if present
            reset_fields = [
                (const.DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT, 0.0),
                (const.DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT, 0),
                (const.DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT, 0),
                (const.DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED, {}),
                (const.DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED, {}),
            ]
            for field, default in reset_fields:
                if field in progress:
                    progress[field] = default

            const.LOGGER.debug(
                "DEBUG: Badge Maintenance - Reset badge '%s' for kid '%s'. New cycle: %s to %s",
                badge_info.get(const.DATA_BADGE_NAME, badge_id),
                kid_info.get(const.DATA_KID_NAME, kid_id),
                new_start_date_iso if new_start_date_iso else "immediate",
                new_end_date_iso,
            )

            const.LOGGER.debug(
                "DEBUG: Badge Maintenance - Reset badge '%s' for kid '%s'. New cycle: %s to %s",
                badge_info.get(const.DATA_BADGE_NAME, badge_id),
                kid_info.get(const.DATA_KID_NAME, kid_id),
                new_start_date_iso if new_start_date_iso else "immediate",
                new_end_date_iso,
            )

        # ===============================================================
        # SECTION 4: FINALIZATION - Save updates back to kid data
        # ===============================================================
        # Save the updated progress back to the kid data
        kid_info[const.DATA_KID_BADGE_PROGRESS] = badge_progress

        self._persist()
        self.async_set_updated_data(self._data)

    def _sync_badge_progress_for_kid(self, kid_id: str) -> None:
        """Sync badge progress for a specific kid."""
        # Initialize badge progress for any badges that don't have progress data yet

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # Phase 4: Clean up badge_progress for badges no longer assigned to this kid
        if const.DATA_KID_BADGE_PROGRESS in kid_info:
            badges_to_remove = []
            for progress_badge_id in kid_info[const.DATA_KID_BADGE_PROGRESS]:
                badge_info = self.badges_data.get(progress_badge_id)
                # Remove if badge deleted OR kid not in assigned_to list
                if not badge_info or kid_id not in badge_info.get(
                    const.DATA_BADGE_ASSIGNED_TO, []
                ):
                    badges_to_remove.append(progress_badge_id)

            for badge_id in badges_to_remove:
                del kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id]
                const.LOGGER.debug(
                    "DEBUG: Removed badge_progress for badge '%s' from kid '%s' (unassigned or deleted)",
                    badge_id,
                    kid_info.get(const.DATA_KID_NAME, kid_id),
                )

        for badge_id, badge_info in self.badges_data.items():
            # Feature Change v4.2: Badges now require explicit assignment.
            # Empty assigned_to means badge is not assigned to any kid.
            assigned_to_list = badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
            is_assigned_to = kid_id in assigned_to_list
            if not is_assigned_to:
                continue

            # Skip cumulative badges (handled separately)
            if badge_info.get(const.DATA_BADGE_TYPE) == const.BADGE_TYPE_CUMULATIVE:
                continue

            # Initialize progress structure if it doesn't exist
            if const.DATA_KID_BADGE_PROGRESS not in kid_info:
                kid_info[const.DATA_KID_BADGE_PROGRESS] = {}

            badge_type = badge_info.get(const.DATA_BADGE_TYPE)

            # --- Set flags based on badge type ---
            has_target = badge_type in const.INCLUDE_TARGET_BADGE_TYPES
            has_special_occasion = (
                badge_type in const.INCLUDE_SPECIAL_OCCASION_BADGE_TYPES
            )
            has_achievement_linked = (
                badge_type in const.INCLUDE_ACHIEVEMENT_LINKED_BADGE_TYPES
            )
            has_challenge_linked = (
                badge_type in const.INCLUDE_CHALLENGE_LINKED_BADGE_TYPES
            )
            has_tracked_chores = badge_type in const.INCLUDE_TRACKED_CHORES_BADGE_TYPES
            has_assigned_to = badge_type in const.INCLUDE_ASSIGNED_TO_BADGE_TYPES
            has_reset_schedule = badge_type in const.INCLUDE_RESET_SCHEDULE_BADGE_TYPES

            # ===============================================================
            # SECTION 1: NEW BADGE SETUP - Create initial progress structure
            # ===============================================================
            if badge_id not in kid_info[const.DATA_KID_BADGE_PROGRESS]:
                # Get badge details

                # --- Common fields ---
                progress = {
                    const.DATA_KID_BADGE_PROGRESS_NAME: badge_info.get(
                        const.DATA_BADGE_NAME
                    ),
                    const.DATA_KID_BADGE_PROGRESS_TYPE: badge_type,
                    const.DATA_KID_BADGE_PROGRESS_STATUS: const.BADGE_STATE_IN_PROGRESS,
                }

                # --- Target fields ---
                if has_target:
                    target_type = badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                        const.DATA_BADGE_TARGET_TYPE
                    )
                    threshold_value = float(
                        badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                            const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                        )
                    )
                    progress[const.DATA_KID_BADGE_PROGRESS_TARGET_TYPE] = target_type
                    progress[const.DATA_KID_BADGE_PROGRESS_TARGET_THRESHOLD_VALUE] = (
                        threshold_value
                    )

                    # Initialize all possible progress fields to their defaults if not present
                    progress.setdefault(
                        const.DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT, 0.0
                    )
                    progress.setdefault(
                        const.DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT, 0
                    )
                    progress.setdefault(
                        const.DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT, 0
                    )
                    progress.setdefault(
                        const.DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED, {}
                    )
                    progress.setdefault(
                        const.DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED, {}
                    )

                # --- Achievement Linked fields ---
                if has_achievement_linked:
                    # Store the associated achievement ID if present
                    achievement_id = badge_info.get(
                        const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT
                    )
                    if achievement_id:
                        progress[const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT] = (
                            achievement_id
                        )

                # --- Challenge Linked fields ---
                if has_challenge_linked:
                    # Store the associated challenge ID if present
                    challenge_id = badge_info.get(const.DATA_BADGE_ASSOCIATED_CHALLENGE)
                    if challenge_id:
                        progress[const.DATA_BADGE_ASSOCIATED_CHALLENGE] = challenge_id

                # --- Tracked Chores fields ---
                if has_tracked_chores and not has_special_occasion:
                    progress[const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES] = (
                        self._get_badge_in_scope_chores_list(badge_info, kid_id)
                    )

                # --- Assigned To fields ---
                if has_assigned_to:
                    assigned_to = badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
                    progress[const.DATA_BADGE_ASSIGNED_TO] = assigned_to

                # --- Awards fields --- Not required for now
                # if has_awards:
                #    awards = badge_info.get(const.DATA_BADGE_AWARDS, {})
                #    progress[const.DATA_BADGE_AWARDS] = awards

                # --- Reset Schedule fields ---
                if has_reset_schedule:
                    reset_schedule = badge_info.get(const.DATA_BADGE_RESET_SCHEDULE, {})
                    recurring_frequency = reset_schedule.get(
                        const.DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY,
                        const.FREQUENCY_NONE,
                    )
                    start_date_iso = reset_schedule.get(
                        const.DATA_BADGE_RESET_SCHEDULE_START_DATE
                    )
                    end_date_iso = reset_schedule.get(
                        const.DATA_BADGE_RESET_SCHEDULE_END_DATE
                    )
                    progress[const.DATA_KID_BADGE_PROGRESS_RECURRING_FREQUENCY] = (
                        recurring_frequency
                    )

                    # Set initial schedule if there is a frequency and no end date
                    if recurring_frequency != const.FREQUENCY_NONE:
                        if end_date_iso:
                            progress[const.DATA_KID_BADGE_PROGRESS_START_DATE] = (
                                start_date_iso
                            )
                            progress[const.DATA_KID_BADGE_PROGRESS_END_DATE] = (
                                end_date_iso
                            )
                            progress[const.DATA_KID_BADGE_PROGRESS_CYCLE_COUNT] = (
                                const.DEFAULT_ZERO
                            )
                        else:
                            # ---------------------------------------------------------------
                            # Calculate initial end date from today since there is no end date
                            # ---------------------------------------------------------------
                            today_local_iso = kh.get_today_local_iso()
                            is_daily = recurring_frequency == const.FREQUENCY_DAILY
                            is_custom_1_day = (
                                recurring_frequency == const.FREQUENCY_CUSTOM
                                and reset_schedule.get(
                                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL
                                )
                                == 1
                                and reset_schedule.get(
                                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT
                                )
                                == const.TIME_UNIT_DAYS
                            )

                            if is_daily or is_custom_1_day:
                                # This is special case where if you set a daily badge, you don't want it to get scheduled with
                                # tomorrow as the end date.
                                new_end_date_iso = today_local_iso
                            elif recurring_frequency == const.FREQUENCY_CUSTOM:
                                # Handle other custom frequencies
                                custom_interval = reset_schedule.get(
                                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL
                                )
                                custom_interval_unit = reset_schedule.get(
                                    const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT
                                )
                                if custom_interval and custom_interval_unit:
                                    new_end_date_iso = kh.adjust_datetime_by_interval(
                                        today_local_iso,
                                        interval_unit=custom_interval_unit,
                                        delta=custom_interval,
                                        require_future=True,
                                        return_type=const.HELPER_RETURN_ISO_DATE,
                                    )
                                else:
                                    # Default fallback to weekly
                                    new_end_date_iso = kh.adjust_datetime_by_interval(
                                        today_local_iso,
                                        interval_unit=const.TIME_UNIT_WEEKS,
                                        delta=1,
                                        require_future=True,
                                        return_type=const.HELPER_RETURN_ISO_DATE,
                                    )
                            else:
                                # Use standard frequency helper
                                new_end_date_iso = kh.get_next_scheduled_datetime(
                                    today_local_iso,
                                    interval_type=recurring_frequency,
                                    require_future=True,
                                    return_type=const.HELPER_RETURN_ISO_DATE,
                                )

                            progress[const.DATA_KID_BADGE_PROGRESS_START_DATE] = (
                                start_date_iso
                            )
                            progress[const.DATA_KID_BADGE_PROGRESS_END_DATE] = (
                                new_end_date_iso
                            )
                            progress[const.DATA_KID_BADGE_PROGRESS_CYCLE_COUNT] = (
                                const.DEFAULT_ZERO
                            )

                            # Set penalty applied to False
                            # This is to ensure that if the badge is not earned, the penalty will be applied
                            progress[const.DATA_KID_BADGE_PROGRESS_PENALTY_APPLIED] = (
                                False
                            )

                # --- Special Occasion fields ---
                if has_special_occasion:
                    # Add occasion type if present
                    occasion_type = badge_info.get(const.DATA_BADGE_OCCASION_TYPE)
                    if occasion_type:
                        progress[const.DATA_BADGE_OCCASION_TYPE] = occasion_type

                # Store the progress data
                kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id] = progress

            # ===============================================================
            # SECTION 2: BADGE SYNC - Update existing badge progress data
            # ===============================================================
            else:
                # --- Remove badge progress if badge is no longer available or not assigned to this kid ---
                if badge_id not in self.badges_data or (
                    badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
                    and kid_id not in badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
                ):
                    if badge_id in kid_info[const.DATA_KID_BADGE_PROGRESS]:
                        del kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id]
                        const.LOGGER.info(
                            "INFO: Badge Maintenance - Removed badge progress for badge '%s' from kid '%s' (badge deleted or unassigned).",
                            badge_id,
                            kid_info.get(const.DATA_KID_NAME, kid_id),
                        )
                    continue

                # The badge already exists in progress data - sync configuration fields
                progress = kid_info[const.DATA_KID_BADGE_PROGRESS][badge_id]

                # --- Common fields ---
                progress[const.DATA_KID_BADGE_PROGRESS_NAME] = badge_info.get(
                    const.DATA_BADGE_NAME, "Unknown Badge"
                )
                progress[const.DATA_KID_BADGE_PROGRESS_TYPE] = badge_type

                # --- Target fields ---
                if has_target:
                    target_type = badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                        const.DATA_BADGE_TARGET_TYPE,
                        const.BADGE_TARGET_THRESHOLD_TYPE_POINTS,
                    )
                    progress[const.DATA_KID_BADGE_PROGRESS_TARGET_TYPE] = target_type

                    progress[const.DATA_KID_BADGE_PROGRESS_TARGET_THRESHOLD_VALUE] = (
                        badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                            const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                        )
                    )

                # --- Special Occasion fields ---
                if has_special_occasion:
                    # Add occasion type if present
                    occasion_type = badge_info.get(const.DATA_BADGE_OCCASION_TYPE)
                    if occasion_type:
                        progress[const.DATA_BADGE_OCCASION_TYPE] = occasion_type

                # --- Achievement Linked fields ---
                if has_achievement_linked:
                    achievement_id = badge_info.get(
                        const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT
                    )
                    if achievement_id:
                        progress[const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT] = (
                            achievement_id
                        )

                # --- Challenge Linked fields ---
                if has_challenge_linked:
                    challenge_id = badge_info.get(const.DATA_BADGE_ASSOCIATED_CHALLENGE)
                    if challenge_id:
                        progress[const.DATA_BADGE_ASSOCIATED_CHALLENGE] = challenge_id

                # --- Tracked Chores fields ---
                if has_tracked_chores and not has_special_occasion:
                    progress[const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES] = (
                        self._get_badge_in_scope_chores_list(badge_info, kid_id)
                    )

                # --- Assigned To fields ---
                if has_assigned_to:
                    assigned_to = badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
                    progress[const.DATA_BADGE_ASSIGNED_TO] = assigned_to

                # --- Awards fields --- Not required for now
                # if has_awards:
                #    awards = badge_info.get(const.DATA_BADGE_AWARDS, {})
                #    progress[const.DATA_BADGE_AWARDS] = awards

                # --- Reset Schedule fields ---
                if has_reset_schedule:
                    reset_schedule = badge_info.get(const.DATA_BADGE_RESET_SCHEDULE, {})
                    recurring_frequency = reset_schedule.get(
                        const.DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY,
                        const.FREQUENCY_NONE,
                    )
                    start_date_iso = reset_schedule.get(
                        const.DATA_BADGE_RESET_SCHEDULE_START_DATE
                    )
                    end_date_iso = reset_schedule.get(
                        const.DATA_BADGE_RESET_SCHEDULE_END_DATE
                    )
                    progress[const.DATA_KID_BADGE_PROGRESS_RECURRING_FREQUENCY] = (
                        recurring_frequency
                    )
                    # Only update start and end dates if they have values
                    if start_date_iso:
                        progress[const.DATA_KID_BADGE_PROGRESS_START_DATE] = (
                            start_date_iso
                        )
                    if end_date_iso:
                        progress[const.DATA_KID_BADGE_PROGRESS_END_DATE] = end_date_iso

    def _manage_cumulative_badge_maintenance(self, kid_id: str) -> None:
        """
        Manages cumulative badge maintenance for a kid:
        - Evaluates whether the maintenance or grace period has ended.
        - Updates badge status (active, grace, or demoted) based on cycle points.
        - Resets cycle points and updates maintenance windows if needed.
        - Updates the current badge information based on maintenance outcome.
        """

        # Retrieve kid-specific information from the kids_data dictionary.
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # Retrieve the cumulative badge progress data for the kid.
        cumulative_badge_progress = kid_info.setdefault(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
        )

        # DEBUG: Log starting state for the kid.
        kid_name = kid_info.get(const.DATA_KID_NAME, kid_id)
        const.LOGGER.debug(
            "DEBUG: Manage Cumulative Badge Maintenance - Kid=%s, Initial Status=%s, Cycle Points=%.2f",
            kid_name,
            cumulative_badge_progress.get(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS, "active"
            ),
            float(
                cumulative_badge_progress.get(
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS, 0
                )
            ),
        )

        # Extract current maintenance and grace end dates, status, and accumulated cycle points.
        end_date_iso = cumulative_badge_progress.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE
        )
        grace_date_iso = cumulative_badge_progress.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE
        )
        status = cumulative_badge_progress.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS,
            const.CUMULATIVE_BADGE_STATE_ACTIVE,
        )
        cycle_points = float(
            cumulative_badge_progress.get(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS, 0
            )
        )

        # Get today's date in ISO format using the local timezone.
        today_local_iso = kh.get_today_local_iso()

        # Get badge level information: highest earned badge, next lower badge, baseline, etc.
        highest_earned, _, next_lower, baseline, _ = self._get_cumulative_badge_levels(
            kid_id
        )
        if not highest_earned:
            return

        # Determine the maintenance threshold, reset type, grace period duration, and whether reset is enabled.
        maintenance_required = float(
            highest_earned.get(const.DATA_BADGE_TARGET, {}).get(
                const.DATA_BADGE_MAINTENANCE_RULES, const.DEFAULT_ZERO
            )
        )
        reset_schedule = highest_earned.get(const.DATA_BADGE_RESET_SCHEDULE, {})
        frequency = reset_schedule.get(
            const.DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY
        )
        grace_days = int(
            reset_schedule.get(
                const.DATA_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS, const.DEFAULT_ZERO
            )
        )
        reset_enabled = frequency is not None and frequency != const.FREQUENCY_NONE

        # DEBUG: Log the key parameters derived from today's date and the highest earned badge.
        const.LOGGER.debug(
            "DEBUG: Manage Cumulative Badge Maintenance - today_local=%s, "
            "highest_earned=%s, maintenance_required=%.2f, reset_type=%s, "
            "grace_days=%d, reset_enabled=%s",
            today_local_iso,
            highest_earned.get(const.DATA_BADGE_NAME),
            maintenance_required,
            frequency,
            grace_days,
            reset_enabled,
        )

        # If the badge is not recurring (reset not enabled):
        # clear any existing maintenance and grace dates and exit the function.
        if not reset_enabled:
            cumulative_badge_progress.update(
                {
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE: None,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE: None,
                }
            )
            self.kids_data[kid_id][const.DATA_KID_CUMULATIVE_BADGE_PROGRESS] = (
                cumulative_badge_progress
            )
            self._persist()
            self.async_set_updated_data(self._data)
            return

        award_success = False
        demotion_required = False

        # Check if the maintenance period (or grace period) has ended based on the current status.
        if (
            status
            in (
                const.CUMULATIVE_BADGE_STATE_ACTIVE,
                const.CUMULATIVE_BADGE_STATE_DEMOTED,
            )
            and end_date_iso
            and today_local_iso >= end_date_iso
        ):
            # If cycle points meet or exceed the required maintenance threshold, the badge is maintained.
            if cycle_points >= maintenance_required:
                award_success = True
            # If it is already past the grace date, then a demotion is required (edge case)
            elif grace_date_iso and today_local_iso >= grace_date_iso:
                demotion_required = True
            # Otherwise, if a grace period is allowed, move the badge status into the grace state.
            elif grace_days > const.DEFAULT_ZERO:
                cumulative_badge_progress[
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS
                ] = const.CUMULATIVE_BADGE_STATE_GRACE
            # If neither condition is met, then a demotion is required.
            else:
                demotion_required = True

        elif status == const.CUMULATIVE_BADGE_STATE_GRACE:
            # While in the grace period, if the required cycle points are met, maintain the badge.
            if cycle_points >= maintenance_required:
                award_success = True
            # If the grace period has expired, then a demotion is required.
            elif grace_date_iso and today_local_iso >= grace_date_iso:
                demotion_required = True

        # Determine the frequency and custom fields before proceeding
        reset_schedule = highest_earned.get(const.DATA_BADGE_RESET_SCHEDULE, {})
        frequency = reset_schedule.get(
            const.DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
        )
        custom_interval = reset_schedule.get(
            const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL
        )
        custom_interval_unit = reset_schedule.get(
            const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT
        )
        # Use reference_dt if available; otherwise, default to today's date
        base_date_iso = reset_schedule.get(
            const.DATA_BADGE_RESET_SCHEDULE_END_DATE, today_local_iso
        )

        # Fallback to today's date if reference_dt is None
        if not base_date_iso:
            base_date_iso = today_local_iso

        # If the base date is in the future, use it as the reference date so the next schedule is in the future of that date.
        # As an example if on June 5th I create a badge and give it an end date of July 7th and chooose frequency of Period End,
        # then the expectation would be a next scheduled date of Sept 30th, not June 30th.
        reference_datetime_iso = (
            base_date_iso if base_date_iso > today_local_iso else today_local_iso
        )

        # Initialize the variables for the next maintenance end date and grace end date
        next_end = None
        next_grace = None

        # First-Time Assignment:
        # If the badge is reset-enabled but no maintenance end date is set (i.e., first-time award),
        # then calculate and set the maintenance and grace dates.
        is_first_time = reset_enabled and not cumulative_badge_progress.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE
        )

        # Check if the maintenance period or grace period has ended
        if award_success or demotion_required or is_first_time:
            if frequency == const.FREQUENCY_CUSTOM:
                # If custom interval and unit are valid, calculate next_end make sure it is in the future and past the reference
                if custom_interval and custom_interval_unit:
                    next_end = kh.adjust_datetime_by_interval(
                        base_date=base_date_iso,
                        interval_unit=custom_interval_unit,  # Fix: change from custom_interval_unit to interval_unit
                        delta=custom_interval,  # Fix: change from custom_interval to delta
                        require_future=True,
                        reference_datetime=reference_datetime_iso,
                        return_type=const.HELPER_RETURN_ISO_DATE,
                    )
                else:
                    # Fallback to existing logic if custom interval/unit are invalid
                    next_end = kh.get_next_scheduled_datetime(
                        base_date_iso,
                        interval_type=frequency,
                        require_future=True,
                        reference_datetime=reference_datetime_iso,
                        return_type=const.HELPER_RETURN_ISO_DATE,
                    )
            else:
                # Default behavior for non-custom frequencies
                base_date_iso = today_local_iso
                next_end = kh.get_next_scheduled_datetime(
                    base_date_iso,
                    interval_type=frequency,
                    require_future=True,
                    reference_datetime=reference_datetime_iso,
                    return_type=const.HELPER_RETURN_ISO_DATE,
                )

            # Compute the grace period end date by adding the grace period (in days) to the maintenance end date
            next_grace = kh.adjust_datetime_by_interval(
                next_end,
                const.TIME_UNIT_DAYS,
                grace_days,
                require_future=True,
                return_type=const.HELPER_RETURN_ISO_DATE,
            )

        # If the badge maintenance requirements are met, update the badge as successfully maintained.
        if award_success:
            cumulative_badge_progress.update(
                {
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE: next_end,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE: next_grace,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS: const.CUMULATIVE_BADGE_STATE_ACTIVE,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID: highest_earned.get(
                        const.DATA_BADGE_INTERNAL_ID
                    ),
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_NAME: highest_earned.get(
                        const.DATA_BADGE_NAME
                    ),
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_THRESHOLD: highest_earned.get(
                        const.DATA_BADGE_TARGET_THRESHOLD_VALUE
                    ),
                }
            )
            # Award the badge through the helper function.
            badge_id = highest_earned.get(const.DATA_BADGE_INTERNAL_ID)
            if badge_id:
                self._award_badge(kid_id, badge_id)

        # If demotion is required due to failure to meet maintenance requirements:
        if demotion_required:
            cumulative_badge_progress.update(
                {
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS: const.CUMULATIVE_BADGE_STATE_DEMOTED,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID: next_lower.get(
                        const.DATA_BADGE_INTERNAL_ID
                    )
                    if next_lower
                    else None,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_NAME: next_lower.get(
                        const.DATA_BADGE_NAME
                    )
                    if next_lower
                    else None,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_THRESHOLD: next_lower.get(
                        const.DATA_BADGE_TARGET_THRESHOLD_VALUE
                    )
                    if next_lower
                    else None,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE: baseline
                    + cycle_points,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS: 0,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE: next_end,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE: next_grace,
                }
            )
            self._update_point_multiplier_for_kid(kid_id)

        # If is first_time, then set the end dates
        if is_first_time:
            cumulative_badge_progress.update(
                {
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE: next_end,
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE: next_grace,
                }
            )

        # Simplified final debug: show only key maintenance info.
        const.LOGGER.debug(
            "DEBUG: Manage Cumulative Badge Maintenance - Final (Kid=%s): Status=%s, End=%s, Grace=%s, CyclePts=%.2f",
            kid_name,
            cumulative_badge_progress.get(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS
            ),
            cumulative_badge_progress.get(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE
            ),
            cumulative_badge_progress.get(
                const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE
            ),
            float(
                cumulative_badge_progress.get(
                    const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS, 0
                )
            ),
        )

        # Save the updated progress and notify any listeners. The extra update here is to do a merge
        # as a precaution ensuring nothing gets lost if other keys have been changed during processign
        existing_progress = self.kids_data[kid_id].get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
        )
        existing_progress.update(cumulative_badge_progress)
        self.kids_data[kid_id][const.DATA_KID_CUMULATIVE_BADGE_PROGRESS] = (
            existing_progress
        )

        self._persist()
        self.async_set_updated_data(self._data)

    def _get_cumulative_badge_levels(
        self, kid_id: str
    ) -> tuple[Optional[dict], Optional[dict], Optional[dict], float, float]:
        """
        Determines the highest earned cumulative badge for a kid, and the next higher/lower badge tiers.

        Returns:
            - highest_earned_badge_info (dict or None)
            - next_higher_badge_info (dict or None)
            - next_lower_badge_info (dict or None)
            - baseline (float)
            - cycle_points (float)
        """

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return None, None, None, 0.0, 0.0

        progress = kid_info.get(const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {})
        baseline = round(
            float(progress.get(const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE, 0)),
            const.DATA_FLOAT_PRECISION,
        )
        cycle_points = round(
            float(
                progress.get(const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS, 0)
            ),
            const.DATA_FLOAT_PRECISION,
        )
        total_points = baseline + cycle_points

        # Get sorted list of cumulative badges (lowest to highest threshold)
        cumulative_badges = sorted(
            (
                (badge_id, badge_info)
                for badge_id, badge_info in self.badges_data.items()
                if badge_info.get(const.DATA_BADGE_TYPE) == const.BADGE_TYPE_CUMULATIVE
            ),
            key=lambda item: float(
                item[1]
                .get(const.DATA_BADGE_TARGET, {})
                .get(const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0)
            ),
        )

        if not cumulative_badges:
            # No cumulative badges exist - reset tracking values to 0
            # When a new cumulative badge is added, tracking will start fresh
            return None, None, None, 0.0, 0.0

        highest_earned = None
        next_higher = None
        next_lower = None
        previous_badge_info = None

        for badge_id, badge_info in cumulative_badges:
            threshold = float(
                badge_info.get(const.DATA_BADGE_TARGET, {}).get(
                    const.DATA_BADGE_TARGET_THRESHOLD_VALUE, 0
                )
            )

            # Set the is_assigned_to flag: True if the list is empty or if kid_id is in the assigned list
            is_assigned_to = not badge_info.get(
                const.DATA_BADGE_ASSIGNED_TO, []
            ) or kid_id in badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])

            if is_assigned_to:
                if total_points >= threshold:
                    highest_earned = badge_info
                    next_lower = previous_badge_info
                else:
                    next_higher = badge_info
                    break

                previous_badge_info = badge_info

        return highest_earned, next_higher, next_lower, baseline, cycle_points

    # -------------------------------------------------------------------------------------
    # Penalties: Apply
    # -------------------------------------------------------------------------------------

    def apply_penalty(self, parent_name: str, kid_id: str, penalty_id: str):  # pylint: disable=unused-argument
        """Apply penalty => negative points to reduce kid's points."""
        penalty_info = self.penalties_data.get(penalty_id)
        if not penalty_info:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_PENALTY,
                    "name": penalty_id,
                },
            )

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_KID,
                    "name": kid_id,
                },
            )

        penalty_pts = penalty_info.get(const.DATA_PENALTY_POINTS, const.DEFAULT_ZERO)
        self.update_kid_points(
            kid_id, delta=penalty_pts, source=const.POINTS_SOURCE_PENALTIES
        )

        # increment penalty_applies
        if penalty_id in kid_info[const.DATA_KID_PENALTY_APPLIES]:
            kid_info[const.DATA_KID_PENALTY_APPLIES][penalty_id] += 1
        else:
            kid_info[const.DATA_KID_PENALTY_APPLIES][penalty_id] = 1

        # Send a notification to the kid that a penalty was applied
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_PENALTY_ID: penalty_id}
        self.hass.async_create_task(
            self._notify_kid_translated(
                kid_id,
                title_key=const.TRANS_KEY_NOTIF_TITLE_PENALTY_APPLIED,
                message_key=const.TRANS_KEY_NOTIF_MESSAGE_PENALTY_APPLIED,
                message_data={
                    "penalty_name": penalty_info[const.DATA_PENALTY_NAME],
                    "points": penalty_pts,
                },
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------
    # Bonuses: Apply
    # -------------------------------------------------------------------------

    def apply_bonus(self, parent_name: str, kid_id: str, bonus_id: str):  # pylint: disable=unused-argument
        """Apply bonus => positive points to increase kid's points."""
        bonus_info = self.bonuses_data.get(bonus_id)
        if not bonus_info:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_BONUS,
                    "name": bonus_id,
                },
            )

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_KID,
                    "name": kid_id,
                },
            )

        bonus_pts = bonus_info.get(const.DATA_BONUS_POINTS, const.DEFAULT_ZERO)
        self.update_kid_points(
            kid_id, delta=bonus_pts, source=const.POINTS_SOURCE_BONUSES
        )

        # increment bonus_applies
        if bonus_id in kid_info[const.DATA_KID_BONUS_APPLIES]:
            kid_info[const.DATA_KID_BONUS_APPLIES][bonus_id] += 1
        else:
            kid_info[const.DATA_KID_BONUS_APPLIES][bonus_id] = 1

        # Send a notification to the kid that a bonus was applied
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_BONUS_ID: bonus_id}
        self.hass.async_create_task(
            self._notify_kid_translated(
                kid_id,
                title_key=const.TRANS_KEY_NOTIF_TITLE_BONUS_APPLIED,
                message_key=const.TRANS_KEY_NOTIF_MESSAGE_BONUS_APPLIED,
                message_data={
                    "bonus_name": bonus_info[const.DATA_BONUS_NAME],
                    "points": bonus_pts,
                },
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------
    # Achievements: Check, Award
    # -------------------------------------------------------------------------
    def _check_achievements_for_kid(self, kid_id: str):
        """Evaluate all achievement criteria for a given kid.

        For each achievement not already awarded, check its type and update progress accordingly.
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        today_local = kh.get_today_local_date()

        for achievement_id, achievement_info in self._data[
            const.DATA_ACHIEVEMENTS
        ].items():
            progress = achievement_info.setdefault(const.DATA_ACHIEVEMENT_PROGRESS, {})
            if kid_id in progress and progress[kid_id].get(
                const.DATA_ACHIEVEMENT_AWARDED, False
            ):
                continue

            ach_type = achievement_info.get(const.DATA_ACHIEVEMENT_TYPE)
            target = achievement_info.get(const.DATA_ACHIEVEMENT_TARGET_VALUE, 1)

            # For a streak achievement, update a streak counter:
            if ach_type == const.ACHIEVEMENT_TYPE_STREAK:
                progress = progress.setdefault(
                    kid_id,
                    {
                        const.DATA_KID_CURRENT_STREAK: const.DEFAULT_ZERO,
                        const.DATA_KID_LAST_STREAK_DATE: None,
                        const.DATA_ACHIEVEMENT_AWARDED: False,
                    },
                )

                self._update_streak_progress(progress, today_local)
                if progress[const.DATA_KID_CURRENT_STREAK] >= target:
                    self._award_achievement(kid_id, achievement_id)

            # For a total achievement, simply compare total completed chores:
            elif ach_type == const.ACHIEVEMENT_TYPE_TOTAL:
                # Get per–kid progress for this achievement.
                progress = achievement_info.setdefault(
                    const.DATA_ACHIEVEMENT_PROGRESS, {}
                ).setdefault(
                    kid_id,
                    {
                        const.DATA_ACHIEVEMENT_BASELINE: None,
                        const.DATA_ACHIEVEMENT_CURRENT_VALUE: const.DEFAULT_ZERO,
                        const.DATA_ACHIEVEMENT_AWARDED: False,
                    },
                )

                # Set the baseline so that we only count chores done after deployment.
                if (
                    const.DATA_ACHIEVEMENT_BASELINE not in progress
                    or progress[const.DATA_ACHIEVEMENT_BASELINE] is None
                ):
                    chore_stats = kid_info.get(const.DATA_KID_CHORE_STATS, {})
                    progress[const.DATA_ACHIEVEMENT_BASELINE] = chore_stats.get(
                        const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME, const.DEFAULT_ZERO
                    )

                # Calculate progress as (current total minus baseline)
                chore_stats = kid_info.get(const.DATA_KID_CHORE_STATS, {})
                current_total = chore_stats.get(
                    const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME, const.DEFAULT_ZERO
                )

                progress[const.DATA_ACHIEVEMENT_CURRENT_VALUE] = current_total

                effective_target = progress[const.DATA_ACHIEVEMENT_BASELINE] + target

                if current_total >= effective_target:
                    self._award_achievement(kid_id, achievement_id)

            # For daily minimum achievement, compare total daily chores:
            elif ach_type == const.ACHIEVEMENT_TYPE_DAILY_MIN:
                # Initialize progress for this achievement if missing.
                progress = achievement_info.setdefault(
                    const.DATA_ACHIEVEMENT_PROGRESS, {}
                ).setdefault(
                    kid_id,
                    {
                        const.DATA_ACHIEVEMENT_LAST_AWARDED_DATE: None,
                        const.DATA_ACHIEVEMENT_AWARDED: False,
                    },
                )

                today_local_iso = kh.get_today_local_iso()

                # Only award bonus if not awarded today AND the kid's daily count meets the threshold.
                chore_stats = kid_info.get(const.DATA_KID_CHORE_STATS, {})
                daily_count = chore_stats.get(
                    const.DATA_KID_CHORE_STATS_APPROVED_TODAY, const.DEFAULT_ZERO
                )
                if (
                    progress.get(const.DATA_ACHIEVEMENT_LAST_AWARDED_DATE)
                    != today_local_iso
                    and daily_count >= target
                ):
                    self._award_achievement(kid_id, achievement_id)
                    progress[const.DATA_ACHIEVEMENT_LAST_AWARDED_DATE] = today_local_iso

    def _award_achievement(self, kid_id: str, achievement_id: str):
        """Award the achievement to the kid.

        Update the achievement progress to indicate it is earned,
        and send notifications to both the kid and their parents.
        """
        achievement_info = self.achievements_data.get(achievement_id)
        if not achievement_info:
            const.LOGGER.error(
                "ERROR: Achievement Award - Achievement ID '%s' not found.",
                achievement_id,
            )
            return

        # Get or create the existing progress dictionary for this kid
        progress_for_kid = achievement_info.setdefault(
            const.DATA_ACHIEVEMENT_PROGRESS, {}
        ).get(kid_id)
        if progress_for_kid is None:
            # If it doesn't exist, initialize it with baseline from the kid's current total.
            kid_info = self.kids_data.get(kid_id, {})
            chore_stats = kid_info.get(const.DATA_KID_CHORE_STATS, {})
            progress_dict = {
                const.DATA_ACHIEVEMENT_BASELINE: chore_stats.get(
                    const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME, const.DEFAULT_ZERO
                ),
                const.DATA_ACHIEVEMENT_CURRENT_VALUE: const.DEFAULT_ZERO,
                const.DATA_ACHIEVEMENT_AWARDED: False,
            }
            achievement_info[const.DATA_ACHIEVEMENT_PROGRESS][kid_id] = progress_dict
            progress_for_kid = progress_dict

        # Mark achievement as earned for the kid by storing progress (e.g. set to target)
        progress_for_kid[const.DATA_ACHIEVEMENT_AWARDED] = True
        progress_for_kid[const.DATA_ACHIEVEMENT_CURRENT_VALUE] = achievement_info.get(
            const.DATA_ACHIEVEMENT_TARGET_VALUE, 1
        )

        # Award the extra reward points defined in the achievement
        extra_points = achievement_info.get(
            const.DATA_ACHIEVEMENT_REWARD_POINTS, const.DEFAULT_ZERO
        )
        kid_info = self.kids_data.get(kid_id)
        if kid_info is not None:
            self.update_kid_points(
                kid_id, delta=extra_points, source=const.POINTS_SOURCE_ACHIEVEMENTS
            )

        # Notify kid and parents
        extra_data = {
            const.DATA_KID_ID: kid_id,
            const.DATA_ACHIEVEMENT_ID: achievement_id,
        }
        self.hass.async_create_task(
            self._notify_kid_translated(
                kid_id,
                title_key=const.TRANS_KEY_NOTIF_TITLE_ACHIEVEMENT_EARNED,
                message_key=const.TRANS_KEY_NOTIF_MESSAGE_ACHIEVEMENT_EARNED_KID,
                message_data={
                    "achievement_name": achievement_info.get(
                        const.DATA_ACHIEVEMENT_NAME
                    ),
                },
                extra_data=extra_data,
            )
        )
        self.hass.async_create_task(
            self._notify_parents_translated(
                kid_id,
                title_key=const.TRANS_KEY_NOTIF_TITLE_ACHIEVEMENT_EARNED,
                message_key=const.TRANS_KEY_NOTIF_MESSAGE_ACHIEVEMENT_EARNED_PARENT,
                message_data={
                    "kid_name": self.kids_data[kid_id][const.DATA_KID_NAME],
                    "achievement_name": achievement_info.get(
                        const.DATA_ACHIEVEMENT_NAME
                    ),
                },
                extra_data=extra_data,
            )
        )
        const.LOGGER.debug(
            "DEBUG: Achievement Award - Achievement ID '%s' to Kid ID '%s'",
            achievement_info.get(const.DATA_ACHIEVEMENT_NAME),
            kid_id,
        )
        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------
    # Challenges: Check, Award
    # -------------------------------------------------------------------------
    def _check_challenges_for_kid(self, kid_id: str):
        """Evaluate all challenge criteria for a given kid.

        Checks that the challenge is active and then updates progress.
        """
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        now_utc = dt_util.utcnow()
        for challenge_id, challenge_info in self.challenges_data.items():
            progress = challenge_info.setdefault(const.DATA_CHALLENGE_PROGRESS, {})
            if kid_id in progress and progress[kid_id].get(
                const.DATA_CHALLENGE_AWARDED, False
            ):
                continue

            # Check challenge window
            start_date_utc = kh.parse_datetime_to_utc(
                challenge_info.get(const.DATA_CHALLENGE_START_DATE)
            )

            end_date_utc = kh.parse_datetime_to_utc(
                challenge_info.get(const.DATA_CHALLENGE_END_DATE)
            )

            if start_date_utc and now_utc < start_date_utc:
                continue
            if end_date_utc and now_utc > end_date_utc:
                continue

            target = challenge_info.get(const.DATA_CHALLENGE_TARGET_VALUE, 1)
            challenge_type = challenge_info.get(const.DATA_CHALLENGE_TYPE)

            # For a total count challenge:
            if challenge_type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                progress = progress.setdefault(
                    kid_id,
                    {
                        const.DATA_CHALLENGE_COUNT: const.DEFAULT_ZERO,
                        const.DATA_CHALLENGE_AWARDED: False,
                    },
                )

                if progress[const.DATA_CHALLENGE_COUNT] >= target:
                    self._award_challenge(kid_id, challenge_id)
            # For a daily minimum challenge, you might store per-day counts:
            elif challenge_type == const.CHALLENGE_TYPE_DAILY_MIN:
                progress = progress.setdefault(
                    kid_id,
                    {
                        const.DATA_CHALLENGE_DAILY_COUNTS: {},
                        const.DATA_CHALLENGE_AWARDED: False,
                    },
                )

                required_daily = challenge_info.get(
                    const.DATA_CHALLENGE_REQUIRED_DAILY, 1
                )

                if start_date_utc and end_date_utc:
                    num_days = (end_date_utc - start_date_utc).days + 1
                    # Verify for each day:
                    success = True
                    for n in range(num_days):
                        day = (start_date_utc + timedelta(days=n)).date().isoformat()
                        if (
                            progress[const.DATA_CHALLENGE_DAILY_COUNTS].get(
                                day, const.DEFAULT_ZERO
                            )
                            < required_daily
                        ):
                            success = False
                            break
                    if success:
                        self._award_challenge(kid_id, challenge_id)

    def _award_challenge(self, kid_id: str, challenge_id: str):
        """Award the challenge to the kid.

        Update progress and notify kid/parents.
        """
        challenge_info = self.challenges_data.get(challenge_id)
        if not challenge_info:
            const.LOGGER.error(
                "ERROR: Challenge Award - Challenge ID '%s' not found", challenge_id
            )
            return

        # Get or create the existing progress dictionary for this kid
        progress_for_kid = challenge_info.setdefault(
            const.DATA_CHALLENGE_PROGRESS, {}
        ).setdefault(
            kid_id,
            {
                const.DATA_CHALLENGE_COUNT: const.DEFAULT_ZERO,
                const.DATA_CHALLENGE_AWARDED: False,
            },
        )

        # Mark challenge as earned for the kid by storing progress
        progress_for_kid[const.DATA_CHALLENGE_AWARDED] = True
        progress_for_kid[const.DATA_CHALLENGE_COUNT] = challenge_info.get(
            const.DATA_CHALLENGE_TARGET_VALUE, 1
        )

        # Award extra reward points from the challenge
        extra_points = challenge_info.get(
            const.DATA_CHALLENGE_REWARD_POINTS, const.DEFAULT_ZERO
        )
        kid_info = self.kids_data.get(kid_id)
        if kid_info is not None:
            self.update_kid_points(
                kid_id, delta=extra_points, source=const.POINTS_SOURCE_CHALLENGES
            )

        # Notify kid and parents
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHALLENGE_ID: challenge_id}
        self.hass.async_create_task(
            self._notify_kid_translated(
                kid_id,
                title_key=const.TRANS_KEY_NOTIF_TITLE_CHALLENGE_COMPLETED,
                message_key=const.TRANS_KEY_NOTIF_MESSAGE_CHALLENGE_COMPLETED_KID,
                message_data={
                    "challenge_name": challenge_info.get(const.DATA_CHALLENGE_NAME),
                },
                extra_data=extra_data,
            )
        )
        self.hass.async_create_task(
            self._notify_parents_translated(
                kid_id,
                title_key=const.TRANS_KEY_NOTIF_TITLE_CHALLENGE_COMPLETED,
                message_key=const.TRANS_KEY_NOTIF_MESSAGE_CHALLENGE_COMPLETED_PARENT,
                message_data={
                    "kid_name": self.kids_data[kid_id][const.DATA_KID_NAME],
                    "challenge_name": challenge_info.get(const.DATA_CHALLENGE_NAME),
                },
                extra_data=extra_data,
            )
        )
        const.LOGGER.debug(
            "DEBUG: Challenge Award - Challenge ID '%s' to Kid ID '%s'",
            challenge_info.get(const.DATA_CHALLENGE_NAME),
            kid_id,
        )
        self._persist()
        self.async_set_updated_data(self._data)

    def _update_streak_progress(self, progress: dict, today: date):
        """Update a streak progress dict.

        If the last approved date was yesterday, increment the streak.
        Otherwise, reset to 1.
        """
        last_date = None
        if progress.get(const.DATA_KID_LAST_STREAK_DATE):
            try:
                last_date = date.fromisoformat(
                    progress[const.DATA_KID_LAST_STREAK_DATE]
                )
            except (ValueError, TypeError, KeyError):
                last_date = None

        # If already updated today, do nothing
        if last_date == today:
            return

        # If yesterday was the last update, increment the streak
        elif last_date == today - timedelta(days=1):
            progress[const.DATA_KID_CURRENT_STREAK] += 1

        # Reset to 1 if not done yesterday
        else:
            progress[const.DATA_KID_CURRENT_STREAK] = 1

        progress[const.DATA_KID_LAST_STREAK_DATE] = today.isoformat()

    # -------------------------------------------------------------------------------------
    # Overdue Logic Helpers
    # -------------------------------------------------------------------------------------

    def _apply_overdue_if_due(
        self,
        kid_id: str,
        chore_id: str,
        due_date_iso: str | None,
        now_utc: datetime,
        chore_info: dict[str, Any],
    ) -> bool:
        """Check if chore is past due and apply overdue state if so.

        Consolidates common overdue logic shared across all completion criteria:
        - Phase 5 NEVER_OVERDUE handling
        - Due date parsing with error handling
        - "Not yet due" early exit with overdue clearing
        - Overdue state application via _process_chore_state
        - Notification via _notify_overdue_chore

        Args:
            kid_id: The kid to check/mark overdue
            chore_id: The chore to check
            due_date_iso: ISO format due date string (or None if no due date)
            now_utc: Current UTC datetime for comparison
            chore_info: Chore info dict for notification context

        Returns:
            True if overdue was applied, False if not (not yet due, no due date,
            NEVER_OVERDUE, or parse error)
        """
        kid_info = self.kids_data.get(kid_id, {})

        # Phase 5: Check overdue handling type
        overdue_handling = chore_info.get(
            const.DATA_CHORE_OVERDUE_HANDLING_TYPE,
            const.OVERDUE_HANDLING_AT_DUE_DATE,
        )
        if overdue_handling == const.OVERDUE_HANDLING_NEVER_OVERDUE:
            return False

        # No due date means no overdue possible - clear if previously set
        if not due_date_iso:
            if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)
            return False

        # Parse due date
        try:
            due_date_utc = kh.parse_datetime_to_utc(due_date_iso)
        except (ValueError, TypeError, AttributeError) as err:
            const.LOGGER.error(
                "ERROR: Overdue Check - Error parsing due date '%s' for Chore '%s', Kid '%s': %s",
                due_date_iso,
                chore_info.get(const.DATA_CHORE_NAME, chore_id),
                kid_id,
                err,
            )
            return False

        if not due_date_utc:
            return False

        # Not yet overdue - clear any existing overdue status
        if now_utc < due_date_utc:
            if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)
            return False

        # Past due date - mark as overdue and notify
        self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_OVERDUE)
        self._notify_overdue_chore(kid_id, chore_id, chore_info, due_date_utc, now_utc)
        return True

    def _check_overdue_shared_first(
        self, chore_id: str, chore_info: dict[str, Any], now_utc: datetime
    ) -> None:
        """Check overdue status for SHARED_FIRST chores.

        SHARED_FIRST chores work like SHARED (shared due date) but only the first
        kid to complete gets credit. Once completed by any kid, other kids are
        set to completed_by_other state and should not be marked overdue.

        Logic:
        - If any kid is approved → chore is complete, no one is overdue
        - If any kid has claimed → only that kid can be overdue
        - Kids in completed_by_other state should never be overdue
        """
        # Phase 5: Check overdue handling type (skip NEVER_OVERDUE)
        overdue_handling = chore_info.get(
            const.DATA_CHORE_OVERDUE_HANDLING_TYPE,
            const.OVERDUE_HANDLING_AT_DUE_DATE,
        )
        if overdue_handling == const.OVERDUE_HANDLING_NEVER_OVERDUE:
            return

        assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        due_str = chore_info.get(const.DATA_CHORE_DUE_DATE)

        # Check if chore is already completed by any kid (SHARED_FIRST specific)
        any_approved = False
        claimant_kid_id = None

        for kid_id in assigned_kids:
            if self.is_approved_in_current_period(kid_id, chore_id):
                any_approved = True
                break
            if self.has_pending_claim(kid_id, chore_id):
                claimant_kid_id = kid_id

        # If any kid completed it, clear overdue for everyone and exit
        if any_approved:
            for kid_id in assigned_kids:
                kid_info = self.kids_data.get(kid_id, {})
                if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                    self._process_chore_state(
                        kid_id, chore_id, const.CHORE_STATE_PENDING
                    )
            return

        # For each assigned kid, determine if they should be marked overdue
        for kid_id in assigned_kids:
            kid_info = self.kids_data.get(kid_id, {})
            kid_chore_data = self._get_kid_chore_data(kid_id, chore_id)
            current_state = kid_chore_data.get(const.DATA_KID_CHORE_DATA_STATE)

            # Kids in completed_by_other state should never be overdue
            if current_state == const.CHORE_STATE_COMPLETED_BY_OTHER:
                if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                    self._process_chore_state(
                        kid_id, chore_id, const.CHORE_STATE_COMPLETED_BY_OTHER
                    )
                continue

            # If there's a claimant, only non-claimants should skip overdue processing
            # - Non-claimants: They're in completed_by_other state, skip overdue
            # - Claimant: Can still become overdue if past due and not approved
            if claimant_kid_id and kid_id != claimant_kid_id:
                # Non-claimant: clear overdue and skip (they're in completed_by_other)
                if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                    self._process_chore_state(
                        kid_id, chore_id, const.CHORE_STATE_PENDING
                    )
                continue

            # Apply overdue check - for claimants OR when no claims yet
            self._apply_overdue_if_due(kid_id, chore_id, due_str, now_utc, chore_info)

    # -------------------------------------------------------------------------------------
    # Recurring / Reset / Overdue
    # -------------------------------------------------------------------------------------

    def _check_overdue_independent(
        self, chore_id: str, chore_info: dict[str, Any], now_utc: datetime
    ) -> None:
        """Check overdue status for INDEPENDENT chores (per-kid due dates).

        INDEPENDENT chores allow each kid to have their own due date.
        Read from chore-level per_kid_due_dates dict (source of truth for INDEPENDENT).
        This dict is populated on chore creation, migration, and kid assignment.

        Phase 5: Respects overdue_handling_type:
        - NEVER_OVERDUE: Never marks as overdue
        - AT_DUE_DATE: Marks overdue when past due (current behavior)
        - AT_DUE_DATE_THEN_RESET: Marks overdue, cleared at next reset
        """
        # Phase 5: Check overdue handling type (skip NEVER_OVERDUE)
        overdue_handling = chore_info.get(
            const.DATA_CHORE_OVERDUE_HANDLING_TYPE,
            const.OVERDUE_HANDLING_AT_DUE_DATE,
        )
        if overdue_handling == const.OVERDUE_HANDLING_NEVER_OVERDUE:
            return

        assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        per_kid_due_dates = chore_info.get(const.DATA_CHORE_PER_KID_DUE_DATES, {})

        for kid_id in assigned_kids:
            # Skip if kid already claimed/approved (v0.4.0+ timestamp-based checking)
            if self.has_pending_claim(
                kid_id, chore_id
            ) or self.is_approved_in_current_period(kid_id, chore_id):
                continue

            # Get per-kid due date (source of truth for INDEPENDENT chores)
            due_str = per_kid_due_dates.get(kid_id)

            # Apply overdue using helper (handles no due date, not yet due, etc.)
            self._apply_overdue_if_due(kid_id, chore_id, due_str, now_utc, chore_info)

    def _check_overdue_shared(
        self, chore_id: str, chore_info: dict[str, Any], now_utc: datetime
    ) -> None:
        """Check overdue status for SHARED chores (chore-level due dates).

        SHARED chores (SHARED_ALL) all kids share same due date.
        Read from chore-level: DATA_CHORE_DUE_DATE.

        Phase 5 - Overdue Handling Type:
        - AT_DUE_DATE: Mark overdue when due date passes (default/current behavior)
        - NEVER_OVERDUE: Never mark this chore as overdue
        - AT_DUE_DATE_THEN_RESET: Mark overdue, but clear at next reset cycle
        """
        # Phase 5: Check overdue handling type (skip NEVER_OVERDUE)
        overdue_handling = chore_info.get(
            const.DATA_CHORE_OVERDUE_HANDLING_TYPE,
            const.OVERDUE_HANDLING_AT_DUE_DATE,
        )
        if overdue_handling == const.OVERDUE_HANDLING_NEVER_OVERDUE:
            return

        assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        due_str = chore_info.get(const.DATA_CHORE_DUE_DATE)

        # Check each kid for overdue status
        for kid_id in assigned_kids:
            # Skip if kid already claimed/approved (v0.4.0+ timestamp-based checking)
            if self.has_pending_claim(
                kid_id, chore_id
            ) or self.is_approved_in_current_period(kid_id, chore_id):
                continue

            # Apply overdue using helper (handles no due date, not yet due, etc.)
            self._apply_overdue_if_due(kid_id, chore_id, due_str, now_utc, chore_info)

    def _notify_overdue_chore(
        self,
        kid_id: str,
        chore_id: str,
        chore_info: dict[str, Any],
        due_date_utc: datetime,
        now_utc: datetime,
    ) -> None:
        """Send overdue notification to kid and parents if not already notified in last 24 hours."""
        kid_info = self.kids_data.get(kid_id, {})

        # Check notification timestamp
        if const.DATA_KID_OVERDUE_NOTIFICATIONS not in kid_info:
            kid_info[const.DATA_KID_OVERDUE_NOTIFICATIONS] = {}

        last_notif_str = kid_info[const.DATA_KID_OVERDUE_NOTIFICATIONS].get(chore_id)
        notify = False

        if last_notif_str:
            try:
                last_dt = kh.parse_datetime_to_utc(last_notif_str)
                if (
                    last_dt is None
                    or (last_dt < due_date_utc)
                    or (
                        (now_utc - last_dt)
                        >= timedelta(hours=const.DEFAULT_NOTIFY_DELAY_REMINDER)
                    )
                ):
                    notify = True
            except (ValueError, TypeError, AttributeError) as err:
                const.LOGGER.error(
                    "ERROR: Overdue Notification - Error parsing timestamp '%s' for Chore ID '%s', Kid ID '%s': %s",
                    last_notif_str,
                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                    kid_id,
                    err,
                )
                notify = True
        else:
            notify = True

        if notify:
            kid_info[const.DATA_KID_OVERDUE_NOTIFICATIONS][chore_id] = (
                now_utc.isoformat()
            )
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHORE_ID: chore_id}
            actions = [
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_CHORE}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_APPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_CHORE}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_DISAPPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_REMIND_30,
                },
            ]

            self.hass.async_create_task(
                self._notify_kid_translated(
                    kid_id,
                    title_key=const.TRANS_KEY_NOTIF_TITLE_CHORE_OVERDUE,
                    message_key=const.TRANS_KEY_NOTIF_MESSAGE_CHORE_OVERDUE,
                    message_data={
                        "chore_name": chore_info.get("name", "Unnamed Chore"),
                        "due_date": due_date_utc.isoformat()
                        if due_date_utc
                        else "Unknown",
                    },
                    extra_data=extra_data,
                )
            )
            self.hass.async_create_task(
                self._notify_parents_translated(
                    kid_id,
                    title_key=const.TRANS_KEY_NOTIF_TITLE_CHORE_OVERDUE,
                    message_key=const.TRANS_KEY_NOTIF_MESSAGE_CHORE_OVERDUE,
                    message_data={
                        "chore_name": chore_info.get("name", "Unnamed Chore"),
                        "due_date": due_date_utc.isoformat()
                        if due_date_utc
                        else "Unknown",
                    },
                    actions=actions,
                    extra_data=extra_data,
                )
            )

    async def _check_overdue_chores(self):
        """Check and mark overdue chores if due date is passed.

        Branching logic based on completion criteria:
        - INDEPENDENT: Each kid can have different due dates (per-kid storage)
        - SHARED_*: All kids share same due date (chore-level storage)

        Send an overdue notification only if not sent in the last 24 hours.
        """
        # PERF: Measure overdue scan duration
        perf_start = time.perf_counter()

        now_utc = dt_util.utcnow()
        const.LOGGER.debug(
            "DEBUG: Overdue Chores - Starting check at %s (branching by completion criteria)",
            now_utc.isoformat(),
        )

        for chore_id, chore_info in self.chores_data.items():
            # Get the list of assigned kids
            assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])

            # Check if all assigned kids have either claimed or approved the chore
            # v0.4.0+: Uses timestamp-based helpers instead of deprecated lists
            all_kids_claimed_or_approved = all(
                self.has_pending_claim(kid_id, chore_id)
                or self.is_approved_in_current_period(kid_id, chore_id)
                for kid_id in assigned_kids
            )

            # Only skip the chore if ALL assigned kids have acted on it
            if all_kids_claimed_or_approved:
                continue

            # Determine completion criteria (branching logic)
            completion_criteria = chore_info.get(
                const.DATA_CHORE_COMPLETION_CRITERIA,
                const.COMPLETION_CRITERIA_INDEPENDENT,
            )

            if completion_criteria == const.COMPLETION_CRITERIA_SHARED:
                # SHARED chores: all kids share same due date
                self._check_overdue_shared(chore_id, chore_info, now_utc)
            elif completion_criteria == const.COMPLETION_CRITERIA_SHARED_FIRST:
                # SHARED_FIRST chores: share due date, but only claimant can be overdue
                self._check_overdue_shared_first(chore_id, chore_info, now_utc)
            else:
                # INDEPENDENT chores: each kid can have different due date
                self._check_overdue_independent(chore_id, chore_info, now_utc)

        const.LOGGER.debug("DEBUG: Overdue Chores - Check completed")

        # PERF: Log overdue scan duration
        perf_duration = time.perf_counter() - perf_start
        chore_count = len(self.chores_data)
        kid_count = len(self.kids_data)
        const.LOGGER.debug(
            "PERF: _check_overdue_chores() took %.3fs for %d chores × %d kids = %d operations",
            perf_duration,
            chore_count,
            kid_count,
            chore_count * kid_count,
        )

    async def _reset_all_chore_counts(self, now: datetime):
        """Trigger resets based on the current time for all frequencies."""
        await self._handle_recurring_chore_resets(now)
        await self._check_overdue_chores()
        # Legacy field DATA_KID_TODAY_CHORE_APPROVALS is no longer used - periods structure handles this

    async def _handle_recurring_chore_resets(self, now: datetime):
        """Handle recurring resets for daily, weekly, and monthly frequencies."""

        await self._reschedule_recurring_chores(now)

        # Daily
        if now.hour == const.DEFAULT_DAILY_RESET_TIME.get(
            const.TIME_UNIT_HOUR, const.DEFAULT_HOUR
        ):
            await self._reset_chore_counts(const.FREQUENCY_DAILY, now)

        # Weekly
        if now.weekday() == const.DEFAULT_WEEKLY_RESET_DAY:
            await self._reset_chore_counts(const.FREQUENCY_WEEKLY, now)

        # Monthly
        days_in_month = monthrange(now.year, now.month)[1]
        reset_day = min(const.DEFAULT_MONTHLY_RESET_DAY, days_in_month)
        if now.day == reset_day:
            await self._reset_chore_counts(const.FREQUENCY_MONTHLY, now)

    async def _reset_chore_counts(self, frequency: str, now: datetime):
        """Reset chore counts and statuses based on the recurring frequency."""
        # Note: Points earned tracking now handled by point_stats structure
        # Legacy points_earned_* counters removed - no longer needed

        const.LOGGER.debug(
            "DEBUG: Reset Chore Counts: %s chore counts have been reset",
            frequency.capitalize(),
        )

        # If daily reset -> reset statuses
        if frequency == const.FREQUENCY_DAILY:
            await self._reset_daily_chore_statuses([frequency])
        elif frequency == const.FREQUENCY_WEEKLY:
            await self._reset_daily_chore_statuses([frequency, const.FREQUENCY_WEEKLY])

    async def _reschedule_recurring_chores(self, now: datetime):
        """For chores with the given recurring frequency, reschedule due date if they are approved and past due.

        Handles both SHARED and INDEPENDENT completion criteria:
        - SHARED: Uses chore-level due_date and state (single due date for all kids)
        - INDEPENDENT: Uses per_kid_due_dates and per-kid state (each kid has own due date)
        """

        for chore_id, chore_info in self.chores_data.items():
            # Only consider chores with a recurring frequency
            if chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY) not in (
                const.FREQUENCY_DAILY,
                const.FREQUENCY_WEEKLY,
                const.FREQUENCY_BIWEEKLY,
                const.FREQUENCY_MONTHLY,
                const.FREQUENCY_CUSTOM,
            ):
                continue

            # Branch on completion criteria
            completion_criteria = chore_info.get(
                const.DATA_CHORE_COMPLETION_CRITERIA,
                const.COMPLETION_CRITERIA_SHARED,
            )

            if completion_criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
                # INDEPENDENT mode: Each kid has their own due date and state
                self._reschedule_independent_recurring_chore(chore_id, chore_info, now)
            else:
                # SHARED mode: Single due date and state for all kids
                self._reschedule_shared_recurring_chore(chore_id, chore_info, now)

        self._persist()
        self.async_set_updated_data(self._data)
        const.LOGGER.debug(
            "DEBUG: Chore Rescheduling - Daily recurring chores rescheduling complete"
        )

    def _reschedule_shared_recurring_chore(
        self, chore_id: str, chore_info: dict[str, Any], now: datetime
    ) -> None:
        """Reschedule a SHARED recurring chore if approved and past due.

        Args:
            chore_id: The chore's internal ID
            chore_info: The chore data dictionary
            now: Current UTC datetime
        """
        # SHARED mode uses chore-level due_date
        if not chore_info.get(const.DATA_CHORE_DUE_DATE):
            return

        due_date_utc = kh.parse_datetime_to_utc(chore_info[const.DATA_CHORE_DUE_DATE])
        if due_date_utc is None:
            const.LOGGER.debug(
                "DEBUG: Chore Rescheduling - Error parsing due date for Chore ID '%s'.",
                chore_id,
            )
            return

        # If the due date is in the past and the chore is approved or approved_in_part
        if now > due_date_utc and chore_info.get(const.DATA_CHORE_STATE) in [
            const.CHORE_STATE_APPROVED,
            const.CHORE_STATE_APPROVED_IN_PART,
        ]:
            # Reschedule the chore (chore-level)
            self._reschedule_chore_next_due_date(chore_info)
            const.LOGGER.debug(
                "DEBUG: Chore Rescheduling - Rescheduled recurring SHARED Chore ID '%s'",
                chore_info.get(const.DATA_CHORE_NAME, chore_id),
            )

    def _reschedule_independent_recurring_chore(
        self, chore_id: str, chore_info: dict[str, Any], now: datetime
    ) -> None:
        """Reschedule an INDEPENDENT recurring chore for each kid if approved and past due.

        For INDEPENDENT chores, each kid has their own due date and state.
        Only reschedules for kids who have completed (approved) their instance.

        Args:
            chore_id: The chore's internal ID
            chore_info: The chore data dictionary
            now: Current UTC datetime
        """
        per_kid_due_dates = chore_info.get(const.DATA_CHORE_PER_KID_DUE_DATES, {})
        assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])

        for kid_id in assigned_kids:
            if not kid_id:
                continue

            # Get per-kid due date (source of truth for INDEPENDENT)
            kid_due_str = per_kid_due_dates.get(kid_id)
            if not kid_due_str:
                # No due date for this kid - skip
                continue

            kid_due_utc = kh.parse_datetime_to_utc(kid_due_str)
            if kid_due_utc is None:
                const.LOGGER.debug(
                    "DEBUG: Chore Rescheduling - Error parsing per-kid due date for Chore '%s', Kid '%s'.",
                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                    kid_id,
                )
                continue

            # Check per-kid state from kid's chore data
            kid_info = self.kids_data.get(kid_id, {})
            kid_chore_data = kid_info.get(const.DATA_KID_CHORE_DATA, {}).get(
                chore_id, {}
            )
            kid_state = kid_chore_data.get(
                const.DATA_KID_CHORE_DATA_STATE, const.CHORE_STATE_PENDING
            )

            # If the due date is in the past and the kid's state is approved
            if now > kid_due_utc and kid_state in [
                const.CHORE_STATE_APPROVED,
                const.CHORE_STATE_APPROVED_IN_PART,
            ]:
                # Reschedule for this kid only
                self._reschedule_chore_next_due_date_for_kid(
                    chore_info, chore_id, kid_id
                )
                # Also reset state to PENDING
                self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)
                const.LOGGER.debug(
                    "DEBUG: Chore Rescheduling - Rescheduled recurring INDEPENDENT Chore '%s' for Kid '%s'",
                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                    kid_info.get(const.DATA_KID_NAME, kid_id),
                )

    async def _reset_daily_chore_statuses(self, target_freqs: list[str]):
        """Reset chore statuses and clear approved/claimed chores for chores with these freq.

        Handles both SHARED and INDEPENDENT completion criteria:
        - SHARED: Uses chore-level due_date to determine if reset needed
        - INDEPENDENT: Uses per_kid_due_dates for each kid's due date check
        """

        now_utc = dt_util.utcnow()
        for chore_id, chore_info in self.chores_data.items():
            frequency = chore_info.get(
                const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
            )
            # Only consider chores whose frequency is either in target_freqs or const.FREQUENCY_NONE.
            if frequency not in target_freqs and frequency != const.FREQUENCY_NONE:
                continue

            # Branch on completion criteria
            completion_criteria = chore_info.get(
                const.DATA_CHORE_COMPLETION_CRITERIA,
                const.COMPLETION_CRITERIA_SHARED,
            )

            if completion_criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
                # INDEPENDENT mode: Check each kid's due date separately
                self._reset_independent_chore_status(chore_id, chore_info, now_utc)
            else:
                # SHARED mode: Use chore-level due_date
                self._reset_shared_chore_status(chore_id, chore_info, now_utc)

        # Queue filter removed - pending approvals computed from timestamps
        # The reset operations above clear timestamps, so computed list auto-updates
        self._pending_chore_changed = True

        self._persist()

    def _reset_shared_chore_status(
        self, chore_id: str, chore_info: dict[str, Any], now_utc: datetime
    ) -> None:
        """Reset a SHARED chore status if due date has passed.

        Phase 5 - Approval Reset Pending Claim Action:
        - HOLD: Keep pending claim, skip reset for kids with pending claims
        - CLEAR: Clear pending claim, reset to fresh state (default/current behavior)
        - AUTO_APPROVE: Auto-approve pending claim, then reset to fresh state

        Args:
            chore_id: The chore's internal ID
            chore_info: The chore data dictionary
            now_utc: Current UTC datetime
        """
        due_date_str = chore_info.get(const.DATA_CHORE_DUE_DATE)
        if due_date_str:
            due_date_utc = kh.parse_datetime_to_utc(due_date_str)
            if due_date_utc is None:
                const.LOGGER.debug(
                    "DEBUG: Chore Reset - Failed to parse due date '%s' for Chore ID '%s'",
                    due_date_str,
                    chore_id,
                )
                return
            # If the due date has not yet been reached, skip resetting this chore.
            if now_utc < due_date_utc:
                return

        # Phase 5: Get pending claim action setting
        pending_claim_action = chore_info.get(
            const.DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION,
            const.APPROVAL_RESET_PENDING_CLAIM_CLEAR,  # Default: current behavior
        )

        # If no due date or the due date has passed, then reset the chore state
        if chore_info[const.DATA_CHORE_STATE] not in [
            const.CHORE_STATE_PENDING,
            const.CHORE_STATE_OVERDUE,
        ]:
            previous_state = chore_info[const.DATA_CHORE_STATE]
            for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                if kid_id:
                    # Phase 5: Handle pending claims based on action setting
                    if self.has_pending_claim(kid_id, chore_id):
                        if (
                            pending_claim_action
                            == const.APPROVAL_RESET_PENDING_CLAIM_HOLD
                        ):
                            # HOLD: Skip reset for this kid, leave claim pending
                            const.LOGGER.debug(
                                "DEBUG: Chore Reset - HOLD pending claim for Kid '%s' on Chore '%s'",
                                kid_id,
                                chore_id,
                            )
                            continue
                        if (
                            pending_claim_action
                            == const.APPROVAL_RESET_PENDING_CLAIM_AUTO_APPROVE
                        ):
                            # AUTO_APPROVE: Approve the pending claim before reset
                            const.LOGGER.debug(
                                "DEBUG: Chore Reset - AUTO_APPROVE pending claim for Kid '%s' on Chore '%s'",
                                kid_id,
                                chore_id,
                            )
                            self._process_chore_state(
                                kid_id, chore_id, const.CHORE_STATE_APPROVED
                            )
                        # CLEAR (default) or after AUTO_APPROVE: Clear pending_claim_count
                        kid_info = self.kids_data.get(kid_id, {})
                        kid_chore_data = kid_info.get(
                            const.DATA_KID_CHORE_DATA, {}
                        ).get(chore_id, {})
                        if kid_chore_data:
                            kid_chore_data[
                                const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT
                            ] = 0

                    self._process_chore_state(
                        kid_id, chore_id, const.CHORE_STATE_PENDING
                    )
            const.LOGGER.debug(
                "DEBUG: Chore Reset - Resetting SHARED Chore '%s' from '%s' to '%s'",
                chore_id,
                previous_state,
                const.CHORE_STATE_PENDING,
            )

    def _reset_independent_chore_status(
        self, chore_id: str, chore_info: dict[str, Any], now_utc: datetime
    ) -> None:
        """Reset an INDEPENDENT chore status for each kid if their due date has passed.

        For INDEPENDENT chores, each kid has their own due date.
        Only reset for kids whose due date has passed.

        Phase 5 - Approval Reset Pending Claim Action:
        - HOLD: Keep pending claim, skip reset for kids with pending claims
        - CLEAR: Clear pending claim, reset to fresh state (default/current behavior)
        - AUTO_APPROVE: Auto-approve pending claim, then reset to fresh state

        Args:
            chore_id: The chore's internal ID
            chore_info: The chore data dictionary
            now_utc: Current UTC datetime
        """
        per_kid_due_dates = chore_info.get(const.DATA_CHORE_PER_KID_DUE_DATES, {})
        assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])

        # Phase 5: Get pending claim action setting
        pending_claim_action = chore_info.get(
            const.DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION,
            const.APPROVAL_RESET_PENDING_CLAIM_CLEAR,  # Default: current behavior
        )

        for kid_id in assigned_kids:
            if not kid_id:
                continue

            # Get per-kid due date (source of truth for INDEPENDENT)
            kid_due_str = per_kid_due_dates.get(kid_id)
            if kid_due_str:
                kid_due_utc = kh.parse_datetime_to_utc(kid_due_str)
                if kid_due_utc is None:
                    const.LOGGER.debug(
                        "DEBUG: Chore Reset - Failed to parse per-kid due date '%s' for Chore '%s', Kid '%s'",
                        kid_due_str,
                        chore_id,
                        kid_id,
                    )
                    continue
                # If the due date has not yet been reached, skip resetting for this kid.
                if now_utc < kid_due_utc:
                    continue

            # Check per-kid state from kid's chore data
            kid_info = self.kids_data.get(kid_id, {})
            kid_chore_data = kid_info.get(const.DATA_KID_CHORE_DATA, {}).get(
                chore_id, {}
            )
            kid_state = kid_chore_data.get(
                const.DATA_KID_CHORE_DATA_STATE, const.CHORE_STATE_PENDING
            )

            # If not already pending/overdue, reset to pending
            if kid_state not in [const.CHORE_STATE_PENDING, const.CHORE_STATE_OVERDUE]:
                # Phase 5: Handle pending claims based on action setting
                if self.has_pending_claim(kid_id, chore_id):
                    if pending_claim_action == const.APPROVAL_RESET_PENDING_CLAIM_HOLD:
                        # HOLD: Skip reset for this kid, leave claim pending
                        const.LOGGER.debug(
                            "DEBUG: Chore Reset - HOLD pending claim for Kid '%s' on Chore '%s'",
                            kid_id,
                            chore_id,
                        )
                        continue
                    if (
                        pending_claim_action
                        == const.APPROVAL_RESET_PENDING_CLAIM_AUTO_APPROVE
                    ):
                        # AUTO_APPROVE: Approve the pending claim before reset
                        const.LOGGER.debug(
                            "DEBUG: Chore Reset - AUTO_APPROVE pending claim for Kid '%s' on Chore '%s'",
                            kid_id,
                            chore_id,
                        )
                        self._process_chore_state(
                            kid_id, chore_id, const.CHORE_STATE_APPROVED
                        )
                    # CLEAR (default) or after AUTO_APPROVE: Clear pending_claim_count
                    if kid_chore_data:
                        kid_chore_data[
                            const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT
                        ] = 0

                self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)
                const.LOGGER.debug(
                    "DEBUG: Chore Reset - Resetting INDEPENDENT Chore '%s' for Kid '%s' from '%s' to '%s'",
                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                    kid_info.get(const.DATA_KID_NAME, kid_id),
                    kid_state,
                    const.CHORE_STATE_PENDING,
                )

    def _calculate_next_due_date_from_info(
        self,
        current_due_utc: datetime | None,
        chore_info: dict[str, Any],
    ) -> datetime | None:
        """Calculate next due date for a chore based on frequency (pure calculation helper).

        Consolidated scheduling logic used by both chore-level and per-kid rescheduling.

        Args:
            current_due_utc: Current due date (UTC datetime, can be None)
            chore_info: Chore data dict containing frequency and configuration

        Returns:
            datetime: Next due date (UTC) or None if calculation failed
        """
        freq = chore_info.get(
            const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
        )

        # Initialize custom frequency parameters (used only when freq == FREQUENCY_CUSTOM)
        custom_interval: int | None = None
        custom_unit: str | None = None

        # Validate custom frequency parameters
        if freq == const.FREQUENCY_CUSTOM:
            custom_interval = chore_info.get(const.DATA_CHORE_CUSTOM_INTERVAL)
            custom_unit = chore_info.get(const.DATA_CHORE_CUSTOM_INTERVAL_UNIT)
            if custom_interval is None or custom_unit not in [
                const.TIME_UNIT_DAYS,
                const.TIME_UNIT_WEEKS,
                const.TIME_UNIT_MONTHS,
            ]:
                const.LOGGER.warning(
                    "Consolidation Helper - Invalid custom frequency for chore: %s",
                    chore_info.get(const.DATA_CHORE_NAME),
                )
                return None

        # Skip if no frequency or no current due date
        if not freq or freq == const.FREQUENCY_NONE or current_due_utc is None:
            return None

        # Get applicable weekdays configuration
        raw_applicable = chore_info.get(
            const.DATA_CHORE_APPLICABLE_DAYS, const.DEFAULT_APPLICABLE_DAYS
        )
        if raw_applicable and isinstance(next(iter(raw_applicable), None), str):
            order = list(const.WEEKDAY_OPTIONS.keys())
            applicable_days = [
                order.index(day.lower())
                for day in raw_applicable
                if day.lower() in order
            ]
        else:
            applicable_days = list(raw_applicable) if raw_applicable else []

        now_local = kh.get_now_local_time()

        # Calculate next due date based on frequency
        if freq == const.FREQUENCY_CUSTOM:
            # Type narrowing: custom_unit and custom_interval are validated above
            assert custom_unit is not None
            assert custom_interval is not None
            next_due_utc = cast(
                datetime,
                kh.adjust_datetime_by_interval(
                    base_date=current_due_utc,
                    interval_unit=custom_unit,
                    delta=custom_interval,
                    require_future=True,
                    return_type=const.HELPER_RETURN_DATETIME,
                ),
            )
        else:
            next_due_utc = cast(
                datetime,
                kh.get_next_scheduled_datetime(
                    base_date=current_due_utc,
                    interval_type=freq,
                    require_future=True,
                    reference_datetime=now_local,
                    return_type=const.HELPER_RETURN_DATETIME,
                ),
            )

        # Snap to applicable weekday if configured
        if applicable_days:
            next_due_local = cast(
                datetime,
                kh.get_next_applicable_day(
                    next_due_utc,
                    applicable_days=applicable_days,
                    return_type=const.HELPER_RETURN_DATETIME,
                ),
            )
            next_due_utc = dt_util.as_utc(next_due_local)

        return next_due_utc

    def _reschedule_chore_next_due_date(self, chore_info: dict[str, Any]):
        """Reschedule chore's next due date (chore-level). Uses consolidation helper."""
        due_date_str = chore_info.get(const.DATA_CHORE_DUE_DATE)
        if not due_date_str:
            const.LOGGER.debug(
                "Chore Due Date - Reschedule: Skipping (no due date for %s)",
                chore_info.get(const.DATA_CHORE_NAME),
            )
            return

        # Parse current due date
        original_due_utc = kh.parse_datetime_to_utc(due_date_str)
        if not original_due_utc:
            const.LOGGER.debug(
                "Chore Due Date - Reschedule: Unable to parse due date for %s",
                chore_info.get(const.DATA_CHORE_NAME),
            )
            return

        # Use consolidation helper for calculation
        next_due_utc = self._calculate_next_due_date_from_info(
            original_due_utc, chore_info
        )
        if not next_due_utc:
            const.LOGGER.warning(
                "Chore Due Date - Reschedule: Failed to calculate next due date for %s",
                chore_info.get(const.DATA_CHORE_NAME),
            )
            return

        # Update chore-level due date
        chore_info[const.DATA_CHORE_DUE_DATE] = next_due_utc.isoformat()
        chore_id = chore_info.get(const.DATA_CHORE_INTERNAL_ID)

        if not chore_id:
            const.LOGGER.error(
                "Chore Due Date - Reschedule: Missing chore_id for chore: %s",
                chore_info.get(const.DATA_CHORE_NAME, "Unknown"),
            )
            return

        # Only reset to PENDING for UPON_COMPLETION type
        # Other reset types (AT_MIDNIGHT_*, AT_DUE_DATE_*) stay APPROVED until scheduled reset
        # This prevents the bug where approval_period_start > last_approved caused
        # is_approved_in_current_period() to return False immediately after approval
        approval_reset = chore_info.get(
            const.DATA_CHORE_APPROVAL_RESET_TYPE,
            const.APPROVAL_RESET_AT_MIDNIGHT_ONCE,
        )
        if approval_reset == const.APPROVAL_RESET_UPON_COMPLETION:
            for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                if kid_id:
                    self._process_chore_state(
                        kid_id, chore_id, const.CHORE_STATE_PENDING
                    )

        const.LOGGER.info(
            "Chore Due Date - Rescheduled (SHARED): %s, from %s to %s",
            chore_info.get(const.DATA_CHORE_NAME),
            dt_util.as_local(original_due_utc).isoformat(),
            dt_util.as_local(next_due_utc).isoformat(),
        )

    def _reschedule_chore_next_due_date_for_kid(
        self, chore_info: dict[str, Any], chore_id: str, kid_id: str
    ) -> None:
        """Reschedule per-kid due date (INDEPENDENT mode).

        Updates DATA_CHORE_PER_KID_DUE_DATES[kid_id]. Calls pure helper.
        Used for INDEPENDENT chores (each kid has own due date).

        Note: After migration, this method reads ONLY from DATA_CHORE_PER_KID_DUE_DATES.
        The migration populates per_kid_due_dates from the chore template (including None).
        """
        # Get per-kid current due date from canonical source (per_kid_due_dates ONLY)
        per_kid_due_dates = chore_info.get(const.DATA_CHORE_PER_KID_DUE_DATES, {})
        current_due_str = per_kid_due_dates.get(kid_id)

        # Parse current due date
        # Per wiki Use Case 2: Chores with no due date but with recurrence should stay None
        # They reset by recurrence pattern only, never become overdue
        if not current_due_str:
            # No due date set - preserve None for recurring chores without explicit due dates
            const.LOGGER.debug(
                "Chore Due Date - No due date for chore %s, kid %s; preserving None (recurrence only)",
                chore_info.get(const.DATA_CHORE_NAME),
                kid_id,
            )
            # Clear per-kid override if it existed
            if kid_id in per_kid_due_dates:
                del per_kid_due_dates[kid_id]
            chore_info[const.DATA_CHORE_PER_KID_DUE_DATES] = per_kid_due_dates

            # Clear kid's chore data due date if it exists
            kid_info = self.kids_data.get(kid_id, {})
            if kid_info:
                kid_chore_data = kid_info.get(const.DATA_KID_CHORE_DATA, {}).get(
                    chore_id, {}
                )
                if kid_chore_data:
                    kid_chore_data[const.DATA_KID_CHORE_DATA_DUE_DATE] = None
            return

        # Parse current due date that exists
        try:
            original_due_utc = kh.parse_datetime_to_utc(current_due_str)
        except (ValueError, TypeError, AttributeError):
            const.LOGGER.debug(
                "Chore Due Date - Reschedule (per-kid): Unable to parse due date for chore %s, kid %s; clearing due date",
                chore_info.get(const.DATA_CHORE_NAME),
                kid_id,
            )
            # Clear invalid due date instead of calculating one
            if kid_id in per_kid_due_dates:
                del per_kid_due_dates[kid_id]
            chore_info[const.DATA_CHORE_PER_KID_DUE_DATES] = per_kid_due_dates

            kid_info = self.kids_data.get(kid_id, {})
            if kid_info:
                kid_chore_data = kid_info.get(const.DATA_KID_CHORE_DATA, {}).get(
                    chore_id, {}
                )
                if kid_chore_data:
                    kid_chore_data[const.DATA_KID_CHORE_DATA_DUE_DATE] = None
            return

        # Use consolidation helper for calculation
        next_due_utc = self._calculate_next_due_date_from_info(
            original_due_utc, chore_info
        )
        if not next_due_utc:
            const.LOGGER.warning(
                "Chore Due Date - Reschedule (per-kid): Failed to calculate next due date for %s, kid %s",
                chore_info.get(const.DATA_CHORE_NAME),
                kid_id,
            )
            return

        # Update per-kid storage
        per_kid_due_dates[kid_id] = next_due_utc.isoformat()
        chore_info[const.DATA_CHORE_PER_KID_DUE_DATES] = per_kid_due_dates

        # Update kid's chore data if it exists (ensure structure exists before updating)
        kid_info = self.kids_data.get(kid_id, {})
        if kid_info:
            kid_chore_data_dict = kid_info.get(const.DATA_KID_CHORE_DATA, {})
            if chore_id in kid_chore_data_dict:
                kid_chore_data_dict[chore_id][const.DATA_KID_CHORE_DATA_DUE_DATE] = (
                    next_due_utc.isoformat()
                )
                # Ensure the parent dict is updated
                kid_info[const.DATA_KID_CHORE_DATA] = kid_chore_data_dict

        # Only reset to PENDING for UPON_COMPLETION type
        # Other reset types (AT_MIDNIGHT_*, AT_DUE_DATE_*) stay APPROVED until scheduled reset
        # This prevents the bug where approval_period_start > last_approved caused
        # is_approved_in_current_period() to return False immediately after approval
        approval_reset = chore_info.get(
            const.DATA_CHORE_APPROVAL_RESET_TYPE,
            const.APPROVAL_RESET_AT_MIDNIGHT_ONCE,
        )
        if approval_reset == const.APPROVAL_RESET_UPON_COMPLETION:
            self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)

        const.LOGGER.info(
            "Chore Due Date - Rescheduled (INDEPENDENT): chore %s, kid %s, from %s to %s",
            chore_info.get(const.DATA_CHORE_NAME),
            kid_info.get(const.DATA_KID_NAME),
            dt_util.as_local(original_due_utc).isoformat()
            if original_due_utc
            else "None",
            dt_util.as_local(next_due_utc).isoformat() if next_due_utc else "None",
        )

    # Set Chore Due Date
    def set_chore_due_date(
        self,
        chore_id: str,
        due_date: Optional[datetime],
        kid_id: Optional[str] = None,
    ) -> None:
        """Set the due date of a chore.

        Args:
            chore_id: Chore to update
            due_date: New due date (or None to clear)
            kid_id: If provided for INDEPENDENT chores, updates only this kid's due date.
                   For SHARED chores, this parameter is ignored.

        For SHARED chores: Updates the single chore-level due date.
        For INDEPENDENT chores:
            - Does NOT set chore-level due_date (respects post-migration structure)
            - If kid_id provided: Updates only that kid's due date
            - If kid_id None: Updates all per-kid due dates
        """
        # Retrieve the chore data; raise error if not found.
        chore_info = self.chores_data.get(chore_id)
        if chore_info is None:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_CHORE,
                    "name": chore_id,
                },
            )

        # Convert the due_date to an ISO-formatted string if provided; otherwise use None.
        # IMPORTANT: Ensure UTC timezone to maintain consistency in storage
        # Bug fix: Previously stored local timezone which caused display issues
        new_due_date_iso = dt_util.as_utc(due_date).isoformat() if due_date else None

        # Get completion criteria to determine update strategy
        criteria = chore_info.get(
            const.DATA_CHORE_COMPLETION_CRITERIA,
            const.COMPLETION_CRITERIA_SHARED,
        )

        # For SHARED chores: Update chore-level due date (single source of truth)
        # For INDEPENDENT chores: Do NOT set chore-level due date (respects post-migration structure)
        if criteria == const.COMPLETION_CRITERIA_SHARED:
            try:
                chore_info[const.DATA_CHORE_DUE_DATE] = new_due_date_iso
            except KeyError as err:
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_MISSING_FIELD,
                    translation_placeholders={
                        "field": "due_date",
                        "entity": f"chore '{chore_id}'",
                    },
                ) from err

        # For INDEPENDENT chores: Update per-kid due dates (respects post-migration structure)
        if criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
            if kid_id:
                # Update only the specified kid's due date
                if kid_id not in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                    raise HomeAssistantError(
                        translation_domain=const.DOMAIN,
                        translation_key=const.TRANS_KEY_ERROR_NOT_ASSIGNED,
                        translation_placeholders={
                            "kid_id": kid_id,
                            "chore_id": chore_id,
                        },
                    )
                if kid_id in self.kids_data:
                    kid_info = self.kids_data[kid_id]
                    chore_data = kid_info.get(const.DATA_KID_CHORE_DATA, {})
                    if chore_id in chore_data:
                        chore_data[chore_id][const.DATA_KID_CHORE_DATA_DUE_DATE] = (
                            new_due_date_iso
                        )
                    # Also update per-kid due dates dict
                    per_kid_due_dates = chore_info.setdefault(
                        const.DATA_CHORE_PER_KID_DUE_DATES, {}
                    )
                    per_kid_due_dates[kid_id] = new_due_date_iso
                    const.LOGGER.debug(
                        "Set due date for INDEPENDENT chore %s, kid %s only: %s",
                        chore_info.get(const.DATA_CHORE_NAME),
                        kid_info.get(const.DATA_KID_NAME),
                        new_due_date_iso,
                    )
            else:
                # Update all assigned kids' due dates
                for assigned_kid_id in chore_info.get(
                    const.DATA_CHORE_ASSIGNED_KIDS, []
                ):
                    if assigned_kid_id and assigned_kid_id in self.kids_data:
                        kid_info = self.kids_data[assigned_kid_id]
                        chore_data = kid_info.get(const.DATA_KID_CHORE_DATA, {})
                        if chore_id in chore_data:
                            chore_data[chore_id][const.DATA_KID_CHORE_DATA_DUE_DATE] = (
                                new_due_date_iso
                            )
                # Also update per-kid due dates dict
                per_kid_due_dates = chore_info.setdefault(
                    const.DATA_CHORE_PER_KID_DUE_DATES, {}
                )
                for assigned_kid_id in chore_info.get(
                    const.DATA_CHORE_ASSIGNED_KIDS, []
                ):
                    per_kid_due_dates[assigned_kid_id] = new_due_date_iso
                const.LOGGER.debug(
                    "Set due date for INDEPENDENT chore %s, all kids: %s",
                    chore_info.get(const.DATA_CHORE_NAME),
                    new_due_date_iso,
                )

        # If the due date is cleared (None), then remove any recurring frequency
        # and custom interval settings unless the frequency is none, daily, or weekly.
        if new_due_date_iso is None:
            # const.FREQUENCY_DAILY, const.FREQUENCY_WEEKLY, and const.FREQUENCY_NONE are all OK without a due_date
            current_frequency = chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY)
            if chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY) not in (
                const.FREQUENCY_NONE,
                const.FREQUENCY_DAILY,
                const.FREQUENCY_WEEKLY,
            ):
                const.LOGGER.debug(
                    "DEBUG: Chore Due Date - Removing frequency for Chore ID '%s' - Current frequency '%s' does not work with a due date of None",
                    chore_id,
                    current_frequency,
                )
                chore_info[const.DATA_CHORE_RECURRING_FREQUENCY] = const.FREQUENCY_NONE
                chore_info.pop(const.DATA_CHORE_CUSTOM_INTERVAL, None)
                chore_info.pop(const.DATA_CHORE_CUSTOM_INTERVAL_UNIT, None)

        # Reset the chore state to Pending and clear pending_count for all kids
        for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            if kid_id:
                self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)
                # Clear pending_count when due date changes (v0.4.0+ counter-based tracking)
                kid_info = self.kids_data.get(kid_id, {})
                kid_chore_data = kid_info.get(const.DATA_KID_CHORE_DATA, {}).get(
                    chore_id, {}
                )
                if kid_chore_data:
                    kid_chore_data[const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT] = 0

        const.LOGGER.info(
            "INFO: Chore Due Date - Due date set for Chore ID '%s'",
            chore_info.get(const.DATA_CHORE_NAME, chore_id),
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # Skip Chore Due Date
    def skip_chore_due_date(self, chore_id: str, kid_id: Optional[str] = None) -> None:
        """Skip the current due date of a recurring chore and reschedule it.

        When a due date is skipped, the chore state is reset to PENDING for all affected kids,
        since the new due date creates a new completion period.

        Args:
            chore_id: Chore to skip
            kid_id: If provided for INDEPENDENT chores, skips only this kid's due date.
                   For SHARED chores, this parameter is ignored.

        For SHARED chores: Reschedules the single chore-level due date and resets state to PENDING for all kids.
        For INDEPENDENT chores:
            - If kid_id provided: Reschedules only that kid's due date and resets that kid's state to PENDING
            - If kid_id None: Reschedules template and all per-kid due dates, resets all kids' states to PENDING
        """
        chore_info = self.chores_data.get(chore_id)
        if not chore_info:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_CHORE,
                    "name": chore_id,
                },
            )

        if (
            chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE)
            == const.FREQUENCY_NONE
        ):
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_INVALID_FREQUENCY,
                translation_placeholders={
                    "frequency": "none",
                },
            )

        # Get completion criteria to determine due date validation strategy
        criteria = chore_info.get(
            const.DATA_CHORE_COMPLETION_CRITERIA,
            const.COMPLETION_CRITERIA_SHARED,
        )

        # Check if chore has due dates based on completion criteria
        if criteria == const.COMPLETION_CRITERIA_SHARED:
            # SHARED chores use chore-level due date
            if not chore_info.get(const.DATA_CHORE_DUE_DATE):
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_MISSING_FIELD,
                    translation_placeholders={
                        "field": "due_date",
                        "entity": f"chore '{chore_info.get(const.DATA_CHORE_NAME, chore_id)}'",
                    },
                )
        else:
            # INDEPENDENT chores use per-kid due dates
            # Check if at least one assigned kid has a due date
            assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
            per_kid_due_dates = chore_info.get(const.DATA_CHORE_PER_KID_DUE_DATES, {})

            has_any_due_date = False
            for assigned_kid_id in assigned_kids:
                if (
                    assigned_kid_id in per_kid_due_dates
                    and per_kid_due_dates[assigned_kid_id]
                ):
                    has_any_due_date = True
                    break
                # Also check kid's chore data for due date
                if assigned_kid_id in self.kids_data:
                    kid_chore_data = self.kids_data[assigned_kid_id].get(
                        const.DATA_KID_CHORE_DATA, {}
                    )
                    if chore_id in kid_chore_data and kid_chore_data[chore_id].get(
                        const.DATA_KID_CHORE_DATA_DUE_DATE
                    ):
                        has_any_due_date = True
                        break

            if not has_any_due_date:
                # No due dates to skip - return early (no-op)
                const.LOGGER.debug(
                    "Skip request ignored: No kids have due dates for chore %s",
                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                )
                return

        # Apply skip logic based on completion criteria
        if criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
            # INDEPENDENT chore: skip per-kid due dates
            if kid_id:
                # Skip only the specified kid's due date
                if kid_id not in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                    raise HomeAssistantError(
                        translation_domain=const.DOMAIN,
                        translation_key=const.TRANS_KEY_ERROR_NOT_ASSIGNED,
                        translation_placeholders={
                            "kid_id": kid_id,
                            "chore_id": chore_id,
                        },
                    )
                # Check if this specific kid has a due date to skip
                per_kid_due_dates = chore_info.get(
                    const.DATA_CHORE_PER_KID_DUE_DATES, {}
                )
                kid_due_date = per_kid_due_dates.get(kid_id)
                if not kid_due_date:
                    # No due date for this kid - nothing to skip
                    const.LOGGER.debug(
                        "Skip request ignored: Kid %s has no due date for chore %s",
                        self.kids_data.get(kid_id, {}).get(const.DATA_KID_NAME, kid_id),
                        chore_info.get(const.DATA_CHORE_NAME, chore_id),
                    )
                    return
                # Reschedule and reset chore state for this kid
                self._reschedule_chore_next_due_date_for_kid(
                    chore_info, chore_id, kid_id
                )
                # Reset chore state to PENDING for this kid
                self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)
                const.LOGGER.info(
                    "Skipped due date for INDEPENDENT chore %s, kid %s - reset to PENDING",
                    chore_info.get(const.DATA_CHORE_NAME),
                    self.kids_data[kid_id].get(const.DATA_KID_NAME),
                )
            else:
                # Skip template and all assigned kids' due dates
                self._reschedule_chore_next_due_date(chore_info)
                for assigned_kid_id in chore_info.get(
                    const.DATA_CHORE_ASSIGNED_KIDS, []
                ):
                    if assigned_kid_id and assigned_kid_id in self.kids_data:
                        self._reschedule_chore_next_due_date_for_kid(
                            chore_info, chore_id, assigned_kid_id
                        )
                        # Reset chore state to PENDING for each kid
                        self._process_chore_state(
                            assigned_kid_id, chore_id, const.CHORE_STATE_PENDING
                        )
                const.LOGGER.info(
                    "Skipped due date for INDEPENDENT chore %s, all kids - reset to PENDING",
                    chore_info.get(const.DATA_CHORE_NAME),
                )
        else:
            # SHARED chore: skip chore-level due date and reset state for all kids
            self._reschedule_chore_next_due_date(chore_info)
            # Reset chore state to PENDING for all assigned kids
            for assigned_kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                if assigned_kid_id and assigned_kid_id in self.kids_data:
                    self._process_chore_state(
                        assigned_kid_id, chore_id, const.CHORE_STATE_PENDING
                    )
            const.LOGGER.info(
                "Skipped due date for SHARED chore %s - reset to PENDING for all kids",
                chore_info.get(const.DATA_CHORE_NAME),
            )

        self._persist()
        self.async_set_updated_data(self._data)

    # Reset Overdue Chores
    def reset_overdue_chores(
        self, chore_id: Optional[str] = None, kid_id: Optional[str] = None
    ) -> None:
        """Reset overdue chore(s) to Pending state and reschedule.

        Branching logic:
        - INDEPENDENT chores: Reschedule per-kid due dates individually
        - SHARED chores: Reschedule chore-level due date (affects all kids)
        """

        if chore_id:
            # Specific chore reset (with or without kid_id)
            chore_info = self.chores_data.get(chore_id)
            if not chore_info:
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                    translation_placeholders={
                        "entity_type": const.LABEL_CHORE,
                        "name": chore_id,
                    },
                )

            # Get completion criteria to determine reset strategy
            criteria = chore_info.get(
                const.DATA_CHORE_COMPLETION_CRITERIA,
                const.COMPLETION_CRITERIA_SHARED,
            )

            if criteria == const.COMPLETION_CRITERIA_INDEPENDENT and kid_id:
                # INDEPENDENT + kid specified: Reset per-kid due date
                const.LOGGER.info(
                    "Reset Overdue Chores: Rescheduling per-kid (INDEPENDENT) chore: %s, kid: %s",
                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                    kid_id,
                )
                self._reschedule_chore_next_due_date_for_kid(
                    chore_info, chore_id, kid_id
                )
            else:
                # INDEPENDENT without kid_id OR SHARED: Reset all kids via chore-level
                const.LOGGER.info(
                    "Reset Overdue Chores: Rescheduling chore (SHARED or all kids): %s",
                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                )
                self._reschedule_chore_next_due_date(chore_info)

        elif kid_id:
            # Kid-only reset: reset all overdue chores for the specified kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                    translation_placeholders={
                        "entity_type": const.LABEL_KID,
                        "name": kid_id,
                    },
                )
            for chore_id, chore_info in self.chores_data.items():
                if kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                    if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                        # Get completion criteria to determine reset strategy
                        criteria = chore_info.get(
                            const.DATA_CHORE_COMPLETION_CRITERIA,
                            const.COMPLETION_CRITERIA_SHARED,
                        )

                        if criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
                            # INDEPENDENT: Reset per-kid due date only
                            const.LOGGER.info(
                                "Reset Overdue Chores: Rescheduling per-kid (INDEPENDENT) chore: %s, kid: %s",
                                chore_info.get(const.DATA_CHORE_NAME, chore_id),
                                kid_id,
                            )
                            self._reschedule_chore_next_due_date_for_kid(
                                chore_info, chore_id, kid_id
                            )
                        else:
                            # SHARED: Reset state for this kid only (don't affect global due date)
                            const.LOGGER.info(
                                "Reset Overdue Chores: Resetting SHARED chore state for kid only: %s, kid: %s",
                                chore_info.get(const.DATA_CHORE_NAME, chore_id),
                                kid_id,
                            )
                            self._process_chore_state(
                                kid_id, chore_id, const.CHORE_STATE_PENDING
                            )
        else:
            # Global reset: Reset all overdue chores for all kids
            for kid_id, kid_info in self.kids_data.items():
                for chore_id, chore_info in self.chores_data.items():
                    if kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                        if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                            # Get completion criteria to determine reset strategy
                            criteria = chore_info.get(
                                const.DATA_CHORE_COMPLETION_CRITERIA,
                                const.COMPLETION_CRITERIA_SHARED,
                            )

                            if criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
                                # INDEPENDENT: Reset per-kid due date only
                                const.LOGGER.info(
                                    "Reset Overdue Chores: Rescheduling per-kid (INDEPENDENT) chore: %s, kid: %s",
                                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                                    kid_id,
                                )
                                self._reschedule_chore_next_due_date_for_kid(
                                    chore_info, chore_id, kid_id
                                )
                            else:
                                # SHARED: Reset chore-level (affects all kids)
                                const.LOGGER.info(
                                    "Reset Overdue Chores: Rescheduling chore (SHARED): %s for kid: %s",
                                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                                    kid_id,
                                )
                                self._reschedule_chore_next_due_date(chore_info)

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------------------
    # Penalties: Reset
    # -------------------------------------------------------------------------------------

    def reset_penalties(
        self, kid_id: Optional[str] = None, penalty_id: Optional[str] = None
    ) -> None:
        """Reset penalties based on provided kid_id and penalty_id."""

        if penalty_id and kid_id:
            # Reset a specific penalty for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Reset Penalties - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                    translation_placeholders={
                        "entity_type": const.LABEL_KID,
                        "name": kid_id,
                    },
                )
            if penalty_id not in kid_info.get(const.DATA_KID_PENALTY_APPLIES, {}):
                const.LOGGER.error(
                    "ERROR: Reset Penalties - Penalty ID '%s' does not apply to Kid ID '%s'.",
                    penalty_id,
                    kid_id,
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_ASSIGNED,
                    translation_placeholders={
                        "entity": f"penalty '{penalty_id}'",
                        "kid": kid_id,
                    },
                )

            kid_info[const.DATA_KID_PENALTY_APPLIES].pop(penalty_id, None)

        elif penalty_id:
            # Reset a specific penalty for all kids
            found = False
            for kid_info in self.kids_data.values():
                if penalty_id in kid_info.get(const.DATA_KID_PENALTY_APPLIES, {}):
                    found = True
                    kid_info[const.DATA_KID_PENALTY_APPLIES].pop(penalty_id, None)

            if not found:
                const.LOGGER.warning(
                    "WARNING: Reset Penalties - Penalty ID '%s' not found in any kid's data.",
                    penalty_id,
                )

        elif kid_id:
            # Reset all penalties for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Reset Penalties - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                    translation_placeholders={
                        "entity_type": const.LABEL_KID,
                        "name": kid_id,
                    },
                )

            kid_info[const.DATA_KID_PENALTY_APPLIES].clear()

        else:
            # Reset all penalties for all kids
            const.LOGGER.info(
                "INFO: Reset Penalties - Resetting all penalties for all kids"
            )
            for kid_info in self.kids_data.values():
                kid_info[const.DATA_KID_PENALTY_APPLIES].clear()

        const.LOGGER.debug(
            "DEBUG: Reset Penalties - Penalties reset completed - Kid ID '%s',  Penalty ID '%s'",
            kid_id,
            penalty_id,
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------------------
    # Bonuses: Reset
    # -------------------------------------------------------------------------------------

    def reset_bonuses(
        self, kid_id: Optional[str] = None, bonus_id: Optional[str] = None
    ) -> None:
        """Reset bonuses based on provided kid_id and bonus_id."""

        if bonus_id and kid_id:
            # Reset a specific bonus for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Reset Bonuses - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                    translation_placeholders={
                        "entity_type": const.LABEL_KID,
                        "name": kid_id,
                    },
                )
            if bonus_id not in kid_info.get(const.DATA_KID_BONUS_APPLIES, {}):
                const.LOGGER.error(
                    "ERROR: Reset Bonuses - Bonus '%s' does not apply to Kid ID '%s'.",
                    bonus_id,
                    kid_id,
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_ASSIGNED,
                    translation_placeholders={
                        "entity": f"bonus '{bonus_id}'",
                        "kid": kid_id,
                    },
                )

            kid_info[const.DATA_KID_BONUS_APPLIES].pop(bonus_id, None)

        elif bonus_id:
            # Reset a specific bonus for all kids
            found = False
            for kid_info in self.kids_data.values():
                if bonus_id in kid_info.get(const.DATA_KID_BONUS_APPLIES, {}):
                    found = True
                    kid_info[const.DATA_KID_BONUS_APPLIES].pop(bonus_id, None)

            if not found:
                const.LOGGER.warning(
                    "WARNING: Reset Bonuses - Bonus '%s' not found in any kid's data.",
                    bonus_id,
                )

        elif kid_id:
            # Reset all bonuses for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Reset Bonuses - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                    translation_placeholders={
                        "entity_type": const.LABEL_KID,
                        "name": kid_id,
                    },
                )

            kid_info[const.DATA_KID_BONUS_APPLIES].clear()

        else:
            # Reset all bonuses for all kids
            const.LOGGER.info(
                "INFO: Reset Bonuses - Resetting all bonuses for all kids."
            )
            for kid_info in self.kids_data.values():
                kid_info[const.DATA_KID_BONUS_APPLIES].clear()

        const.LOGGER.debug(
            "DEBUG: Reset Bonuses - Bonuses reset completed - Kid ID '%s', Bonus ID '%s'",
            kid_id,
            bonus_id,
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------------------
    # Rewards: Reset
    # This function resets reward-related data for a specified kid and/or reward by
    # clearing the reward_data entries which track claims, approvals, and period stats.
    # -------------------------------------------------------------------------------------

    def reset_rewards(
        self, kid_id: Optional[str] = None, reward_id: Optional[str] = None
    ) -> None:
        """Reset rewards based on provided kid_id and reward_id."""

        if reward_id and kid_id:
            # Reset a specific reward for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Reset Rewards - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                    translation_placeholders={
                        "entity_type": const.LABEL_KID,
                        "name": kid_id,
                    },
                )

            # Clear reward_data entry for this reward
            reward_data = kid_info.get(const.DATA_KID_REWARD_DATA, {})
            reward_data.pop(reward_id, None)

        elif reward_id:
            # Reset a specific reward for all kids
            found = False
            for kid_info in self.kids_data.values():
                reward_data = kid_info.get(const.DATA_KID_REWARD_DATA, {})
                if reward_id in reward_data:
                    found = True
                    reward_data.pop(reward_id, None)

            if not found:
                const.LOGGER.warning(
                    "WARNING: Reset Rewards - Reward '%s' not found in any kid's data.",
                    reward_id,
                )

        elif kid_id:
            # Reset all rewards for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "ERROR: Reset Rewards - Kid ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                    translation_placeholders={
                        "entity_type": const.LABEL_KID,
                        "name": kid_id,
                    },
                )

            # Clear all reward_data for this kid
            if const.DATA_KID_REWARD_DATA in kid_info:
                kid_info[const.DATA_KID_REWARD_DATA].clear()

        else:
            # Reset all rewards for all kids
            const.LOGGER.info(
                "INFO: Reset Rewards - Resetting all rewards for all kids."
            )
            for kid_info in self.kids_data.values():
                # Clear all reward_data for this kid
                if const.DATA_KID_REWARD_DATA in kid_info:
                    kid_info[const.DATA_KID_REWARD_DATA].clear()

        const.LOGGER.debug(
            "DEBUG: Reset Rewards - Rewards reset completed - Kid ID '%s', Reward ID '%s'",
            kid_id,
            reward_id,
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------------------
    # Notifications
    # -------------------------------------------------------------------------------------

    async def send_kc_notification(
        self,
        user_id: Optional[str],
        title: str,
        message: str,
        notification_id: str,
    ) -> None:
        """Send a persistent notification to a user if possible.

        Fallback to a general persistent notification if the user is not found or not set.
        """

        hass = self.hass
        if not user_id:
            # If no user_id is provided, use a general notification
            const.LOGGER.debug(
                "DEBUG: Notification - No User ID provided. Sending a general persistent notification"
            )
            await hass.services.async_call(
                const.NOTIFY_PERSISTENT_NOTIFICATION,
                const.NOTIFY_CREATE,
                {
                    const.NOTIFY_TITLE: title,
                    const.NOTIFY_MESSAGE: message,
                    const.NOTIFY_NOTIFICATION_ID: notification_id,
                },
                blocking=True,
            )
            return

        try:
            user_obj = await hass.auth.async_get_user(user_id)
            if not user_obj:
                const.LOGGER.warning(
                    "WARNING: Notification - User ID '%s' not found. Sending fallback persistent notification",
                    user_id,
                )
                await hass.services.async_call(
                    const.NOTIFY_PERSISTENT_NOTIFICATION,
                    const.NOTIFY_CREATE,
                    {
                        const.NOTIFY_TITLE: title,
                        const.NOTIFY_MESSAGE: message,
                        const.NOTIFY_NOTIFICATION_ID: notification_id,
                    },
                    blocking=True,
                )
                return

            await hass.services.async_call(
                const.NOTIFY_PERSISTENT_NOTIFICATION,
                const.NOTIFY_CREATE,
                {
                    const.NOTIFY_TITLE: title,
                    const.NOTIFY_MESSAGE: message,
                    const.NOTIFY_NOTIFICATION_ID: notification_id,
                },
                blocking=True,
            )
        except Exception as err:  # pylint: disable=broad-exception-caught
            const.LOGGER.warning(
                "WARNING: Notification - Failed to send notification to '%s': %s. Fallback to persistent notification",
                user_id,
                err,
            )
            await hass.services.async_call(
                const.NOTIFY_PERSISTENT_NOTIFICATION,
                const.NOTIFY_CREATE,
                {
                    const.NOTIFY_TITLE: title,
                    const.NOTIFY_MESSAGE: message,
                    const.NOTIFY_NOTIFICATION_ID: notification_id,
                },
                blocking=True,
            )

    async def _notify_kid(
        self,
        kid_id: str,
        title: str,
        message: str,
        actions: Optional[list[dict[str, str]]] = None,
        extra_data: Optional[dict] = None,
    ) -> None:
        """Notify a kid using their configured notification settings."""

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return
        if not kid_info.get(const.DATA_KID_ENABLE_NOTIFICATIONS, True):
            const.LOGGER.debug(
                "DEBUG: Notification - Notifications disabled for Kid ID '%s'", kid_id
            )
            return
        mobile_enabled = kid_info.get(const.DATA_KID_ENABLE_NOTIFICATIONS, True)
        persistent_enabled = kid_info.get(
            const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS, True
        )
        mobile_notify_service = kid_info.get(
            const.DATA_KID_MOBILE_NOTIFY_SERVICE, const.SENTINEL_EMPTY
        )
        if mobile_enabled and mobile_notify_service:
            await async_send_notification(
                self.hass,
                mobile_notify_service,
                title,
                message,
                actions=actions,
                extra_data=extra_data,
            )
        elif persistent_enabled:
            await self.hass.services.async_call(
                const.NOTIFY_PERSISTENT_NOTIFICATION,
                const.NOTIFY_CREATE,
                {
                    const.NOTIFY_TITLE: title,
                    const.NOTIFY_MESSAGE: message,
                    const.NOTIFY_NOTIFICATION_ID: f"kid_{kid_id}",
                },
                blocking=True,
            )
        else:
            const.LOGGER.debug(
                "DEBUG: Notification - No notification method configured for Kid ID '%s'",
                kid_id,
            )

    async def _notify_kid_translated(
        self,
        kid_id: str,
        title_key: str,
        message_key: str,
        message_data: Optional[dict[str, Any]] = None,
        actions: Optional[list[dict[str, str]]] = None,
        extra_data: Optional[dict] = None,
    ) -> None:
        """Notify a kid using translated title and message.

        Args:
            kid_id: The internal ID of the kid
            title_key: Translation key for the notification title
            message_key: Translation key for the notification message
            message_data: Dictionary of placeholder values for message formatting
            actions: Optional list of notification actions
            extra_data: Optional extra data for mobile notifications
        """
        # Get kid's preferred language (or fall back to system language)
        kid_info = self.kids_data.get(kid_id, {})
        language = kid_info.get(
            const.DATA_KID_DASHBOARD_LANGUAGE,
            self.hass.config.language,
        )
        const.LOGGER.debug(
            "Notification: kid_id=%s, language=%s, title_key=%s",
            kid_id,
            language,
            title_key,
        )

        # Load notification translations from custom translations directory
        translations = await kh.load_notification_translation(self.hass, language)
        const.LOGGER.debug(
            "Notification translations loaded: %d keys, language=%s",
            len(translations),
            language,
        )

        # Convert const key to JSON key by removing prefix
        # e.g., "notification_title_chore_assigned" -> "chore_assigned"
        json_key = title_key.replace("notification_title_", "").replace(
            "notification_message_", ""
        )

        # Look up translations from the loaded notification file
        notification = translations.get(json_key, {})
        title = notification.get("title", title_key)
        message_template = notification.get("message", message_key)

        # Format message with placeholders
        try:
            message = message_template.format(**(message_data or {}))
        except KeyError as err:
            const.LOGGER.warning(
                "Missing placeholder %s for notification '%s'",
                err,
                json_key,
            )
            message = message_template  # Use template without formatting

        # Translate action button titles
        translated_actions = None
        if actions:
            # Get action translations from the "actions" section
            action_translations = translations.get("actions", {})
            translated_actions = []
            for action in actions:
                translated_action = action.copy()
                action_title_key = action.get(const.NOTIFY_TITLE, "")
                # Convert "notif_action_approve" -> "approve"
                action_key = action_title_key.replace("notif_action_", "")
                # Look up translation, fallback to key
                translated_title = action_translations.get(action_key, action_title_key)
                translated_action[const.NOTIFY_TITLE] = translated_title
                translated_actions.append(translated_action)
            const.LOGGER.debug(
                "Translated action buttons: %s -> %s",
                [a.get(const.NOTIFY_TITLE) for a in actions],
                [a.get(const.NOTIFY_TITLE) for a in translated_actions],
            )

        # Call original notification method
        await self._notify_kid(kid_id, title, message, translated_actions, extra_data)

    async def _notify_parents(
        self,
        kid_id: str,
        title: str,
        message: str,
        actions: Optional[list[dict[str, str]]] = None,
        extra_data: Optional[dict] = None,
    ) -> None:
        """Notify all parents associated with a kid using their settings."""
        # PERF: Measure parent notification latency (sequential vs concurrent)
        perf_start = time.perf_counter()
        parent_count = 0

        for parent_id, parent_info in self.parents_data.items():
            if kid_id not in parent_info.get(const.DATA_PARENT_ASSOCIATED_KIDS, []):
                continue
            if not parent_info.get(const.DATA_PARENT_ENABLE_NOTIFICATIONS, True):
                const.LOGGER.debug(
                    "DEBUG: Notification - Notifications disabled for Parent ID '%s'",
                    parent_id,
                )
                continue
            mobile_enabled = parent_info.get(
                const.DATA_PARENT_ENABLE_NOTIFICATIONS, True
            )
            persistent_enabled = parent_info.get(
                const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS, True
            )
            mobile_notify_service = parent_info.get(
                const.DATA_PARENT_MOBILE_NOTIFY_SERVICE, const.SENTINEL_EMPTY
            )
            if mobile_enabled and mobile_notify_service:
                parent_count += 1
                await async_send_notification(
                    self.hass,
                    mobile_notify_service,
                    title,
                    message,
                    actions=actions,
                    extra_data=extra_data,
                )
            elif persistent_enabled:
                parent_count += 1
                await self.hass.services.async_call(
                    const.NOTIFY_PERSISTENT_NOTIFICATION,
                    const.NOTIFY_CREATE,
                    {
                        const.NOTIFY_TITLE: title,
                        const.NOTIFY_MESSAGE: message,
                        const.NOTIFY_NOTIFICATION_ID: f"parent_{parent_id}",
                    },
                    blocking=True,
                )
            else:
                const.LOGGER.debug(
                    "DEBUG: Notification - No notification method configured for Parent ID '%s'",
                    parent_id,
                )

        # PERF: Log parent notification latency
        perf_duration = time.perf_counter() - perf_start
        const.LOGGER.debug(
            "PERF: _notify_parents() sent %d notifications in %.3fs (sequential, avg %.3fs/parent)",
            parent_count,
            perf_duration,
            perf_duration / parent_count if parent_count > 0 else 0,
        )

    async def _notify_parents_translated(
        self,
        kid_id: str,
        title_key: str,
        message_key: str,
        message_data: Optional[dict[str, Any]] = None,
        actions: Optional[list[dict[str, str]]] = None,
        extra_data: Optional[dict] = None,
    ) -> None:
        """Notify parents using translated title and message.

        Args:
            kid_id: The internal ID of the kid (to find associated parents)
            title_key: Translation key for the notification title
            message_key: Translation key for the notification message
            message_data: Dictionary of placeholder values for message formatting
            actions: Optional list of notification actions
            extra_data: Optional extra data for mobile notifications
        """
        # Load notification translations using kid's language
        # (parent likely speaks same language as their child)
        kid_info = self.kids_data.get(kid_id, {})
        language = kid_info.get(
            const.DATA_KID_DASHBOARD_LANGUAGE,
            self.hass.config.language,
        )
        const.LOGGER.debug(
            "Parent notification: kid_id=%s, language=%s, title_key=%s",
            kid_id,
            language,
            title_key,
        )
        translations = await kh.load_notification_translation(self.hass, language)
        const.LOGGER.debug(
            "Parent notification translations loaded: %d keys, language=%s",
            len(translations),
            language,
        )

        # Convert const key to JSON key by removing prefix
        # e.g., "notification_title_chore_assigned" -> "chore_assigned"
        json_key = title_key.replace("notification_title_", "").replace(
            "notification_message_", ""
        )

        # Look up translations from the loaded notification file
        notification = translations.get(json_key, {})
        title = notification.get("title", title_key)
        message_template = notification.get("message", message_key)

        # Format message with placeholders
        try:
            message = message_template.format(**(message_data or {}))
        except KeyError as err:
            const.LOGGER.warning(
                "Missing placeholder %s for notification '%s'",
                err,
                json_key,
            )
            message = message_template  # Use template without formatting

        # Translate action button titles
        translated_actions = None
        if actions:
            # Get action translations from the "actions" section
            action_translations = translations.get("actions", {})
            translated_actions = []
            for action in actions:
                translated_action = action.copy()
                action_title_key = action.get(const.NOTIFY_TITLE, "")
                # Convert "notif_action_approve" -> "approve"
                action_key = action_title_key.replace("notif_action_", "")
                # Look up translation, fallback to key
                translated_title = action_translations.get(action_key, action_title_key)
                translated_action[const.NOTIFY_TITLE] = translated_title
                translated_actions.append(translated_action)
            const.LOGGER.debug(
                "Translated action buttons: %s -> %s",
                [a.get(const.NOTIFY_TITLE) for a in actions],
                [a.get(const.NOTIFY_TITLE) for a in translated_actions],
            )

        # Call original notification method
        await self._notify_parents(
            kid_id, title, message, translated_actions, extra_data
        )

    async def remind_in_minutes(
        self,
        kid_id: str,
        minutes: int,
        *,
        chore_id: Optional[str] = None,
        reward_id: Optional[str] = None,
    ) -> None:
        """
        Wait for the specified number of minutes and then resend the parent's
        notification if the chore or reward is still pending approval.

        If a chore_id is provided, the method checks the corresponding chore’s state.
        If a reward_id is provided, it checks whether that reward is still pending.
        """
        const.LOGGER.debug(
            "DEBUG: Notification - Scheduling reminder for Kid ID '%s', Chore ID '%s', Reward ID '%s' in %d minutes",
            kid_id,
            chore_id,
            reward_id,
            minutes,
        )
        # Use 5 seconds in test mode, convert minutes to seconds in production
        delay_seconds = 5 if self._test_mode else (minutes * 60)
        await asyncio.sleep(delay_seconds)

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            const.LOGGER.warning(
                "WARNING: Notification - Kid ID '%s' not found during reminder check",
                kid_id,
            )
            return

        if chore_id:
            chore_info = self.chores_data.get(chore_id)
            if not chore_info:
                const.LOGGER.warning(
                    "WARNING: Notification - Chore ID '%s' not found during reminder check",
                    chore_id,
                )
                return
            # Only resend if the chore is still in a pending-like state.
            if chore_info.get(const.DATA_CHORE_STATE) not in [
                const.CHORE_STATE_PENDING,
                const.CHORE_STATE_CLAIMED,
                const.CHORE_STATE_OVERDUE,
            ]:
                const.LOGGER.info(
                    "INFO: Notification - Chore ID '%s' is no longer pending approval. No reminder sent",
                    chore_id,
                )
                return
            actions = [
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_CHORE}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_APPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_CHORE}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_DISAPPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_REMIND_30,
                },
            ]
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHORE_ID: chore_id}
            await self._notify_parents_translated(
                kid_id,
                title_key=const.TRANS_KEY_NOTIF_TITLE_CHORE_REMINDER,
                message_key=const.TRANS_KEY_NOTIF_MESSAGE_CHORE_REMINDER,
                message_data={
                    "chore_name": chore_info.get(
                        const.DATA_CHORE_NAME, "Unnamed Chore"
                    ),
                    "kid_name": kid_info.get(const.DATA_KID_NAME, "A kid"),
                },
                actions=actions,
                extra_data=extra_data,
            )
            const.LOGGER.info(
                "INFO: Notification - Resent reminder for Chore ID '%s' for Kid ID '%s'",
                chore_id,
                kid_id,
            )
        elif reward_id:
            # Check if the reward is still pending approval using modern reward_data
            reward_data = kid_info.get(const.DATA_KID_REWARD_DATA, {}).get(
                reward_id, {}
            )
            pending_count = reward_data.get(const.DATA_KID_REWARD_DATA_PENDING_COUNT, 0)
            if pending_count <= 0:
                const.LOGGER.info(
                    "INFO: Notification - Reward ID '%s' is no longer pending approval for Kid ID '%s'. No reminder sent",
                    reward_id,
                    kid_id,
                )
                return
            actions = [
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_REWARD}|{kid_id}|{reward_id}",
                    const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_APPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_REWARD}|{kid_id}|{reward_id}",
                    const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_DISAPPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{reward_id}",
                    const.NOTIFY_TITLE: const.TRANS_KEY_NOTIF_ACTION_REMIND_30,
                },
            ]
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_REWARD_ID: reward_id}
            reward_info = self.rewards_data.get(reward_id, {})
            reward_name = reward_info.get(const.DATA_REWARD_NAME, "the reward")
            await self._notify_parents_translated(
                kid_id,
                title_key=const.TRANS_KEY_NOTIF_TITLE_REWARD_REMINDER,
                message_key=const.TRANS_KEY_NOTIF_MESSAGE_REWARD_REMINDER,
                message_data={
                    "reward_name": reward_name,
                    "kid_name": kid_info.get(const.DATA_KID_NAME, "A kid"),
                },
                actions=actions,
                extra_data=extra_data,
            )
            const.LOGGER.info(
                "INFO: Notification - Resent reminder for Reward ID '%s' for Kid ID '%s'",
                reward_id,
                kid_id,
            )
        else:
            const.LOGGER.warning(
                "WARNING: Notification - No Chore ID or Reward ID provided for reminder action"
            )

    # -------------------------------------------------------------------------------------
    # Storage
    # -------------------------------------------------------------------------------------

    def _persist(self, immediate: bool = True):
        """Save coordinator data to persistent storage.

        Default behavior is immediate synchronous persistence to avoid race conditions
        between persist operations and config entry reload/unload. This is the safest
        and simplest approach for a system with frequent entity additions/deletions.

        Args:
            immediate: If True (default), save immediately without debouncing.
                      If False, schedule save with 5-second debouncing to batch multiple
                      updates (NOT currently used - kept for future optimization if needed).

        Philosophy:
            - Immediate=True is the default because:
              1. Most _persist() calls are NOT in loops
              2. Avoids race conditions with config reload timing
              3. Simplifies debugging and guarantees consistency
              4. Tests run efficiently without artificial delays
            - Debouncing (immediate=False) could be added in the future if profiling
              shows a specific high-frequency operation benefits from it
        """
        if immediate:
            # Cancel any pending debounced save
            if self._persist_task and not self._persist_task.done():
                self._persist_task.cancel()
                self._persist_task = None

            # Immediate synchronous save
            perf_start = time.perf_counter()
            self.storage_manager.set_data(self._data)
            self.hass.add_job(self.storage_manager.async_save)
            perf_duration = time.perf_counter() - perf_start
            const.LOGGER.debug(
                "PERF: _persist(immediate=True) took %.3fs (queued async save)",
                perf_duration,
            )
        else:
            # Debounced save - cancel existing task and schedule new one
            if self._persist_task and not self._persist_task.done():
                self._persist_task.cancel()

            self._persist_task = self.hass.async_create_task(
                self._persist_debounced_impl()
            )

    async def _persist_debounced_impl(self):
        """Implementation of debounced persist with delay."""
        try:
            # Wait for debounce period
            await asyncio.sleep(self._persist_debounce_seconds)

            # PERF: Track storage write frequency
            perf_start = time.perf_counter()

            self.storage_manager.set_data(self._data)
            await self.storage_manager.async_save()

            perf_duration = time.perf_counter() - perf_start
            const.LOGGER.debug(
                "PERF: _persist_debounced_impl() took %.3fs (async save completed)",
                perf_duration,
            )
        except asyncio.CancelledError:
            # Task was cancelled, new save scheduled
            const.LOGGER.debug("Debounced persist cancelled (replaced by new save)")
            raise
