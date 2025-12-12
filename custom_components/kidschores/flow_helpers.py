# File: flow_helpers.py
"""Helpers for the KidsChores integration's Config and Options flow.

Provides schema builders and input-processing logic for internal_id-based management.
"""

# pyright: reportArgumentType=false

import datetime
import uuid
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from . import const
from . import kc_helpers as kh

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


async def build_kid_schema(
    hass,
    users,
    default_kid_name=const.CONF_EMPTY,
    default_ha_user_id=None,
    internal_id=None,
    default_enable_mobile_notifications=False,
    default_mobile_notify_service=None,
    default_enable_persistent_notifications=False,
    default_dashboard_language=None,
):
    """Build a Voluptuous schema for adding/editing a Kid, keyed by internal_id in the dict."""
    user_options = [{"value": const.CONF_EMPTY, "label": const.LABEL_NONE}] + [
        {"value": user.id, "label": user.name} for user in users
    ]
    notify_options = [
        {"value": const.CONF_EMPTY, "label": const.LABEL_NONE}
    ] + _get_notify_services(hass)

    # Get available dashboard languages
    language_options = await kh.get_available_dashboard_languages(hass)

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
            vol.Optional(
                const.CONF_DASHBOARD_LANGUAGE,
                default=default_dashboard_language or const.DEFAULT_DASHBOARD_LANGUAGE,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=language_options,
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


# --- Consolidated Build Function ---
def build_badge_common_data(
    user_input: Dict[str, Any],
    internal_id: str,  # Pass internal_id explicitly
    badge_type: str = const.BADGE_TYPE_CUMULATIVE,
) -> Dict[str, Any]:
    """
    Build the badge data dictionary, including common fields and selected components.

    Args:
        user_input: The dictionary containing user inputs from the form.
        internal_id: The internal ID for the badge.
        badge_type: The type of the badge (e.g., cumulative, daily, periodic). Default is cumulative.

    Returns:
        A dictionary representing the badge's configuration data.
    """
    # --- Set include_ flags based on badge type ---
    include_target = badge_type in const.INCLUDE_TARGET_BADGE_TYPES
    include_special_occasion = badge_type in const.INCLUDE_SPECIAL_OCCASION_BADGE_TYPES
    include_achievement_linked = (
        badge_type in const.INCLUDE_ACHIEVEMENT_LINKED_BADGE_TYPES
    )
    include_challenge_linked = badge_type in const.INCLUDE_CHALLENGE_LINKED_BADGE_TYPES
    include_tracked_chores = badge_type in const.INCLUDE_TRACKED_CHORES_BADGE_TYPES
    include_assigned_to = badge_type in const.INCLUDE_ASSIGNED_TO_BADGE_TYPES
    include_awards = badge_type in const.INCLUDE_AWARDS_BADGE_TYPES
    include_reset_schedule = badge_type in const.INCLUDE_RESET_SCHEDULE_BADGE_TYPES

    # --- Start Common Data ---
    badge_data = {
        const.DATA_BADGE_NAME: user_input.get(const.CFOF_BADGES_INPUT_NAME, "").strip(),
        const.DATA_BADGE_DESCRIPTION: user_input.get(
            const.CFOF_BADGES_INPUT_DESCRIPTION, const.CONF_EMPTY
        ),
        const.DATA_BADGE_LABELS: user_input.get(const.CFOF_BADGES_INPUT_LABELS, []),
        const.DATA_BADGE_ICON: user_input.get(
            const.CFOF_BADGES_INPUT_ICON, const.DEFAULT_BADGE_ICON
        ),
        const.DATA_BADGE_INTERNAL_ID: internal_id,
    }
    # --- End Common Data ---

    # --- Target Component ---
    if include_target:
        target_type = user_input.get(
            const.CFOF_BADGES_INPUT_TARGET_TYPE, const.DEFAULT_BADGE_TARGET_TYPE
        )
        threshold_value_input = user_input.get(
            const.CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE,
            const.DEFAULT_BADGE_TARGET_THRESHOLD_VALUE,
        )
        threshold_value = const.DEFAULT_BADGE_TARGET_THRESHOLD_VALUE  # Default
        try:
            threshold_value = float(threshold_value_input)
        except (TypeError, ValueError, AttributeError):
            const.LOGGER.warning(
                "Could not parse target threshold value '%s' for type '%s'. Using default.",
                threshold_value_input,
                target_type,
            )

        maintenance_rules = user_input.get(
            const.CFOF_BADGES_INPUT_MAINTENANCE_RULES,
            const.DEFAULT_BADGE_MAINTENANCE_THRESHOLD,
        )

        badge_data[const.DATA_BADGE_TARGET] = {
            const.DATA_BADGE_TARGET_TYPE: target_type,
            const.DATA_BADGE_TARGET_THRESHOLD_VALUE: threshold_value,
            const.DATA_BADGE_MAINTENANCE_RULES: maintenance_rules,
        }

    # --- Special Occasion Component ---
    if include_special_occasion:
        occasion_type = user_input.get(
            const.CFOF_BADGES_INPUT_OCCASION_TYPE, const.CONF_EMPTY
        )
        badge_data[const.DATA_BADGE_SPECIAL_OCCASION_TYPE] = occasion_type

    # --- Achievement-Linked Component ---
    if include_achievement_linked:
        achievement_id = user_input.get(
            const.CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT, const.CONF_EMPTY
        )
        badge_data[const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT] = achievement_id

    # --- Challenge-Linked Component ---
    if include_challenge_linked:
        challenge_id = user_input.get(
            const.CFOF_BADGES_INPUT_ASSOCIATED_CHALLENGE, const.CONF_EMPTY
        )
        badge_data[const.DATA_BADGE_ASSOCIATED_CHALLENGE] = challenge_id

    # --- Tracked Chores Component ---
    if include_tracked_chores:  # Use renamed flag
        selected_chores = user_input.get(const.CFOF_BADGES_INPUT_SELECTED_CHORES, [])
        if not isinstance(selected_chores, list):
            selected_chores = [selected_chores] if selected_chores else []
        selected_chores = [
            chore_id
            for chore_id in selected_chores
            if chore_id and chore_id != const.CONF_EMPTY
        ]
        # Output key remains 'tracked' as per spec example, flag name is just for clarity
        badge_data[const.DATA_BADGE_TRACKED_CHORES] = {
            const.DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: selected_chores
        }

    # --- Assigned To Component ---
    if include_assigned_to:
        assigned = user_input.get(const.CFOF_BADGES_INPUT_ASSIGNED_TO, [])
        if not isinstance(assigned, list):
            assigned = [assigned] if assigned else []
        assigned = [
            kid_id for kid_id in assigned if kid_id and kid_id != const.CONF_EMPTY
        ]
        badge_data[const.DATA_BADGE_ASSIGNED_TO] = assigned

    # --- Awards Component ---
    if include_awards:
        # Logic from build_badge_awards_data
        points_input = user_input.get(
            const.CFOF_BADGES_INPUT_AWARD_POINTS, const.DEFAULT_BADGE_AWARD_POINTS
        )
        points = const.DEFAULT_BADGE_AWARD_POINTS  # Default
        try:
            points = float(points_input)
        except (TypeError, ValueError, AttributeError):
            const.LOGGER.warning(
                "Could not parse award points value '%s'. Using default.", points_input
            )
        multiplier = user_input.get(
            const.CFOF_BADGES_INPUT_POINTS_MULTIPLIER, const.CONF_NONE
        )

        # --- Unified Award Items ---
        award_items = user_input.get(const.CFOF_BADGES_INPUT_AWARD_ITEMS, [])
        if not isinstance(award_items, list):
            award_items = [award_items] if award_items else []

        badge_data[const.DATA_BADGE_AWARDS] = {
            const.DATA_BADGE_AWARDS_AWARD_POINTS: points,
            const.DATA_BADGE_AWARDS_POINT_MULTIPLIER: multiplier,
            const.DATA_BADGE_AWARDS_AWARD_ITEMS: award_items,
        }

    # --- Reset Component ---
    if include_reset_schedule:
        recurring_frequency = user_input.get(
            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_RECURRING_FREQUENCY,
            const.CONF_WEEKLY,  # Default mode if not provided
        )
        start_date = user_input.get(
            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_START_DATE, None
        )
        end_date = user_input.get(const.CFOF_BADGES_INPUT_RESET_SCHEDULE_END_DATE, None)
        grace_period_days = user_input.get(
            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_GRACE_PERIOD_DAYS,
            const.DEFAULT_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS,
        )
        custom_interval = user_input.get(
            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL,
            const.DEFAULT_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL,
        )
        custom_interval_unit = user_input.get(
            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT,
            const.DEFAULT_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT,
        )

        # Clean empty strings to None
        start_date = None if start_date in (None, "") else start_date
        end_date = None if end_date in (None, "") else end_date

        if recurring_frequency == const.CONF_CUSTOM:
            start_date = user_input.get(
                const.CFOF_BADGES_INPUT_RESET_SCHEDULE_START_DATE
            )  # Get raw
            end_date = user_input.get(
                const.CFOF_BADGES_INPUT_RESET_SCHEDULE_END_DATE
            )  # Get raw
            # Clean empty strings to None
            start_date = None if start_date in (None, "") else start_date
            end_date = None if end_date in (None, "") else end_date
        # For CONF_NONE or any other non-CUSTOM mode, dates remain None

        badge_data[const.DATA_BADGE_RESET_SCHEDULE] = {
            const.DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY: recurring_frequency,
            const.DATA_BADGE_RESET_SCHEDULE_START_DATE: start_date,
            const.DATA_BADGE_RESET_SCHEDULE_END_DATE: end_date,
            const.DATA_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS: grace_period_days,
            const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL: custom_interval,
            const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT: custom_interval_unit,
        }

    # --- Return the constructed badge data ---
    return badge_data


# --- Consolidated Validation Function ---


def validate_badge_common_inputs(
    user_input: Dict[str, Any],
    internal_id: Optional[str],
    existing_badges: Optional[Dict[str, Any]] = None,
    rewards_dict: Optional[Dict[str, Any]] = None,
    bonuses_dict: Optional[Dict[str, Any]] = None,
    penalties_dict: Optional[Dict[str, Any]] = None,
    badge_type: str = const.BADGE_TYPE_CUMULATIVE,
) -> Dict[str, str]:
    """
    Validate common badge inputs and selected component inputs.

    Args:
        user_input: The dictionary containing user inputs from the form.
        internal_id: The internal ID for the badge (None when adding a new badge).
        existing_badges: Dictionary of existing badge configurations for uniqueness checks.
        badge_type: The type of the badge (e.g., cumulative, daily, periodic). Default is cumulative.

    Returns:
        A dictionary of validation errors {field_key: error_message_or_translation_key}.
    """
    errors: Dict[str, str] = {}
    existing_badges = existing_badges or {}

    rewards_dict = rewards_dict or {}
    bonuses_dict = bonuses_dict or {}
    penalties_dict = penalties_dict or {}

    # --- Set include_ flags based on badge type ---
    include_target = badge_type in const.INCLUDE_TARGET_BADGE_TYPES
    include_special_occasion = badge_type in const.INCLUDE_SPECIAL_OCCASION_BADGE_TYPES
    include_achievement_linked = (
        badge_type in const.INCLUDE_ACHIEVEMENT_LINKED_BADGE_TYPES
    )
    include_challenge_linked = badge_type in const.INCLUDE_CHALLENGE_LINKED_BADGE_TYPES
    include_tracked_chores = badge_type in const.INCLUDE_TRACKED_CHORES_BADGE_TYPES
    include_assigned_to = badge_type in const.INCLUDE_ASSIGNED_TO_BADGE_TYPES
    include_awards = badge_type in const.INCLUDE_AWARDS_BADGE_TYPES
    include_reset_schedule = badge_type in const.INCLUDE_RESET_SCHEDULE_BADGE_TYPES

    is_cumulative = badge_type == const.BADGE_TYPE_CUMULATIVE
    is_periodic = badge_type == const.BADGE_TYPE_PERIODIC
    is_daily = badge_type == const.BADGE_TYPE_DAILY
    is_special_occasion = badge_type == const.BADGE_TYPE_SPECIAL_OCCASION

    # --- Start Common Validation ---
    badge_name = user_input.get(const.CFOF_BADGES_INPUT_NAME, "").strip()

    if not badge_name:
        errors[const.CFOF_BADGES_INPUT_NAME] = const.TRANS_KEY_CFOF_INVALID_BADGE_NAME

    # Validate badge is not duplicate (exclude the badge being edited)
    for badge_id, badge_info in existing_badges.items():
        if badge_id == internal_id:
            continue  # Skip the badge being edited
        if (
            badge_info.get(const.DATA_BADGE_NAME, "").strip().lower()
            == badge_name.lower()
        ):
            errors[const.CFOF_BADGES_INPUT_NAME] = const.TRANS_KEY_CFOF_DUPLICATE_BADGE
            break
    # --- End Common Validation ---

    # --- Target Component Validation ---
    if include_target:
        # Special Occasion badge handling - force target type and threshold value
        if is_special_occasion:
            # Force special occasion badges to use points with threshold 1
            user_input[const.CFOF_BADGES_INPUT_TARGET_TYPE] = (
                const.BADGE_TARGET_THRESHOLD_TYPE_CHORE_COUNT
            )
            user_input[const.CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE] = 1

        # Cumulative badge handling - force target type to points
        elif is_cumulative:
            # Force cumulative badges to use points
            user_input[const.CFOF_BADGES_INPUT_TARGET_TYPE] = (
                const.BADGE_TARGET_THRESHOLD_TYPE_POINTS
            )

            # Validate maintenance rules
            maintenance_rules = user_input.get(
                const.CFOF_BADGES_INPUT_MAINTENANCE_RULES
            )
            if maintenance_rules is None or maintenance_rules < 0:
                errors[const.CFOF_BADGES_INPUT_MAINTENANCE_RULES] = (
                    "invalid_maintenance_rules"
                )
        else:
            # Regular badge validation
            target_threshold = user_input.get(
                const.CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE
            )

            if target_threshold is None or str(target_threshold).strip() == "":
                errors[const.CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE] = (
                    "target_threshold_required"  # Use translation key
                )
            else:
                try:
                    value = float(target_threshold)
                    if value <= 0:
                        errors[const.CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE] = (
                            const.TRANS_KEY_CFOF_INVALID_BADGE_TARGET_THRESHOLD_VALUE
                        )
                except (TypeError, ValueError):
                    errors[const.CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE] = (
                        const.TRANS_KEY_CFOF_INVALID_BADGE_TARGET_THRESHOLD_VALUE
                    )

        # Handle maintenance rules for non-cumulative badges
        if not is_cumulative:
            # If not cumulative, set maintenance rules to Zero
            user_input[const.CFOF_BADGES_INPUT_MAINTENANCE_RULES] = const.DEFAULT_ZERO

    # --- Special Occasion Validation ---
    if include_special_occasion:
        occasion_type = user_input.get(
            const.CFOF_BADGES_INPUT_OCCASION_TYPE, const.CONF_EMPTY
        )
        if not occasion_type or occasion_type == const.CONF_EMPTY:
            errors[const.CFOF_BADGES_INPUT_OCCASION_TYPE] = (
                const.TRANS_KEY_CFOF_ERROR_BADGE_OCCASION_TYPE_REQUIRED
            )

    # --- Achievement-Linked Validation ---
    if include_achievement_linked:
        achievement_id = user_input.get(
            const.CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT, const.CONF_EMPTY
        )
        if not achievement_id or achievement_id == const.CONF_EMPTY:
            errors[const.CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT] = (
                const.TRANS_KEY_CFOF_ERROR_BADGE_ACHIEVEMENT_REQUIRED
            )

    # --- Challenge-Linked Validation ---
    if include_challenge_linked:
        challenge_id = user_input.get(
            const.CFOF_BADGES_INPUT_ASSOCIATED_CHALLENGE, const.CONF_EMPTY
        )
        if not challenge_id or challenge_id == const.CONF_EMPTY:
            errors[const.CFOF_BADGES_INPUT_ASSOCIATED_CHALLENGE] = (
                const.TRANS_KEY_CFOF_ERROR_BADGE_CHALLENGE_REQUIRED
            )

    # --- Tracked Chores Component Validation ---
    if include_tracked_chores:
        selected_chores = user_input.get(const.CFOF_BADGES_INPUT_SELECTED_CHORES, [])
        if not isinstance(selected_chores, list):
            errors[const.CFOF_BADGES_INPUT_SELECTED_CHORES] = (
                "invalid_format_list_expected"  # Use translation keys
            )

    # --- Assigned To Component Validation ---
    if include_assigned_to:
        assigned = user_input.get(const.CFOF_BADGES_INPUT_ASSIGNED_TO, [])
        if not isinstance(assigned, list):
            errors[const.CFOF_BADGES_INPUT_ASSIGNED_TO] = (
                "invalid_format_list_expected"  # Use translation keys
            )
        # Optional: Check existence of kid IDs here if needed

    # --- Awards Component Validation ---
    award_items_valid_values = None
    if include_awards:
        # ...existing award_mode logic...

        award_items = user_input.get(const.CFOF_BADGES_INPUT_AWARD_ITEMS, [])
        if not isinstance(award_items, list):
            award_items = [award_items] if award_items else []

        # If award_items_valid_values is not provided, build it here
        if award_items_valid_values is None:
            award_items_valid_values = [
                const.AWARD_ITEMS_KEY_POINTS,
                const.AWARD_ITEMS_KEY_POINTS_MULTIPLIER,
            ]
            if rewards_dict:
                award_items_valid_values += [
                    f"{const.AWARD_ITEMS_PREFIX_REWARD}{reward_id}"
                    for reward_id in rewards_dict.keys()
                ]
            if bonuses_dict:
                award_items_valid_values += [
                    f"{const.AWARD_ITEMS_PREFIX_BONUS}{bonus_id}"
                    for bonus_id in bonuses_dict.keys()
                ]
            if penalties_dict:
                award_items_valid_values += [
                    f"{const.AWARD_ITEMS_PREFIX_PENALTY}{penalty_id}"
                    for penalty_id in penalties_dict.keys()
                ]

        # 1. POINTS: logic
        if const.AWARD_ITEMS_KEY_POINTS in award_items:
            points = user_input.get(
                const.CFOF_BADGES_INPUT_AWARD_POINTS, const.DEFAULT_ZERO
            )
            try:
                if float(points) <= const.DEFAULT_ZERO:
                    errors[const.CFOF_BADGES_INPUT_AWARD_POINTS] = (
                        const.TRANS_KEY_CFOF_ERROR_AWARD_POINTS_MINIMUM
                    )
            except (TypeError, ValueError):
                errors[const.CFOF_BADGES_INPUT_AWARD_POINTS] = (
                    const.TRANS_KEY_CFOF_ERROR_AWARD_POINTS_MINIMUM
                )
        else:
            user_input[const.CFOF_BADGES_INPUT_AWARD_POINTS] = const.DEFAULT_ZERO

        # 2. POINTS MULTIPLIER: logic
        if const.AWARD_ITEMS_KEY_POINTS_MULTIPLIER in award_items:
            multiplier = user_input.get(
                const.CFOF_BADGES_INPUT_POINTS_MULTIPLIER,
                const.DEFAULT_POINTS_MULTIPLIER,
            )
            try:
                if float(multiplier) <= const.DEFAULT_ZERO:
                    errors[const.CFOF_BADGES_INPUT_POINTS_MULTIPLIER] = (
                        const.TRANS_KEY_CFOF_ERROR_AWARD_INVALID_MULTIPLIER
                    )
            except (TypeError, ValueError):
                errors[const.CFOF_BADGES_INPUT_POINTS_MULTIPLIER] = (
                    const.TRANS_KEY_CFOF_ERROR_AWARD_INVALID_MULTIPLIER
                )
        else:
            user_input[const.CFOF_BADGES_INPUT_POINTS_MULTIPLIER] = const.CONF_NONE

        # 3. All selected award_items must be valid
        for item in award_items:
            if item not in award_items_valid_values:
                errors[const.CFOF_BADGES_INPUT_AWARD_ITEMS] = (
                    const.TRANS_KEY_CFOF_ERROR_AWARD_INVALID_AWARD_ITEM
                )
                break

    # --- Reset Component Validation ---
    if include_reset_schedule:
        recurring_frequency = user_input.get(
            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_RECURRING_FREQUENCY,
            const.DEFAULT_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY,
        )

        # Clear custom interval fields if not custom
        if recurring_frequency != const.CONF_CUSTOM:
            # Note that END_DATE is not cleared here, because it can be used with the frequencies as a reference date
            user_input.update(
                {
                    const.CFOF_BADGES_INPUT_RESET_SCHEDULE_START_DATE: const.CONF_NONE,
                    const.CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL: const.CONF_NONE,
                    const.CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT: const.CONF_NONE,
                }
            )

        start_date = user_input.get(const.CFOF_BADGES_INPUT_RESET_SCHEDULE_START_DATE)
        end_date = user_input.get(const.CFOF_BADGES_INPUT_RESET_SCHEDULE_END_DATE)

        if recurring_frequency == const.CONF_CUSTOM:
            # Validate start and end dates for periodic badges
            # If no custom interval and custom interval unit, then it will just do a one time reset
            if is_periodic and not start_date:
                errors[const.CFOF_BADGES_INPUT_RESET_SCHEDULE_START_DATE] = (
                    const.TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_START_DATE_REQUIRED
                )
            if not end_date:
                errors[const.CFOF_BADGES_INPUT_RESET_SCHEDULE_END_DATE] = (
                    const.TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_END_DATE_REQUIRED
                )
            elif start_date and end_date < start_date:
                errors[const.CFOF_BADGES_INPUT_RESET_SCHEDULE_END_DATE] = (
                    "end_date_before_start_date"
                )

        # Validate grace period for cumulative badges
        if is_cumulative:
            grace_period_days = user_input.get(
                const.CFOF_BADGES_INPUT_RESET_SCHEDULE_GRACE_PERIOD_DAYS
            )
            if grace_period_days is None or grace_period_days < 0:
                errors[const.CFOF_BADGES_INPUT_RESET_SCHEDULE_GRACE_PERIOD_DAYS] = (
                    "invalid_grace_period_days"
                )
        else:
            # Set grace period to zero for non-cumulative badges
            user_input[const.CFOF_BADGES_INPUT_RESET_SCHEDULE_GRACE_PERIOD_DAYS] = (
                const.DEFAULT_ZERO
            )

        if is_daily:
            user_input[const.CFOF_BADGES_INPUT_RESET_SCHEDULE_RECURRING_FREQUENCY] = (
                const.CONF_DAILY
            )

        # Special occasion is just a periodic badge that has a start and end date of the same day.
        if is_special_occasion:
            user_input[const.CFOF_BADGES_INPUT_RESET_SCHEDULE_START_DATE] = (
                user_input.get(const.CFOF_BADGES_INPUT_RESET_SCHEDULE_END_DATE)
            )

    return errors


# --- Consolidated Schema Function ---


def build_badge_common_schema(
    default: Optional[Dict[str, Any]] = None,
    kids_dict: Optional[Dict[str, Any]] = None,
    chores_dict: Optional[Dict[str, Any]] = None,
    rewards_dict: Optional[Dict[str, Any]] = None,
    challenges_dict: Optional[Dict[str, Any]] = None,
    achievements_dict: Optional[Dict[str, Any]] = None,
    bonuses_dict: Optional[Dict[str, Any]] = None,
    penalties_dict: Optional[Dict[str, Any]] = None,
    badge_type: str = const.BADGE_TYPE_CUMULATIVE,
) -> Dict[vol.Marker, Any]:
    """
    Build a Voluptuous schema for badge configuration, including common fields
    and selected components.

    Args:
        default: Dictionary containing default values for the fields.
        kids: Dictionary of available kids for the assigned_to selector.
        chores: Dictionary of available chores for the tracked selector.
        rewards: Dictionary of available rewards for the awards selector.
        badge_type: The type of the badge (e.g., cumulative, daily, periodic). Default is cumulative.

    Special Notes:
        The `default` parameter in this helper is populated dynamically based on the context.
        or editing, it receives either `badge_data` (on the first load) or `user_input` (after an error).
        This allows the schema to pre-fill fields with existing data while preserving user changes
        when the form is regenerated after validation errors.
        Reason for this is because user_input field names do not always match the data keys in the badge data.

    Returns:
        A dictionary representing the Voluptuous schema.
    """
    default = default or {}
    kids_dict = kids_dict or {}
    chores_dict = chores_dict or {}
    rewards_dict = rewards_dict or {}
    challenges_dict = challenges_dict or {}
    achievements_dict = achievements_dict or {}
    bonuses_dict = bonuses_dict or {}
    penalties_dict = penalties_dict or {}
    # Initialize schema fields
    schema_fields = {}

    # --- Set include_ flags based on badge type ---
    include_target = badge_type in const.INCLUDE_TARGET_BADGE_TYPES
    include_special_occasion = badge_type in const.INCLUDE_SPECIAL_OCCASION_BADGE_TYPES
    include_achievement_linked = (
        badge_type in const.INCLUDE_ACHIEVEMENT_LINKED_BADGE_TYPES
    )
    include_challenge_linked = badge_type in const.INCLUDE_CHALLENGE_LINKED_BADGE_TYPES
    include_tracked_chores = badge_type in const.INCLUDE_TRACKED_CHORES_BADGE_TYPES
    include_assigned_to = badge_type in const.INCLUDE_ASSIGNED_TO_BADGE_TYPES
    include_awards = badge_type in const.INCLUDE_AWARDS_BADGE_TYPES
    include_penalties = badge_type in const.INCLUDE_PENALTIES_BADGE_TYPES
    include_reset_schedule = badge_type in const.INCLUDE_RESET_SCHEDULE_BADGE_TYPES

    is_cumulative = badge_type == const.BADGE_TYPE_CUMULATIVE
    is_periodic = badge_type == const.BADGE_TYPE_PERIODIC
    is_daily = badge_type == const.BADGE_TYPE_DAILY
    is_special_occasion = badge_type == const.BADGE_TYPE_SPECIAL_OCCASION

    const.LOGGER.debug(
        "DEBUG: Build Badge Common Schema - Badge Data Passed to Schema: %s", default
    )

    # --- Start Common Schema ---
    # See Special Notes above for explanation of default usage rational
    schema_fields.update(
        {
            vol.Required(
                const.CFOF_BADGES_INPUT_NAME,
                default=default.get(
                    const.CFOF_BADGES_INPUT_NAME,
                    default.get(const.DATA_BADGE_NAME, const.CONF_EMPTY),
                ),
            ): str,
            vol.Optional(
                const.CFOF_BADGES_INPUT_DESCRIPTION,
                default=default.get(
                    const.CFOF_BADGES_INPUT_DESCRIPTION,
                    default.get(const.DATA_BADGE_DESCRIPTION, const.CONF_EMPTY),
                ),
            ): str,
            # CLS - Tried to make this work with tranlation_key, but it doesn't seem to support it
            vol.Optional(
                const.CFOF_BADGES_INPUT_LABELS,
                default=default.get(
                    const.CFOF_BADGES_INPUT_LABELS,
                    default.get(const.DATA_BADGE_LABELS, []),
                ),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Optional(
                const.CFOF_BADGES_INPUT_ICON,
                default=default.get(
                    const.CFOF_BADGES_INPUT_ICON, const.DEFAULT_BADGE_ICON
                ),
            ): selector.IconSelector(),
        }
    )
    # --- End Common Schema ---

    # --- Target Component Schema ---
    if include_target:
        # Filter target_type_options based on whether tracked chores are included
        # For daily badges, filter out all streak targets
        if badge_type == const.BADGE_TYPE_DAILY:
            streak_types = {
                const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES,
                const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_CHORES,
                const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES_NO_OVERDUE,
                const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_DUE_CHORES,
                const.BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_DUE_CHORES_NO_OVERDUE,
            }
            target_type_options = [
                option
                for option in const.TARGET_TYPE_OPTIONS or []
                if option["value"] not in streak_types
            ]
        else:
            target_type_options = [
                option
                for option in const.TARGET_TYPE_OPTIONS or []
                if include_tracked_chores
                or option["value"]
                in (
                    const.BADGE_TARGET_THRESHOLD_TYPE_POINTS,
                    const.BADGE_TARGET_THRESHOLD_TYPE_POINTS_CHORES,
                    const.BADGE_TARGET_THRESHOLD_TYPE_CHORE_COUNT,
                )
            ]

        default_target_type = default.get(
            const.CFOF_BADGES_INPUT_TARGET_TYPE,
            default.get(const.DATA_BADGE_TARGET, {}).get(
                const.DATA_BADGE_TARGET_TYPE, const.DEFAULT_BADGE_TARGET_TYPE
            ),
        )
        default_threshold = default.get(
            const.CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE,
            default.get(const.DATA_BADGE_TARGET, {}).get(
                const.DATA_BADGE_TARGET_THRESHOLD_VALUE,
                const.DEFAULT_BADGE_TARGET_THRESHOLD_VALUE,
            ),
        )

        if not (is_cumulative or is_special_occasion):
            # Include the target_type field for non-cumulative badges
            schema_fields.update(
                {
                    vol.Required(
                        const.CFOF_BADGES_INPUT_TARGET_TYPE,
                        default=default_target_type,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=target_type_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key=const.TRANS_KEY_CFOF_BADGE_TARGET_TYPE,
                        )
                    ),
                }
            )

        # Always include the threshold field unless it's a special occasion
        if not is_special_occasion:
            schema_fields.update(
                {
                    vol.Required(
                        const.CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE,
                        default=float(
                            default_threshold
                        ),  # Ensure the default is a float
                    ): vol.All(
                        selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                mode=selector.NumberSelectorMode.BOX,
                                min=0,
                                step=1,
                            )
                        ),
                        vol.Coerce(float),  # Coerce the input to an integer
                        vol.Range(min=0),  # Ensure non-negative values
                    ),
                }
            )

        # Add maintenance rules only if cumulative
        if is_cumulative:
            schema_fields.update(
                {
                    vol.Optional(
                        const.CFOF_BADGES_INPUT_MAINTENANCE_RULES,
                        default=int(
                            default.get(
                                const.CFOF_BADGES_INPUT_MAINTENANCE_RULES,
                                default.get(const.DATA_BADGE_TARGET, {}).get(
                                    const.DATA_BADGE_MAINTENANCE_RULES,
                                    const.DEFAULT_BADGE_MAINTENANCE_THRESHOLD,
                                ),
                            )
                        ),  # Ensure the default is an integer
                    ): vol.All(
                        selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                mode=selector.NumberSelectorMode.BOX,
                                min=0,
                                step=1,
                            )
                        ),
                        vol.Coerce(int),  # Coerce the input to an integer
                        vol.Range(min=0),  # Ensure non-negative values
                    ),
                }
            )

    # --- Special Occasion Component Schema ---
    if include_special_occasion:
        occasion_type_options = const.OCCASION_TYPE_OPTIONS or []
        default_occasion_type = default.get(
            const.CFOF_BADGES_INPUT_OCCASION_TYPE,
            default.get(const.DATA_BADGE_SPECIAL_OCCASION_TYPE, const.CONF_EMPTY),
        )
        schema_fields.update(
            {
                vol.Required(
                    const.CFOF_BADGES_INPUT_OCCASION_TYPE,
                    default=default_occasion_type,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=occasion_type_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key=const.TRANS_KEY_CFOF_BADGE_OCCASION_TYPE,
                    )
                )
            }
        )

    # --- Achievement-Linked Component Schema ---
    if include_achievement_linked:
        achievement_options = [
            {"value": const.CONF_EMPTY, "label": const.LABEL_NONE}
        ] + [
            {
                "value": achievement_id,
                "label": achievement.get(
                    const.DATA_ACHIEVEMENT_NAME, const.CONF_NONE_TEXT
                ),
            }
            for achievement_id, achievement in achievements_dict.items()
        ]
        default_achievement = default.get(
            const.CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT,
            default.get(const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT, const.CONF_EMPTY),
        )
        schema_fields.update(
            {
                vol.Required(
                    const.CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT,
                    default=default_achievement,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=achievement_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key=const.TRANS_KEY_CFOF_BADGE_ASSOCIATED_ACHIEVEMENT,
                    )
                )
            }
        )

    # --- Challenge-Linked Component Schema ---
    if include_challenge_linked:
        challenge_options = [{"value": const.CONF_EMPTY, "label": const.LABEL_NONE}] + [
            {
                "value": challenge_id,
                "label": challenge.get(const.DATA_CHALLENGE_NAME, const.CONF_NONE_TEXT),
            }
            for challenge_id, challenge in challenges_dict.items()
        ]
        default_challenge = default.get(
            const.CFOF_BADGES_INPUT_ASSOCIATED_CHALLENGE,
            default.get(const.DATA_BADGE_ASSOCIATED_CHALLENGE, const.CONF_EMPTY),
        )
        schema_fields.update(
            {
                vol.Required(
                    const.CFOF_BADGES_INPUT_ASSOCIATED_CHALLENGE,
                    default=default_challenge,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=challenge_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key=const.TRANS_KEY_CFOF_BADGE_ASSOCIATED_CHALLENGE,
                    )
                )
            }
        )

    # --- Tracked Chores Component Schema ---
    if include_tracked_chores:  # Use renamed flag
        options = [{"value": const.CONF_EMPTY, "label": const.LABEL_NONE}]
        options += [
            {
                "value": chore_id,
                "label": chore.get(const.DATA_CHORE_NAME, const.CONF_NONE_TEXT),
            }
            for chore_id, chore in chores_dict.items()
        ]
        default_selected = default.get(
            const.CFOF_BADGES_INPUT_SELECTED_CHORES,
            default.get(const.DATA_BADGE_TRACKED_CHORES, {}).get(
                const.DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES, []
            ),
        )
        schema_fields.update(
            {
                vol.Optional(
                    const.CFOF_BADGES_INPUT_SELECTED_CHORES,
                    default=default_selected
                    if isinstance(default_selected, list)
                    else [],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key=const.TRANS_KEY_CFOF_BADGE_SELECTED_CHORES,
                    )
                )
            }
        )

    # --- Assigned To Component Schema ---
    if include_assigned_to:
        options = [{"value": const.CONF_EMPTY, "label": const.LABEL_NONE}]
        options += [
            {
                "value": kid_id,
                "label": kid.get(const.DATA_KID_NAME, const.CONF_NONE_TEXT),
            }
            for kid_id, kid in kids_dict.items()
        ]
        default_assigned = default.get(
            const.CFOF_BADGES_INPUT_ASSIGNED_TO,
            default.get(const.DATA_BADGE_ASSIGNED_TO, []),
        )
        schema_fields.update(
            {
                vol.Optional(
                    const.CFOF_BADGES_INPUT_ASSIGNED_TO,
                    default=default_assigned
                    if isinstance(default_assigned, list)
                    else [],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key=const.TRANS_KEY_CFOF_BADGE_ASSIGNED_TO,
                    )
                )
            }
        )

    # --- Awards Component Schema ---
    if include_awards:
        # Logic from build_badge_awards_schema

        award_items_options = []

        award_items_options.append(
            {
                const.CONF_VALUE: const.AWARD_ITEMS_KEY_POINTS,
                const.CONF_LABEL: const.AWARD_ITEMS_LABEL_POINTS,
            }
        )

        if is_cumulative:
            award_items_options.append(
                {
                    const.CONF_VALUE: const.AWARD_ITEMS_KEY_POINTS_MULTIPLIER,
                    const.CONF_LABEL: const.AWARD_ITEMS_LABEL_POINTS_MULTIPLIER,
                }
            )

        if rewards_dict:
            for reward_id, reward in rewards_dict.items():
                label = f"{const.AWARD_ITEMS_LABEL_REWARD} {reward.get(const.DATA_REWARD_NAME, reward_id)}"
                award_items_options.append(
                    {
                        const.CONF_VALUE: f"{const.AWARD_ITEMS_PREFIX_REWARD}{reward_id}",
                        const.CONF_LABEL: label,
                    }
                )
        if bonuses_dict:
            for bonus_id, bonus in bonuses_dict.items():
                label = f"{const.AWARD_ITEMS_LABEL_BONUS} {bonus.get(const.DATA_BONUS_NAME, bonus_id)}"
                award_items_options.append(
                    {
                        const.CONF_VALUE: f"{const.AWARD_ITEMS_PREFIX_BONUS}{bonus_id}",
                        const.CONF_LABEL: label,
                    }
                )
        if include_penalties:
            if penalties_dict:
                for penalty_id, penalty in penalties_dict.items():
                    label = f"{const.AWARD_ITEMS_LABEL_PENALTY} {penalty.get(const.DATA_PENALTY_NAME, penalty_id)}"
                    award_items_options.append(
                        {
                            const.CONF_VALUE: f"{const.AWARD_ITEMS_PREFIX_PENALTY}{penalty_id}",
                            const.CONF_LABEL: label,
                        }
                    )

        default_award_items = default.get(
            const.CFOF_BADGES_INPUT_AWARD_ITEMS,
            default.get(const.DATA_BADGE_AWARDS, {}).get(
                const.DATA_BADGE_AWARDS_AWARD_ITEMS, []
            ),
        )

        schema_fields.update(
            {
                vol.Optional(
                    const.CFOF_BADGES_INPUT_AWARD_ITEMS,
                    default=default_award_items
                    if isinstance(default_award_items, list)
                    else [],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=award_items_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key=const.TRANS_KEY_CFOF_BADGE_AWARD_ITEMS,
                    )
                )
            }
        )

        schema_fields.update(
            {
                # Points field is technically optional depending on mode, but schema can keep it simple
                # Validation layer handles the logic of whether value is needed/used
                vol.Optional(
                    const.CFOF_BADGES_INPUT_AWARD_POINTS,
                    # Ensure default is treated as float if present
                    default=float(
                        default.get(
                            const.CFOF_BADGES_INPUT_AWARD_POINTS,
                            default.get(const.DATA_BADGE_AWARDS, {}).get(
                                const.DATA_BADGE_AWARDS_AWARD_POINTS,
                                const.DEFAULT_BADGE_AWARD_POINTS,
                            ),
                        )
                    ),
                ): vol.All(
                    selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            mode=selector.NumberSelectorMode.BOX,
                            min=0.0,  # Allow zero as the minimum value
                            step=0.1,
                        )
                    ),
                    vol.Coerce(float),  # Coerce the input to a float
                    vol.Range(
                        min=0.0
                    ),  # Ensure the value is greater than or equal to zero
                ),
            }
        )
        # Points multiplier is only relevant for cumulative badges
        if is_cumulative:
            schema_fields.update(
                {
                    vol.Optional(
                        const.CFOF_BADGES_INPUT_POINTS_MULTIPLIER,
                        default=default.get(
                            const.CFOF_BADGES_INPUT_POINTS_MULTIPLIER,
                            default.get(const.DATA_BADGE_AWARDS, {}).get(
                                const.DATA_BADGE_AWARDS_POINT_MULTIPLIER,
                                None,
                            ),
                        ),
                    ): vol.Any(
                        None,
                        vol.All(
                            selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    mode=selector.NumberSelectorMode.BOX,
                                    step=0.1,
                                    min=0.1,
                                )
                            ),
                            vol.Coerce(float),
                            vol.Range(min=0.1),
                        ),
                    ),
                }
            )

    # --- Reset Component Schema ---
    if include_reset_schedule:
        # Define defaults at the top for easier adjustments
        # Get the reset_schedule once instead of repeated lookups
        reset_schedule = default.get(const.DATA_BADGE_RESET_SCHEDULE, {})

        # Get defaults from user_input first (if present), then from reset_schedule, then use defaults
        default_recurring_frequency = default.get(
            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_RECURRING_FREQUENCY,
            reset_schedule.get(
                const.DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY,
                const.DEFAULT_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY,
            ),
        )
        default_custom_interval = default.get(
            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL,
            reset_schedule.get(
                const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL,
                const.DEFAULT_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL,
            ),
        )
        default_custom_interval_unit = default.get(
            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT,
            reset_schedule.get(
                const.DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT,
                const.DEFAULT_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT,
            ),
        )
        default_start_date = default.get(
            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_START_DATE,
            reset_schedule.get(
                const.DATA_BADGE_RESET_SCHEDULE_START_DATE,
                const.DEFAULT_BADGE_RESET_SCHEDULE_START_DATE,
            ),
        )
        default_end_date = default.get(
            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_END_DATE,
            reset_schedule.get(
                const.DATA_BADGE_RESET_SCHEDULE_END_DATE,
                const.DEFAULT_BADGE_RESET_SCHEDULE_END_DATE,
            ),
        )
        default_grace_period_days = default.get(
            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_GRACE_PERIOD_DAYS,
            reset_schedule.get(
                const.DATA_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS,
                const.DEFAULT_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS,
            ),
        )

        # For BADGE_TYPE_DAILY hide reset schedule fields and force value in validation
        if not is_daily:
            # Build the schema fields for other badge types
            schema_fields.update(
                {
                    # Recurring Frequency
                    vol.Required(
                        const.CFOF_BADGES_INPUT_RESET_SCHEDULE_RECURRING_FREQUENCY,
                        default=default_recurring_frequency,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=const.BADGE_RESET_SCHEDULE_OPTIONS,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key=const.TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY,
                        )
                    ),
                    # Custom Interval
                    vol.Optional(
                        const.CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL,
                        default=default_custom_interval,  # Default can be None or an integer
                    ): vol.Any(
                        None,
                        vol.All(
                            selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    mode=selector.NumberSelectorMode.BOX,
                                    min=0,  # Ensure values are greater than or equal to 0
                                    step=1,
                                )
                            ),
                            vol.Coerce(int),  # Coerce the input to an integer
                            vol.Range(
                                min=0
                            ),  # Ensure the value is greater than or equal to 0
                        ),
                    ),
                    # Custom Interval Unit
                    vol.Optional(
                        const.CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT,
                        default=default_custom_interval_unit,
                    ): vol.Any(
                        None,
                        selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=const.CUSTOM_INTERVAL_UNIT_OPTIONS,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                                translation_key=const.TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT,
                            )
                        ),
                    ),
                }
            )

            # Conditionally add Start Date for periodic badges
            if is_periodic:
                schema_fields.update(
                    {
                        vol.Optional(
                            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_START_DATE,
                            default=default_start_date,
                        ): vol.Any(None, selector.DateSelector()),
                    }
                )

            # End Date
            schema_fields.update(
                {
                    vol.Optional(
                        const.CFOF_BADGES_INPUT_RESET_SCHEDULE_END_DATE,
                        default=default_end_date,
                    ): vol.Any(None, selector.DateSelector()),
                }
            )

            # Nested Grace Period Days under is_cumulative flag
            if is_cumulative:
                schema_fields.update(
                    {
                        vol.Optional(
                            const.CFOF_BADGES_INPUT_RESET_SCHEDULE_GRACE_PERIOD_DAYS,
                            default=int(default_grace_period_days),
                        ): vol.All(
                            selector.NumberSelector(
                                selector.NumberSelectorConfig(
                                    mode=selector.NumberSelectorMode.BOX,
                                    min=0,
                                    step=1,
                                )
                            ),
                            vol.Coerce(int),  # Coerce to integer
                            vol.Range(min=0),  # Ensure non-negative values
                        ),
                    }
                )

    const.LOGGER.debug("DEBUG: Build Badge Common Schema - Returning Schema Fields")
    return schema_fields


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


