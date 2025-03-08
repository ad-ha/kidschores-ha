# File: coordinator.py
"""Coordinator for the KidsChores integration.

Handles data synchronization, chore claiming and approval, badge tracking,
reward redemption, penalty application, and recurring chore handling.
Manages entities primarily using internal_id for consistency.
"""

import asyncio
import uuid
from calendar import monthrange
from datetime import datetime, timedelta
from typing import Any, Optional

from homeassistant.auth.models import User
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util


from .const import (
    ACHIEVEMENT_TYPE_DAILY_MIN,
    ACHIEVEMENT_TYPE_STREAK,
    ACHIEVEMENT_TYPE_TOTAL,
    ACTION_APPROVE_CHORE,
    ACTION_APPROVE_REWARD,
    ACTION_DISAPPROVE_CHORE,
    ACTION_DISAPPROVE_REWARD,
    ACTION_REMIND_30,
    ACTION_TITLE_APPROVE,
    ACTION_TITLE_DISAPPROVE,
    ACTION_TITLE_REMIND_30,
    BADGE_THRESHOLD_TYPE_CHORE_COUNT,
    BADGE_THRESHOLD_TYPE_POINTS,
    CHALLENGE_TYPE_DAILY_MIN,
    CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW,
    CHORE_STATE_APPROVED,
    CHORE_STATE_APPROVED_IN_PART,
    CHORE_STATE_CLAIMED,
    CHORE_STATE_CLAIMED_IN_PART,
    CHORE_STATE_INDEPENDENT,
    CHORE_STATE_OVERDUE,
    CHORE_STATE_PARTIAL,
    CHORE_STATE_PENDING,
    CHORE_STATE_UNKNOWN,
    CONF_ACHIEVEMENTS,
    CONF_APPLICABLE_DAYS,
    CONF_BADGES,
    CONF_CHALLENGES,
    CONF_CHORES,
    CONF_ENABLE_MOBILE_NOTIFICATIONS,
    CONF_ENABLE_PERSISTENT_NOTIFICATIONS,
    CONF_KIDS,
    CONF_MOBILE_NOTIFY_SERVICE,
    CONF_NOTIFY_ON_APPROVAL,
    CONF_NOTIFY_ON_CLAIM,
    CONF_NOTIFY_ON_DISAPPROVAL,
    CONF_PARENTS,
    CONF_PENALTIES,
    CONF_REWARDS,
    CONF_BONUSES,
    DATA_ACHIEVEMENTS,
    DATA_BADGES,
    DATA_CHALLENGES,
    DATA_CHORES,
    DATA_KIDS,
    DATA_PARENTS,
    DATA_PENDING_CHORE_APPROVALS,
    DATA_PENDING_REWARD_APPROVALS,
    DATA_PENALTIES,
    DATA_REWARDS,
    DATA_BONUSES,
    DEFAULT_APPLICABLE_DAYS,
    DEFAULT_BADGE_THRESHOLD,
    DEFAULT_DAILY_RESET_TIME,
    DEFAULT_ICON,
    DEFAULT_MONTHLY_RESET_DAY,
    DEFAULT_MULTIPLE_CLAIMS_PER_DAY,
    DEFAULT_NOTIFY_ON_APPROVAL,
    DEFAULT_NOTIFY_ON_CLAIM,
    DEFAULT_NOTIFY_ON_DISAPPROVAL,
    DEFAULT_PARTIAL_ALLOWED,
    DEFAULT_PENALTY_ICON,
    DEFAULT_PENALTY_POINTS,
    DEFAULT_POINTS,
    DEFAULT_POINTS_MULTIPLIER,
    DEFAULT_REWARD_COST,
    DEFAULT_REWARD_ICON,
    DEFAULT_BONUS_ICON,
    DEFAULT_BONUS_POINTS,
    DEFAULT_WEEKLY_RESET_DAY,
    DOMAIN,
    FREQUENCY_BIWEEKLY,
    FREQUENCY_CUSTOM,
    FREQUENCY_DAILY,
    FREQUENCY_MONTHLY,
    FREQUENCY_NONE,
    FREQUENCY_WEEKLY,
    LOGGER,
    UPDATE_INTERVAL,
    WEEKDAY_OPTIONS,
)

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
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(minutes=UPDATE_INTERVAL),
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
            LOGGER.warning("Error migrating datetime '%s': %s", dt_str, err)
            return dt_str

    def _migrate_stored_datetimes(self):
        """Walk through stored data and convert known datetime fields to UTC-aware ISO strings."""
        # For each chore, migrate due_date, last_completed, and last_claimed
        for chore in self._data.get(DATA_CHORES, {}).values():
            if chore.get("due_date"):
                chore["due_date"] = self._migrate_datetime(chore["due_date"])
            if chore.get("last_completed"):
                chore["last_completed"] = self._migrate_datetime(
                    chore["last_completed"]
                )
            if chore.get("last_claimed"):
                chore["last_claimed"] = self._migrate_datetime(chore["last_claimed"])
        # Also, migrate timestamps in pending approvals
        for approval in self._data.get(DATA_PENDING_CHORE_APPROVALS, []):
            if approval.get("timestamp"):
                approval["timestamp"] = self._migrate_datetime(approval["timestamp"])
        for approval in self._data.get(DATA_PENDING_REWARD_APPROVALS, []):
            if approval.get("timestamp"):
                approval["timestamp"] = self._migrate_datetime(approval["timestamp"])

        # Migrate datetime on Challenges
        for challenge in self._data.get(DATA_CHALLENGES, {}).values():
            start_date = challenge.get("start_date")
            if not isinstance(start_date, str) or not start_date.strip():
                challenge["start_date"] = None
            else:
                challenge["start_date"] = self._migrate_datetime(start_date)

            end_date = challenge.get("end_date")
            if not isinstance(end_date, str) or not end_date.strip():
                challenge["end_date"] = None
            else:
                challenge["end_date"] = self._migrate_datetime(end_date)

    def _migrate_chore_data(self):
        """Migrate each chore's data to include new fields if missing.

        This method iterates over each chore entry in the stored data and ensures
        that the following keys are present:
        - CONF_APPLICABLE_DAYS (defaults to DEFAULT_APPLICABLE_DAYS)
        - CONF_NOTIFY_ON_CLAIM (defaults to DEFAULT_NOTIFY_ON_CLAIM)
        - CONF_NOTIFY_ON_APPROVAL (defaults to DEFAULT_NOTIFY_ON_APPROVAL)
        - CONF_NOTIFY_ON_DISAPPROVAL (defaults to DEFAULT_NOTIFY_ON_DISAPPROVAL)
        """
        chores = self._data.get(DATA_CHORES, {})
        for chore in chores.values():
            chore.setdefault(CONF_APPLICABLE_DAYS, DEFAULT_APPLICABLE_DAYS)
            chore.setdefault(CONF_NOTIFY_ON_CLAIM, DEFAULT_NOTIFY_ON_CLAIM)
            chore.setdefault(CONF_NOTIFY_ON_APPROVAL, DEFAULT_NOTIFY_ON_APPROVAL)
            chore.setdefault(CONF_NOTIFY_ON_DISAPPROVAL, DEFAULT_NOTIFY_ON_DISAPPROVAL)
        LOGGER.info("Chore data migration complete.")

    # -------------------------------------------------------------------------------------
    # Normalize Lists
    # -------------------------------------------------------------------------------------

    def _normalize_kid_lists(self, kid_info: dict[str, Any]) -> None:
        "Normalize lists and ensuring they are not dict"
        for key in [
            "claimed_chores",
            "approved_chores",
            "pending_rewards",
            "redeemed_rewards",
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

        else:
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
                DATA_PENDING_CHORE_APPROVALS: [],
                DATA_PENDING_REWARD_APPROVALS: [],
            }

        if not isinstance(self._data.get(DATA_PENDING_CHORE_APPROVALS), list):
            self._data[DATA_PENDING_CHORE_APPROVALS] = []
        if not isinstance(self._data.get(DATA_PENDING_REWARD_APPROVALS), list):
            self._data[DATA_PENDING_REWARD_APPROVALS] = []

        # Register daily/weekly/monthly resets
        async_track_time_change(
            self.hass, self._reset_all_chore_counts, **DEFAULT_DAILY_RESET_TIME
        )

        # Merge config entry data (options) into the stored data
        self._initialize_data_from_config()

        # Normalize all kids list fields
        for kid in self._data.get(DATA_KIDS, {}).values():
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
            DATA_KIDS: options.get(CONF_KIDS, {}),
            DATA_PARENTS: options.get(CONF_PARENTS, {}),
            DATA_CHORES: options.get(CONF_CHORES, {}),
            DATA_BADGES: options.get(CONF_BADGES, {}),
            DATA_REWARDS: options.get(CONF_REWARDS, {}),
            DATA_PENALTIES: options.get(CONF_PENALTIES, {}),
            DATA_BONUSES: options.get(CONF_BONUSES, {}),
            DATA_ACHIEVEMENTS: options.get(CONF_ACHIEVEMENTS, {}),
            DATA_CHALLENGES: options.get(CONF_CHALLENGES, {}),
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
                LOGGER.warning("No initializer found for section '%s'", section_key)

        # Recalculate Badges on reload
        self._recalculate_all_badges()

    def _ensure_minimal_structure(self):
        """Ensure that all necessary data sections are present."""
        for key in [
            DATA_KIDS,
            DATA_PARENTS,
            DATA_CHORES,
            DATA_BADGES,
            DATA_REWARDS,
            DATA_PENALTIES,
            DATA_BONUSES,
            DATA_ACHIEVEMENTS,
            DATA_CHALLENGES,
        ]:
            self._data.setdefault(key, {})

        for key in [DATA_PENDING_CHORE_APPROVALS, DATA_PENDING_REWARD_APPROVALS]:
            if not isinstance(self._data.get(key), list):
                self._data[key] = []

    # -------------------------------------------------------------------------------------
    # Helpers to Sync Entities from config
    # -------------------------------------------------------------------------------------

    def _initialize_kids(self, kids_dict: dict[str, Any]):
        self._sync_entities(DATA_KIDS, kids_dict, self._create_kid, self._update_kid)

    def _initialize_parents(self, parents_dict: dict[str, Any]):
        self._sync_entities(
            DATA_PARENTS, parents_dict, self._create_parent, self._update_parent
        )

    def _initialize_chores(self, chores_dict: dict[str, Any]):
        self._sync_entities(
            DATA_CHORES, chores_dict, self._create_chore, self._update_chore
        )

    def _initialize_badges(self, badges_dict: dict[str, Any]):
        self._sync_entities(
            DATA_BADGES, badges_dict, self._create_badge, self._update_badge
        )

    def _initialize_rewards(self, rewards_dict: dict[str, Any]):
        self._sync_entities(
            DATA_REWARDS, rewards_dict, self._create_reward, self._update_reward
        )

    def _initialize_penalties(self, penalties_dict: dict[str, Any]):
        self._sync_entities(
            DATA_PENALTIES, penalties_dict, self._create_penalty, self._update_penalty
        )

    def _initialize_achievements(self, achievements_dict: dict[str, Any]):
        self._sync_entities(
            DATA_ACHIEVEMENTS,
            achievements_dict,
            self._create_achievement,
            self._update_achievement,
        )

    def _initialize_challenges(self, challenges_dict: dict[str, Any]):
        self._sync_entities(
            DATA_CHALLENGES,
            challenges_dict,
            self._create_challenge,
            self._update_challenge,
        )

    def _initialize_bonuses(self, bonuses_dict: dict[str, Any]):
        self._sync_entities(
            DATA_BONUSES, bonuses_dict, self._create_bonus, self._update_bonus
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
            if section == DATA_CHORES:
                for kid_id in self.kids_data.keys():
                    self._remove_kid_chore_entities(kid_id, entity_id)

            # Perform general clean-up
            self._cleanup_all_links()

            # Remove deleted kids from parents list
            self._cleanup_parent_assignments()

            # Remove chore approvals on chore delete
            self._cleanup_pending_chore_approvals()

            # Remove reward approvals on reward delete
            if section == DATA_REWARDS:
                self._cleanup_pending_reward_approvals()

        # Add or update entities
        for entity_id, entity_body in config_data.items():
            if entity_id not in self._data[section]:
                create_method(entity_id, entity_body)
            else:
                update_method(entity_id, entity_body)

        # Remove orphaned shared chore sensors.
        if section == DATA_CHORES:
            self.hass.async_create_task(self._remove_orphaned_shared_chore_sensors())

        # Remove orphaned achievement and challenges sensors
        self.hass.async_create_task(self._remove_orphaned_achievement_entities())
        self.hass.async_create_task(self._remove_orphaned_challenge_entities())

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
            if item_id in entity_entry.unique_id:
                ent_reg.async_remove(entity_entry.entity_id)
                LOGGER.debug(
                    "Auto-removed entity '%s' with unique_id '%s' from registry",
                    entity_entry.entity_id,
                    entity_entry.unique_id,
                )

    async def _remove_orphaned_shared_chore_sensors(self):
        """Remove SharedChoreGlobalStateSensor entities for chores no longer marked as shared."""
        ent_reg = er.async_get(self.hass)
        prefix = f"{self.config_entry.entry_id}_"
        suffix = "_global_state"
        for entity_entry in list(ent_reg.entities.values()):
            if (
                entity_entry.domain == "sensor"
                and entity_entry.unique_id.startswith(prefix)
                and entity_entry.unique_id.endswith(suffix)
            ):
                chore_id = entity_entry.unique_id[len(prefix) : -len(suffix)]
                chore_info = self.chores_data.get(chore_id)
                if not chore_info or not chore_info.get("shared_chore", False):
                    ent_reg.async_remove(entity_entry.entity_id)
                    LOGGER.debug(
                        "Removed orphaned SharedChoreGlobalStateSensor: %s",
                        entity_entry.entity_id,
                    )

    async def _remove_orphaned_achievement_entities(self) -> None:
        """Remove achievement progress entities for kids that are no longer assigned."""
        ent_reg = er.async_get(self.hass)
        prefix = f"{self.config_entry.entry_id}_"
        suffix = "_achievement_progress"
        for entity_entry in list(ent_reg.entities.values()):
            if (
                entity_entry.domain == "sensor"
                and entity_entry.unique_id.startswith(prefix)
                and entity_entry.unique_id.endswith(suffix)
            ):
                core_id = entity_entry.unique_id[len(prefix) : -len(suffix)]
                parts = core_id.split("_", 1)
                if len(parts) != 2:
                    continue

                kid_id, achievement_id = parts
                achievement = self._data.get(DATA_ACHIEVEMENTS, {}).get(achievement_id)
                if not achievement or kid_id not in achievement.get(
                    "assigned_kids", []
                ):
                    ent_reg.async_remove(entity_entry.entity_id)
                    LOGGER.debug(
                        "Removed orphaned achievement progress sensor '%s' because kid '%s' is not assigned to achievement '%s'",
                        entity_entry.entity_id,
                        kid_id,
                        achievement_id,
                    )

    async def _remove_orphaned_challenge_entities(self) -> None:
        """Remove challenge progress sensor entities for kids no longer assigned."""
        ent_reg = er.async_get(self.hass)
        prefix = f"{self.config_entry.entry_id}_"
        suffix = "_challenge_progress"
        for entity_entry in list(ent_reg.entities.values()):
            if (
                entity_entry.domain == "sensor"
                and entity_entry.unique_id.startswith(prefix)
                and entity_entry.unique_id.endswith(suffix)
            ):
                core_id = entity_entry.unique_id[len(prefix) : -len(suffix)]
                parts = core_id.split("_", 1)
                if len(parts) != 2:
                    continue

                kid_id, challenge_id = parts
                challenge = self._data.get(DATA_CHALLENGES, {}).get(challenge_id)
                if not challenge or kid_id not in challenge.get("assigned_kids", []):
                    ent_reg.async_remove(entity_entry.entity_id)
                    LOGGER.debug(
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
                LOGGER.debug(
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
        for key in ["claimed_chores", "approved_chores"]:
            if chore_id in kid.get(key, []):
                kid[key] = [c for c in kid[key] if c != chore_id]
                LOGGER.debug(
                    "Removed chore '%s' from kid '%s' list '%s'", chore_id, kid_id, key
                )

        # Remove from dictionary fields if present
        for dict_key in ["chore_claims", "chore_approvals"]:
            if chore_id in kid.get(dict_key, {}):
                kid[dict_key].pop(chore_id)
                LOGGER.debug(
                    "Removed chore '%s' from kid '%s' dict '%s'",
                    chore_id,
                    kid_id,
                    dict_key,
                )

        # Remove from chore streaks if present
        if "chore_streaks" in kid and chore_id in kid["chore_streaks"]:
            kid["chore_streaks"].pop(chore_id)
            LOGGER.debug(
                "Removed chore streak for chore '%s' from kid '%s'", chore_id, kid_id
            )

        # Remove any pending chore approvals for this kid and chore
        self._data[DATA_PENDING_CHORE_APPROVALS] = [
            ap
            for ap in self._data.get(DATA_PENDING_CHORE_APPROVALS, [])
            if not (ap.get("kid_id") == kid_id and ap.get("chore_id") == chore_id)
        ]

    def _cleanup_pending_chore_approvals(self) -> None:
        """Remove any pending chore approvals for chore IDs that no longer exist."""
        valid_chore_ids = set(self._data.get(DATA_CHORES, {}).keys())
        self._data[DATA_PENDING_CHORE_APPROVALS] = [
            ap
            for ap in self._data.get(DATA_PENDING_CHORE_APPROVALS, [])
            if ap.get("chore_id") in valid_chore_ids
        ]

    def _cleanup_pending_reward_approvals(self) -> None:
        """Remove any pending reward approvals for reward IDs that no longer exist."""
        valid_reward_ids = set(self._data.get(DATA_REWARDS, {}).keys())
        self._data[DATA_PENDING_REWARD_APPROVALS] = [
            approval
            for approval in self._data.get(DATA_PENDING_REWARD_APPROVALS, [])
            if approval.get("reward_id") in valid_reward_ids
        ]

    def _cleanup_deleted_kid_references(self) -> None:
        """Remove references to kids that no longer exist from other sections."""
        valid_kid_ids = set(self.kids_data.keys())

        # Remove deleted kid IDs from all chore assignments
        for chore in self._data.get(DATA_CHORES, {}).values():
            if "assigned_kids" in chore:
                original = chore["assigned_kids"]
                filtered = [kid for kid in original if kid in valid_kid_ids]
                if filtered != original:
                    chore["assigned_kids"] = filtered
                    LOGGER.debug(
                        "Cleaned up assigned_kids in chore '%s'", chore.get("name")
                    )

        # Remove progress in achievements and challenges
        for section in [DATA_ACHIEVEMENTS, DATA_CHALLENGES]:
            for entity in self._data.get(section, {}).values():
                progress = entity.get("progress", {})
                keys_to_remove = [kid for kid in progress if kid not in valid_kid_ids]
                for kid in keys_to_remove:
                    del progress[kid]
                    LOGGER.debug(
                        "Removed progress for deleted kid '%s' in section '%s'",
                        kid,
                        section,
                    )
                if "assigned_kids" in entity:
                    original_assigned = entity["assigned_kids"]
                    filtered_assigned = [
                        kid for kid in original_assigned if kid in valid_kid_ids
                    ]
                    if filtered_assigned != original_assigned:
                        entity["assigned_kids"] = filtered_assigned
                        LOGGER.debug(
                            "Cleaned up assigned_kids in %s '%s'",
                            section,
                            entity.get("name"),
                        )

    def _cleanup_deleted_chore_references(self) -> None:
        """Remove references to chores that no longer exist from kid data."""
        valid_chore_ids = set(self.chores_data.keys())
        for kid in self.kids_data.values():
            # Clean up list fields
            for key in ["claimed_chores", "approved_chores"]:
                if key in kid:
                    original = kid[key]
                    filtered = [chore for chore in original if chore in valid_chore_ids]
                    if filtered != original:
                        kid[key] = filtered

            # Clean up dictionary fields
            for dict_key in ["chore_claims", "chore_approvals"]:
                if dict_key in kid:
                    kid[dict_key] = {
                        chore: count
                        for chore, count in kid[dict_key].items()
                        if chore in valid_chore_ids
                    }

            # Clean up chore streaks
            if "chore_streaks" in kid:
                for chore in list(kid["chore_streaks"].keys()):
                    if chore not in valid_chore_ids:
                        del kid["chore_streaks"][chore]
                        LOGGER.debug(
                            "Removed chore streak for deleted chore '%s'", chore
                        )

    def _cleanup_parent_assignments(self) -> None:
        """Remove any kid IDs from parent's 'associated_kids' that no longer exist."""
        valid_kid_ids = set(self.kids_data.keys())
        for parent in self._data.get(DATA_PARENTS, {}).values():
            original = parent.get("associated_kids", [])
            filtered = [kid_id for kid_id in original if kid_id in valid_kid_ids]
            if filtered != original:
                parent["associated_kids"] = filtered
                LOGGER.debug(
                    "Cleaned up associated_kids for parent '%s'. New list: %s",
                    parent.get("name"),
                    filtered,
                )

    def _cleanup_deleted_chore_in_achievements(self) -> None:
        """Clear selected_chore_id in achievements if the chore no longer exists."""
        valid_chore_ids = set(self.chores_data.keys())
        for achievement in self._data.get(DATA_ACHIEVEMENTS, {}).values():
            selected = achievement.get("selected_chore_id")
            if selected and selected not in valid_chore_ids:
                achievement["selected_chore_id"] = ""
                LOGGER.debug(
                    "Cleared selected_chore_id in achievement '%s'",
                    achievement.get("name"),
                )

    def _cleanup_deleted_chore_in_challenges(self) -> None:
        """Clear selected_chore_id in challenges if the chore no longer exists."""
        valid_chore_ids = set(self.chores_data.keys())
        for challenge in self._data.get(DATA_CHALLENGES, {}).values():
            selected = challenge.get("selected_chore_id")
            if selected and selected not in valid_chore_ids:
                challenge["selected_chore_id"] = ""
                LOGGER.debug(
                    "Cleared selected_chore_id in challenge '%s'", challenge.get("name")
                )

    # -------------------------------------------------------------------------------------
    # Create/Update Entities
    # (Kids, Parents, Chores, Badges, Rewards, Penalties, Achievements and Challenges)
    # -------------------------------------------------------------------------------------

    # -- Kids
    def _create_kid(self, kid_id: str, kid_data: dict[str, Any]):
        self._data[DATA_KIDS][kid_id] = {
            "name": kid_data.get("name", ""),
            "points": kid_data.get("points", 0.0),
            "badges": kid_data.get("badges", []),
            "claimed_chores": kid_data.get("claimed_chores", []),
            "approved_chores": kid_data.get("approved_chores", []),
            "completed_chores_today": kid_data.get("completed_chores_today", 0),
            "completed_chores_weekly": kid_data.get("completed_chores_weekly", 0),
            "completed_chores_monthly": kid_data.get("completed_chores_monthly", 0),
            "completed_chores_total": kid_data.get("completed_chores_total", 0),
            "ha_user_id": kid_data.get("ha_user_id"),
            "internal_id": kid_id,
            "points_multiplier": kid_data.get("points_multiplier", 1.0),
            "reward_claims": kid_data.get("reward_claims", {}),
            "reward_approvals": kid_data.get("reward_approvals", {}),
            "chore_claims": kid_data.get("chore_claims", {}),
            "chore_approvals": kid_data.get("chore_approvals", {}),
            "penalty_applies": kid_data.get("penalty_applies", {}),
            "bonus_applies": kid_data.get("bonus_applies", {}),
            "pending_rewards": kid_data.get("pending_rewards", []),
            "redeemed_rewards": kid_data.get("redeemed_rewards", []),
            "points_earned_today": kid_data.get("points_earned_today", 0.0),
            "points_earned_weekly": kid_data.get("points_earned_weekly", 0.0),
            "points_earned_monthly": kid_data.get("points_earned_monthly", 0.0),
            "max_points_ever": kid_data.get("max_points_ever", 0.0),
            "enable_notifications": kid_data.get("enable_notifications", True),
            "mobile_notify_service": kid_data.get("mobile_notify_service", ""),
            "use_persistent_notifications": kid_data.get(
                "use_persistent_notifications", True
            ),
            "chore_streaks": {},
            "overall_chore_streak": 0,
            "last_chore_date": None,
            "overdue_chores": [],
            "overdue_notifications": {},
        }

        self._normalize_kid_lists(self._data[DATA_KIDS][kid_id])

        LOGGER.debug(
            "Added new kid '%s' with ID: %s",
            self._data[DATA_KIDS][kid_id]["name"],
            kid_id,
        )

    def _update_kid(self, kid_id: str, kid_data: dict[str, Any]):
        kid_info = self._data[DATA_KIDS][kid_id]
        # Overwrite or set default if not present
        kid_info["name"] = kid_data.get("name", kid_info["name"])
        kid_info["ha_user_id"] = kid_data.get("ha_user_id", kid_info["ha_user_id"])
        kid_info.setdefault("reward_claims", kid_data.get("reward_claims", {}))
        kid_info.setdefault("reward_approvals", kid_data.get("reward_approvals", {}))
        kid_info.setdefault("chore_claims", kid_data.get("chore_claims", {}))
        kid_info.setdefault("chore_approvals", kid_data.get("chore_approvals", {}))
        kid_info.setdefault("penalty_applies", kid_data.get("penalty_applies", {}))
        kid_info.setdefault("bonus_applies", kid_data.get("bonus_applies", {}))
        kid_info.setdefault("pending_rewards", kid_data.get("pending_rewards", []))
        kid_info.setdefault("redeemed_rewards", kid_data.get("redeemed_rewards", []))
        kid_info.setdefault(
            "points_earned_today", kid_data.get("points_earned_today", 0.0)
        )
        kid_info.setdefault(
            "points_earned_weekly", kid_data.get("points_earned_weekly", 0.0)
        )
        kid_info.setdefault(
            "points_earned_monthly", kid_data.get("points_earned_monthly", 0.0)
        )
        kid_info.setdefault("max_points_ever", kid_data.get("max_points_ever", 0.0))
        kid_info.setdefault("points_multiplier", kid_data.get("points_multiplier", 1.0))
        kid_info["enable_notifications"] = kid_data.get(
            "enable_notifications", kid_info.get("enable_notifications", True)
        )
        kid_info["mobile_notify_service"] = kid_data.get(
            "mobile_notify_service", kid_info.get("mobile_notify_service", "")
        )
        kid_info["use_persistent_notifications"] = kid_data.get(
            "use_persistent_notifications",
            kid_info.get("use_persistent_notifications", True),
        )
        kid_info.setdefault("chore_streaks", {})
        kid_info.setdefault("overall_chore_streak", 0)
        kid_info.setdefault("last_chore_date", None)
        kid_info.setdefault("overdue_chores", [])
        kid_info.setdefault("overdue_notifications", {})

        self._normalize_kid_lists(self._data[DATA_KIDS][kid_id])

        LOGGER.debug("Updated kid '%s' with ID: %s", kid_info["name"], kid_id)

    # -- Parents
    def _create_parent(self, parent_id: str, parent_data: dict[str, Any]):
        associated_kids_ids = []
        for kid_id in parent_data.get("associated_kids", []):
            if kid_id in self.kids_data:
                associated_kids_ids.append(kid_id)
            else:
                LOGGER.warning(
                    "Parent '%s': Kid ID '%s' not found. Skipping assignment to parent",
                    parent_data.get("name", parent_id),
                    kid_id,
                )

        self._data[DATA_PARENTS][parent_id] = {
            "name": parent_data.get("name", ""),
            "ha_user_id": parent_data.get("ha_user_id", ""),
            "associated_kids": associated_kids_ids,
            "enable_notifications": parent_data.get("enable_notifications", True),
            "mobile_notify_service": parent_data.get("mobile_notify_service", ""),
            "use_persistent_notifications": parent_data.get(
                "use_persistent_notifications", True
            ),
            "internal_id": parent_id,
        }
        LOGGER.debug(
            "Added new parent '%s' with ID: %s",
            self._data[DATA_PARENTS][parent_id]["name"],
            parent_id,
        )

    def _update_parent(self, parent_id: str, parent_data: dict[str, Any]):
        parent_info = self._data[DATA_PARENTS][parent_id]
        parent_info["name"] = parent_data.get("name", parent_info["name"])
        parent_info["ha_user_id"] = parent_data.get(
            "ha_user_id", parent_info["ha_user_id"]
        )

        # Update associated_kids
        updated_kids = []
        for kid_id in parent_data.get("associated_kids", []):
            if kid_id in self.kids_data:
                updated_kids.append(kid_id)
            else:
                LOGGER.warning(
                    "Parent '%s': Kid ID '%s' not found. Skipping assignment",
                    parent_info["name"],
                    kid_id,
                )
        parent_info["associated_kids"] = updated_kids
        parent_info["enable_notifications"] = parent_data.get(
            "enable_notifications", parent_info.get("enable_notifications", True)
        )
        parent_info["mobile_notify_service"] = parent_data.get(
            "mobile_notify_service", parent_info.get("mobile_notify_service", "")
        )
        parent_info["use_persistent_notifications"] = parent_data.get(
            "use_persistent_notifications",
            parent_info.get("use_persistent_notifications", True),
        )

        LOGGER.debug("Updated parent '%s' with ID: %s", parent_info["name"], parent_id)

    # -- Chores
    def _create_chore(self, chore_id: str, chore_data: dict[str, Any]):
        assigned_kids_ids = []
        for kid_name in chore_data.get("assigned_kids", []):
            kid_id = self._get_kid_id_by_name(kid_name)
            if kid_id:
                assigned_kids_ids.append(kid_id)
            else:
                LOGGER.warning(
                    "Chore '%s': Kid name '%s' not found. Skipping assignment",
                    chore_data.get("name", chore_id),
                    kid_name,
                )

        # If chore is recurring, set due_date to creation date if not set
        freq = chore_data.get("recurring_frequency", FREQUENCY_NONE)
        if freq != FREQUENCY_NONE and not chore_data.get("due_date"):
            now_local = dt_util.utcnow()
            # Force the time to 23:59:00 (and zero microseconds)
            default_due = now_local.replace(hour=23, minute=59, second=0, microsecond=0)
            chore_data["due_date"] = default_due.isoformat()
            LOGGER.debug(
                "Chore '%s' has freq '%s' but no due_date. Defaulting to 23:59 local time: %s",
                chore_data.get("name", chore_id),
                freq,
                chore_data["due_date"],
            )

        self._data[DATA_CHORES][chore_id] = {
            "name": chore_data.get("name", ""),
            "state": chore_data.get("state", CHORE_STATE_PENDING),
            "default_points": chore_data.get("default_points", DEFAULT_POINTS),
            "allow_multiple_claims_per_day": chore_data.get(
                "allow_multiple_claims_per_day", DEFAULT_MULTIPLE_CLAIMS_PER_DAY
            ),
            "partial_allowed": chore_data.get(
                "partial_allowed", DEFAULT_PARTIAL_ALLOWED
            ),
            "description": chore_data.get("description", ""),
            "chore_labels": chore_data.get("chore_labels", []),
            "icon": chore_data.get("icon", DEFAULT_ICON),
            "shared_chore": chore_data.get("shared_chore", False),
            "assigned_kids": assigned_kids_ids,
            "recurring_frequency": chore_data.get(
                "recurring_frequency", FREQUENCY_NONE
            ),
            "custom_interval": chore_data.get("custom_interval")
            if chore_data.get("recurring_frequency") == FREQUENCY_CUSTOM
            else None,
            "custom_interval_unit": chore_data.get("custom_interval_unit")
            if chore_data.get("recurring_frequency") == FREQUENCY_CUSTOM
            else None,
            "due_date": chore_data.get("due_date"),
            "last_completed": chore_data.get("last_completed"),
            "last_claimed": chore_data.get("last_claimed"),
            "applicable_days": chore_data.get("applicable_days", []),
            "notify_on_claim": chore_data.get(
                "notify_on_claim", DEFAULT_NOTIFY_ON_CLAIM
            ),
            "notify_on_approval": chore_data.get(
                "notify_on_approval", DEFAULT_NOTIFY_ON_APPROVAL
            ),
            "notify_on_disapproval": chore_data.get(
                "notify_on_disapproval", DEFAULT_NOTIFY_ON_DISAPPROVAL
            ),
            "internal_id": chore_id,
        }
        LOGGER.debug(
            "Added new chore '%s' with ID: %s",
            self._data[DATA_CHORES][chore_id]["name"],
            chore_id,
        )

        # Notify Kids of new chore
        new_name = self._data[DATA_CHORES][chore_id]["name"]
        due_date = self._data[DATA_CHORES][chore_id]["due_date"]
        for kid_id in assigned_kids_ids:
            due_str = due_date if due_date else "No due date set"
            extra_data = {"kid_id": kid_id, "chore_id": chore_id}
            self.hass.async_create_task(
                self._notify_kid(
                    kid_id,
                    title="KidsChores: New Chore",
                    message=f"A new chore '{new_name}' was assigned to you! Due: {due_str}",
                    extra_data=extra_data,
                )
            )

    def _update_chore(self, chore_id: str, chore_data: dict[str, Any]):
        chore_info = self._data[DATA_CHORES][chore_id]
        chore_info["name"] = chore_data.get("name", chore_info["name"])
        chore_info["state"] = chore_data.get("state", chore_info["state"])
        chore_info["default_points"] = chore_data.get(
            "default_points", chore_info["default_points"]
        )
        chore_info["allow_multiple_claims_per_day"] = chore_data.get(
            "allow_multiple_claims_per_day", chore_info["allow_multiple_claims_per_day"]
        )
        chore_info["partial_allowed"] = chore_data.get(
            "partial_allowed", chore_info["partial_allowed"]
        )
        chore_info["description"] = chore_data.get(
            "description", chore_info["description"]
        )
        chore_info["chore_labels"] = chore_data.get(
            "chore_labels", chore_info.get("chore_labels", [])
        )
        chore_info["icon"] = chore_data.get("icon", chore_info["icon"])
        chore_info["shared_chore"] = chore_data.get(
            "shared_chore", chore_info["shared_chore"]
        )

        assigned_kids_ids = []
        for kid_name in chore_data.get("assigned_kids", []):
            kid_id = self._get_kid_id_by_name(kid_name)
            if kid_id:
                assigned_kids_ids.append(kid_id)
            else:
                LOGGER.warning(
                    "Chore '%s': Kid name '%s' not found. Skipping assignment",
                    chore_data.get("name", chore_id),
                    kid_name,
                )
        old_assigned = set(chore_info.get("assigned_kids", []))
        new_assigned = set(assigned_kids_ids)
        removed_kids = old_assigned - new_assigned
        for kid in removed_kids:
            self._remove_kid_chore_entities(kid, chore_id)
            self._cleanup_chore_from_kid(kid, chore_id)

        # Update the chore's assigned kids list with the new assignments
        chore_info["assigned_kids"] = list(new_assigned)

        chore_info["recurring_frequency"] = chore_data.get(
            "recurring_frequency", chore_info["recurring_frequency"]
        )
        chore_info["due_date"] = chore_data.get("due_date", chore_info["due_date"])
        chore_info["last_completed"] = chore_data.get(
            "last_completed", chore_info.get("last_completed")
        )
        chore_info["last_claimed"] = chore_data.get(
            "last_claimed", chore_info.get("last_claimed")
        )
        chore_info["applicable_days"] = chore_data.get(
            "applicable_days", chore_info.get("applicable_days", [])
        )
        chore_info["notify_on_claim"] = chore_data.get(
            "notify_on_claim",
            chore_info.get("notify_on_claim", DEFAULT_NOTIFY_ON_CLAIM),
        )
        chore_info["notify_on_approval"] = chore_data.get(
            "notify_on_approval",
            chore_info.get("notify_on_approval", DEFAULT_NOTIFY_ON_APPROVAL),
        )
        chore_info["notify_on_disapproval"] = chore_data.get(
            "notify_on_disapproval",
            chore_info.get("notify_on_disapproval", DEFAULT_NOTIFY_ON_DISAPPROVAL),
        )
        if chore_info["recurring_frequency"] == FREQUENCY_CUSTOM:
            chore_info["custom_interval"] = chore_data.get("custom_interval")
            chore_info["custom_interval_unit"] = chore_data.get("custom_interval_unit")
        else:
            chore_info["custom_interval"] = None
            chore_info["custom_interval_unit"] = None

        LOGGER.debug("Updated chore '%s' with ID: %s", chore_info["name"], chore_id)

        self.hass.async_create_task(self._check_overdue_chores())

    # -- Badges
    def _create_badge(self, badge_id: str, badge_data: dict[str, Any]):
        self._data[DATA_BADGES][badge_id] = {
            "name": badge_data.get("name", ""),
            "threshold_type": badge_data.get(
                "threshold_type", BADGE_THRESHOLD_TYPE_POINTS
            ),
            "threshold_value": badge_data.get(
                "threshold_value", DEFAULT_BADGE_THRESHOLD
            ),
            "chore_count_type": badge_data.get("chore_count_type", FREQUENCY_DAILY),
            "earned_by": badge_data.get("earned_by", []),
            "points_multiplier": badge_data.get(
                "points_multiplier", DEFAULT_POINTS_MULTIPLIER
            ),
            "icon": badge_data.get("icon", DEFAULT_ICON),
            "description": badge_data.get("description", ""),
            "badge_labels": badge_data.get("badge_labels", []),
            "internal_id": badge_id,
        }
        LOGGER.debug(
            "Added new badge '%s' with ID: %s",
            self._data[DATA_BADGES][badge_id]["name"],
            badge_id,
        )

    def _update_badge(self, badge_id: str, badge_data: dict[str, Any]):
        badge_info = self._data[DATA_BADGES][badge_id]
        badge_info["name"] = badge_data.get("name", badge_info["name"])
        badge_info["threshold_type"] = badge_data.get(
            "threshold_type",
            badge_info.get("threshold_type", BADGE_THRESHOLD_TYPE_POINTS),
        )
        badge_info["threshold_value"] = badge_data.get(
            "threshold_value",
            badge_info.get("threshold_value", DEFAULT_BADGE_THRESHOLD),
        )
        badge_info["chore_count_type"] = badge_data.get(
            "chore_count_type", badge_info.get("chore_count_type", FREQUENCY_NONE)
        )
        badge_info["points_multiplier"] = badge_data.get(
            "points_multiplier",
            badge_info.get("points_multiplier", DEFAULT_POINTS_MULTIPLIER),
        )
        badge_info["icon"] = badge_data.get(
            "icon", badge_info.get("icon", DEFAULT_ICON)
        )
        badge_info["description"] = badge_data.get(
            "description", badge_info.get("description", "")
        )
        badge_info["badge_labels"] = badge_data.get(
            "badge_labels", badge_info.get("badge_labels", [])
        )

        LOGGER.debug("Updated badge '%s' with ID: %s", badge_info["name"], badge_id)

    # -- Rewards
    def _create_reward(self, reward_id: str, reward_data: dict[str, Any]):
        self._data[DATA_REWARDS][reward_id] = {
            "name": reward_data.get("name", ""),
            "cost": reward_data.get("cost", DEFAULT_REWARD_COST),
            "description": reward_data.get("description", ""),
            "reward_labels": reward_data.get("reward_labels", []),
            "icon": reward_data.get("icon", DEFAULT_REWARD_ICON),
            "internal_id": reward_id,
        }
        LOGGER.debug(
            "Added new reward '%s' with ID: %s",
            self._data[DATA_REWARDS][reward_id]["name"],
            reward_id,
        )

    def _update_reward(self, reward_id: str, reward_data: dict[str, Any]):
        reward_info = self._data[DATA_REWARDS][reward_id]
        reward_info["name"] = reward_data.get("name", reward_info["name"])
        reward_info["cost"] = reward_data.get("cost", reward_info["cost"])
        reward_info["description"] = reward_data.get(
            "description", reward_info["description"]
        )
        reward_info["reward_labels"] = reward_data.get(
            "reward_labels", reward_info.get("reward_labels", [])
        )
        reward_info["icon"] = reward_data.get("icon", reward_info["icon"])
        LOGGER.debug("Updated reward '%s' with ID: %s", reward_info["name"], reward_id)

    # -- Penalties
    def _create_penalty(self, penalty_id: str, penalty_data: dict[str, Any]):
        self._data[DATA_PENALTIES][penalty_id] = {
            "name": penalty_data.get("name", ""),
            "points": penalty_data.get("points", -DEFAULT_PENALTY_POINTS),
            "description": penalty_data.get("description", ""),
            "penalty_labels": penalty_data.get("penalty_labels", []),
            "icon": penalty_data.get("icon", DEFAULT_PENALTY_ICON),
            "internal_id": penalty_id,
        }
        LOGGER.debug(
            "Added new penalty '%s' with ID: %s",
            self._data[DATA_PENALTIES][penalty_id]["name"],
            penalty_id,
        )

    def _update_penalty(self, penalty_id: str, penalty_data: dict[str, Any]):
        penalty_info = self._data[DATA_PENALTIES][penalty_id]
        penalty_info["name"] = penalty_data.get("name", penalty_info["name"])
        penalty_info["points"] = penalty_data.get("points", penalty_info["points"])
        penalty_info["description"] = penalty_data.get(
            "description", penalty_info["description"]
        )
        penalty_info["penalty_labels"] = penalty_data.get(
            "penalty_labels", penalty_info.get("penalty_labels", [])
        )
        penalty_info["icon"] = penalty_data.get("icon", penalty_info["icon"])
        LOGGER.debug(
            "Updated penalty '%s' with ID: %s", penalty_info["name"], penalty_id
        )

    # -- Bonuses
    def _create_bonus(self, bonus_id: str, bonus_data: dict[str, Any]):
        self._data[DATA_BONUSES][bonus_id] = {
            "name": bonus_data.get("name", ""),
            "points": bonus_data.get("points", DEFAULT_BONUS_POINTS),
            "description": bonus_data.get("description", ""),
            "bonus_labels": bonus_data.get("bonus_labels", []),
            "icon": bonus_data.get("icon", DEFAULT_BONUS_ICON),
            "internal_id": bonus_id,
        }
        LOGGER.debug(
            "Added new bonus '%s' with ID: %s",
            self._data[DATA_BONUSES][bonus_id]["name"],
            bonus_id,
        )

    def _update_bonus(self, bonus_id: str, bonus_data: dict[str, Any]):
        bonus_info = self._data[DATA_BONUSES][bonus_id]
        bonus_info["name"] = bonus_data.get("name", bonus_info["name"])
        bonus_info["points"] = bonus_data.get("points", bonus_info["points"])
        bonus_info["description"] = bonus_data.get(
            "description", bonus_info["description"]
        )
        bonus_info["bonus_labels"] = bonus_data.get(
            "bonus_labels", bonus_info.get("bonus_labels", [])
        )
        bonus_info["icon"] = bonus_data.get("icon", bonus_info["icon"])
        LOGGER.debug("Updated bonus '%s' with ID: %s", bonus_info["name"], bonus_id)

    # -- Achievements
    def _create_achievement(
        self, achievement_id: str, achievement_data: dict[str, Any]
    ):
        self._data[DATA_ACHIEVEMENTS][achievement_id] = {
            "name": achievement_data.get("name", ""),
            "description": achievement_data.get("description", ""),
            "achievement_labels": achievement_data.get("achievement_labels", []),
            "icon": achievement_data.get("icon", ""),
            "assigned_kids": achievement_data.get("assigned_kids", []),
            "type": achievement_data.get("type", "individual"),
            "selected_chore_id": achievement_data.get("selected_chore_id", ""),
            "criteria": achievement_data.get("criteria", ""),
            "target_value": achievement_data.get("target_value", 1),
            "reward_points": achievement_data.get("reward_points", 0),
            "progress": achievement_data.get("progress", {}),
            "internal_id": achievement_id,
        }
        LOGGER.debug(
            "Added new achievement '%s' with ID: %s",
            self._data[DATA_ACHIEVEMENTS][achievement_id]["name"],
            achievement_id,
        )

    def _update_achievement(
        self, achievement_id: str, achievement_data: dict[str, Any]
    ):
        achievement_info = self._data[DATA_ACHIEVEMENTS][achievement_id]
        achievement_info["name"] = achievement_data.get(
            "name", achievement_info["name"]
        )
        achievement_info["description"] = achievement_data.get(
            "description", achievement_info["description"]
        )
        achievement_info["achievement_labels"] = achievement_data.get(
            "achievement_labels", achievement_info.get("achievement_labels", [])
        )
        achievement_info["icon"] = achievement_data.get(
            "icon", achievement_info["icon"]
        )
        achievement_info["assigned_kids"] = achievement_data.get(
            "assigned_kids", achievement_info["assigned_kids"]
        )
        achievement_info["type"] = achievement_data.get(
            "type", achievement_info["type"]
        )
        achievement_info["selected_chore_id"] = achievement_data.get(
            "selected_chore_id", achievement_info.get("selected_chore_id", "")
        )
        achievement_info["criteria"] = achievement_data.get(
            "criteria", achievement_info["criteria"]
        )
        achievement_info["target_value"] = achievement_data.get(
            "target_value", achievement_info["target_value"]
        )
        achievement_info["reward_points"] = achievement_data.get(
            "reward_points", achievement_info["reward_points"]
        )

        LOGGER.debug(
            "Updated achievement '%s' with ID: %s",
            achievement_info["name"],
            achievement_id,
        )

    # -- Challenges
    def _create_challenge(self, challenge_id: str, challenge_data: dict[str, Any]):
        self._data[DATA_CHALLENGES][challenge_id] = {
            "name": challenge_data.get("name", ""),
            "description": challenge_data.get("description", ""),
            "challenge_labels": challenge_data.get("challenge_labels", []),
            "icon": challenge_data.get("icon", ""),
            "assigned_kids": challenge_data.get("assigned_kids", []),
            "type": challenge_data.get("type", "individual"),
            "selected_chore_id": challenge_data.get("selected_chore_id", ""),
            "criteria": challenge_data.get("criteria", ""),
            "target_value": challenge_data.get("target_value", 1),
            "reward_points": challenge_data.get("reward_points", 0),
            "start_date": challenge_data.get("start_date")
            if challenge_data.get("start_date") not in [None, {}]
            else None,
            "end_date": challenge_data.get("end_date")
            if challenge_data.get("end_date") not in [None, {}]
            else None,
            "progress": challenge_data.get("progress", {}),
            "internal_id": challenge_id,
        }
        LOGGER.debug(
            "Added new challenge '%s' with ID: %s",
            self._data[DATA_CHALLENGES][challenge_id]["name"],
            challenge_id,
        )

    def _update_challenge(self, challenge_id: str, challenge_data: dict[str, Any]):
        challenge_info = self._data[DATA_CHALLENGES][challenge_id]
        challenge_info["name"] = challenge_data.get("name", challenge_info["name"])
        challenge_info["description"] = challenge_data.get(
            "description", challenge_info["description"]
        )
        challenge_info["challenge_labels"] = challenge_data.get(
            "challenge_labels", challenge_info.get("challenge_labels", [])
        )
        challenge_info["icon"] = challenge_data.get("icon", challenge_info["icon"])
        challenge_info["assigned_kids"] = challenge_data.get(
            "assigned_kids", challenge_info["assigned_kids"]
        )
        challenge_info["type"] = challenge_data.get("type", challenge_info["type"])
        challenge_info["selected_chore_id"] = challenge_data.get(
            "selected_chore_id", challenge_info.get("selected_chore_id", "")
        )
        challenge_info["criteria"] = challenge_data.get(
            "criteria", challenge_info["criteria"]
        )
        challenge_info["target_value"] = challenge_data.get(
            "target_value", challenge_info["target_value"]
        )
        challenge_info["reward_points"] = challenge_data.get(
            "reward_points", challenge_info["reward_points"]
        )
        challenge_info["start_date"] = (
            challenge_data.get("start_date")
            if challenge_data.get("start_date") not in [None, {}]
            else None
        )
        challenge_info["end_date"] = (
            challenge_data.get("end_date")
            if challenge_data.get("end_date") not in [None, {}]
            else None
        )
        LOGGER.debug(
            "Updated challenge '%s' with ID: %s", challenge_info["name"], challenge_id
        )

    # -------------------------------------------------------------------------------------
    # Properties for Easy Access
    # -------------------------------------------------------------------------------------

    @property
    def kids_data(self) -> dict[str, Any]:
        """Return the kids data."""
        return self._data.get(DATA_KIDS, {})

    @property
    def parents_data(self) -> dict[str, Any]:
        """Return the parents data."""
        return self._data.get(DATA_PARENTS, {})

    @property
    def chores_data(self) -> dict[str, Any]:
        """Return the chores data."""
        return self._data.get(DATA_CHORES, {})

    @property
    def badges_data(self) -> dict[str, Any]:
        """Return the badges data."""
        return self._data.get(DATA_BADGES, {})

    @property
    def rewards_data(self) -> dict[str, Any]:
        """Return the rewards data."""
        return self._data.get(DATA_REWARDS, {})

    @property
    def penalties_data(self) -> dict[str, Any]:
        """Return the penalties data."""
        return self._data.get(DATA_PENALTIES, {})

    @property
    def achievements_data(self) -> dict[str, Any]:
        """Return the achievements data."""
        return self._data.get(DATA_ACHIEVEMENTS, {})  # New

    @property
    def challenges_data(self) -> dict[str, Any]:
        """Return the challenges data."""
        return self._data.get(DATA_CHALLENGES, {})

    @property
    def bonuses_data(self) -> dict[str, Any]:
        """Return the bonuses data."""
        return self._data.get(DATA_BONUSES, {})

    # -------------------------------------------------------------------------------------
    # Parents: Add, Remove
    # -------------------------------------------------------------------------------------

    def add_parent(self, parent_def: dict[str, Any]):
        """Add new parent at runtime if needed."""
        parent_name = parent_def.get("name")
        ha_user_id = parent_def.get("ha_user_id")
        kid_ids = parent_def.get("associated_kids", [])

        if not parent_name or not ha_user_id:
            LOGGER.warning("Add parent: Parent must have a name and ha_user_id")
            return

        if any(p["ha_user_id"] == ha_user_id for p in self.parents_data.values()):
            LOGGER.warning(
                "Add parent: Parent with ha_user_id '%s' already exists", ha_user_id
            )
            return

        valid_kids = []
        for kid_id in kid_ids:
            if kid_id in self.kids_data:
                valid_kids.append(kid_id)
            else:
                LOGGER.warning(
                    "Add parent: Kid ID '%s' not found. Skipping assignment to parent '%s'",
                    kid_id,
                    parent_name,
                )

        new_id = str(uuid.uuid4())
        self.parents_data[new_id] = {
            "name": parent_name,
            "ha_user_id": ha_user_id,
            "associated_kids": valid_kids,
            "internal_id": new_id,
        }
        LOGGER.debug("Added new parent '%s' with ID: %s", parent_name, new_id)
        self._persist()
        self.async_set_updated_data(self._data)

    def remove_parent(self, parent_id: str):
        """Remove a parent by ID."""
        if parent_id in self.parents_data:
            parent_name = self.parents_data[parent_id]["name"]
            del self.parents_data[parent_id]
            LOGGER.debug("Removed parent '%s' with ID: %s", parent_name, parent_id)
            self._persist()
            self.async_set_updated_data(self._data)
        else:
            LOGGER.warning("Remove parent: Parent ID '%s' not found", parent_id)

    # -------------------------------------------------------------------------------------
    # Chores: Claim, Approve, Disapprove, Compute Glonal State for Shared Chores
    # -------------------------------------------------------------------------------------

    def claim_chore(self, kid_id: str, chore_id: str, user_name: str):
        """Kid claims chore => state=claimed; parent must then approve."""
        if chore_id not in self.chores_data:
            LOGGER.warning("Chore ID '%s' not found for claim", chore_id)
            raise HomeAssistantError(f"Chore with ID '{chore_id}' not found.")

        chore_info = self.chores_data[chore_id]
        if kid_id not in chore_info.get("assigned_kids", []):
            LOGGER.warning(
                "Claim chore: Chore ID '%s' not assigned to kid ID '%s'",
                chore_id,
                kid_id,
            )
            raise HomeAssistantError(
                f"Chore '{chore_info.get('name')}' is not assigned to kid '{self.kids_data[kid_id]['name']}'."
            )

        if kid_id not in self.kids_data:
            LOGGER.warning("Kid ID '%s' not found", kid_id)
            raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

        kid_info = self.kids_data.get(kid_id)

        self._normalize_kid_lists(kid_info)

        allow_multiple = chore_info.get("allow_multiple_claims_per_day", False)
        if allow_multiple:
            # If already approved, remove it so the new claim can trigger a new approval flow
            kid_info["approved_chores"] = [
                item for item in kid_info.get("approved_chores", []) if item != chore_id
            ]

        if not allow_multiple:
            if chore_id in kid_info.get(
                "claimed_chores", []
            ) or chore_id in kid_info.get("approved_chores", []):
                error_message = f"Chore '{chore_info['name']}' has already been claimed today and multiple claims are not allowed."
                LOGGER.warning(error_message)
                raise HomeAssistantError(error_message)

        self._process_chore_state(kid_id, chore_id, CHORE_STATE_CLAIMED)

        # Send a notification to the parents that a kid claimed a chore
        if chore_info.get(CONF_NOTIFY_ON_CLAIM, DEFAULT_NOTIFY_ON_CLAIM):
            actions = [
                {
                    "action": f"{ACTION_APPROVE_CHORE}|{kid_id}|{chore_id}",
                    "title": ACTION_TITLE_APPROVE,
                },
                {
                    "action": f"{ACTION_DISAPPROVE_CHORE}|{kid_id}|{chore_id}",
                    "title": ACTION_TITLE_DISAPPROVE,
                },
                {
                    "action": f"{ACTION_REMIND_30}|{kid_id}|{chore_id}",
                    "title": ACTION_TITLE_REMIND_30,
                },
            ]
            # Pass extra context so the event handler can route the action.
            extra_data = {
                "kid_id": kid_id,
                "chore_id": chore_id,
            }
            self.hass.async_create_task(
                self._notify_parents(
                    kid_id,
                    title="KidsChores: Chore Claimed",
                    message=f"'{self.kids_data[kid_id]['name']}' claimed chore '{self.chores_data[chore_id]['name']}'",
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
        if kid_id not in chore_info.get("assigned_kids", []):
            raise HomeAssistantError(
                f"Chore '{chore_info.get('name')}' is not assigned to kid '{self.kids_data[kid_id]['name']}'."
            )

        if kid_id not in self.kids_data:
            raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

        kid_info = self.kids_data.get(kid_id)

        allow_multiple = chore_info.get("allow_multiple_claims_per_day", False)
        if not allow_multiple:
            if chore_id in kid_info.get("approved_chores", []):
                error_message = f"Chore '{chore_info['name']}' has already been approved today; multiple approvals not allowed."
                LOGGER.warning(error_message)
                raise HomeAssistantError(error_message)

        default_points = chore_info.get("default_points", DEFAULT_POINTS)
        multiplier = kid_info.get("points_multiplier", 1.0)
        awarded_points = (
            points_awarded * multiplier
            if points_awarded is not None
            else default_points * multiplier
        )

        self._process_chore_state(
            kid_id, chore_id, CHORE_STATE_APPROVED, points_awarded=awarded_points
        )

        old_points = float(kid_info["points"])
        new_points = old_points + awarded_points
        self.update_kid_points(kid_id, new_points)

        # increment completed chores counters
        kid_info["completed_chores_today"] += 1
        kid_info["completed_chores_weekly"] += 1
        kid_info["completed_chores_monthly"] += 1
        kid_info["completed_chores_total"] += 1

        # Track today’s approvals for chores that allow multiple claims.
        if chore_info.get("allow_multiple_claims_per_day", False):
            kid_info.setdefault("today_chore_approvals", {})
            kid_info["today_chore_approvals"][chore_id] = (
                kid_info["today_chore_approvals"].get(chore_id, 0) + 1
            )

        chore_info["last_completed"] = dt_util.utcnow().isoformat()

        today = dt_util.as_local(dt_util.utcnow()).date()
        self._update_chore_streak_for_kid(kid_id, chore_id, today)
        self._update_overall_chore_streak(kid_id, today)

        # remove from pending approvals
        self._data[DATA_PENDING_CHORE_APPROVALS] = [
            ap
            for ap in self._data[DATA_PENDING_CHORE_APPROVALS]
            if not (ap["kid_id"] == kid_id and ap["chore_id"] == chore_id)
        ]

        # increment chore approvals
        if chore_id in kid_info["chore_approvals"]:
            kid_info["chore_approvals"][chore_id] += 1
        else:
            kid_info["chore_approvals"][chore_id] = 1

        # Manage Achievements
        today = dt_util.as_local(dt_util.utcnow()).date()
        for achievement_id, achievement in self.achievements_data.items():
            if achievement.get("type") == ACHIEVEMENT_TYPE_STREAK:
                selected_chore_id = achievement.get("selected_chore_id")
                if selected_chore_id == chore_id:
                    # Get or create the progress dict for this kid
                    progress = achievement.setdefault("progress", {}).setdefault(
                        kid_id,
                        {"current_streak": 0, "last_date": None, "awarded": False},
                    )
                    self._update_streak_progress(progress, today)

        # Manage Challenges
        today_iso = dt_util.as_local(dt_util.utcnow()).date().isoformat()
        for challenge_id, challenge in self.challenges_data.items():
            if challenge.get("type") == CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                # (Challenge update logic for total-within-window remains here)
                start_date_raw = challenge.get("start_date")
                if isinstance(start_date_raw, str):
                    start_date = dt_util.parse_datetime(start_date_raw)
                    if start_date and start_date.tzinfo is None:
                        start_date = start_date.replace(tzinfo=dt_util.UTC)
                else:
                    start_date = None

                end_date_raw = challenge.get("end_date")
                if isinstance(end_date_raw, str):
                    end_date = dt_util.parse_datetime(end_date_raw)
                    if end_date and end_date.tzinfo is None:
                        end_date = end_date.replace(tzinfo=dt_util.UTC)
                else:
                    end_date = None

                now = dt_util.utcnow()

                if start_date and end_date and start_date <= now <= end_date:
                    progress = challenge.setdefault("progress", {}).setdefault(
                        kid_id, {"count": 0, "awarded": False}
                    )
                    progress["count"] += 1

            elif challenge.get("type") == CHALLENGE_TYPE_DAILY_MIN:
                # Only update if the challenge is tracking a specific chore.
                selected_chore = challenge.get("selected_chore_id")
                if not selected_chore:
                    LOGGER.warning(
                        "Challenge '%s' of type daily_min has no selected_chore_id set. Skipping progress update.",
                        challenge.get("name"),
                    )
                    continue
                if selected_chore != chore_id:
                    continue
                if kid_id in challenge.get("assigned_kids", []):
                    progress = challenge.setdefault("progress", {}).setdefault(
                        kid_id, {"daily_counts": {}, "awarded": False}
                    )
                    progress["daily_counts"][today_iso] = (
                        progress["daily_counts"].get(today_iso, 0) + 1
                    )

        # Send a notification to the kid that chore was approved
        if chore_info.get(CONF_NOTIFY_ON_APPROVAL, DEFAULT_NOTIFY_ON_APPROVAL):
            extra_data = {"kid_id": kid_id, "chore_id": chore_id}
            self.hass.async_create_task(
                self._notify_kid(
                    kid_id,
                    title="KidsChores: Chore Approved",
                    message=f"Your chore '{chore_info['name']}' was approved. You earned {awarded_points} points.",
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

        self._process_chore_state(kid_id, chore_id, CHORE_STATE_PENDING)

        # Send a notification to the kid that chore was disapproved
        if chore_info.get(CONF_NOTIFY_ON_DISAPPROVAL, DEFAULT_NOTIFY_ON_DISAPPROVAL):
            extra_data = {"kid_id": kid_id, "chore_id": chore_id}
            self.hass.async_create_task(
                self._notify_kid(
                    kid_id,
                    title="KidsChores: Chore Disapproved",
                    message=f"Your chore '{chore_info['name']}' was disapproved.",
                    extra_data=extra_data,
                )
            )

        self._persist()
        self.async_set_updated_data(self._data)

    def update_chore_state(self, chore_id: str, state: str):
        """Manually override a chore's state."""
        chore_info = self.chores_data.get(chore_id)
        if not chore_info:
            LOGGER.warning("Update chore state: Chore ID '%s' not found", chore_id)
            return
        # Set state for all kids assigned to the chore:
        for kid_id in chore_info.get("assigned_kids", []):
            if kid_id:
                self._process_chore_state(kid_id, chore_id, state)
        self._persist()
        self.async_set_updated_data(self._data)
        LOGGER.debug(f"Chore ID '{chore_id}' state manually updated to '{state}'")

    # -------------------------------------------------------------------------------------
    # Chore State Processing: Centralized Function
    # The most critical thing to understand when working on this function is that
    # chore_info["state"] is actually the global state of the chore. The individual chore
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
        LOGGER.debug(
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
            LOGGER.warning(
                "State change skipped: Kid '%s' or Chore '%s' not found",
                kid_id,
                chore_id,
            )
            return

        # Clear any overdue tracking.
        kid_info.setdefault("overdue_chores", [])
        kid_info.setdefault("overdue_notifications", {})

        # Remove all instances of the chore from overdue lists.
        kid_info["overdue_chores"] = [
            entry for entry in kid_info.get("overdue_chores", []) if entry != chore_id
        ]

        if chore_id in kid_info["overdue_notifications"]:
            kid_info["overdue_notifications"].pop(chore_id)

        if new_state == CHORE_STATE_CLAIMED:
            # Remove all previous approvals in case of duplicate, add to claimed.
            kid_info["approved_chores"] = [
                item for item in kid_info.get("approved_chores", []) if item != chore_id
            ]

            kid_info.setdefault("claimed_chores", [])

            if chore_id not in kid_info["claimed_chores"]:
                kid_info["claimed_chores"].append(chore_id)

            chore_info["last_claimed"] = dt_util.utcnow().isoformat()

            self._data.setdefault(DATA_PENDING_CHORE_APPROVALS, []).append(
                {
                    "kid_id": kid_id,
                    "chore_id": chore_id,
                    "timestamp": dt_util.utcnow().isoformat(),
                }
            )

        elif new_state == CHORE_STATE_APPROVED:
            # Remove all claims for chores in case of duplicates, add to approvals.
            kid_info["claimed_chores"] = [
                item for item in kid_info.get("claimed_chores", []) if item != chore_id
            ]

            kid_info.setdefault("approved_chores", [])

            if chore_id not in kid_info["approved_chores"]:
                kid_info["approved_chores"].append(chore_id)

            chore_info["last_completed"] = dt_util.utcnow().isoformat()

            if points_awarded is not None:
                current_points = float(kid_info.get("points", 0))
                self.update_kid_points(kid_id, current_points + points_awarded)

            today = dt_util.as_local(dt_util.utcnow()).date()

            self._update_chore_streak_for_kid(kid_id, chore_id, today)
            self._update_overall_chore_streak(kid_id, today)

            self._data[DATA_PENDING_CHORE_APPROVALS] = [
                ap
                for ap in self._data.get(DATA_PENDING_CHORE_APPROVALS, [])
                if not (ap.get("kid_id") == kid_id and ap.get("chore_id") == chore_id)
            ]

        elif new_state == CHORE_STATE_PENDING:
            # Remove the chore from both claimed and approved lists.
            for field in ["claimed_chores", "approved_chores"]:
                if chore_id in kid_info.get(field, []):
                    kid_info[field] = [c for c in kid_info[field] if c != chore_id]

            # Remove from pending approvals.
            self._data[DATA_PENDING_CHORE_APPROVALS] = [
                ap
                for ap in self._data.get(DATA_PENDING_CHORE_APPROVALS, [])
                if not (ap.get("kid_id") == kid_id and ap.get("chore_id") == chore_id)
            ]

        elif new_state == CHORE_STATE_OVERDUE:
            # Mark as overdue.
            kid_info.setdefault("overdue_chores", [])

            if chore_id not in kid_info["overdue_chores"]:
                kid_info["overdue_chores"].append(chore_id)

            kid_info.setdefault("overdue_notifications", {})
            kid_info["overdue_notifications"][chore_id] = dt_util.utcnow().isoformat()

        # Compute and update the chore's global state.
        # Given the process above is handling everything properly for each kid, computing the global state straightforward.
        # This process needs run every time a chore state changes, so it no longer warrants a separate function.
        assigned_kids = chore_info.get("assigned_kids", [])

        if len(assigned_kids) == 1:
            # if only one kid is assigned to the chore, update the chore state to new state 1:1
            chore_info["state"] = new_state
        elif len(assigned_kids) > 1:
            # For chores assigned to multiple kids, you have to figure out the global state
            count_pending = count_claimed = count_approved = count_overdue = 0
            for kid_id in assigned_kids:
                kid_info = self.kids_data.get(kid_id, {})
                if chore_id in kid_info.get("overdue_chores", []):
                    count_overdue += 1
                elif chore_id in kid_info.get("approved_chores", []):
                    count_approved += 1
                elif chore_id in kid_info.get("claimed_chores", []):
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
                chore_info["state"] = new_state

            # For shared chores, recompute global state of a partial if they aren't all in the same state as checked above
            elif chore_info.get("shared_chore", False):
                if count_overdue > 0:
                    chore_info["state"] = CHORE_STATE_OVERDUE
                elif count_approved > 0:
                    chore_info["state"] = CHORE_STATE_APPROVED_IN_PART
                elif count_claimed > 0:
                    chore_info["state"] = CHORE_STATE_CLAIMED_IN_PART
                else:
                    chore_info["state"] = CHORE_STATE_UNKNOWN

            # For non-shared chores multiple assign it will be independent if they aren't all in the same state as checked above.
            elif chore_info.get("shared_chore", False) is False:
                chore_info["state"] = CHORE_STATE_INDEPENDENT

        else:
            chore_info["state"] = CHORE_STATE_UNKNOWN

        LOGGER.debug(
            "Chore '%s' global state computed as '%s'",
            chore_id,
            chore_info["state"],
        )

    # -------------------------------------------------------------------------------------
    # Kids: Update Points
    # -------------------------------------------------------------------------------------

    def update_kid_points(self, kid_id: str, new_points: float):
        """Set a kid's points to 'new_points', updating daily/weekly/monthly counters."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            LOGGER.warning("Update kid points: Kid ID '%s' not found", kid_id)
            return

        old_points = float(kid_info["points"])
        delta = new_points - old_points
        if delta == 0:
            LOGGER.debug("No change in points for kid '%s'. Skipping updates", kid_id)
            return

        kid_info["points"] = new_points
        kid_info["points_earned_today"] += delta
        kid_info["points_earned_weekly"] += delta
        kid_info["points_earned_monthly"] += delta

        # Update Max Points Ever
        if new_points > kid_info.get("max_points_ever", 0):
            kid_info["max_points_ever"] = new_points

        # Check Badges
        self._check_badges_for_kid(kid_id)
        self._check_achievements_for_kid(kid_id)
        self._check_challenges_for_kid(kid_id)

        self._persist()
        self.async_set_updated_data(self._data)

        LOGGER.debug(
            "update_kid_points: Kid '%s' changed from %.2f to %.2f (delta=%.2f)",
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

        cost = reward.get("cost", 0.0)
        if kid_info["points"] < cost:
            raise HomeAssistantError(
                f"'{kid_info['name']}' does not have enough points ({cost} needed)."
            )

        kid_info.setdefault("pending_rewards", []).append(reward_id)
        kid_info.setdefault("redeemed_rewards", [])

        # Add to pending approvals
        self._data[DATA_PENDING_REWARD_APPROVALS].append(
            {
                "kid_id": kid_id,
                "reward_id": reward_id,
                "timestamp": dt_util.utcnow().isoformat(),
            }
        )

        # increment reward_claims counter
        if reward_id in kid_info["reward_claims"]:
            kid_info["reward_claims"][reward_id] += 1
        else:
            kid_info["reward_claims"][reward_id] = 1

        # Send a notification to the parents that a kid claimed a reward
        actions = [
            {
                "action": f"{ACTION_APPROVE_REWARD}|{kid_id}|{reward_id}",
                "title": ACTION_TITLE_APPROVE,
            },
            {
                "action": f"{ACTION_DISAPPROVE_REWARD}|{kid_id}|{reward_id}",
                "title": ACTION_TITLE_DISAPPROVE,
            },
            {
                "action": f"{ACTION_REMIND_30}|{kid_id}|{reward_id}",
                "title": ACTION_TITLE_REMIND_30,
            },
        ]
        extra_data = {"kid_id": kid_id, "reward_id": reward_id}
        self.hass.async_create_task(
            self._notify_parents(
                kid_id,
                title="KidsChores: Reward Claimed",
                message=f"'{kid_info['name']}' claimed reward '{reward['name']}'",
                actions=actions,
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    def approve_reward(self, parent_name: str, kid_id: str, reward_id: str):
        """Parent approves the reward => deduct points."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

        reward = self.rewards_data.get(reward_id)
        if not reward:
            raise HomeAssistantError(f"Reward with ID '{reward_id}' not found.")

        cost = reward.get("cost", 0.0)
        if reward_id in kid_info.get("pending_rewards", []):
            if kid_info["points"] < cost:
                raise HomeAssistantError(
                    f"'{kid_info['name']}' does not have enough points to redeem '{reward['name']}'."
                )

            # Deduct
            new_points = float(kid_info["points"]) - cost
            self.update_kid_points(kid_id, new_points)

            kid_info["pending_rewards"].remove(reward_id)
            kid_info["redeemed_rewards"].append(reward_id)
        else:
            # direct approval scenario
            if kid_info["points"] < cost:
                raise HomeAssistantError(
                    f"'{kid_info['name']}' does not have enough points to redeem '{reward['name']}'."
                )
            kid_info["points"] -= cost
            kid_info["redeemed_rewards"].append(reward_id)

        self._check_badges_for_kid(kid_id)

        # remove 1 claim from pending approvals
        approvals = self._data[DATA_PENDING_REWARD_APPROVALS]
        for i, ap in enumerate(approvals):
            if ap["kid_id"] == kid_id and ap["reward_id"] == reward_id:
                del approvals[i]  # Remove only the first match
                break  # Stop after the first removal

        # increment reward_approvals
        if reward_id in kid_info["reward_approvals"]:
            kid_info["reward_approvals"][reward_id] += 1
        else:
            kid_info["reward_approvals"][reward_id] = 1

        # Send a notification to the kid that reward was approved
        extra_data = {"kid_id": kid_id, "reward_id": reward_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Reward Approved",
                message=f"Your reward '{reward['name']}' was approved.",
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

        # remove from pending approvals
        self._data[DATA_PENDING_REWARD_APPROVALS] = [
            ap
            for ap in self._data[DATA_PENDING_REWARD_APPROVALS]
            if not (ap["kid_id"] == kid_id and ap["reward_id"] == reward_id)
        ]

        kid_info = self.kids_data.get(kid_id)
        if kid_info and reward_id in kid_info.get("pending_rewards", []):
            kid_info["pending_rewards"].remove(reward_id)

        # Send a notification to the kid that reward was disapproved
        extra_data = {"kid_id": kid_id, "reward_id": reward_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Reward Disapproved",
                message=f"Your reward '{reward['name']}' was disapproved.",
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------------------
    # Badges: Add, Check, Award
    # -------------------------------------------------------------------------------------

    def add_badge(self, badge_def: dict[str, Any]):
        """Add new badge at runtime if needed."""
        badge_name = badge_def.get("name")
        if not badge_name:
            LOGGER.warning("Add badge: Badge must have a name")
            return
        if any(b["name"] == badge_name for b in self.badges_data.values()):
            LOGGER.warning("Add badge: Badge '%s' already exists", badge_name)
            return
        internal_id = str(uuid.uuid4())
        self.badges_data[internal_id] = {
            "name": badge_name,
            "threshold_type": badge_def.get(
                "threshold_type", BADGE_THRESHOLD_TYPE_POINTS
            ),
            "threshold_value": badge_def.get(
                "threshold_value", DEFAULT_BADGE_THRESHOLD
            ),
            "chore_count_type": badge_def.get("chore_count_type", FREQUENCY_DAILY),
            "earned_by": [],
            "points_multiplier": badge_def.get(
                "points_multiplier", DEFAULT_POINTS_MULTIPLIER
            ),
            "icon": badge_def.get("icon", DEFAULT_ICON),
            "description": badge_def.get("description", ""),
            "internal_id": internal_id,
        }
        LOGGER.debug("Added new badge '%s' with ID: %s", badge_name, internal_id)
        self._persist()
        self.async_set_updated_data(self._data)

    def _check_badges_for_kid(self, kid_id: str):
        """Evaluate all badge thresholds for kid."""
        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return

        for badge_id, badge_data in self.badges_data.items():
            if kid_id in badge_data.get("earned_by", []):
                continue  # already earned
            threshold_type = badge_data.get("threshold_type")
            threshold_val = badge_data.get("threshold_value", 0)
            if threshold_type == BADGE_THRESHOLD_TYPE_POINTS:
                if kid_info["points"] >= threshold_val:
                    self._award_badge(kid_id, badge_id)
            elif threshold_type == BADGE_THRESHOLD_TYPE_CHORE_COUNT:
                ctype = badge_data.get("chore_count_type", FREQUENCY_DAILY)
                if ctype == "total":
                    ccount = kid_info.get("completed_chores_total", 0)
                else:
                    ccount = kid_info.get(f"completed_chores_{ctype}", 0)
                if ccount >= threshold_val:
                    self._award_badge(kid_id, badge_id)

    def _award_badge(self, kid_id: str, badge_id: str):
        """Add the badge to kid's 'earned_by' and kid's 'badges' list."""
        badge = self.badges_data.get(badge_id)
        if not badge:
            LOGGER.error(
                "Attempted to award non-existent badge ID '%s' to kid ID '%s'",
                badge_id,
                kid_id,
            )
            return

        if kid_id in badge.get("earned_by", []):
            return  # already earned

        badge.setdefault("earned_by", []).append(kid_id)
        kid_info = self.kids_data.get(kid_id, {})
        if badge["name"] not in kid_info.get("badges", []):
            kid_info.setdefault("badges", []).append(badge["name"])
            self._update_kid_multiplier(kid_id)

            badge_name = badge["name"]
            kid_name = kid_info["name"]

            # Send a notification to the kid and parents that a new badge was earned
            extra_data = {"kid_id": kid_id, "badge_id": badge_id}
            self.hass.async_create_task(
                self._notify_kid(
                    kid_id,
                    title="KidsChores: Badge Earned",
                    message=f"You earned a new badge: '{badge_name}'!",
                    extra_data=extra_data,
                )
            )
            self.hass.async_create_task(
                self._notify_parents(
                    kid_id,
                    title="KidsChores: Badge Earned",
                    message=f"'{kid_name}' earned a new badge: '{badge_name}'.",
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
            b for b in self.badges_data.values() if kid_id in b.get("earned_by", [])
        ]
        if not earned_badges:
            kid_info["points_multiplier"] = 1.0
            return
        highest_mult = max(b.get("points_multiplier", 1.0) for b in earned_badges)
        kid_info["points_multiplier"] = highest_mult

    def _recalculate_all_badges(self):
        """Global re-check of all badges for all kids."""
        LOGGER.info("Starting global badge recalculation")

        ## Clear current references
        # for _, badge_info in self.badges_data.items():
        #    badge_info["earned_by"] = []
        # for _, kid_info in self.kids_data.items():
        #    kid_info["badges"] = []

        # Re-check thresholds
        for badge_id, badge_info in self.badges_data.items():
            ttype = badge_info.get("threshold_type", BADGE_THRESHOLD_TYPE_POINTS)
            tval = badge_info.get("threshold_value", 0)
            for kid_id, kid_info in self.kids_data.items():
                if ttype == BADGE_THRESHOLD_TYPE_POINTS:
                    if kid_info.get("max_points_ever", 0.0) >= tval:
                        self._award_badge(kid_id, badge_id)
                elif ttype == BADGE_THRESHOLD_TYPE_CHORE_COUNT:
                    ctype = badge_info.get("chore_count_type", FREQUENCY_DAILY)
                    if ctype == "total":
                        ccount = kid_info.get("completed_chores_total", 0)
                    else:
                        ccount = kid_info.get(f"completed_chores_{ctype}", 0)
                    if ccount >= tval:
                        self._award_badge(kid_id, badge_id)

        self._persist()
        self.async_set_updated_data(self._data)
        LOGGER.info("Badge recalculation complete")

    # -------------------------------------------------------------------------------------
    # Penalties: Apply, Add
    # -------------------------------------------------------------------------------------

    def apply_penalty(self, parent_name: str, kid_id: str, penalty_id: str):
        """Apply penalty => negative points to reduce kid's points."""
        penalty = self.penalties_data.get(penalty_id)
        if not penalty:
            raise HomeAssistantError(f"Penalty with ID '{penalty_id}' not found.")

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

        penalty_pts = penalty.get("points", 0)
        new_points = float(kid_info["points"]) + penalty_pts
        self.update_kid_points(kid_id, new_points)

        # increment penalty_applies
        if penalty_id in kid_info["penalty_applies"]:
            kid_info["penalty_applies"][penalty_id] += 1
        else:
            kid_info["penalty_applies"][penalty_id] = 1

        # Send a notification to the kid that a penalty was applied
        extra_data = {"kid_id": kid_id, "penalty_id": penalty_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Penalty Applied",
                message=f"A '{penalty['name']}' penalty was applied. Your points changed by {penalty_pts}.",
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    def add_penalty(self, penalty_def: dict[str, Any]):
        """Add new penalty at runtime if needed."""
        penalty_name = penalty_def.get("name")
        if not penalty_name:
            LOGGER.warning("Add penalty: Penalty must have a name")
            return
        if any(p["name"] == penalty_name for p in self.penalties_data.values()):
            LOGGER.warning("Add penalty: Penalty '%s' already exists", penalty_name)
            return
        internal_id = str(uuid.uuid4())
        self.penalties_data[internal_id] = {
            "name": penalty_name,
            "points": penalty_def.get("points", -DEFAULT_PENALTY_POINTS),
            "description": penalty_def.get("description", ""),
            "icon": penalty_def.get("icon", DEFAULT_PENALTY_ICON),
            "internal_id": internal_id,
        }
        LOGGER.debug("Added new penalty '%s' with ID: %s", penalty_name, internal_id)
        self._persist()
        self.async_set_updated_data(self._data)

    # -------------------------------------------------------------------------
    # Bonuses: Apply, Add
    # -------------------------------------------------------------------------

    def apply_bonus(self, parent_name: str, kid_id: str, bonus_id: str):
        """Apply bonus => positive points to increase kid's points."""
        bonus = self.bonuses_data.get(bonus_id)
        if not bonus:
            raise HomeAssistantError(f"Bonus with ID '{bonus_id}' not found.")

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")

        bonus_pts = bonus.get("points", 0)
        new_points = float(kid_info["points"]) + bonus_pts
        self.update_kid_points(kid_id, new_points)

        # increment bonus_applies
        if bonus_id in kid_info["bonus_applies"]:
            kid_info["bonus_applies"][bonus_id] += 1
        else:
            kid_info["bonus_applies"][bonus_id] = 1

        # Send a notification to the kid that a bonus was applied
        extra_data = {"kid_id": kid_id, "bonus_id": bonus_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Bonus Applied",
                message=f"A '{bonus['name']}' bonus was applied. Your points changed by {bonus_pts}.",
                extra_data=extra_data,
            )
        )

        self._persist()
        self.async_set_updated_data(self._data)

    def add_bonus(self, bonus_def: dict[str, Any]):
        """Add new bonus at runtime if needed."""
        bonus_name = bonus_def.get("name")
        if not bonus_name:
            LOGGER.warning("Add bonus: Bonus must have a name")
            return
        if any(s["name"] == bonus_name for s in self.bonuses_data.values()):
            LOGGER.warning("Add bonus: Bonus '%s' already exists", bonus_name)
            return
        internal_id = str(uuid.uuid4())
        self.bonuses_data[internal_id] = {
            "name": bonus_name,
            "points": bonus_def.get("points", DEFAULT_BONUS_POINTS),
            "description": bonus_def.get("description", ""),
            "icon": bonus_def.get("icon", DEFAULT_BONUS_ICON),
            "internal_id": internal_id,
        }
        LOGGER.debug("Added new bonus '%s' with ID: %s", bonus_name, internal_id)
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

        for achievement_id, achievement in self._data[DATA_ACHIEVEMENTS].items():
            progress = achievement.setdefault("progress", {})
            if kid_id in progress and progress[kid_id].get("awarded", False):
                continue

            ach_type = achievement.get("type")
            target = achievement.get("target_value", 1)

            # For a streak achievement, update a streak counter:
            if ach_type == ACHIEVEMENT_TYPE_STREAK:
                progress = progress.setdefault(
                    kid_id, {"current_streak": 0, "last_date": None, "awarded": False}
                )

                self._update_streak_progress(progress, now_date)
                if progress["current_streak"] >= target:
                    self._award_achievement(kid_id, achievement_id)

            # For a total achievement, simply compare total completed chores:
            elif ach_type == ACHIEVEMENT_TYPE_TOTAL:
                # Get per–kid progress for this achievement.
                progress = achievement.setdefault("progress", {}).setdefault(
                    kid_id, {"baseline": None, "current_value": 0, "awarded": False}
                )

                # Set the baseline so that we only count chores done after deployment.
                if progress["baseline"] is None:
                    progress["baseline"] = kid_info.get("completed_chores_total", 0)

                # Calculate progress as (current total minus baseline)
                current_total = kid_info.get("completed_chores_total", 0)

                progress["current_value"] = current_total

                effective_target = progress["baseline"] + target

                if current_total >= effective_target:
                    self._award_achievement(kid_id, achievement_id)

            # For daily minimum achievement, compare total daily chores:
            elif ach_type == ACHIEVEMENT_TYPE_DAILY_MIN:
                # Initialize progress for this achievement if missing.
                progress = achievement.setdefault("progress", {}).setdefault(
                    kid_id, {"last_awarded_date": None, "awarded": False}
                )

                today = dt_util.as_local(dt_util.utcnow()).date().isoformat()

                # Only award bonus if not awarded today AND the kid's daily count meets the threshold.
                if (
                    progress.get("last_awarded_date") != today
                    and kid_info.get("completed_chores_today", 0) >= target
                ):
                    self._award_achievement(kid_id, achievement_id)
                    progress["last_awarded_date"] = today

    def _award_achievement(self, kid_id: str, achievement_id: str):
        """Award the achievement to the kid.

        Update the achievement progress to indicate it is earned,
        and send notifications to both the kid and their parents.
        """
        achievement = self.achievements_data.get(achievement_id)
        if not achievement:
            LOGGER.error(
                "Attempted to award non-existent achievement '%s'", achievement_id
            )
            return

        # Get or create the existing progress dictionary for this kid
        progress_for_kid = achievement.setdefault("progress", {}).get(kid_id)
        if progress_for_kid is None:
            # If it doesn't exist, initialize it with baseline from the kid's current total.
            kid_info = self.kids_data.get(kid_id, {})
            progress_dict = {
                "baseline": kid_info.get("completed_chores_total", 0),
                "current_value": 0,
                "awarded": False,
            }
            achievement["progress"][kid_id] = progress_dict

        # Mark achievement as earned for the kid by storing progress (e.g. set to target)
        progress_for_kid["awarded"] = True
        progress_for_kid["current_value"] = achievement.get("target_value", 1)

        # Award the extra reward points defined in the achievement
        extra_points = achievement.get("reward_points", 0)
        kid_info = self.kids_data.get(kid_id)
        if kid_info is not None:
            new_points = float(kid_info["points"]) + extra_points
            self.update_kid_points(kid_id, new_points)

        # Notify kid and parents
        extra_data = {"kid_id": kid_id, "achievement_id": achievement_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Achievement Earned",
                message=f"You have earned the achievement: '{achievement.get('name')}'.",
                extra_data=extra_data,
            )
        )
        self.hass.async_create_task(
            self._notify_parents(
                kid_id,
                title="KidsChores: Achievement Earned",
                message=f"{self.kids_data[kid_id]['name']} has earned the achievement: '{achievement.get('name')}'.",
                extra_data=extra_data,
            )
        )
        LOGGER.info(
            "Awarded achievement '%s' to kid '%s'", achievement.get("name"), kid_id
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
            progress = challenge.setdefault("progress", {})
            if kid_id in progress and progress[kid_id].get("awarded", False):
                continue

            # Check challenge window
            start_date_raw = challenge.get("start_date")
            if isinstance(start_date_raw, str):
                start = dt_util.parse_datetime(start_date_raw)
            else:
                start = None

            end_date_raw = challenge.get("end_date")
            if isinstance(end_date_raw, str):
                end = dt_util.parse_datetime(end_date_raw)
            else:
                end = None

            if start and now < start:
                continue
            if end and now > end:
                continue

            target = challenge.get("target_value", 1)
            challenge_type = challenge.get("type")

            # For a total count challenge:
            if challenge_type == CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                progress = progress.setdefault(kid_id, {"count": 0, "awarded": False})

                if progress["count"] >= target:
                    self._award_challenge(kid_id, challenge_id)
            # For a daily minimum challenge, you might store per-day counts:
            elif challenge_type == CHALLENGE_TYPE_DAILY_MIN:
                progress = progress.setdefault(
                    kid_id, {"daily_counts": {}, "awarded": False}
                )

                required_daily = challenge.get("required_daily", 1)
                start = dt_util.parse_datetime(challenge.get("start_date"))
                end = dt_util.parse_datetime(challenge.get("end_date"))
                if start and end:
                    num_days = (end - start).days + 1
                    # Verify for each day:
                    success = True
                    for n in range(num_days):
                        day = (start + timedelta(days=n)).date().isoformat()
                        if progress["daily_counts"].get(day, 0) < required_daily:
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
            LOGGER.error("Attempted to award non-existent challenge '%s'", challenge_id)
            return

        # Get or create the existing progress dictionary for this kid
        progress_for_kid = challenge.setdefault("progress", {}).setdefault(
            kid_id, {"count": 0, "awarded": False}
        )

        # Mark challenge as earned for the kid by storing progress
        progress_for_kid["awarded"] = True
        progress_for_kid["count"] = challenge.get("target_value", 1)

        # Award extra reward points from the challenge
        extra_points = challenge.get("reward_points", 0)
        kid_info = self.kids_data.get(kid_id)
        if kid_info is not None:
            new_points = float(kid_info["points"]) + extra_points
            self.update_kid_points(kid_id, new_points)

        # Notify kid and parents
        extra_data = {"kid_id": kid_id, "challenge_id": challenge_id}
        self.hass.async_create_task(
            self._notify_kid(
                kid_id,
                title="KidsChores: Challenge Completed",
                message=f"You have completed the challenge: '{challenge.get('name')}'.",
                extra_data=extra_data,
            )
        )
        self.hass.async_create_task(
            self._notify_parents(
                kid_id,
                title="KidsChores: Challenge Completed",
                message=f"{self.kids_data[kid_id]['name']} has completed the challenge: '{challenge.get('name')}'.",
                extra_data=extra_data,
            )
        )
        LOGGER.info("Awarded challenge '%s' to kid '%s'", challenge.get("name"), kid_id)
        self._persist()
        self.async_set_updated_data(self._data)

    def _update_streak_progress(self, progress: dict, today: datetime.date):
        """Update a streak progress dict.

        If the last approved date was yesterday, increment the streak.
        Otherwise, reset to 1.
        """
        last_date = None
        if progress.get("last_date"):
            # Parse the stored ISO string using Home Assistant's dt_util
            last_dt = dt_util.parse_datetime(progress["last_date"])
            if last_dt:
                # Convert to local time and get the date portion
                last_date = dt_util.as_local(last_dt).date()
        if last_date == today:
            # Already updated today – do nothing
            return
        elif last_date == today - timedelta(days=1):
            progress["current_streak"] += 1
        else:
            progress["current_streak"] = 1
        progress["last_date"] = today.isoformat()

    def _update_chore_streak_for_kid(
        self, kid_id: str, chore_id: str, completion_date: datetime.date
    ):
        """Update (or initialize) the streak for a specific chore for a kid, and update the max streak achieved so far."""

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return
        # Ensure a streak dictionary exists
        if "chore_streaks" not in kid_info:
            kid_info["chore_streaks"] = {}

        # Initialize the streak record if not already present
        streak = kid_info["chore_streaks"].get(
            chore_id, {"current_streak": 0, "max_streak": 0, "last_date": None}
        )
        last_date = None
        if streak["last_date"]:
            try:
                last_date = datetime.fromisoformat(streak["last_date"]).date()
            except Exception:
                pass

        if last_date == completion_date - timedelta(days=1):
            streak["current_streak"] += 1
        else:
            streak["current_streak"] = 1

        streak["last_date"] = completion_date.isoformat()

        # Update the maximum streak if the current streak is higher.
        if streak["current_streak"] > streak.get("max_streak", 0):
            streak["max_streak"] = streak["current_streak"]

        kid_info["chore_streaks"][chore_id] = streak

    def _update_overall_chore_streak(self, kid_id: str, completion_date: datetime.date):
        """Update the overall streak for a kid (days in a row with at least one approved chore)."""

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            return
        last_date = None
        if "last_chore_date" in kid_info and kid_info["last_chore_date"]:
            try:
                last_date = datetime.fromisoformat(kid_info["last_chore_date"]).date()
            except Exception:
                pass
        if last_date == completion_date - timedelta(days=1):
            kid_info["overall_chore_streak"] = (
                kid_info.get("overall_chore_streak", 0) + 1
            )
        else:
            kid_info["overall_chore_streak"] = 1
        kid_info["last_chore_date"] = completion_date.isoformat()

    # -------------------------------------------------------------------------------------
    # Recurring / Reset / Overdue
    # -------------------------------------------------------------------------------------

    async def _check_overdue_chores(self):
        """Check and mark overdue chores if due date is passed.

        Send an overdue notification only if not sent in the last 24 hours.
        """
        now = dt_util.utcnow()
        LOGGER.debug("Starting overdue check at %s", now.isoformat())

        for chore_id, chore_info in self.chores_data.items():
            LOGGER.debug(
                "Checking chore '%s' id '%s' (state=%s)",
                chore_info.get("name"),
                chore_id,
                chore_info.get("state"),
            )

            # Get the list of assigned kids
            assigned_kids = chore_info.get("assigned_kids", [])
            LOGGER.debug(
                "Chore '%s' id '%s' assigned to kids: %s",
                chore_info.get("name"),
                chore_id,
                assigned_kids,
            )

            # Check if all assigned kids have either claimed or approved the chore
            all_kids_claimed_or_approved = all(
                chore_id in self.kids_data.get(kid_id, {}).get("claimed_chores", [])
                or chore_id in self.kids_data.get(kid_id, {}).get("approved_chores", [])
                for kid_id in assigned_kids
            )

            # Debugging: Log the claim/approval status of each assigned kid
            for kid_id in assigned_kids:
                kid_info = self.kids_data.get(kid_id, {})
                has_claimed = chore_id in kid_info.get("claimed_chores", [])
                has_approved = chore_id in kid_info.get("approved_chores", [])

                LOGGER.debug(
                    "Kid '%s': claimed=%s, approved=%s",
                    kid_id,
                    has_claimed,
                    has_approved,
                )

            # Log the overall result of the check
            LOGGER.debug(
                "Chore '%s': all_kids_claimed_or_approved=%s",
                chore_id,
                all_kids_claimed_or_approved,
            )

            # Only skip the chore if ALL assigned kids have acted on it
            if all_kids_claimed_or_approved:
                LOGGER.debug(
                    "Skipping chore '%s': all assigned kids have claimed or approved",
                    chore_id,
                )
                continue

            due_str = chore_info.get("due_date")
            if not due_str:
                LOGGER.debug(
                    "Chore '%s' has no due_date; checking to confirm it isn't overdue; then skipping if not",
                    chore_id,
                )
                # If it has no due date, but is overdue, it should be marked as pending
                if chore_info.get("state") == CHORE_STATE_OVERDUE:
                    self._process_chore_state(kid_id, chore_id, CHORE_STATE_PENDING)
                continue

            try:
                due_date = dt_util.parse_datetime(due_str)
                if due_date is None:
                    raise ValueError("Parsed datetime is None")
                due_date = dt_util.as_utc(due_date)
                LOGGER.debug(
                    "Chore '%s' due_date parsed as %s", chore_id, due_date.isoformat()
                )
            except Exception as err:
                LOGGER.error(
                    "Error parsing due_date '%s' for chore '%s': %s",
                    due_str,
                    chore_id,
                    err,
                )
                continue

            # Check if today is an applicable day.
            applicable_days = chore_info.get(
                CONF_APPLICABLE_DAYS, DEFAULT_APPLICABLE_DAYS
            )
            if applicable_days:
                weekday_mapping = {
                    0: "mon",
                    1: "tue",
                    2: "wed",
                    3: "thu",
                    4: "fri",
                    5: "sat",
                    6: "sun",
                }
                today_weekday = weekday_mapping[dt_util.as_local(now).weekday()]
                if today_weekday not in applicable_days:
                    LOGGER.debug(
                        "Chore '%s' is not scheduled for today (today=%s, applicable=%s)",
                        chore_id,
                        today_weekday,
                        applicable_days,
                    )
                    continue

            LOGGER.debug(
                "Chore '%s': now=%s, due_date=%s",
                chore_id,
                now.isoformat(),
                due_date.isoformat(),
            )
            if now < due_date:
                # Not past due date, but before resetting the state back to pending, check if global state is currently overdue
                for kid_id in assigned_kids:
                    if chore_id in kid_info.get("overdue_chores", []):
                        self._process_chore_state(kid_id, chore_id, CHORE_STATE_PENDING)
                        LOGGER.debug(
                            "Chore '%s' status is overdue but not yet due; cleared overdue flags",
                            chore_id,
                        )

                continue

            # Handling for overdue is the same for shared and non-shared chores
            # Status and global status will be determined by the chore state processor
            assigned_kids = chore_info.get("assigned_kids", [])
            for kid_id in assigned_kids:
                kid_info = self.kids_data.get(kid_id, {})

                # Skip if kid already claimed/approved on the chore.
                if chore_id in kid_info.get(
                    "claimed_chores", []
                ) or chore_id in kid_info.get("approved_chores", []):
                    continue

                # Mark chore as overdue for this kid.
                self._process_chore_state(kid_id, chore_id, CHORE_STATE_OVERDUE)

                # Check notification timestamp.
                last_notif_str = kid_info["overdue_notifications"].get(chore_id)
                notify = False
                if last_notif_str:
                    try:
                        last_dt = dt_util.parse_datetime(last_notif_str)
                        if (
                            (not last_dt)
                            or (last_dt < due_date)
                            or ((now - last_dt) >= timedelta(hours=24))
                        ):
                            notify = True
                        else:
                            LOGGER.debug(
                                "Chore '%s' for kid '%s' already notified within 24 hours",
                                chore_id,
                                kid_id,
                            )
                    except Exception as err:
                        LOGGER.error(
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
                    kid_info["overdue_notifications"][chore_id] = now.isoformat()
                    extra_data = {"kid_id": kid_id, "chore_id": chore_id}
                    actions = [
                        {
                            "action": f"{ACTION_APPROVE_CHORE}|{kid_id}|{chore_id}",
                            "title": ACTION_TITLE_APPROVE,
                        },
                        {
                            "action": f"{ACTION_DISAPPROVE_CHORE}|{kid_id}|{chore_id}",
                            "title": ACTION_TITLE_DISAPPROVE,
                        },
                        {
                            "action": f"{ACTION_REMIND_30}|{kid_id}|{chore_id}",
                            "title": ACTION_TITLE_REMIND_30,
                        },
                    ]
                    LOGGER.debug(
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
                            message=f"{self._get_kid_name_by_id(kid_id)}'s chore '{chore_info.get('name', 'Unnamed Chore')}' is overdue",
                            actions=actions,
                            extra_data=extra_data,
                        )
                    )
        LOGGER.debug("Overdue check completed")

    async def _reset_all_chore_counts(self, now: datetime):
        """Trigger resets based on the current time for all frequencies."""
        await self._handle_recurring_chore_resets(now)
        await self._reset_daily_reward_statuses()
        await self._check_overdue_chores()

        for kid in self.kids_data.values():
            kid["today_chore_approvals"] = {}

    async def _handle_recurring_chore_resets(self, now: datetime):
        """Handle recurring resets for daily, weekly, and monthly frequencies."""

        await self._reschedule_recurring_chores(now)

        # Daily
        if now.hour == DEFAULT_DAILY_RESET_TIME.get("hour", 0):
            await self._reset_chore_counts(FREQUENCY_DAILY, now)

        # Weekly
        if now.weekday() == DEFAULT_WEEKLY_RESET_DAY:
            await self._reset_chore_counts(FREQUENCY_WEEKLY, now)

        # Monthly
        days_in_month = monthrange(now.year, now.month)[1]
        reset_day = min(DEFAULT_MONTHLY_RESET_DAY, days_in_month)
        if now.day == reset_day:
            await self._reset_chore_counts(FREQUENCY_MONTHLY, now)

    async def _reset_chore_counts(self, frequency: str, now: datetime):
        """Reset chore counts and statuses based on the recurring frequency."""
        # Reset counters on kids
        for kid_info in self.kids_data.values():
            if frequency == FREQUENCY_DAILY:
                kid_info["completed_chores_today"] = 0
                kid_info["points_earned_today"] = 0.0
            elif frequency == FREQUENCY_WEEKLY:
                kid_info["completed_chores_weekly"] = 0
                kid_info["points_earned_weekly"] = 0.0
            elif frequency == FREQUENCY_MONTHLY:
                kid_info["completed_chores_monthly"] = 0
                kid_info["points_earned_monthly"] = 0.0

        LOGGER.info(f"{frequency.capitalize()} chore counts have been reset")

        # If daily reset -> reset statuses
        if frequency == FREQUENCY_DAILY:
            await self._reset_daily_chore_statuses([frequency])

    async def _reschedule_recurring_chores(self, now: datetime):
        """For chores with the given recurring frequency, reschedule due date if they are approved and past due."""

        for chore_id, chore_info in self.chores_data.items():
            # Only consider chores with a recurring frequency (any of the three) and a defined due_date:
            if chore_info.get("recurring_frequency") not in (
                FREQUENCY_DAILY,
                FREQUENCY_WEEKLY,
                FREQUENCY_BIWEEKLY,
                FREQUENCY_MONTHLY,
                FREQUENCY_CUSTOM,
            ):
                continue
            if not chore_info.get("due_date"):
                continue

            try:
                due_date = dt_util.parse_datetime(
                    chore_info["due_date"]
                ) or datetime.fromisoformat(chore_info["due_date"])
            except Exception as e:
                LOGGER.warning("Error parsing due_date for chore '%s': %s", chore_id, e)
                continue

            # If the due date is in the past and the chore is approved or approved_in_part
            if now > due_date and chore_info.get("state") in [
                CHORE_STATE_APPROVED,
                CHORE_STATE_APPROVED_IN_PART,
            ]:
                # Reschedule the chore
                self._reschedule_next_due_date(chore_info)
                LOGGER.debug(
                    "Rescheduled recurring chore '%s'", chore_info.get("name", chore_id)
                )

                # Reset the chore's state for each kid to pending using central processor
                for kid_id in chore_info.get("assigned_kids", []):
                    if kid_id:
                        self._process_chore_state(kid_id, chore_id, CHORE_STATE_PENDING)

        self._persist()
        self.async_set_updated_data(self._data)
        LOGGER.debug("Daily rescheduling of recurring chores complete")

    async def _reset_daily_chore_statuses(self, target_freqs: list[str]):
        """Reset chore statuses and clear approved/claimed chores for chores with these freq."""
        LOGGER.info("Executing _reset_daily_chore_statuses")

        now = dt_util.utcnow()
        for chore_id, chore_info in self.chores_data.items():
            frequency = chore_info.get("recurring_frequency", FREQUENCY_NONE)
            # Only consider chores whose frequency is either in target_freqs or FREQUENCY_NONE.
            if frequency in target_freqs or frequency == FREQUENCY_NONE:
                due_date_str = chore_info.get("due_date")
                if due_date_str:
                    try:
                        due_date = dt_util.parse_datetime(
                            due_date_str
                        ) or datetime.fromisoformat(due_date_str)
                        # If the due date has not yet been reached, skip resetting this chore.
                        if now < due_date:
                            continue
                    except Exception as e:
                        LOGGER.warning(
                            "Error parsing due_date '%s' for chore '%s': %s",
                            due_date_str,
                            chore_id,
                            e,
                        )
                # If no due date or the due date has passed, then reset the chore state
                if chore_info["state"] not in [
                    CHORE_STATE_PENDING,
                    CHORE_STATE_OVERDUE,
                ]:
                    previous_state = chore_info["state"]
                    for kid_id in chore_info.get("assigned_kids", []):
                        if kid_id:
                            self._process_chore_state(
                                kid_id, chore_id, CHORE_STATE_PENDING
                            )
                    LOGGER.debug(
                        "Resetting chore '%s' from '%s' to '%s'",
                        chore_id,
                        previous_state,
                        CHORE_STATE_PENDING,
                    )

        # clear pending chore approvals
        target_chore_ids = [
            chore_id
            for chore_id, chore_info in self.chores_data.items()
            if chore_info.get("recurring_frequency") in target_freqs
        ]
        self._data[DATA_PENDING_CHORE_APPROVALS] = [
            ap
            for ap in self._data[DATA_PENDING_CHORE_APPROVALS]
            if ap["chore_id"] not in target_chore_ids
        ]

        self._persist()

    async def _reset_daily_reward_statuses(self):
        """Reset all kids' reward states daily."""
        # Remove from global pending reward approvals
        self._data[DATA_PENDING_REWARD_APPROVALS] = []
        LOGGER.debug("Cleared all pending reward approvals globally")

        # For each kid, clear pending/approved reward lists to reflect daily reset
        for kid_id, kid_info in self.kids_data.items():
            kid_info["pending_rewards"] = []
            kid_info["redeemed_rewards"] = []

            LOGGER.debug(
                "Cleared daily reward statuses for kid ID '%s' (%s)",
                kid_id,
                kid_info.get("name", "Unknown"),
            )

        self._persist()
        self.async_set_updated_data(self._data)
        LOGGER.info("Daily reward statuses have been reset")

    def _handle_recurring_chore(self, chore_info: dict[str, Any]):
        """If chore is daily/weekly/monthly, reset & set next due date (no due_date set)."""
        freq = chore_info.get("recurring_frequency", FREQUENCY_NONE)
        if freq == FREQUENCY_NONE:
            return
        # daily, weekly, monthly logic if chore lacks a due_date
        now = dt_util.utcnow()
        if freq == FREQUENCY_DAILY:
            next_due = now + timedelta(days=1)
        elif freq == FREQUENCY_WEEKLY:
            next_due = now + timedelta(weeks=1)
        elif freq == FREQUENCY_MONTHLY:
            days_in_month = monthrange(now.year, now.month)[1]
            reset_day = min(DEFAULT_MONTHLY_RESET_DAY, days_in_month)
            # handle logic
            next_due = now.replace(day=reset_day)
            if next_due <= now:
                pass
        else:
            return

        chore_info["due_date"] = next_due.isoformat()

    def _reschedule_next_due_date(self, chore_info: dict[str, Any]):
        """Reschedule the next due date based on the recurring frequency."""
        freq = chore_info.get("recurring_frequency", FREQUENCY_NONE)
        due_date_str = chore_info.get("due_date")
        if not freq or freq == FREQUENCY_NONE or not due_date_str:
            LOGGER.debug(
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
            LOGGER.warning("Unable to parse due_date '%s'", due_date_str)
            return

        if freq == FREQUENCY_DAILY:
            next_due = original_due + timedelta(days=1)
        elif freq == FREQUENCY_WEEKLY:
            next_due = original_due + timedelta(weeks=1)
        elif freq == FREQUENCY_BIWEEKLY:
            next_due = original_due + timedelta(weeks=2)
        elif freq == FREQUENCY_MONTHLY:
            next_due = self._add_one_month(original_due)
        elif freq == FREQUENCY_CUSTOM:
            custom_interval = chore_info.get("custom_interval")
            custom_unit = chore_info.get("custom_interval_unit")
            if custom_interval is None or custom_unit not in [
                "days",
                "weeks",
                "months",
            ]:
                LOGGER.warning(
                    "Custom frequency set but custom_interval or unit invalid for chore '%s'",
                    chore_info.get("name"),
                )
                return
            if custom_unit == "days":
                next_due = original_due + timedelta(days=custom_interval)
            elif custom_unit == "weeks":
                next_due = original_due + timedelta(weeks=custom_interval)
            elif custom_unit == "months":
                next_due = self._add_months(original_due, custom_interval)
        else:
            return

        now = dt_util.utcnow()
        while next_due <= now:
            if freq == FREQUENCY_DAILY:
                next_due += timedelta(days=1)
            elif freq == FREQUENCY_WEEKLY:
                next_due += timedelta(weeks=1)
            elif freq == FREQUENCY_BIWEEKLY:
                next_due += timedelta(weeks=2)
            elif freq == FREQUENCY_MONTHLY:
                next_due = self._add_one_month(next_due)
            elif freq == FREQUENCY_CUSTOM:
                if custom_unit == "days":
                    next_due += timedelta(days=custom_interval)
                elif custom_unit == "weeks":
                    next_due += timedelta(weeks=custom_interval)
                elif custom_unit == "months":
                    next_due = self._add_months(next_due, custom_interval)

        applicable_days = chore_info.get(CONF_APPLICABLE_DAYS, DEFAULT_APPLICABLE_DAYS)
        if applicable_days:
            weekday_mapping = {i: key for i, key in enumerate(WEEKDAY_OPTIONS.keys())}
            # Increment next_due day-by-day until its weekday is in applicable_days.
            while weekday_mapping[next_due.weekday()] not in applicable_days:
                next_due += timedelta(days=1)

        chore_info["due_date"] = next_due.isoformat()

        # Update config_entry.options for this chore so that the new due_date is visible in Options
        updated_options = dict(self.config_entry.options)
        if DATA_CHORES in updated_options:
            chores_conf = dict(updated_options[DATA_CHORES])
            if chore_info["internal_id"] in chores_conf:
                # Update only the due_date in the static part:
                chores_conf[chore_info["internal_id"]]["due_date"] = (
                    next_due.isoformat()
                )
            else:
                chores_conf[chore_info["internal_id"]] = {
                    "due_date": next_due.isoformat()
                }
            updated_options[DATA_CHORES] = chores_conf
            new_data = dict(self.config_entry.data)
            new_data["last_change"] = dt_util.utcnow().isoformat()

            # Push the new options to the config entry.
            result = self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data, options=updated_options
            )
            if asyncio.iscoroutine(result):
                self.hass.async_create_task(result)

    def _add_one_month(self, dt_in: datetime) -> datetime:
        """Add one month to a datetime, preserving day if possible."""
        year = dt_in.year
        month = dt_in.month
        day = dt_in.day
        new_month = month + 1
        new_year = year
        if new_month > 12:
            new_month = 1
            new_year += 1
        days_in_new_month = monthrange(new_year, new_month)[1]
        if day > days_in_new_month:
            day = days_in_new_month
        return dt_in.replace(year=new_year, month=new_month, day=day)

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

    # Skip Chore Due Date
    def skip_chore_due_date(self, chore_id: str) -> None:
        """Skip the current due date of a recurring chore and reschedule it."""
        chore = self.chores_data.get(chore_id)
        if not chore:
            raise HomeAssistantError(f"Chore with ID '{chore_id}' not found.")

        if chore.get("recurring_frequency", FREQUENCY_NONE) == FREQUENCY_NONE:
            raise HomeAssistantError(
                f"Chore '{chore.get('name', chore_id)}' does not have a recurring frequency."
            )
        if not chore.get("due_date"):
            raise HomeAssistantError(
                f"Chore '{chore.get('name', chore_id)}' does not have a due date set."
            )

        if chore.get("state") != CHORE_STATE_PENDING:
            for kid in self.kids_data.values():
                kid["claimed_chores"] = [
                    item for item in kid.get("claimed_chores", []) if item != chore_id
                ]
                kid["approved_chores"] = [
                    item for item in kid.get("approved_chores", []) if item != chore_id
                ]
                kid["overdue_chores"] = [
                    item for item in kid.get("overdue_chores", []) if item != chore_id
                ]

        # Compute the next due date and update the chore options/config.
        self._reschedule_next_due_date(chore)
        # Set state to pending so it will be ready for action again.
        chore["state"] = CHORE_STATE_PENDING

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

            # In either case, reschedule chore.
            # This may need another look.  Is it really possible to reschedule just for one kid.
            self._reschedule_next_due_date(chore)

            if kid_id:
                # Reset only for the given kid.
                kid = self.kids_data.get(kid_id)
                if not kid:
                    raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")
                if kid_id not in chore.get("assigned_kids", []):
                    raise HomeAssistantError(
                        f"Kid '{kid.get('name', kid_id)}' is not assigned to chore '{chore.get('name', chore_id)}'."
                    )
                # Set state for kid assigned to the chore:
                self._process_chore_state(kid_id, chore_id, CHORE_STATE_PENDING)
            else:
                # Reset this chore for all kids.
                for kid_id in chore.get("assigned_kids", []):
                    if kid_id:
                        self._process_chore_state(kid_id, chore_id, CHORE_STATE_PENDING)

        elif kid_id:
            # Kid-only reset: reset all overdue chores for the specified kid.
            kid = self.kids_data.get(kid_id)
            if not kid:
                raise HomeAssistantError(f"Kid with ID '{kid_id}' not found.")
            for cid, chore in self.chores_data.items():
                if kid_id in chore.get("assigned_kids", []):
                    if cid in kid.get("overdue_chores", []):
                        # Reschedule chore
                        self._reschedule_next_due_date(chore)
                        # Change to Pending state
                        self._process_chore_state(kid_id, cid, CHORE_STATE_PENDING)

        else:
            # Global reset: Reset all chores that are overdue.
            for kid_id, kid in self.kids_data.items():
                for cid, chore in self.chores_data.items():
                    if kid_id in chore.get("assigned_kids", []):
                        if cid in kid.get("overdue_chores", []):
                            # Reschedule chore
                            self._reschedule_next_due_date(chore)
                            # Change to Pending state
                            self._process_chore_state(kid_id, cid, CHORE_STATE_PENDING)

        self._persist()
        self.async_set_updated_data(self._data)

    # Persist new due dates on config entries
    async def _update_all_chore_due_dates_in_config(self) -> None:
        updated_options = dict(self.config_entry.options)
        chores_conf = dict(updated_options.get(DATA_CHORES, {}))
        for chore_id, chore in self.chores_data.items():
            if "due_date" in chore:
                existing_options = dict(chores_conf.get(chore_id, {}))
                existing_options["due_date"] = chore["due_date"]
                chores_conf[chore_id] = existing_options
        updated_options[DATA_CHORES] = chores_conf
        new_data = dict(self.config_entry.data)
        new_data["last_change"] = dt_util.utcnow().isoformat()
        await self.hass.config_entries.async_update_entry(
            self.config_entry, data=new_data, options=updated_options
        )

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
        """Send a persistent notification to a user if possible; fallback to a general persistent notification if the user is not found or not set."""
        hass = self.hass
        if not user_id:
            # If no user_id is provided, use a general notification
            LOGGER.debug(
                "No user_id provided. Sending a general persistent notification"
            )
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": notification_id,
                },
                blocking=True,
            )
            return

        try:
            user_obj: User = await hass.auth.async_get_user(user_id)
            if not user_obj:
                LOGGER.warning(
                    "User with ID '%s' not found. Sending fallback persistent notification",
                    user_id,
                )
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": title,
                        "message": message,
                        "notification_id": notification_id,
                    },
                    blocking=True,
                )
                return

            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": notification_id,
                },
                blocking=True,
            )
        except Exception as err:
            LOGGER.warning(
                "Failed to send user-specific notification to user_id='%s': %s. Fallback to persistent_notification",
                user_id,
                err,
            )
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": notification_id,
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
        if not kid_info.get("enable_notifications", True):
            LOGGER.debug("Notifications disabled for kid '%s'", kid_id)
            return
        mobile_enabled = kid_info.get(CONF_ENABLE_MOBILE_NOTIFICATIONS, True)
        persistent_enabled = kid_info.get(CONF_ENABLE_PERSISTENT_NOTIFICATIONS, True)
        mobile_notify_service = kid_info.get(CONF_MOBILE_NOTIFY_SERVICE, "")
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
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": f"kid_{kid_id}",
                },
                blocking=True,
            )
        else:
            LOGGER.debug("No notification method configured for kid '%s'", kid_id)

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
            if kid_id not in parent_info.get("associated_kids", []):
                continue
            if not parent_info.get("enable_notifications", True):
                LOGGER.debug("Notifications disabled for parent '%s'", parent_id)
                continue
            mobile_enabled = parent_info.get(CONF_ENABLE_MOBILE_NOTIFICATIONS, True)
            persistent_enabled = parent_info.get(
                CONF_ENABLE_PERSISTENT_NOTIFICATIONS, True
            )
            mobile_notify_service = parent_info.get(CONF_MOBILE_NOTIFY_SERVICE, "")
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
                    "persistent_notification",
                    "create",
                    {
                        "title": title,
                        "message": message,
                        "notification_id": f"parent_{parent_id}",
                    },
                    blocking=True,
                )
            else:
                LOGGER.debug(
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
        LOGGER.info(
            "Scheduling reminder for kid '%s', chore '%s', reward '%s' in %d minutes",
            kid_id,
            chore_id,
            reward_id,
            minutes,
        )
        await asyncio.sleep(minutes * 60)

        kid_info = self.kids_data.get(kid_id)
        if not kid_info:
            LOGGER.warning("Kid with ID '%s' not found during reminder check", kid_id)
            return

        if chore_id:
            chore_info = self.chores_data.get(chore_id)
            if not chore_info:
                LOGGER.warning(
                    "Chore with ID '%s' not found during reminder check", chore_id
                )
                return
            # Only resend if the chore is still in a pending-like state.
            if chore_info.get("state") not in [
                CHORE_STATE_PENDING,
                CHORE_STATE_CLAIMED,
                CHORE_STATE_OVERDUE,
            ]:
                LOGGER.info(
                    "Chore '%s' is no longer pending approval; no reminder sent",
                    chore_id,
                )
                return
            actions = [
                {
                    "action": f"{ACTION_APPROVE_CHORE}|{kid_id}|{chore_id}",
                    "title": ACTION_TITLE_APPROVE,
                },
                {
                    "action": f"{ACTION_DISAPPROVE_CHORE}|{kid_id}|{chore_id}",
                    "title": ACTION_TITLE_DISAPPROVE,
                },
                {
                    "action": f"{ACTION_REMIND_30}|{kid_id}|{chore_id}",
                    "title": ACTION_TITLE_REMIND_30,
                },
            ]
            extra_data = {"kid_id": kid_id, "chore_id": chore_id}
            await self._notify_parents(
                kid_id,
                title="KidsChores: Reminder for Pending Chore",
                message=f"Reminder: {kid_info.get('name', 'A kid')} has '{chore_info.get('name', 'Unnamed Chore')}' chore pending approval.",
                actions=actions,
                extra_data=extra_data,
            )
            LOGGER.info("Resent reminder for chore '%s' for kid '%s'", chore_id, kid_id)
        elif reward_id:
            # Check if the reward is still pending approval.
            if reward_id not in kid_info.get("pending_rewards", []):
                LOGGER.info(
                    "Reward '%s' is no longer pending approval for kid '%s'; no reminder sent",
                    reward_id,
                    kid_id,
                )
                return
            actions = [
                {
                    "action": f"{ACTION_APPROVE_REWARD}|{kid_id}|{reward_id}",
                    "title": ACTION_TITLE_APPROVE,
                },
                {
                    "action": f"{ACTION_DISAPPROVE_REWARD}|{kid_id}|{reward_id}",
                    "title": ACTION_TITLE_DISAPPROVE,
                },
                {
                    "action": f"{ACTION_REMIND_30}|{kid_id}|{reward_id}",
                    "title": ACTION_TITLE_REMIND_30,
                },
            ]
            extra_data = {"kid_id": kid_id, "reward_id": reward_id}
            reward = self.rewards_data.get(reward_id, {})
            reward_name = reward.get("name", "the reward")
            await self._notify_parents(
                kid_id,
                title="KidsChores: Reminder for Pending Reward",
                message=f"Reminder: {kid_info.get('name', 'A kid')} has '{reward_name}' reward pending approval.",
                actions=actions,
                extra_data=extra_data,
            )
            LOGGER.info(
                "Resent reminder for reward '%s' for kid '%s'", reward_id, kid_id
            )
        else:
            LOGGER.warning("No chore_id or reward_id provided for reminder action")

    # -------------------------------------------------------------------------------------
    # Storage
    # -------------------------------------------------------------------------------------

    def _persist(self):
        """Save to persistent storage."""
        self.storage_manager.set_data(self._data)
        self.hass.add_job(self.storage_manager.async_save)

    # -------------------------------------------------------------------------------------
    # Internal Helper for kid <-> name lookups
    # -------------------------------------------------------------------------------------

    def _get_kid_id_by_name(self, kid_name: str) -> Optional[str]:
        """Help function to get kid_id by kid_name."""
        for kid_id, k_info in self.kids_data.items():
            if k_info.get("name") == kid_name:
                return kid_id
        return None

    def _get_kid_name_by_id(self, kid_id: str) -> Optional[str]:
        """Help function to get kid_name by kid_id."""
        kid_info = self.kids_data.get(kid_id)
        if kid_info:
            return kid_info.get("name")
        return None
