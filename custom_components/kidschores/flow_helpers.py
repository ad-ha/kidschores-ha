# File: flow_helpers.py
"""Helpers for the KidsChores integration's Config and Options flow.

Provides schema builders and input-processing logic for internal_id-based management.
"""

import datetime
import uuid
import voluptuous as vol
from . import const
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector, config_validation as cv
from homeassistant.util import dt as dt_util

# ----------------------------------------------------------------------------------
# POINTS SCHEMA
# ----------------------------------------------------------------------------------


def build_points_schema(
    default_label=const.DEFAULT_POINTS_LABEL, default_icon=const.DEFAULT_POINTS_ICON
):
    """Build a schema for points label & icon."""
    return vol.Schema(
        {
            vol.Required(const.CONF_POINTS_LABEL, default=default_label): str,
            vol.Optional(
                const.CONF_POINTS_ICON, default=default_icon
            ): selector.IconSelector(),
        }
    )


# ----------------------------------------------------------------------------------
# KIDS SCHEMA
# ----------------------------------------------------------------------------------


def build_kid_schema(
    hass,
    users,
    default_kid_name=const.CONF_EMPTY,
    default_ha_user_id=None,
    internal_id=None,
    default_enable_mobile_notifications=False,
    default_mobile_notify_service=None,
    default_enable_persistent_notifications=False,
):
    """Build a Voluptuous schema for adding/editing a Kid, keyed by internal_id in the dict."""
    user_options = [{"value": const.CONF_EMPTY, "label": const.LABEL_NONE}] + [
        {"value": user.id, "label": user.name} for user in users
    ]
    notify_options = [
        {"value": const.CONF_EMPTY, "label": const.LABEL_NONE}
    ] + _get_notify_services(hass)

    return vol.Schema(
        {
            vol.Required(const.CFOF_KIDS_INPUT_KID_NAME, default=default_kid_name): str,
            vol.Optional(
                const.CONF_HA_USER, default=default_ha_user_id or const.CONF_EMPTY
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=user_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False,
                )
            ),
            vol.Required(
                const.CONF_ENABLE_MOBILE_NOTIFICATIONS,
                default=default_enable_mobile_notifications,
            ): selector.BooleanSelector(),
            vol.Optional(
                const.CONF_MOBILE_NOTIFY_SERVICE,
                default=default_mobile_notify_service or const.CONF_EMPTY,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=notify_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False,
                )
            ),
            vol.Required(
                const.CONF_ENABLE_PERSISTENT_NOTIFICATIONS,
                default=default_enable_persistent_notifications,
            ): selector.BooleanSelector(),
            vol.Required(
                const.CONF_INTERNAL_ID, default=internal_id or str(uuid.uuid4())
            ): str,
        }
    )


# ----------------------------------------------------------------------------------
# PARENTS SCHEMA
# ----------------------------------------------------------------------------------


def build_parent_schema(
    hass,
    users,
    kids_dict,
    default_parent_name=const.CONF_EMPTY,
    default_ha_user_id=None,
    default_associated_kids=None,
    default_enable_mobile_notifications=False,
    default_mobile_notify_service=None,
    default_enable_persistent_notifications=False,
    internal_id=None,
):
    """Build a Voluptuous schema for adding/editing a Parent, keyed by internal_id in the dict."""
    user_options = [{"value": const.CONF_EMPTY, "label": const.LABEL_NONE}] + [
        {"value": user.id, "label": user.name} for user in users
    ]
    kid_options = [
        {"value": kid_id, "label": kid_name} for kid_name, kid_id in kids_dict.items()
    ]
    notify_options = [
        {"value": const.CONF_EMPTY, "label": const.LABEL_NONE}
    ] + _get_notify_services(hass)

    return vol.Schema(
        {
            vol.Required(const.CONF_PARENT_NAME, default=default_parent_name): str,
            vol.Optional(
                const.CONF_HA_USER_ID, default=default_ha_user_id or const.CONF_EMPTY
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=user_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False,
                )
            ),
            vol.Optional(
                const.CONF_ASSOCIATED_KIDS,
                default=default_associated_kids or [],
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=kid_options,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_ASSOCIATED_KIDS,
                    multiple=True,
                )
            ),
            vol.Required(
                const.CONF_ENABLE_MOBILE_NOTIFICATIONS,
                default=default_enable_mobile_notifications,
            ): selector.BooleanSelector(),
            vol.Optional(
                const.CONF_MOBILE_NOTIFY_SERVICE,
                default=default_mobile_notify_service or const.CONF_EMPTY,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=notify_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False,
                )
            ),
            vol.Required(
                const.CONF_ENABLE_PERSISTENT_NOTIFICATIONS,
                default=default_enable_persistent_notifications,
            ): selector.BooleanSelector(),
            vol.Required(
                const.CONF_INTERNAL_ID, default=internal_id or str(uuid.uuid4())
            ): str,
        }
    )


# ----------------------------------------------------------------------------------
# CHORES SCHEMA
# ----------------------------------------------------------------------------------


