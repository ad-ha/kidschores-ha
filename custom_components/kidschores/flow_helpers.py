# File: flow_helpers.py
"""Helpers for the KidsChores integration's Config and Options flow.

Provides schema builders and input-processing logic for internal_id-based management.

## REFACTORING PATTERNS ##

This module implements TWO distinct refactoring patterns for different entity types:

### PATTERN 1: Simple Entities (Separate validate/build functions)
**Used for:** Kids, Parents, Rewards, Bonuses, Penalties

**Functions:**
- validate_<entity>_inputs(user_input, internal_id, existing_dict) -> errors_dict
- build_<entity>_schema(default, kids_dict, ...) -> schema_fields
- build_<entity>_data(user_input, internal_id) -> entity_dict

**Characteristics:**
- Validation returns error dict (empty dict = no errors)
- Build functions are pure data transformers
- Clear separation of concerns (validate, display schema, build data)
- Simpler entities with straightforward validation rules

**Example flow:**
```python
errors = validate_reward_inputs(user_input, internal_id, existing_rewards)
if not errors:
    reward_data = build_reward_data(user_input, internal_id)
```

### PATTERN 2: Complex Entities (Integrated validation with tuple return)
**Used for:** Chores, Achievements, Challenges

**Functions:**
- validate_<entity>_inputs(user_input, internal_id, existing_dict, ...)
  -> Tuple[errors_dict, data_dict]
- build_<entity>_schema(default, kids_dict, ...) -> schema_fields

**Characteristics:**
- Validation returns (errors, data) tuple
- Data is built INSIDE validation when there are no errors
- Handles complex validation requiring entity context
- Entities with interdependencies (e.g., shared/multi chores, badge triggers)

**Example flow:**
```python
errors, chore_data = validate_chore_inputs(
    user_input, internal_id, existing_chores, kids_dict
)
if not errors:
    # chore_data is already built with all processing done
    save_data(chore_data)
```

### CHOOSING A PATTERN ###

Use **Pattern 1 (Simple)** when:
- Validation rules are straightforward
- No complex interdependencies between fields
- Data building is mostly direct mapping from input

Use **Pattern 2 (Complex)** when:
- Validation requires computing/transforming values (e.g., kidIds from selected names)
- Entity has special modes (shared chores, multi-approval chores)
- Need to verify relationships with other entities during validation
- Data structure depends on validation outcomes

### MIGRATION NOTES ###

All entity types have been refactored from the old direct-processing pattern to
one of these two patterns. Pattern 2 evolved from Pattern 1 when complexity grew
beyond what made sense for separate validate/build functions.

Future entities should start with Pattern 1 and only move to Pattern 2 if
validation logic becomes complex enough to warrant it.
"""

# pyright: reportArgumentType=false
# Reason: Voluptuous schema definitions use dynamic typing that pyright cannot infer.
# The selector.SelectSelector and vol.Schema patterns are runtime-validated by Home Assistant.

import datetime
import json
import os
import shutil
import uuid
from typing import Any, Dict, Optional, Tuple

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from . import const
from . import kc_helpers as kh

# ----------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------------------------------


def _build_notification_defaults(default: Dict[str, Any]) -> list[str]:
    """Build default notification options from config.

    Args:
        default: Dictionary containing existing configuration defaults.

    Returns:
        List of selected notification option values.
    """
    notifications = []
    if default.get(
        const.CFOF_CHORES_INPUT_NOTIFY_ON_CLAIM, const.DEFAULT_NOTIFY_ON_CLAIM
    ):
        notifications.append(const.DATA_CHORE_NOTIFY_ON_CLAIM)
    if default.get(
        const.CFOF_CHORES_INPUT_NOTIFY_ON_APPROVAL, const.DEFAULT_NOTIFY_ON_APPROVAL
    ):
        notifications.append(const.DATA_CHORE_NOTIFY_ON_APPROVAL)
    if default.get(
        const.CFOF_CHORES_INPUT_NOTIFY_ON_DISAPPROVAL,
        const.DEFAULT_NOTIFY_ON_DISAPPROVAL,
    ):
        notifications.append(const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL)
    return notifications


# ----------------------------------------------------------------------------------
# POINTS SCHEMA
# ----------------------------------------------------------------------------------


def build_points_schema(
    default_label=const.DEFAULT_POINTS_LABEL, default_icon=const.DEFAULT_POINTS_ICON
):
    """Build a schema for points label & icon."""
    return vol.Schema(
        {
            vol.Required(
                const.CFOF_SYSTEM_INPUT_POINTS_LABEL, default=default_label
            ): str,
            vol.Optional(
                const.CFOF_SYSTEM_INPUT_POINTS_ICON, default=default_icon
            ): selector.IconSelector(),
        }
    )


def build_points_data(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """Build points configuration data from user input.

    Converts form input (CONF_* keys) to system settings format.

    Args:
        user_input: Dictionary containing user inputs from the form.

    Returns:
        Dictionary with points label and icon configuration.
    """
    return {
        const.CONF_POINTS_LABEL: user_input.get(
            const.CFOF_SYSTEM_INPUT_POINTS_LABEL, const.DEFAULT_POINTS_LABEL
        ),
        const.CONF_POINTS_ICON: user_input.get(
            const.CFOF_SYSTEM_INPUT_POINTS_ICON, const.DEFAULT_POINTS_ICON
        ),
    }


def validate_points_inputs(user_input: Dict[str, Any]) -> Dict[str, str]:
    """Validate points configuration inputs.

    Args:
        user_input: Dictionary containing user inputs from the form.

    Returns:
        Dictionary of errors (empty if validation passes).
    """
    errors = {}

    points_label = user_input.get(const.CFOF_SYSTEM_INPUT_POINTS_LABEL, "").strip()

    # Validate label is not empty
    if not points_label:
        errors["base"] = const.TRANS_KEY_CFOF_POINTS_LABEL_REQUIRED

    return errors


# ----------------------------------------------------------------------------------
# KIDS SCHEMA (Pattern 1: Simple - Separate validate/build)
# ----------------------------------------------------------------------------------


async def build_kid_schema(
    hass,
    users,
    default_kid_name=const.SENTINEL_EMPTY,
    default_ha_user_id=None,
    default_enable_mobile_notifications=False,
    default_mobile_notify_service=None,
    default_enable_persistent_notifications=False,
    default_dashboard_language=None,
):
    """Build a Voluptuous schema for adding/editing a Kid, keyed by internal_id in the dict."""
    user_options = [{"value": const.SENTINEL_EMPTY, "label": const.LABEL_NONE}] + [
        {"value": user.id, "label": user.name} for user in users
    ]
    notify_options = [
        {"value": const.SENTINEL_EMPTY, "label": const.LABEL_NONE}
    ] + _get_notify_services(hass)

    # Get available dashboard languages
    language_options = await kh.get_available_dashboard_languages(hass)

    return vol.Schema(
        {
            vol.Required(const.CFOF_KIDS_INPUT_KID_NAME, default=default_kid_name): str,
            vol.Optional(
                const.CFOF_KIDS_INPUT_HA_USER,
                default=default_ha_user_id or const.SENTINEL_EMPTY,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=user_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False,
                )
            ),
            vol.Optional(
                const.CFOF_KIDS_INPUT_DASHBOARD_LANGUAGE,
                default=default_dashboard_language or const.DEFAULT_DASHBOARD_LANGUAGE,
            ): selector.LanguageSelector(
                selector.LanguageSelectorConfig(
                    languages=language_options,
                    native_name=True,
                )
            ),
            vol.Required(
                const.CFOF_KIDS_INPUT_ENABLE_MOBILE_NOTIFICATIONS,
                default=default_enable_mobile_notifications,
            ): selector.BooleanSelector(),
            vol.Optional(
                const.CFOF_KIDS_INPUT_MOBILE_NOTIFY_SERVICE,
                default=default_mobile_notify_service or const.SENTINEL_EMPTY,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=notify_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False,
                )
            ),
            vol.Required(
                const.CFOF_KIDS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS,
                default=default_enable_persistent_notifications,
            ): selector.BooleanSelector(),
        }
    )


def build_kids_data(
    user_input: Dict[str, Any],
    existing_kids: Dict[str, Any] = None,  # pylint: disable=unused-argument  # Reserved for API consistency with validate_kids_inputs
) -> Dict[str, Any]:
    """Build kid data from user input.

    Converts form input (CFOF_* keys) to storage format (DATA_* keys).

    Args:
        user_input: Dictionary containing user inputs from the form.
        existing_kids: Optional dictionary of existing kids for duplicate checking.

    Returns:
        Dictionary with kid data in storage format, keyed by internal_id.
    """
    kid_name = user_input.get(const.CFOF_KIDS_INPUT_KID_NAME, "").strip()
    internal_id = user_input.get(const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4()))

    ha_user_id = user_input.get(const.CFOF_KIDS_INPUT_HA_USER) or const.SENTINEL_EMPTY
    enable_mobile_notifications = user_input.get(
        const.CFOF_KIDS_INPUT_ENABLE_MOBILE_NOTIFICATIONS, True
    )
    notify_service = (
        user_input.get(const.CFOF_KIDS_INPUT_MOBILE_NOTIFY_SERVICE)
        or const.SENTINEL_EMPTY
    )
    enable_persist = user_input.get(
        const.CFOF_KIDS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS, True
    )
    dashboard_language = user_input.get(
        const.CFOF_KIDS_INPUT_DASHBOARD_LANGUAGE, const.DEFAULT_DASHBOARD_LANGUAGE
    )

    return {
        internal_id: {
            const.DATA_KID_NAME: kid_name,
            const.DATA_KID_HA_USER_ID: ha_user_id,
            const.DATA_KID_ENABLE_NOTIFICATIONS: enable_mobile_notifications,
            const.DATA_KID_MOBILE_NOTIFY_SERVICE: notify_service,
            const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS: enable_persist,
            const.DATA_KID_DASHBOARD_LANGUAGE: dashboard_language,
            const.DATA_KID_INTERNAL_ID: internal_id,
        }
    }


def validate_kids_inputs(
    user_input: Dict[str, Any], existing_kids: Dict[str, Any] = None
) -> Dict[str, str]:
    """Validate kid configuration inputs.

    Args:
        user_input: Dictionary containing user inputs from the form.
        existing_kids: Optional dictionary of existing kids for duplicate checking.

    Returns:
        Dictionary of errors (empty if validation passes).
    """
    errors = {}

    kid_name = user_input.get(const.CFOF_KIDS_INPUT_KID_NAME, "").strip()

    # Validate name is not empty
    if not kid_name:
        errors[const.CFOP_ERROR_KID_NAME] = const.TRANS_KEY_CFOF_INVALID_KID_NAME
        return errors

    # Check for duplicate names
    if existing_kids:
        if any(
            kid_data[const.DATA_KID_NAME] == kid_name
            for kid_data in existing_kids.values()
        ):
            errors[const.CFOP_ERROR_KID_NAME] = const.TRANS_KEY_CFOF_DUPLICATE_KID

    return errors


# ----------------------------------------------------------------------------------
# PARENTS SCHEMA (Pattern 1: Simple - Separate validate/build)
# ----------------------------------------------------------------------------------


def build_parent_schema(
    hass,
    users,
    kids_dict,
    default_parent_name=const.SENTINEL_EMPTY,
    default_ha_user_id=None,
    default_associated_kids=None,
    default_enable_mobile_notifications=False,
    default_mobile_notify_service=None,
    default_enable_persistent_notifications=False,
):
    """Build a Voluptuous schema for adding/editing a Parent, keyed by internal_id in the dict."""
    user_options = [{"value": const.SENTINEL_EMPTY, "label": const.LABEL_NONE}] + [
        {"value": user.id, "label": user.name} for user in users
    ]
    kid_options = [
        {"value": kid_id, "label": kid_name} for kid_name, kid_id in kids_dict.items()
    ]
    notify_options = [
        {"value": const.SENTINEL_EMPTY, "label": const.LABEL_NONE}
    ] + _get_notify_services(hass)

    return vol.Schema(
        {
            vol.Required(
                const.CFOF_PARENTS_INPUT_NAME, default=default_parent_name
            ): str,
            vol.Optional(
                const.CFOF_PARENTS_INPUT_HA_USER,
                default=default_ha_user_id or const.SENTINEL_EMPTY,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=user_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False,
                )
            ),
            vol.Optional(
                const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS,
                default=default_associated_kids or [],
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=kid_options,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_ASSOCIATED_KIDS,
                    multiple=True,
                )
            ),
            vol.Required(
                const.CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS,
                default=default_enable_mobile_notifications,
            ): selector.BooleanSelector(),
            vol.Optional(
                const.CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE,
                default=default_mobile_notify_service or const.SENTINEL_EMPTY,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=notify_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False,
                )
            ),
            vol.Required(
                const.CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS,
                default=default_enable_persistent_notifications,
            ): selector.BooleanSelector(),
        }
    )


