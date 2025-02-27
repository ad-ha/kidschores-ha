# File: config_flow.py
"""Multi-step config flow for the KidsChores integration, storing entities by internal_id.

Ensures that all add/edit/delete operations reference entities via internal_id for consistency.
"""

import datetime
import uuid
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util
from typing import Any, Optional

from .const import (
    ACHIEVEMENT_TYPE_STREAK,
    CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW,
    CONF_APPLICABLE_DAYS,
    CONF_ACHIEVEMENTS,
    CONF_BADGES,
    CONF_CHALLENGES,
    CONF_CHORES,
    CONF_KIDS,
    CONF_NOTIFY_ON_APPROVAL,
    CONF_NOTIFY_ON_CLAIM,
    CONF_NOTIFY_ON_DISAPPROVAL,
    CONF_PARENTS,
    CONF_PENALTIES,
    CONF_POINTS_ICON,
    CONF_POINTS_LABEL,
    CONF_REWARDS,
    CONF_BONUSES,
    DEFAULT_APPLICABLE_DAYS,
    DEFAULT_NOTIFY_ON_APPROVAL,
    DEFAULT_NOTIFY_ON_CLAIM,
    DEFAULT_NOTIFY_ON_DISAPPROVAL,
    DEFAULT_POINTS_ICON,
    DEFAULT_POINTS_LABEL,
    FREQUENCY_CUSTOM,
    DOMAIN,
    LOGGER,
)
from .flow_helpers import (
    build_points_schema,
    build_kid_schema,
    build_parent_schema,
    build_chore_schema,
    build_badge_schema,
    build_reward_schema,
    build_penalty_schema,
    build_achievement_schema,
    build_challenge_schema,
    ensure_utc_datetime,
    build_bonus_schema,
)


class KidsChoresConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow for KidsChores with internal_id-based entity management."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._kids_temp: dict[str, dict[str, Any]] = {}
        self._parents_temp: dict[str, dict[str, Any]] = {}
        self._chores_temp: dict[str, dict[str, Any]] = {}
        self._badges_temp: dict[str, dict[str, Any]] = {}
        self._rewards_temp: dict[str, dict[str, Any]] = {}
        self._achievements_temp: dict[str, dict[str, Any]] = {}
        self._challenges_temp: dict[str, dict[str, Any]] = {}
        self._penalties_temp: dict[str, dict[str, Any]] = {}
        self._bonuses_temp: dict[str, dict[str, Any]] = {}

        self._kid_count: int = 0
        self._parents_count: int = 0
        self._chore_count: int = 0
        self._badge_count: int = 0
        self._reward_count: int = 0
        self._achievement_count: int = 0
        self._challenge_count: int = 0
        self._penalty_count: int = 0
        self._bonus_count: int = 0

        self._kid_index: int = 0
        self._parents_index: int = 0
        self._chore_index: int = 0
        self._badge_index: int = 0
        self._reward_index: int = 0
        self._achievement_index: int = 0
        self._challenge_index: int = 0
        self._penalty_index: int = 0
        self._bonus_index: int = 0

    async def async_step_user(self, user_input: Optional[dict[str, Any]] = None):
        """Start the config flow with an intro step."""

        # Check if there's an existing KidsChores entry
        if any(self._async_current_entries()):
            return self.async_abort(reason="single_instance_allowed")

        # Continue your normal flow
        return await self.async_step_intro()

    async def async_step_intro(self, user_input=None):
        """Intro / welcome step. Press Next to continue."""
        if user_input is not None:
            return await self.async_step_points_label()

        return self.async_show_form(step_id="intro", data_schema=vol.Schema({}))

    async def async_step_points_label(self, user_input=None):
        """Let the user define a custom label for points."""
        errors = {}

        if user_input is not None:
            points_label = user_input.get(CONF_POINTS_LABEL, DEFAULT_POINTS_LABEL)
            points_icon = user_input.get(CONF_POINTS_ICON, DEFAULT_POINTS_ICON)

            self._data[CONF_POINTS_LABEL] = points_label
            self._data[CONF_POINTS_ICON] = points_icon

            return await self.async_step_kid_count()

        points_schema = build_points_schema(
            default_label=DEFAULT_POINTS_LABEL, default_icon=DEFAULT_POINTS_ICON
        )

        return self.async_show_form(
            step_id="points_label", data_schema=points_schema, errors=errors
        )

    # --------------------------------------------------------------------------
    # KIDS
    # --------------------------------------------------------------------------
    async def async_step_kid_count(self, user_input=None):
        """Ask how many kids to define initially."""
        errors = {}
        if user_input is not None:
            try:
                self._kid_count = int(user_input["kid_count"])
                if self._kid_count < 0:
                    raise ValueError
                if self._kid_count == 0:
                    return await self.async_step_chore_count()
                self._kid_index = 0
                return await self.async_step_kids()
            except ValueError:
                errors["base"] = "invalid_kid_count"

        schema = vol.Schema({vol.Required("kid_count", default=1): vol.Coerce(int)})
        return self.async_show_form(
            step_id="kid_count", data_schema=schema, errors=errors
        )

    async def async_step_kids(self, user_input=None):
        """Collect each kid's info using internal_id as the primary key.

        Store in self._kids_temp as a dict keyed by internal_id.
        """
        errors = {}
        if user_input is not None:
            kid_name = user_input["kid_name"].strip()
            ha_user_id = user_input.get("ha_user") or ""
            enable_mobile_notifications = user_input.get(
                "enable_mobile_notifications", True
            )
            notify_service = user_input.get("mobile_notify_service") or ""
            enable_persist = user_input.get("enable_persistent_notifications", True)

            if not kid_name:
                errors["kid_name"] = "invalid_kid_name"
            elif any(
                kid_data["name"] == kid_name for kid_data in self._kids_temp.values()
            ):
                errors["kid_name"] = "duplicate_kid"
            else:
                internal_id = user_input.get("internal_id", str(uuid.uuid4()))
                self._kids_temp[internal_id] = {
                    "name": kid_name,
                    "ha_user_id": ha_user_id,
                    "enable_notifications": enable_mobile_notifications,
                    "mobile_notify_service": notify_service,
                    "use_persistent_notifications": enable_persist,
                    "internal_id": internal_id,
                }
                LOGGER.debug("Added kid: %s with ID: %s", kid_name, internal_id)

            self._kid_index += 1
            if self._kid_index >= self._kid_count:
                return await self.async_step_parent_count()
            return await self.async_step_kids()

        # Retrieve HA users for linking
        users = await self.hass.auth.async_get_users()
        kid_schema = build_kid_schema(
            self.hass,
            users=users,
            default_kid_name="",
            default_ha_user_id=None,
            default_enable_mobile_notifications=False,
            default_mobile_notify_service=None,
            default_enable_persistent_notifications=False,
        )
        return self.async_show_form(
            step_id="kids", data_schema=kid_schema, errors=errors
        )

    # --------------------------------------------------------------------------
    # PARENTS
    # --------------------------------------------------------------------------
    async def async_step_parent_count(self, user_input=None):
        """Ask how many parents to define initially."""
        errors = {}
        if user_input is not None:
            try:
                self._parents_count = int(user_input["parent_count"])
                if self._parents_count < 0:
                    raise ValueError
                if self._parents_count == 0:
                    return await self.async_step_chore_count()
                self._parents_index = 0
                return await self.async_step_parents()
            except ValueError:
                errors["base"] = "invalid_parent_count"

        schema = vol.Schema({vol.Required("parent_count", default=1): vol.Coerce(int)})
        return self.async_show_form(
            step_id="parent_count", data_schema=schema, errors=errors
        )

    async def async_step_parents(self, user_input=None):
        """Collect each parent's info using internal_id as the primary key.

        Store in self._parents_temp as a dict keyed by internal_id.
        """
        errors = {}
        if user_input is not None:
            parent_name = user_input["parent_name"].strip()
            ha_user_id = user_input.get("ha_user_id") or ""
            associated_kids = user_input.get("associated_kids", [])
            enable_mobile_notifications = user_input.get(
                "enable_mobile_notifications", True
            )
            notify_service = user_input.get("mobile_notify_service") or ""
            enable_persist = user_input.get("enable_persistent_notifications", True)

            if not parent_name:
                errors["parent_name"] = "invalid_parent_name"
            elif any(
                parent_data["name"] == parent_name
                for parent_data in self._parents_temp.values()
            ):
                errors["parent_name"] = "duplicate_parent"
            else:
                internal_id = user_input.get("internal_id", str(uuid.uuid4()))
                self._parents_temp[internal_id] = {
                    "name": parent_name,
                    "ha_user_id": ha_user_id,
                    "associated_kids": associated_kids,
                    "enable_notifications": enable_mobile_notifications,
                    "mobile_notify_service": notify_service,
                    "use_persistent_notifications": enable_persist,
                    "internal_id": internal_id,
                }
                LOGGER.debug("Added parent: %s with ID: %s", parent_name, internal_id)

            self._parents_index += 1
            if self._parents_index >= self._parents_count:
                return await self.async_step_chore_count()
            return await self.async_step_parents()

        # Retrieve kids for association from _kids_temp
        kids_dict = {
            kid_data["name"]: kid_id for kid_id, kid_data in self._kids_temp.items()
        }

        users = await self.hass.auth.async_get_users()

        parent_schema = build_parent_schema(
            self.hass,
            users=users,
            kids_dict=kids_dict,
            default_parent_name="",
            default_ha_user_id=None,
            default_associated_kids=[],
            default_enable_mobile_notifications=False,
            default_mobile_notify_service=None,
            default_enable_persistent_notifications=False,
            internal_id=None,
        )
        return self.async_show_form(
            step_id="parents", data_schema=parent_schema, errors=errors
        )

    # --------------------------------------------------------------------------
    # CHORES
    # --------------------------------------------------------------------------
    async def async_step_chore_count(self, user_input=None):
        """Ask how many chores to define."""
        errors = {}
        if user_input is not None:
            try:
                self._chore_count = int(user_input["chore_count"])
                if self._chore_count < 0:
                    raise ValueError
                if self._chore_count == 0:
                    return await self.async_step_badge_count()
                self._chore_index = 0
                return await self.async_step_chores()
            except ValueError:
                errors["base"] = "invalid_chore_count"

        schema = vol.Schema({vol.Required("chore_count", default=1): vol.Coerce(int)})
        return self.async_show_form(
            step_id="chore_count", data_schema=schema, errors=errors
        )

    async def async_step_chores(self, user_input=None):
        """Collect chore details using internal_id as the primary key.

        Store in self._chores_temp as a dict keyed by internal_id.
        """
        errors = {}

        if user_input is not None:
            chore_name = user_input["chore_name"].strip()
            internal_id = user_input.get("internal_id", str(uuid.uuid4()))

            if user_input.get("due_date"):
                raw_due = user_input["due_date"]
                try:
                    due_date_str = ensure_utc_datetime(self.hass, raw_due)
                    due_dt = dt_util.parse_datetime(due_date_str)
                    if due_dt and due_dt < dt_util.utcnow():
                        errors["due_date"] = "due_date_in_past"
                except ValueError:
                    errors["due_date"] = "invalid_due_date"
                    due_date_str = None
            else:
                due_date_str = None

            if not chore_name:
                errors["chore_name"] = "invalid_chore_name"
            elif any(
                chore_data["name"] == chore_name
                for chore_data in self._chores_temp.values()
            ):
                errors["chore_name"] = "duplicate_chore"

            if errors:
                kids_dict = {
                    kid_data["name"]: kid_id
                    for kid_id, kid_data in self._kids_temp.items()
                }
                # Re-show the form with the user's current input and errors:
                default_data = user_input.copy()
                return self.async_show_form(
                    step_id="chores",
                    data_schema=build_chore_schema(kids_dict, default_data),
                    errors=errors,
                )

            if user_input.get("recurring_frequency") != FREQUENCY_CUSTOM:
                user_input.pop("custom_interval", None)
                user_input.pop("custom_interval_unit", None)

            # If no errors, store the chore
            self._chores_temp[internal_id] = {
                "name": chore_name,
                "default_points": user_input["default_points"],
                "partial_allowed": user_input["partial_allowed"],
                "shared_chore": user_input["shared_chore"],
                "assigned_kids": user_input["assigned_kids"],
                "allow_multiple_claims_per_day": user_input[
                    "allow_multiple_claims_per_day"
                ],
                "description": user_input.get("chore_description", ""),
                "chore_labels": user_input.get("chore_labels", []),
                "icon": user_input.get("icon", ""),
                "recurring_frequency": user_input.get("recurring_frequency", "none"),
                "custom_interval": user_input.get("custom_interval"),
                "custom_interval_unit": user_input.get("custom_interval_unit"),
                "due_date": due_date_str,
                "applicable_days": user_input.get(
                    CONF_APPLICABLE_DAYS, DEFAULT_APPLICABLE_DAYS
                ),
                "notify_on_claim": user_input.get(
                    CONF_NOTIFY_ON_CLAIM, DEFAULT_NOTIFY_ON_CLAIM
                ),
                "notify_on_approval": user_input.get(
                    CONF_NOTIFY_ON_APPROVAL, DEFAULT_NOTIFY_ON_APPROVAL
                ),
                "notify_on_disapproval": user_input.get(
                    CONF_NOTIFY_ON_DISAPPROVAL, DEFAULT_NOTIFY_ON_DISAPPROVAL
                ),
                "internal_id": internal_id,
            }
            LOGGER.debug("Added chore: %s with ID: %s", chore_name, internal_id)

            self._chore_index += 1
            if self._chore_index >= self._chore_count:
                return await self.async_step_badge_count()
            return await self.async_step_chores()

        # Use flow_helpers.build_chore_schema, passing the current kids
        kids_dict = {
            kid_data["name"]: kid_id for kid_id, kid_data in self._kids_temp.items()
        }
        default_data = {}
        chore_schema = build_chore_schema(kids_dict, default_data)
        return self.async_show_form(
            step_id="chores", data_schema=chore_schema, errors=errors
        )

    # --------------------------------------------------------------------------
    # BADGES
    # --------------------------------------------------------------------------
    async def async_step_badge_count(self, user_input=None):
        """Ask how many badges to define."""
        errors = {}
        if user_input is not None:
            try:
                self._badge_count = int(user_input["badge_count"])
                if self._badge_count < 0:
                    raise ValueError
                if self._badge_count == 0:
                    return await self.async_step_reward_count()
                self._badge_index = 0
                return await self.async_step_badges()
            except ValueError:
                errors["base"] = "invalid_badge_count"

        schema = vol.Schema({vol.Required("badge_count", default=0): vol.Coerce(int)})
        return self.async_show_form(
            step_id="badge_count", data_schema=schema, errors=errors
        )

    async def async_step_badges(self, user_input=None):
        """Collect badge details using internal_id as the primary key.

        Store in self._badges_temp as a dict keyed by internal_id.
        """
        errors = {}
        if user_input is not None:
            badge_name = user_input["badge_name"].strip()
            internal_id = user_input.get("internal_id", str(uuid.uuid4()))

            if not badge_name:
                errors["badge_name"] = "invalid_badge_name"
            elif any(
                badge_data["name"] == badge_name
                for badge_data in self._badges_temp.values()
            ):
                errors["badge_name"] = "duplicate_badge"
            else:
                self._badges_temp[internal_id] = {
                    "name": badge_name,
                    "threshold_type": user_input["threshold_type"],
                    "threshold_value": user_input["threshold_value"],
                    "points_multiplier": user_input["points_multiplier"],
                    "icon": user_input.get("icon", ""),
                    "internal_id": internal_id,
                    "description": user_input.get("badge_description", ""),
                    "badge_labels": user_input.get("badge_labels", []),
                }
                LOGGER.debug("Added badge: %s with ID: %s", badge_name, internal_id)

            self._badge_index += 1
            if self._badge_index >= self._badge_count:
                return await self.async_step_reward_count()
            return await self.async_step_badges()

        badge_schema = build_badge_schema()
        return self.async_show_form(
            step_id="badges", data_schema=badge_schema, errors=errors
        )

    # --------------------------------------------------------------------------
    # REWARDS
    # --------------------------------------------------------------------------
    async def async_step_reward_count(self, user_input=None):
        """Ask how many rewards to define."""
        errors = {}
        if user_input is not None:
            try:
                self._reward_count = int(user_input["reward_count"])
                if self._reward_count < 0:
                    raise ValueError
                if self._reward_count == 0:
                    return await self.async_step_penalty_count()
                self._reward_index = 0
                return await self.async_step_rewards()
            except ValueError:
                errors["base"] = "invalid_reward_count"

        schema = vol.Schema({vol.Required("reward_count", default=0): vol.Coerce(int)})
        return self.async_show_form(
            step_id="reward_count", data_schema=schema, errors=errors
        )

    async def async_step_rewards(self, user_input=None):
        """Collect reward details using internal_id as the primary key.

        Store in self._rewards_temp as a dict keyed by internal_id.
        """
        errors = {}
        if user_input is not None:
            reward_name = user_input["reward_name"].strip()
            internal_id = user_input.get("internal_id", str(uuid.uuid4()))

            if not reward_name:
                errors["reward_name"] = "invalid_reward_name"
            elif any(
                reward_data["name"] == reward_name
                for reward_data in self._rewards_temp.values()
            ):
                errors["reward_name"] = "duplicate_reward"
            else:
                self._rewards_temp[internal_id] = {
                    "name": reward_name,
                    "cost": user_input["reward_cost"],
                    "description": user_input.get("reward_description", ""),
                    "reward_labels": user_input.get("reward_labels", []),
                    "icon": user_input.get("icon", ""),
                    "internal_id": internal_id,
                }
                LOGGER.debug("Added reward: %s with ID: %s", reward_name, internal_id)

            self._reward_index += 1
            if self._reward_index >= self._reward_count:
                return await self.async_step_penalty_count()
            return await self.async_step_rewards()

        reward_schema = build_reward_schema()
        return self.async_show_form(
            step_id="rewards", data_schema=reward_schema, errors=errors
        )

    # --------------------------------------------------------------------------
    # PENALTIES
    # --------------------------------------------------------------------------
    async def async_step_penalty_count(self, user_input=None):
        """Ask how many penalties to define."""
        errors = {}
        if user_input is not None:
            try:
                self._penalty_count = int(user_input["penalty_count"])
                if self._penalty_count < 0:
                    raise ValueError
                if self._penalty_count == 0:
                    return await self.async_step_bonus_count()
                self._penalty_index = 0
                return await self.async_step_penalties()
            except ValueError:
                errors["base"] = "invalid_penalty_count"

        schema = vol.Schema({vol.Required("penalty_count", default=0): vol.Coerce(int)})
        return self.async_show_form(
            step_id="penalty_count", data_schema=schema, errors=errors
        )

    async def async_step_penalties(self, user_input=None):
        """Collect penalty details using internal_id as the primary key.

        Store in self._penalties_temp as a dict keyed by internal_id.
        """
        errors = {}
        if user_input is not None:
            penalty_name = user_input["penalty_name"].strip()
            penalty_points = user_input["penalty_points"]
            internal_id = user_input.get("internal_id", str(uuid.uuid4()))

            if not penalty_name:
                errors["penalty_name"] = "invalid_penalty_name"
            elif any(
                penalty_data["name"] == penalty_name
                for penalty_data in self._penalties_temp.values()
            ):
                errors["penalty_name"] = "duplicate_penalty"
            else:
                self._penalties_temp[internal_id] = {
                    "name": penalty_name,
                    "description": user_input.get("penalty_description", ""),
                    "penalty_labels": user_input.get("penalty_labels", []),
                    "points": -abs(penalty_points),  # Ensure points are negative
                    "icon": user_input.get("icon", ""),
                    "internal_id": internal_id,
                }
                LOGGER.debug("Added penalty: %s with ID: %s", penalty_name, internal_id)

            self._penalty_index += 1
            if self._penalty_index >= self._penalty_count:
                return await self.async_step_bonus_count()
            return await self.async_step_penalties()

        penalty_schema = build_penalty_schema()
        return self.async_show_form(
            step_id="penalties", data_schema=penalty_schema, errors=errors
        )

    # --------------------------------------------------------------------------
    # BONUSES
    # --------------------------------------------------------------------------
    async def async_step_bonus_count(self, user_input=None):
        """Ask how many bonuses to define."""
        errors = {}
        if user_input is not None:
            try:
                self._bonus_count = int(user_input["bonus_count"])
                if self._bonus_count < 0:
                    raise ValueError
                if self._bonus_count == 0:
                    return await self.async_step_achievement_count()
                self._bonus_index = 0
                return await self.async_step_bonuses()
            except ValueError:
                errors["base"] = "invalid_bonus_count"

        schema = vol.Schema({vol.Required("bonus_count", default=0): vol.Coerce(int)})
        return self.async_show_form(
            step_id="bonus_count", data_schema=schema, errors=errors
        )

    async def async_step_bonuses(self, user_input=None):
        """Collect bonus details using internal_id as the primary key.

        Store in self._bonuses_temp as a dict keyed by internal_id.
        """
        errors = {}
        if user_input is not None:
            bonus_name = user_input["bonus_name"].strip()
            bonus_points = user_input["bonus_points"]
            internal_id = user_input.get("internal_id", str(uuid.uuid4()))

            if not bonus_name:
                errors["bonus_name"] = "invalid_bonus_name"
            elif any(
                bonus_data["name"] == bonus_name
                for bonus_data in self._bonuses_temp.values()
            ):
                errors["bonus_name"] = "duplicate_bonus"
            else:
                self._bonuses_temp[internal_id] = {
                    "name": bonus_name,
                    "description": user_input.get("bonus_description", ""),
                    "bonus_labels": user_input.get("bonus_labels", []),
                    "points": abs(bonus_points),  # Ensure points are positive
                    "icon": user_input.get("icon", ""),
                    "internal_id": internal_id,
                }
                LOGGER.debug("Added bonus '%s' with ID: %s", bonus_name, internal_id)

            self._bonus_index += 1
            if self._bonus_index >= self._bonus_count:
                return await self.async_step_achievement_count()
            return await self.async_step_bonuses()

        schema = build_bonus_schema()
        return self.async_show_form(
            step_id="bonuses", data_schema=schema, errors=errors
        )

    # --------------------------------------------------------------------------
    # ACHIEVEMENTS
    # --------------------------------------------------------------------------
    async def async_step_achievement_count(self, user_input=None):
        """Ask how many achievements to define initially."""
        errors = {}
        if user_input is not None:
            try:
                self._achievement_count = int(user_input["achievement_count"])
                if self._achievement_count < 0:
                    raise ValueError
                if self._achievement_count == 0:
                    return await self.async_step_challenge_count()
                self._achievement_index = 0
                return await self.async_step_achievements()
            except ValueError:
                errors["base"] = "invalid_achievement_count"
        schema = vol.Schema(
            {vol.Required("achievement_count", default=0): vol.Coerce(int)}
        )
        return self.async_show_form(
            step_id="achievement_count", data_schema=schema, errors=errors
        )

    async def async_step_achievements(self, user_input=None):
        """Collect each achievement's details using internal_id as the key."""
        errors = {}

        if user_input is not None:
            achievement_name = user_input["name"].strip()
            if not achievement_name:
                errors["name"] = "invalid_achievement_name"
            elif any(
                achievement_data["name"] == achievement_name
                for achievement_data in self._achievements_temp.values()
            ):
                errors["name"] = "duplicate_achievement"
            else:
                _type = user_input["type"]

                if _type == ACHIEVEMENT_TYPE_STREAK:
                    chore_id = user_input.get("selected_chore_id")
                    if not chore_id or chore_id == "None":
                        errors["selected_chore_id"] = "a_chore_must_be_selected"

                    final_chore_id = chore_id
                else:
                    # Discard chore if not streak
                    final_chore_id = ""

                if not errors:
                    internal_id = user_input.get("internal_id", str(uuid.uuid4()))
                    self._achievements_temp[internal_id] = {
                        "name": achievement_name,
                        "description": user_input.get("description", ""),
                        "achievement_labels": user_input.get("achievement_labels", []),
                        "icon": user_input.get("icon", ""),
                        "assigned_kids": user_input["assigned_kids"],
                        "type": _type,
                        "selected_chore_id": final_chore_id,
                        "criteria": user_input.get("criteria", "").strip(),
                        "target_value": user_input["target_value"],
                        "reward_points": user_input["reward_points"],
                        "internal_id": internal_id,
                        "progress": {},
                    }

                    self._achievement_index += 1
                    if self._achievement_index >= self._achievement_count:
                        return await self.async_step_challenge_count()
                    return await self.async_step_achievements()

        kids_dict = {
            kid_data["name"]: kid_id for kid_id, kid_data in self._kids_temp.items()
        }
        all_chores = self._chores_temp
        achievement_schema = build_achievement_schema(
            kids_dict=kids_dict, chores_dict=all_chores, default=None
        )
        return self.async_show_form(
            step_id="achievements", data_schema=achievement_schema, errors=errors
        )

    # --------------------------------------------------------------------------
    # CHALLENGES
    # --------------------------------------------------------------------------
    async def async_step_challenge_count(self, user_input=None):
        """Ask how many challenges to define initially."""
        errors = {}
        if user_input is not None:
            try:
                self._challenge_count = int(user_input["challenge_count"])
                if self._challenge_count < 0:
                    raise ValueError
                if self._challenge_count == 0:
                    return await self.async_step_finish()
                self._challenge_index = 0
                return await self.async_step_challenges()
            except ValueError:
                errors["base"] = "invalid_challenge_count"
        schema = vol.Schema(
            {vol.Required("challenge_count", default=0): vol.Coerce(int)}
        )
        return self.async_show_form(
            step_id="challenge_count", data_schema=schema, errors=errors
        )

    async def async_step_challenges(self, user_input=None):
        """Collect each challenge's details using internal_id as the key."""
        errors = {}
        if user_input is not None:
            challenge_name = user_input["name"].strip()
            if not challenge_name:
                errors["name"] = "invalid_challenge_name"
            elif any(
                challenge_data["name"] == challenge_name
                for challenge_data in self._challenges_temp.values()
            ):
                errors["name"] = "duplicate_challenge"
            else:
                _type = user_input["type"]

                if _type == CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                    chosen_chore_id = user_input.get("selected_chore_id")
                    if not chosen_chore_id or chosen_chore_id == "None":
                        errors["selected_chore_id"] = "a_chore_must_be_selected"
                    final_chore_id = chosen_chore_id
                else:
                    # Discard chore if not "CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW"
                    final_chore_id = ""

                # Process start_date and end_date using the helper:
                start_date_input = user_input.get("start_date")
                end_date_input = user_input.get("end_date")

                if start_date_input:
                    try:
                        start_date = ensure_utc_datetime(self.hass, start_date_input)
                        start_dt = dt_util.parse_datetime(start_date)
                        if start_dt and start_dt < dt_util.utcnow():
                            errors["start_date"] = "start_date_in_past"
                    except Exception:
                        errors["start_date"] = "invalid_start_date"
                        start_date = None
                else:
                    start_date = None

                if end_date_input:
                    try:
                        end_date = ensure_utc_datetime(self.hass, end_date_input)
                        end_dt = dt_util.parse_datetime(end_date)
                        if end_dt and end_dt <= dt_util.utcnow():
                            errors["end_date"] = "end_date_in_past"
                        if start_date:
                            # Compare start_dt and end_dt if both are valid
                            if end_dt and start_dt and end_dt <= start_dt:
                                errors["end_date"] = "end_date_not_after_start_date"
                    except Exception:
                        errors["end_date"] = "invalid_end_date"
                        end_date = None
                else:
                    end_date = None

                if not errors:
                    internal_id = user_input.get("internal_id", str(uuid.uuid4()))
                    self._challenges_temp[internal_id] = {
                        "name": challenge_name,
                        "description": user_input.get("description", ""),
                        "challenge_labels": user_input.get("challenge_labels", []),
                        "icon": user_input.get("icon", ""),
                        "assigned_kids": user_input["assigned_kids"],
                        "type": _type,
                        "selected_chore_id": final_chore_id,
                        "criteria": user_input.get("criteria", "").strip(),
                        "target_value": user_input["target_value"],
                        "reward_points": user_input["reward_points"],
                        "start_date": start_date,
                        "end_date": end_date,
                        "internal_id": internal_id,
                        "progress": {},
                    }
                    self._challenge_index += 1
                    if self._challenge_index >= self._challenge_count:
                        return await self.async_step_finish()
                    return await self.async_step_challenges()

        kids_dict = {
            kid_data["name"]: kid_id for kid_id, kid_data in self._kids_temp.items()
        }
        all_chores = self._chores_temp
        default_data = user_input if user_input else None
        challenge_schema = build_challenge_schema(
            kids_dict=kids_dict,
            chores_dict=all_chores,
            default=default_data,
        )
        return self.async_show_form(
            step_id="challenges", data_schema=challenge_schema, errors=errors
        )

    # --------------------------------------------------------------------------
    # FINISH
    # --------------------------------------------------------------------------
    async def async_step_finish(self, user_input=None):
        """Finalize summary and create the config entry."""
        if user_input is not None:
            return self._create_entry()

        # Create a mapping from kid_id to kid_name for easy lookup
        kid_id_to_name = {
            kid_id: data["name"] for kid_id, data in self._kids_temp.items()
        }

        # Enhance parents summary to include associated kids by name
        parents_summary = []
        for parent in self._parents_temp.values():
            associated_kids_names = [
                kid_id_to_name.get(kid_id, "Unknown")
                for kid_id in parent.get("associated_kids", [])
            ]
            if associated_kids_names:
                kids_str = ", ".join(associated_kids_names)
                parents_summary.append(f"{parent['name']} (Kids: {kids_str})")
            else:
                parents_summary.append(parent["name"])

        summary = (
            f"\nKids: {', '.join(kid_data['name'] for kid_data in self._kids_temp.values()) or 'None'}\n\n"
            f"Parents: {', '.join(parents_summary) or 'None'}\n\n"
            f"Chores: {', '.join(chore_data['name'] for chore_data in self._chores_temp.values()) or 'None'}\n\n"
            f"Badges: {', '.join(badge_data['name'] for badge_data in self._badges_temp.values()) or 'None'}\n\n"
            f"Rewards: {', '.join(reward_data['name'] for reward_data in self._rewards_temp.values()) or 'None'}\n\n"
            f"Penalties: {', '.join(penalty_data['name'] for penalty_data in self._penalties_temp.values()) or 'None'}\n\n"
            f"Bonuses: {', '.join(bonus_data['name'] for bonus_data in self._bonuses_temp.values()) or 'None'}\n\n"
            f"Achievements: {', '.join(achievement_data['name'] for achievement_data in self._achievements_temp.values()) or 'None'}\n\n"
            f"Challenges: {', '.join(challenge_data['name'] for challenge_data in self._challenges_temp.values()) or 'None'}\n\n"
        )
        return self.async_show_form(
            step_id="finish",
            data_schema=vol.Schema({}),
            description_placeholders={"summary": summary},
        )

    def _create_entry(self):
        """Finalize config entry with data and options using internal_id as keys."""
        entry_data = {}
        entry_options = {
            CONF_POINTS_LABEL: self._data.get(CONF_POINTS_LABEL, DEFAULT_POINTS_LABEL),
            CONF_POINTS_ICON: self._data.get(CONF_POINTS_ICON, DEFAULT_POINTS_ICON),
            CONF_KIDS: self._kids_temp,
            CONF_PARENTS: self._parents_temp,
            CONF_CHORES: self._chores_temp,
            CONF_BADGES: self._badges_temp,
            CONF_REWARDS: self._rewards_temp,
            CONF_PENALTIES: self._penalties_temp,
            CONF_BONUSES: self._bonuses_temp,
            CONF_ACHIEVEMENTS: self._achievements_temp,
            CONF_CHALLENGES: self._challenges_temp,
        }

        LOGGER.debug(
            "Creating entry with data=%s, options=%s", entry_data, entry_options
        )
        return self.async_create_entry(
            title="KidsChores", data=entry_data, options=entry_options
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the Options Flow."""
        from .options_flow import KidsChoresOptionsFlowHandler

        return KidsChoresOptionsFlowHandler(config_entry)