def build_chore_schema(kids_dict, default=None):
    """Build a schema for chores, referencing existing kids by name.

    Uses internal_id for entity management.
    """
    default = default or {}
    chore_name_default = default.get(const.CONF_NAME, const.CONF_EMPTY)
    internal_id_default = default.get(const.CONF_INTERNAL_ID, str(uuid.uuid4()))

    kid_choices = {k: k for k in kids_dict}

    return vol.Schema(
        {
            vol.Required(const.CONF_CHORE_NAME, default=chore_name_default): str,
            vol.Optional(
                const.CONF_CHORE_DESCRIPTION,
                default=default.get(const.CONF_DESCRIPTION, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_CHORE_LABELS,
                default=default.get(const.CONF_CHORE_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Required(
                const.CONF_DEFAULT_POINTS,
                default=default.get(const.CONF_DEFAULT_POINTS, const.DEFAULT_POINTS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=0.1,
                )
            ),
            vol.Required(
                const.CONF_ASSIGNED_KIDS,
                default=default.get(const.CONF_ASSIGNED_KIDS, []),
            ): cv.multi_select(kid_choices),
            vol.Required(
                const.CONF_SHARED_CHORE,
                default=default.get(const.CONF_SHARED_CHORE, False),
            ): selector.BooleanSelector(),
            vol.Required(
                const.CONF_ALLOW_MULTIPLE_CLAIMS_PER_DAY,
                default=default.get(const.CONF_ALLOW_MULTIPLE_CLAIMS_PER_DAY, False),
            ): selector.BooleanSelector(),
            vol.Required(
                const.CONF_PARTIAL_ALLOWED,
                default=default.get(const.CONF_PARTIAL_ALLOWED, False),
            ): selector.BooleanSelector(),
            vol.Optional(
                const.CONF_ICON, default=default.get(const.CONF_ICON, const.CONF_EMPTY)
            ): selector.IconSelector(),
            vol.Required(
                const.CONF_RECURRING_FREQUENCY,
                default=default.get(
                    const.CONF_RECURRING_FREQUENCY, const.FREQUENCY_NONE
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.FREQUENCY_OPTIONS,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_RECURRING_FREQUENCY,
                )
            ),
            vol.Optional(
                const.CONF_CUSTOM_INTERVAL,
                default=default.get(const.CONF_CUSTOM_INTERVAL, None),
            ): vol.Any(
                None,
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX, min=1, step=1
                    )
                ),
            ),
            vol.Optional(
                const.CONF_CUSTOM_INTERVAL_UNIT,
                default=default.get(const.CONF_CUSTOM_INTERVAL_UNIT, None),
            ): vol.Any(
                None,
                selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=const.CUSTOM_INTERVAL_UNIT_OPTIONS,
                        translation_key=const.TRANS_KEY_FLOW_HELPERS_CUSTOM_INTERVAL_UNIT,
                        multiple=False,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            ),
            vol.Optional(
                const.CONF_APPLICABLE_DAYS,
                default=default.get(
                    const.CONF_APPLICABLE_DAYS, const.DEFAULT_APPLICABLE_DAYS
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": key, "label": const.WEEKDAY_OPTIONS[key]}
                        for key in const.WEEKDAY_OPTIONS
                    ],
                    multiple=True,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_APPLICABLE_DAYS,
                )
            ),
            vol.Optional(
                const.CONF_DUE_DATE, default=default.get(const.CONF_DUE_DATE)
            ): vol.Any(None, selector.DateTimeSelector()),
            vol.Optional(
                const.CONF_NOTIFY_ON_CLAIM,
                default=default.get(
                    const.CONF_NOTIFY_ON_CLAIM, const.DEFAULT_NOTIFY_ON_CLAIM
                ),
            ): selector.BooleanSelector(),
            vol.Optional(
                const.CONF_NOTIFY_ON_APPROVAL,
                default=default.get(
                    const.CONF_NOTIFY_ON_APPROVAL, const.DEFAULT_NOTIFY_ON_APPROVAL
                ),
            ): selector.BooleanSelector(),
            vol.Optional(
                const.CONF_NOTIFY_ON_DISAPPROVAL,
                default=default.get(
                    const.CONF_NOTIFY_ON_DISAPPROVAL,
                    const.DEFAULT_NOTIFY_ON_DISAPPROVAL,
                ),
            ): selector.BooleanSelector(),
            vol.Required(const.CONF_INTERNAL_ID, default=internal_id_default): str,
        }
    )


# ----------------------------------------------------------------------------------
# BADGES SCHEMAS
# ----------------------------------------------------------------------------------


