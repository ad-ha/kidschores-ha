# File: coordinator.py
"""Coordinator for the KidsChores integration.

Handles data synchronization, chore claiming and approval, badge tracking,
reward redemption, penalty application, and recurring chore handling.
Manages entities primarily using internal_id for consistency.
"""

import asyncio
import uuid

from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any, Optional

from homeassistant.auth.models import User
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import const
from . import kc_helpers as kh
from .storage_manager import KidsChoresStorageManager
from .notification_helper import async_send_notification


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

    # -------------------------------------------------------------------------------------
    # Migrate Data and Converters
    # -------------------------------------------------------------------------------------

    def _migrate_datetime(self, dt_str: str) -> str:
        """Convert a datetime string to a UTC-aware ISO string."""
        if not isinstance(dt_str, str):
            return dt_str

        try:
            # Try to parse using Home Assistant’s utility first:
            dt_obj = dt_util.parse_datetime(dt_str)
            if dt_obj is None:
                # Fallback using fromisoformat
                dt_obj = datetime.fromisoformat(dt_str)
            # If naive, assume local time and make it aware:
            if dt_obj.tzinfo is None:
                dt_obj = dt_obj.replace(
                    tzinfo=dt_util.get_time_zone(self.hass.config.time_zone)
                )
            # Convert to UTC
            dt_obj_utc = dt_util.as_utc(dt_obj)
            return dt_obj_utc.isoformat()
        except Exception as err:
            const.LOGGER.warning("Error migrating datetime '%s': %s", dt_str, err)
            return dt_str

    def _migrate_stored_datetimes(self):
        """Walk through stored data and convert known datetime fields to UTC-aware ISO strings."""
        # For each chore, migrate due_date, last_completed, and last_claimed
        for chore in self._data.get(const.DATA_CHORES, {}).values():
            if chore.get(const.DATA_CHORE_DUE_DATE):
                chore[const.DATA_CHORE_DUE_DATE] = self._migrate_datetime(
                    chore[const.DATA_CHORE_DUE_DATE]
                )
            if chore.get(const.DATA_CHORE_LAST_COMPLETED):
                chore[const.DATA_CHORE_LAST_COMPLETED] = self._migrate_datetime(
                    chore[const.DATA_CHORE_LAST_COMPLETED]
                )
            if chore.get(const.DATA_CHORE_LAST_CLAIMED):
                chore[const.DATA_CHORE_LAST_CLAIMED] = self._migrate_datetime(
                    chore[const.DATA_CHORE_LAST_CLAIMED]
                )
        # Also, migrate timestamps in pending approvals
        for approval in self._data.get(const.DATA_PENDING_CHORE_APPROVALS, []):
            if approval.get(const.DATA_CHORE_TIMESTAMP):
                approval[const.DATA_CHORE_TIMESTAMP] = self._migrate_datetime(
                    approval[const.DATA_CHORE_TIMESTAMP]
                )
        for approval in self._data.get(const.DATA_PENDING_REWARD_APPROVALS, []):
            if approval.get(const.DATA_CHORE_TIMESTAMP):
                approval[const.DATA_CHORE_TIMESTAMP] = self._migrate_datetime(
                    approval[const.DATA_CHORE_TIMESTAMP]
                )

        # Migrate datetime on Challenges
        for challenge in self._data.get(const.DATA_CHALLENGES, {}).values():
            start_date = challenge.get(const.DATA_CHALLENGE_START_DATE)
            if not isinstance(start_date, str) or not start_date.strip():
                challenge[const.DATA_CHALLENGE_START_DATE] = None
            else:
                challenge[const.DATA_CHALLENGE_START_DATE] = self._migrate_datetime(
                    start_date
                )

            end_date = challenge.get(const.DATA_CHALLENGE_END_DATE)
            if not isinstance(end_date, str) or not end_date.strip():
                challenge[const.DATA_CHALLENGE_END_DATE] = None
            else:
                challenge[const.DATA_CHALLENGE_END_DATE] = self._migrate_datetime(
                    end_date
                )

    def _migrate_chore_data(self):
        """Migrate each chore's data to include new fields if missing."""
        chores = self._data.get(const.DATA_CHORES, {})
        for chore in chores.values():
            chore.setdefault(const.CONF_APPLICABLE_DAYS, const.DEFAULT_APPLICABLE_DAYS)
            chore.setdefault(const.CONF_NOTIFY_ON_CLAIM, const.DEFAULT_NOTIFY_ON_CLAIM)
            chore.setdefault(
                const.CONF_NOTIFY_ON_APPROVAL, const.DEFAULT_NOTIFY_ON_APPROVAL
            )
            chore.setdefault(
                const.CONF_NOTIFY_ON_DISAPPROVAL, const.DEFAULT_NOTIFY_ON_DISAPPROVAL
            )
        const.LOGGER.info("Chore data migration complete.")

    def _migrate_badges(self):
        """Migrate legacy 'chore_count' badges into cumulative badges.

        For badges whose threshold_type is set to the legacy value (e.g. BADGE_THRESHOLD_TYPE_CHORE_COUNT),
        compute the new threshold as the legacy count multiplied by the average default points across all chores.
        Also, set reset fields to empty and disable periodic resets.
        """
        badges = self._data.get(const.DATA_BADGES, {})
        chores = self._data.get(const.DATA_CHORES, {})

        # Calculate the average default points over all chores.
        total_points = 0.0
        count = 0
        for chore in chores.values():
            try:
                default_points = float(
                    chore.get(const.DATA_CHORE_DEFAULT_POINTS, const.DEFAULT_POINTS)
                )
                total_points += default_points
                count += 1
            except Exception:
                continue

        # If there are no chores, we fallback to DEFAULT_POINTS.
        average_points = (total_points / count) if count > 0 else const.DEFAULT_POINTS

        # Process each badge.
        for badge in badges.values():
            # Check if the badge uses the legacy "chore_count" threshold type.
            if (
                badge.get(const.DATA_BADGE_THRESHOLD_TYPE)
                == const.BADGE_THRESHOLD_TYPE_CHORE_COUNT
            ):
                old_threshold = badge.get(
                    const.DATA_BADGE_THRESHOLD_VALUE,
                    const.DEFAULT_BADGE_THRESHOLD_VALUE,
                )
                try:
                    # Multiply the legacy count by the average default points.
                    new_threshold = float(old_threshold) * average_points
                except Exception:
                    new_threshold = old_threshold

                # Update the badge data to be a cumulative points badge.
                badge[const.DATA_BADGE_THRESHOLD_VALUE] = new_threshold
                badge[const.DATA_BADGE_THRESHOLD_TYPE] = const.CONF_POINTS

                # Set reset-related fields to empty and disable periodic resets.
                badge[const.DATA_BADGE_RESET_PERIODICALLY] = False
                badge[const.DATA_BADGE_RESET_PERIOD] = const.CONF_EMPTY
                badge[const.DATA_BADGE_RESET_GRACE_PERIOD] = const.CONF_EMPTY
                badge[const.DATA_BADGE_MAINTENANCE_RULES] = const.CONF_EMPTY

                const.LOGGER.info(
                    "Migrated legacy chore_count badge '%s': old threshold %s -> new threshold %s (average_points=%.2f)",
                    badge.get(const.DATA_BADGE_NAME),
                    old_threshold,
                    new_threshold,
                    average_points,
                )

    # -------------------------------------------------------------------------------------
    # Normalize Lists
    # -------------------------------------------------------------------------------------

    def _normalize_kid_lists(self, kid_info: dict[str, Any]) -> None:
        "Normalize lists and ensuring they are not dict"
        for key in [
            const.DATA_KID_CLAIMED_CHORES,
            const.DATA_KID_APPROVED_CHORES,
            const.DATA_KID_PENDING_REWARDS,
            const.DATA_KID_REDEEMED_REWARDS,
        ]:
            if not isinstance(kid_info.get(key), list):
                kid_info[key] = []

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
        except Exception as err:
            raise UpdateFailed(f"Error updating KidsChores data: {err}") from err

    async def async_config_entry_first_refresh(self):
        """Load from storage and merge config options."""
        stored_data = self.storage_manager.get_data()
        if stored_data:
            self._data = stored_data

            # Migrate any datetime fields in stored data to UTC-aware strings
            self._migrate_stored_datetimes()

            # Migrate chore data and add new fields
            self._migrate_chore_data()

            #  Migrate Badge Data for Legacy Badges
            self._migrate_badges()

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
                const.DATA_PENDING_CHORE_APPROVALS: [],
                const.DATA_PENDING_REWARD_APPROVALS: [],
            }

        if not isinstance(self._data.get(const.DATA_PENDING_CHORE_APPROVALS), list):
            self._data[const.DATA_PENDING_CHORE_APPROVALS] = []
        if not isinstance(self._data.get(const.DATA_PENDING_REWARD_APPROVALS), list):
            self._data[const.DATA_PENDING_REWARD_APPROVALS] = []

        # Register daily/weekly/monthly resets
        async_track_time_change(
            self.hass, self._reset_all_chore_counts, **const.DEFAULT_DAILY_RESET_TIME
        )

        # Merge config entry data (options) into the stored data
        self._initialize_data_from_config()

        # Normalize all kids list fields
        for kid in self._data.get(const.DATA_KIDS, {}).values():
            self._normalize_kid_lists(kid)

        self._persist()
        await super().async_config_entry_first_refresh()

    # -------------------------------------------------------------------------------------
    # Data Initialization from Config
    # -------------------------------------------------------------------------------------

    def _initialize_data_from_config(self):
        """Merge config_entry options with stored data structures using internal_id."""
        options = self.config_entry.options

        # Retrieve configuration dictionaries from config entry options
        config_sections = {
            const.DATA_KIDS: options.get(const.CONF_KIDS, {}),
            const.DATA_PARENTS: options.get(const.CONF_PARENTS, {}),
            const.DATA_CHORES: options.get(const.CONF_CHORES, {}),
            const.DATA_BADGES: options.get(const.CONF_BADGES, {}),
            const.DATA_REWARDS: options.get(const.CONF_REWARDS, {}),
            const.DATA_PENALTIES: options.get(const.CONF_PENALTIES, {}),
            const.DATA_BONUSES: options.get(const.CONF_BONUSES, {}),
            const.DATA_ACHIEVEMENTS: options.get(const.CONF_ACHIEVEMENTS, {}),
            const.DATA_CHALLENGES: options.get(const.CONF_CHALLENGES, {}),
        }

        # Ensure minimal structure
        self._ensure_minimal_structure()

        # Initialize each section using private helper
        for section_key, data_dict in config_sections.items():
            init_func = getattr(self, f"_initialize_{section_key}", None)
            if init_func:
                init_func(data_dict)
            else:
                self._data.setdefault(section_key, data_dict)
                const.LOGGER.warning(
                    "No initializer found for section '%s'", section_key
                )

        # Recalculate Badges on reload
        self._recalculate_all_badges()

    def _ensure_minimal_structure(self):
        """Ensure that all necessary data sections are present."""
        for key in [
            const.DATA_KIDS,
            const.DATA_PARENTS,
            const.DATA_CHORES,
            const.DATA_BADGES,
            const.DATA_REWARDS,
            const.DATA_PENALTIES,
            const.DATA_BONUSES,
            const.DATA_ACHIEVEMENTS,
            const.DATA_CHALLENGES,
        ]:
            self._data.setdefault(key, {})

        for key in [
            const.DATA_PENDING_CHORE_APPROVALS,
            const.DATA_PENDING_REWARD_APPROVALS,
        ]:
            if not isinstance(self._data.get(key), list):
                self._data[key] = []

    # -------------------------------------------------------------------------------------
    # Helpers to Sync Entities from config
    # -------------------------------------------------------------------------------------

    def _initialize_kids(self, kids_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_KIDS, kids_dict, self._create_kid, self._update_kid
        )

    def _initialize_parents(self, parents_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_PARENTS, parents_dict, self._create_parent, self._update_parent
        )

    def _initialize_chores(self, chores_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_CHORES, chores_dict, self._create_chore, self._update_chore
        )

    def _initialize_badges(self, badges_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_BADGES, badges_dict, self._create_badge, self._update_badge
        )

    def _initialize_rewards(self, rewards_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_REWARDS, rewards_dict, self._create_reward, self._update_reward
        )

    def _initialize_penalties(self, penalties_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_PENALTIES,
            penalties_dict,
            self._create_penalty,
            self._update_penalty,
        )

    def _initialize_achievements(self, achievements_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_ACHIEVEMENTS,
            achievements_dict,
            self._create_achievement,
            self._update_achievement,
        )

    def _initialize_challenges(self, challenges_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_CHALLENGES,
            challenges_dict,
            self._create_challenge,
            self._update_challenge,
        )

    def _initialize_bonuses(self, bonuses_dict: dict[str, Any]):
        self._sync_entities(
            const.DATA_BONUSES, bonuses_dict, self._create_bonus, self._update_bonus
        )

    def _sync_entities(
        self,
        section: str,
        config_data: dict[str, Any],
        create_method,
        update_method,
    ):
        """Synchronize entities in a given data section based on config_data."""
        existing_ids = set(self._data[section].keys())
        config_ids = set(config_data.keys())

        # Identify entities to remove
        entities_to_remove = existing_ids - config_ids
        for entity_id in entities_to_remove:
            # Remove entity from data
            del self._data[section][entity_id]

            # Remove entity from HA registry
            self._remove_entities_in_ha(section, entity_id)
            if section == const.DATA_CHORES:
                for kid_id in self.kids_data.keys():
                    self._remove_kid_chore_entities(kid_id, entity_id)

            # Perform general clean-up
            self._cleanup_all_links()

            # Remove deleted kids from parents list
            self._cleanup_parent_assignments()

            # Remove chore approvals on chore delete
            self._cleanup_pending_chore_approvals()

            # Remove reward approvals on reward delete
            if section == const.DATA_REWARDS:
                self._cleanup_pending_reward_approvals()

        # Add or update entities
        for entity_id, entity_body in config_data.items():
            if entity_id not in self._data[section]:
                create_method(entity_id, entity_body)
            else:
                update_method(entity_id, entity_body)

        # Remove orphaned shared chore sensors.
        if section == const.DATA_CHORES:
            self.hass.async_create_task(self._remove_orphaned_shared_chore_sensors())

        # Remove orphaned achievement and challenges sensors
        self.hass.async_create_task(self._remove_orphaned_achievement_entities())
        self.hass.async_create_task(self._remove_orphaned_challenge_entities())

        # Remove deprecated sensors
        self.hass.async_create_task(
            self.remove_deprecated_entities(self.hass, self.config_entry)
        )

        # Remove deprecated buttons
        self.remove_deprecated_button_entities()

    def _cleanup_all_links(self) -> None:
        """Run all cross-entity cleanup routines."""
        self._cleanup_deleted_kid_references()
        self._cleanup_deleted_chore_references()
        self._cleanup_deleted_chore_in_achievements()
        self._cleanup_deleted_chore_in_challenges()

    def _remove_entities_in_ha(self, section: str, item_id: str):
        """Remove all platform entities whose unique_id references the given item_id."""
        ent_reg = er.async_get(self.hass)
        for entity_entry in list(ent_reg.entities.values()):
            if str(item_id) in str(entity_entry.unique_id):
                ent_reg.async_remove(entity_entry.entity_id)
                const.LOGGER.debug(
                    "Auto-removed entity '%s' with unique_id '%s' from registry",
                    entity_entry.entity_id,
                    entity_entry.unique_id,
                )

    async def _remove_orphaned_shared_chore_sensors(self):
        """Remove SharedChoreGlobalStateSensor entities for chores no longer marked as shared."""
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
                if not chore_info or not chore_info.get(
                    const.DATA_CHORE_SHARED_CHORE, False
                ):
                    ent_reg.async_remove(entity_entry.entity_id)
                    const.LOGGER.debug(
                        "Removed orphaned SharedChoreGlobalStateSensor: %s",
                        entity_entry.entity_id,
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
                achievement = self._data.get(const.DATA_ACHIEVEMENTS, {}).get(
                    achievement_id
                )
                if not achievement or kid_id not in achievement.get(
                    const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, []
                ):
                    ent_reg.async_remove(entity_entry.entity_id)
                    const.LOGGER.debug(
                        "Removed orphaned achievement progress sensor '%s' because kid '%s' is not assigned to achievement '%s'",
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
                challenge = self._data.get(const.DATA_CHALLENGES, {}).get(challenge_id)
                if not challenge or kid_id not in challenge.get(
                    const.DATA_CHALLENGE_ASSIGNED_KIDS, []
                ):
                    ent_reg.async_remove(entity_entry.entity_id)
                    const.LOGGER.debug(
                        "Removed orphaned challenge progress sensor '%s' because kid '%s' is not assigned to challenge '%s'",
                        entity_entry.entity_id,
                        kid_id,
                        challenge_id,
                    )

    def _remove_kid_chore_entities(self, kid_id: str, chore_id: str) -> None:
        """Remove all kid-specific chore entities for a given kid and chore."""
        ent_reg = er.async_get(self.hass)
        for entity_entry in list(ent_reg.entities.values()):
            if (kid_id in entity_entry.unique_id) and (
                chore_id in entity_entry.unique_id
            ):
                ent_reg.async_remove(entity_entry.entity_id)
                const.LOGGER.debug(
                    "Removed kid-specific entity '%s' for kid '%s' and chore '%s'",
                    entity_entry.entity_id,
                    kid_id,
                    chore_id,
                )

    def _cleanup_chore_from_kid(self, kid_id: str, chore_id: str) -> None:
        """Remove references to a specific chore from a kid's data."""
        kid = self.kids_data.get(kid_id)
        if not kid:
            return

        # Remove from lists if present
        for key in [const.DATA_KID_CLAIMED_CHORES, const.DATA_KID_APPROVED_CHORES]:
            if chore_id in kid.get(key, []):
                kid[key] = [c for c in kid[key] if c != chore_id]
                const.LOGGER.debug(
                    "Removed chore '%s' from kid '%s' list '%s'", chore_id, kid_id, key
                )

        # Remove from dictionary fields if present
        for dict_key in [const.DATA_KID_CHORE_CLAIMS, const.DATA_KID_CHORE_APPROVALS]:
            if chore_id in kid.get(dict_key, {}):
                kid[dict_key].pop(chore_id)
                const.LOGGER.debug(
                    "Removed chore '%s' from kid '%s' dict '%s'",
                    chore_id,
                    kid_id,
                    dict_key,
                )

        # Remove from chore streaks if present
        if (
            const.DATA_KID_CHORE_STREAKS in kid
            and chore_id in kid[const.DATA_KID_CHORE_STREAKS]
        ):
            kid[const.DATA_KID_CHORE_STREAKS].pop(chore_id)
            const.LOGGER.debug(
                "Removed chore streak for chore '%s' from kid '%s'", chore_id, kid_id
            )

        # Remove any pending chore approvals for this kid and chore
        self._data[const.DATA_PENDING_CHORE_APPROVALS] = [
            ap
            for ap in self._data.get(const.DATA_PENDING_CHORE_APPROVALS, [])
            if not (
                ap.get(const.DATA_KID_ID) == kid_id
                and ap.get(const.DATA_CHORE_ID) == chore_id
            )
        ]

    def _cleanup_pending_chore_approvals(self) -> None:
        """Remove any pending chore approvals for chore IDs that no longer exist."""
        valid_chore_ids = set(self._data.get(const.DATA_CHORES, {}).keys())
        self._data[const.DATA_PENDING_CHORE_APPROVALS] = [
            ap
            for ap in self._data.get(const.DATA_PENDING_CHORE_APPROVALS, [])
            if ap.get(const.DATA_CHORE_ID) in valid_chore_ids
        ]

    def _cleanup_pending_reward_approvals(self) -> None:
        """Remove any pending reward approvals for reward IDs that no longer exist."""
        valid_reward_ids = set(self._data.get(const.DATA_REWARDS, {}).keys())
        self._data[const.DATA_PENDING_REWARD_APPROVALS] = [
            approval
            for approval in self._data.get(const.DATA_PENDING_REWARD_APPROVALS, [])
            if approval.get(const.DATA_REWARD_ID) in valid_reward_ids
        ]

    def _cleanup_deleted_kid_references(self) -> None:
        """Remove references to kids that no longer exist from other sections."""
        valid_kid_ids = set(self.kids_data.keys())

        # Remove deleted kid IDs from all chore assignments
        for chore in self._data.get(const.DATA_CHORES, {}).values():
            if const.DATA_CHORE_ASSIGNED_KIDS in chore:
                original = chore[const.DATA_CHORE_ASSIGNED_KIDS]
                filtered = [kid for kid in original if kid in valid_kid_ids]
                if filtered != original:
                    chore[const.DATA_CHORE_ASSIGNED_KIDS] = filtered
                    const.LOGGER.debug(
                        "Cleaned up assigned_kids in chore '%s'",
                        chore.get(const.DATA_CHORE_NAME),
                    )

        # Remove progress in achievements and challenges
        for section in [const.DATA_ACHIEVEMENTS, const.DATA_CHALLENGES]:
            for entity in self._data.get(section, {}).values():
                progress = entity.get(const.DATA_PROGRESS, {})
                keys_to_remove = [kid for kid in progress if kid not in valid_kid_ids]
                for kid in keys_to_remove:
                    del progress[kid]
                    const.LOGGER.debug(
                        "Removed progress for deleted kid '%s' in section '%s'",
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
                            "Cleaned up assigned_kids in %s '%s'",
                            section,
                            entity.get(const.DATA_NAME),
                        )

    def _cleanup_deleted_chore_references(self) -> None:
        """Remove references to chores that no longer exist from kid data."""
        valid_chore_ids = set(self.chores_data.keys())
        for kid in self.kids_data.values():
            # Clean up list fields
            for key in [const.DATA_KID_CLAIMED_CHORES, const.DATA_KID_APPROVED_CHORES]:
                if key in kid:
                    original = kid[key]
                    filtered = [chore for chore in original if chore in valid_chore_ids]
                    if filtered != original:
                        kid[key] = filtered

            # Clean up dictionary fields
            for dict_key in [
                const.DATA_KID_CHORE_CLAIMS,
                const.DATA_KID_CHORE_APPROVALS,
            ]:
                if dict_key in kid:
                    kid[dict_key] = {
                        chore: count
                        for chore, count in kid[dict_key].items()
                        if chore in valid_chore_ids
                    }

            # Clean up chore streaks
            if const.DATA_KID_CHORE_STREAKS in kid:
                for chore in list(kid[const.DATA_KID_CHORE_STREAKS].keys()):
                    if chore not in valid_chore_ids:
                        del kid[const.DATA_KID_CHORE_STREAKS][chore]
                        const.LOGGER.debug(
                            "Removed chore streak for deleted chore '%s'", chore
                        )

    def _cleanup_parent_assignments(self) -> None:
        """Remove any kid IDs from parent's 'associated_kids' that no longer exist."""
        valid_kid_ids = set(self.kids_data.keys())
        for parent in self._data.get(const.DATA_PARENTS, {}).values():
            original = parent.get(const.DATA_PARENT_ASSOCIATED_KIDS, [])
            filtered = [kid_id for kid_id in original if kid_id in valid_kid_ids]
            if filtered != original:
                parent[const.DATA_PARENT_ASSOCIATED_KIDS] = filtered
                const.LOGGER.debug(
                    "Cleaned up associated_kids for parent '%s'. New list: %s",
                    parent.get(const.DATA_PARENT_NAME),
                    filtered,
                )

    def _cleanup_deleted_chore_in_achievements(self) -> None:
        """Clear selected_chore_id in achievements if the chore no longer exists."""
        valid_chore_ids = set(self.chores_data.keys())
        for achievement in self._data.get(const.DATA_ACHIEVEMENTS, {}).values():
            selected = achievement.get(const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID)
            if selected and selected not in valid_chore_ids:
                achievement[const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID] = ""
                const.LOGGER.debug(
                    "Cleared selected_chore_id in achievement '%s'",
                    achievement.get(const.DATA_ACHIEVEMENT_NAME),
                )

    def _cleanup_deleted_chore_in_challenges(self) -> None:
        """Clear selected_chore_id in challenges if the chore no longer exists."""
        valid_chore_ids = set(self.chores_data.keys())
        for challenge in self._data.get(const.DATA_CHALLENGES, {}).values():
            selected = challenge.get(const.DATA_CHALLENGE_SELECTED_CHORE_ID)
            if selected and selected not in valid_chore_ids:
                challenge[const.DATA_CHALLENGE_SELECTED_CHORE_ID] = const.CONF_EMPTY
                const.LOGGER.debug(
                    "Cleared selected_chore_id in challenge '%s'",
                    challenge.get(const.DATA_CHALLENGE_NAME),
                )

    async def remove_deprecated_entities(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Remove old/deprecated sensor entities from the entity registry that are no longer used."""

        ent_reg = er.async_get(hass)
        old_suffixes = [
            "_badges",
            "_reward_claims",
            "_reward_approvals",
            "_chore_claims",
            "_chore_approvals",
            "_streak",
        ]

        for entity_id, entity_entry in list(ent_reg.entities.items()):
            if not entity_entry.unique_id.startswith(f"{entry.entry_id}_"):
                continue
            if any(entity_entry.unique_id.endswith(suffix) for suffix in old_suffixes):
                ent_reg.async_remove(entity_id)
                const.LOGGER.debug(
                    "Removed deprecated entity: %s (unique_id=%s)",
                    entity_id,
                    entity_entry.unique_id,
                )

    def remove_deprecated_button_entities(self) -> None:
        """Remove dynamic button entities that are not present in the current configuration."""
        ent_reg = er.async_get(self.hass)
        entry_prefix = f"{self.config_entry.entry_id}_"

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
            if entity_entry.domain != "button" or not entity_entry.unique_id.startswith(
                entry_prefix
            ):
                continue
            if entity_entry.unique_id not in allowed_uids:
                ent_reg.async_remove(entity_entry.entity_id)
                const.LOGGER.debug(
                    "Removed deprecated button entity: %s", entity_entry.entity_id
                )

    # -------------------------------------------------------------------------------------
    # Create/Update Entities
    # (Kids, Parents, Chores, Badges, Rewards, Penalties, Achievements and Challenges)
    # -------------------------------------------------------------------------------------

    # -- Kids
    def _create_kid(self, kid_id: str, kid_data: dict[str, Any]):
        self._data[const.DATA_KIDS][kid_id] = {
            const.DATA_KID_NAME: kid_data.get(const.DATA_KID_NAME, const.CONF_EMPTY),
            const.DATA_KID_POINTS: kid_data.get(
                const.DATA_KID_POINTS, const.DEFAULT_ZERO
            ),
            const.DATA_KID_BADGES: kid_data.get(const.DATA_KID_BADGES, []),
            const.DATA_KID_CLAIMED_CHORES: kid_data.get(
                const.DATA_KID_CLAIMED_CHORES, []
            ),
            const.DATA_KID_APPROVED_CHORES: kid_data.get(
                const.DATA_KID_APPROVED_CHORES, []
            ),
            const.DATA_KID_COMPLETED_CHORES_TODAY: kid_data.get(
                const.DATA_KID_COMPLETED_CHORES_TODAY, const.DEFAULT_ZERO
            ),
            const.DATA_KID_COMPLETED_CHORES_WEEKLY: kid_data.get(
                const.DATA_KID_COMPLETED_CHORES_WEEKLY, const.DEFAULT_ZERO
            ),
            const.DATA_KID_COMPLETED_CHORES_MONTHLY: kid_data.get(
                const.DATA_KID_COMPLETED_CHORES_MONTHLY, const.DEFAULT_ZERO
            ),
            const.DATA_KID_COMPLETED_CHORES_TOTAL: kid_data.get(
                const.DATA_KID_COMPLETED_CHORES_TOTAL, const.DEFAULT_ZERO
            ),
            const.DATA_KID_HA_USER_ID: kid_data.get(const.DATA_KID_HA_USER_ID),
            const.DATA_KID_INTERNAL_ID: kid_id,
            const.DATA_KID_POINTS_MULTIPLIER: kid_data.get(
                const.DATA_KID_POINTS_MULTIPLIER, const.DEFAULT_KID_POINTS_MULTIPLIER
            ),
            const.DATA_KID_REWARD_CLAIMS: kid_data.get(
                const.DATA_KID_REWARD_CLAIMS, {}
            ),
            const.DATA_KID_REWARD_APPROVALS: kid_data.get(
                const.DATA_KID_REWARD_APPROVALS, {}
            ),
            const.DATA_KID_CHORE_CLAIMS: kid_data.get(const.DATA_KID_CHORE_CLAIMS, {}),
            const.DATA_KID_CHORE_APPROVALS: kid_data.get(
                const.DATA_KID_CHORE_APPROVALS, {}
            ),
            const.DATA_KID_PENALTY_APPLIES: kid_data.get(
                const.DATA_KID_PENALTY_APPLIES, {}
            ),
            const.DATA_KID_BONUS_APPLIES: kid_data.get(
                const.DATA_KID_BONUS_APPLIES, {}
            ),
            const.DATA_KID_PENDING_REWARDS: kid_data.get(
                const.DATA_KID_PENDING_REWARDS, []
            ),
            const.DATA_KID_REDEEMED_REWARDS: kid_data.get(
                const.DATA_KID_REDEEMED_REWARDS, []
            ),
            const.DATA_KID_POINTS_EARNED_TODAY: kid_data.get(
                const.DATA_KID_POINTS_EARNED_TODAY, const.DEFAULT_ZERO
            ),
            const.DATA_KID_POINTS_EARNED_WEEKLY: kid_data.get(
                const.DATA_KID_POINTS_EARNED_WEEKLY, const.DEFAULT_ZERO
            ),
            const.DATA_KID_POINTS_EARNED_MONTHLY: kid_data.get(
                const.DATA_KID_POINTS_EARNED_MONTHLY, const.DEFAULT_ZERO
            ),
            const.DATA_KID_MAX_POINTS_EVER: kid_data.get(
                const.DATA_KID_MAX_POINTS_EVER, const.DEFAULT_ZERO
            ),
            const.DATA_KID_ENABLE_NOTIFICATIONS: kid_data.get(
                const.DATA_KID_ENABLE_NOTIFICATIONS, True
            ),
            const.DATA_KID_MOBILE_NOTIFY_SERVICE: kid_data.get(
                const.DATA_KID_MOBILE_NOTIFY_SERVICE, const.CONF_EMPTY
            ),
            const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS: kid_data.get(
                const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS, True
            ),
            const.DATA_KID_CHORE_STREAKS: {},
            const.DATA_KID_OVERALL_CHORE_STREAK: const.DEFAULT_ZERO,
            const.DATA_KID_LAST_CHORE_DATE: None,
            const.DATA_KID_OVERDUE_CHORES: [],
            const.DATA_KID_OVERDUE_NOTIFICATIONS: {},
        }

        self._normalize_kid_lists(self._data[const.DATA_KIDS][kid_id])

        const.LOGGER.debug(
            "Added new kid '%s' with ID: %s",
            self._data[const.DATA_KIDS][kid_id][const.DATA_KID_NAME],
            kid_id,
        )

    def _update_kid(self, kid_id: str, kid_data: dict[str, Any]):
        kid_info = self._data[const.DATA_KIDS][kid_id]

        # Overwrite or set default if not present
        kid_info[const.DATA_KID_NAME] = kid_data.get(
            const.DATA_KID_NAME, kid_info[const.DATA_KID_NAME]
        )
        kid_info[const.DATA_KID_HA_USER_ID] = kid_data.get(
            const.DATA_KID_HA_USER_ID, kid_info[const.DATA_KID_HA_USER_ID]
        )
        kid_info.setdefault(
            const.DATA_KID_REWARD_CLAIMS, kid_data.get(const.DATA_KID_REWARD_CLAIMS, {})
        )
        kid_info.setdefault(
            const.DATA_KID_REWARD_APPROVALS,
            kid_data.get(const.DATA_KID_REWARD_APPROVALS, {}),
        )
        kid_info.setdefault(
            const.DATA_KID_CHORE_CLAIMS, kid_data.get(const.DATA_KID_CHORE_CLAIMS, {})
        )
        kid_info.setdefault(
            const.DATA_KID_CHORE_APPROVALS,
            kid_data.get(const.DATA_KID_CHORE_APPROVALS, {}),
        )
        kid_info.setdefault(
            const.DATA_KID_PENALTY_APPLIES,
            kid_data.get(const.DATA_KID_PENALTY_APPLIES, {}),
        )
        kid_info.setdefault(
            const.DATA_KID_BONUS_APPLIES, kid_data.get(const.DATA_KID_BONUS_APPLIES, {})
        )
        kid_info.setdefault(
            const.DATA_KID_PENDING_REWARDS,
            kid_data.get(const.DATA_KID_PENDING_REWARDS, []),
        )
        kid_info.setdefault(
            const.DATA_KID_REDEEMED_REWARDS,
            kid_data.get(const.DATA_KID_REDEEMED_REWARDS, []),
        )
        kid_info.setdefault(
            const.DATA_KID_POINTS_EARNED_TODAY,
            kid_data.get(const.DATA_KID_POINTS_EARNED_TODAY, const.DEFAULT_ZERO),
        )
        kid_info.setdefault(
            const.DATA_KID_POINTS_EARNED_WEEKLY,
            kid_data.get(const.DATA_KID_POINTS_EARNED_WEEKLY, const.DEFAULT_ZERO),
        )
        kid_info.setdefault(
            const.DATA_KID_POINTS_EARNED_MONTHLY,
            kid_data.get(const.DATA_KID_POINTS_EARNED_MONTHLY, const.DEFAULT_ZERO),
        )
        kid_info.setdefault(
            const.DATA_KID_MAX_POINTS_EVER,
            kid_data.get(const.DATA_KID_MAX_POINTS_EVER, const.DEFAULT_ZERO),
        )
        kid_info.setdefault(
            const.DATA_KID_POINTS_MULTIPLIER,
            kid_data.get(
                const.DATA_KID_POINTS_MULTIPLIER, const.DEFAULT_KID_POINTS_MULTIPLIER
            ),
        )
        kid_info[const.DATA_KID_ENABLE_NOTIFICATIONS] = kid_data.get(
            const.DATA_KID_ENABLE_NOTIFICATIONS,
            kid_info.get(const.DATA_KID_ENABLE_NOTIFICATIONS, True),
        )
        kid_info[const.DATA_KID_MOBILE_NOTIFY_SERVICE] = kid_data.get(
            const.DATA_KID_MOBILE_NOTIFY_SERVICE,
            kid_info.get(const.DATA_KID_MOBILE_NOTIFY_SERVICE, const.CONF_EMPTY),
        )
        kid_info[const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS] = kid_data.get(
            const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS,
            kid_info.get(const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS, True),
        )
        kid_info.setdefault(const.DATA_KID_CHORE_STREAKS, {})
        kid_info.setdefault(const.DATA_KID_OVERALL_CHORE_STREAK, const.DEFAULT_ZERO)
        kid_info.setdefault(const.DATA_KID_LAST_CHORE_DATE, None)
        kid_info.setdefault(const.DATA_KID_OVERDUE_CHORES, [])
        kid_info.setdefault(const.DATA_KID_OVERDUE_NOTIFICATIONS, {})

        self._normalize_kid_lists(self._data[const.DATA_KIDS][kid_id])

        const.LOGGER.debug(
            "Updated kid '%s' with ID: %s", kid_info[const.DATA_KID_NAME], kid_id
        )

    # -- Parents
    def _create_parent(self, parent_id: str, parent_data: dict[str, Any]):
        associated_kids_ids = []
        for kid_id in parent_data.get(const.DATA_PARENT_ASSOCIATED_KIDS, []):
            if kid_id in self.kids_data:
                associated_kids_ids.append(kid_id)
            else:
                const.LOGGER.warning(
                    "Parent '%s': Kid ID '%s' not found. Skipping assignment to parent",
                    parent_data.get(const.DATA_PARENT_NAME, parent_id),
                    kid_id,
                )

        self._data[const.DATA_PARENTS][parent_id] = {
            const.DATA_PARENT_NAME: parent_data.get(
                const.DATA_PARENT_NAME, const.CONF_EMPTY
            ),
            const.DATA_PARENT_HA_USER_ID: parent_data.get(
                const.DATA_PARENT_HA_USER_ID, const.CONF_EMPTY
            ),
            const.DATA_PARENT_ASSOCIATED_KIDS: associated_kids_ids,
            const.DATA_PARENT_ENABLE_NOTIFICATIONS: parent_data.get(
                const.DATA_PARENT_ENABLE_NOTIFICATIONS, True
            ),
            const.DATA_PARENT_MOBILE_NOTIFY_SERVICE: parent_data.get(
                const.DATA_PARENT_MOBILE_NOTIFY_SERVICE, const.CONF_EMPTY
            ),
            const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS: parent_data.get(
                const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS, True
            ),
            const.DATA_PARENT_INTERNAL_ID: parent_id,
        }
        const.LOGGER.debug(
            "Added new parent '%s' with ID: %s",
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
                    "Parent '%s': Kid ID '%s' not found. Skipping assignment",
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
            parent_info.get(const.DATA_PARENT_MOBILE_NOTIFY_SERVICE, const.CONF_EMPTY),
        )
        parent_info[const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS] = parent_data.get(
            const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS,
            parent_info.get(const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS, True),
        )

        const.LOGGER.debug(
            "Updated parent '%s' with ID: %s",
            parent_info[const.DATA_PARENT_NAME],
            parent_id,
        )

    # -- Chores
    def _create_chore(self, chore_id: str, chore_data: dict[str, Any]):
        assigned_kids_ids = []
        for kid_name in chore_data.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            kid_id = kh.get_kid_id_by_name(self, kid_name)
            if kid_id:
                assigned_kids_ids.append(kid_id)
            else:
                const.LOGGER.warning(
                    "Chore '%s': Kid name '%s' not found. Skipping assignment",
                    chore_data.get(const.DATA_CHORE_NAME, chore_id),
                    kid_name,
                )

        # If chore is recurring, set due_date to creation date if not set
        freq = chore_data.get(
            const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
        )
        if freq != const.FREQUENCY_NONE and not chore_data.get(
            const.DATA_CHORE_DUE_DATE
        ):
            now_local = dt_util.utcnow().astimezone(
                dt_util.get_time_zone(self.hass.config.time_zone)
            )
            # Force the time to 23:59:00 (and zero microseconds)
            default_due = now_local.replace(**const.DEFAULT_DUE_TIME)
            chore_data[const.DATA_CHORE_DUE_DATE] = default_due.isoformat()
            const.LOGGER.debug(
                "Chore '%s' has freq '%s' but no due_date. Defaulting to 23:59 local time: %s",
                chore_data.get(const.DATA_CHORE_NAME, chore_id),
                freq,
                chore_data[const.DATA_CHORE_DUE_DATE],
            )

        self._data[const.DATA_CHORES][chore_id] = {
            const.DATA_CHORE_NAME: chore_data.get(
                const.DATA_CHORE_NAME, const.CONF_EMPTY
            ),
            const.DATA_CHORE_STATE: chore_data.get(
                const.DATA_CHORE_STATE, const.CHORE_STATE_PENDING
            ),
            const.DATA_CHORE_DEFAULT_POINTS: chore_data.get(
                const.DATA_CHORE_DEFAULT_POINTS, const.DEFAULT_POINTS
            ),
            const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY: chore_data.get(
                const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY,
                const.DEFAULT_MULTIPLE_CLAIMS_PER_DAY,
            ),
            const.DATA_CHORE_PARTIAL_ALLOWED: chore_data.get(
                const.DATA_CHORE_PARTIAL_ALLOWED, const.DEFAULT_PARTIAL_ALLOWED
            ),
            const.DATA_CHORE_DESCRIPTION: chore_data.get(
                const.DATA_CHORE_DESCRIPTION, const.CONF_EMPTY
            ),
            const.DATA_CHORE_LABELS: chore_data.get(const.DATA_CHORE_LABELS, []),
            const.DATA_CHORE_ICON: chore_data.get(
                const.DATA_CHORE_ICON, const.DEFAULT_ICON
            ),
            const.DATA_CHORE_SHARED_CHORE: chore_data.get(
                const.DATA_CHORE_SHARED_CHORE, False
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
            const.DATA_CHORE_INTERNAL_ID: chore_id,
        }
        const.LOGGER.debug(
            "Added new chore '%s' with ID: %s",
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
                self._notify_kid(
                    kid_id,
                    title="KidsChores: New Chore",
                    message=f"A new chore '{new_name}' was assigned to you! Due: {due_str}",
                    extra_data=extra_data,
                )
            )

    def _update_chore(self, chore_id: str, chore_data: dict[str, Any]):
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
        chore_info[const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY] = chore_data.get(
            const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY,
            chore_info[const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY],
        )
        chore_info[const.DATA_CHORE_PARTIAL_ALLOWED] = chore_data.get(
            const.DATA_CHORE_PARTIAL_ALLOWED,
            chore_info[const.DATA_CHORE_PARTIAL_ALLOWED],
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
        chore_info[const.DATA_CHORE_SHARED_CHORE] = chore_data.get(
            const.DATA_CHORE_SHARED_CHORE, chore_info[const.DATA_CHORE_SHARED_CHORE]
        )

        assigned_kids_ids = []
        for kid_name in chore_data.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            kid_id = kh.get_kid_id_by_name(self, kid_name)
            if kid_id:
                assigned_kids_ids.append(kid_id)
            else:
                const.LOGGER.warning(
                    "Chore '%s': Kid name '%s' not found. Skipping assignment",
                    chore_data.get(const.DATA_CHORE_NAME, chore_id),
                    kid_name,
                )
        old_assigned = set(chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []))
        new_assigned = set(assigned_kids_ids)
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
        chore_info[const.DATA_CHORE_DUE_DATE] = chore_data.get(
            const.DATA_CHORE_DUE_DATE, chore_info[const.DATA_CHORE_DUE_DATE]
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

        const.LOGGER.debug(
            "Updated chore '%s' with ID: %s",
            chore_info[const.DATA_CHORE_NAME],
            chore_id,
        )

        self.hass.async_create_task(self._check_overdue_chores())

    # -- Badges
    def _create_badge(self, badge_id: str, badge_data: dict[str, Any]):
        """Create a new badge entity."""

        # Base fields common to all types:
        self._data[const.DATA_BADGES][badge_id] = {
            const.DATA_BADGE_NAME: badge_data.get(
                const.DATA_BADGE_NAME, const.CONF_EMPTY
            ),
            const.DATA_BADGE_DESCRIPTION: badge_data.get(
                const.DATA_BADGE_DESCRIPTION, const.CONF_EMPTY
            ),
            const.DATA_BADGE_LABELS: badge_data.get(const.DATA_BADGE_LABELS, []),
            const.DATA_BADGE_ICON: badge_data.get(
                const.DATA_BADGE_ICON, const.DEFAULT_ICON
            ),
            const.DATA_BADGE_INTERNAL_ID: badge_id,
            const.DATA_BADGE_TYPE: badge_data.get(
                const.DATA_BADGE_TYPE, const.BADGE_TYPE_CUMULATIVE
            ),
            const.DATA_BADGE_AWARD_MODE: badge_data.get(
                const.DATA_BADGE_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE
            ),
            const.DATA_BADGE_AWARD_POINTS: badge_data.get(
                const.DATA_BADGE_AWARD_POINTS, const.DEFAULT_BADGE_AWARD_POINTS
            ),
            const.DATA_BADGE_AWARD_REWARD: badge_data.get(
                const.DATA_BADGE_AWARD_REWARD, const.CONF_EMPTY
            ),
        }

        # For non‑cumulative badges, store assigned kids
        if (
            self._data[const.DATA_BADGES][badge_id].get(const.DATA_BADGE_TYPE)
            != const.BADGE_TYPE_CUMULATIVE
        ):
            self._data[const.DATA_BADGES][badge_id][const.DATA_BADGE_ASSIGNED_KIDS] = (
                badge_data.get(const.DATA_BADGE_ASSIGNED_KIDS, [])
            )

        badge_type = badge_data.get(const.DATA_BADGE_TYPE, const.BADGE_TYPE_CUMULATIVE)
        if badge_type == const.BADGE_TYPE_CUMULATIVE:
            self._data[const.DATA_BADGES][badge_id].update(
                {
                    const.DATA_BADGE_THRESHOLD_TYPE: const.CONF_POINTS,
                    const.DATA_BADGE_THRESHOLD_VALUE: badge_data.get(
                        const.DATA_BADGE_THRESHOLD_VALUE,
                        const.DEFAULT_BADGE_THRESHOLD_VALUE,
                    ),
                    const.DATA_BADGE_POINTS_MULTIPLIER: badge_data.get(
                        const.DATA_BADGE_POINTS_MULTIPLIER,
                        const.DEFAULT_POINTS_MULTIPLIER,
                    ),
                    const.DATA_BADGE_RESET_PERIODICALLY: badge_data.get(
                        const.DATA_BADGE_RESET_PERIODICALLY, False
                    ),
                    const.DATA_BADGE_RESET_TYPE: badge_data.get(
                        const.DATA_BADGE_RESET_TYPE, const.CONF_YEAR_END
                    ),
                    const.DATA_BADGE_CUSTOM_RESET_DATE: badge_data.get(
                        const.DATA_BADGE_CUSTOM_RESET_DATE, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_RESET_GRACE_PERIOD: badge_data.get(
                        const.DATA_BADGE_RESET_GRACE_PERIOD,
                        const.DEFAULT_BADGE_RESET_GRACE_PERIOD,
                    ),
                    const.DATA_BADGE_MAINTENANCE_RULES: badge_data.get(
                        const.DATA_BADGE_MAINTENANCE_RULES,
                        const.DEFAULT_BADGE_MAINTENANCE_THRESHOLD,
                    ),
                }
            )
        elif badge_type == const.BADGE_TYPE_DAILY:
            self._data[const.DATA_BADGES][badge_id].update(
                {
                    const.DATA_BADGE_DAILY_THRESHOLD: badge_data.get(
                        const.DATA_BADGE_DAILY_THRESHOLD
                    ),
                    const.DATA_BADGE_REWARD: badge_data.get(const.DATA_BADGE_REWARD),
                }
            )
        elif badge_type == const.BADGE_TYPE_PERIODIC:
            self._data[const.DATA_BADGES][badge_id].update(
                {
                    const.DATA_BADGE_RESET_SCHEDULE: badge_data.get(
                        const.DATA_BADGE_RESET_SCHEDULE, const.CONF_WEEKLY
                    ),
                    const.DATA_BADGE_START_DATE: badge_data.get(
                        const.DATA_BADGE_START_DATE, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_END_DATE: badge_data.get(
                        const.DATA_BADGE_END_DATE, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_PERIODIC_RECURRENT: badge_data.get(
                        const.DATA_BADGE_PERIODIC_RECURRENT, False
                    ),
                    const.DATA_BADGE_THRESHOLD_TYPE: badge_data.get(
                        const.DATA_BADGE_THRESHOLD_TYPE,
                        const.DEFAULT_BADGE_THRESHOLD_TYPE,
                    ),
                    const.DATA_BADGE_REQUIRED_CHORES: badge_data.get(
                        const.DATA_BADGE_REQUIRED_CHORES, []
                    ),
                    const.DATA_BADGE_THRESHOLD_VALUE: badge_data.get(
                        const.DATA_BADGE_THRESHOLD_VALUE,
                        const.DEFAULT_BADGE_THRESHOLD_VALUE,
                    ),
                    const.DATA_BADGE_LAST_RESET: None,
                }
            )
        elif badge_type == const.BADGE_TYPE_ACHIEVEMENT_LINKED:
            self._data[const.DATA_BADGES][badge_id].update(
                {
                    const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT: badge_data.get(
                        const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT, const.CONF_EMPTY
                    ),
                }
            )
        elif badge_type == const.BADGE_TYPE_CHALLENGE_LINKED:
            self._data[const.DATA_BADGES][badge_id].update(
                {
                    const.DATA_BADGE_ASSOCIATED_CHALLENGE: badge_data.get(
                        const.DATA_BADGE_ASSOCIATED_CHALLENGE, const.CONF_EMPTY
                    ),
                }
            )
        elif badge_type == const.BADGE_TYPE_SPECIAL_OCCASION:
            self._data[const.DATA_BADGES][badge_id].update(
                {
                    const.DATA_BADGE_OCCASION_TYPE: badge_data.get(
                        const.DATA_BADGE_OCCASION_TYPE, const.CONF_HOLIDAY
                    ),
                    const.DATA_BADGE_SPECIAL_OCCASION_DATE: badge_data.get(
                        const.DATA_BADGE_SPECIAL_OCCASION_DATE, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_SPECIAL_OCCASION_RECURRENCY: badge_data.get(
                        const.DATA_BADGE_SPECIAL_OCCASION_RECURRENCY, False
                    ),
                    const.DATA_BADGE_ASSIGNED_KIDS: badge_data.get(
                        const.DATA_BADGE_ASSIGNED_KIDS, []
                    ),
                }
            )
        const.LOGGER.debug(
            "Added new badge '%s' with ID: %s",
            self._data[const.DATA_BADGES][badge_id][const.DATA_BADGE_NAME],
            badge_id,
        )

    def _update_badge(self, badge_id: str, badge_data: dict[str, Any]):
        """Update an existing badge entity."""

        badge_info = self._data[const.DATA_BADGES][badge_id]
        badge_info[const.DATA_BADGE_NAME] = badge_data.get(
            const.DATA_BADGE_NAME, badge_info[const.DATA_BADGE_NAME]
        )
        badge_info[const.DATA_BADGE_DESCRIPTION] = badge_data.get(
            const.DATA_BADGE_DESCRIPTION,
            badge_info[const.DATA_BADGE_DESCRIPTION],
        )
        badge_info[const.DATA_BADGE_LABELS] = badge_data.get(
            const.DATA_BADGE_LABELS,
            badge_info.get(const.DATA_BADGE_LABELS, []),
        )
        badge_info[const.DATA_BADGE_ICON] = badge_data.get(
            const.DATA_BADGE_ICON,
            badge_info.get(const.DATA_BADGE_ICON, const.DEFAULT_ICON),
        )
        badge_type = badge_data.get(
            const.DATA_BADGE_TYPE,
            badge_info.get(const.DATA_BADGE_TYPE, const.BADGE_TYPE_CUMULATIVE),
        )
        badge_info[const.DATA_BADGE_AWARD_MODE] = badge_data.get(
            const.DATA_BADGE_AWARD_MODE,
            badge_info.get(const.DATA_BADGE_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE),
        )
        badge_info[const.DATA_BADGE_AWARD_POINTS] = badge_data.get(
            const.DATA_BADGE_AWARD_POINTS,
            badge_info.get(
                const.DATA_BADGE_AWARD_POINTS, const.DEFAULT_BADGE_AWARD_POINTS
            ),
        )
        badge_info[const.DATA_BADGE_AWARD_REWARD] = badge_data.get(
            const.DATA_BADGE_AWARD_REWARD,
            badge_info.get(const.DATA_BADGE_AWARD_REWARD, const.CONF_EMPTY),
        )

        badge_info[const.DATA_BADGE_TYPE] = badge_type

        # For non‑cumulative badges, update the "assigned_kids" field
        if badge_type != const.BADGE_TYPE_CUMULATIVE:
            badge_info[const.DATA_BADGE_ASSIGNED_KIDS] = badge_data.get(
                const.DATA_BADGE_ASSIGNED_KIDS,
                badge_info.get(const.DATA_BADGE_ASSIGNED_KIDS, []),
            )

        if badge_type == const.BADGE_TYPE_CUMULATIVE:
            badge_info[const.DATA_BADGE_THRESHOLD_VALUE] = badge_data.get(
                const.DATA_BADGE_THRESHOLD_VALUE,
                badge_info.get(
                    const.DATA_BADGE_THRESHOLD_VALUE,
                    const.DEFAULT_BADGE_THRESHOLD_VALUE,
                ),
            )
            badge_info[const.DATA_BADGE_POINTS_MULTIPLIER] = badge_data.get(
                const.DATA_BADGE_POINTS_MULTIPLIER,
                badge_info.get(
                    const.DATA_BADGE_POINTS_MULTIPLIER, const.DEFAULT_POINTS_MULTIPLIER
                ),
            )
            badge_info[const.DATA_BADGE_RESET_PERIODICALLY] = badge_data.get(
                const.DATA_BADGE_RESET_PERIODICALLY,
                badge_info.get(const.DATA_BADGE_RESET_PERIODICALLY, False),
            )
            badge_info[const.DATA_BADGE_RESET_TYPE] = badge_data.get(
                const.DATA_BADGE_RESET_TYPE,
                badge_info.get(const.DATA_BADGE_RESET_TYPE, const.CONF_YEAR_END),
            )
            badge_info[const.DATA_BADGE_CUSTOM_RESET_DATE] = badge_data.get(
                const.DATA_BADGE_CUSTOM_RESET_DATE,
                badge_info.get(const.DATA_BADGE_CUSTOM_RESET_DATE, const.CONF_EMPTY),
            )
            badge_info[const.DATA_BADGE_RESET_GRACE_PERIOD] = badge_data.get(
                const.DATA_BADGE_RESET_GRACE_PERIOD,
                badge_info.get(
                    const.DATA_BADGE_RESET_GRACE_PERIOD,
                    const.DEFAULT_BADGE_RESET_GRACE_PERIOD,
                ),
            )
            badge_info[const.DATA_BADGE_MAINTENANCE_RULES] = badge_data.get(
                const.DATA_BADGE_MAINTENANCE_RULES,
                badge_info.get(
                    const.DATA_BADGE_MAINTENANCE_RULES,
                    const.DEFAULT_BADGE_MAINTENANCE_THRESHOLD,
                ),
            )
        elif badge_type == const.BADGE_TYPE_DAILY:
            badge_info[const.DATA_BADGE_DAILY_THRESHOLD] = badge_data.get(
                const.DATA_BADGE_DAILY_THRESHOLD,
                badge_info.get(const.DATA_BADGE_DAILY_THRESHOLD),
            )
            badge_info[const.DATA_BADGE_REWARD] = badge_data.get(
                const.DATA_BADGE_REWARD, badge_info.get(const.DATA_BADGE_REWARD)
            )
        elif badge_type == const.BADGE_TYPE_PERIODIC:
            badge_info[const.DATA_BADGE_RESET_SCHEDULE] = badge_data.get(
                const.DATA_BADGE_RESET_SCHEDULE,
                badge_info.get(const.DATA_BADGE_RESET_SCHEDULE, const.CONF_WEEKLY),
            )
            badge_info[const.DATA_BADGE_START_DATE] = badge_data.get(
                const.DATA_BADGE_START_DATE,
                badge_info.get(const.DATA_BADGE_START_DATE, const.CONF_EMPTY),
            )
            badge_info[const.DATA_BADGE_END_DATE] = badge_data.get(
                const.DATA_BADGE_END_DATE,
                badge_info.get(const.DATA_BADGE_END_DATE, const.CONF_EMPTY),
            )
            badge_info[const.DATA_BADGE_PERIODIC_RECURRENT] = badge_data.get(
                const.DATA_BADGE_PERIODIC_RECURRENT,
                badge_info.get(const.DATA_BADGE_PERIODIC_RECURRENT, False),
            )
            badge_info[const.DATA_BADGE_THRESHOLD_TYPE] = badge_data.get(
                const.DATA_BADGE_THRESHOLD_TYPE,
                badge_info.get(
                    const.DATA_BADGE_THRESHOLD_TYPE, const.DEFAULT_BADGE_THRESHOLD_TYPE
                ),
            )
            badge_info[const.DATA_BADGE_REQUIRED_CHORES] = badge_data.get(
                const.DATA_BADGE_REQUIRED_CHORES,
                badge_info.get(const.DATA_BADGE_REQUIRED_CHORES, []),
            )
            badge_info[const.DATA_BADGE_THRESHOLD_VALUE] = badge_data.get(
                const.DATA_BADGE_THRESHOLD_VALUE,
                badge_info.get(
                    const.DATA_BADGE_THRESHOLD_VALUE,
                    const.DEFAULT_BADGE_THRESHOLD_VALUE,
                ),
            )

        elif badge_type == const.BADGE_TYPE_ACHIEVEMENT_LINKED:
            badge_info[const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT] = badge_data.get(
                const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT,
                badge_info.get(
                    const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT, const.CONF_EMPTY
                ),
            )

        elif badge_type == const.BADGE_TYPE_CHALLENGE_LINKED:
            badge_info[const.DATA_BADGE_ASSOCIATED_CHALLENGE] = badge_data.get(
                const.DATA_BADGE_ASSOCIATED_CHALLENGE,
                badge_info.get(const.DATA_BADGE_ASSOCIATED_CHALLENGE, const.CONF_EMPTY),
            )

        elif badge_type == const.BADGE_TYPE_SPECIAL_OCCASION:
            badge_info[const.DATA_BADGE_OCCASION_TYPE] = badge_data.get(
                const.DATA_BADGE_OCCASION_TYPE,
                badge_info.get(const.DATA_BADGE_OCCASION_TYPE, const.CONF_HOLIDAY),
            )
            badge_info[const.DATA_BADGE_SPECIAL_OCCASION_DATE] = badge_data.get(
                const.DATA_BADGE_SPECIAL_OCCASION_DATE,
                badge_info.get(
                    const.DATA_BADGE_SPECIAL_OCCASION_DATE, const.CONF_EMPTY
                ),
            )
            badge_info[const.DATA_BADGE_SPECIAL_OCCASION_RECURRENCY] = badge_data.get(
                const.DATA_BADGE_SPECIAL_OCCASION_RECURRENCY,
                badge_info.get(const.DATA_BADGE_SPECIAL_OCCASION_RECURRENCY, False),
            )
            badge_info[const.DATA_BADGE_ASSIGNED_KIDS] = badge_data.get(
                const.DATA_BADGE_ASSIGNED_KIDS,
                badge_info[const.DATA_BADGE_ASSIGNED_KIDS],
            )

        const.LOGGER.debug(
            "Updated badge '%s' with ID: %s",
            badge_info[const.DATA_BADGE_NAME],
            badge_id,
        )

    # -- Rewards
    def _create_reward(self, reward_id: str, reward_data: dict[str, Any]):
        self._data[const.DATA_REWARDS][reward_id] = {
            const.DATA_REWARD_NAME: reward_data.get(
                const.DATA_REWARD_NAME, const.CONF_EMPTY
            ),
            const.DATA_REWARD_COST: reward_data.get(
                const.DATA_REWARD_COST, const.DEFAULT_REWARD_COST
            ),
            const.DATA_REWARD_DESCRIPTION: reward_data.get(
                const.DATA_REWARD_DESCRIPTION, const.CONF_EMPTY
            ),
            const.DATA_REWARD_LABELS: reward_data.get(const.DATA_REWARD_LABELS, []),
            const.DATA_REWARD_ICON: reward_data.get(
                const.DATA_REWARD_ICON, const.DEFAULT_REWARD_ICON
            ),
            const.DATA_REWARD_INTERNAL_ID: reward_id,
        }
        const.LOGGER.debug(
            "Added new reward '%s' with ID: %s",
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
            "Updated reward '%s' with ID: %s",
            reward_info[const.DATA_REWARD_NAME],
            reward_id,
        )

    # -- Bonuses
    def _create_bonus(self, bonus_id: str, bonus_data: dict[str, Any]):
        self._data[const.DATA_BONUSES][bonus_id] = {
            const.DATA_BONUS_NAME: bonus_data.get(
                const.DATA_BONUS_NAME, const.CONF_EMPTY
            ),
            const.DATA_BONUS_POINTS: bonus_data.get(
                const.DATA_BONUS_POINTS, const.DEFAULT_BONUS_POINTS
            ),
            const.DATA_BONUS_DESCRIPTION: bonus_data.get(
                const.DATA_BONUS_DESCRIPTION, const.CONF_EMPTY
            ),
            const.DATA_BONUS_LABELS: bonus_data.get(const.DATA_BONUS_LABELS, []),
            const.DATA_BONUS_ICON: bonus_data.get(
                const.DATA_BONUS_ICON, const.DEFAULT_BONUS_ICON
            ),
            const.DATA_BONUS_INTERNAL_ID: bonus_id,
        }
        const.LOGGER.debug(
            "Added new bonus '%s' with ID: %s",
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
            "Updated bonus '%s' with ID: %s",
            bonus_info[const.DATA_BONUS_NAME],
            bonus_id,
        )

    # -- Penalties
    def _create_penalty(self, penalty_id: str, penalty_data: dict[str, Any]):
        self._data[const.DATA_PENALTIES][penalty_id] = {
            const.DATA_PENALTY_NAME: penalty_data.get(
                const.DATA_PENALTY_NAME, const.CONF_EMPTY
            ),
            const.DATA_PENALTY_POINTS: penalty_data.get(
                const.DATA_PENALTY_POINTS, -const.DEFAULT_PENALTY_POINTS
            ),
            const.DATA_PENALTY_DESCRIPTION: penalty_data.get(
                const.DATA_PENALTY_DESCRIPTION, const.CONF_EMPTY
            ),
            const.DATA_PENALTY_LABELS: penalty_data.get(const.DATA_PENALTY_LABELS, []),
            const.DATA_PENALTY_ICON: penalty_data.get(
                const.DATA_PENALTY_ICON, const.DEFAULT_PENALTY_ICON
            ),
            const.DATA_PENALTY_INTERNAL_ID: penalty_id,
        }
        const.LOGGER.debug(
            "Added new penalty '%s' with ID: %s",
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
            "Updated penalty '%s' with ID: %s",
            penalty_info[const.DATA_PENALTY_NAME],
            penalty_id,
        )

    # -- Achievements
    def _create_achievement(
        self, achievement_id: str, achievement_data: dict[str, Any]
    ):
        self._data[const.DATA_ACHIEVEMENTS][achievement_id] = {
            const.DATA_ACHIEVEMENT_NAME: achievement_data.get(
                const.DATA_ACHIEVEMENT_NAME, const.CONF_EMPTY
            ),
            const.DATA_ACHIEVEMENT_DESCRIPTION: achievement_data.get(
                const.DATA_ACHIEVEMENT_DESCRIPTION, const.CONF_EMPTY
            ),
            const.DATA_ACHIEVEMENT_LABELS: achievement_data.get(
                const.DATA_ACHIEVEMENT_LABELS, []
            ),
            const.DATA_ACHIEVEMENT_ICON: achievement_data.get(
                const.DATA_ACHIEVEMENT_ICON, const.CONF_EMPTY
            ),
            const.DATA_ACHIEVEMENT_ASSIGNED_KIDS: achievement_data.get(
                const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, []
            ),
            const.DATA_ACHIEVEMENT_TYPE: achievement_data.get(
                const.DATA_ACHIEVEMENT_TYPE, const.ACHIEVEMENT_TYPE_STREAK
            ),
            const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID: achievement_data.get(
                const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID, const.CONF_EMPTY
            ),
            const.DATA_ACHIEVEMENT_CRITERIA: achievement_data.get(
                const.DATA_ACHIEVEMENT_CRITERIA, const.CONF_EMPTY
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
            "Added new achievement '%s' with ID: %s",
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
                    const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID, const.CONF_EMPTY
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
            "Updated achievement '%s' with ID: %s",
            achievement_info[const.DATA_ACHIEVEMENT_NAME],
            achievement_id,
        )

    # -- Challenges
    def _create_challenge(self, challenge_id: str, challenge_data: dict[str, Any]):
        self._data[const.DATA_CHALLENGES][challenge_id] = {
            const.DATA_CHALLENGE_NAME: challenge_data.get(
                const.DATA_CHALLENGE_NAME, const.CONF_EMPTY
            ),
            const.DATA_CHALLENGE_DESCRIPTION: challenge_data.get(
                const.DATA_CHALLENGE_DESCRIPTION, const.CONF_EMPTY
            ),
            const.DATA_CHALLENGE_LABELS: challenge_data.get(
                const.DATA_CHALLENGE_LABELS, []
            ),
            const.DATA_CHALLENGE_ICON: challenge_data.get(
                const.DATA_CHALLENGE_ICON, const.CONF_EMPTY
            ),
            const.DATA_CHALLENGE_ASSIGNED_KIDS: challenge_data.get(
                const.DATA_CHALLENGE_ASSIGNED_KIDS, []
            ),
            const.DATA_CHALLENGE_TYPE: challenge_data.get(
                const.DATA_CHALLENGE_TYPE, const.CHALLENGE_TYPE_DAILY_MIN
            ),
            const.DATA_CHALLENGE_SELECTED_CHORE_ID: challenge_data.get(
                const.DATA_CHALLENGE_SELECTED_CHORE_ID, const.CONF_EMPTY
            ),
            const.DATA_CHALLENGE_CRITERIA: challenge_data.get(
                const.DATA_CHALLENGE_CRITERIA, const.CONF_EMPTY
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
            "Added new challenge '%s' with ID: %s",
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
                const.DATA_CHALLENGE_SELECTED_CHORE_ID, const.CONF_EMPTY
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
            "Updated challenge '%s' with ID: %s",
            challenge_info[const.DATA_CHALLENGE_NAME],
            challenge_id,
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

    # -------------------------------------------------------------------------------------
    # Chores: Claim, Approve, Disapprove, Compute Global State for Shared Chores
    # -------------------------------------------------------------------------------------

    def claim_chore(self, kid_id: str, chore_id: str, user_name: str):
        """Kid claims chore => state=claimed; parent must then approve."""
        if chore_id not in self.chores_data:
            const.LOGGER.warning("Chore ID '%s' not found for claim", chore_id)
            raise HomeAssistantError(f"Chore with ID '{chore_id}' not found.")

        chore_info = self.chores_data[chore_id]
        if kid_id not in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            const.LOGGER.warning(
                "Claim chore: Chore ID '%s' not assigned to kid ID '%s'",
                chore_id,
                kid_id,
            )
            raise HomeAssistantError(
                f"Chore '{chore_info.get(const.DATA_CHORE_NAME)}' is not assigned to kid '{self.kids_data[kid_id][const.DATA_KID_NAME]}'."
            )

        if kid_id not in self.kids_data:
            const.LOGGER.warning("Kid ID '%s' not found", kid_id)
            raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

        kid_info = self.kids_data.get(kid_id)

        self._normalize_kid_lists(kid_info)

        allow_multiple = chore_info.get(
            const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY, False
        )
        if allow_multiple:
            # If already approved, remove it so the new claim can trigger a new approval flow
            kid_info[const.DATA_KID_APPROVED_CHORES] = [
                item
                for item in kid_info.get(const.DATA_KID_APPROVED_CHORES, [])
                if item != chore_id
            ]

        if not allow_multiple:
            if chore_id in kid_info.get(
                const.DATA_KID_CLAIMED_CHORES, []
            ) or chore_id in kid_info.get(const.DATA_KID_APPROVED_CHORES, []):
                error_message = f"Chore '{chore_info[const.DATA_CHORE_NAME]}' has already been claimed today and multiple claims are not allowed."
                const.LOGGER.warning(error_message)
                raise HomeAssistantError(error_message)

        self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_CLAIMED)

        # Send a notification to the parents that a kid claimed a chore
        if chore_info.get(const.CONF_NOTIFY_ON_CLAIM, const.DEFAULT_NOTIFY_ON_CLAIM):
            actions = [
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_CHORE}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_APPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_CHORE}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_DISAPPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_REMIND_30,
                },
            ]
            # Pass extra context so the event handler can route the action.
            extra_data = {
                const.DATA_KID_ID: kid_id,
                const.DATA_CHORE_ID: chore_id,
            }
            self.hass.async_create_task(
                self._notify_parents(
                    kid_id,
                    title="KidsChores: Chore Claimed",
                    message=f"'{self.kids_data[kid_id][const.DATA_KID_NAME]}' claimed chore '{self.chores_data[chore_id][const.DATA_CHORE_NAME]}'",
                    actions=actions,
                    extra_data=extra_data,
                )
            )

        self._persist()
        self.async_set_updated_data(self._data)

    def approve_chore(
        self,
        parent_name: str,
        kid_id: str,
        chore_id: str,
        points_awarded: Optional[float] = None,
    ):
        """Approve a chore for kid_id if assigned."""
        if chore_id not in self.chores_data:
            raise HomeAssistantError(f"Chore with ID '{chore_id}' not found.")

        chore_info = self.chores_data[chore_id]
        if kid_id not in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            raise HomeAssistantError(
                f"Chore '{chore_info.get(const.DATA_CHORE_NAME)}' is not assigned to kid '{self.kids_data[kid_id][const.DATA_KID_NAME]}'."
            )

        if kid_id not in self.kids_data:
            raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

        kid_info = self.kids_data.get(kid_id)

        allow_multiple = chore_info.get(
            const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY, False
        )
        if not allow_multiple:
            if chore_id in kid_info.get(const.DATA_KID_APPROVED_CHORES, []):
                error_message = f"Chore '{chore_info[const.DATA_CHORE_NAME]}' has already been approved today; multiple approvals not allowed."
                const.LOGGER.warning(error_message)
                raise HomeAssistantError(error_message)

        default_points = chore_info.get(
            const.DATA_CHORE_DEFAULT_POINTS, const.DEFAULT_POINTS
        )
        multiplier = kid_info.get(
            const.DATA_KID_POINTS_MULTIPLIER, const.DEFAULT_KID_POINTS_MULTIPLIER
        )
        awarded_points = (
            points_awarded * multiplier
            if points_awarded is not None
            else default_points * multiplier
        )

        self._process_chore_state(
            kid_id, chore_id, const.CHORE_STATE_APPROVED, points_awarded=awarded_points
        )

        # increment completed chores counters
        kid_info[const.DATA_KID_COMPLETED_CHORES_TODAY] += 1
        kid_info[const.DATA_KID_COMPLETED_CHORES_WEEKLY] += 1
        kid_info[const.DATA_KID_COMPLETED_CHORES_MONTHLY] += 1
        kid_info[const.DATA_KID_COMPLETED_CHORES_TOTAL] += 1

        # Track today’s approvals for chores that allow multiple claims.
        if chore_info.get(const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY, False):
            kid_info.setdefault(const.DATA_KID_TODAY_CHORE_APPROVALS, {})
            kid_info[const.DATA_KID_TODAY_CHORE_APPROVALS][chore_id] = (
                kid_info[const.DATA_KID_TODAY_CHORE_APPROVALS].get(
                    chore_id, const.DEFAULT_ZERO
                )
                + 1
            )

        chore_info[const.DATA_CHORE_LAST_COMPLETED] = dt_util.utcnow().isoformat()

        today = dt_util.as_local(dt_util.utcnow()).date()
        self._update_chore_streak_for_kid(kid_id, chore_id, today)
        self._update_overall_chore_streak(kid_id, today)

        # Remove from Pending Approvals
        self._data[const.DATA_PENDING_CHORE_APPROVALS] = [
            ap
            for ap in self._data[const.DATA_PENDING_CHORE_APPROVALS]
            if not (
                ap[const.DATA_KID_ID] == kid_id and ap[const.DATA_CHORE_ID] == chore_id
            )
        ]

        # Increment Chore Approvals
        if chore_id in kid_info[const.DATA_KID_CHORE_APPROVALS]:
            kid_info[const.DATA_KID_CHORE_APPROVALS][chore_id] += 1
        else:
            kid_info[const.DATA_KID_CHORE_APPROVALS][chore_id] = 1

        # Manage Achievements
        today = dt_util.as_local(dt_util.utcnow()).date()
        for achievement_id, achievement in self.achievements_data.items():
            if (
                achievement.get(const.DATA_ACHIEVEMENT_TYPE)
                == const.ACHIEVEMENT_TYPE_STREAK
            ):
                selected_chore_id = achievement.get(
                    const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID
                )
                if selected_chore_id == chore_id:
                    # Get or create the progress dict for this kid
                    progress = achievement.setdefault(
                        const.DATA_ACHIEVEMENT_PROGRESS, {}
                    ).setdefault(
                        kid_id,
                        {
                            const.DATA_KID_CURRENT_STREAK: const.DEFAULT_ZERO,
                            const.DATA_KID_LAST_STREAK_DATE: None,
                            const.DATA_ACHIEVEMENT_AWARDED: False,
                        },
                    )
                    self._update_streak_progress(progress, today)

        # Manage Challenges
        today_iso = dt_util.as_local(dt_util.utcnow()).date().isoformat()
        for challenge_id, challenge in self.challenges_data.items():
            challenge_type = challenge.get(const.DATA_CHALLENGE_TYPE)

            if challenge_type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                selected_chore = challenge.get(const.DATA_CHALLENGE_SELECTED_CHORE_ID)
                if selected_chore and selected_chore != chore_id:
                    continue

                start_date_raw = challenge.get(const.DATA_CHALLENGE_START_DATE)
                if isinstance(start_date_raw, str):
                    start_date = dt_util.parse_datetime(start_date_raw)
                    if start_date and start_date.tzinfo is None:
                        start_date = start_date.replace(tzinfo=dt_util.UTC)
                else:
                    start_date = None

                end_date_raw = challenge.get(const.DATA_CHALLENGE_END_DATE)
                if isinstance(end_date_raw, str):
                    end_date = dt_util.parse_datetime(end_date_raw)
                    if end_date and end_date.tzinfo is None:
                        end_date = end_date.replace(tzinfo=dt_util.UTC)
                else:
                    end_date = None

                now = dt_util.utcnow()

                if start_date and end_date and start_date <= now <= end_date:
                    progress = challenge.setdefault(
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
                selected_chore = challenge.get(const.DATA_CHALLENGE_SELECTED_CHORE_ID)
                if not selected_chore:
                    const.LOGGER.warning(
                        "Challenge '%s' of type daily min has no selected chore id set. Skipping progress update.",
                        challenge.get(const.DATA_CHALLENGE_NAME),
                    )
                    continue

                if selected_chore != chore_id:
                    continue

                if kid_id in challenge.get(const.DATA_CHALLENGE_ASSIGNED_KIDS, []):
                    progress = challenge.setdefault(
                        const.DATA_CHALLENGE_PROGRESS, {}
                    ).setdefault(
                        kid_id,
                        {
                            const.DATA_CHALLENGE_DAILY_COUNTS: {},
                            const.DATA_CHALLENGE_AWARDED: False,
                        },
                    )
                    progress[const.DATA_CHALLENGE_DAILY_COUNTS][today_iso] = (
                        progress[const.DATA_CHALLENGE_DAILY_COUNTS].get(
                            today_iso, const.DEFAULT_ZERO
                        )
                        + 1
                    )

        # Send a notification to the kid that chore was approved
        if chore_info.get(
            const.CONF_NOTIFY_ON_APPROVAL, const.DEFAULT_NOTIFY_ON_APPROVAL
        ):
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHORE_ID: chore_id}
            self.hass.async_create_task(
                self._notify_kid(
                    kid_id,
                    title="KidsChores: Chore Approved",
                    message=f"Your chore '{chore_info[const.DATA_CHORE_NAME]}' was approved. You earned {awarded_points} points.",
                    extra_data=extra_data,
                )
            )

        self._persist()
        self.async_set_updated_data(self._data)

    def disapprove_chore(self, parent_name: str, kid_id: str, chore_id: str):
        """Disapprove a chore for kid_id."""
        chore_info = self.chores_data.get(chore_id)
        if not chore_info:
            raise HomeAssistantError(f"Chore with ID '{chore_id}' not found.")

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

        self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)

        # Send a notification to the kid that chore was disapproved
        if chore_info.get(
            const.CONF_NOTIFY_ON_DISAPPROVAL, const.DEFAULT_NOTIFY_ON_DISAPPROVAL
        ):
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHORE_ID: chore_id}
            self.hass.async_create_task(
                self._notify_kid(
                    kid_id,
                    title="KidsChores: Chore Disapproved",
                    message=f"Your chore '{chore_info[const.DATA_CHORE_NAME]}' was disapproved.",
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
                "Update chore state: Chore ID '%s' not found", chore_id
            )
            return
        # Set state for all kids assigned to the chore:
        for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            if kid_id:
                self._process_chore_state(kid_id, chore_id, state)
        self._persist()
        self.async_set_updated_data(self._data)
        const.LOGGER.debug(f"Chore ID '{chore_id}' state manually updated to '{state}'")

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

    def _process_chore_state(
        self,
        kid_id: str,
        chore_id: str,
        new_state: str,
        *,
        points_awarded: Optional[float] = None,
    ) -> None:
        const.LOGGER.debug(
            "Entering _process_chore_state with kid_id=%s, chore_id=%s, new_state=%s, points_awarded=%s",
            kid_id,
            chore_id,
            new_state,
            points_awarded,
        )

        """Centralized function to update a chore’s state for a given kid."""
        kid_info = self.kids_data.get(kid_id)
        chore_info = self.chores_data.get(chore_id)

        if not kid_info or not chore_info:
            const.LOGGER.warning(
                "State change skipped: Kid '%s' or Chore '%s' not found",
                kid_id,
                chore_id,
            )
            return

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
            # Remove all previous approvals in case of duplicate, add to claimed.
            kid_info[const.DATA_KID_APPROVED_CHORES] = [
                item
                for item in kid_info.get(const.DATA_KID_APPROVED_CHORES, [])
                if item != chore_id
            ]

            kid_info.setdefault(const.DATA_KID_CLAIMED_CHORES, [])

            if chore_id not in kid_info[const.DATA_KID_CLAIMED_CHORES]:
                kid_info[const.DATA_KID_CLAIMED_CHORES].append(chore_id)

            chore_info[const.DATA_CHORE_LAST_CLAIMED] = dt_util.utcnow().isoformat()

            self._data.setdefault(const.DATA_PENDING_CHORE_APPROVALS, []).append(
                {
                    const.DATA_KID_ID: kid_id,
                    const.DATA_CHORE_ID: chore_id,
                    const.DATA_CHORE_TIMESTAMP: dt_util.utcnow().isoformat(),
                }
            )

        elif new_state == const.CHORE_STATE_APPROVED:
            # Remove all claims for chores in case of duplicates, add to approvals.
            kid_info[const.DATA_KID_CLAIMED_CHORES] = [
                item
                for item in kid_info.get(const.DATA_KID_CLAIMED_CHORES, [])
                if item != chore_id
            ]

            kid_info.setdefault(const.DATA_KID_APPROVED_CHORES, [])

            if chore_id not in kid_info[const.DATA_KID_APPROVED_CHORES]:
                kid_info[const.DATA_KID_APPROVED_CHORES].append(chore_id)

            chore_info[const.DATA_CHORE_LAST_COMPLETED] = dt_util.utcnow().isoformat()

            if points_awarded is not None:
                current_points = float(
                    kid_info.get(const.DATA_KID_POINTS, const.DEFAULT_ZERO)
                )
                self.update_kid_points(kid_id, current_points + points_awarded)

            today = dt_util.as_local(dt_util.utcnow()).date()

            self._update_chore_streak_for_kid(kid_id, chore_id, today)
            self._update_overall_chore_streak(kid_id, today)

            self._data[const.DATA_PENDING_CHORE_APPROVALS] = [
                ap
                for ap in self._data.get(const.DATA_PENDING_CHORE_APPROVALS, [])
                if not (
                    ap.get(const.DATA_KID_ID) == kid_id
                    and ap.get(const.DATA_CHORE_ID) == chore_id
                )
            ]

        elif new_state == const.CHORE_STATE_PENDING:
            # Remove the chore from both claimed and approved lists.
            for field in [
                const.DATA_KID_CLAIMED_CHORES,
                const.DATA_KID_APPROVED_CHORES,
            ]:
                if chore_id in kid_info.get(field, []):
                    kid_info[field] = [c for c in kid_info[field] if c != chore_id]

            # Remove from pending approvals.
            self._data[const.DATA_PENDING_CHORE_APPROVALS] = [
                ap
                for ap in self._data.get(const.DATA_PENDING_CHORE_APPROVALS, [])
                if not (
                    ap.get(const.DATA_KID_ID) == kid_id
                    and ap.get(const.DATA_CHORE_ID) == chore_id
                )
            ]

        elif new_state == const.CHORE_STATE_OVERDUE:
            # Mark as overdue.
            kid_info.setdefault(const.DATA_KID_OVERDUE_CHORES, [])

            if chore_id not in kid_info[const.DATA_KID_OVERDUE_CHORES]:
                kid_info[const.DATA_KID_OVERDUE_CHORES].append(chore_id)

            # This bit is handled on _check_overdue_chores
            # # kid_info.setdefault(const.DATA_KID_OVERDUE_NOTIFICATIONS, {})
            # kid_info[const.DATA_KID_OVERDUE_NOTIFICATIONS][chore_id] = (
            #     dt_util.utcnow().isoformat()
            # )

        # Compute and update the chore's global state.
        # Given the process above is handling everything properly for each kid, computing the global state straightforward.
        # This process needs run every time a chore state changes, so it no longer warrants a separate function.
        assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])

        if len(assigned_kids) == 1:
            # if only one kid is assigned to the chore, update the chore state to new state 1:1
            chore_info[const.DATA_CHORE_STATE] = new_state
        elif len(assigned_kids) > 1:
            # For chores assigned to multiple kids, you have to figure out the global state
            count_pending = count_claimed = count_approved = count_overdue = (
                const.DEFAULT_ZERO
            )
            for kid_id in assigned_kids:
                kid_info = self.kids_data.get(kid_id, {})
                if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                    count_overdue += 1
                elif chore_id in kid_info.get(const.DATA_KID_APPROVED_CHORES, []):
                    count_approved += 1
                elif chore_id in kid_info.get(const.DATA_KID_CLAIMED_CHORES, []):
                    count_claimed += 1
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

            # For shared chores, recompute global state of a partial if they aren't all in the same state as checked above
            elif chore_info.get(const.DATA_CHORE_SHARED_CHORE, False):
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

            # For non-shared chores multiple assign it will be independent if they aren't all in the same state as checked above.
            elif chore_info.get(const.DATA_CHORE_SHARED_CHORE, False) is False:
                chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_INDEPENDENT

        else:
            chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_UNKNOWN

        const.LOGGER.debug(
            "Chore '%s' global state computed as '%s'",
            chore_id,
            chore_info[const.DATA_CHORE_STATE],
        )

    # -------------------------------------------------------------------------------------
    # Kids: Update Points
    # -------------------------------------------------------------------------------------

    def update_kid_points(self, kid_id: str, new_points: float):
        """Set a kid's points to 'new_points', updating daily/weekly/monthly counters."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            const.LOGGER.warning("Update kid points: Kid ID '%s' not found", kid_id)
            return

        old_points = float(kid_info[const.DATA_KID_POINTS])
        delta = new_points - old_points
        if delta == const.DEFAULT_ZERO:
            const.LOGGER.debug(
                "No change in points for kid '%s'. Skipping updates", kid_id
            )
            return

        kid_info[const.DATA_KID_POINTS] = new_points
        kid_info[const.DATA_KID_POINTS_EARNED_TODAY] += delta
        kid_info[const.DATA_KID_POINTS_EARNED_WEEKLY] += delta
        kid_info[const.DATA_KID_POINTS_EARNED_MONTHLY] += delta

        # Update cumulative earned points if delta is positive (do not decrease on spending)
        if delta > 0:
            kid_info.setdefault(
                const.DATA_KID_CUMULATIVE_EARNED_POINTS, const.DEFAULT_ZERO
            )
            kid_info[const.DATA_KID_CUMULATIVE_EARNED_POINTS] += delta

        # Update Max Points Ever
        if new_points > kid_info.get(
            const.DATA_KID_MAX_POINTS_EVER, const.DEFAULT_ZERO
        ):
            kid_info[const.DATA_KID_MAX_POINTS_EVER] = new_points

        # Check Badges
        self._check_badges_for_kid(kid_id)
        self._check_achievements_for_kid(kid_id)
        self._check_challenges_for_kid(kid_id)

        # Check Reset Cumulative Badges
        self.hass.async_create_task(self._reset_cumulative_badges())

        self._persist()
        self.async_set_updated_data(self._data)

        const.LOGGER.debug(
            "Update Kid Points: Kid '%s' changed from %.2f to %.2f (delta=%.2f)",
            kid_id,
            old_points,
            new_points,
            delta,
        )

    # -------------------------------------------------------------------------------------
    # Rewards: Redeem, Approve, Disapprove
    # -------------------------------------------------------------------------------------

    def redeem_reward(self, parent_name: str, kid_id: str, reward_id: str):
        """Kid claims a reward => mark as pending approval (no deduction yet)."""
        reward = self.rewards_data.get(reward_id)
        if not reward:
            raise HomeAssistantError(f"Reward with ID '{reward_id}' not found.")

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

        cost = reward.get(const.DATA_REWARD_COST, const.DEFAULT_ZERO)
        if kid_info[const.DATA_KID_POINTS] < cost:
            raise HomeAssistantError(
                f"'{kid_info[const.DATA_KID_NAME]}' does not have enough points ({cost} needed)."
            )

        kid_info.setdefault(const.DATA_KID_PENDING_REWARDS, []).append(reward_id)
        kid_info.setdefault(const.DATA_KID_REDEEMED_REWARDS, [])

        # Generate a unique notification ID for this claim.
        notif_id = uuid.uuid4().hex

        # Add to pending approvals
        self._data[const.DATA_PENDING_REWARD_APPROVALS].append(
            {
                const.DATA_KID_ID: kid_id,
                const.DATA_REWARD_ID: reward_id,
                const.DATA_REWARD_TIMESTAMP: dt_util.utcnow().isoformat(),
                const.DATA_REWARD_NOTIFICATION_ID: notif_id,
            }
        )

        # increment reward_claims counter
        if reward_id in kid_info[const.DATA_KID_REWARD_CLAIMS]:
            kid_info[const.DATA_KID_REWARD_CLAIMS][reward_id] += 1
        else:
            kid_info[const.DATA_KID_REWARD_CLAIMS][reward_id] = 1

        # Send a notification to the parents that a kid claimed a reward
        actions = [
            {
                const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_REWARD}|{kid_id}|{reward_id}|{notif_id}",
                const.NOTIFY_TITLE: const.ACTION_TITLE_APPROVE,
            },
            {
                const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_REWARD}|{kid_id}|{reward_id}|{notif_id}",
                const.NOTIFY_TITLE: const.ACTION_TITLE_DISAPPROVE,
            },
            {
                const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{reward_id}|{notif_id}",
                const.NOTIFY_TITLE: const.ACTION_TITLE_REMIND_30,
            },
        ]
        extra_data = {
            const.DATA_KID_ID: kid_id,
            const.DATA_REWARD_ID: reward_id,
            const.DATA_REWARD_NOTIFICATION_ID: notif_id,
        }
        self.hass.async_create_task(
            self._notify_parents(
                kid_id,
                title="KidsChores: Reward Claimed",
                message=f"'{kid_info[const.DATA_KID_NAME]}' claimed reward '{reward[const.DATA_REWARD_NAME]}'",
                actions=actions,
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    def approve_reward(
        self,
        parent_name: str,
        kid_id: str,
        reward_id: str,
        notif_id: Optional[str] = None,
    ):
        """Parent approves the reward => deduct points."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

        reward = self.rewards_data.get(reward_id)
        if not reward:
            raise HomeAssistantError(f"Reward with ID '{reward_id}' not found.")

        cost = reward.get(const.DATA_REWARD_COST, const.DEFAULT_ZERO)

        pending_count = kid_info.get(const.DATA_KID_PENDING_REWARDS, []).count(
            reward_id
        )
        if pending_count > 0:
            if kid_info[const.DATA_KID_POINTS] < cost:
                raise HomeAssistantError(
                    f"'{kid_info[const.DATA_KID_NAME]}' does not have enough points to redeem '{reward[const.DATA_REWARD_NAME]}'."
                )

            # Deduct points for one claim.
            new_points = float(kid_info[const.DATA_KID_POINTS]) - cost
            self.update_kid_points(kid_id, new_points)

            # Remove one occurrence from the kid's pending rewards list and add to redeemed.
            kid_info[const.DATA_KID_PENDING_REWARDS].remove(reward_id)
            kid_info.setdefault(const.DATA_KID_REDEEMED_REWARDS, []).append(reward_id)

        else:
            # Direct approval (no pending claim present).
            if kid_info[const.DATA_KID_POINTS] < cost:
                raise HomeAssistantError(
                    f"'{kid_info[const.DATA_KID_NAME]}' does not have enough points to redeem '{reward[const.DATA_REWARD_NAME]}'."
                )
            kid_info[const.DATA_KID_POINTS] -= cost
            kid_info[const.DATA_KID_REDEEMED_REWARDS].append(reward_id)

        # Remove only one matching pending reward approval from global approvals.
        approvals = self._data.get(const.DATA_PENDING_REWARD_APPROVALS, [])
        for i, ap in enumerate(approvals):
            if (
                ap.get(const.DATA_KID_ID) == kid_id
                and ap.get(const.DATA_REWARD_ID) == reward_id
            ):
                # If a notification ID was passed, only remove the matching one.
                if notif_id is not None:
                    if ap.get(const.DATA_REWARD_NOTIFICATION_ID) == notif_id:
                        del approvals[i]
                        break
                else:
                    del approvals[i]
                    break

        # Increment reward approval counter for the kid.
        if reward_id in kid_info[const.DATA_KID_REWARD_APPROVALS]:
            kid_info[const.DATA_KID_REWARD_APPROVALS][reward_id] += 1
        else:
            kid_info[const.DATA_KID_REWARD_APPROVALS][reward_id] = 1

        # Check badges
        self._check_badges_for_kid(kid_id)

        # Notify the kid that the reward has been approved
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_REWARD_ID: reward_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Reward Approved",
                message=f"Your reward '{reward[const.DATA_REWARD_NAME]}' was approved.",
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    def disapprove_reward(self, parent_name: str, kid_id: str, reward_id: str):
        """Disapprove a reward for kid_id."""

        reward = self.rewards_data.get(reward_id)
        if not reward:
            raise HomeAssistantError(f"Reward with ID '{reward_id}' not found.")

        # Remove only one entry of each reward claim from pending approvals
        approvals = self._data.get(const.DATA_PENDING_REWARD_APPROVALS, [])
        for i, ap in enumerate(approvals):
            if (
                ap.get(const.DATA_KID_ID) == kid_id
                and ap.get(const.DATA_REWARD_ID) == reward_id
            ):
                del approvals[i]
                break
        self._data[const.DATA_PENDING_REWARD_APPROVALS] = approvals

        kid_info = self.kids_data.get(kid_id)
        if kid_info and reward_id in kid_info.get(const.DATA_KID_PENDING_REWARDS, []):
            kid_info[const.DATA_KID_PENDING_REWARDS].remove(reward_id)

        # Send a notification to the kid that reward was disapproved
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_REWARD_ID: reward_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Reward Disapproved",
                message=f"Your reward '{reward[const.DATA_REWARD_NAME]}' was disapproved.",
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------------------
    # Badges: Check, Award
    # -------------------------------------------------------------------------------------

    def _check_badges_for_kid(self, kid_id: str):
        """Evaluate all badge thresholds for kid."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        for badge_id, badge in self.badges_data.items():
            badge_type = badge.get(const.DATA_BADGE_TYPE)

            # For non-cumulative badges, if assigned kids is defined, only award if kid_id is in it.
            if badge.get(const.DATA_BADGE_TYPE) != const.BADGE_TYPE_CUMULATIVE:
                assigned = badge.get(const.DATA_BADGE_ASSIGNED_KIDS, [])
                if assigned and kid_id not in assigned:
                    continue

            # For all types except special occasion, skip if already earned.
            if badge_type != const.BADGE_TYPE_SPECIAL_OCCASION and kid_id in badge.get(
                const.DATA_BADGE_EARNED_BY, []
            ):
                continue

            if badge_type == const.BADGE_TYPE_CUMULATIVE:
                effective_badge_id = self._determine_cumulative_badge_for_kid(kid_id)

                if effective_badge_id == badge_id:
                    self._award_badge(kid_id, badge_id)

                else:
                    self._remove_badge_from_kid(kid_id, badge)

            elif badge_type == const.BADGE_TYPE_DAILY:
                # Award daily badge if the kid completed enough chores today.
                threshold = badge.get(
                    const.DATA_BADGE_DAILY_THRESHOLD,
                    const.DEFAULT_BADGE_DAILY_THRESHOLD,
                )
                if (
                    kid_info.get(
                        const.DATA_KID_COMPLETED_CHORES_TODAY, const.DEFAULT_ZERO
                    )
                    >= threshold
                ):
                    self._award_badge(kid_id, badge_id)

            elif badge_type == const.BADGE_TYPE_PERIODIC:
                threshold = badge.get(
                    const.DATA_BADGE_THRESHOLD_VALUE,
                    const.DEFAULT_BADGE_THRESHOLD_VALUE,
                )
                criteria_type = badge.get(
                    const.DATA_BADGE_THRESHOLD_TYPE, const.BADGE_THRESHOLD_TYPE_POINTS
                )
                reset_schedule = badge.get(
                    const.DATA_BADGE_RESET_SCHEDULE, const.CONF_WEEKLY
                )
                now = dt_util.utcnow()

                if reset_schedule in [
                    const.CONF_WEEKLY,
                    const.CONF_MONTHLY,
                ]:
                    # Non-custom schedules: use pre‐defined counters
                    if criteria_type == const.BADGE_THRESHOLD_TYPE_POINTS:
                        if reset_schedule == const.CONF_WEEKLY:
                            period_points = kid_info.get(
                                const.DATA_KID_POINTS_EARNED_WEEKLY, const.DEFAULT_ZERO
                            )
                        elif reset_schedule == const.CONF_MONTHLY:
                            period_points = kid_info.get(
                                const.DATA_KID_POINTS_EARNED_MONTHLY, const.DEFAULT_ZERO
                            )
                        else:
                            period_points = kid_info.get(
                                const.DATA_KID_POINTS_EARNED_TODAY, const.DEFAULT_ZERO
                            )
                        if period_points >= threshold:
                            self._award_badge(kid_id, badge_id)

                    elif criteria_type == const.BADGE_THRESHOLD_TYPE_CHORE_COUNT:
                        # For non-custom chore-based badges, here we assume the period is the current week.
                        today_local = dt_util.as_local(now).date()
                        # For example, assume the week starts on Monday:
                        week_start = today_local - timedelta(days=today_local.weekday())
                        all_completed = True
                        required_chores = badge.get(
                            const.DATA_BADGE_REQUIRED_CHORES, []
                        )
                        for req_chore in required_chores:
                            # Check if the kid has an approved record for the chore...
                            if req_chore not in kid_info.get(
                                const.DATA_KID_APPROVED_CHORES, []
                            ):
                                all_completed = False
                                break
                            chore = self.chores_data.get(req_chore)
                            if not chore:
                                all_completed = False
                                break
                            last_completed_str = chore.get(
                                const.DATA_CHORE_LAST_COMPLETED
                            )
                            if not last_completed_str:
                                all_completed = False
                                break
                            try:
                                last_dt = dt_util.parse_datetime(last_completed_str)
                                if last_dt.date() < week_start:
                                    all_completed = False
                                    break
                            except Exception:
                                all_completed = False
                                break
                        if all_completed:
                            kid_success = kid_info.setdefault(
                                const.DATA_KID_PERIODIC_BADGE_SUCCESS, {}
                            )
                            count = kid_success.get(badge_id, const.DEFAULT_ZERO) + 1
                            kid_success[badge_id] = count
                            if count >= threshold:
                                self._award_badge(kid_id, badge_id)

                elif reset_schedule == const.CONF_CUSTOM:
                    # Custom reset schedule: use start and end dates from the badge.
                    start_date_str = badge.get(const.DATA_BADGE_START_DATE, "").strip()
                    end_date_str = badge.get(const.DATA_BADGE_END_DATE, "").strip()
                    is_recurrent = badge.get(const.DATA_BADGE_PERIODIC_RECURRENT, False)

                    if start_date_str and end_date_str:
                        try:
                            start_date = dt_util.parse_datetime(start_date_str)
                            end_date = dt_util.parse_datetime(end_date_str)
                            if start_date is None or end_date is None:
                                const.LOGGER.error(
                                    "Custom schedule dates invalid for badge '%s'",
                                    badge.get(const.DATA_BADGE_NAME),
                                )
                                continue

                            # Ensure the parsed dates are timezone-aware:
                            if start_date.tzinfo is None:
                                local_tz = dt_util.get_time_zone(
                                    self.hass.config.time_zone
                                )
                                start_date = start_date.replace(tzinfo=local_tz)
                            start_date = dt_util.as_utc(start_date)

                            if end_date.tzinfo is None:
                                local_tz = dt_util.get_time_zone(
                                    self.hass.config.time_zone
                                )
                                end_date = end_date.replace(tzinfo=local_tz)
                            end_date = dt_util.as_utc(end_date)

                        except Exception as e:
                            const.LOGGER.error(
                                "Error parsing custom schedule for badge '%s': %s",
                                badge.get(const.DATA_BADGE_NAME),
                                e,
                            )
                            continue

                        # Now both start_date and end_date are aware UTC datetimes.
                        if now < start_date or now > end_date:
                            if now > end_date and is_recurrent:
                                period_delta = end_date - start_date
                                new_start = start_date + period_delta
                                new_end = end_date + period_delta
                                badge[const.DATA_BADGE_START_DATE] = (
                                    new_start.isoformat()
                                )
                                badge[const.DATA_BADGE_END_DATE] = new_end.isoformat()
                                kid_info.setdefault(
                                    const.DATA_KID_PERIODIC_BADGE_SUCCESS, {}
                                )[badge_id] = 0
                                const.LOGGER.info(
                                    "Rescheduled periodic badge '%s' for kid '%s' to new period %s - %s",
                                    badge.get(const.DATA_BADGE_NAME),
                                    kid_id,
                                    new_start.isoformat(),
                                    new_end.isoformat(),
                                )
                            continue

                        if criteria_type == const.BADGE_THRESHOLD_TYPE_POINTS:
                            kid_points = kid_info.setdefault(
                                const.DATA_KID_PERIODIC_BADGE_POINTS, {}
                            ).get(badge_id, const.DEFAULT_ZERO)
                            if kid_points >= threshold:
                                self._award_badge(kid_id, badge_id)
                        elif criteria_type == const.BADGE_THRESHOLD_TYPE_CHORE_COUNT:
                            required_chores = badge.get(
                                const.DATA_BADGE_REQUIRED_CHORES, []
                            )
                            all_completed = True
                            for req_chore in required_chores:
                                chore = self.chores_data.get(req_chore)
                                if not chore:
                                    all_completed = False
                                    break
                                last_completed_str = chore.get(
                                    const.DATA_CHORE_LAST_COMPLETED
                                )
                                if not last_completed_str:
                                    all_completed = False
                                    break
                                try:
                                    last_dt = dt_util.parse_datetime(last_completed_str)
                                    # Ensure the chore was completed within the custom period.
                                    if not (start_date <= last_dt <= end_date):
                                        all_completed = False
                                        break
                                except Exception:
                                    all_completed = False
                                    break
                            if all_completed:
                                kid_success = kid_info.setdefault(
                                    const.DATA_KID_PERIODIC_BADGE_SUCCESS, {}
                                )
                                count = (
                                    kid_success.get(badge_id, const.DEFAULT_ZERO) + 1
                                )
                                kid_success[badge_id] = count
                                if count >= threshold:
                                    self._award_badge(kid_id, badge_id)

            elif badge_type == const.BADGE_TYPE_ACHIEVEMENT_LINKED:
                # Award if the linked achievement has been awarded.
                linked_achievement = badge.get(const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT)
                if linked_achievement:
                    achievement = self.achievements_data.get(linked_achievement)
                    if achievement:
                        progress = achievement.get(const.DATA_ACHIEVEMENT_PROGRESS, {})
                        kid_prog = progress.get(kid_id, {})
                        if kid_prog.get(const.DATA_ACHIEVEMENT_AWARDED, False):
                            self._award_badge(kid_id, badge_id)

            elif badge_type == const.BADGE_TYPE_CHALLENGE_LINKED:
                # Award if the linked challenge has been completed.
                linked_challenge = badge.get(const.DATA_BADGE_ASSOCIATED_CHALLENGE)
                if linked_challenge:
                    challenge = self.challenges_data.get(linked_challenge)
                    if challenge:
                        progress = challenge.get(const.DATA_CHALLENGE_PROGRESS, {})
                        kid_prog = progress.get(kid_id, {})
                        if kid_prog.get(const.DATA_CHALLENGE_AWARDED, False):
                            self._award_badge(kid_id, badge_id)

            elif badge_type == const.BADGE_TYPE_SPECIAL_OCCASION:
                # Special Occasion badges are re‑evaluated even if previously awarded.
                occasion_date_str = badge.get(
                    const.DATA_BADGE_SPECIAL_OCCASION_DATE, const.CONF_EMPTY
                ).strip()
                is_recurrent = badge.get(
                    const.DATA_BADGE_SPECIAL_OCCASION_RECURRENCY, False
                )
                if occasion_date_str:
                    try:
                        # Using parse_date since these badges use a Date selector.
                        occasion_date = dt_util.parse_date(occasion_date_str)
                        if occasion_date:
                            today = dt_util.as_local(dt_util.utcnow()).date()
                            if is_recurrent:
                                # For recurrent badges compare month and day only.
                                if (
                                    today.month == occasion_date.month
                                    and today.day == occasion_date.day
                                ):
                                    if (
                                        kid_info.get(
                                            const.DATA_KID_COMPLETED_CHORES_TODAY,
                                            const.DEFAULT_ZERO,
                                        )
                                        > const.DEFAULT_ZERO
                                    ):
                                        self._award_badge(kid_id, badge_id)
                                        # Bump the badge's date by one year for the next recurrence.
                                        next_year = today.year + 1
                                        try:
                                            new_date = occasion_date.replace(
                                                year=next_year
                                            )
                                        except ValueError:
                                            new_date = occasion_date.replace(
                                                year=next_year, day=28
                                            )
                                        badge[
                                            const.DATA_BADGE_SPECIAL_OCCASION_DATE
                                        ] = new_date.isoformat()
                                        updated_options = dict(
                                            self.config_entry.options
                                        )
                                        badges_conf = dict(
                                            updated_options.get(const.CONF_BADGES, {})
                                        )
                                        if badge_id in badges_conf:
                                            badges_conf[badge_id][
                                                const.DATA_BADGE_SPECIAL_OCCASION_DATE
                                            ] = new_date.isoformat()
                                            updated_options[const.CONF_BADGES] = (
                                                badges_conf
                                            )
                                            new_data = dict(self.config_entry.data)
                                            new_data[const.DATA_LAST_CHANGE] = (
                                                dt_util.utcnow().isoformat()
                                            )
                                            self.hass.config_entries.async_update_entry(
                                                self.config_entry,
                                                data=new_data,
                                                options=updated_options,
                                            )

                            else:
                                # One‑off: require an exact match.
                                if today == occasion_date:
                                    if (
                                        kid_info.get(
                                            const.DATA_KID_COMPLETED_CHORES_TODAY,
                                            const.DEFAULT_ZERO,
                                        )
                                        > const.DEFAULT_ZERO
                                    ):
                                        self._award_badge(kid_id, badge_id)
                    except Exception as e:
                        const.LOGGER.error(
                            "Error processing special occasion badge '%s': %s",
                            badge.get(const.DATA_BADGE_NAME),
                            e,
                        )

    def _award_badge(self, kid_id: str, badge_id: str):
        """Add the badge to kid's 'earned_by' and kid's 'badges' list."""
        badge = self.badges_data.get(badge_id)

        kid_info = self.kids_data.get(kid_id, {})
        if not kid_info:
            const.LOGGER.error("Kid with ID '%s' not found when awarding badge", kid_id)
            return

        if not badge:
            const.LOGGER.error(
                "Attempted to award non-existent badge ID '%s' to kid ID '%s'",
                badge_id,
                kid_id,
            )
            return

        badge_type = badge.get(const.DATA_BADGE_TYPE, const.BADGE_TYPE_CUMULATIVE)
        # For non-special occasion badges, do not re‑award if already earned.
        if badge_type != const.BADGE_TYPE_SPECIAL_OCCASION and kid_id in badge.get(
            const.DATA_BADGE_EARNED_BY, []
        ):
            return

        # For special occasion badges, only award once per day.
        if badge_type == const.BADGE_TYPE_SPECIAL_OCCASION:
            kid_info = self.kids_data.get(kid_id, {})
            today = dt_util.as_local(dt_util.utcnow()).date().isoformat()
            # Track the last award date for this badge.
            last_award_key = (
                f"{const.DATA_BADGE_SPECIAL_OCCASION_LAST_AWARDED}_{badge_id}"
            )
            if kid_info.get(last_award_key) == today:
                return  # Already awarded today.
            # Store last awarded date
            kid_info[last_award_key] = today
            # If it was awarded previously, remove it so we can award again.
            if kid_id in badge.get(const.DATA_BADGE_EARNED_BY, []):
                badge[const.DATA_BADGE_EARNED_BY].remove(kid_id)
            # After awarding below, we’ll update kid_info[last_award_key] = today.

        # When awarding a periodic cumulative badge, record baseline and current badge if not already set.
        if badge_type == const.BADGE_TYPE_CUMULATIVE and badge.get(
            const.DATA_BADGE_RESET_PERIODICALLY, False
        ):
            if const.DATA_KID_CUMULATIVE_BADGE_BASELINE not in kid_info:
                kid_info[const.DATA_KID_CUMULATIVE_BADGE_BASELINE] = kid_info.get(
                    const.DATA_KID_CUMULATIVE_EARNED_POINTS, const.DEFAULT_ZERO
                )
            if const.DATA_KID_PRE_RESET_BADGE not in kid_info:
                kid_info[const.DATA_KID_PRE_RESET_BADGE] = badge_id

        # Award the badge (for all types, including special occasion).
        badge.setdefault(const.DATA_BADGE_EARNED_BY, []).append(kid_id)

        badge_name = badge.get(const.DATA_BADGE_NAME)
        kid_name = kid_info[const.DATA_KID_NAME]

        if badge_name not in kid_info.get(const.DATA_KID_BADGES, []):
            kid_info.setdefault(const.DATA_KID_BADGES, []).append(badge_name)

        badge_type = badge.get(const.DATA_BADGE_TYPE, const.BADGE_TYPE_CUMULATIVE)

        one_time_reward = badge.get(const.DATA_BADGE_AWARD_REWARD, const.CONF_EMPTY)

        if badge_type == const.BADGE_TYPE_CUMULATIVE:
            # Update the kid's multiplier based on all earned cumulative badges.
            self._update_kid_multiplier(kid_id)

        elif badge_type in [
            const.BADGE_TYPE_DAILY,
            const.BADGE_TYPE_PERIODIC,
            const.BADGE_TYPE_ACHIEVEMENT_LINKED,
            const.BADGE_TYPE_CHALLENGE_LINKED,
            const.BADGE_TYPE_SPECIAL_OCCASION,
        ]:
            # Determine award mode and apply accordingly:
            award_mode = badge.get(
                const.DATA_BADGE_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE
            )
            if award_mode == const.DATA_BADGE_AWARD_POINTS:
                extra_points = badge.get(
                    const.DATA_BADGE_AWARD_POINTS, const.DEFAULT_ZERO
                )
                one_time_reward = const.CONF_EMPTY
            elif award_mode == const.DATA_BADGE_AWARD_REWARD:
                extra_points = 0
                one_time_reward = badge.get(
                    const.DATA_BADGE_AWARD_REWARD, const.CONF_EMPTY
                )
            elif award_mode == const.DATA_BADGE_AWARD_POINTS_REWARD:
                extra_points = badge.get(
                    const.DATA_BADGE_AWARD_POINTS, const.DEFAULT_ZERO
                )
                one_time_reward = badge.get(
                    const.DATA_BADGE_AWARD_REWARD, const.CONF_EMPTY
                )
            else:
                # Fallback behavior
                extra_points = badge.get(
                    const.DATA_BADGE_AWARD_POINTS, const.DEFAULT_ZERO
                )
                one_time_reward = badge.get(
                    const.DATA_BADGE_AWARD_REWARD, const.CONF_EMPTY
                )

            # Process extra points if applicable
            if extra_points:
                current_points = float(
                    kid_info.get(const.DATA_KID_POINTS, const.DEFAULT_ZERO)
                )
                new_points = current_points + extra_points
                self.update_kid_points(kid_id, new_points)

            # Process one-time reward if applicable
            if one_time_reward:
                if one_time_reward in kid_info.get(const.DATA_KID_PENDING_REWARDS, []):
                    kid_info[const.DATA_KID_PENDING_REWARDS].remove(one_time_reward)
                kid_info.setdefault(const.DATA_KID_REWARD_APPROVALS, {})
                if one_time_reward in kid_info[const.DATA_KID_REWARD_APPROVALS]:
                    kid_info[const.DATA_KID_REWARD_APPROVALS][one_time_reward] += 1
                else:
                    kid_info[const.DATA_KID_REWARD_APPROVALS][one_time_reward] = 1
                if one_time_reward not in kid_info.get(
                    const.DATA_KID_REDEEMED_REWARDS, []
                ):
                    kid_info.setdefault(const.DATA_KID_REDEEMED_REWARDS, []).append(
                        one_time_reward
                    )

        else:
            const.LOGGER.warning(
                "Badge type '%s' is not ellegible for extra perks", badge_type
            )

        # Send a notification to the kid and parents that a new badge was earned
        message = f"You earned a new badge: '{badge_name}'!"
        if one_time_reward:
            message += f" And extra reward: '{one_time_reward}'."

        parent_message = f"'{kid_name}' earned a new badge: '{badge_name}'."
        if one_time_reward:
            parent_message += f" And extra reward: '{one_time_reward}'."

        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_BADGE_ID: badge_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Badge Earned",
                message=message,
                extra_data=extra_data,
            )
        )
        self.hass.async_create_task(
            self._notify_parents(
                kid_id,
                title="KidsChores: Badge Earned",
                message=parent_message,
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    def _update_kid_multiplier(self, kid_id: str):
        """Update the kid's points multiplier based on highest badge achieved."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return
        earned_badges = [
            badge
            for badge in self.badges_data.values()
            if kid_id in badge.get(const.DATA_BADGE_EARNED_BY, [])
        ]
        if not earned_badges:
            kid_info[const.DATA_KID_POINTS_MULTIPLIER] = (
                const.DEFAULT_KID_POINTS_MULTIPLIER
            )
        else:
            highest_mult = max(
                badge.get(
                    const.DATA_BADGE_POINTS_MULTIPLIER,
                    const.DEFAULT_KID_POINTS_MULTIPLIER,
                )
                for badge in earned_badges
            )
            kid_info[const.DATA_KID_POINTS_MULTIPLIER] = highest_mult

    async def _reset_cumulative_badges(self):
        """Check and reset cumulative badges for all kids."""
        for kid_id, kid_info in self.kids_data.items():
            for badge in self.badges_data.values():
                if badge.get(const.DATA_BADGE_TYPE) != const.BADGE_TYPE_CUMULATIVE:
                    continue

                if not self._process_cumulative_badge_reset(kid_id, badge):
                    self._remove_badge_from_kid(kid_id, badge)

    def _process_cumulative_badge_reset(self, kid_id: str, badge: dict) -> bool:
        """Determine whether a cumulative badge is maintained for a kid."""
        now_local = dt_util.as_local(dt_util.utcnow())
        reset_type = badge.get(const.DATA_BADGE_RESET_TYPE, const.CONF_YEAR_END)
        grace_period_days = badge.get(
            const.DATA_BADGE_RESET_GRACE_PERIOD,
            const.DEFAULT_BADGE_RESET_GRACE_PERIOD,
        )
        custom_reset_date = badge.get(const.DATA_BADGE_CUSTOM_RESET_DATE)

        # Determine expected reset date based on reset_type.
        if reset_type == const.CONF_YEAR_END:
            expected_reset = now_local.replace(
                month=const.DEFAULT_YEAR_END_MONTH,
                day=const.DEFAULT_YEAR_END_DAY,
                hour=const.DEFAULT_YEAR_END_HOUR,
                minute=const.DEFAULT_YEAR_END_MINUTE,
                second=const.DEFAULT_YEAR_END_SECOND,
            )

        elif reset_type == const.CONF_QUARTER:
            quarter = (now_local.month - 1) // 3 + 1
            last_month = quarter * 3
            from calendar import monthrange

            last_day = monthrange(now_local.year, last_month)[1]
            expected_reset = now_local.replace(
                month=last_month,
                day=last_day,
                hour=const.DEFAULT_YEAR_END_HOUR,
                minute=const.DEFAULT_YEAR_END_MINUTE,
                second=const.DEFAULT_YEAR_END_SECOND,
            )

        elif reset_type == const.CONF_MONTHLY:
            from calendar import monthrange

            last_day = monthrange(now_local.year, now_local.month)[1]
            expected_reset = now_local.replace(
                day=last_day,
                hour=const.DEFAULT_YEAR_END_HOUR,
                minute=const.DEFAULT_YEAR_END_MINUTE,
                second=const.DEFAULT_YEAR_END_SECOND,
            )

        elif reset_type == const.CONF_CUSTOM and custom_reset_date:
            expected_reset = dt_util.parse_datetime(custom_reset_date)

            if expected_reset and expected_reset.tzinfo is None:
                local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
                expected_reset = expected_reset.replace(tzinfo=local_tz)

            expected_reset = dt_util.as_local(expected_reset)

        else:
            expected_reset = now_local

        grace_expiration = expected_reset + timedelta(days=grace_period_days)

        # Check if the badge is maintained.
        kid_info = self.kids_data.get(kid_id, {})
        cycle_points = kid_info.get(
            const.DATA_KID_CUMULATIVE_EARNED_POINTS, const.DEFAULT_ZERO
        )
        maintenance_required = badge.get(
            const.DATA_BADGE_MAINTENANCE_RULES, const.DEFAULT_ZERO
        )

        if now_local < grace_expiration:
            # Within grace period: badge is maintained only if maintenance points are met.
            return cycle_points >= maintenance_required

        else:
            # Grace period expired. In either case, reset the cycle counter.
            if cycle_points >= maintenance_required:
                kid_info[const.DATA_KID_CUMULATIVE_BADGE_BASELINE] = (
                    kid_info.get(
                        const.DATA_KID_CUMULATIVE_BADGE_BASELINE, const.DEFAULT_ZERO
                    )
                    + cycle_points
                )
                kid_info[const.DATA_KID_CUMULATIVE_EARNED_POINTS] = const.DEFAULT_ZERO
                return True

            else:
                kid_info[const.DATA_KID_CUMULATIVE_EARNED_POINTS] = const.DEFAULT_ZERO
                return False

    def _remove_badge_from_kid(self, kid_id: str, badge: dict) -> None:
        """Remove a cumulative badge from a kid if they no longer qualify."""
        if kid_id in badge.get(const.DATA_BADGE_EARNED_BY, []):
            badge[const.DATA_BADGE_EARNED_BY].remove(kid_id)

        kid_info = self.kids_data.get(kid_id, {})
        badge_name = badge.get(const.DATA_BADGE_NAME)

        if badge_name in kid_info.get(const.DATA_KID_BADGES, []):
            kid_info[const.DATA_KID_BADGES].remove(badge_name)

    def _recalculate_all_badges(self):
        """Global re-check of all badges for all kids."""
        const.LOGGER.info("Starting global badge recalculation")

        # Clear any per-kid periodic badge counters.
        for kid in self.kids_data.values():
            if const.DATA_KID_PERIODIC_BADGE_SUCCESS in kid:
                kid[const.DATA_KID_PERIODIC_BADGE_SUCCESS].clear()

        # Re-evaluate badge criteria for each kid.
        for kid_id in self.kids_data.keys():
            self._check_badges_for_kid(kid_id)

        self._persist()
        self.async_set_updated_data(self._data)
        const.LOGGER.info("Badge recalculation complete")

    def _determine_cumulative_badge_for_kid(self, kid_id: str) -> Optional[str]:
        """Determine which cumulative badge a kid should currently have."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return None

        cumulative_badges = [
            badge
            for badge in self.badges_data.values()
            if badge.get(const.DATA_BADGE_TYPE) == const.BADGE_TYPE_CUMULATIVE
        ]

        cumulative_badges.sort(
            key=lambda badge: badge.get(
                const.CONF_BADGE_THRESHOLD_VALUE, const.DEFAULT_ZERO
            )
        )
        baseline = kid_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_BASELINE, const.DEFAULT_ZERO
        )
        cycle_points = kid_info.get(
            const.DATA_KID_CUMULATIVE_EARNED_POINTS, const.DEFAULT_ZERO
        )
        total = baseline + cycle_points
        current_badge_id = kid_info.get(const.DATA_KID_PRE_RESET_BADGE)

        if current_badge_id:
            current_badge = next(
                (
                    badge
                    for badge in cumulative_badges
                    if badge.get(const.DATA_BADGE_INTERNAL_ID) == current_badge_id
                ),
                None,
            )

            if current_badge:
                maintenance_required = current_badge.get(
                    const.DATA_BADGE_MAINTENANCE_RULES, const.DEFAULT_ZERO
                )
                current_threshold = current_badge.get(
                    const.CONF_BADGE_THRESHOLD_VALUE, const.DEFAULT_ZERO
                )

                if cycle_points >= maintenance_required:
                    # Check for upgrade possibility.
                    for badge in cumulative_badges:
                        badge_threshold = badge.get(
                            const.CONF_BADGE_THRESHOLD_VALUE, const.DEFAULT_ZERO
                        )
                        if (
                            badge_threshold > current_threshold
                            and total >= badge_threshold
                        ):
                            # Upgrade: record the new badge and update baseline.
                            kid_info[const.DATA_KID_PRE_RESET_BADGE] = badge.get(
                                const.DATA_BADGE_INTERNAL_ID
                            )
                            kid_info[const.DATA_KID_CUMULATIVE_BADGE_BASELINE] = total
                            return badge.get(const.DATA_BADGE_INTERNAL_ID)
                    return current_badge_id

                else:
                    # Not maintained: downgrade by one level.
                    return self._get_next_lower_badge(current_badge_id)

        else:
            # No pre-reset badge recorded: award the highest badge that qualifies.
            awarded_badge = None

            for badge in cumulative_badges:
                threshold = badge.get(
                    const.CONF_BADGE_THRESHOLD_VALUE, const.DEFAULT_ZERO
                )
                if total >= threshold:
                    awarded_badge = badge

            if awarded_badge:
                return awarded_badge.get(const.DATA_BADGE_INTERNAL_ID)

        return None

    def _get_next_lower_badge(self, current_badge_id: str) -> Optional[str]:
        """Given a cumulative badge ID, return the badge ID immediately lower in threshold."""
        cumulative_badges = [
            badge
            for badge in self.badges_data.values()
            if badge.get(const.DATA_BADGE_TYPE) == const.BADGE_TYPE_CUMULATIVE
        ]
        cumulative_badges.sort(
            key=lambda badge: badge.get(
                const.CONF_BADGE_THRESHOLD_VALUE, const.DEFAULT_ZERO
            )
        )
        current_index = None

        for index, badge in enumerate(cumulative_badges):
            if badge.get(const.DATA_BADGE_INTERNAL_ID) == current_badge_id:
                current_index = index
                break

        if current_index is None or current_index == 0:
            return None

        lower_badge = cumulative_badges[current_index - 1]

        return lower_badge.get(const.DATA_BADGE_INTERNAL_ID)

    def _reset_cumulative_earned_points_for_kid(self, kid_id: str):
        """Reset the cumulative earned points counter for the kid."""
        kid_info = self.kids_data.get(kid_id)
        if kid_info is not None:
            kid_info[const.DATA_KID_CUMULATIVE_EARNED_POINTS] = 0

    # -------------------------------------------------------------------------------------
    # Penalties: Apply
    # -------------------------------------------------------------------------------------

    def apply_penalty(self, parent_name: str, kid_id: str, penalty_id: str):
        """Apply penalty => negative points to reduce kid's points."""
        penalty = self.penalties_data.get(penalty_id)
        if not penalty:
            raise HomeAssistantError(f"Penalty with ID '{penalty_id}' not found.")

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

        penalty_pts = penalty.get(const.DATA_PENALTY_POINTS, const.DEFAULT_ZERO)
        new_points = float(kid_info[const.DATA_KID_POINTS]) + penalty_pts
        self.update_kid_points(kid_id, new_points)

        # increment penalty_applies
        if penalty_id in kid_info[const.DATA_KID_PENALTY_APPLIES]:
            kid_info[const.DATA_KID_PENALTY_APPLIES][penalty_id] += 1
        else:
            kid_info[const.DATA_KID_PENALTY_APPLIES][penalty_id] = 1

        # Send a notification to the kid that a penalty was applied
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_PENALTY_ID: penalty_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Penalty Applied",
                message=f"A '{penalty[const.DATA_PENALTY_NAME]}' penalty was applied. Your points changed by {penalty_pts}.",
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------
    # Bonuses: Apply
    # -------------------------------------------------------------------------

    def apply_bonus(self, parent_name: str, kid_id: str, bonus_id: str):
        """Apply bonus => positive points to increase kid's points."""
        bonus = self.bonuses_data.get(bonus_id)
        if not bonus:
            raise HomeAssistantError(f"Bonus with ID '{bonus_id}' not found.")

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

        bonus_pts = bonus.get(const.DATA_BONUS_POINTS, const.DEFAULT_ZERO)
        new_points = float(kid_info[const.DATA_KID_POINTS]) + bonus_pts
        self.update_kid_points(kid_id, new_points)

        # increment bonus_applies
        if bonus_id in kid_info[const.DATA_KID_BONUS_APPLIES]:
            kid_info[const.DATA_KID_BONUS_APPLIES][bonus_id] += 1
        else:
            kid_info[const.DATA_KID_BONUS_APPLIES][bonus_id] = 1

        # Send a notification to the kid that a bonus was applied
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_BONUS_ID: bonus_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Bonus Applied",
                message=f"A '{bonus[const.DATA_BONUS_NAME]}' bonus was applied. Your points changed by {bonus_pts}.",
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

        now_date = dt_util.as_local(dt_util.utcnow()).date()

        for achievement_id, achievement in self._data[const.DATA_ACHIEVEMENTS].items():
            progress = achievement.setdefault(const.DATA_ACHIEVEMENT_PROGRESS, {})
            if kid_id in progress and progress[kid_id].get(
                const.DATA_ACHIEVEMENT_AWARDED, False
            ):
                continue

            ach_type = achievement.get(const.DATA_ACHIEVEMENT_TYPE)
            target = achievement.get(const.DATA_ACHIEVEMENT_TARGET_VALUE, 1)

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

                self._update_streak_progress(progress, now_date)
                if progress[const.DATA_KID_CURRENT_STREAK] >= target:
                    self._award_achievement(kid_id, achievement_id)

            # For a total achievement, simply compare total completed chores:
            elif ach_type == const.ACHIEVEMENT_TYPE_TOTAL:
                # Get per–kid progress for this achievement.
                progress = achievement.setdefault(
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
                    progress[const.DATA_ACHIEVEMENT_BASELINE] = kid_info.get(
                        const.DATA_KID_COMPLETED_CHORES_TOTAL, const.DEFAULT_ZERO
                    )

                # Calculate progress as (current total minus baseline)
                current_total = kid_info.get(
                    const.DATA_KID_COMPLETED_CHORES_TOTAL, const.DEFAULT_ZERO
                )

                progress[const.DATA_ACHIEVEMENT_CURRENT_VALUE] = current_total

                effective_target = progress[const.DATA_ACHIEVEMENT_BASELINE] + target

                if current_total >= effective_target:
                    self._award_achievement(kid_id, achievement_id)

            # For daily minimum achievement, compare total daily chores:
            elif ach_type == const.ACHIEVEMENT_TYPE_DAILY_MIN:
                # Initialize progress for this achievement if missing.
                progress = achievement.setdefault(
                    const.DATA_ACHIEVEMENT_PROGRESS, {}
                ).setdefault(
                    kid_id,
                    {
                        const.DATA_ACHIEVEMENT_LAST_AWARDED_DATE: None,
                        const.DATA_ACHIEVEMENT_AWARDED: False,
                    },
                )

                today = dt_util.as_local(dt_util.utcnow()).date().isoformat()

                # Only award bonus if not awarded today AND the kid's daily count meets the threshold.
                if (
                    progress.get(const.DATA_ACHIEVEMENT_LAST_AWARDED_DATE) != today
                    and kid_info.get(
                        const.DATA_KID_COMPLETED_CHORES_TODAY,
                        const.DEFAULT_ZERO,
                    )
                    >= target
                ):
                    self._award_achievement(kid_id, achievement_id)
                    progress[const.DATA_ACHIEVEMENT_LAST_AWARDED_DATE] = today

    def _award_achievement(self, kid_id: str, achievement_id: str):
        """Award the achievement to the kid.

        Update the achievement progress to indicate it is earned,
        and send notifications to both the kid and their parents.
        """
        achievement = self.achievements_data.get(achievement_id)
        if not achievement:
            const.LOGGER.error(
                "Attempted to award non-existent achievement '%s'", achievement_id
            )
            return

        # Get or create the existing progress dictionary for this kid
        progress_for_kid = achievement.setdefault(
            const.DATA_ACHIEVEMENT_PROGRESS, {}
        ).get(kid_id)
        if progress_for_kid is None:
            # If it doesn't exist, initialize it with baseline from the kid's current total.
            kid_info = self.kids_data.get(kid_id, {})
            progress_dict = {
                const.DATA_ACHIEVEMENT_BASELINE: kid_info.get(
                    const.DATA_KID_COMPLETED_CHORES_TOTAL, const.DEFAULT_ZERO
                ),
                const.DATA_ACHIEVEMENT_CURRENT_VALUE: const.DEFAULT_ZERO,
                const.DATA_ACHIEVEMENT_AWARDED: False,
            }
            achievement[const.DATA_ACHIEVEMENT_PROGRESS][kid_id] = progress_dict
            progress_for_kid = progress_dict

        # Mark achievement as earned for the kid by storing progress (e.g. set to target)
        progress_for_kid[const.DATA_ACHIEVEMENT_AWARDED] = True
        progress_for_kid[const.DATA_ACHIEVEMENT_CURRENT_VALUE] = achievement.get(
            const.DATA_ACHIEVEMENT_TARGET_VALUE, 1
        )

        # Award the extra reward points defined in the achievement
        extra_points = achievement.get(
            const.DATA_ACHIEVEMENT_REWARD_POINTS, const.DEFAULT_ZERO
        )
        kid_info = self.kids_data.get(kid_id)
        if kid_info is not None:
            new_points = float(kid_info[const.DATA_KID_POINTS]) + extra_points
            self.update_kid_points(kid_id, new_points)

        # Notify kid and parents
        extra_data = {
            const.DATA_KID_ID: kid_id,
            const.DATA_ACHIEVEMENT_ID: achievement_id,
        }
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Achievement Earned",
                message=f"You have earned the achievement: '{achievement.get(const.DATA_ACHIEVEMENT_NAME)}'.",
                extra_data=extra_data,
            )
        )
        self.hass.async_create_task(
            self._notify_parents(
                kid_id,
                title="KidsChores: Achievement Earned",
                message=f"{self.kids_data[kid_id][const.DATA_KID_NAME]} has earned the achievement: '{achievement.get(const.DATA_ACHIEVEMENT_NAME)}'.",
                extra_data=extra_data,
            )
        )
        const.LOGGER.info(
            "Awarded achievement '%s' to kid '%s'",
            achievement.get(const.DATA_ACHIEVEMENT_NAME),
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

        now = dt_util.utcnow()
        for challenge_id, challenge in self.challenges_data.items():
            progress = challenge.setdefault(const.DATA_CHALLENGE_PROGRESS, {})
            if kid_id in progress and progress[kid_id].get(
                const.DATA_CHALLENGE_AWARDED, False
            ):
                continue

            # Check challenge window
            start_date_raw = challenge.get(const.DATA_CHALLENGE_START_DATE)
            if isinstance(start_date_raw, str):
                start = dt_util.parse_datetime(start_date_raw)
            else:
                start = None

            end_date_raw = challenge.get(const.DATA_CHALLENGE_END_DATE)
            if isinstance(end_date_raw, str):
                end = dt_util.parse_datetime(end_date_raw)
            else:
                end = None

            if start and now < start:
                continue
            if end and now > end:
                continue

            target = challenge.get(const.DATA_CHALLENGE_TARGET_VALUE, 1)
            challenge_type = challenge.get(const.DATA_CHALLENGE_TYPE)

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

                required_daily = challenge.get(const.DATA_CHALLENGE_REQUIRED_DAILY, 1)
                start = dt_util.parse_datetime(
                    challenge.get(const.DATA_CHALLENGE_START_DATE)
                )
                end = dt_util.parse_datetime(
                    challenge.get(const.DATA_CHALLENGE_END_DATE)
                )
                if start and end:
                    num_days = (end - start).days + 1
                    # Verify for each day:
                    success = True
                    for n in range(num_days):
                        day = (start + timedelta(days=n)).date().isoformat()
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
        challenge = self.challenges_data.get(challenge_id)
        if not challenge:
            const.LOGGER.error(
                "Attempted to award non-existent challenge '%s'", challenge_id
            )
            return

        # Get or create the existing progress dictionary for this kid
        progress_for_kid = challenge.setdefault(
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
        progress_for_kid[const.DATA_CHALLENGE_COUNT] = challenge.get(
            const.DATA_CHALLENGE_TARGET_VALUE, 1
        )

        # Award extra reward points from the challenge
        extra_points = challenge.get(
            const.DATA_CHALLENGE_REWARD_POINTS, const.DEFAULT_ZERO
        )
        kid_info = self.kids_data.get(kid_id)
        if kid_info is not None:
            new_points = float(kid_info[const.DATA_KID_POINTS]) + extra_points
            self.update_kid_points(kid_id, new_points)

        # Notify kid and parents
        extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHALLENGE_ID: challenge_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Challenge Completed",
                message=f"You have completed the challenge: '{challenge.get(const.DATA_CHALLENGE_NAME)}'.",
                extra_data=extra_data,
            )
        )
        self.hass.async_create_task(
            self._notify_parents(
                kid_id,
                title="KidsChores: Challenge Completed",
                message=f"{self.kids_data[kid_id][const.DATA_KID_NAME]} has completed the challenge: '{challenge.get(const.DATA_CHALLENGE_NAME)}'.",
                extra_data=extra_data,
            )
        )
        const.LOGGER.info(
            "Awarded challenge '%s' to kid '%s'",
            challenge.get(const.DATA_CHALLENGE_NAME),
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
            except Exception:
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

    def _update_chore_streak_for_kid(
        self, kid_id: str, chore_id: str, completion_date: date
    ):
        """Update (or initialize) the streak for a specific chore for a kid, and update the max streak achieved so far."""

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        # Ensure a streak dictionary exists
        if const.DATA_KID_CHORE_STREAKS not in kid_info:
            kid_info[const.DATA_KID_CHORE_STREAKS] = {}

        # Initialize the streak record if not already present
        streak = kid_info[const.DATA_KID_CHORE_STREAKS].get(
            chore_id,
            {
                const.DATA_KID_CURRENT_STREAK: const.DEFAULT_ZERO,
                const.DATA_KID_MAX_STREAK: const.DEFAULT_ZERO,
                const.DATA_KID_LAST_STREAK_DATE: None,
            },
        )
        last_date = None
        if streak.get(const.DATA_KID_LAST_STREAK_DATE):
            try:
                last_date = date.fromisoformat(streak[const.DATA_KID_LAST_STREAK_DATE])
            except Exception:
                last_date = None

        # If the chore was already recorded today, do nothing
        if last_date == completion_date:
            return

        # If the last completion was exactly yesterday, increase the streak
        elif last_date == completion_date - timedelta(days=1):
            streak[const.DATA_KID_CURRENT_STREAK] += 1

        # Reset to 1 if not done yesterday
        else:
            streak[const.DATA_KID_CURRENT_STREAK] = 1

        streak[const.DATA_KID_LAST_STREAK_DATE] = completion_date.isoformat()

        # Update the maximum streak if the current streak is higher.
        if streak[const.DATA_KID_CURRENT_STREAK] > streak.get(
            const.DATA_KID_MAX_STREAK, const.DEFAULT_ZERO
        ):
            streak[const.DATA_KID_MAX_STREAK] = streak[const.DATA_KID_CURRENT_STREAK]

        kid_info[const.DATA_KID_CHORE_STREAKS][chore_id] = streak

    def _update_overall_chore_streak(self, kid_id: str, completion_date: date):
        """Update the overall streak for a kid (days in a row with at least one approved chore)."""

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return
        last_date = None
        if kid_info.get(const.DATA_KID_LAST_CHORE_DATE):
            try:
                last_date = date.fromisoformat(kid_info[const.DATA_KID_LAST_CHORE_DATE])
            except Exception:
                last_date = None

        # If the chore was already recorded today, do nothing
        if last_date == completion_date:
            return

        # If the last completion was exactly yesterday, increase the streak
        elif last_date == completion_date - timedelta(days=1):
            kid_info[const.DATA_KID_OVERALL_CHORE_STREAK] = (
                kid_info.get(const.DATA_KID_OVERALL_CHORE_STREAK, const.DEFAULT_ZERO)
                + 1
            )

        # Reset to 1 if not done yesterday
        else:
            kid_info[const.DATA_KID_OVERALL_CHORE_STREAK] = 1

        kid_info[const.DATA_KID_LAST_CHORE_DATE] = completion_date.isoformat()

    # -------------------------------------------------------------------------------------
    # Recurring / Reset / Overdue
    # -------------------------------------------------------------------------------------

    async def _check_overdue_chores(self):
        """Check and mark overdue chores if due date is passed.

        Send an overdue notification only if not sent in the last 24 hours.
        """
        now = dt_util.utcnow()
        const.LOGGER.debug("Starting overdue check at %s", now.isoformat())

        for chore_id, chore_info in self.chores_data.items():
            # const.LOGGER.debug("Checking chore '%s' id '%s' (state=%s)", chore_info.get(const.DATA_CHORE_NAME), chore_id, chore_info.get(const.DATA_CHORE_STATE))

            # Get the list of assigned kids
            assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
            # const.LOGGER.debug("Chore '%s' id '%s' assigned to kids: %s", chore_info.get(const.DATA_CHORE_NAME), chore_id, assigned_kids,)

            # Check if all assigned kids have either claimed or approved the chore
            all_kids_claimed_or_approved = all(
                chore_id
                in self.kids_data.get(kid_id, {}).get(const.DATA_KID_CLAIMED_CHORES, [])
                or chore_id
                in self.kids_data.get(kid_id, {}).get(
                    const.DATA_KID_APPROVED_CHORES, []
                )
                for kid_id in assigned_kids
            )

            # Debugging: Log the claim/approval status of each assigned kid
            for kid_id in assigned_kids:
                kid_info = self.kids_data.get(kid_id, {})
                has_claimed = chore_id in kid_info.get(
                    const.DATA_KID_CLAIMED_CHORES, []
                )
                has_approved = chore_id in kid_info.get(
                    const.DATA_KID_APPROVED_CHORES, []
                )

                # const.LOGGER.debug("Kid '%s': claimed=%s, approved=%s", kid_id, has_claimed, has_approved

            # Log the overall result of the check
            # const.LOGGER.debug("Chore '%s': all_kids_claimed_or_approved=%s", chore_id, all_kids_claimed_or_approved)

            # Only skip the chore if ALL assigned kids have acted on it
            if all_kids_claimed_or_approved:
                # const.LOGGER.debug("Skipping chore '%s': all assigned kids have claimed or approved", chore_id,)
                continue

            due_str = chore_info.get(const.DATA_CHORE_DUE_DATE)
            if not due_str:
                const.LOGGER.debug(
                    "Chore '%s' has no due_date; checking to confirm it isn't overdue; then skipping if not",
                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                )
                # If it has no due date, but is overdue, it should be marked as pending
                # Also check if status is independent, just in case
                if (
                    chore_info.get(const.DATA_CHORE_STATE) == const.CHORE_STATE_OVERDUE
                    or chore_info.get(const.DATA_CHORE_STATE)
                    == const.CHORE_STATE_INDEPENDENT
                ):
                    for kid_id in assigned_kids:
                        if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                            self._process_chore_state(
                                kid_id, chore_id, const.CHORE_STATE_PENDING
                            )
                            const.LOGGER.debug(
                                "Chore '%s' status is overdue but no due date; cleared overdue flags",
                                chore_id,
                            )
                continue

            try:
                due_date = dt_util.parse_datetime(due_str)
                if due_date is None:
                    raise ValueError("Parsed datetime is None")
                due_date = dt_util.as_utc(due_date)
                # const.LOGGER.debug("Chore '%s' due_date parsed as %s", chore_id, due_date.isoformat())
            except Exception as err:
                const.LOGGER.error(
                    "Error parsing due_date '%s' for chore '%s': %s",
                    due_str,
                    chore_id,
                    err,
                )
                continue

            # Check for applicable day is no longer required; the scheduling function ensures due_date matches applicable day criteria.
            # const.LOGGER.debug("Chore '%s': now=%s, due_date=%s", chore_id, now.isoformat(), due_date.isoformat()
            if now < due_date:
                # Not past due date, but before resetting the state back to pending, check if global state is currently overdue
                for kid_id in assigned_kids:
                    if chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
                        self._process_chore_state(
                            kid_id, chore_id, const.CHORE_STATE_PENDING
                        )
                        const.LOGGER.debug(
                            "Chore '%s' status is overdue but not yet due; cleared overdue flags",
                            chore_id,
                        )

                continue

            # Handling for overdue is the same for shared and non-shared chores
            # Status and global status will be determined by the chore state processor
            assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
            for kid_id in assigned_kids:
                kid_info = self.kids_data.get(kid_id, {})

                # Skip if kid already claimed/approved on the chore.
                if chore_id in kid_info.get(
                    const.DATA_KID_CLAIMED_CHORES, []
                ) or chore_id in kid_info.get(const.DATA_KID_APPROVED_CHORES, []):
                    continue

                # Mark chore as overdue for this kid.
                self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_OVERDUE)
                const.LOGGER.debug(
                    "Marking chore '%s' as overdue for kid '%s'", chore_id, kid_id
                )

                # Check notification timestamp.
                last_notif_str = kid_info[const.DATA_KID_OVERDUE_NOTIFICATIONS].get(
                    chore_id
                )
                notify = False
                if last_notif_str:
                    try:
                        last_dt = dt_util.parse_datetime(last_notif_str)
                        if (
                            last_dt is None
                            or (last_dt < due_date)
                            or (
                                (now - last_dt)
                                >= timedelta(hours=const.DEFAULT_NOTIFY_DELAY_REMINDER)
                            )
                        ):
                            notify = True
                        else:
                            const.LOGGER.debug(
                                "Chore '%s' for kid '%s' already notified within 24 hours",
                                chore_id,
                                kid_id,
                            )
                    except Exception as err:
                        const.LOGGER.error(
                            "Error parsing overdue notification '%s' for chore '%s', kid '%s': %s",
                            last_notif_str,
                            chore_id,
                            kid_id,
                            err,
                        )
                        notify = True
                else:
                    notify = True

                if notify:
                    kid_info[const.DATA_KID_OVERDUE_NOTIFICATIONS][chore_id] = (
                        now.isoformat()
                    )
                    extra_data = {
                        const.DATA_KID_ID: kid_id,
                        const.DATA_CHORE_ID: chore_id,
                    }
                    actions = [
                        {
                            const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_CHORE}|{kid_id}|{chore_id}",
                            const.NOTIFY_TITLE: const.ACTION_TITLE_APPROVE,
                        },
                        {
                            const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_CHORE}|{kid_id}|{chore_id}",
                            const.NOTIFY_TITLE: const.ACTION_TITLE_DISAPPROVE,
                        },
                        {
                            const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{chore_id}",
                            const.NOTIFY_TITLE: const.ACTION_TITLE_REMIND_30,
                        },
                    ]
                    const.LOGGER.debug(
                        "Sending overdue notification for chore '%s' to kid '%s'",
                        chore_id,
                        kid_id,
                    )
                    self.hass.async_create_task(
                        self._notify_kid(
                            kid_id,
                            title="KidsChores: Chore Overdue",
                            message=f"Your chore '{chore_info.get('name', 'Unnamed Chore')}' is overdue",
                            extra_data=extra_data,
                        )
                    )
                    self.hass.async_create_task(
                        self._notify_parents(
                            kid_id,
                            title="KidsChores: Chore Overdue",
                            message=f"{kh.get_kid_name_by_id(self, kid_id)}'s chore '{chore_info.get('name', 'Unnamed Chore')}' is overdue",
                            actions=actions,
                            extra_data=extra_data,
                        )
                    )
        const.LOGGER.debug("Overdue check completed")

    async def _reset_all_chore_counts(self, now: datetime):
        """Trigger resets based on the current time for all frequencies."""
        await self._handle_recurring_chore_resets(now)
        await self._reset_daily_reward_statuses()
        await self._check_overdue_chores()

        # Process Cumulative Badge Resets
        await self._reset_cumulative_badges()

        for kid in self.kids_data.values():
            kid[const.DATA_KID_TODAY_CHORE_APPROVALS] = {}

    async def _handle_recurring_chore_resets(self, now: datetime):
        """Handle recurring resets for daily, weekly, and monthly frequencies."""

        await self._reschedule_recurring_chores(now)

        # Daily
        if now.hour == const.DEFAULT_DAILY_RESET_TIME.get(
            const.CONF_HOUR, const.DEFAULT_HOUR
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
        # Reset counters on kids
        for kid_info in self.kids_data.values():
            if frequency == const.FREQUENCY_DAILY:
                kid_info[const.DATA_KID_COMPLETED_CHORES_TODAY] = const.DEFAULT_ZERO
                kid_info[const.DATA_KID_POINTS_EARNED_TODAY] = const.DEFAULT_ZERO
            elif frequency == const.FREQUENCY_WEEKLY:
                kid_info[const.DATA_KID_COMPLETED_CHORES_WEEKLY] = const.DEFAULT_ZERO
                kid_info[const.DATA_KID_POINTS_EARNED_WEEKLY] = const.DEFAULT_ZERO
            elif frequency == const.FREQUENCY_MONTHLY:
                kid_info[const.DATA_KID_COMPLETED_CHORES_MONTHLY] = const.DEFAULT_ZERO
                kid_info[const.DATA_KID_POINTS_EARNED_MONTHLY] = const.DEFAULT_ZERO

        const.LOGGER.info(f"{frequency.capitalize()} chore counts have been reset")

        # If daily reset -> reset statuses
        if frequency == const.FREQUENCY_DAILY:
            await self._reset_daily_chore_statuses([frequency])
        elif frequency == const.FREQUENCY_WEEKLY:
            await self._reset_daily_chore_statuses([frequency, const.FREQUENCY_WEEKLY])

    async def _reschedule_recurring_chores(self, now: datetime):
        """For chores with the given recurring frequency, reschedule due date if they are approved and past due."""

        for chore_id, chore_info in self.chores_data.items():
            # Only consider chores with a recurring frequency (any of the three) and a defined due_date:
            if chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY) not in (
                const.FREQUENCY_DAILY,
                const.FREQUENCY_WEEKLY,
                const.FREQUENCY_BIWEEKLY,
                const.FREQUENCY_MONTHLY,
                const.FREQUENCY_CUSTOM,
            ):
                continue
            if not chore_info.get(const.DATA_CHORE_DUE_DATE):
                continue

            try:
                due_date = dt_util.parse_datetime(
                    chore_info[const.DATA_CHORE_DUE_DATE]
                ) or datetime.fromisoformat(chore_info[const.DATA_CHORE_DUE_DATE])
            except Exception as e:
                const.LOGGER.warning(
                    "Error parsing due_date for chore '%s': %s", chore_id, e
                )
                continue

            # If the due date is in the past and the chore is approved or approved_in_part
            if now > due_date and chore_info.get(const.DATA_CHORE_STATE) in [
                const.CHORE_STATE_APPROVED,
                const.CHORE_STATE_APPROVED_IN_PART,
            ]:
                # Reschedule the chore
                self._reschedule_next_due_date(chore_info)
                const.LOGGER.debug(
                    "Rescheduled recurring chore '%s'",
                    chore_info.get(const.DATA_CHORE_NAME, chore_id),
                )

        self._persist()
        self.async_set_updated_data(self._data)
        const.LOGGER.debug("Daily rescheduling of recurring chores complete")

    async def _reset_daily_chore_statuses(self, target_freqs: list[str]):
        """Reset chore statuses and clear approved/claimed chores for chores with these freq."""
        const.LOGGER.info("Executing _reset_daily_chore_statuses")

        now = dt_util.utcnow()
        for chore_id, chore_info in self.chores_data.items():
            frequency = chore_info.get(
                const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
            )
            # Only consider chores whose frequency is either in target_freqs or const.FREQUENCY_NONE.
            if frequency in target_freqs or frequency == const.FREQUENCY_NONE:
                due_date_str = chore_info.get(const.DATA_CHORE_DUE_DATE)
                if due_date_str:
                    try:
                        due_date = dt_util.parse_datetime(
                            due_date_str
                        ) or datetime.fromisoformat(due_date_str)
                        # If the due date has not yet been reached, skip resetting this chore.
                        if now < due_date:
                            continue
                    except Exception as e:
                        const.LOGGER.warning(
                            "Error parsing due_date '%s' for chore '%s': %s",
                            due_date_str,
                            chore_id,
                            e,
                        )
                # If no due date or the due date has passed, then reset the chore state
                if chore_info[const.DATA_CHORE_STATE] not in [
                    const.CHORE_STATE_PENDING,
                    const.CHORE_STATE_OVERDUE,
                ]:
                    previous_state = chore_info[const.DATA_CHORE_STATE]
                    for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                        if kid_id:
                            self._process_chore_state(
                                kid_id, chore_id, const.CHORE_STATE_PENDING
                            )
                    const.LOGGER.debug(
                        "Resetting chore '%s' from '%s' to '%s'",
                        chore_id,
                        previous_state,
                        const.CHORE_STATE_PENDING,
                    )

        # clear pending chore approvals
        target_chore_ids = [
            chore_id
            for chore_id, chore_info in self.chores_data.items()
            if chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY) in target_freqs
        ]
        self._data[const.DATA_PENDING_CHORE_APPROVALS] = [
            ap
            for ap in self._data[const.DATA_PENDING_CHORE_APPROVALS]
            if ap[const.DATA_CHORE_ID] not in target_chore_ids
        ]

        self._persist()

    async def _reset_daily_reward_statuses(self):
        """Reset all kids' reward states daily."""
        # Remove from global pending reward approvals
        self._data[const.DATA_PENDING_REWARD_APPROVALS] = []
        const.LOGGER.debug("Cleared all pending reward approvals globally")

        # For each kid, clear pending/approved reward lists to reflect daily reset
        for kid_id, kid_info in self.kids_data.items():
            kid_info[const.DATA_KID_PENDING_REWARDS] = []
            kid_info[const.DATA_KID_REDEEMED_REWARDS] = []

            const.LOGGER.debug(
                "Cleared daily reward statuses for kid ID '%s' (%s)",
                kid_id,
                kid_info.get(const.DATA_KID_NAME, const.UNKNOWN_KID),
            )

        self._persist()
        self.async_set_updated_data(self._data)
        const.LOGGER.info("Daily reward statuses have been reset")

    def _reschedule_next_due_date(self, chore_info: dict[str, Any]):
        """Reschedule the next due date based on the recurring frequency."""
        freq = chore_info.get(
            const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
        )
        if freq == const.FREQUENCY_CUSTOM:
            custom_interval = chore_info.get(const.DATA_CHORE_CUSTOM_INTERVAL)
            custom_unit = chore_info.get(const.DATA_CHORE_CUSTOM_INTERVAL_UNIT)
            if custom_interval is None or custom_unit not in [
                const.CONF_DAYS,
                const.CONF_WEEKS,
                const.CONF_MONTHS,
            ]:
                const.LOGGER.warning(
                    "Custom frequency set but custom_interval or unit invalid for chore '%s'",
                    chore_info.get(const.DATA_CHORE_NAME),
                )
                return

        due_date_str = chore_info.get(const.DATA_CHORE_DUE_DATE)
        if not freq or freq == const.FREQUENCY_NONE or not due_date_str:
            const.LOGGER.debug(
                "Skipping reschedule: recurring_frequency=%s, due_date=%s",
                freq,
                due_date_str,
            )
            return
        try:
            original_due = dt_util.parse_datetime(due_date_str)
            if not original_due:
                original_due = datetime.fromisoformat(due_date_str)
        except ValueError:
            const.LOGGER.warning("Unable to parse due_date '%s'", due_date_str)
            return

        applicable_days = chore_info.get(
            const.CONF_APPLICABLE_DAYS, const.DEFAULT_APPLICABLE_DAYS
        )
        weekday_mapping = {i: key for i, key in enumerate(const.WEEKDAY_OPTIONS.keys())}
        # Convert next_due to local time for proper weekday checking
        now = dt_util.utcnow()
        now_local = dt_util.as_local(now)
        next_due = original_due
        next_due_local = dt_util.as_local(next_due)

        # Track first iteration to allow one advancement for future dates
        first_iteration = True
        # Ensure the next due date is advanced even if it's already scheduled in the future
        # Handle past due_date by looping until we find a future date that is also on an applicable day
        while (
            first_iteration
            or next_due_local <= now_local
            or (
                applicable_days
                and weekday_mapping[next_due_local.weekday()] not in applicable_days
            )
        ):
            # If next_due is still in the past, increment by the full frequency period
            if first_iteration or (next_due_local <= now_local):
                if freq == const.FREQUENCY_DAILY:
                    next_due += timedelta(days=1)
                elif freq == const.FREQUENCY_WEEKLY:
                    next_due += timedelta(weeks=1)
                elif freq == const.FREQUENCY_BIWEEKLY:
                    next_due += timedelta(weeks=2)
                elif freq == const.FREQUENCY_MONTHLY:
                    next_due = self._add_months(next_due, 1)
                elif freq == const.FREQUENCY_CUSTOM:
                    if custom_unit == const.CONF_DAYS:
                        next_due += timedelta(days=custom_interval)
                    elif custom_unit == const.CONF_WEEKS:
                        next_due += timedelta(weeks=custom_interval)
                    elif custom_unit == const.CONF_MONTHS:
                        next_due = self._add_months(next_due, custom_interval)
            else:
                # Next due is in the future but not on an applicable day,
                # so just add one day until it falls on an applicable day.
                next_due += timedelta(days=1)

            # After first loop, only move forward if necessary
            first_iteration = False

            # Update the local time reference for the new next_due
            next_due_local = dt_util.as_local(next_due)

            const.LOGGER.debug(
                "Rescheduling chore: Original Due: %s, New Attempt: %s (Local: %s), Now: %s (Local: %s), Weekday: %s, Applicable Days: %s",
                original_due,
                next_due,
                next_due_local,
                now,
                now_local,
                weekday_mapping[next_due_local.weekday()],
                applicable_days,
            )

        chore_info[const.DATA_CHORE_DUE_DATE] = next_due.isoformat()
        chore_id = chore_info.get(const.DATA_CHORE_INTERNAL_ID)

        # Update config_entry.options for this chore so that the new due_date is visible in Options
        self.hass.async_create_task(
            self._update_chore_due_date_in_config(
                chore_id, chore_info[const.DATA_CHORE_DUE_DATE], None, None, None
            )
        )
        # Reset the chore state to Pending
        for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            if kid_id:
                self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)

        const.LOGGER.info(
            "Chore '%s' rescheduled: Original due date %s, Final new due date (local) %s",
            chore_info.get(const.DATA_CHORE_NAME, chore_id),
            dt_util.as_local(original_due).isoformat(),
            next_due_local.isoformat(),
        )

    # Removed the _add_one_month method since _add_months method will handle all cases including adding one month.
    def _add_months(self, dt_in: datetime, months: int) -> datetime:
        """Add a specified number of months to a datetime, preserving the day if possible."""
        total_month = dt_in.month + months
        year = dt_in.year + (total_month - 1) // 12
        month = ((total_month - 1) % 12) + 1
        day = dt_in.day
        days_in_new_month = monthrange(year, month)[1]

        if day > days_in_new_month:
            day = days_in_new_month

        return dt_in.replace(year=year, month=month, day=day)

    # Set Chore Due Date
    def set_chore_due_date(self, chore_id: str, due_date: Optional[datetime]) -> None:
        """Set the due date of a chore."""
        # Retrieve the chore data; raise error if not found.
        chore_info = self.chores_data.get(chore_id)
        if chore_info is None:
            raise HomeAssistantError(f"Chore with ID '{chore_id}' not found.")

        # Convert the due_date to an ISO-formatted string if provided; otherwise use None.
        new_due_date = due_date.isoformat() if due_date else None

        # Update the chore's due date. If the key is missing, add it.
        try:
            chore_info[const.DATA_CHORE_DUE_DATE] = new_due_date
        except KeyError as err:
            raise HomeAssistantError(
                f"Missing 'due_date' key in chore data for '{chore_id}': {err}"
            )

        # If the due date is cleared (None), then remove any recurring frequency
        # and custom interval settings unless the frequency is none, daily, or weekly.
        if new_due_date is None:
            # const.FREQUENCY_DAILY, const.FREQUENCY_WEEKLY, and const.FREQUENCY_NONE are all OK without a due_date
            current_frequency = chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY)
            if chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY) not in (
                const.FREQUENCY_NONE,
                const.FREQUENCY_DAILY,
                const.FREQUENCY_WEEKLY,
            ):
                const.LOGGER.debug(
                    "Removing frequency for chore '%s': current frequency '%s' is does not work with a due date of None",
                    chore_id,
                    current_frequency,
                )
                chore_info[const.DATA_CHORE_RECURRING_FREQUENCY] = const.FREQUENCY_NONE
                chore_info.pop(const.DATA_CHORE_CUSTOM_INTERVAL, None)
                chore_info.pop(const.DATA_CHORE_CUSTOM_INTERVAL_UNIT, None)

        # Update config_entry.options so that the new due date is visible in Options.
        # Use new_due_date here to ensure we’re passing the updated value.
        self.hass.async_create_task(
            self._update_chore_due_date_in_config(
                chore_id,
                chore_info.get(const.DATA_CHORE_DUE_DATE),
                chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY),
                chore_info.get(const.DATA_CHORE_CUSTOM_INTERVAL),
                chore_info.get(const.DATA_CHORE_CUSTOM_INTERVAL_UNIT),
            )
        )

        # Reset the chore state to Pending
        for kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
            if kid_id:
                self._process_chore_state(kid_id, chore_id, const.CHORE_STATE_PENDING)

        const.LOGGER.info(
            "Chore '%s' due date set",
            chore_info.get(const.DATA_CHORE_NAME, chore_id),
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # Skip Chore Due Date
    def skip_chore_due_date(self, chore_id: str) -> None:
        """Skip the current due date of a recurring chore and reschedule it."""
        chore = self.chores_data.get(chore_id)
        if not chore:
            raise HomeAssistantError(f"Chore with ID '{chore_id}' not found.")

        if (
            chore.get(const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE)
            == const.FREQUENCY_NONE
        ):
            raise HomeAssistantError(
                f"Chore '{chore.get(const.DATA_CHORE_NAME, chore_id)}' does not have a recurring frequency."
            )
        if not chore.get(const.DATA_CHORE_DUE_DATE):
            raise HomeAssistantError(
                f"Chore '{chore.get(const.DATA_CHORE_NAME, chore_id)}' does not have a due date set."
            )

        # Compute the next due date and update the chore options/config.
        self._reschedule_next_due_date(chore)

        self._persist()
        self.async_set_updated_data(self._data)

    # Reset Overdue Chores
    def reset_overdue_chores(
        self, chore_id: Optional[str] = None, kid_id: Optional[str] = None
    ) -> None:
        """Reset overdue chore(s) to Pending state and reschedule."""

        if chore_id:
            # Specific chore reset (with or without kid_id)
            chore = self.chores_data.get(chore_id)
            if not chore:
                raise HomeAssistantError(f"Chore with ID '{chore_id}' not found.")

            # Reschedule happens at the chore level, so it is not necessary to check for kid_id
            # _rescheduled_next_due_date will also handle setting the status to Pending
            self._reschedule_next_due_date(chore)

        elif kid_id:
            # Kid-only reset: reset all overdue chores for the specified kid.
            # Note that reschedule happens at the chore level, so it chores assigned to this
            # kid that are multi assigned will show as reset for those other kids
            kid = self.kids_data.get(kid_id)
            if not kid:
                raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")
            for cid, chore in self.chores_data.items():
                if kid_id in chore.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                    if cid in kid.get(const.DATA_KID_OVERDUE_CHORES, []):
                        # Reschedule chore which will also set status to Pending
                        self._reschedule_next_due_date(chore)
        else:
            # Global reset: Reset all chores that are overdue.
            for kid_id, kid in self.kids_data.items():
                for cid, chore in self.chores_data.items():
                    if kid_id in chore.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                        if cid in kid.get(const.DATA_KID_OVERDUE_CHORES, []):
                            # Reschedule chore which will also set status to Pending
                            self._reschedule_next_due_date(chore)

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
                    "Reset Penalties: Kid with ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")
            if penalty_id not in kid_info.get(const.DATA_KID_PENALTY_APPLIES, {}):
                const.LOGGER.error(
                    "Reset Penalties: Penalty '%s' does not apply to kid '%s'.",
                    penalty_id,
                    kid_id,
                )
                raise HomeAssistantError(
                    f"Penalty '{penalty_id}' does not apply to kid '{kid_id}'."
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
                    "Reset Penalties: Penalty '%s' not found in any kid's data.",
                    penalty_id,
                )

        elif kid_id:
            # Reset all penalties for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error(
                    "Reset Penalties: Kid with ID '%s' not found.", kid_id
                )
                raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

            kid_info[const.DATA_KID_PENALTY_APPLIES].clear()

        else:
            # Reset all penalties for all kids
            const.LOGGER.info("Reset Penalties: Resetting all penalties for all kids.")
            for kid_info in self.kids_data.values():
                kid_info[const.DATA_KID_PENALTY_APPLIES].clear()

        const.LOGGER.debug(
            "Penalties reset completed (kid_id=%s, penalty_id=%s)", kid_id, penalty_id
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
                const.LOGGER.error("Reset Bonuses: Kid with ID '%s' not found.", kid_id)
                raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")
            if bonus_id not in kid_info.get(const.DATA_KID_BONUS_APPLIES, {}):
                const.LOGGER.error(
                    "Reset Bonuses: Bonus '%s' does not apply to kid '%s'.",
                    bonus_id,
                    kid_id,
                )
                raise HomeAssistantError(
                    f"Bonus '{bonus_id}' does not apply to kid '{kid_id}'."
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
                    "Reset Bonuses: Bonus '%s' not found in any kid's data.", bonus_id
                )

        elif kid_id:
            # Reset all bonuses for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error("Reset Bonuses: Kid with ID '%s' not found.", kid_id)
                raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

            kid_info[const.DATA_KID_BONUS_APPLIES].clear()

        else:
            # Reset all bonuses for all kids
            const.LOGGER.info("Reset Bonuses: Resetting all bonuses for all kids.")
            for kid_info in self.kids_data.values():
                kid_info[const.DATA_KID_BONUS_APPLIES].clear()

        const.LOGGER.debug(
            "Bonuses reset completed (kid_id=%s, bonus_id=%s)", kid_id, bonus_id
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------------------
    # Rewards: Reset
    # This function resets reward-related data for a specified kid and/or reward by
    # clearing claims, approvals, redeemed and pending rewards, and removing associated
    # pending reward approvals from the global data.
    # -------------------------------------------------------------------------------------

    def reset_rewards(
        self, kid_id: Optional[str] = None, reward_id: Optional[str] = None
    ) -> None:
        """Reset rewards based on provided kid_id and reward_id."""

        if reward_id and kid_id:
            # Reset a specific reward for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error("Reset Rewards: Kid with ID '%s' not found.", kid_id)
                raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

            kid_info[const.DATA_KID_REWARD_CLAIMS].pop(reward_id, None)
            kid_info[const.DATA_KID_REWARD_APPROVALS].pop(reward_id, None)
            kid_info[const.DATA_KID_REDEEMED_REWARDS] = [
                reward
                for reward in kid_info[const.DATA_KID_REDEEMED_REWARDS]
                if reward != reward_id
            ]
            kid_info[const.DATA_KID_PENDING_REWARDS] = [
                reward
                for reward in kid_info[const.DATA_KID_PENDING_REWARDS]
                if reward != reward_id
            ]

            # Remove open claims from pending approvals for this kid and reward.
            self._data[const.DATA_PENDING_REWARD_APPROVALS] = [
                ap
                for ap in self._data[const.DATA_PENDING_REWARD_APPROVALS]
                if not (
                    ap[const.DATA_KID_ID] == kid_id
                    and ap[const.DATA_REWARD_ID] == reward_id
                )
            ]

        elif reward_id:
            # Reset a specific reward for all kids
            found = False
            for kid_info in self.kids_data.values():
                if reward_id in kid_info.get(const.DATA_KID_REWARD_CLAIMS, {}):
                    found = True
                    kid_info[const.DATA_KID_REWARD_CLAIMS].pop(reward_id, None)
                if reward_id in kid_info.get(const.DATA_KID_REWARD_APPROVALS, {}):
                    found = True
                    kid_info[const.DATA_KID_REWARD_APPROVALS].pop(reward_id, None)
                kid_info[const.DATA_KID_REDEEMED_REWARDS] = [
                    reward
                    for reward in kid_info[const.DATA_KID_REDEEMED_REWARDS]
                    if reward != reward_id
                ]
                kid_info[const.DATA_KID_PENDING_REWARDS] = [
                    reward
                    for reward in kid_info[const.DATA_KID_PENDING_REWARDS]
                    if reward != reward_id
                ]
            # Remove open claims from pending approvals for this reward (all kids).
            self._data[const.DATA_PENDING_REWARD_APPROVALS] = [
                ap
                for ap in self._data[const.DATA_PENDING_REWARD_APPROVALS]
                if ap[const.DATA_REWARD_ID] != reward_id
            ]
            if not found:
                const.LOGGER.warning(
                    "Reset Rewards: Reward '%s' not found in any kid's data.",
                    reward_id,
                )

        elif kid_id:
            # Reset all rewards for a specific kid
            kid_info = self.kids_data.get(kid_id)
            if not kid_info:
                const.LOGGER.error("Reset Rewards: Kid with ID '%s' not found.", kid_id)
                raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

            kid_info[const.DATA_KID_REWARD_CLAIMS].clear()
            kid_info[const.DATA_KID_REWARD_APPROVALS].clear()
            kid_info[const.DATA_KID_REDEEMED_REWARDS].clear()
            kid_info[const.DATA_KID_PENDING_REWARDS].clear()

            # Remove open claims from pending approvals for that kid.
            self._data[const.DATA_PENDING_REWARD_APPROVALS] = [
                ap
                for ap in self._data[const.DATA_PENDING_REWARD_APPROVALS]
                if ap[const.DATA_KID_ID] != kid_id
            ]

        else:
            # Reset all rewards for all kids
            const.LOGGER.info("Reset Rewards: Resetting all rewards for all kids.")
            for kid_info in self.kids_data.values():
                kid_info[const.DATA_KID_REWARD_CLAIMS].clear()
                kid_info[const.DATA_KID_REWARD_APPROVALS].clear()
                kid_info[const.DATA_KID_REDEEMED_REWARDS].clear()
                kid_info[const.DATA_KID_PENDING_REWARDS].clear()

            # Clear all pending reward approvals.
            self._data[const.DATA_PENDING_REWARD_APPROVALS].clear()

        const.LOGGER.debug(
            "Rewards reset completed (kid_id=%s, reward_id=%s)", kid_id, reward_id
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # Persist new due dates on config entries
    # This is not being used currently, but was refactored so it calls a new function _update_chore_due_date_in_config
    # which can be used to update a single chore's due date and frequency.  New function can be used in multiple places.

    async def _update_all_chore_due_dates_in_config(self) -> None:
        """Update due dates for all chores in config_entry.options."""
        tasks = []
        for chore_id, chore_info in self.chores_data.items():
            if const.DATA_CHORE_DUE_DATE in chore_info:
                tasks.append(
                    self._update_chore_due_date_in_config(
                        chore_id,
                        chore_info.get(const.DATA_CHORE_DUE_DATE),
                        recurring_frequency=chore_info.get(
                            const.DATA_CHORE_RECURRING_FREQUENCY
                        ),
                        custom_interval=chore_info.get(
                            const.DATA_CHORE_CUSTOM_INTERVAL
                        ),
                        custom_interval_unit=chore_info.get(
                            const.DATA_CHORE_CUSTOM_INTERVAL_UNIT
                        ),
                    )
                )

        # Run all updates concurrently
        if tasks:
            await asyncio.gather(*tasks)

    # Persist new due dates on config entries
    async def _update_chore_due_date_in_config(
        self,
        chore_id: str,
        due_date: Optional[str],
        recurring_frequency: Optional[str] = None,
        custom_interval: Optional[int] = None,
        custom_interval_unit: Optional[str] = None,
    ) -> None:
        """Update the due date and frequency fields for a specific chore in config_entry.options.

        - due_date should be an ISO-formatted string (or None).
        - If a frequency is passed, then that value is set.
        If the frequency is const.FREQUENCY_CUSTOM, custom_interval and custom_interval_unit are required.
        If the frequency is not custom, any custom interval settings are cleared.
        - If no frequency is passed, then do not change the frequency or custom interval settings.
        """
        updated_options = dict(self.config_entry.options)
        chores_conf = dict(updated_options.get(const.DATA_CHORES, {}))

        # Get existing options for the chore.
        existing_options = dict(chores_conf.get(chore_id, {}))

        # Update due_date: set if provided; otherwise remove.
        if due_date is not None:
            existing_options[const.DATA_CHORE_DUE_DATE] = due_date
        else:
            existing_options.pop(const.DATA_CHORE_DUE_DATE, None)

        # If a frequency is passed, update it.
        if recurring_frequency is not None:
            existing_options[const.DATA_CHORE_RECURRING_FREQUENCY] = recurring_frequency
            if recurring_frequency == const.FREQUENCY_CUSTOM:
                # For custom frequency, custom_interval and custom_interval_unit are required.
                if custom_interval is None or custom_interval_unit is None:
                    raise HomeAssistantError(
                        "For custom frequency, both custom_interval and custom_interval_unit are required."
                    )
                existing_options[const.DATA_CHORE_CUSTOM_INTERVAL] = custom_interval
                existing_options[const.DATA_CHORE_CUSTOM_INTERVAL_UNIT] = (
                    custom_interval_unit
                )
            else:
                # For non-custom frequencies, clear any custom interval settings.
                existing_options.pop(const.DATA_CHORE_CUSTOM_INTERVAL, None)
                existing_options.pop(const.DATA_CHORE_CUSTOM_INTERVAL_UNIT, None)
        # If no frequency is passed, leave the frequency and custom fields unchanged.

        chores_conf[chore_id] = existing_options
        updated_options[const.DATA_CHORES] = chores_conf

        new_data = dict(self.config_entry.data)
        new_data[const.DATA_LAST_CHANGE] = dt_util.utcnow().isoformat()

        update_result = self.hass.config_entries.async_update_entry(
            self.config_entry, data=new_data, options=updated_options
        )
        if asyncio.iscoroutine(update_result):
            await update_result

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
                "No user id provided. Sending a general persistent notification"
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
            user_obj: User = await hass.auth.async_get_user(user_id)
            if not user_obj:
                const.LOGGER.warning(
                    "User with ID '%s' not found. Sending fallback persistent notification",
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
        except Exception as err:
            const.LOGGER.warning(
                "Failed to send user-specific notification to '%s': %s. Fallback to persistent notification",
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
            const.LOGGER.debug("Notifications disabled for kid '%s'", kid_id)
            return
        mobile_enabled = kid_info.get(const.CONF_ENABLE_MOBILE_NOTIFICATIONS, True)
        persistent_enabled = kid_info.get(
            const.CONF_ENABLE_PERSISTENT_NOTIFICATIONS, True
        )
        mobile_notify_service = kid_info.get(
            const.CONF_MOBILE_NOTIFY_SERVICE, const.CONF_EMPTY
        )
        if mobile_enabled and mobile_notify_service:
            await async_send_notification(
                self.hass,
                mobile_notify_service,
                title,
                message,
                actions=actions,
                extra_data=extra_data,
                use_persistent=persistent_enabled,
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
            const.LOGGER.debug("No notification method configured for kid '%s'", kid_id)

    async def _notify_parents(
        self,
        kid_id: str,
        title: str,
        message: str,
        actions: Optional[list[dict[str, str]]] = None,
        extra_data: Optional[dict] = None,
    ) -> None:
        """Notify all parents associated with a kid using their settings."""
        for parent_id, parent_info in self.parents_data.items():
            if kid_id not in parent_info.get(const.DATA_PARENT_ASSOCIATED_KIDS, []):
                continue
            if not parent_info.get(const.DATA_PARENT_ENABLE_NOTIFICATIONS, True):
                const.LOGGER.debug("Notifications disabled for parent '%s'", parent_id)
                continue
            mobile_enabled = parent_info.get(
                const.CONF_ENABLE_MOBILE_NOTIFICATIONS, True
            )
            persistent_enabled = parent_info.get(
                const.CONF_ENABLE_PERSISTENT_NOTIFICATIONS, True
            )
            mobile_notify_service = parent_info.get(
                const.CONF_MOBILE_NOTIFY_SERVICE, const.CONF_EMPTY
            )
            if mobile_enabled and mobile_notify_service:
                await async_send_notification(
                    self.hass,
                    mobile_notify_service,
                    title,
                    message,
                    actions=actions,
                    extra_data=extra_data,
                    use_persistent=persistent_enabled,
                )
            elif persistent_enabled:
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
                    "No notification method configured for parent '%s'", parent_id
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
        const.LOGGER.info(
            "Scheduling reminder for kid '%s', chore '%s', reward '%s' in %d minutes",
            kid_id,
            chore_id,
            reward_id,
            minutes,
        )
        await asyncio.sleep(minutes * 60)

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            const.LOGGER.warning(
                "Kid with ID '%s' not found during reminder check", kid_id
            )
            return

        if chore_id:
            chore_info = self.chores_data.get(chore_id)
            if not chore_info:
                const.LOGGER.warning(
                    "Chore with ID '%s' not found during reminder check", chore_id
                )
                return
            # Only resend if the chore is still in a pending-like state.
            if chore_info.get(const.DATA_CHORE_STATE) not in [
                const.CHORE_STATE_PENDING,
                const.CHORE_STATE_CLAIMED,
                const.CHORE_STATE_OVERDUE,
            ]:
                const.LOGGER.info(
                    "Chore '%s' is no longer pending approval; no reminder sent",
                    chore_id,
                )
                return
            actions = [
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_CHORE}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_APPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_CHORE}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_DISAPPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{chore_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_REMIND_30,
                },
            ]
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_CHORE_ID: chore_id}
            await self._notify_parents(
                kid_id,
                title="KidsChores: Reminder for Pending Chore",
                message=f"Reminder: {kid_info.get(const.DATA_KID_NAME, 'A kid')} has '{chore_info.get(const.DATA_CHORE_NAME, 'Unnamed Chore')}' chore pending approval.",
                actions=actions,
                extra_data=extra_data,
            )
            const.LOGGER.info(
                "Resent reminder for chore '%s' for kid '%s'", chore_id, kid_id
            )
        elif reward_id:
            # Check if the reward is still pending approval.
            if reward_id not in kid_info.get(const.DATA_KID_PENDING_REWARDS, []):
                const.LOGGER.info(
                    "Reward '%s' is no longer pending approval for kid '%s'; no reminder sent",
                    reward_id,
                    kid_id,
                )
                return
            actions = [
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_APPROVE_REWARD}|{kid_id}|{reward_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_APPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_DISAPPROVE_REWARD}|{kid_id}|{reward_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_DISAPPROVE,
                },
                {
                    const.NOTIFY_ACTION: f"{const.ACTION_REMIND_30}|{kid_id}|{reward_id}",
                    const.NOTIFY_TITLE: const.ACTION_TITLE_REMIND_30,
                },
            ]
            extra_data = {const.DATA_KID_ID: kid_id, const.DATA_REWARD_ID: reward_id}
            reward = self.rewards_data.get(reward_id, {})
            reward_name = reward.get(const.DATA_REWARD_NAME, "the reward")
            await self._notify_parents(
                kid_id,
                title="KidsChores: Reminder for Pending Reward",
                message=f"Reminder: {kid_info.get(const.DATA_KID_NAME, 'A kid')} has '{reward_name}' reward pending approval.",
                actions=actions,
                extra_data=extra_data,
            )
            const.LOGGER.info(
                "Resent reminder for reward '%s' for kid '%s'", reward_id, kid_id
            )
        else:
            const.LOGGER.warning(
                "No chore_id or reward_id provided for reminder action"
            )

    # -------------------------------------------------------------------------------------
    # Storage
    # -------------------------------------------------------------------------------------

    def _persist(self):
        """Save to persistent storage."""
        self.storage_manager.set_data(self._data)
        self.hass.add_job(self.storage_manager.async_save)