def build_parents_data(
    user_input: Dict[str, Any],
    existing_parents: Dict[str, Any] = None,  # pylint: disable=unused-argument  # Reserved for API consistency with validate_parents_inputs
) -> Dict[str, Any]:
    """Build parent data from user input.

    Converts form input (CFOF_* keys) to storage format (DATA_* keys).

    Args:
        user_input: Dictionary containing user inputs from the form.
        existing_parents: Optional dictionary of existing parents for duplicate checking.

    Returns:
        Dictionary with parent data in storage format, keyed by internal_id.
    """
    parent_name = user_input.get(const.CFOF_PARENTS_INPUT_NAME, "").strip()
    internal_id = user_input.get(const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4()))

    ha_user_id = (
        user_input.get(const.CFOF_PARENTS_INPUT_HA_USER) or const.SENTINEL_EMPTY
    )
    associated_kids = user_input.get(const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS, [])
    enable_mobile_notifications = user_input.get(
        const.CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS, True
    )
    notify_service = (
        user_input.get(const.CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE)
        or const.SENTINEL_EMPTY
    )
    enable_persist = user_input.get(
        const.CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS, True
    )

    return {
        internal_id: {
            const.DATA_PARENT_NAME: parent_name,
            const.DATA_PARENT_HA_USER_ID: ha_user_id,
            const.DATA_PARENT_ASSOCIATED_KIDS: associated_kids,
            const.DATA_PARENT_ENABLE_NOTIFICATIONS: enable_mobile_notifications,
            const.DATA_PARENT_MOBILE_NOTIFY_SERVICE: notify_service,
            const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS: enable_persist,
            const.DATA_PARENT_INTERNAL_ID: internal_id,
        }
    }


def validate_parents_inputs(
    user_input: Dict[str, Any], existing_parents: Dict[str, Any] = None
) -> Dict[str, str]:
    """Validate parent configuration inputs.

    Args:
        user_input: Dictionary containing user inputs from the form.
        existing_parents: Optional dictionary of existing parents for duplicate checking.

    Returns:
        Dictionary of errors (empty if validation passes).
    """
    errors = {}

    parent_name = user_input.get(const.CFOF_PARENTS_INPUT_NAME, "").strip()

    # Validate name is not empty
    if not parent_name:
        errors[const.CFOP_ERROR_PARENT_NAME] = const.TRANS_KEY_CFOF_INVALID_PARENT_NAME
        return errors

    # Check for duplicate names
    if existing_parents:
        if any(
            parent_data[const.DATA_PARENT_NAME] == parent_name
            for parent_data in existing_parents.values()
        ):
            errors[const.CFOP_ERROR_PARENT_NAME] = const.TRANS_KEY_CFOF_DUPLICATE_PARENT

    return errors


# ----------------------------------------------------------------------------------
# CHORES SCHEMA (Pattern 2: Complex - Integrated validation with tuple return)
# ----------------------------------------------------------------------------------


def build_chore_schema(kids_dict, default=None):
    """Build a schema for chores, referencing existing kids by name.

    Uses internal_id for entity management.
    Dynamically adds "clear due date" checkbox when editing with existing date.
    """
    default = default or {}
    chore_name_default = default.get(const.DATA_CHORE_NAME, const.SENTINEL_EMPTY)

    kid_choices = {k: k for k in kids_dict}

    # Check if there's an existing due date (for edit mode)
    existing_due_date = default.get(const.CFOF_CHORES_INPUT_DUE_DATE) or default.get(
        const.DATA_CHORE_DUE_DATE
    )

    # Build schema fields dict
    schema_fields: dict[Any, Any] = {
        vol.Required(const.CFOF_CHORES_INPUT_NAME, default=chore_name_default): str,
        vol.Optional(
            const.CFOF_CHORES_INPUT_DESCRIPTION,
            default=default.get(const.DATA_CHORE_DESCRIPTION, const.SENTINEL_EMPTY),
        ): str,
        vol.Optional(
            const.CFOF_CHORES_INPUT_ICON,
            default=default.get(const.DATA_CHORE_ICON, const.DEFAULT_CHORE_ICON),
        ): selector.IconSelector(),
        vol.Optional(
            const.CFOF_CHORES_INPUT_LABELS,
            default=default.get(const.CFOF_CHORES_INPUT_LABELS, []),
        ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
        vol.Required(
            const.CFOF_CHORES_INPUT_DEFAULT_POINTS,
            default=default.get(
                const.CFOF_CHORES_INPUT_DEFAULT_POINTS, const.DEFAULT_POINTS
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                min=0,
                step=0.1,
            )
        ),
        vol.Required(
            const.CFOF_CHORES_INPUT_ASSIGNED_KIDS,
            default=default.get(const.CFOF_CHORES_INPUT_ASSIGNED_KIDS, []),
        ): cv.multi_select(kid_choices),
        vol.Required(
            const.CFOF_CHORES_INPUT_COMPLETION_CRITERIA,
            default=default.get(
                const.CFOF_CHORES_INPUT_COMPLETION_CRITERIA,
                const.COMPLETION_CRITERIA_INDEPENDENT,
            ),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=const.COMPLETION_CRITERIA_OPTIONS,
                translation_key=const.TRANS_KEY_FLOW_HELPERS_COMPLETION_CRITERIA,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(
            const.CFOF_CHORES_INPUT_APPROVAL_RESET_TYPE,
            default=default.get(
                const.CFOF_CHORES_INPUT_APPROVAL_RESET_TYPE,
                const.DEFAULT_APPROVAL_RESET_TYPE,
            ),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=const.APPROVAL_RESET_TYPE_OPTIONS,
                translation_key=const.TRANS_KEY_FLOW_HELPERS_APPROVAL_RESET_TYPE,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(
            const.CFOF_CHORES_INPUT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
            default=default.get(
                const.CFOF_CHORES_INPUT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
                const.DEFAULT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
            ),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=const.APPROVAL_RESET_PENDING_CLAIM_ACTION_OPTIONS,
                translation_key=const.TRANS_KEY_FLOW_HELPERS_APPROVAL_RESET_PENDING_CLAIM_ACTION,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(
            const.CFOF_CHORES_INPUT_OVERDUE_HANDLING_TYPE,
            default=default.get(
                const.CFOF_CHORES_INPUT_OVERDUE_HANDLING_TYPE,
                const.DEFAULT_OVERDUE_HANDLING_TYPE,
            ),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=const.OVERDUE_HANDLING_TYPE_OPTIONS,
                translation_key=const.TRANS_KEY_FLOW_HELPERS_OVERDUE_HANDLING_TYPE,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(
            const.CFOF_CHORES_INPUT_AUTO_APPROVE,
            default=default.get(
                const.CFOF_CHORES_INPUT_AUTO_APPROVE,
                const.DEFAULT_CHORE_AUTO_APPROVE,
            ),
        ): selector.BooleanSelector(),
        vol.Required(
            const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY,
            default=default.get(
                const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY, const.FREQUENCY_NONE
            ),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=const.FREQUENCY_OPTIONS,
                translation_key=const.TRANS_KEY_FLOW_HELPERS_RECURRING_FREQUENCY,
            )
        ),
        vol.Optional(
            const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL,
            default=default.get(const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL, None),
        ): vol.Any(
            None,
            selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX, min=1, step=1
                )
            ),
        ),
        vol.Optional(
            const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL_UNIT,
            default=default.get(const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL_UNIT, None),
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
            const.CFOF_CHORES_INPUT_APPLICABLE_DAYS,
            default=default.get(
                const.CFOF_CHORES_INPUT_APPLICABLE_DAYS,
                const.DEFAULT_APPLICABLE_DAYS,
            ),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": key, "label": label}
                    for key, label in const.WEEKDAY_OPTIONS.items()
                ],
                multiple=True,
                translation_key=const.TRANS_KEY_FLOW_HELPERS_APPLICABLE_DAYS,
            )
        ),
        vol.Optional(
            const.CFOF_CHORES_INPUT_DUE_DATE,
            default=default.get(const.CFOF_CHORES_INPUT_DUE_DATE),
        ): vol.Any(None, selector.DateTimeSelector()),
    }

    # Add "Clear due date" checkbox only when there's an existing date
    if existing_due_date:
        schema_fields[
            vol.Optional(const.CFOF_CHORES_INPUT_CLEAR_DUE_DATE, default=False)
        ] = selector.BooleanSelector()

    # Add remaining fields
    schema_fields[
        vol.Required(
            const.CFOF_CHORES_INPUT_SHOW_ON_CALENDAR,
            default=default.get(const.CFOF_CHORES_INPUT_SHOW_ON_CALENDAR, True),
        )
    ] = selector.BooleanSelector()

    schema_fields[
        vol.Optional(
            const.CFOF_CHORES_INPUT_NOTIFICATIONS,
            default=_build_notification_defaults(default),
        )
    ] = selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                const.DATA_CHORE_NOTIFY_ON_CLAIM,
                const.DATA_CHORE_NOTIFY_ON_APPROVAL,
                const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL,
            ],
            multiple=True,
            translation_key=const.TRANS_KEY_FLOW_HELPERS_CHORE_NOTIFICATIONS,
        )
    )

    return vol.Schema(schema_fields)