def build_badge_cumulative_schema(default: dict = None, rewards_list: list = None):
    """Build schema for cumulative badges (by points or chore count)."""
    default = default or {}
    rewards_list = rewards_list or [
        {"value": const.CONF_EMPTY, "label": const.LABEL_NONE}
    ]
    internal_id_default = default.get(const.CONF_INTERNAL_ID, str(uuid.uuid4()))

    return vol.Schema(
        {
            vol.Required(
                const.CONF_BADGE_NAME,
                default=default.get(const.CONF_NAME, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_BADGE_DESCRIPTION,
                default=default.get(const.CONF_DESCRIPTION, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_BADGE_LABELS,
                default=default.get(const.CONF_BADGE_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Optional(
                const.CONF_ICON, default=default.get(const.CONF_ICON, const.CONF_EMPTY)
            ): selector.IconSelector(),
            vol.Required(
                const.CONF_BADGE_THRESOLD_VALUE,
                default=default.get(
                    const.CONF_BADGE_THRESOLD_VALUE, const.DEFAULT_BADGE_THRESHOLD_VALUE
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=1,
                )
            ),
            vol.Required(
                const.CONF_BADGE_AWARD_MODE,
                default=default.get(
                    const.CONF_BADGE_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.AWARD_MODE_OPTIONS,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_AWARD_MODE,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_AWARD_POINTS,
                default=default.get(
                    const.CONF_BADGE_AWARD_POINTS, const.DEFAULT_BADGE_AWARD_POINTS
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=1,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_AWARD_REWARD,
                default=default.get(const.CONF_BADGE_AWARD_REWARD, const.CONF_EMPTY),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=rewards_list,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_AWARD_REWARD,
                )
            ),
            vol.Required(
                const.CONF_BADGE_POINTS_MULTIPLIER,
                default=default.get(
                    const.CONF_BADGE_POINTS_MULTIPLIER, const.DEFAULT_POINTS_MULTIPLIER
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    step=0.01,
                    min=1.0,
                )
            ),
            vol.Required(
                const.CONF_BADGE_RESET_PERIODICALLY,
                default=default.get(const.CONF_BADGE_RESET_PERIODICALLY, False),
            ): selector.BooleanSelector(),
            vol.Optional(
                const.CONF_BADGE_RESET_PERIOD,
                default=default.get(const.CONF_BADGE_RESET_PERIOD, const.CONF_YEAR_END),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.BADGE_CUMULATIVE_RESET_PERIOD_OPTIONS,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_RESET_PERIOD,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_RESET_GRACE_PERIOD,
                default=default.get(
                    const.CONF_BADGE_RESET_GRACE_PERIOD,
                    const.DEFAULT_BADGE_RESET_GRACE_PERIOD,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=1,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_MAINTENANCE_RULES,
                default=default.get(
                    const.CONF_BADGE_MAINTENANCE_RULES, const.CONF_EMPTY
                ),
            ): str,
            vol.Required(
                const.CONF_BADGE_TYPE,
                default=default.get(const.CONF_BADGE_TYPE, const.BADGE_TYPE_CUMULATIVE),
            ): str,
            vol.Required(const.CONF_INTERNAL_ID, default=internal_id_default): str,
        }
    )


def build_badge_daily_schema(default: dict = None, rewards_list: list = None):
    """Build schema for daily badges that reset every day."""
    default = default or {}
    rewards_list = rewards_list or [
        {"value": const.CONF_EMPTY, "label": const.LABEL_NONE}
    ]
    internal_id_default = default.get(const.CONF_INTERNAL_ID, str(uuid.uuid4()))

    return vol.Schema(
        {
            vol.Required(
                const.CONF_BADGE_NAME,
                default=default.get(const.CONF_NAME, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_BADGE_DESCRIPTION,
                default=default.get(const.CONF_DESCRIPTION, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_BADGE_LABELS,
                default=default.get(const.CONF_BADGE_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Optional(
                const.CONF_ICON, default=default.get(const.CONF_ICON, const.CONF_EMPTY)
            ): selector.IconSelector(),
            vol.Required(
                const.CONF_BADGE_DAILY_THRESHOLD_TYPE,
                default=default.get(
                    const.CONF_BADGE_DAILY_THRESHOLD_TYPE,
                    const.DEFAULT_BADGE_THRESOLD_TYPE,
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.THRESHOLD_TYPE_OPTIONS,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_DAILY_THRESHOLD_TYPE,
                )
            ),
            vol.Required(
                const.CONF_BADGE_DAILY_THRESHOLD,
                default=default.get(
                    const.CONF_BADGE_DAILY_THRESHOLD,
                    const.DEFAULT_BADGE_DAILY_THRESHOLD,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=1,
                )
            ),
            vol.Required(
                const.CONF_BADGE_AWARD_MODE,
                default=default.get(
                    const.CONF_BADGE_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.AWARD_MODE_OPTIONS,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_AWARD_MODE,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_AWARD_POINTS,
                default=default.get(
                    const.CONF_BADGE_AWARD_POINTS, const.DEFAULT_BADGE_AWARD_POINTS
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=1,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_AWARD_REWARD,
                default=default.get(const.CONF_BADGE_AWARD_REWARD, const.CONF_EMPTY),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=rewards_list,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_AWARD_REWARD,
                )
            ),
            vol.Required(
                const.CONF_BADGE_TYPE,
                default=default.get(const.CONF_BADGE_TYPE, const.BADGE_TYPE_DAILY),
            ): str,
            vol.Required(const.CONF_INTERNAL_ID, default=internal_id_default): str,
        }
    )


def build_badge_periodic_schema(
    default: dict = None, rewards_list: list = None, chores_list: list = None
):
    """Build schema for periodic badges (e.g. weekly or monthly)."""
    default = default or {}

    rewards_list = [
        {"value": const.CONF_EMPTY, "label": const.LABEL_NONE}
    ] + rewards_list
    chores_list = [{"value": const.CONF_EMPTY, "label": const.LABEL_NONE}] + chores_list
    internal_id_default = default.get(const.CONF_INTERNAL_ID, str(uuid.uuid4()))

    return vol.Schema(
        {
            vol.Required(
                const.CONF_BADGE_NAME,
                default=default.get(const.CONF_NAME, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_BADGE_DESCRIPTION,
                default=default.get(const.CONF_DESCRIPTION, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_BADGE_LABELS,
                default=default.get(const.CONF_BADGE_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Optional(
                const.CONF_ICON, default=default.get(const.CONF_ICON, const.CONF_EMPTY)
            ): selector.IconSelector(),
            vol.Required(
                const.CONF_BADGE_RESET_SCHEDULE,
                default=default.get(const.CONF_BADGE_RESET_SCHEDULE, const.CONF_WEEKLY),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.BADGE_RESET_SCHEDULE_OPTIONS,
                    translation_key=const.TRANS_KEY_CFOP_RESET_SCHEDULE,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_START_DATE,
                default=default.get(const.CONF_BADGE_START_DATE, None),
            ): selector.DateSelector(),
            vol.Optional(
                const.CONF_BADGE_END_DATE,
                default=default.get(const.CONF_BADGE_END_DATE, None),
            ): selector.DateSelector(),
            vol.Optional(
                const.CONF_BADGE_PERIODIC_RECURRENT,
                default=default.get(const.CONF_BADGE_PERIODIC_RECURRENT, False),
            ): selector.BooleanSelector(),
            vol.Required(
                const.CONF_BADGE_THRESHOLD_TYPE,
                default=default.get(
                    const.CONF_BADGE_THRESHOLD_TYPE, const.DEFAULT_BADGE_THRESOLD_TYPE
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.THRESHOLD_TYPE_OPTIONS,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_THRESHOLD_TYPE,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_REQUIRED_CHORES,
                default=default.get(const.CONF_BADGE_REQUIRED_CHORES, []),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=chores_list,
                    multiple=True,
                    translation_key=const.TRANS_KEY_CFOF_REQUIRED_CHORES,
                )
            ),
            vol.Required(
                const.CONF_BADGE_THRESOLD_VALUE,
                default=default.get(
                    const.CONF_BADGE_THRESOLD_VALUE, const.DEFAULT_BADGE_THRESHOLD_VALUE
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=1,
                )
            ),
            vol.Required(
                const.CONF_BADGE_AWARD_MODE,
                default=default.get(
                    const.CONF_BADGE_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.AWARD_MODE_OPTIONS,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_AWARD_MODE,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_AWARD_POINTS,
                default=default.get(
                    const.CONF_BADGE_AWARD_POINTS, const.DEFAULT_BADGE_AWARD_POINTS
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=1,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_AWARD_REWARD,
                default=default.get(const.CONF_BADGE_AWARD_REWARD, const.CONF_EMPTY),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=rewards_list,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_AWARD_REWARD,
                )
            ),
            vol.Required(
                const.CONF_BADGE_TYPE,
                default=default.get(const.CONF_BADGE_TYPE, const.BADGE_TYPE_PERIODIC),
            ): str,
            vol.Required(const.CONF_INTERNAL_ID, default=internal_id_default): str,
        }
    )


def build_badge_achievement_schema(
    default: dict = None, achievements_list: list = None, rewards_list: list = None
):
    """Build schema for achievement‑linked badges."""
    default = default or {}
    internal_id_default = default.get(const.CONF_INTERNAL_ID, str(uuid.uuid4()))
    achievements_list = [
        {"value": const.CONF_EMPTY, "label": const.LABEL_NONE}
    ] + achievements_list
    rewards_list = [
        {"value": const.CONF_EMPTY, "label": const.LABEL_NONE}
    ] + rewards_list

    return vol.Schema(
        {
            vol.Required(
                const.CONF_BADGE_NAME,
                default=default.get(const.CONF_NAME, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_BADGE_DESCRIPTION,
                default=default.get(const.CONF_DESCRIPTION, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_BADGE_LABELS,
                default=default.get(const.CONF_BADGE_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Optional(
                const.CONF_ICON, default=default.get(const.CONF_ICON, const.CONF_EMPTY)
            ): selector.IconSelector(),
            vol.Required(
                const.CONF_BADGE_ASSOCIATED_ACHIEVEMENT,
                default=default.get(
                    const.CONF_BADGE_ASSOCIATED_ACHIEVEMENT, const.CONF_EMPTY
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=achievements_list,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_ASSOCIATED_ACHIEVEMENT,
                )
            ),
            vol.Required(
                const.CONF_BADGE_AWARD_MODE,
                default=default.get(
                    const.CONF_BADGE_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.AWARD_MODE_OPTIONS,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_AWARD_MODE,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_AWARD_POINTS,
                default=default.get(
                    const.CONF_BADGE_AWARD_POINTS, const.DEFAULT_BADGE_AWARD_POINTS
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=1,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_AWARD_REWARD,
                default=default.get(const.CONF_BADGE_AWARD_REWARD, const.CONF_EMPTY),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=rewards_list,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_AWARD_REWARD,
                )
            ),
            vol.Required(
                const.CONF_BADGE_TYPE,
                default=default.get(
                    const.CONF_BADGE_TYPE, const.BADGE_TYPE_ACHIEVEMENT_LINKED
                ),
            ): str,
            vol.Required(const.CONF_INTERNAL_ID, default=internal_id_default): str,
        }
    )


def build_badge_challenge_schema(
    default: dict = None, challenges_list: list = None, rewards_list: list = None
):
    """Build schema for challenge‑linked badges."""
    default = default or {}
    internal_id_default = default.get(const.CONF_INTERNAL_ID, str(uuid.uuid4()))
    challenges_list = [
        {"value": const.CONF_EMPTY, "label": const.LABEL_NONE}
    ] + challenges_list
    rewards_list = [
        {"value": const.CONF_EMPTY, "label": const.LABEL_NONE}
    ] + rewards_list

    return vol.Schema(
        {
            vol.Required(
                const.CONF_BADGE_NAME,
                default=default.get(const.CONF_NAME, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_BADGE_DESCRIPTION,
                default=default.get(const.CONF_DESCRIPTION, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_BADGE_LABELS,
                default=default.get(const.CONF_BADGE_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Optional(
                const.CONF_ICON, default=default.get(const.CONF_ICON, const.CONF_EMPTY)
            ): selector.IconSelector(),
            vol.Required(
                const.CONF_BADGE_ASSOCIATED_CHALLENGE,
                default=default.get(
                    const.CONF_BADGE_ASSOCIATED_CHALLENGE, const.CONF_EMPTY
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=challenges_list,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_ASSOCIATED_CHALLENGE,
                )
            ),
            vol.Required(
                const.CONF_BADGE_AWARD_MODE,
                default=default.get(
                    const.CONF_BADGE_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.AWARD_MODE_OPTIONS,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_AWARD_MODE,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_AWARD_POINTS,
                default=default.get(
                    const.CONF_BADGE_AWARD_POINTS, const.DEFAULT_BADGE_AWARD_POINTS
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=1,
                )
            ),
            vol.Optional(
                const.CONF_BADGE_AWARD_REWARD,
                default=default.get(const.CONF_BADGE_AWARD_REWARD, const.CONF_EMPTY),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=rewards_list,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_AWARD_REWARD,
                )
            ),
            vol.Required(
                const.CONF_BADGE_TYPE,
                default=default.get(
                    const.CONF_BADGE_TYPE, const.BADGE_TYPE_CHALLENGE_LINKED
                ),
            ): str,
            vol.Required(const.CONF_INTERNAL_ID, default=internal_id_default): str,
        }
    )


def build_badge_special_occasions_schema(default: dict = None):
    """Build schema for special occasion badges."""
    default = default or {}
    internal_id_default = default.get(const.CONF_INTERNAL_ID, str(uuid.uuid4()))
    return vol.Schema(
        {
            vol.Required(
                const.CONF_BADGE_NAME,
                default=default.get(const.CONF_NAME, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_BADGE_DESCRIPTION,
                default=default.get(const.CONF_DESCRIPTION, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_BADGE_LABELS,
                default=default.get(const.CONF_BADGE_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Optional(
                const.CONF_ICON, default=default.get(const.CONF_ICON, const.CONF_EMPTY)
            ): selector.IconSelector(),
            vol.Required(
                const.CONF_BADGE_OCCASION_TYPE,
                default=default.get(const.CONF_BADGE_OCCASION_TYPE, const.CONF_HOLIDAY),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.OCCASION_TYPE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_OCCASION_TYPE,
                )
            ),
            vol.Required(
                const.CONF_BADGE_OCCASION_DATE,
                default=default.get(const.CONF_BADGE_OCCASION_DATE, const.CONF_EMPTY),
            ): selector.DateSelector(),
            vol.Required(
                const.CONF_BADGE_SPECIAL_OCCASION_RECURRENCY,
                default=default.get(
                    const.CONF_BADGE_SPECIAL_OCCASION_RECURRENCY, False
                ),
            ): selector.BooleanSelector(),
            vol.Required(
                const.CONF_BADGE_TYPE,
                default=default.get(
                    const.CONF_BADGE_TYPE, const.BADGE_TYPE_SPECIAL_OCCASION
                ),
            ): str,
            vol.Required(const.CONF_INTERNAL_ID, default=internal_id_default): str,
        }
    )


# ----------------------------------------------------------------------------------
# REWARDS SCHEMA
# ----------------------------------------------------------------------------------


def build_reward_schema(default=None):
    """Build a schema for rewards, keyed by internal_id in the dict."""
    default = default or {}
    reward_name_default = default.get(const.CONF_NAME, const.CONF_EMPTY)
    internal_id_default = default.get(const.CONF_INTERNAL_ID, str(uuid.uuid4()))

    return vol.Schema(
        {
            vol.Required(const.CONF_REWARD_NAME, default=reward_name_default): str,
            vol.Optional(
                const.CONF_REWARD_DESCRIPTION,
                default=default.get(const.CONF_DESCRIPTION, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_REWARD_LABELS,
                default=default.get(const.CONF_REWARD_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Required(
                const.CONF_REWARD_COST,
                default=default.get(const.CONF_COST, const.DEFAULT_REWARD_COST),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=0.1,
                )
            ),
            vol.Optional(
                const.CONF_ICON, default=default.get(const.CONF_ICON, const.CONF_EMPTY)
            ): selector.IconSelector(),
            vol.Required(const.CONF_INTERNAL_ID, default=internal_id_default): str,
        }
    )


# ----------------------------------------------------------------------------------
# BONUSES SCHEMA
# ----------------------------------------------------------------------------------


def build_bonus_schema(default=None):
    """Build a schema for bonuses, keyed by internal_id in the dict.

    Stores bonus_points as positive in the form, converted to negative internally.
    """
    default = default or {}
    bonus_name_default = default.get(const.CONF_NAME, const.CONF_EMPTY)
    internal_id_default = default.get(const.CONF_INTERNAL_ID, str(uuid.uuid4()))

    # Display bonus points as positive for user input
    display_points = (
        abs(default.get(const.CONF_POINTS, const.DEFAULT_BONUS_POINTS))
        if default
        else const.DEFAULT_BONUS_POINTS
    )

    return vol.Schema(
        {
            vol.Required(const.CONF_BONUS_NAME, default=bonus_name_default): str,
            vol.Optional(
                const.CONF_BONUS_DESCRIPTION,
                default=default.get(const.CONF_DESCRIPTION, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_BONUS_LABELS,
                default=default.get(const.CONF_BONUS_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Required(
                const.CONF_BONUS_POINTS, default=display_points
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=0.1,
                )
            ),
            vol.Optional(
                const.CONF_ICON, default=default.get(const.CONF_ICON, const.CONF_EMPTY)
            ): selector.IconSelector(),
            vol.Required(const.CONF_INTERNAL_ID, default=internal_id_default): str,
        }
    )


# ----------------------------------------------------------------------------------
# PENALTIES SCHEMA
# ----------------------------------------------------------------------------------


def build_penalty_schema(default=None):
    """Build a schema for penalties, keyed by internal_id in the dict.

    Stores penalty_points as positive in the form, converted to negative internally.
    """
    default = default or {}
    penalty_name_default = default.get(const.CONF_NAME, const.CONF_EMPTY)
    internal_id_default = default.get(const.CONF_INTERNAL_ID, str(uuid.uuid4()))

    # Display penalty points as positive for user input
    display_points = (
        abs(default.get(const.CONF_POINTS, const.DEFAULT_PENALTY_POINTS))
        if default
        else const.DEFAULT_PENALTY_POINTS
    )

    return vol.Schema(
        {
            vol.Required(const.CONF_PENALTY_NAME, default=penalty_name_default): str,
            vol.Optional(
                const.CONF_PENALTY_DESCRIPTION,
                default=default.get(const.CONF_DESCRIPTION, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_PENALTY_LABELS,
                default=default.get(const.CONF_PENALTY_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Required(
                const.CONF_PENALTY_POINTS, default=display_points
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=0.1,
                )
            ),
            vol.Optional(
                const.CONF_ICON, default=default.get(const.CONF_ICON, const.CONF_EMPTY)
            ): selector.IconSelector(),
            vol.Required(const.CONF_INTERNAL_ID, default=internal_id_default): str,
        }
    )


# ----------------------------------------------------------------------------------
# ACHIEVEMENTS SCHEMA
# ----------------------------------------------------------------------------------


def build_achievement_schema(kids_dict, chores_dict, default=None):
    """Build a schema for achievements, keyed by internal_id."""
    default = default or {}
    achievement_name_default = default.get(const.CONF_NAME, const.CONF_EMPTY)
    internal_id_default = default.get(const.CONF_INTERNAL_ID, str(uuid.uuid4()))

    kid_options = [
        {"value": kid_id, "label": kid_name} for kid_name, kid_id in kids_dict.items()
    ]

    chore_options = [{"value": const.CONF_EMPTY, "label": const.LABEL_NONE}]
    for chore_id, chore_data in chores_dict.items():
        chore_name = chore_data.get(const.CONF_NAME, f"Chore {chore_id[:6]}")
        chore_options.append({"value": chore_id, "label": chore_name})

    default_selected_chore = default.get(
        const.CONF_ACHIEVEMENT_SELECTED_CHORE_ID, const.CONF_EMPTY
    )
    if not default_selected_chore or default_selected_chore not in [
        option["value"] for option in chore_options
    ]:
        pass

    default_criteria = default.get(const.CONF_ACHIEVEMENT_CRITERIA, const.CONF_EMPTY)
    default_assigned_kids = default.get(const.CONF_ACHIEVEMENT_ASSIGNED_KIDS, [])
    if not isinstance(default_assigned_kids, list):
        default_assigned_kids = [default_assigned_kids]

    return vol.Schema(
        {
            vol.Required(const.CONF_NAME, default=achievement_name_default): str,
            vol.Optional(
                const.CONF_DESCRIPTION,
                default=default.get(const.CONF_DESCRIPTION, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_ACHIEVEMENT_LABELS,
                default=default.get(const.CONF_ACHIEVEMENT_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Optional(
                const.CONF_ICON, default=default.get(const.CONF_ICON, const.CONF_EMPTY)
            ): selector.IconSelector(),
            vol.Required(
                const.CONF_ACHIEVEMENT_ASSIGNED_KIDS, default=default_assigned_kids
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=kid_options,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_ASSIGNED_KIDS,
                    multiple=True,
                )
            ),
            vol.Required(
                const.CONF_ACHIEVEMENT_TYPE,
                default=default.get(
                    const.CONF_ACHIEVEMENT_TYPE, const.ACHIEVEMENT_TYPE_STREAK
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.ACHIEVEMENT_TYPE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            # If type == "chore_streak", let the user choose the chore to track:
            vol.Optional(
                const.CONF_ACHIEVEMENT_SELECTED_CHORE_ID, default=default_selected_chore
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=chore_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False,
                )
            ),
            # For non-streak achievements the user can type criteria freely:
            vol.Optional(
                const.CONF_ACHIEVEMENT_CRITERIA, default=default_criteria
            ): str,
            vol.Required(
                const.CONF_ACHIEVEMENT_TARGET_VALUE,
                default=default.get(
                    const.CONF_ACHIEVEMENT_TARGET_VALUE,
                    const.DEFAULT_ACHIEVEMENT_TARGET,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=0.1,
                )
            ),
            vol.Required(
                const.CONF_ACHIEVEMENT_REWARD_POINTS,
                default=default.get(
                    const.CONF_ACHIEVEMENT_REWARD_POINTS,
                    const.DEFAULT_ACHIEVEMENT_REWARD_POINTS,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=0.1,
                )
            ),
            vol.Required(const.CONF_INTERNAL_ID, default=internal_id_default): str,
        }
    )


# ----------------------------------------------------------------------------------
# CHALLENGES SCHEMA
# ----------------------------------------------------------------------------------


def build_challenge_schema(kids_dict, chores_dict, default=None):
    """Build a schema for challenges, keyed by internal_id."""
    default = default or {}
    challenge_name_default = default.get(const.CONF_NAME, const.CONF_EMPTY)
    internal_id_default = default.get(const.CONF_INTERNAL_ID, str(uuid.uuid4()))

    kid_options = [
        {"value": kid_id, "label": kid_name} for kid_name, kid_id in kids_dict.items()
    ]

    chore_options = [{"value": const.CONF_EMPTY, "label": const.LABEL_NONE}]
    for chore_id, chore_data in chores_dict.items():
        chore_name = chore_data.get(const.CONF_NAME, f"Chore {chore_id[:6]}")
        chore_options.append({"value": chore_id, "label": chore_name})

    default_selected_chore = default.get(
        const.CONF_CHALLENGE_SELECTED_CHORE_ID, const.CONF_EMPTY
    )
    available_values = [option["value"] for option in chore_options]
    if default_selected_chore not in available_values:
        default_selected_chore = ""

    default_criteria = default.get(const.CONF_CHALLENGE_CRITERIA, const.CONF_EMPTY)
    default_assigned_kids = default.get(const.CONF_CHALLENGE_ASSIGNED_KIDS, [])
    if not isinstance(default_assigned_kids, list):
        default_assigned_kids = [default_assigned_kids]

    return vol.Schema(
        {
            vol.Required(const.CONF_NAME, default=challenge_name_default): str,
            vol.Optional(
                const.CONF_DESCRIPTION,
                default=default.get(const.CONF_DESCRIPTION, const.CONF_EMPTY),
            ): str,
            vol.Optional(
                const.CONF_CHALLENGE_LABELS,
                default=default.get(const.CONF_CHALLENGE_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Optional(
                const.CONF_ICON, default=default.get(const.CONF_ICON, const.CONF_EMPTY)
            ): selector.IconSelector(),
            vol.Required(
                const.CONF_CHALLENGE_ASSIGNED_KIDS, default=default_assigned_kids
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=kid_options,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_ASSIGNED_KIDS,
                    multiple=True,
                )
            ),
            vol.Required(
                const.CONF_CHALLENGE_TYPE,
                default=default.get(
                    const.CONF_CHALLENGE_TYPE, const.CHALLENGE_TYPE_DAILY_MIN
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.CHALLENGE_TYPE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            # If type == "chore_streak", let the user choose the chore to track:
            vol.Optional(
                const.CONF_CHALLENGE_SELECTED_CHORE_ID, default=default_selected_chore
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=chore_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False,
                )
            ),
            # For non-streak achievements the user can type criteria freely:
            vol.Optional(const.CONF_CHALLENGE_CRITERIA, default=default_criteria): str,
            vol.Required(
                const.CONF_CHALLENGE_TARGET_VALUE,
                default=default.get(
                    const.CONF_CHALLENGE_TARGET_VALUE, const.DEFAULT_CHALLENGE_TARGET
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=0.1,
                )
            ),
            vol.Required(
                const.CONF_CHALLENGE_REWARD_POINTS,
                default=default.get(
                    const.CONF_CHALLENGE_REWARD_POINTS,
                    const.DEFAULT_CHALLENGE_REWARD_POINTS,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=0.1,
                )
            ),
            vol.Required(
                const.CONF_CHALLENGE_START_DATE,
                default=default.get(const.CONF_CHALLENGE_START_DATE),
            ): selector.DateTimeSelector(),
            vol.Required(
                const.CONF_CHALLENGE_END_DATE,
                default=default.get(const.CONF_CHALLENGE_END_DATE),
            ): selector.DateTimeSelector(),
            vol.Required(const.CONF_INTERNAL_ID, default=internal_id_default): str,
        }
    )


# ----------------------------------------------------------------------------------
# GENERAL OPTIONS SCHEMA
# ----------------------------------------------------------------------------------


def build_general_options_schema(default: dict = None) -> vol.Schema:
    """Build schema for general options including points adjust values and update interval."""
    default = default or {}
    current_values = default.get(const.CONF_POINTS_ADJUST_VALUES)
    if current_values and isinstance(current_values, list):
        default_points_str = "\n".join(str(v) for v in current_values)
    else:
        default_points_str = "\n".join(
            str(v) for v in const.DEFAULT_POINTS_ADJUST_VALUES
        )

    default_interval = default.get(const.CONF_UPDATE_INTERVAL, const.UPDATE_INTERVAL)
    default_calendar_period = default.get(
        const.CONF_CALENDAR_SHOW_PERIOD, const.DEFAULT_CALENDAR_SHOW_PERIOD
    )

    return vol.Schema(
        {
            vol.Required(
                const.CONF_POINTS_ADJUST_VALUES, default=default_points_str
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=True,
                )
            ),
            vol.Required(
                const.CONF_UPDATE_INTERVAL, default=default_interval
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=1,
                    step=1,
                )
            ),
            vol.Required(
                const.CONF_CALENDAR_SHOW_PERIOD, default=default_calendar_period
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=1,
                    step=1,
                )
            ),
        }
    )


# ----------------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------------


# Penalty points are stored as negative internally, but displayed as positive in the form.
def process_penalty_form_input(user_input: dict) -> dict:
    """Ensure penalty points are negative internally."""
    data = dict(user_input)
    data[const.DATA_PENALTY_POINTS] = -abs(data[const.CONF_PENALTY_POINTS])
    return data


# Get notify services from HA
def _get_notify_services(hass: HomeAssistant) -> list[dict[str, str]]:
    """Return a list of all notify.* services as"""
    services_list = []
    all_services = hass.services.async_services()
    if const.NOTIFY_DOMAIN in all_services:
        for service_name in all_services[const.NOTIFY_DOMAIN].keys():
            fullname = f"{const.NOTIFY_DOMAIN}.{service_name}"
            services_list.append({"value": fullname, "label": fullname})
    return services_list


# Ensure aware datetime objects
def ensure_utc_datetime(hass: HomeAssistant, dt_value: any) -> str:
    """Convert a datetime input (or datetime string) into an ISO timezone aware string(in UTC).

    If dt_value is naive, assume it is in the local timezone.
    """
    # Convert dt_value to a datetime object if necessary
    if not isinstance(dt_value, datetime.datetime):
        dt_value = dt_util.parse_datetime(dt_value)
        if dt_value is None:
            raise ValueError(f"Unable to parse datetime from {dt_value}")

    # If the datetime is naive, assume local time using hass.config.time_zone
    if dt_value.tzinfo is None:
        local_tz = dt_util.get_time_zone(hass.config.time_zone)
        dt_value = dt_value.replace(tzinfo=local_tz)

    # Convert to UTC and return the ISO string
    return dt_util.as_utc(dt_value).isoformat()