def build_general_options_schema(default: Optional[dict] = None) -> vol.Schema:
    """Build schema for general options including points adjust values and update interval."""
    default = default or {}
    current_values = default.get(const.CONF_POINTS_ADJUST_VALUES)
    if current_values and isinstance(current_values, list):
        default_points_str = "|".join(str(v) for v in current_values)
    else:
        default_points_str = "|".join(
            str(v) for v in const.DEFAULT_POINTS_ADJUST_VALUES
        )

    default_interval = default.get(
        const.CONF_UPDATE_INTERVAL, const.DEFAULT_UPDATE_INTERVAL
    )
    default_calendar_period = default.get(
        const.CONF_CALENDAR_SHOW_PERIOD, const.DEFAULT_CALENDAR_SHOW_PERIOD
    )
    default_retention_daily = default.get(
        const.CONF_RETENTION_DAILY, const.DEFAULT_RETENTION_DAILY
    )
    default_retention_weekly = default.get(
        const.CONF_RETENTION_WEEKLY, const.DEFAULT_RETENTION_WEEKLY
    )
    default_retention_monthly = default.get(
        const.CONF_RETENTION_MONTHLY, const.DEFAULT_RETENTION_MONTHLY
    )
    default_retention_yearly = default.get(
        const.CONF_RETENTION_YEARLY, const.DEFAULT_RETENTION_YEARLY
    )

    return vol.Schema(
        {
            vol.Required(
                const.CONF_POINTS_ADJUST_VALUES, default=default_points_str
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=False,
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
            vol.Required(
                const.CONF_RETENTION_DAILY, default=default_retention_daily
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=1,
                    max=90,
                    step=1,
                )
            ),
            vol.Required(
                const.CONF_RETENTION_WEEKLY, default=default_retention_weekly
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=1,
                    max=52,
                    step=1,
                )
            ),
            vol.Required(
                const.CONF_RETENTION_MONTHLY, default=default_retention_monthly
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=1,
                    max=24,
                    step=1,
                )
            ),
            vol.Required(
                const.CONF_RETENTION_YEARLY, default=default_retention_yearly
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=1,
                    max=10,
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
def ensure_utc_datetime(hass: HomeAssistant, dt_value: Any) -> str:
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
