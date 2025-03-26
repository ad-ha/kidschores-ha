# File: config_flow.py
"""Multi-step config flow for the KidsChores integration, storing entities by internal_id.

Ensures that all add/edit/delete operations reference entities via internal_id for consistency.
"""

from typing import Any, Optional

import uuid
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from . import const
from . import flow_helpers as fh


class KidsChoresConfigFlow(config_entries.ConfigFlow, domain=const.DOMAIN):
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
            return self.async_abort(reason=const.TRANS_KEY_ERROR_SINGLE_INSTANCE)

        # Continue your normal flow
        return await self.async_step_intro()

    async def async_step_intro(self, user_input=None):
        """Intro / welcome step. Press Next to continue."""
        if user_input is not None:
            return await self.async_step_points_label()

        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_INTRO, data_schema=vol.Schema({})
        )

    async def async_step_points_label(self, user_input=None):
        """Let the user define a custom label for points."""
        errors = {}

        if user_input is not None:
            points_label = user_input.get(
                const.CONF_POINTS_LABEL, const.DEFAULT_POINTS_LABEL
            )
            points_icon = user_input.get(
                const.CONF_POINTS_ICON, const.DEFAULT_POINTS_ICON
            )

            self._data[const.CONF_POINTS_LABEL] = points_label
            self._data[const.CONF_POINTS_ICON] = points_icon

            return await self.async_step_kid_count()

        points_schema = fh.build_points_schema(
            default_label=const.DEFAULT_POINTS_LABEL,
            default_icon=const.DEFAULT_POINTS_ICON,
        )

        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_POINTS,
            data_schema=points_schema,
            errors=errors,
        )

    # --------------------------------------------------------------------------
    # KIDS
    # --------------------------------------------------------------------------
    async def async_step_kid_count(self, user_input=None):
        """Ask how many kids to define initially."""
        errors = {}
        if user_input is not None:
            try:
                self._kid_count = int(user_input[const.CFOF_KIDS_INPUT_KID_COUNT])
                if self._kid_count < 0:
                    raise ValueError
                if self._kid_count == 0:
                    return await self.async_step_chore_count()
                self._kid_index = 0
                return await self.async_step_kids()
            except ValueError:
                errors[const.CFOP_ERROR_BASE] = const.TRANS_KEY_CFOF_INVALID_KID_COUNT

        schema = vol.Schema(
            {vol.Required(const.CFOF_KIDS_INPUT_KID_COUNT, default=1): vol.Coerce(int)}
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_KID_COUNT, data_schema=schema, errors=errors
        )

    async def async_step_kids(self, user_input=None):
        """Collect each kid's info using internal_id as the primary key."""
        errors = {}
        if user_input is not None:
            kid_name = user_input[const.CFOF_KIDS_INPUT_KID_NAME].strip()
            ha_user_id = (
                user_input.get(const.CFOF_KIDS_INPUT_HA_USER) or const.CONF_EMPTY
            )
            enable_mobile_notifications = user_input.get(
                const.CFOF_KIDS_INPUT_ENABLE_MOBILE_NOTIFICATIONS, True
            )
            notify_service = (
                user_input.get(const.CFOF_KIDS_INPUT_MOBILE_NOTIFY_SERVICE)
                or const.CONF_EMPTY
            )
            enable_persist = user_input.get(
                const.CFOF_KIDS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS, True
            )

            if not kid_name:
                errors[const.CFOP_ERROR_KID_NAME] = (
                    const.TRANS_KEY_CFOF_INVALID_KID_NAME
                )
            elif any(
                kid_data[const.DATA_KID_NAME] == kid_name
                for kid_data in self._kids_temp.values()
            ):
                errors[const.CFOP_ERROR_KID_NAME] = const.TRANS_KEY_CFOF_DUPLICATE_KID
            else:
                internal_id = user_input.get(
                    const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
                )
                self._kids_temp[internal_id] = {
                    const.DATA_KID_NAME: kid_name,
                    const.DATA_KID_HA_USER_ID: ha_user_id,
                    const.DATA_KID_ENABLE_NOTIFICATIONS: enable_mobile_notifications,
                    const.DATA_KID_MOBILE_NOTIFY_SERVICE: notify_service,
                    const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS: enable_persist,
                    const.DATA_KID_INTERNAL_ID: internal_id,
                }
                const.LOGGER.debug("Added kid: %s with ID: %s", kid_name, internal_id)

            self._kid_index += 1
            if self._kid_index >= self._kid_count:
                return await self.async_step_parent_count()
            return await self.async_step_kids()

        # Retrieve HA users for linking
        users = await self.hass.auth.async_get_users()
        kid_schema = fh.build_kid_schema(
            self.hass,
            users=users,
            default_kid_name=const.CONF_EMPTY,
            default_ha_user_id=None,
            default_enable_mobile_notifications=False,
            default_mobile_notify_service=None,
            default_enable_persistent_notifications=False,
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_KIDS, data_schema=kid_schema, errors=errors
        )

    # --------------------------------------------------------------------------
    # PARENTS
    # --------------------------------------------------------------------------
    async def async_step_parent_count(self, user_input=None):
        """Ask how many parents to define initially."""
        errors = {}
        if user_input is not None:
            try:
                self._parents_count = int(
                    user_input[const.CFOF_PARENTS_INPUT_PARENT_COUNT]
                )
                if self._parents_count < 0:
                    raise ValueError
                if self._parents_count == 0:
                    return await self.async_step_chore_count()
                self._parents_index = 0
                return await self.async_step_parents()
            except ValueError:
                errors[const.CFOP_ERROR_BASE] = (
                    const.TRANS_KEY_CFOF_INVALID_PARENT_COUNT
                )

        schema = vol.Schema(
            {
                vol.Required(
                    const.CFOF_PARENTS_INPUT_PARENT_COUNT, default=1
                ): vol.Coerce(int)
            }
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_PARENT_COUNT,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_parents(self, user_input=None):
        """Collect each parent's info using internal_id as the primary key.

        Store in self._parents_temp as a dict keyed by internal_id.
        """
        errors = {}
        if user_input is not None:
            parent_name = user_input[const.CFOF_PARENTS_INPUT_NAME].strip()
            ha_user_id = (
                user_input.get(const.CFOF_PARENTS_INPUT_HA_USER) or const.CONF_EMPTY
            )
            associated_kids = user_input.get(
                const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS, []
            )
            enable_mobile_notifications = user_input.get(
                const.CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS, True
            )
            notify_service = (
                user_input.get(const.CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE)
                or const.CONF_EMPTY
            )
            enable_persist = user_input.get(
                const.CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS, True
            )

            if not parent_name:
                errors[const.CFPO_ERROR_PARENT_NAME] = (
                    const.TRANS_KEY_CFOF_INVALID_PARENT_NAME
                )
            elif any(
                parent_data[const.DATA_PARENT_NAME] == parent_name
                for parent_data in self._parents_temp.values()
            ):
                errors[const.CFPO_ERROR_PARENT_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_PARENT
                )
            else:
                internal_id = user_input.get(
                    const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
                )
                self._parents_temp[internal_id] = {
                    const.DATA_PARENT_NAME: parent_name,
                    const.DATA_PARENT_HA_USER_ID: ha_user_id,
                    const.DATA_PARENT_ASSOCIATED_KIDS: associated_kids,
                    const.DATA_PARENT_ENABLE_NOTIFICATIONS: enable_mobile_notifications,
                    const.DATA_PARENT_MOBILE_NOTIFY_SERVICE: notify_service,
                    const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS: enable_persist,
                    const.DATA_PARENT_INTERNAL_ID: internal_id,
                }
                const.LOGGER.debug(
                    "Added parent: %s with ID: %s", parent_name, internal_id
                )

            self._parents_index += 1
            if self._parents_index >= self._parents_count:
                return await self.async_step_chore_count()
            return await self.async_step_parents()

        # Retrieve kids for association from _kids_temp
        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in self._kids_temp.items()
        }

        users = await self.hass.auth.async_get_users()

        parent_schema = fh.build_parent_schema(
            self.hass,
            users=users,
            kids_dict=kids_dict,
            default_parent_name=const.CONF_EMPTY,
            default_ha_user_id=None,
            default_associated_kids=[],
            default_enable_mobile_notifications=False,
            default_mobile_notify_service=None,
            default_enable_persistent_notifications=False,
            internal_id=None,
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_PARENTS,
            data_schema=parent_schema,
            errors=errors,
        )

    # --------------------------------------------------------------------------
    # CHORES
    # --------------------------------------------------------------------------
    async def async_step_chore_count(self, user_input=None):
        """Ask how many chores to define."""
        errors = {}
        if user_input is not None:
            try:
                self._chore_count = int(user_input[const.CFOF_CHORES_INPUT_CHORE_COUNT])
                if self._chore_count < 0:
                    raise ValueError
                if self._chore_count == 0:
                    return await self.async_step_badge_count()
                self._chore_index = 0
                return await self.async_step_chores()
            except ValueError:
                errors[const.CFOP_ERROR_BASE] = const.TRANS_KEY_CFOF_INVALID_CHORE_COUNT

        schema = vol.Schema(
            {
                vol.Required(
                    const.CFOF_CHORES_INPUT_CHORE_COUNT, default=1
                ): vol.Coerce(int)
            }
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_CHORE_COUNT,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_chores(self, user_input=None):
        """Collect chore details using internal_id as the primary key.

        Store in self._chores_temp as a dict keyed by internal_id.
        """
        errors = {}

        if user_input is not None:
            chore_name = user_input[const.CFOF_CHORES_INPUT_NAME].strip()
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )

            if user_input.get(const.CFOF_CHORES_INPUT_DUE_DATE):
                raw_due = user_input[const.CFOF_CHORES_INPUT_DUE_DATE]
                try:
                    due_date_str = fh.ensure_utc_datetime(self.hass, raw_due)
                    due_dt = dt_util.parse_datetime(due_date_str)
                    if due_dt and due_dt < dt_util.utcnow():
                        errors[const.CFOP_ERROR_DUE_DATE] = (
                            const.TRANS_KEY_CFOF_DUE_DATE_IN_PAST
                        )
                except ValueError:
                    errors[const.CFOP_ERROR_DUE_DATE] = (
                        const.TRANS_KEY_CFOF_INVALID_DUE_DATE
                    )
                    due_date_str = None
            else:
                due_date_str = None

            if not chore_name:
                errors[const.CFOP_ERROR_CHORE_NAME] = (
                    const.TRANS_KEY_CFOF_INVALID_CHORE_NAME
                )
            elif any(
                chore_data[const.DATA_CHORE_NAME] == chore_name
                for chore_data in self._chores_temp.values()
            ):
                errors[const.CFOP_ERROR_CHORE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_CHORE
                )

            if errors:
                kids_dict = {
                    kid_data[const.DATA_KID_NAME]: kid_id
                    for kid_id, kid_data in self._kids_temp.items()
                }
                # Re-show the form with the user's current input and errors:
                default_data = user_input.copy()
                return self.async_show_form(
                    step_id=const.CONFIG_FLOW_STEP_CHORES,
                    data_schema=fh.build_chore_schema(kids_dict, default_data),
                    errors=errors,
                )

            if (
                user_input.get(const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY)
                != const.FREQUENCY_CUSTOM
            ):
                user_input.pop(const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL, None)
                user_input.pop(const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL_UNIT, None)

            # If no errors, store the chore
            self._chores_temp[internal_id] = {
                const.DATA_CHORE_NAME: chore_name,
                const.DATA_CHORE_DEFAULT_POINTS: user_input[
                    const.CFOF_CHORES_INPUT_DEFAULT_POINTS
                ],
                const.DATA_CHORE_PARTIAL_ALLOWED: user_input[
                    const.CFOF_CHORES_INPUT_PARTIAL_ALLOWED
                ],
                const.DATA_CHORE_SHARED_CHORE: user_input[
                    const.CFOF_CHORES_INPUT_SHARED_CHORE
                ],
                const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY: user_input[
                    const.CFOF_CHORES_INPUT_ALLOW_MULTIPLE_CLAIMS
                ],
                const.DATA_CHORE_ASSIGNED_KIDS: user_input[
                    const.CFOF_CHORES_INPUT_ASSIGNED_KIDS
                ],
                const.DATA_CHORE_DESCRIPTION: user_input.get(
                    const.CFOF_CHORES_INPUT_DESCRIPTION, const.CONF_EMPTY
                ),
                const.DATA_CHORE_LABELS: user_input.get(
                    const.CFOF_CHORES_INPUT_LABELS, []
                ),
                const.DATA_CHORE_ICON: user_input.get(
                    const.CFOF_CHORES_INPUT_ICON, const.DEFAULT_CHORE_ICON
                ),
                const.DATA_CHORE_RECURRING_FREQUENCY: user_input.get(
                    const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY, const.CONF_EMPTY
                ),
                const.DATA_CHORE_CUSTOM_INTERVAL: user_input.get(
                    const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL
                ),
                const.DATA_CHORE_CUSTOM_INTERVAL_UNIT: user_input.get(
                    const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL_UNIT
                ),
                const.DATA_CHORE_DUE_DATE: due_date_str,
                const.DATA_CHORE_APPLICABLE_DAYS: user_input.get(
                    const.CFOF_CHORES_INPUT_APPLICABLE_DAYS,
                    const.DEFAULT_APPLICABLE_DAYS,
                ),
                const.DATA_CHORE_NOTIFY_ON_CLAIM: user_input.get(
                    const.CFOF_CHORES_INPUT_NOTIFY_ON_CLAIM,
                    const.DEFAULT_NOTIFY_ON_CLAIM,
                ),
                const.DATA_CHORE_NOTIFY_ON_APPROVAL: user_input.get(
                    const.CFOF_CHORES_INPUT_NOTIFY_ON_APPROVAL,
                    const.DEFAULT_NOTIFY_ON_APPROVAL,
                ),
                const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL: user_input.get(
                    const.CFOF_CHORES_INPUT_NOTIFY_ON_DISAPPROVAL,
                    const.DEFAULT_NOTIFY_ON_DISAPPROVAL,
                ),
                const.DATA_CHORE_INTERNAL_ID: internal_id,
            }
            const.LOGGER.debug("Added chore: %s with ID: %s", chore_name, internal_id)

            self._chore_index += 1
            if self._chore_index >= self._chore_count:
                return await self.async_step_badge_count()
            return await self.async_step_chores()

        # Use flow_helpers.fh.build_chore_schema, passing the current kids
        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in self._kids_temp.items()
        }
        default_data = {}
        chore_schema = fh.build_chore_schema(kids_dict, default_data)
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_CHORES,
            data_schema=chore_schema,
            errors=errors,
        )

    # --------------------------------------------------------------------------
    # BADGES
    # --------------------------------------------------------------------------
    async def async_step_badge_count(self, user_input=None):
        """Ask how many badges to define."""
        errors = {}
        if user_input is not None:
            try:
                self._badge_count = int(user_input[const.CFOF_BADGES_INPUT_BADGE_COUNT])
                if self._badge_count < 0:
                    raise ValueError
                if self._badge_count == 0:
                    return await self.async_step_reward_count()
                self._badge_index = 0
                return await self.async_step_badges()
            except ValueError:
                errors[const.CFOP_ERROR_BASE] = const.TRANS_KEY_CFOF_INVALID_BADGE_COUNT

        schema = vol.Schema(
            {
                vol.Required(
                    const.CFOF_BADGES_INPUT_BADGE_COUNT, default=0
                ): vol.Coerce(int)
            }
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_BADGE_COUNT,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_badges(self, user_input=None):
        """Collect badge details using internal_id as the primary key."""
        errors = {}
        if user_input is not None:
            badge_name = user_input[const.CFOF_BADGES_INPUT_NAME].strip()
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )

            if not badge_name:
                errors[const.CFOP_ERROR_BADGE_NAME] = (
                    const.TRANS_KEY_CFOF_INVALID_BADGE_NAME
                )
            elif any(
                badge_data[const.DATA_BADGE_NAME] == badge_name
                for badge_data in self._badges_temp.values()
            ):
                errors[const.CFOP_ERROR_BADGE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_BADGE
                )
            else:
                self._badges_temp[internal_id] = {
                    const.DATA_BADGE_NAME: badge_name,
                    const.DATA_BADGE_DESCRIPTION: user_input.get(
                        const.CFOF_BADGES_INPUT_DESCRIPTION, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_LABELS: user_input.get(
                        const.CFOF_BADGES_INPUT_LABELS, []
                    ),
                    const.DATA_BADGE_ICON: user_input.get(
                        const.CFOF_BADGES_INPUT_ICON, const.DEFAULT_BADGE_ICON
                    ),
                    const.DATA_BADGE_THRESHOLD_TYPE: const.DEFAULT_BADGE_THRESHOLD_TYPE,
                    const.DATA_BADGE_THRESHOLD_VALUE: user_input[
                        const.CFOF_BADGES_INPUT_THRESHOLD_VALUE
                    ],
                    const.DATA_BADGE_POINTS_MULTIPLIER: user_input[
                        const.CFOF_BADGES_INPUT_POINTS_MULTIPLIER
                    ],
                    const.CONF_BADGE_RESET_PERIODICALLY: user_input.get(
                        const.CONF_BADGE_RESET_PERIODICALLY, False
                    ),
                    const.CONF_BADGE_RESET_PERIOD: user_input.get(
                        const.CONF_BADGE_RESET_PERIOD, const.CONF_YEAR_END
                    ),
                    const.CONF_BADGE_RESET_GRACE_PERIOD: user_input.get(
                        const.CONF_BADGE_RESET_GRACE_PERIOD,
                        const.DEFAULT_BADGE_RESET_GRACE_PERIOD,
                    ),
                    const.CONF_BADGE_MAINTENANCE_RULES: user_input.get(
                        const.CONF_BADGE_MAINTENANCE_RULES, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_TYPE: const.BADGE_TYPE_CUMULATIVE,
                    const.DATA_BADGE_INTERNAL_ID: internal_id,
                }
                const.LOGGER.debug(
                    "Added badge: %s with ID: %s", badge_name, internal_id
                )

            self._badge_index += 1
            if self._badge_index >= self._badge_count:
                return await self.async_step_reward_count()
            return await self.async_step_badges()

        badge_schema = fh.build_badge_cumulative_schema()
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_BADGES,
            data_schema=badge_schema,
            errors=errors,
        )

    # --------------------------------------------------------------------------
    # REWARDS
    # --------------------------------------------------------------------------
    async def async_step_reward_count(self, user_input=None):
        """Ask how many rewards to define."""
        errors = {}
        if user_input is not None:
            try:
                self._reward_count = int(
                    user_input[const.CFOF_REWARDS_INPUT_REWARD_COUNT]
                )
                if self._reward_count < 0:
                    raise ValueError
                if self._reward_count == 0:
                    return await self.async_step_penalty_count()
                self._reward_index = 0
                return await self.async_step_rewards()
            except ValueError:
                errors[const.CFOP_ERROR_BASE] = (
                    const.TRANS_KEY_CFOF_INVALID_REWARD_COUNT
                )

        schema = vol.Schema(
            {
                vol.Required(
                    const.CFOF_REWARDS_INPUT_REWARD_COUNT, default=0
                ): vol.Coerce(int)
            }
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_REWARD_COUNT,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_rewards(self, user_input=None):
        """Collect reward details using internal_id as the primary key.

        Store in self._rewards_temp as a dict keyed by internal_id.
        """
        errors = {}
        if user_input is not None:
            reward_name = user_input[const.CFOF_REWARDS_INPUT_NAME].strip()
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )

            if not reward_name:
                errors[const.CFOP_ERROR_REWARD_NAME] = (
                    const.TRANS_KEY_CFOF_INVALID_REWARD_NAME
                )
            elif any(
                reward_data[const.DATA_REWARD_NAME] == reward_name
                for reward_data in self._rewards_temp.values()
            ):
                errors[const.CFOP_ERROR_REWARD_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_REWARD
                )
            else:
                self._rewards_temp[internal_id] = {
                    const.DATA_REWARD_NAME: reward_name,
                    const.DATA_REWARD_COST: user_input[const.CFOF_REWARDS_INPUT_COST],
                    const.DATA_REWARD_DESCRIPTION: user_input.get(
                        const.CFOF_REWARDS_INPUT_DESCRIPTION, const.CONF_EMPTY
                    ),
                    const.DATA_REWARD_LABELS: user_input.get(
                        const.CFOF_REWARDS_INPUT_LABELS, []
                    ),
                    const.DATA_REWARD_ICON: user_input.get(
                        const.CFOF_REWARDS_INPUT_ICON, const.DEFAULT_REWARD_ICON
                    ),
                    const.DATA_REWARD_INTERNAL_ID: internal_id,
                }
                const.LOGGER.debug(
                    "Added reward: %s with ID: %s", reward_name, internal_id
                )

            self._reward_index += 1
            if self._reward_index >= self._reward_count:
                return await self.async_step_penalty_count()
            return await self.async_step_rewards()

        reward_schema = fh.build_reward_schema()
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_REWARDS,
            data_schema=reward_schema,
            errors=errors,
        )

    # --------------------------------------------------------------------------
    # PENALTIES
    # --------------------------------------------------------------------------
    async def async_step_penalty_count(self, user_input=None):
        """Ask how many penalties to define."""
        errors = {}
        if user_input is not None:
            try:
                self._penalty_count = int(
                    user_input[const.CFOF_PENALTIES_INPUT_PENALTY_COUNT]
                )
                if self._penalty_count < 0:
                    raise ValueError
                if self._penalty_count == 0:
                    return await self.async_step_bonus_count()
                self._penalty_index = 0
                return await self.async_step_penalties()
            except ValueError:
                errors[const.CFOP_ERROR_BASE] = (
                    const.TRANS_KEY_CFOF_INVALID_PENALTY_COUNT
                )

        schema = vol.Schema(
            {
                vol.Required(
                    const.CFOF_PENALTIES_INPUT_PENALTY_COUNT, default=0
                ): vol.Coerce(int)
            }
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_PENALTY_COUNT,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_penalties(self, user_input=None):
        """Collect penalty details using internal_id as the primary key.

        Store in self._penalties_temp as a dict keyed by internal_id.
        """
        errors = {}
        if user_input is not None:
            penalty_name = user_input[const.CFOF_PENALTIES_INPUT_NAME].strip()
            penalty_points = user_input[const.CFOF_PENALTIES_INPUT_POINTS]
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )

            if not penalty_name:
                errors[const.CFOP_ERROR_PENALTY_NAME] = (
                    const.TRANS_KEY_CFOF_INVALID_PENALTY_NAME
                )
            elif any(
                penalty_data[const.DATA_PENALTY_NAME] == penalty_name
                for penalty_data in self._penalties_temp.values()
            ):
                errors[const.CFOP_ERROR_PENALTY_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_PENALTY
                )
            else:
                self._penalties_temp[internal_id] = {
                    const.DATA_PENALTY_NAME: penalty_name,
                    const.DATA_PENALTY_DESCRIPTION: user_input.get(
                        const.CFOF_PENALTIES_INPUT_DESCRIPTION, const.CONF_EMPTY
                    ),
                    const.DATA_PENALTY_LABELS: user_input.get(
                        const.CFOF_PENALTIES_INPUT_LABELS, []
                    ),
                    const.DATA_PENALTY_POINTS: -abs(
                        penalty_points
                    ),  # Ensure points are negative
                    const.DATA_PENALTY_ICON: user_input.get(
                        const.CFOF_PENALTIES_INPUT_ICON, const.DEFAULT_PENALTY_ICON
                    ),
                    const.DATA_PENALTY_INTERNAL_ID: internal_id,
                }
                const.LOGGER.debug(
                    "Added penalty: %s with ID: %s", penalty_name, internal_id
                )

            self._penalty_index += 1
            if self._penalty_index >= self._penalty_count:
                return await self.async_step_bonus_count()
            return await self.async_step_penalties()

        penalty_schema = fh.build_penalty_schema()
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_PENALTIES,
            data_schema=penalty_schema,
            errors=errors,
        )

    # --------------------------------------------------------------------------
    # BONUSES
    # --------------------------------------------------------------------------
    async def async_step_bonus_count(self, user_input=None):
        """Ask how many bonuses to define."""
        errors = {}
        if user_input is not None:
            try:
                self._bonus_count = int(
                    user_input[const.CFOF_BONUSES_INPUT_BONUS_COUNT]
                )
                if self._bonus_count < 0:
                    raise ValueError
                if self._bonus_count == 0:
                    return await self.async_step_achievement_count()
                self._bonus_index = 0
                return await self.async_step_bonuses()
            except ValueError:
                errors[const.CFOP_ERROR_BASE] = const.TRANS_KEY_CFOF_INVALID_BONUS_COUNT

        schema = vol.Schema(
            {
                vol.Required(
                    const.CFOF_BONUSES_INPUT_BONUS_COUNT, default=0
                ): vol.Coerce(int)
            }
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_BONUS_COUNT,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_bonuses(self, user_input=None):
        """Collect bonus details using internal_id as the primary key.

        Store in self._bonuses_temp as a dict keyed by internal_id.
        """
        errors = {}
        if user_input is not None:
            bonus_name = user_input[const.CFOF_BONUSES_INPUT_NAME].strip()
            bonus_points = user_input[const.CFOF_BONUSES_INPUT_POINTS]
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )

            if not bonus_name:
                errors[const.CFOP_ERROR_BONUS_NAME] = (
                    const.TRANS_KEY_CFOF_INVALID_BONUS_NAME
                )
            elif any(
                bonus_data[const.DATA_BONUS_NAME] == bonus_name
                for bonus_data in self._bonuses_temp.values()
            ):
                errors[const.CFOP_ERROR_BONUS_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_BONUS
                )
            else:
                self._bonuses_temp[internal_id] = {
                    const.DATA_BONUS_NAME: bonus_name,
                    const.DATA_BONUS_DESCRIPTION: user_input.get(
                        const.CFOF_BONUSES_INPUT_DESCRIPTION, const.CONF_EMPTY
                    ),
                    const.DATA_BONUS_LABELS: user_input.get(
                        const.CFOF_BONUSES_INPUT_LABELS, []
                    ),
                    const.DATA_BONUS_POINTS: abs(bonus_points),
                    const.DATA_BONUS_ICON: user_input.get(
                        const.CFOF_BONUSES_INPUT_ICON, const.DEFAULT_BONUS_ICON
                    ),
                    const.DATA_BONUS_INTERNAL_ID: internal_id,
                }
                const.LOGGER.debug(
                    "Added bonus '%s' with ID: %s", bonus_name, internal_id
                )

            self._bonus_index += 1
            if self._bonus_index >= self._bonus_count:
                return await self.async_step_achievement_count()
            return await self.async_step_bonuses()

        schema = fh.build_bonus_schema()
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_BONUSES, data_schema=schema, errors=errors
        )

    # --------------------------------------------------------------------------
    # ACHIEVEMENTS
    # --------------------------------------------------------------------------
    async def async_step_achievement_count(self, user_input=None):
        """Ask how many achievements to define initially."""
        errors = {}
        if user_input is not None:
            try:
                self._achievement_count = int(
                    user_input[const.CFOF_ACHIEVEMENTS_INPUT_ACHIEVEMENT_COUNT]
                )
                if self._achievement_count < 0:
                    raise ValueError
                if self._achievement_count == 0:
                    return await self.async_step_challenge_count()
                self._achievement_index = 0
                return await self.async_step_achievements()
            except ValueError:
                errors[const.CFOP_ERROR_BASE] = (
                    const.TRANS_KEY_CFOF_INVALID_ACHIEVEMENT_COUNT
                )
        schema = vol.Schema(
            {
                vol.Required(
                    const.CFOF_ACHIEVEMENTS_INPUT_ACHIEVEMENT_COUNT, default=0
                ): vol.Coerce(int)
            }
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_achievements(self, user_input=None):
        """Collect each achievement's details using internal_id as the key."""
        errors = {}

        if user_input is not None:
            achievement_name = user_input[const.CFOF_ACHIEVEMENTS_INPUT_NAME].strip()
            if not achievement_name:
                errors[const.CFOP_ERROR_ACHIEVEMENT_NAME] = (
                    const.TRANS_KEY_CFOF_INVALID_ACHIEVEMENT_NAME
                )
            elif any(
                achievement_data[const.DATA_ACHIEVEMENT_NAME] == achievement_name
                for achievement_data in self._achievements_temp.values()
            ):
                errors[const.CFOP_ERROR_ACHIEVEMENT_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_ACHIEVEMENT
                )
            else:
                _type = user_input[const.CFOF_ACHIEVEMENTS_INPUT_TYPE]

                if _type == const.ACHIEVEMENT_TYPE_STREAK:
                    chore_id = user_input.get(
                        const.CFOF_ACHIEVEMENTS_INPUT_SELECTED_CHORE_ID
                    )
                    if not chore_id or chore_id == const.CONF_NONE_TEXT:
                        errors[const.CFOP_ERROR_SELECT_CHORE_ID] = (
                            const.TRANS_KEY_CFOF_CHORE_MUST_BE_SELECTED
                        )

                    final_chore_id = chore_id
                else:
                    # Discard chore if not streak
                    final_chore_id = const.CONF_EMPTY

                if not errors:
                    internal_id = user_input.get(
                        const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
                    )
                    self._achievements_temp[internal_id] = {
                        const.DATA_ACHIEVEMENT_NAME: achievement_name,
                        const.DATA_ACHIEVEMENT_DESCRIPTION: user_input.get(
                            const.CFOF_ACHIEVEMENTS_INPUT_DESCRIPTION, const.CONF_EMPTY
                        ),
                        const.DATA_ACHIEVEMENT_LABELS: user_input.get(
                            const.CFOF_ACHIEVEMENTS_INPUT_LABELS, []
                        ),
                        const.DATA_ACHIEVEMENT_ICON: user_input.get(
                            const.CFOF_ACHIEVEMENTS_INPUT_ICON,
                            const.DEFAULT_ACHIEVEMENTS_ICON,
                        ),
                        const.DATA_ACHIEVEMENT_ASSIGNED_KIDS: user_input[
                            const.CFOF_ACHIEVEMENTS_INPUT_ASSIGNED_KIDS
                        ],
                        const.DATA_ACHIEVEMENT_TYPE: _type,
                        const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID: final_chore_id,
                        const.DATA_ACHIEVEMENT_CRITERIA: user_input.get(
                            const.CFOF_ACHIEVEMENTS_INPUT_CRITERIA, const.CONF_EMPTY
                        ).strip(),
                        const.DATA_ACHIEVEMENT_TARGET_VALUE: user_input[
                            const.CFOF_ACHIEVEMENTS_INPUT_TARGET_VALUE
                        ],
                        const.DATA_ACHIEVEMENT_REWARD_POINTS: user_input[
                            const.CFOF_ACHIEVEMENTS_INPUT_REWARD_POINTS
                        ],
                        const.DATA_ACHIEVEMENT_INTERNAL_ID: internal_id,
                        const.DATA_ACHIEVEMENT_PROGRESS: {},
                    }

                    self._achievement_index += 1
                    if self._achievement_index >= self._achievement_count:
                        return await self.async_step_challenge_count()
                    return await self.async_step_achievements()

        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in self._kids_temp.items()
        }
        all_chores = self._chores_temp
        achievement_schema = fh.build_achievement_schema(
            kids_dict=kids_dict, chores_dict=all_chores, default=None
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_ACHIEVEMENTS,
            data_schema=achievement_schema,
            errors=errors,
        )

    # --------------------------------------------------------------------------
    # CHALLENGES
    # --------------------------------------------------------------------------
    async def async_step_challenge_count(self, user_input=None):
        """Ask how many challenges to define initially."""
        errors = {}
        if user_input is not None:
            try:
                self._challenge_count = int(
                    user_input[const.CFOF_CHALLENGES_INPUT_CHALLENGE_COUNT]
                )
                if self._challenge_count < 0:
                    raise ValueError
                if self._challenge_count == 0:
                    return await self.async_step_finish()
                self._challenge_index = 0
                return await self.async_step_challenges()
            except ValueError:
                errors[const.CFOP_ERROR_BASE] = (
                    const.TRANS_KEY_CFOF_INVALID_CHALLENGE_COUNT
                )
        schema = vol.Schema(
            {
                vol.Required(
                    const.CFOF_CHALLENGES_INPUT_CHALLENGE_COUNT, default=0
                ): vol.Coerce(int)
            }
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_CHALLENGE_COUNT,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_challenges(self, user_input=None):
        """Collect each challenge's details using internal_id as the key."""
        errors = {}
        if user_input is not None:
            challenge_name = user_input[const.CFOF_CHALLENGES_INPUT_NAME].strip()
            if not challenge_name:
                errors[const.CFOP_ERROR_CHALLENGE_NAME] = (
                    const.TRANS_KEY_CFOF_INVALID_CHALLENGE_NAME
                )
            elif any(
                challenge_data[const.DATA_CHALLENGE_NAME] == challenge_name
                for challenge_data in self._challenges_temp.values()
            ):
                errors[const.CFOP_ERROR_CHALLENGE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_CHALLENGE
                )
            else:
                _type = user_input[const.CFOF_CHALLENGES_INPUT_TYPE]

                if _type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                    chosen_chore_id = user_input.get(
                        const.CFOF_CHALLENGES_INPUT_SELECTED_CHORE_ID
                    )
                    if not chosen_chore_id or chosen_chore_id == const.CONF_NONE_TEXT:
                        errors[const.CFOP_ERROR_SELECT_CHORE_ID] = (
                            const.TRANS_KEY_CFOF_CHORE_MUST_BE_SELECTED
                        )
                    final_chore_id = chosen_chore_id
                else:
                    # Discard chore if not "const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW"
                    final_chore_id = const.CONF_EMPTY

                # Process start_date and end_date using the helper:
                start_date_input = user_input.get(
                    const.CFOF_CHALLENGES_INPUT_START_DATE
                )
                end_date_input = user_input.get(const.CFOF_CHALLENGES_INPUT_END_DATE)

                if start_date_input:
                    try:
                        start_date = fh.ensure_utc_datetime(self.hass, start_date_input)
                        start_dt = dt_util.parse_datetime(start_date)
                        if start_dt and start_dt < dt_util.utcnow():
                            errors[const.CFOP_ERROR_START_DATE] = (
                                const.TRANS_KEY_CFOF_START_DATE_IN_PAST
                            )
                    except Exception:
                        errors[const.CFOP_ERROR_START_DATE] = (
                            const.TRANS_KEY_CFOF_INVALID_START_DATE
                        )
                        start_date = None
                else:
                    start_date = None

                if end_date_input:
                    try:
                        end_date = fh.ensure_utc_datetime(self.hass, end_date_input)
                        end_dt = dt_util.parse_datetime(end_date)
                        if end_dt and end_dt <= dt_util.utcnow():
                            errors[const.CFOP_ERROR_END_DATE] = (
                                const.TRANS_KEY_CFOF_END_DATE_IN_PAST
                            )
                        if start_date:
                            # Compare start_dt and end_dt if both are valid
                            if end_dt and start_dt and end_dt <= start_dt:
                                errors[const.CFOP_ERROR_END_DATE] = (
                                    const.TRANS_KEY_CFOF_END_DATE_NOT_AFTER_START_DATE
                                )
                    except Exception:
                        errors[const.CFOP_ERROR_END_DATE] = (
                            const.TRANS_KEY_CFOF_INVALID_END_DATE
                        )
                        end_date = None
                else:
                    end_date = None

                if not errors:
                    internal_id = user_input.get(
                        const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
                    )
                    self._challenges_temp[internal_id] = {
                        const.DATA_CHALLENGE_NAME: challenge_name,
                        const.DATA_CHALLENGE_DESCRIPTION: user_input.get(
                            const.CFOF_CHALLENGES_INPUT_DESCRIPTION, const.CONF_EMPTY
                        ),
                        const.DATA_CHALLENGE_LABELS: user_input.get(
                            const.CFOF_CHALLENGES_INPUT_LABELS, []
                        ),
                        const.DATA_CHALLENGE_ICON: user_input.get(
                            const.CFOF_CHALLENGES_INPUT_ICON,
                            const.DEFAULT_CHALLENGES_ICON,
                        ),
                        const.DATA_CHALLENGE_ASSIGNED_KIDS: user_input[
                            const.CFOF_CHALLENGES_INPUT_ASSIGNED_KIDS
                        ],
                        const.DATA_CHALLENGE_TYPE: _type,
                        const.DATA_CHALLENGE_SELECTED_CHORE_ID: final_chore_id,
                        const.DATA_CHALLENGE_CRITERIA: user_input.get(
                            const.CFOF_CHALLENGES_INPUT_CRITERIA, const.CONF_EMPTY
                        ).strip(),
                        const.DATA_CHALLENGE_TARGET_VALUE: user_input[
                            const.CFOF_CHALLENGES_INPUT_TARGET_VALUE
                        ],
                        const.DATA_CHALLENGE_REWARD_POINTS: user_input[
                            const.CFOF_CHALLENGES_INPUT_REWARD_POINTS
                        ],
                        const.DATA_CHALLENGE_START_DATE: start_date,
                        const.DATA_CHALLENGE_END_DATE: end_date,
                        const.DATA_CHALLENGE_INTERNAL_ID: internal_id,
                        const.DATA_CHALLENGE_PROGRESS: {},
                    }
                    self._challenge_index += 1
                    if self._challenge_index >= self._challenge_count:
                        return await self.async_step_finish()
                    return await self.async_step_challenges()

        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in self._kids_temp.items()
        }
        all_chores = self._chores_temp
        default_data = user_input if user_input else None
        challenge_schema = fh.build_challenge_schema(
            kids_dict=kids_dict,
            chores_dict=all_chores,
            default=default_data,
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_CHALLENGES,
            data_schema=challenge_schema,
            errors=errors,
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
            kid_id: data[const.DATA_KID_NAME]
            for kid_id, data in self._kids_temp.items()
        }

        # Enhance parents summary to include associated kids by name
        parents_summary = []
        for parent in self._parents_temp.values():
            associated_kids_names = [
                kid_id_to_name.get(kid_id, const.UNKNOWN_KID)
                for kid_id in parent.get(const.DATA_PARENT_ASSOCIATED_KIDS, [])
            ]
            if associated_kids_names:
                kids_str = ", ".join(associated_kids_names)
                parents_summary.append(
                    f"{parent[const.DATA_PARENT_NAME]} (Kids: {kids_str})"
                )
            else:
                parents_summary.append(parent[const.DATA_PARENT_NAME])

        summary = (
            f"{const.TRANS_KEY_CFOF_SUMMARY_KIDS}{', '.join(kid_data[const.DATA_KID_NAME] for kid_data in self._kids_temp.values()) or const.CONF_NONE_TEXT}\n\n"
            f"{const.TRANS_KEY_CFOF_SUMMARY_PARENTS}{', '.join(parents_summary) or const.CONF_NONE_TEXT}\n\n"
            f"{const.TRANS_KEY_CFOF_SUMMARY_CHORES}{', '.join(chore_data[const.DATA_CHORE_NAME] for chore_data in self._chores_temp.values()) or const.CONF_NONE_TEXT}\n\n"
            f"{const.TRANS_KEY_CFOF_SUMMARY_BADGES}{', '.join(badge_data[const.DATA_BADGE_NAME] for badge_data in self._badges_temp.values()) or const.CONF_NONE_TEXT}\n\n"
            f"{const.TRANS_KEY_CFOF_SUMMARY_REWARDS}{', '.join(reward_data[const.DATA_REWARD_NAME] for reward_data in self._rewards_temp.values()) or const.CONF_NONE_TEXT}\n\n"
            f"{const.TRANS_KEY_CFOF_SUMMARY_PENALTIES}{', '.join(penalty_data[const.DATA_PENALTY_NAME] for penalty_data in self._penalties_temp.values()) or const.CONF_NONE_TEXT}\n\n"
            f"{const.TRANS_KEY_CFOF_SUMMARY_BONUSES}{', '.join(bonus_data[const.DATA_BONUS_NAME] for bonus_data in self._bonuses_temp.values()) or const.CONF_NONE_TEXT}\n\n"
            f"{const.TRANS_KEY_CFOF_SUMMARY_ACHIEVEMENTS}{', '.join(achievement_data[const.DATA_ACHIEVEMENT_NAME] for achievement_data in self._achievements_temp.values()) or const.CONF_NONE_TEXT}\n\n"
            f"{const.TRANS_KEY_CFOF_SUMMARY_CHALLENGES}{', '.join(challenge_data[const.DATA_CHALLENGE_NAME] for challenge_data in self._challenges_temp.values()) or const.CONF_NONE_TEXT}\n\n"
        )
        return self.async_show_form(
            step_id=const.CONFIG_FLOW_STEP_FINISH,
            data_schema=vol.Schema({}),
            description_placeholders={const.OPTIONS_FLOW_PLACEHOLDER_SUMMARY: summary},
        )

    def _create_entry(self):
        """Finalize config entry with data and options using internal_id as keys."""
        entry_data = {}
        entry_options = {
            const.CONF_POINTS_LABEL: self._data.get(
                const.CONF_POINTS_LABEL, const.DEFAULT_POINTS_LABEL
            ),
            const.CONF_POINTS_ICON: self._data.get(
                const.CONF_POINTS_ICON, const.DEFAULT_POINTS_ICON
            ),
            const.CONF_KIDS: self._kids_temp,
            const.CONF_PARENTS: self._parents_temp,
            const.CONF_CHORES: self._chores_temp,
            const.CONF_BADGES: self._badges_temp,
            const.CONF_REWARDS: self._rewards_temp,
            const.CONF_PENALTIES: self._penalties_temp,
            const.CONF_BONUSES: self._bonuses_temp,
            const.CONF_ACHIEVEMENTS: self._achievements_temp,
            const.CONF_CHALLENGES: self._challenges_temp,
        }

        const.LOGGER.debug(
            "Creating entry with data=%s, options=%s", entry_data, entry_options
        )
        return self.async_create_entry(
            title=const.KIDSCHORES_TITLE, data=entry_data, options=entry_options
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the Options Flow."""
        from .options_flow import KidsChoresOptionsFlowHandler

        return KidsChoresOptionsFlowHandler(config_entry)