def build_chores_data(
    user_input: Dict[str, Any],
    kids_dict: Dict[str, Any],
    existing_chores: Dict[str, Any] = None,
    existing_per_kid_due_dates: Dict[str, str | None] = None,
) -> tuple[Dict[str, Any], Dict[str, str]]:
    """Build chore data from user input with validation.

    Converts form input (CFOF_* keys) to storage format (DATA_* keys).
    Also validates the due date and converts assigned kid names to UUIDs.

    Args:
        user_input: Dictionary containing user inputs from the form.
        kids_dict: Dictionary mapping kid names to kid internal_ids (UUIDs).
        existing_chores: Optional dictionary of existing chores for duplicate checking.
        existing_per_kid_due_dates: Optional dictionary of existing per-kid due dates
            to preserve when editing INDEPENDENT chores. Keys are kid UUIDs, values
            are ISO datetime strings or None. New kids use template date.

    Returns:
        Tuple of (chore_data_dict, errors_dict). If errors exist, chore_data will be empty.
    """
    errors = {}
    chore_name = user_input.get(const.CFOF_CHORES_INPUT_NAME, "").strip()
    internal_id = user_input.get(const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4()))

    # Validate chore name
    if not chore_name:
        errors[const.CFOP_ERROR_CHORE_NAME] = const.TRANS_KEY_CFOF_INVALID_CHORE_NAME
        return {}, errors

    # Check for duplicate names
    if existing_chores and any(
        chore_data[const.DATA_CHORE_NAME] == chore_name
        for chore_data in existing_chores.values()
    ):
        errors[const.CFOP_ERROR_CHORE_NAME] = const.TRANS_KEY_CFOF_DUPLICATE_CHORE
        return {}, errors

    # Process due date
    # Check if user explicitly wants to clear the date
    clear_due_date = user_input.get(const.CFOF_CHORES_INPUT_CLEAR_DUE_DATE, False)
    due_date_str = None

    if clear_due_date:
        # User explicitly cleared the date
        const.LOGGER.debug("build_chores_data: user cleared due date via checkbox")
        due_date_str = None
    elif user_input.get(const.CFOF_CHORES_INPUT_DUE_DATE):
        raw_due = user_input[const.CFOF_CHORES_INPUT_DUE_DATE]
        const.LOGGER.debug(
            "build_chores_data: raw_due input = %s (type: %s)",
            raw_due,
            type(raw_due).__name__,
        )
        try:
            due_dt = kh.normalize_datetime_input(
                raw_due,
                default_tzinfo=const.DEFAULT_TIME_ZONE,
                return_type=const.HELPER_RETURN_DATETIME_UTC,
            )
            const.LOGGER.debug(
                "build_chores_data: normalized due_dt = %s (type: %s)",
                due_dt,
                type(due_dt).__name__ if due_dt else "None",
            )
            # Type guard: narrow datetime | date | str | None to datetime
            if due_dt and not isinstance(due_dt, datetime.datetime):
                const.LOGGER.warning(
                    "build_chores_data: due_dt is not datetime: %s", type(due_dt)
                )
                errors[const.CFOP_ERROR_DUE_DATE] = (
                    const.TRANS_KEY_CFOF_INVALID_DUE_DATE
                )
                return {}, errors
            if due_dt and due_dt < dt_util.utcnow():
                const.LOGGER.warning(
                    "build_chores_data: due_dt in past: %s < %s",
                    due_dt,
                    dt_util.utcnow(),
                )
                errors[const.CFOP_ERROR_DUE_DATE] = (
                    const.TRANS_KEY_CFOF_DUE_DATE_IN_PAST
                )
                return {}, errors
            # Store the normalized due date as ISO string
            if due_dt:
                due_date_str = due_dt.isoformat()
        except (ValueError, TypeError, AttributeError) as exc:
            const.LOGGER.warning(
                "build_chores_data: exception parsing due date: %s", exc
            )
            errors[const.CFOP_ERROR_DUE_DATE] = const.TRANS_KEY_CFOF_INVALID_DUE_DATE
            return {}, errors

    # Clean up custom interval fields if not using custom frequency
    if (
        user_input.get(const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY)
        != const.FREQUENCY_CUSTOM
    ):
        custom_interval = None
        custom_interval_unit = None
    else:
        custom_interval = user_input.get(const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL)
        custom_interval_unit = user_input.get(
            const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL_UNIT
        )

    # Convert assigned kid names to UUIDs
    assigned_kids_names = user_input.get(const.CFOF_CHORES_INPUT_ASSIGNED_KIDS, [])
    assigned_kids_ids = [
        kids_dict[kid_name] for kid_name in assigned_kids_names if kid_name in kids_dict
    ]

    # Validate at least one kid is assigned
    if not assigned_kids_ids:
        errors[const.CFOP_ERROR_ASSIGNED_KIDS] = const.TRANS_KEY_CFOF_NO_KIDS_ASSIGNED
        return {}, errors

    # Validate AT_DUE_DATE_THEN_RESET only works with AT_MIDNIGHT_* reset types
    overdue_handling = user_input.get(
        const.CFOF_CHORES_INPUT_OVERDUE_HANDLING_TYPE,
        const.DEFAULT_OVERDUE_HANDLING_TYPE,
    )
    approval_reset = user_input.get(
        const.CFOF_CHORES_INPUT_APPROVAL_RESET_TYPE,
        const.DEFAULT_APPROVAL_RESET_TYPE,
    )
    if overdue_handling == const.OVERDUE_HANDLING_AT_DUE_DATE_THEN_RESET:
        # AT_DUE_DATE_THEN_RESET only makes sense with midnight resets
        # where the reset time is AFTER the due date
        valid_reset_types = {
            const.APPROVAL_RESET_AT_MIDNIGHT_ONCE,
            const.APPROVAL_RESET_AT_MIDNIGHT_MULTI,
        }
        if approval_reset not in valid_reset_types:
            errors[const.CFOP_ERROR_OVERDUE_RESET_COMBO] = (
                const.TRANS_KEY_CFOF_INVALID_OVERDUE_RESET_COMBINATION
            )
            return {}, errors

    # Build chore data
    completion_criteria = user_input.get(
        const.CFOF_CHORES_INPUT_COMPLETION_CRITERIA,
        const.COMPLETION_CRITERIA_INDEPENDENT,
    )

    # Build per_kid_due_dates for ALL chores (SHARED + INDEPENDENT)
    # - SHARED: All kids have same date (synced with chore-level)
    # - INDEPENDENT: Template on creation, preserve existing per-kid overrides on edit
    #   (unless user explicitly cleared the date via checkbox)
    per_kid_due_dates: dict[str, str | None] = {}
    for kid_id in assigned_kids_ids:
        # For INDEPENDENT chores being edited: preserve existing per-kid dates
        # UNLESS user explicitly cleared the date via checkbox
        # For new kids or SHARED chores: use template date
        if (
            existing_per_kid_due_dates
            and completion_criteria == const.COMPLETION_CRITERIA_INDEPENDENT
            and kid_id in existing_per_kid_due_dates
            and not clear_due_date  # Don't preserve if user wants to clear
        ):
            # Preserve existing per-kid date (may have been set via service)
            per_kid_due_dates[kid_id] = existing_per_kid_due_dates[kid_id]
        else:
            # New kid, SHARED chore, or explicit clear: use template date (may be None)
            per_kid_due_dates[kid_id] = due_date_str  # Can be None (never overdue)

    # Build partial chore data from user input
    # The shared helper (kh.build_default_chore_data) will apply all defaults
    partial_chore_data = {
        const.DATA_CHORE_NAME: chore_name,
        const.DATA_CHORE_DEFAULT_POINTS: user_input.get(
            const.CFOF_CHORES_INPUT_DEFAULT_POINTS, const.DEFAULT_POINTS
        ),
        # Completion criteria (new canonical field)
        const.DATA_CHORE_COMPLETION_CRITERIA: completion_criteria,
        # Per-kid due dates for independent tracking
        const.DATA_CHORE_PER_KID_DUE_DATES: per_kid_due_dates,
        const.DATA_CHORE_APPROVAL_RESET_TYPE: user_input.get(
            const.CFOF_CHORES_INPUT_APPROVAL_RESET_TYPE,
            const.DEFAULT_APPROVAL_RESET_TYPE,
        ),
        # Phase 5: Overdue handling type
        const.DATA_CHORE_OVERDUE_HANDLING_TYPE: user_input.get(
            const.CFOF_CHORES_INPUT_OVERDUE_HANDLING_TYPE,
            const.DEFAULT_OVERDUE_HANDLING_TYPE,
        ),
        # Phase 5: Pending claim action at approval reset
        const.DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION: user_input.get(
            const.CFOF_CHORES_INPUT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
            const.DEFAULT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
        ),
        const.DATA_CHORE_ASSIGNED_KIDS: assigned_kids_ids,
        const.DATA_CHORE_DESCRIPTION: user_input.get(
            const.CFOF_CHORES_INPUT_DESCRIPTION, const.SENTINEL_EMPTY
        ),
        const.DATA_CHORE_LABELS: user_input.get(const.CFOF_CHORES_INPUT_LABELS, []),
        const.DATA_CHORE_ICON: user_input.get(
            const.CFOF_CHORES_INPUT_ICON, const.DEFAULT_CHORE_ICON
        ),
        const.DATA_CHORE_RECURRING_FREQUENCY: user_input.get(
            const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY, const.SENTINEL_EMPTY
        ),
        const.DATA_CHORE_CUSTOM_INTERVAL: custom_interval,
        const.DATA_CHORE_CUSTOM_INTERVAL_UNIT: custom_interval_unit,
        # For INDEPENDENT chores, chore-level due_date is cleared since per_kid_due_dates
        # are authoritative. The template value is just for UX convenience during editing.
        # For SHARED chores, chore-level due_date is the source of truth.
        const.DATA_CHORE_DUE_DATE: (
            None
            if completion_criteria == const.COMPLETION_CRITERIA_INDEPENDENT
            else due_date_str
        ),
        const.DATA_CHORE_APPLICABLE_DAYS: user_input.get(
            const.CFOF_CHORES_INPUT_APPLICABLE_DAYS,
            const.DEFAULT_APPLICABLE_DAYS,
        ),
        # Extract notification selections from consolidated field
        const.DATA_CHORE_NOTIFY_ON_CLAIM: (
            const.DATA_CHORE_NOTIFY_ON_CLAIM
            in user_input.get(const.CFOF_CHORES_INPUT_NOTIFICATIONS, [])
        ),
        const.DATA_CHORE_NOTIFY_ON_APPROVAL: (
            const.DATA_CHORE_NOTIFY_ON_APPROVAL
            in user_input.get(const.CFOF_CHORES_INPUT_NOTIFICATIONS, [])
        ),
        const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL: (
            const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL
            in user_input.get(const.CFOF_CHORES_INPUT_NOTIFICATIONS, [])
        ),
        # Calendar and auto-approve settings
        const.DATA_CHORE_SHOW_ON_CALENDAR: user_input.get(
            const.CFOF_CHORES_INPUT_SHOW_ON_CALENDAR,
            const.DEFAULT_CHORE_SHOW_ON_CALENDAR,
        ),
        const.DATA_CHORE_AUTO_APPROVE: user_input.get(
            const.CFOF_CHORES_INPUT_AUTO_APPROVE,
            const.DEFAULT_CHORE_AUTO_APPROVE,
        ),
    }

    # Use shared helper to build complete chore data with all defaults
    # This is the SINGLE SOURCE OF TRUTH for chore field initialization
    chore_data = kh.build_default_chore_data(internal_id, partial_chore_data)

    return {internal_id: chore_data}, {}


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
        badge_type: The type of the badge (cumulative, daily, periodic).
            Default is cumulative.

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
            const.CFOF_BADGES_INPUT_DESCRIPTION, const.SENTINEL_EMPTY
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

        # Build target dict - only add target_type for non-cumulative badges
        target_dict = {
            const.DATA_BADGE_TARGET_THRESHOLD_VALUE: threshold_value,
            const.DATA_BADGE_MAINTENANCE_RULES: maintenance_rules,
        }

        # Cumulative badges don't need target_type (they always use points)
        if badge_type != const.BADGE_TYPE_CUMULATIVE:
            target_dict[const.DATA_BADGE_TARGET_TYPE] = target_type

        badge_data[const.DATA_BADGE_TARGET] = target_dict

    # --- Special Occasion Component ---
    if include_special_occasion:
        occasion_type = user_input.get(
            const.CFOF_BADGES_INPUT_OCCASION_TYPE, const.SENTINEL_EMPTY
        )
        badge_data[const.DATA_BADGE_SPECIAL_OCCASION_TYPE] = occasion_type

    # --- Achievement-Linked Component ---
    if include_achievement_linked:
        achievement_id = user_input.get(
            const.CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT, const.SENTINEL_EMPTY
        )
        badge_data[const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT] = achievement_id

    # --- Challenge-Linked Component ---
    if include_challenge_linked:
        challenge_id = user_input.get(
            const.CFOF_BADGES_INPUT_ASSOCIATED_CHALLENGE, const.SENTINEL_EMPTY
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
            if chore_id and chore_id != const.SENTINEL_EMPTY
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
            kid_id for kid_id in assigned if kid_id and kid_id != const.SENTINEL_EMPTY
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
            const.CFOF_BADGES_INPUT_POINTS_MULTIPLIER, const.SENTINEL_NONE
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
            const.FREQUENCY_WEEKLY,  # Default mode if not provided
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

        if recurring_frequency == const.FREQUENCY_CUSTOM:
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
        internal_id: The internal ID for the badge (None when adding new).
        existing_badges: Dictionary of existing badges for uniqueness checks.
        badge_type: The type of the badge (cumulative, daily, periodic).
            Default is cumulative.

    Returns:
        A dictionary of validation errors {field_key: error_message}.
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

    # Feature Change v4.2: Validate assigned_to is not empty for badge types that support it
    if include_assigned_to:
        assigned_to = user_input.get(const.CFOF_BADGES_INPUT_ASSIGNED_TO, [])
        if not assigned_to or len(assigned_to) == 0:
            errors[const.CFOF_BADGES_INPUT_ASSIGNED_TO] = (
                const.TRANS_KEY_CFOF_BADGE_REQUIRES_ASSIGNMENT
            )

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

            # Validate threshold value
            target_threshold = user_input.get(
                const.CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE
            )

            if target_threshold is None or str(target_threshold).strip() == "":
                errors[const.CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE] = (
                    const.TRANS_KEY_CFOF_TARGET_THRESHOLD_REQUIRED
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

            # Validate maintenance rules
            maintenance_rules = user_input.get(
                const.CFOF_BADGES_INPUT_MAINTENANCE_RULES
            )
            if maintenance_rules is None or maintenance_rules < 0:
                errors[const.CFOF_BADGES_INPUT_MAINTENANCE_RULES] = (
                    const.TRANS_KEY_CFOF_INVALID_MAINTENANCE_RULES
                )
        else:
            # Regular badge validation
            target_threshold = user_input.get(
                const.CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE
            )

            if target_threshold is None or str(target_threshold).strip() == "":
                errors[const.CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE] = (
                    const.TRANS_KEY_CFOF_TARGET_THRESHOLD_REQUIRED
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
            const.CFOF_BADGES_INPUT_OCCASION_TYPE, const.SENTINEL_EMPTY
        )
        if not occasion_type or occasion_type == const.SENTINEL_EMPTY:
            errors[const.CFOF_BADGES_INPUT_OCCASION_TYPE] = (
                const.TRANS_KEY_CFOF_ERROR_BADGE_OCCASION_TYPE_REQUIRED
            )

    # --- Achievement-Linked Validation ---
    if include_achievement_linked:
        achievement_id = user_input.get(
            const.CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT, const.SENTINEL_EMPTY
        )
        if not achievement_id or achievement_id == const.SENTINEL_EMPTY:
            errors[const.CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT] = (
                const.TRANS_KEY_CFOF_ERROR_BADGE_ACHIEVEMENT_REQUIRED
            )

    # --- Challenge-Linked Validation ---
    if include_challenge_linked:
        challenge_id = user_input.get(
            const.CFOF_BADGES_INPUT_ASSOCIATED_CHALLENGE, const.SENTINEL_EMPTY
        )
        if not challenge_id or challenge_id == const.SENTINEL_EMPTY:
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
            user_input[const.CFOF_BADGES_INPUT_POINTS_MULTIPLIER] = const.SENTINEL_NONE

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
        if recurring_frequency != const.FREQUENCY_CUSTOM:
            # Note: END_DATE not cleared - can be used as reference date
            user_input.update(
                {
                    const.CFOF_BADGES_INPUT_RESET_SCHEDULE_START_DATE: const.SENTINEL_NONE,
                    const.CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL: const.SENTINEL_NONE,
                    const.CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT: const.SENTINEL_NONE,
                }
            )

        start_date = user_input.get(const.CFOF_BADGES_INPUT_RESET_SCHEDULE_START_DATE)
        end_date = user_input.get(const.CFOF_BADGES_INPUT_RESET_SCHEDULE_END_DATE)

        if recurring_frequency == const.FREQUENCY_CUSTOM:
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
                    const.TRANS_KEY_CFOF_END_DATE_BEFORE_START
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
                const.FREQUENCY_DAILY
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
        badge_type: The type of the badge (cumulative, daily, periodic).
            Default is cumulative.

    Special Notes:
        The `default` parameter is populated dynamically:
        - On first load: receives `badge_data`
        - After error: receives `user_input`
        This pre-fills fields while preserving user changes when form
        is regenerated after validation errors.
        Note: user_input field names don't always match badge data keys.

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
        "Build Badge Common Schema - Badge Data Passed to Schema: %s", default
    )

    # --- Start Common Schema ---
    # See Special Notes above for explanation of default usage rational
    schema_fields.update(
        {
            vol.Required(
                const.CFOF_BADGES_INPUT_NAME,
                default=default.get(
                    const.CFOF_BADGES_INPUT_NAME,
                    default.get(const.DATA_BADGE_NAME, const.SENTINEL_EMPTY),
                ),
            ): str,
            vol.Optional(
                const.CFOF_BADGES_INPUT_DESCRIPTION,
                default=default.get(
                    const.CFOF_BADGES_INPUT_DESCRIPTION,
                    default.get(const.DATA_BADGE_DESCRIPTION, const.SENTINEL_EMPTY),
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

        # Ensure default_threshold is always convertible to float
        try:
            default_threshold_float = float(default_threshold)
        except (TypeError, ValueError):
            default_threshold_float = float(const.DEFAULT_BADGE_TARGET_THRESHOLD_VALUE)

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
                        default=default_threshold_float,
                    ): vol.All(
                        selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                mode=selector.NumberSelectorMode.BOX,
                                min=0,
                                step=1,
                            )
                        ),
                        vol.Coerce(float),  # Coerce the input to a float
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
            default.get(const.DATA_BADGE_SPECIAL_OCCASION_TYPE, const.SENTINEL_EMPTY),
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
            {"value": const.SENTINEL_EMPTY, "label": const.LABEL_NONE}
        ] + [
            {
                "value": achievement_id,
                "label": achievement.get(
                    const.DATA_ACHIEVEMENT_NAME, const.SENTINEL_NONE_TEXT
                ),
            }
            for achievement_id, achievement in achievements_dict.items()
        ]
        default_achievement = default.get(
            const.CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT,
            default.get(const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT, const.SENTINEL_EMPTY),
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
        challenge_options = [
            {"value": const.SENTINEL_EMPTY, "label": const.LABEL_NONE}
        ] + [
            {
                "value": challenge_id,
                "label": challenge.get(
                    const.DATA_CHALLENGE_NAME, const.SENTINEL_NONE_TEXT
                ),
            }
            for challenge_id, challenge in challenges_dict.items()
        ]
        default_challenge = default.get(
            const.CFOF_BADGES_INPUT_ASSOCIATED_CHALLENGE,
            default.get(const.DATA_BADGE_ASSOCIATED_CHALLENGE, const.SENTINEL_EMPTY),
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
        options = [{"value": const.SENTINEL_EMPTY, "label": const.LABEL_NONE}]
        options += [
            {
                "value": chore_id,
                "label": chore.get(const.DATA_CHORE_NAME, const.SENTINEL_NONE_TEXT),
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
        options = [{"value": const.SENTINEL_EMPTY, "label": const.LABEL_NONE}]
        options += [
            {
                "value": kid_id,
                "label": kid.get(const.DATA_KID_NAME, const.SENTINEL_NONE_TEXT),
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
                "value": const.AWARD_ITEMS_KEY_POINTS,
                "label": const.AWARD_ITEMS_LABEL_POINTS,
            }
        )

        if is_cumulative:
            award_items_options.append(
                {
                    "value": (const.AWARD_ITEMS_KEY_POINTS_MULTIPLIER),
                    "label": (const.AWARD_ITEMS_LABEL_POINTS_MULTIPLIER),
                }
            )

        if rewards_dict:
            for reward_id, reward in rewards_dict.items():
                reward_name = reward.get(const.DATA_REWARD_NAME, reward_id)
                label = f"{const.AWARD_ITEMS_LABEL_REWARD} {reward_name}"
                award_items_options.append(
                    {
                        "value": f"{const.AWARD_ITEMS_PREFIX_REWARD}{reward_id}",
                        "label": label,
                    }
                )
        if bonuses_dict:
            for bonus_id, bonus in bonuses_dict.items():
                bonus_name = bonus.get(const.DATA_BONUS_NAME, bonus_id)
                label = f"{const.AWARD_ITEMS_LABEL_BONUS} {bonus_name}"
                award_items_options.append(
                    {
                        "value": f"{const.AWARD_ITEMS_PREFIX_BONUS}{bonus_id}",
                        "label": label,
                    }
                )
        if include_penalties:
            if penalties_dict:
                for penalty_id, penalty in penalties_dict.items():
                    label = f"{const.AWARD_ITEMS_LABEL_PENALTY} {penalty.get(const.DATA_PENALTY_NAME, penalty_id)}"
                    award_items_options.append(
                        {
                            "value": f"{const.AWARD_ITEMS_PREFIX_PENALTY}{penalty_id}",
                            "label": label,
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

        # For BADGE_TYPE_DAILY hide reset schedule fields
        # and force value in validation
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
                            vol.Coerce(int),  # Coerce to integer
                            vol.Range(min=0),  # Ensure >= 0
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

    const.LOGGER.debug("Build Badge Common Schema - Returning Schema Fields")
    return schema_fields


# ----------------------------------------------------------------------------------
# REWARDS SCHEMA (Pattern 1: Simple - Separate validate/build)
# ----------------------------------------------------------------------------------


def build_reward_schema(default=None):
    """Build a schema for rewards, keyed by internal_id in the dict."""
    default = default or {}
    reward_name_default = default.get(const.DATA_REWARD_NAME, const.SENTINEL_EMPTY)

    return vol.Schema(
        {
            vol.Required(
                const.CFOF_REWARDS_INPUT_NAME, default=reward_name_default
            ): str,
            vol.Optional(
                const.CFOF_REWARDS_INPUT_DESCRIPTION,
                default=default.get(
                    const.DATA_REWARD_DESCRIPTION, const.SENTINEL_EMPTY
                ),
            ): str,
            vol.Optional(
                const.CFOF_REWARDS_INPUT_LABELS,
                default=default.get(const.CFOF_REWARDS_INPUT_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Required(
                const.CFOF_REWARDS_INPUT_COST,
                default=default.get(
                    const.CFOF_REWARDS_INPUT_COST, const.DEFAULT_REWARD_COST
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=0.1,
                )
            ),
            vol.Optional(
                const.CFOF_REWARDS_INPUT_ICON,
                default=default.get(const.DATA_REWARD_ICON, const.SENTINEL_EMPTY),
            ): selector.IconSelector(),
        }
    )


def build_rewards_data(
    user_input: Dict[str, Any],
    existing_rewards: Dict[str, Any] = None,  # pylint: disable=unused-argument  # Reserved for API consistency with validate_rewards_inputs
) -> Dict[str, Any]:
    """Build reward data from user input.

    Converts form input (CFOF_* keys) to storage format (DATA_* keys).

    Args:
        user_input: Dictionary containing user inputs from the form.
        existing_rewards: Optional dictionary of existing rewards for duplicate checking.

    Returns:
        Dictionary with reward data in storage format, keyed by internal_id.
    """
    reward_name = user_input.get(const.CFOF_REWARDS_INPUT_NAME, "").strip()
    internal_id = user_input.get(const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4()))

    return {
        internal_id: {
            const.DATA_REWARD_NAME: reward_name,
            const.DATA_REWARD_COST: user_input[const.CFOF_REWARDS_INPUT_COST],
            const.DATA_REWARD_DESCRIPTION: user_input.get(
                const.CFOF_REWARDS_INPUT_DESCRIPTION, const.SENTINEL_EMPTY
            ),
            const.DATA_REWARD_LABELS: user_input.get(
                const.CFOF_REWARDS_INPUT_LABELS, []
            ),
            const.DATA_REWARD_ICON: user_input.get(
                const.CFOF_REWARDS_INPUT_ICON, const.DEFAULT_REWARD_ICON
            ),
            const.DATA_REWARD_INTERNAL_ID: internal_id,
        }
    }


def validate_rewards_inputs(
    user_input: Dict[str, Any], existing_rewards: Dict[str, Any] = None
) -> Dict[str, str]:
    """Validate reward configuration inputs.

    Args:
        user_input: Dictionary containing user inputs from the form.
        existing_rewards: Optional dictionary of existing rewards for duplicate checking.

    Returns:
        Dictionary of errors (empty if validation passes).
    """
    errors = {}

    reward_name = user_input.get(const.CFOF_REWARDS_INPUT_NAME, "").strip()

    # Validate name is not empty
    if not reward_name:
        errors[const.CFOP_ERROR_REWARD_NAME] = const.TRANS_KEY_CFOF_INVALID_REWARD_NAME
        return errors

    # Check for duplicate names
    if existing_rewards:
        if any(
            reward_data[const.DATA_REWARD_NAME] == reward_name
            for reward_data in existing_rewards.values()
        ):
            errors[const.CFOP_ERROR_REWARD_NAME] = const.TRANS_KEY_CFOF_DUPLICATE_REWARD

    return errors


# ----------------------------------------------------------------------------------
# BONUSES SCHEMA (Pattern 1: Simple - Separate validate/build)
# ----------------------------------------------------------------------------------


def build_bonus_schema(default=None):
    """Build a schema for bonuses, keyed by internal_id in the dict.

    Stores bonus_points as positive in the form, converted to negative internally.
    """
    default = default or {}
    bonus_name_default = default.get(const.DATA_BONUS_NAME, const.SENTINEL_EMPTY)

    # Display bonus points as positive for user input
    display_points = (
        abs(default.get(const.CFOF_BONUSES_INPUT_POINTS, const.DEFAULT_BONUS_POINTS))
        if default
        else const.DEFAULT_BONUS_POINTS
    )

    return vol.Schema(
        {
            vol.Required(
                const.CFOF_BONUSES_INPUT_NAME, default=bonus_name_default
            ): str,
            vol.Optional(
                const.CFOF_BONUSES_INPUT_DESCRIPTION,
                default=default.get(const.DATA_BONUS_DESCRIPTION, const.SENTINEL_EMPTY),
            ): str,
            vol.Optional(
                const.CFOF_BONUSES_INPUT_LABELS,
                default=default.get(const.CFOF_BONUSES_INPUT_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Required(
                const.CFOF_BONUSES_INPUT_POINTS, default=display_points
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=0.1,
                )
            ),
            vol.Optional(
                const.CFOF_BONUSES_INPUT_ICON,
                default=default.get(const.DATA_BONUS_ICON, const.SENTINEL_EMPTY),
            ): selector.IconSelector(),
        }
    )


def build_bonuses_data(
    user_input: Dict[str, Any],
    existing_bonuses: Dict[str, Any] = None,  # pylint: disable=unused-argument  # Reserved for API consistency with validate_bonuses_inputs
) -> Dict[str, Any]:
    """Build bonus data from user input.

    Converts form input (CFOF_* keys) to storage format (DATA_* keys).
    Ensures points are positive using abs().

    Args:
        user_input: Dictionary containing user inputs from the form.
        existing_bonuses: Optional dictionary of existing bonuses for duplicate checking.

    Returns:
        Dictionary with bonus data in storage format, keyed by internal_id.
    """
    bonus_name = user_input.get(const.CFOF_BONUSES_INPUT_NAME, "").strip()
    bonus_points = user_input[const.CFOF_BONUSES_INPUT_POINTS]
    internal_id = user_input.get(const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4()))

    return {
        internal_id: {
            const.DATA_BONUS_NAME: bonus_name,
            const.DATA_BONUS_DESCRIPTION: user_input.get(
                const.CFOF_BONUSES_INPUT_DESCRIPTION, const.SENTINEL_EMPTY
            ),
            const.DATA_BONUS_LABELS: user_input.get(
                const.CFOF_BONUSES_INPUT_LABELS, []
            ),
            const.DATA_BONUS_POINTS: abs(bonus_points),  # Ensure positive
            const.DATA_BONUS_ICON: user_input.get(
                const.CFOF_BONUSES_INPUT_ICON, const.DEFAULT_BONUS_ICON
            ),
            const.DATA_BONUS_INTERNAL_ID: internal_id,
        }
    }


def validate_bonuses_inputs(
    user_input: Dict[str, Any], existing_bonuses: Dict[str, Any] = None
) -> Dict[str, str]:
    """Validate bonus configuration inputs.

    Args:
        user_input: Dictionary containing user inputs from the form.
        existing_bonuses: Optional dictionary of existing bonuses for duplicate checking.

    Returns:
        Dictionary of errors (empty if validation passes).
    """
    errors = {}

    bonus_name = user_input.get(const.CFOF_BONUSES_INPUT_NAME, "").strip()

    # Validate name is not empty
    if not bonus_name:
        errors[const.CFOP_ERROR_BONUS_NAME] = const.TRANS_KEY_CFOF_INVALID_BONUS_NAME
        return errors

    # Check for duplicate names
    if existing_bonuses:
        if any(
            bonus_data[const.DATA_BONUS_NAME] == bonus_name
            for bonus_data in existing_bonuses.values()
        ):
            errors[const.CFOP_ERROR_BONUS_NAME] = const.TRANS_KEY_CFOF_DUPLICATE_BONUS

    return errors


# ----------------------------------------------------------------------------------
# PENALTIES SCHEMA (Pattern 1: Simple - Separate validate/build)
# ----------------------------------------------------------------------------------


def build_penalty_schema(default=None):
    """Build a schema for penalties, keyed by internal_id in the dict.

    Stores penalty_points as positive in the form, converted to negative internally.
    """
    default = default or {}
    penalty_name_default = default.get(const.DATA_PENALTY_NAME, const.SENTINEL_EMPTY)

    # Display penalty points as positive for user input
    display_points = (
        abs(
            default.get(const.CFOF_PENALTIES_INPUT_POINTS, const.DEFAULT_PENALTY_POINTS)
        )
        if default
        else const.DEFAULT_PENALTY_POINTS
    )

    return vol.Schema(
        {
            vol.Required(
                const.CFOF_PENALTIES_INPUT_NAME, default=penalty_name_default
            ): str,
            vol.Optional(
                const.CFOF_PENALTIES_INPUT_DESCRIPTION,
                default=default.get(
                    const.DATA_PENALTY_DESCRIPTION, const.SENTINEL_EMPTY
                ),
            ): str,
            vol.Optional(
                const.CFOF_PENALTIES_INPUT_LABELS,
                default=default.get(const.CFOF_PENALTIES_INPUT_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Required(
                const.CFOF_PENALTIES_INPUT_POINTS, default=display_points
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=0.1,
                )
            ),
            vol.Optional(
                const.CFOF_PENALTIES_INPUT_ICON,
                default=default.get(const.DATA_PENALTY_ICON, const.SENTINEL_EMPTY),
            ): selector.IconSelector(),
        }
    )


def build_penalties_data(
    user_input: Dict[str, Any],
    existing_penalties: Dict[str, Any] = None,  # pylint: disable=unused-argument  # Reserved for API consistency with validate_penalties_inputs
) -> Dict[str, Any]:
    """Build penalty data from user input.

    Converts form input (CFOF_* keys) to storage format (DATA_* keys).
    Ensures points are negative using -abs().

    Args:
        user_input: Dictionary containing user inputs from the form.
        existing_penalties: Optional dictionary of existing penalties for duplicate checking.

    Returns:
        Dictionary with penalty data in storage format, keyed by internal_id.
    """
    penalty_name = user_input.get(const.CFOF_PENALTIES_INPUT_NAME, "").strip()
    penalty_points = user_input[const.CFOF_PENALTIES_INPUT_POINTS]
    internal_id = user_input.get(const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4()))

    return {
        internal_id: {
            const.DATA_PENALTY_NAME: penalty_name,
            const.DATA_PENALTY_DESCRIPTION: user_input.get(
                const.CFOF_PENALTIES_INPUT_DESCRIPTION, const.SENTINEL_EMPTY
            ),
            const.DATA_PENALTY_LABELS: user_input.get(
                const.CFOF_PENALTIES_INPUT_LABELS, []
            ),
            const.DATA_PENALTY_POINTS: -abs(penalty_points),  # Ensure negative
            const.DATA_PENALTY_ICON: user_input.get(
                const.CFOF_PENALTIES_INPUT_ICON, const.DEFAULT_PENALTY_ICON
            ),
            const.DATA_PENALTY_INTERNAL_ID: internal_id,
        }
    }


def validate_penalties_inputs(
    user_input: Dict[str, Any], existing_penalties: Dict[str, Any] = None
) -> Dict[str, str]:
    """Validate penalty configuration inputs.

    Args:
        user_input: Dictionary containing user inputs from the form.
        existing_penalties: Optional dictionary of existing penalties for duplicate checking.

    Returns:
        Dictionary of errors (empty if validation passes).
    """
    errors = {}

    penalty_name = user_input.get(const.CFOF_PENALTIES_INPUT_NAME, "").strip()

    # Validate name is not empty
    if not penalty_name:
        errors[const.CFOP_ERROR_PENALTY_NAME] = (
            const.TRANS_KEY_CFOF_INVALID_PENALTY_NAME
        )
        return errors

    # Check for duplicate names
    if existing_penalties:
        if any(
            penalty_data[const.DATA_PENALTY_NAME] == penalty_name
            for penalty_data in existing_penalties.values()
        ):
            errors[const.CFOP_ERROR_PENALTY_NAME] = (
                const.TRANS_KEY_CFOF_DUPLICATE_PENALTY
            )

    return errors


def build_achievements_data(
    user_input: Dict[str, Any],
    existing_achievements: Dict[str, Any] = None,
    kids_name_to_id: Dict[str, str] = None,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Build achievement data from user input with integrated validation.

    This uses the complex pattern (returns tuple) because achievements have
    type-specific validation: streak type requires chore selection.

    Args:
        user_input: Dictionary containing user inputs from the form.
        existing_achievements: Optional dictionary of existing achievements for duplicate checking.
        kids_name_to_id: Optional mapping of kid names to internal IDs (for options flow).

    Returns:
        Tuple of (data_dict, errors_dict). Data dict is keyed by internal_id.
    """
    errors = {}
    achievement_name = user_input.get(const.CFOF_ACHIEVEMENTS_INPUT_NAME, "").strip()

    # Validate name is not empty
    if not achievement_name:
        errors[const.CFOP_ERROR_ACHIEVEMENT_NAME] = (
            const.TRANS_KEY_CFOF_INVALID_ACHIEVEMENT_NAME
        )
        return {}, errors

    # Check for duplicate names
    if existing_achievements:
        if any(
            achievement_data[const.DATA_ACHIEVEMENT_NAME] == achievement_name
            for achievement_data in existing_achievements.values()
        ):
            errors[const.CFOP_ERROR_ACHIEVEMENT_NAME] = (
                const.TRANS_KEY_CFOF_DUPLICATE_ACHIEVEMENT
            )
            return {}, errors

    # Type-specific validation: streak type requires chore selection
    # Streak achievements track consecutive completions of a specific chore
    # Other achievement types (one_time, recurring) don't need chore selection
    _type = user_input[const.CFOF_ACHIEVEMENTS_INPUT_TYPE]
    if _type == const.ACHIEVEMENT_TYPE_STREAK:
        chore_id = user_input.get(const.CFOF_ACHIEVEMENTS_INPUT_SELECTED_CHORE_ID)
        # Validate that a chore was actually selected (not None or placeholder)
        if not chore_id or chore_id == const.SENTINEL_NONE_TEXT:
            errors[const.CFOP_ERROR_SELECT_CHORE_ID] = (
                const.TRANS_KEY_CFOF_CHORE_MUST_BE_SELECTED
            )
            return {}, errors
        final_chore_id = chore_id
    else:
        # Non-streak types: discard any chore selection to prevent data inconsistency
        final_chore_id = const.SENTINEL_EMPTY

    # Get assigned kids (convert names to IDs if in options flow)
    # Different flow contexts use different kid identifiers:
    # - Config flow: uses internal_ids directly (kids created in same session)
    # - Options flow: uses kid names (must convert to internal_ids for storage)
    assigned_kids = user_input[const.CFOF_ACHIEVEMENTS_INPUT_ASSIGNED_KIDS]
    if kids_name_to_id:
        # Options flow: convert kid names to internal IDs using provided mapping
        # Fallback to name if mapping fails (defensive programming)
        assigned_kids_ids = [kids_name_to_id.get(name, name) for name in assigned_kids]
    else:
        # Config flow: already has internal IDs from entity creation in same session
        assigned_kids_ids = assigned_kids

    internal_id = user_input.get(const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4()))

    achievement_data = {
        internal_id: {
            const.DATA_ACHIEVEMENT_NAME: achievement_name,
            const.DATA_ACHIEVEMENT_DESCRIPTION: user_input.get(
                const.CFOF_ACHIEVEMENTS_INPUT_DESCRIPTION, const.SENTINEL_EMPTY
            ),
            const.DATA_ACHIEVEMENT_LABELS: user_input.get(
                const.CFOF_ACHIEVEMENTS_INPUT_LABELS, []
            ),
            const.DATA_ACHIEVEMENT_ICON: user_input.get(
                const.CFOF_ACHIEVEMENTS_INPUT_ICON,
                const.DEFAULT_ACHIEVEMENTS_ICON,
            ),
            const.DATA_ACHIEVEMENT_ASSIGNED_KIDS: assigned_kids_ids,
            const.DATA_ACHIEVEMENT_TYPE: _type,
            const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID: final_chore_id,
            const.DATA_ACHIEVEMENT_CRITERIA: user_input.get(
                const.CFOF_ACHIEVEMENTS_INPUT_CRITERIA, const.SENTINEL_EMPTY
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
    }

    return achievement_data, errors


def build_challenges_data(
    user_input: dict,
    kids_data: dict,
    existing_challenges: dict | None = None,
    current_id: str | None = None,
) -> Tuple[dict | None, dict]:
    """Build challenge data dict from user input with integrated validation.

    Returns: (data_dict, errors_dict) tuple
    - If validation passes: (data_dict, {})
    - If validation fails: (None, {"base": "error_key"})

    This uses the COMPLEX pattern (integrated validation) because challenges
    have date validation that requires checking relationships between fields.
    """
    errors = {}

    # Validate required fields
    if not user_input.get(const.CFOF_CHALLENGES_INPUT_NAME, "").strip():
        return None, {"base": const.TRANS_KEY_CFOF_CHALLENGE_NAME_REQUIRED}

    challenge_name = user_input[const.CFOF_CHALLENGES_INPUT_NAME].strip()

    # Check for duplicate names (exclude current challenge when editing)
    if existing_challenges:
        for chal_id, chal_data in existing_challenges.items():
            if chal_id != current_id:  # Skip the current challenge when editing
                if (
                    chal_data.get(const.DATA_CHALLENGE_NAME, "").lower()
                    == challenge_name.lower()
                ):
                    return None, {"base": const.TRANS_KEY_CFOF_CHALLENGE_NAME_DUPLICATE}

    # Validate dates
    start_date_str = user_input.get(const.CFOF_CHALLENGES_INPUT_START_DATE)
    end_date_str = user_input.get(const.CFOF_CHALLENGES_INPUT_END_DATE)

    if not start_date_str or not end_date_str:
        return None, {"base": const.TRANS_KEY_CFOF_CHALLENGE_DATES_REQUIRED}

    try:
        # Normalize dates to UTC-aware datetime objects for comparison
        start_dt = kh.normalize_datetime_input(
            start_date_str,
            default_tzinfo=const.DEFAULT_TIME_ZONE,
            return_type=const.HELPER_RETURN_DATETIME_UTC,
        )
        end_dt = kh.normalize_datetime_input(
            end_date_str,
            default_tzinfo=const.DEFAULT_TIME_ZONE,
            return_type=const.HELPER_RETURN_DATETIME_UTC,
        )

        # Type guard: ensure both are datetime.datetime before operations
        # (narrow from datetime | date | str | None)
        if not isinstance(start_dt, datetime.datetime):
            return None, {"base": const.TRANS_KEY_CFOF_CHALLENGE_INVALID_DATE}
        if not isinstance(end_dt, datetime.datetime):
            return None, {"base": const.TRANS_KEY_CFOF_CHALLENGE_INVALID_DATE}

        # Validate end date is after start date (chronological order required)
        # Now safe: both are definitely datetime.datetime
        if end_dt <= start_dt:
            return None, {"base": const.TRANS_KEY_CFOF_CHALLENGE_END_BEFORE_START}

        # Convert to ISO strings for storage
        # Now safe: both are definitely datetime.datetime with .isoformat() method
        start_date = start_dt.isoformat()
        end_date = end_dt.isoformat()

    except (ValueError, TypeError) as ex:
        const.LOGGER.warning("Challenge date parsing error: %s", ex)
        return None, {"base": const.TRANS_KEY_CFOF_CHALLENGE_INVALID_DATE}

    # Validate target value
    try:
        target_value = float(
            user_input.get(const.CFOF_CHALLENGES_INPUT_TARGET_VALUE, 0)
        )
        if target_value <= 0:
            return None, {"base": const.TRANS_KEY_CFOF_CHALLENGE_TARGET_INVALID}
    except (ValueError, TypeError):
        return None, {"base": const.TRANS_KEY_CFOF_CHALLENGE_TARGET_INVALID}

    # Validate reward points
    try:
        reward_points = float(
            user_input.get(const.CFOF_CHALLENGES_INPUT_REWARD_POINTS, 0)
        )
        if reward_points < 0:
            return None, {"base": const.TRANS_KEY_CFOF_CHALLENGE_POINTS_NEGATIVE}
    except (ValueError, TypeError):
        return None, {"base": const.TRANS_KEY_CFOF_CHALLENGE_POINTS_INVALID}

    # Convert assigned kids from names to IDs
    # UI uses kid names (user-friendly), but storage uses internal_ids (rename-safe)
    assigned_kids_names = user_input.get(const.CFOF_CHALLENGES_INPUT_ASSIGNED_KIDS, [])
    # Normalize to list (selector might return single value or list)
    if not isinstance(assigned_kids_names, list):
        assigned_kids_names = [assigned_kids_names] if assigned_kids_names else []

    assigned_kids_ids = []
    for kid_name in assigned_kids_names:
        # Look up internal_id by matching kid name (case-sensitive)
        kid_id = next(
            (
                k_id
                for k_id, k_data in kids_data.items()
                if k_data.get(const.DATA_KID_NAME) == kid_name
            ),
            None,
        )
        if kid_id:
            assigned_kids_ids.append(kid_id)

    # Get or generate internal_id
    internal_id = current_id or str(uuid.uuid4())

    # Get challenge type and associated chore
    _type = user_input.get(
        const.CFOF_CHALLENGES_INPUT_TYPE, const.CHALLENGE_TYPE_DAILY_MIN
    )

    # Build the challenge data dict
    challenge_data = {
        internal_id: {
            const.DATA_CHALLENGE_NAME: challenge_name,
            const.DATA_CHALLENGE_DESCRIPTION: user_input.get(
                const.CFOF_CHALLENGES_INPUT_DESCRIPTION, const.SENTINEL_EMPTY
            ).strip(),
            const.DATA_CHALLENGE_LABELS: user_input.get(
                const.CFOF_CHALLENGES_INPUT_LABELS, []
            ),
            const.DATA_CHALLENGE_ICON: user_input.get(
                const.CFOF_CHALLENGES_INPUT_ICON,
                const.DEFAULT_CHALLENGES_ICON,
            ),
            const.DATA_CHALLENGE_ASSIGNED_KIDS: assigned_kids_ids,
            const.DATA_CHALLENGE_TYPE: _type,
            const.DATA_CHALLENGE_SELECTED_CHORE_ID: user_input.get(
                const.CFOF_CHALLENGES_INPUT_SELECTED_CHORE_ID, const.SENTINEL_EMPTY
            ),
            const.DATA_CHALLENGE_CRITERIA: user_input.get(
                const.CFOF_CHALLENGES_INPUT_CRITERIA, const.SENTINEL_EMPTY
            ).strip(),
            const.DATA_CHALLENGE_TARGET_VALUE: target_value,
            const.DATA_CHALLENGE_REWARD_POINTS: reward_points,
            const.DATA_CHALLENGE_START_DATE: start_date,
            const.DATA_CHALLENGE_END_DATE: end_date,
            const.DATA_CHALLENGE_INTERNAL_ID: internal_id,
            const.DATA_CHALLENGE_PROGRESS: {},
        }
    }

    return challenge_data, errors


# ----------------------------------------------------------------------------------
# ACHIEVEMENTS SCHEMA (Pattern 2: Complex - Integrated validation with tuple return)
# ----------------------------------------------------------------------------------


def build_achievement_schema(kids_dict, chores_dict, default=None):
    """Build a schema for achievements, keyed by internal_id."""
    default = default or {}
    achievement_name_default = default.get(
        const.DATA_ACHIEVEMENT_NAME, const.SENTINEL_EMPTY
    )

    kid_options = [
        {"value": kid_id, "label": kid_name} for kid_name, kid_id in kids_dict.items()
    ]

    chore_options = [{"value": const.SENTINEL_EMPTY, "label": const.LABEL_NONE}]
    for chore_id, chore_data in chores_dict.items():
        chore_name = chore_data.get(const.DATA_CHORE_NAME, f"Chore {chore_id[:6]}")
        chore_options.append({"value": chore_id, "label": chore_name})

    default_selected_chore = default.get(
        const.CONF_ACHIEVEMENT_SELECTED_CHORE_ID_LEGACY, const.SENTINEL_EMPTY
    )
    if not default_selected_chore or default_selected_chore not in [
        option["value"] for option in chore_options
    ]:
        pass

    default_criteria = default.get(
        const.CFOF_ACHIEVEMENTS_INPUT_CRITERIA, const.SENTINEL_EMPTY
    )
    default_assigned_kids = default.get(const.CFOF_ACHIEVEMENTS_INPUT_ASSIGNED_KIDS, [])
    if not isinstance(default_assigned_kids, list):
        default_assigned_kids = [default_assigned_kids]

    return vol.Schema(
        {
            vol.Required(
                const.CFOF_ACHIEVEMENTS_INPUT_NAME, default=achievement_name_default
            ): str,
            vol.Optional(
                const.CFOF_ACHIEVEMENTS_INPUT_DESCRIPTION,
                default=default.get(
                    const.DATA_ACHIEVEMENT_DESCRIPTION, const.SENTINEL_EMPTY
                ),
            ): str,
            vol.Optional(
                const.CFOF_ACHIEVEMENTS_INPUT_LABELS,
                default=default.get(const.CFOF_ACHIEVEMENTS_INPUT_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Optional(
                const.CFOF_ACHIEVEMENTS_INPUT_ICON,
                default=default.get(const.DATA_ACHIEVEMENT_ICON, const.SENTINEL_EMPTY),
            ): selector.IconSelector(),
            vol.Required(
                const.CFOF_ACHIEVEMENTS_INPUT_ASSIGNED_KIDS,
                default=default_assigned_kids,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=kid_options,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_ASSIGNED_KIDS,
                    multiple=True,
                )
            ),
            vol.Required(
                const.CFOF_ACHIEVEMENTS_INPUT_TYPE,
                default=default.get(
                    const.CFOF_ACHIEVEMENTS_INPUT_TYPE, const.ACHIEVEMENT_TYPE_STREAK
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.ACHIEVEMENT_TYPE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            # If type == "chore_streak", let the user choose the chore to track:
            vol.Optional(
                const.CFOF_ACHIEVEMENTS_INPUT_SELECTED_CHORE_ID,
                default=default_selected_chore,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=chore_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False,
                )
            ),
            # For non-streak achievements the user can type criteria freely:
            vol.Optional(
                const.CFOF_ACHIEVEMENTS_INPUT_CRITERIA, default=default_criteria
            ): str,
            vol.Required(
                const.CFOF_ACHIEVEMENTS_INPUT_TARGET_VALUE,
                default=default.get(
                    const.CFOF_ACHIEVEMENTS_INPUT_TARGET_VALUE,
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
                const.CFOF_ACHIEVEMENTS_INPUT_REWARD_POINTS,
                default=default.get(
                    const.CFOF_ACHIEVEMENTS_INPUT_REWARD_POINTS,
                    const.DEFAULT_ACHIEVEMENT_REWARD_POINTS,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=0.1,
                )
            ),
        }
    )


# ----------------------------------------------------------------------------------
# CHALLENGES SCHEMA (Pattern 2: Complex - Integrated validation with tuple return)
# ----------------------------------------------------------------------------------


def build_challenge_schema(kids_dict, chores_dict, default=None):
    """Build a schema for challenges, keyed by internal_id."""
    default = default or {}
    challenge_name_default = default.get(
        const.DATA_CHALLENGE_NAME, const.SENTINEL_EMPTY
    )

    kid_options = [
        {"value": kid_id, "label": kid_name} for kid_name, kid_id in kids_dict.items()
    ]

    chore_options = [{"value": const.SENTINEL_EMPTY, "label": const.LABEL_NONE}]
    for chore_id, chore_data in chores_dict.items():
        chore_name = chore_data.get(const.DATA_CHORE_NAME, f"Chore {chore_id[:6]}")
        chore_options.append({"value": chore_id, "label": chore_name})

    default_selected_chore = default.get(
        const.CONF_CHALLENGE_SELECTED_CHORE_ID_LEGACY, const.SENTINEL_EMPTY
    )
    available_values = [option["value"] for option in chore_options]
    if default_selected_chore not in available_values:
        default_selected_chore = ""

    default_criteria = default.get(
        const.CFOF_CHALLENGES_INPUT_CRITERIA, const.SENTINEL_EMPTY
    )
    default_assigned_kids = default.get(const.CFOF_CHALLENGES_INPUT_ASSIGNED_KIDS, [])
    if not isinstance(default_assigned_kids, list):
        default_assigned_kids = [default_assigned_kids]

    return vol.Schema(
        {
            vol.Required(
                const.CFOF_CHALLENGES_INPUT_NAME, default=challenge_name_default
            ): str,
            vol.Optional(
                const.CFOF_CHALLENGES_INPUT_DESCRIPTION,
                default=default.get(
                    const.DATA_CHALLENGE_DESCRIPTION, const.SENTINEL_EMPTY
                ),
            ): str,
            vol.Optional(
                const.CFOF_CHALLENGES_INPUT_LABELS,
                default=default.get(const.CFOF_CHALLENGES_INPUT_LABELS, []),
            ): selector.LabelSelector(selector.LabelSelectorConfig(multiple=True)),
            vol.Optional(
                const.CFOF_CHALLENGES_INPUT_ICON,
                default=default.get(const.DATA_CHALLENGE_ICON, const.SENTINEL_EMPTY),
            ): selector.IconSelector(),
            vol.Required(
                const.CFOF_CHALLENGES_INPUT_ASSIGNED_KIDS, default=default_assigned_kids
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=kid_options,
                    translation_key=const.TRANS_KEY_FLOW_HELPERS_ASSIGNED_KIDS,
                    multiple=True,
                )
            ),
            vol.Required(
                const.CFOF_CHALLENGES_INPUT_TYPE,
                default=default.get(
                    const.CFOF_CHALLENGES_INPUT_TYPE, const.CHALLENGE_TYPE_DAILY_MIN
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.CHALLENGE_TYPE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            # If type == "chore_streak", let the user choose the chore to track:
            vol.Optional(
                const.CFOF_CHALLENGES_INPUT_SELECTED_CHORE_ID,
                default=default_selected_chore,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=chore_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False,
                )
            ),
            # For non-streak achievements the user can type criteria freely:
            vol.Optional(
                const.CFOF_CHALLENGES_INPUT_CRITERIA, default=default_criteria
            ): str,
            vol.Required(
                const.CFOF_CHALLENGES_INPUT_TARGET_VALUE,
                default=default.get(
                    const.CFOF_CHALLENGES_INPUT_TARGET_VALUE,
                    const.DEFAULT_CHALLENGE_TARGET,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    step=0.1,
                )
            ),
            vol.Required(
                const.CFOF_CHALLENGES_INPUT_REWARD_POINTS,
                default=default.get(
                    const.CFOF_CHALLENGES_INPUT_REWARD_POINTS,
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
                const.CFOF_CHALLENGES_INPUT_START_DATE,
                default=default.get(const.CFOF_CHALLENGES_INPUT_START_DATE),
            ): selector.DateTimeSelector(),
            vol.Required(
                const.CFOF_CHALLENGES_INPUT_END_DATE,
                default=default.get(const.CFOF_CHALLENGES_INPUT_END_DATE),
            ): selector.DateTimeSelector(),
        }
    )


# ----------------------------------------------------------------------------------
# GENERAL OPTIONS SCHEMA
# ----------------------------------------------------------------------------------


def build_general_options_schema(default: Optional[dict] = None) -> vol.Schema:
    """Build schema for general options including points adjust values and update interval."""
    default = default or {}
    current_values = default.get(const.CFOF_SYSTEM_INPUT_POINTS_ADJUST_VALUES)
    if current_values and isinstance(current_values, list):
        default_points_str = "|".join(str(v) for v in current_values)
    else:
        default_points_str = "|".join(
            str(v) for v in const.DEFAULT_POINTS_ADJUST_VALUES
        )

    default_interval = default.get(
        const.CFOF_SYSTEM_INPUT_UPDATE_INTERVAL, const.DEFAULT_UPDATE_INTERVAL
    )
    default_calendar_period = default.get(
        const.CFOF_SYSTEM_INPUT_CALENDAR_SHOW_PERIOD, const.DEFAULT_CALENDAR_SHOW_PERIOD
    )

    # Consolidated retention periods (pipe-separated: Daily|Weekly|Monthly|Yearly)
    default_retention_daily = default.get(
        const.CFOF_SYSTEM_INPUT_RETENTION_DAILY, const.DEFAULT_RETENTION_DAILY
    )
    default_retention_weekly = default.get(
        const.CFOF_SYSTEM_INPUT_RETENTION_WEEKLY, const.DEFAULT_RETENTION_WEEKLY
    )
    default_retention_monthly = default.get(
        const.CFOF_SYSTEM_INPUT_RETENTION_MONTHLY, const.DEFAULT_RETENTION_MONTHLY
    )
    default_retention_yearly = default.get(
        const.CFOF_SYSTEM_INPUT_RETENTION_YEARLY, const.DEFAULT_RETENTION_YEARLY
    )
    default_retention_periods = format_retention_periods(
        default_retention_daily,
        default_retention_weekly,
        default_retention_monthly,
        default_retention_yearly,
    )

    default_show_legacy_entities = default.get(
        const.CONF_SHOW_LEGACY_ENTITIES, const.DEFAULT_SHOW_LEGACY_ENTITIES
    )

    return vol.Schema(
        {
            vol.Required(
                const.CFOF_SYSTEM_INPUT_POINTS_ADJUST_VALUES, default=default_points_str
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=False,
                )
            ),
            vol.Required(
                const.CFOF_SYSTEM_INPUT_UPDATE_INTERVAL, default=default_interval
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=1,
                    step=1,
                )
            ),
            vol.Required(
                const.CFOF_SYSTEM_INPUT_CALENDAR_SHOW_PERIOD,
                default=default_calendar_period,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=1,
                    step=1,
                )
            ),
            vol.Required(
                const.CFOF_SYSTEM_INPUT_RETENTION_PERIODS,
                default=default_retention_periods,
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=False,
                )
            ),
            vol.Required(
                const.CFOF_SYSTEM_INPUT_SHOW_LEGACY_ENTITIES,
                default=default_show_legacy_entities,
            ): selector.BooleanSelector(),
            vol.Required(
                const.CFOF_SYSTEM_INPUT_BACKUPS_MAX_RETAINED,
                default=default.get(
                    const.CONF_BACKUPS_MAX_RETAINED,
                    const.DEFAULT_BACKUPS_MAX_RETAINED,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=const.MIN_BACKUPS_MAX_RETAINED,
                    max=const.MAX_BACKUPS_MAX_RETAINED,
                    step=1,
                )
            ),
            vol.Optional(
                const.CFOF_BACKUP_ACTION_SELECTION,
                default=const.OPTIONS_FLOW_BACKUP_ACTION_SELECT,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        const.OPTIONS_FLOW_BACKUP_ACTION_SELECT,
                        const.OPTIONS_FLOW_BACKUP_ACTION_CREATE,
                        const.OPTIONS_FLOW_BACKUP_ACTION_DELETE,
                        const.OPTIONS_FLOW_BACKUP_ACTION_RESTORE,
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=const.TRANS_KEY_CFOF_BACKUP_ACTIONS_MENU,
                )
            ),
        }
    )


# ----------------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------------


def format_retention_periods(daily: int, weekly: int, monthly: int, yearly: int) -> str:
    """Format retention periods as pipe-separated string for display.

    Args:
        daily: Daily retention count
        weekly: Weekly retention count
        monthly: Monthly retention count
        yearly: Yearly retention count

    Returns:
        Pipe-separated string (e.g., "7|4|12|3")
    """
    return f"{daily}|{weekly}|{monthly}|{yearly}"


def parse_retention_periods(retention_str: str) -> tuple[int, int, int, int]:
    """Parse pipe-separated retention periods string.

    Args:
        retention_str: Pipe-separated string (e.g., "7|4|12|3")

    Returns:
        Tuple of (daily, weekly, monthly, yearly) as integers

    Raises:
        ValueError: If format is invalid or values are not positive integers
    """
    try:
        parts = [p.strip() for p in retention_str.split("|")]
        if len(parts) != 4:
            raise ValueError(
                f"Expected 4 values (Daily|Weekly|Monthly|Yearly), got {len(parts)}"
            )

        daily, weekly, monthly, yearly = [int(p) for p in parts]

        if not all(v > 0 for v in [daily, weekly, monthly, yearly]):
            raise ValueError("All retention values must be positive integers")

        return daily, weekly, monthly, yearly
    except (ValueError, AttributeError) as ex:
        raise ValueError(
            f"Invalid retention format. Expected 'Daily|Weekly|Monthly|Yearly' "
            f"(e.g., '7|4|12|3'): {ex}"
        ) from ex


# Penalty points are stored as negative internally, but displayed as positive in the form.
def process_penalty_form_input(user_input: dict) -> dict:
    """Ensure penalty points are negative internally."""
    data = dict(user_input)
    data[const.DATA_PENALTY_POINTS] = -abs(data[const.CFOF_PENALTIES_INPUT_POINTS])
    return data


# Get notify services from HA
def _get_notify_services(hass: HomeAssistant) -> list[dict[str, str]]:
    """Return a list of all notify.* services as value/label dictionaries for selector options."""
    services_list = []
    all_services = hass.services.async_services()
    if const.NOTIFY_DOMAIN in all_services:
        for service_name in all_services[const.NOTIFY_DOMAIN].keys():
            fullname = f"{const.NOTIFY_DOMAIN}.{service_name}"
            services_list.append({"value": fullname, "label": fullname})
    return services_list


# ----------------------------------------------------------------------------------
# BACKUP HELPERS
# ----------------------------------------------------------------------------------


async def create_timestamped_backup(
    hass: HomeAssistant, storage_manager, tag: str
) -> str | None:
    """Create a timestamped backup file with specified tag.

    Args:
        hass: Home Assistant instance
        storage_manager: Storage manager instance
        tag: Backup tag (e.g., 'recovery', 'removal', 'reset', 'pre-migration', 'manual')

    Returns:
        Filename of created backup (e.g., 'kidschores_data_2025-12-18_14-30-22_removal')
        or None if backup creation failed.

    File naming format: kidschores_data_YYYY-MM-DD_HH-MM-SS_<tag>
    Example: kidschores_data_2025-12-18_14-30-22_removal
    """
    try:
        # Get current UTC timestamp in filesystem-safe ISO 8601 format
        timestamp = dt_util.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"kidschores_data_{timestamp}_{tag}"

        # Get storage file path
        storage_path = storage_manager.get_storage_path()

        # Check if source file exists (non-blocking)
        if not await hass.async_add_executor_job(os.path.exists, storage_path):
            const.LOGGER.warning("Storage file does not exist, cannot create backup")
            return None

        # Ensure .storage directory exists (non-blocking)
        storage_dir = hass.config.path(".storage")
        await hass.async_add_executor_job(
            lambda: os.makedirs(storage_dir, exist_ok=True)
        )

        # Copy file to backup location (non-blocking)
        backup_path = hass.config.path(".storage", filename)
        await hass.async_add_executor_job(shutil.copy2, storage_path, backup_path)

        const.LOGGER.debug("Created backup: %s", filename)
        return filename

    except (OSError, ValueError) as ex:
        const.LOGGER.error("Failed to create backup with tag %s: %s", tag, ex)
        return None


async def cleanup_old_backups(
    hass: HomeAssistant,
    storage_manager,
    max_backups: int,  # pylint: disable=unused-argument
) -> None:
    """Delete old backups beyond max_backups limit per tag.

    Args:
        hass: Home Assistant instance
        storage_manager: Storage manager instance (unused but kept for API consistency)
        max_backups: Maximum number of backups to retain per tag (0 = no limit)

    Behavior:
        - Keeps newest N backups per tag (e.g., 5 manual, 5 recovery, etc.)
        - Retention applies equally to ALL backup types
        - If max_backups is 0, no cleanup is performed (unlimited retention)
        - Logs warnings for deletion failures but continues processing
    """
    # Ensure max_backups is an integer (defensive programming for config entry options)
    max_backups = int(max_backups)

    if max_backups <= 0:
        const.LOGGER.debug("Backup cleanup disabled (max_backups=%s)", max_backups)
        return

    try:
        # Discover all backups
        backups_list = await discover_backups(hass, storage_manager)
        const.LOGGER.debug("Backup cleanup: found %d total backups", len(backups_list))

        # Group backups by tag
        backups_by_tag: dict[str, list[dict]] = {}
        for backup in backups_list:
            tag = backup.get("tag", "unknown")  # Handle backups without tag
            if tag not in backups_by_tag:
                backups_by_tag[tag] = []
            backups_by_tag[tag].append(backup)

        const.LOGGER.debug(
            "Backup cleanup: tags found: %s", list(backups_by_tag.keys())
        )

        # Process each tag - retention applies to ALL tags equally
        for tag, tag_backups in backups_by_tag.items():
            const.LOGGER.debug(
                "Processing %d backups for tag '%s'", len(tag_backups), tag
            )

            # Sort by timestamp (newest first) - use defensive programming for missing timestamp
            tag_backups.sort(
                key=lambda b: b.get("timestamp", "1970-01-01T00:00:00.000000+00:00"),
                reverse=True,
            )

            # Delete oldest backups beyond max_backups (applies to all tags: recovery, reset, etc.)
            backups_to_delete = tag_backups[max_backups:]
            const.LOGGER.debug(
                "Tag '%s': keeping %d newest, deleting %d oldest (max_backups=%d)",
                tag,
                min(len(tag_backups), max_backups),
                len(backups_to_delete),
                max_backups,
            )

            for backup in backups_to_delete:
                try:
                    backup_path = hass.config.path(".storage", backup["filename"])
                    await hass.async_add_executor_job(os.remove, backup_path)
                    const.LOGGER.info(
                        "Cleaned up old %s backup: %s", tag, backup["filename"]
                    )
                except OSError as ex:
                    const.LOGGER.warning(
                        "Failed to delete backup %s: %s", backup["filename"], ex
                    )

    except (OSError, ValueError) as ex:
        const.LOGGER.error("Failed during backup cleanup: %s", ex)


async def discover_backups(hass: HomeAssistant, storage_manager) -> list[dict]:  # pylint: disable=unused-argument
    """Scan .storage/ directory for backup files and return metadata list.

    Args:
        hass: Home Assistant instance
        storage_manager: Storage manager instance (unused but kept for API consistency)

    Returns:
        List of backup metadata dictionaries with keys:
        - filename: str (e.g., 'kidschores_data_2025-12-18_14-30-22_removal')
        - tag: str (e.g., 'recovery', 'removal', 'reset', 'pre-migration', 'manual')
        - timestamp: datetime (parsed from filename)
        - age_hours: float (hours since backup creation)
        - size_bytes: int (file size in bytes)

    File naming format: kidschores_data_YYYY-MM-DD_HH-MM-SS_<tag>
    Invalid filenames are skipped with debug log.
    """
    backups_list = []
    storage_dir = hass.config.path(".storage")

    try:
        # Check if storage directory exists (non-blocking)
        if not await hass.async_add_executor_job(os.path.exists, storage_dir):
            const.LOGGER.warning("Storage directory does not exist: %s", storage_dir)
            return backups_list

        # Get directory listing (non-blocking)
        filenames = await hass.async_add_executor_job(os.listdir, storage_dir)
        for filename in filenames:
            # Match format: kidschores_data_YYYY-MM-DD_HH-MM-SS_<tag>
            if not filename.startswith("kidschores_data_"):
                continue

            # Skip active file (no timestamp/tag suffix)
            if filename == "kidschores_data":
                continue

            # Parse filename: kidschores_data_YYYY-MM-DD_HH-MM-SS_<tag>
            try:
                # Remove 'kidschores_data_' prefix
                suffix = filename[16:]  # len("kidschores_data_") = 16

                # Split into timestamp and tag parts
                # Format: YYYY-MM-DD_HH-MM-SS_<tag>
                parts = suffix.rsplit("_", 1)  # Split from right to get tag
                if len(parts) != 2:
                    const.LOGGER.debug("Skipping invalid backup filename: %s", filename)
                    continue

                timestamp_str, tag = parts

                # Parse timestamp (format: YYYY-MM-DD_HH-MM-SS)
                # Split date and time parts, convert time hyphens to colons
                # YYYY-MM-DD_HH-MM-SS -> YYYY-MM-DD HH:MM:SS
                date_part, time_part = timestamp_str.split("_", 1)
                time_part_clean = time_part.replace("-", ":")
                timestamp_str_clean = f"{date_part} {time_part_clean}"
                timestamp = datetime.datetime.strptime(
                    timestamp_str_clean, "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=datetime.timezone.utc)

                # Calculate age
                age_hours = (dt_util.utcnow() - timestamp).total_seconds() / 3600

                # Get file size (non-blocking)
                file_path = os.path.join(storage_dir, filename)
                size_bytes = await hass.async_add_executor_job(
                    os.path.getsize, file_path
                )

                backups_list.append(
                    {
                        "filename": filename,
                        "tag": tag,
                        "timestamp": timestamp,
                        "age_hours": age_hours,
                        "size_bytes": size_bytes,
                    }
                )

            except (ValueError, OSError) as ex:
                const.LOGGER.debug("Skipping invalid backup file %s: %s", filename, ex)
                continue

    except OSError as ex:
        const.LOGGER.error("Failed to scan storage directory: %s", ex)

    # Sort by timestamp (newest first)
    backups_list.sort(key=lambda b: b["timestamp"], reverse=True)
    return backups_list


def format_backup_age(age_hours: float) -> str:
    """Convert hours to human-readable age string.

    Args:
        age_hours: Age in hours (can be fractional)

    Returns:
        Human-readable string like:
        - "2 minutes ago"
        - "1 hour ago"
        - "5 hours ago"
        - "2 days ago"
        - "3 weeks ago"

    Precision:
        - < 1 hour: minutes
        - < 24 hours: hours
        - < 7 days: days
        - >= 7 days: weeks
    """
    if age_hours < 1:
        minutes = max(1, int(age_hours * 60))  # Always show at least 1 minute
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

    if age_hours < 24:
        hours = int(age_hours)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    if age_hours < 168:  # 7 days
        days = int(age_hours / 24)
        return f"{days} day{'s' if days != 1 else ''} ago"

    weeks = int(age_hours / 168)
    return f"{weeks} week{'s' if weeks != 1 else ''} ago"


def validate_backup_json(json_str: str) -> bool:
    """Validate JSON structure of backup data.

    Args:
        json_str: JSON string to validate

    Returns:
        True if JSON is valid and contains expected top-level keys.
        False if JSON is malformed or missing required structure.

    Supported formats:
        1. Diagnostic format (KC 4.0+ diagnostic exports):
            {
                "home_assistant": {...},
                "custom_components": {...},
                "integration_manifest": {...},
                "data": {
                    "kids": dict,
                    "parents": dict,
                    ...
                }
            }

        2. Modern format (schema_version 42):
            {
                "schema_version": 42,
                "kids": dict,
                "parents": dict,
                ...
            }

        3. Legacy format (no schema_version - KC 3.0/3.1/early 4.0beta):
            {
                "kids": dict,
                "parents": dict,
                ...
            }

        4. Store format (version 1 - KC 3.0/3.1/4.0beta1):
            {
                "version": 1,
                "minor_version": 1,
                "key": "kidschores_data",
                "data": {
                    "kids": dict,
                    "parents": dict,
                    ...
                }
            }

    Minimum requirements:
        - Valid JSON syntax
        - Top-level object (dict)
        - If Store format, version must be 1 (only version supported)
        - Contains at least one entity type key (kids, parents, chores, rewards)
    """
    try:
        data = json.loads(json_str)

        # Must be a dictionary
        if not isinstance(data, dict):
            const.LOGGER.debug("Backup JSON is not a dictionary")
            return False

        # Handle diagnostic format (KC 4.0+ diagnostic exports)
        if "home_assistant" in data and "data" in data:
            const.LOGGER.debug("Detected diagnostic export format")
            # Diagnostic format wraps storage data in "data" key with metadata
            if not isinstance(data["data"], dict):
                const.LOGGER.debug("Diagnostic format 'data' is not a dictionary")
                return False
            data = data["data"]  # Unwrap for entity validation

        # Handle Store format (KC 3.0/3.1/4.0beta1) - version 1 only
        elif "version" in data:
            store_version = data.get("version")
            if store_version != 1:
                const.LOGGER.warning(
                    "Unsupported Store version %s - only version 1 (KC 3.x/4.0beta) is supported",
                    store_version,
                )
                return False
            # Store format wraps data in "data" key
            if "data" not in data:
                const.LOGGER.debug("Store format missing 'data' wrapper")
                return False
            data = data["data"]  # Unwrap for entity validation

        # schema_version is optional - old backups won't have it and will be migrated

        # Must have at least one entity type
        entity_keys = {
            "kids",
            "parents",
            "chores",
            "rewards",
            "bonuses",
            "penalties",
            "achievements",
            "challenges",
            "badges",
        }
        if not any(key in data for key in entity_keys):
            const.LOGGER.debug("Backup JSON missing all entity type keys")
            return False

        return True

    except json.JSONDecodeError as ex:
        const.LOGGER.debug("Invalid JSON in backup: %s", ex)
        return False
    except (TypeError, ValueError) as ex:
        const.LOGGER.debug("Unexpected error validating backup JSON: %s", ex)
        return False


# ----------------------------------------------------------------------------------
# SYSTEM SETTINGS CONSOLIDATION (Phase 3c)
# ----------------------------------------------------------------------------------


def build_all_system_settings_schema(
    default_points_label: str | None = None,
    default_points_icon: str | None = None,
    default_update_interval: int | None = None,
    default_calendar_show_period: int | None = None,
    default_retention_daily: int | None = None,
    default_retention_weekly: int | None = None,
    default_retention_monthly: int | None = None,
    default_retention_yearly: int | None = None,
    default_points_adjust_values: list[int] | None = None,
) -> vol.Schema:
    """Build form schema for all 9 system settings.

    Combines points schema, update interval, calendar period, retention periods,
    and points adjust values into a single comprehensive schema.

    Args:
        default_points_label: Points label (e.g., "Points", "Stars")
        default_points_icon: MDI icon for points
        default_update_interval: Coordinator update interval in minutes
        default_calendar_show_period: Calendar lookback period in days
        default_retention_daily: Days retention for daily history
        default_retention_weekly: Weeks retention for weekly history
        default_retention_monthly: Months retention for monthly history
        default_retention_yearly: Years retention for yearly history
        default_points_adjust_values: List of point adjustment values

    Returns:
        vol.Schema with all 9 system settings fields
    """
    # Use defaults if not provided
    defaults = {
        "points_label": default_points_label or const.DEFAULT_POINTS_LABEL,
        "points_icon": default_points_icon or const.DEFAULT_POINTS_ICON,
        "update_interval": default_update_interval or const.DEFAULT_UPDATE_INTERVAL,
        "calendar_show_period": default_calendar_show_period
        or const.DEFAULT_CALENDAR_SHOW_PERIOD,
        "retention_daily": default_retention_daily or const.DEFAULT_RETENTION_DAILY,
        "retention_weekly": default_retention_weekly or const.DEFAULT_RETENTION_WEEKLY,
        "retention_monthly": default_retention_monthly
        or const.DEFAULT_RETENTION_MONTHLY,
        "retention_yearly": default_retention_yearly or const.DEFAULT_RETENTION_YEARLY,
        "points_adjust_values": default_points_adjust_values
        or const.DEFAULT_POINTS_ADJUST_VALUES,
    }

    # Build combined schema from points + other settings
    points_fields = build_points_schema(
        default_label=defaults["points_label"],
        default_icon=defaults["points_icon"],
    )

    # Add update interval field
    update_interval_fields = {
        vol.Required(
            const.CFOF_SYSTEM_INPUT_UPDATE_INTERVAL, default=defaults["update_interval"]
        ): cv.positive_int,
    }

    # Add calendar period field
    calendar_fields = {
        vol.Required(
            const.CFOF_SYSTEM_INPUT_CALENDAR_SHOW_PERIOD,
            default=defaults["calendar_show_period"],
        ): cv.positive_int,
    }

    # Add retention period fields
    retention_fields = {
        vol.Required(
            const.CFOF_SYSTEM_INPUT_RETENTION_DAILY, default=defaults["retention_daily"]
        ): cv.positive_int,
        vol.Required(
            const.CFOF_SYSTEM_INPUT_RETENTION_WEEKLY,
            default=defaults["retention_weekly"],
        ): cv.positive_int,
        vol.Required(
            const.CFOF_SYSTEM_INPUT_RETENTION_MONTHLY,
            default=defaults["retention_monthly"],
        ): cv.positive_int,
        vol.Required(
            const.CFOF_SYSTEM_INPUT_RETENTION_YEARLY,
            default=defaults["retention_yearly"],
        ): cv.positive_int,
    }

    # Add points adjust values field
    adjust_values_fields = {
        vol.Required(
            const.CFOF_SYSTEM_INPUT_POINTS_ADJUST_VALUES,
            default=defaults["points_adjust_values"],
        ): cv.ensure_list,
    }

    # Combine all fields
    all_fields = {
        **points_fields.schema,
        **update_interval_fields,
        **calendar_fields,
        **retention_fields,
        **adjust_values_fields,
    }

    return vol.Schema(all_fields)


def validate_all_system_settings(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate all 9 system settings.

    Validates points label/icon, update interval, calendar period,
    retention periods, and points adjust values.

    Args:
        user_input: Form input from user

    Returns:
        dict: Errors dictionary (empty if valid)
    """
    errors: dict[str, str] = {}

    # Validate points using existing function
    points_errors = validate_points_inputs(user_input)
    if points_errors:
        errors.update(points_errors)

    # Validate update interval
    update_interval = user_input.get(const.CFOF_SYSTEM_INPUT_UPDATE_INTERVAL)
    if update_interval is not None and not isinstance(update_interval, int):
        try:
            int(update_interval)
        except (ValueError, TypeError):
            errors[const.CFOP_ERROR_UPDATE_INTERVAL] = (
                const.TRANS_KEY_CFOF_INVALID_UPDATE_INTERVAL
            )

    # Validate calendar show period
    calendar_period = user_input.get(const.CFOF_SYSTEM_INPUT_CALENDAR_SHOW_PERIOD)
    if calendar_period is not None and not isinstance(calendar_period, int):
        try:
            int(calendar_period)
        except (ValueError, TypeError):
            errors[const.CFOP_ERROR_CALENDAR_SHOW_PERIOD] = (
                const.TRANS_KEY_CFOF_INVALID_CALENDAR_SHOW_PERIOD
            )

    # Validate retention periods (all positive ints)
    for field, error_key in [
        (const.CFOF_SYSTEM_INPUT_RETENTION_DAILY, const.CFOP_ERROR_RETENTION_DAILY),
        (const.CFOF_SYSTEM_INPUT_RETENTION_WEEKLY, const.CFOP_ERROR_RETENTION_WEEKLY),
        (const.CFOF_SYSTEM_INPUT_RETENTION_MONTHLY, const.CFOP_ERROR_RETENTION_MONTHLY),
        (const.CFOF_SYSTEM_INPUT_RETENTION_YEARLY, const.CFOP_ERROR_RETENTION_YEARLY),
    ]:
        value = user_input.get(field)
        if value is not None and not isinstance(value, int):
            try:
                int(value)
            except (ValueError, TypeError):
                errors[error_key] = const.TRANS_KEY_CFOF_INVALID_RETENTION_PERIOD

    # Validate points adjust values is list
    adjust_values = user_input.get(const.CFOF_SYSTEM_INPUT_POINTS_ADJUST_VALUES)
    if adjust_values is not None and not isinstance(adjust_values, list):
        errors[const.CFOP_ERROR_POINTS_ADJUST_VALUES] = (
            const.TRANS_KEY_CFOF_INVALID_POINTS_ADJUST_VALUES
        )

    return errors


def build_all_system_settings_data(user_input: dict[str, Any]) -> dict[str, Any]:
    """Build 9-key system settings options dictionary from user input.

    Extracts all 9 system setting values from user input and returns
    a dictionary ready for config_entry.options.

    Args:
        user_input: Form input from user (assumed valid)

    Returns:
        dict: 9-key dictionary with system settings
    """
    # Build points settings using existing function
    points_data = build_points_data(user_input)

    # Extract other settings
    settings_data = {
        const.CONF_UPDATE_INTERVAL: user_input.get(
            const.CFOF_SYSTEM_INPUT_UPDATE_INTERVAL, const.DEFAULT_UPDATE_INTERVAL
        ),
        const.CONF_CALENDAR_SHOW_PERIOD: user_input.get(
            const.CFOF_SYSTEM_INPUT_CALENDAR_SHOW_PERIOD,
            const.DEFAULT_CALENDAR_SHOW_PERIOD,
        ),
        const.CONF_RETENTION_DAILY: user_input.get(
            const.CFOF_SYSTEM_INPUT_RETENTION_DAILY, const.DEFAULT_RETENTION_DAILY
        ),
        const.CONF_RETENTION_WEEKLY: user_input.get(
            const.CFOF_SYSTEM_INPUT_RETENTION_WEEKLY, const.DEFAULT_RETENTION_WEEKLY
        ),
        const.CONF_RETENTION_MONTHLY: user_input.get(
            const.CFOF_SYSTEM_INPUT_RETENTION_MONTHLY, const.DEFAULT_RETENTION_MONTHLY
        ),
        const.CONF_RETENTION_YEARLY: user_input.get(
            const.CFOF_SYSTEM_INPUT_RETENTION_YEARLY, const.DEFAULT_RETENTION_YEARLY
        ),
        const.CONF_POINTS_ADJUST_VALUES: user_input.get(
            const.CFOF_SYSTEM_INPUT_POINTS_ADJUST_VALUES,
            const.DEFAULT_POINTS_ADJUST_VALUES,
        ),
    }

    # Combine points + other settings into single dict
    return {**points_data, **settings_data}
