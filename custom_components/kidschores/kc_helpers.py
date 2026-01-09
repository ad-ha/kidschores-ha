# File: kc_helpers.py
"""KidsChores helper functions and shared logic.

## Organization Guide (Sections Below)

This file is organized into logical sections for easy navigation:

1. **Get Coordinator** (Line 26)
   - Retrieves KidsChores coordinator from hass.data

2. **Authorization for General Actions** (Line 47)
   - Global authorization checks for coordinator-wide operations

3. **Authorization for Kid-Specific Actions** (Line 85)
   - Kid-level authorization checks (parent/kid role validation)

4. **Parse Points Adjustment Values** (Line 140)
   - Button entity configuration parsing for point adjustments

5. **Helper Functions** (Line 160)
   - Basic ID/name lookups without error raising (safe for optional checks)

6. **Data Structure Builders** (Line 470) 🏗️
   - build_default_chore_data() - Single source of truth for chore field initialization

7. **Entity Lookup Helpers with Error Raising** (Line 560) 🔍
   - ID/name lookups that raise HomeAssistantError (for services/actions)

8. **KidsChores Progress & Completion Helpers** (Line 520) 🧮
   - Badge progress, chore completion, streak calculations

9. **Date & Time Helpers** (Line 690) 🕒
   - DateTime parsing, UTC conversion, interval calculations, scheduling

10. **Dashboard Translation Loaders** (Line 1500)
    - Helper translations for dashboard UI rendering

11. **Device Info Helpers** (Line 1630)
    - Device registry and device info construction

"""

# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false, reportCallIssue=false, reportReturnType=false, reportOperatorIssue=false

from __future__ import annotations

import json
import os
from calendar import monthrange
from datetime import date, datetime, timedelta, tzinfo
from typing import TYPE_CHECKING, Any, Iterable, Optional, Union

import homeassistant.util.dt as dt_util
from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.label_registry import async_get as async_get_label_registry

from . import const

if TYPE_CHECKING:
    from .coordinator import KidsChoresDataCoordinator  # Used for type checking only


# 📍 -------- Get Coordinator --------
def _get_kidschores_coordinator(
    hass: HomeAssistant,
) -> Optional[KidsChoresDataCoordinator]:
    """Retrieve KidsChores coordinator from hass.data."""

    domain_entries = hass.data.get(const.DOMAIN, {})
    if not domain_entries:
        return None

    entry_id = next(iter(domain_entries), None)
    if not entry_id:
        return None

    data = domain_entries.get(entry_id)
    if not data or const.COORDINATOR not in data:
        return None

    return data[const.COORDINATOR]


# 🔐 -------- Authorization for General Actions --------
async def is_user_authorized_for_global_action(
    hass: HomeAssistant,
    user_id: str,
    action: str,
) -> bool:
    """Check if the user is allowed to do a global action (penalty, reward, points adjust) that doesn't require a specific kid_id.

    Authorization rules:
      - Admin users => authorized
      - Registered KidsChores parents => authorized
      - Everyone else => not authorized
    """
    if not user_id:
        return False  # no user context => not authorized

    user: Optional[User] = await hass.auth.async_get_user(user_id)
    if not user:
        const.LOGGER.warning("WARNING: %s: Invalid user ID '%s'", action, user_id)
        return False

    if user.is_admin:
        return True

    # Allow non-admin users if they are registered as a parent in KidsChores.
    coordinator = _get_kidschores_coordinator(hass)
    if coordinator:
        for parent in coordinator.parents_data.values():
            if parent.get(const.DATA_PARENT_HA_USER_ID) == user.id:
                return True

    const.LOGGER.warning(
        "WARNING: %s: Non-admin user '%s' is not authorized in this logic",
        action,
        user.name,
    )
    return False


# 👶 -------- Authorization for Kid-Specific Actions --------
async def is_user_authorized_for_kid(
    hass: HomeAssistant,
    user_id: str,
    kid_id: str,
) -> bool:
    """Check if user is authorized to manage chores/rewards/etc. for the given kid.

    By default:
      - Admin => authorized
      - If kid_info['ha_user_id'] == user.id => authorized
      - Otherwise => not authorized
    """
    if not user_id:
        return False

    user: Optional[User] = await hass.auth.async_get_user(user_id)
    if not user:
        const.LOGGER.warning("WARNING: Authorization: Invalid user ID '%s'", user_id)
        return False

    # Admin => automatically allowed
    if user.is_admin:
        return True

    # Allow non-admin users if they are registered as a parent in KidsChores.
    coordinator: Optional[KidsChoresDataCoordinator] = _get_kidschores_coordinator(hass)
    if coordinator:
        for parent in coordinator.parents_data.values():
            if parent.get(const.DATA_PARENT_HA_USER_ID) == user.id:
                return True

    if not coordinator:
        const.LOGGER.warning("WARNING: Authorization: KidsChores coordinator not found")
        return False

    kid_info = coordinator.kids_data.get(kid_id)
    if not kid_info:
        const.LOGGER.warning(
            "WARNING: Authorization: Kid ID '%s' not found in coordinator data", kid_id
        )
        return False

    linked_ha_id = kid_info.get(const.DATA_KID_HA_USER_ID)
    if linked_ha_id and linked_ha_id == user.id:
        return True

    const.LOGGER.warning(
        "WARNING: Authorization: Non-admin user '%s' attempted to manage Kid ID '%s' but is not linked",
        user.name,
        kid_info.get(const.DATA_KID_NAME),
    )
    return False


# 📊 ----------- Parse Points Adjustment Values -----------
def parse_points_adjust_values(points_str: str) -> list[float]:
    """Parse a multiline string into a list of float values."""

    values = []
    for part in points_str.split("|"):
        part = part.strip()
        if not part:
            continue

        try:
            value = float(part.replace(",", "."))
            values.append(value)
        except ValueError:
            const.LOGGER.error(
                "ERROR: Invalid number '%s' in points adjust values", part
            )
    return values


# 🔍 -------- Basic Entity Lookup Helpers --------
def get_first_kidschores_entry(hass: HomeAssistant) -> Optional[str]:
    """Retrieve the first KidsChores config entry ID."""
    domain_entries = hass.data.get(const.DOMAIN)
    if not domain_entries:
        return None
    return next(iter(domain_entries.keys()), None)


# ────────────────────────────────────────────────────────────────
# 🔍 Generic Entity Lookup Helper
# Central implementation for looking up entity IDs by name across all
# entity types. Eliminates ~80 lines of duplicate code by providing
# a single parametrizable function for all entity lookups.
# ────────────────────────────────────────────────────────────────


def get_entity_id_by_name(
    coordinator: KidsChoresDataCoordinator, entity_type: str, entity_name: str
) -> Optional[str]:
    """Generic entity ID lookup by name across all entity types.

    Replaces duplicate get_*_id_by_name() functions with a single parametrizable
    implementation that maps entity types to their data dictionaries and name keys.

    Args:
        coordinator: The KidsChores data coordinator.
        entity_type: The type of entity ("kid", "chore", "reward", "penalty",
            "badge", "bonus", "parent", "achievement", "challenge").
        entity_name: The name of the entity to look up.

    Returns:
        The internal ID (UUID) of the entity, or None if not found.

    Raises:
        ValueError: If entity_type is not recognized.
    """
    # Map entity type to (data dict, name key constant)
    entity_map = {
        const.ENTITY_TYPE_KID: (coordinator.kids_data, const.DATA_KID_NAME),
        const.ENTITY_TYPE_CHORE: (coordinator.chores_data, const.DATA_CHORE_NAME),
        const.ENTITY_TYPE_REWARD: (coordinator.rewards_data, const.DATA_REWARD_NAME),
        const.ENTITY_TYPE_PENALTY: (
            coordinator.penalties_data,
            const.DATA_PENALTY_NAME,
        ),
        const.ENTITY_TYPE_BADGE: (coordinator.badges_data, const.DATA_BADGE_NAME),
        const.ENTITY_TYPE_BONUS: (coordinator.bonuses_data, const.DATA_BONUS_NAME),
        const.ENTITY_TYPE_PARENT: (coordinator.parents_data, const.DATA_PARENT_NAME),
        const.ENTITY_TYPE_ACHIEVEMENT: (
            coordinator.achievements_data,
            const.DATA_ACHIEVEMENT_NAME,
        ),
        const.ENTITY_TYPE_CHALLENGE: (
            coordinator.challenges_data,
            const.DATA_CHALLENGE_NAME,
        ),
    }

    if entity_type not in entity_map:
        raise ValueError(
            f"Unknown entity_type: {entity_type}. "
            f"Valid options: {', '.join(entity_map.keys())}"
        )

    data_dict, name_key = entity_map[entity_type]
    for entity_id, entity_info in data_dict.items():
        if entity_info.get(name_key) == entity_name:
            return entity_id
    return None


# Thin wrapper functions for backward compatibility and convenience
def get_kid_id_by_name(
    coordinator: KidsChoresDataCoordinator, kid_name: str
) -> Optional[str]:
    """Retrieve the kid_id for a given kid_name.

    Args:
        coordinator: The KidsChores data coordinator.
        kid_name: The name of the kid to look up.

    Returns:
        The internal ID (UUID) of the kid, or None if not found.
    """
    return get_entity_id_by_name(coordinator, const.ENTITY_TYPE_KID, kid_name)


def get_kid_name_by_id(
    coordinator: KidsChoresDataCoordinator, kid_id: str
) -> Optional[str]:
    """Retrieve the kid_name for a given kid_id.

    Args:
        coordinator: The KidsChores data coordinator.
        kid_id: The internal ID (UUID) of the kid to look up.

    Returns:
        The name of the kid, or None if not found.
    """
    kid_info = coordinator.kids_data.get(kid_id)
    if kid_info:
        return kid_info.get(const.DATA_KID_NAME)
    return None


def get_chore_id_by_name(
    coordinator: KidsChoresDataCoordinator, chore_name: str
) -> Optional[str]:
    """Retrieve the chore_id for a given chore_name.

    Args:
        coordinator: The KidsChores data coordinator.
        chore_name: The name of the chore to look up.

    Returns:
        The internal ID (UUID) of the chore, or None if not found.
    """
    return get_entity_id_by_name(coordinator, const.ENTITY_TYPE_CHORE, chore_name)


def get_reward_id_by_name(
    coordinator: KidsChoresDataCoordinator, reward_name: str
) -> Optional[str]:
    """Retrieve the reward_id for a given reward_name.

    Args:
        coordinator: The KidsChores data coordinator.
        reward_name: The name of the reward to look up.

    Returns:
        The internal ID (UUID) of the reward, or None if not found.
    """
    return get_entity_id_by_name(coordinator, const.ENTITY_TYPE_REWARD, reward_name)


def get_penalty_id_by_name(
    coordinator: KidsChoresDataCoordinator, penalty_name: str
) -> Optional[str]:
    """Retrieve the penalty_id for a given penalty_name.

    Args:
        coordinator: The KidsChores data coordinator.
        penalty_name: The name of the penalty to look up.

    Returns:
        The internal ID (UUID) of the penalty, or None if not found.
    """
    return get_entity_id_by_name(coordinator, const.ENTITY_TYPE_PENALTY, penalty_name)


def get_badge_id_by_name(
    coordinator: KidsChoresDataCoordinator, badge_name: str
) -> Optional[str]:
    """Retrieve the badge_id for a given badge_name.

    Args:
        coordinator: The KidsChores data coordinator.
        badge_name: The name of the badge to look up.

    Returns:
        The internal ID (UUID) of the badge, or None if not found.
    """
    return get_entity_id_by_name(coordinator, const.ENTITY_TYPE_BADGE, badge_name)


def get_bonus_id_by_name(
    coordinator: KidsChoresDataCoordinator, bonus_name: str
) -> Optional[str]:
    """Retrieve the bonus_id for a given bonus_name.

    Args:
        coordinator: The KidsChores data coordinator.
        bonus_name: The name of the bonus to look up.

    Returns:
        The internal ID (UUID) of the bonus, or None if not found.
    """
    return get_entity_id_by_name(coordinator, const.ENTITY_TYPE_BONUS, bonus_name)


def get_parent_id_by_name(
    coordinator: KidsChoresDataCoordinator, parent_name: str
) -> Optional[str]:
    """Retrieve the parent_id for a given parent_name.

    Args:
        coordinator: The KidsChores data coordinator.
        parent_name: The name of the parent to look up.

    Returns:
        The internal ID (UUID) of the parent, or None if not found.
    """
    return get_entity_id_by_name(coordinator, const.ENTITY_TYPE_PARENT, parent_name)


def get_achievement_id_by_name(
    coordinator: KidsChoresDataCoordinator, achievement_name: str
) -> Optional[str]:
    """Retrieve the achievement_id for a given achievement_name.

    Args:
        coordinator: The KidsChores data coordinator.
        achievement_name: The name of the achievement to look up.

    Returns:
        The internal ID (UUID) of the achievement, or None if not found.
    """
    return get_entity_id_by_name(
        coordinator, const.ENTITY_TYPE_ACHIEVEMENT, achievement_name
    )


def get_challenge_id_by_name(
    coordinator: KidsChoresDataCoordinator, challenge_name: str
) -> Optional[str]:
    """Retrieve the challenge_id for a given challenge_name.

    Args:
        coordinator: The KidsChores data coordinator.
        challenge_name: The name of the challenge to look up.

    Returns:
        The internal ID (UUID) of the challenge, or None if not found.
    """
    return get_entity_id_by_name(
        coordinator, const.ENTITY_TYPE_CHALLENGE, challenge_name
    )


def get_friendly_label(hass: HomeAssistant, label_name: str) -> str:
    """Retrieve the friendly name for a given label_name (synchronous cached version).

    Args:
        hass: The Home Assistant instance.
        label_name: The label name to look up.

    Returns:
        The friendly name from the label registry, or the original label_name if not found.

    Note:
        This is a synchronous wrapper. For fresh lookups, use async_get_friendly_label().
    """
    try:
        registry = async_get_label_registry(hass)
        label_entry = registry.async_get_label(label_name)
        return label_entry.name if label_entry else label_name
    except Exception:  # pylint: disable=broad-except
        # Fallback if label registry unavailable
        return label_name


async def async_get_friendly_label(hass: HomeAssistant, label_name: str) -> str:
    """Asynchronously retrieve the friendly name for a given label_name.

    Args:
        hass: The Home Assistant instance.
        label_name: The label name to look up.

    Returns:
        The friendly name from the label registry, or the original label_name if not found.

    Raises:
        No exceptions raised - returns original label_name as fallback on any error.
    """
    try:
        registry = async_get_label_registry(hass)
        label_entry = registry.async_get_label(label_name)
        return label_entry.name if label_entry else label_name
    except Exception:  # pylint: disable=broad-except
        # Fallback if label registry unavailable
        return label_name


# ────────────────────────────────────────────────────────────────
# �️ -------- Data Structure Builders --------
# These helpers build complete data structures with all required fields.
# SINGLE SOURCE OF TRUTH for entity field initialization.
# Used by both config flow (build_chores_data) and coordinator (_create_chore).
# ────────────────────────────────────────────────────────────────


def build_default_chore_data(
    chore_id: str, chore_data: dict[str, Any]
) -> dict[str, Any]:
    """Build a complete chore data structure with all fields initialized.

    This is the SINGLE SOURCE OF TRUTH for chore field initialization.
    Used by both config flow's build_chores_data() and coordinator's _create_chore().

    Args:
        chore_id: The internal UUID for the chore.
        chore_data: Partial chore data dict (from user input or existing data).

    Returns:
        Complete chore data dict with all fields set to appropriate defaults.
    """
    # Extract assigned_kids - these should already be UUIDs from flow helpers
    assigned_kids_ids = chore_data.get(const.DATA_CHORE_ASSIGNED_KIDS, [])

    # Handle custom interval fields - only set if frequency is CUSTOM
    is_custom_frequency = (
        chore_data.get(const.DATA_CHORE_RECURRING_FREQUENCY) == const.FREQUENCY_CUSTOM
    )

    return {
        # Core identification
        const.DATA_CHORE_INTERNAL_ID: chore_id,
        const.DATA_CHORE_NAME: chore_data.get(
            const.DATA_CHORE_NAME, const.SENTINEL_EMPTY
        ),
        # State - always starts as PENDING
        const.DATA_CHORE_STATE: chore_data.get(
            const.DATA_CHORE_STATE, const.CHORE_STATE_PENDING
        ),
        # Points and configuration
        const.DATA_CHORE_DEFAULT_POINTS: chore_data.get(
            const.DATA_CHORE_DEFAULT_POINTS, const.DEFAULT_POINTS
        ),
        const.DATA_CHORE_APPROVAL_RESET_TYPE: chore_data.get(
            const.DATA_CHORE_APPROVAL_RESET_TYPE,
            const.DEFAULT_APPROVAL_RESET_TYPE,
        ),
        const.DATA_CHORE_OVERDUE_HANDLING_TYPE: chore_data.get(
            const.DATA_CHORE_OVERDUE_HANDLING_TYPE,
            const.DEFAULT_OVERDUE_HANDLING_TYPE,
        ),
        const.DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION: chore_data.get(
            const.DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION,
            const.DEFAULT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
        ),
        # Description and display
        const.DATA_CHORE_DESCRIPTION: chore_data.get(
            const.DATA_CHORE_DESCRIPTION, const.SENTINEL_EMPTY
        ),
        const.DATA_CHORE_LABELS: chore_data.get(const.DATA_CHORE_LABELS, []),
        const.DATA_CHORE_ICON: chore_data.get(
            const.DATA_CHORE_ICON, const.DEFAULT_ICON
        ),
        # Assignment
        const.DATA_CHORE_ASSIGNED_KIDS: assigned_kids_ids,
        # Scheduling - recurring frequency and custom interval
        const.DATA_CHORE_RECURRING_FREQUENCY: chore_data.get(
            const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
        ),
        const.DATA_CHORE_CUSTOM_INTERVAL: (
            chore_data.get(const.DATA_CHORE_CUSTOM_INTERVAL)
            if is_custom_frequency
            else None
        ),
        const.DATA_CHORE_CUSTOM_INTERVAL_UNIT: (
            chore_data.get(const.DATA_CHORE_CUSTOM_INTERVAL_UNIT)
            if is_custom_frequency
            else None
        ),
        # Due dates
        const.DATA_CHORE_DUE_DATE: chore_data.get(const.DATA_CHORE_DUE_DATE),
        const.DATA_CHORE_PER_KID_DUE_DATES: chore_data.get(
            const.DATA_CHORE_PER_KID_DUE_DATES, {}
        ),
        const.DATA_CHORE_APPLICABLE_DAYS: chore_data.get(
            const.DATA_CHORE_APPLICABLE_DAYS, []
        ),
        # Runtime tracking fields (initially None/empty)
        const.DATA_CHORE_LAST_COMPLETED: chore_data.get(
            const.DATA_CHORE_LAST_COMPLETED
        ),
        const.DATA_CHORE_LAST_CLAIMED: chore_data.get(const.DATA_CHORE_LAST_CLAIMED),
        const.DATA_CHORE_APPROVAL_PERIOD_START: chore_data.get(
            const.DATA_CHORE_APPROVAL_PERIOD_START
        ),
        # Notifications
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
        # Calendar and features
        const.DATA_CHORE_SHOW_ON_CALENDAR: chore_data.get(
            const.DATA_CHORE_SHOW_ON_CALENDAR, const.DEFAULT_CHORE_SHOW_ON_CALENDAR
        ),
        const.DATA_CHORE_AUTO_APPROVE: chore_data.get(
            const.DATA_CHORE_AUTO_APPROVE, const.DEFAULT_CHORE_AUTO_APPROVE
        ),
        # Completion criteria (SHARED vs INDEPENDENT)
        const.DATA_CHORE_COMPLETION_CRITERIA: chore_data.get(
            const.DATA_CHORE_COMPLETION_CRITERIA,
            const.COMPLETION_CRITERIA_INDEPENDENT,
        ),
    }


# ────────────────────────────────────────────────────────────────
# �🎯 -------- Entity Lookup Helpers with Error Raising (for Services) --------
# These helpers wrap the lookup functions above and raise HomeAssistantError
# when entities are not found. This centralizes the error handling pattern
# used throughout services.py, eliminating 40+ duplicate lookup blocks.
# ────────────────────────────────────────────────────────────────


def get_entity_id_or_raise(
    coordinator: KidsChoresDataCoordinator, entity_type: str, entity_name: str
) -> str:
    """Get entity ID by name or raise HomeAssistantError if not found.

    Generic version of all *_or_raise() functions. Centralizes error
    handling pattern for entity lookups across services.

    Args:
        coordinator: The KidsChores data coordinator.
        entity_type: The type of entity ("kid", "chore", "reward", "penalty",
            "badge", "bonus", "parent", "achievement", "challenge").
        entity_name: The name of the entity to look up.

    Returns:
        The internal ID (UUID) of the entity.

    Raises:
        HomeAssistantError: If the entity is not found.
    """
    entity_id = get_entity_id_by_name(coordinator, entity_type, entity_name)
    if not entity_id:
        raise HomeAssistantError(
            f"{entity_type.capitalize()} '{entity_name}' not found"
        )
    return entity_id


# Thin wrapper functions for backward compatibility
def get_kid_id_or_raise(coordinator: KidsChoresDataCoordinator, kid_name: str) -> str:
    """Get kid ID by name or raise HomeAssistantError if not found."""
    return get_entity_id_or_raise(coordinator, const.ENTITY_TYPE_KID, kid_name)


def get_chore_id_or_raise(
    coordinator: KidsChoresDataCoordinator, chore_name: str
) -> str:
    """Get chore ID by name or raise HomeAssistantError if not found.

    Args:
        coordinator: The KidsChores data coordinator.
        chore_name: The name of the chore to look up.

    Returns:
        The internal ID (UUID) of the chore.

    Raises:
        HomeAssistantError: If the chore is not found.
    """
    return get_entity_id_or_raise(coordinator, const.ENTITY_TYPE_CHORE, chore_name)


def get_reward_id_or_raise(
    coordinator: KidsChoresDataCoordinator, reward_name: str
) -> str:
    """Get reward ID by name or raise HomeAssistantError if not found.

    Args:
        coordinator: The KidsChores data coordinator.
        reward_name: The name of the reward to look up.

    Returns:
        The internal ID (UUID) of the reward.

    Raises:
        HomeAssistantError: If the reward is not found.
    """
    return get_entity_id_or_raise(coordinator, const.ENTITY_TYPE_REWARD, reward_name)


def get_penalty_id_or_raise(
    coordinator: KidsChoresDataCoordinator, penalty_name: str
) -> str:
    """Get penalty ID by name or raise HomeAssistantError if not found.

    Args:
        coordinator: The KidsChores data coordinator.
        penalty_name: The name of the penalty to look up.

    Returns:
        The internal ID (UUID) of the penalty.

    Raises:
        HomeAssistantError: If the penalty is not found.
    """
    return get_entity_id_or_raise(coordinator, const.ENTITY_TYPE_PENALTY, penalty_name)


def get_badge_id_or_raise(
    coordinator: KidsChoresDataCoordinator, badge_name: str
) -> str:
    """Get badge ID by name or raise HomeAssistantError if not found.

    Args:
        coordinator: The KidsChores data coordinator.
        badge_name: The name of the badge to look up.

    Returns:
        The internal ID (UUID) of the badge.

    Raises:
        HomeAssistantError: If the badge is not found.
    """
    return get_entity_id_or_raise(coordinator, const.ENTITY_TYPE_BADGE, badge_name)


def get_bonus_id_or_raise(
    coordinator: KidsChoresDataCoordinator, bonus_name: str
) -> str:
    """Get bonus ID by name or raise HomeAssistantError if not found.

    Args:
        coordinator: The KidsChores data coordinator.
        bonus_name: The name of the bonus to look up.

    Returns:
        The internal ID (UUID) of the bonus.

    Raises:
        HomeAssistantError: If the bonus is not found.
    """
    return get_entity_id_or_raise(coordinator, const.ENTITY_TYPE_BONUS, bonus_name)


def get_parent_id_or_raise(
    coordinator: KidsChoresDataCoordinator, parent_name: str
) -> str:
    """Get parent ID by name or raise HomeAssistantError if not found.

    Args:
        coordinator: The KidsChores data coordinator.
        parent_name: The name of the parent to look up.

    Returns:
        The internal ID (UUID) of the parent.

    Raises:
        HomeAssistantError: If the parent is not found.
    """
    return get_entity_id_or_raise(coordinator, const.ENTITY_TYPE_PARENT, parent_name)


def get_achievement_id_or_raise(
    coordinator: KidsChoresDataCoordinator, achievement_name: str
) -> str:
    """Get achievement ID by name or raise HomeAssistantError if not found.

    Args:
        coordinator: The KidsChores data coordinator.
        achievement_name: The name of the achievement to look up.

    Returns:
        The internal ID (UUID) of the achievement.

    Raises:
        HomeAssistantError: If the achievement is not found.
    """
    return get_entity_id_or_raise(
        coordinator, const.ENTITY_TYPE_ACHIEVEMENT, achievement_name
    )


def get_challenge_id_or_raise(
    coordinator: KidsChoresDataCoordinator, challenge_name: str
) -> str:
    """Get challenge ID by name or raise HomeAssistantError if not found.

    Args:
        coordinator: The KidsChores data coordinator.
        challenge_name: The name of the challenge to look up.

    Returns:
        The internal ID (UUID) of the challenge.

    Raises:
        HomeAssistantError: If the challenge is not found.
    """
    return get_entity_id_or_raise(
        coordinator, const.ENTITY_TYPE_CHALLENGE, challenge_name
    )


# ────────────────────────────────────────────────────────────────
# 🧮 -------- KidsChores Progress & Completion Helpers --------
# These helpers provide reusable logic for evaluating daily chore progress,
# points, streaks, and completion criteria for a kid. They are used by
# badges, achievements, challenges, and other features that need to
# calculate or check progress for a set of chores.
# - get_today_chore_and_point_progress: Returns today's points, count, and streaks.
# - get_today_chore_completion_progress: Returns if completion criteria are met, and actual counts.
# ────────────────────────────────────────────────────────────────


def get_today_chore_and_point_progress(
    kid_info: dict,
    tracked_chores: list,
) -> tuple[int, int, int, int, dict, dict, dict]:
    """
    Calculate today's points from all sources, points from chores, total chore completions,
    and longest streak for the given kid and tracked chores.
    If tracked_chores is empty, use all chores for the kid.

    Returns:
        (
            total_points_all_sources: int,
            total_points_chores: int,
            total_chore_count: int,
            longest_chore_streak: int,
            points_per_chore: {chore_id: points_today, ...},
            count_per_chore: {chore_id: count_today, ...},
            streak_per_chore: {chore_id: streak_length, ...}
        )
    """
    today_iso = get_today_local_iso()
    if not tracked_chores:
        tracked_chores = list(kid_info.get(const.DATA_KID_CHORE_DATA, {}).keys())

    total_points_chores = 0
    total_chore_count = 0
    longest_chore_streak = 0
    points_per_chore = {}
    count_per_chore = {}
    streak_per_chore = {}

    for chore_id in tracked_chores:
        kid_chore_data = kid_info.get(const.DATA_KID_CHORE_DATA, {}).get(chore_id, {})
        periods_data = kid_chore_data.get(const.DATA_KID_CHORE_DATA_PERIODS, {})
        daily_stats = periods_data.get(const.DATA_KID_CHORE_DATA_PERIODS_DAILY, {})

        # Points today (from this chore)
        points_today = daily_stats.get(today_iso, {}).get(
            const.DATA_KID_CHORE_DATA_PERIOD_POINTS, 0
        )
        if points_today > 0:
            points_per_chore[chore_id] = points_today
            total_points_chores += points_today

        # Chore count today
        count_today = daily_stats.get(today_iso, {}).get(
            const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, 0
        )
        if count_today > 0:
            count_per_chore[chore_id] = count_today
            total_chore_count += count_today

        # Streak: now stored in daily period data
        streak_today = daily_stats.get(today_iso, {}).get(
            const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, 0
        )
        streak_per_chore[chore_id] = streak_today
        if streak_today > longest_chore_streak:
            longest_chore_streak = streak_today

    # Points from all sources (if tracked in kid point_stats)
    point_stats = kid_info.get(const.DATA_KID_POINT_STATS, {})
    total_points_all_sources = point_stats.get(
        const.DATA_KID_POINT_STATS_EARNED_TODAY, total_points_chores
    )

    return (
        total_points_all_sources,
        total_points_chores,
        total_chore_count,
        longest_chore_streak,
        points_per_chore,
        count_per_chore,
        streak_per_chore,
    )


def get_today_chore_completion_progress(
    kid_info: dict,
    tracked_chores: list,
    *,
    count_required: Optional[int] = None,
    percent_required: float = 1.0,
    require_no_overdue: bool = False,
    only_due_today: bool = False,
) -> tuple[bool, int, int]:
    """
    Check if a required number or percentage of tracked chores have been completed (approved) today for the given kid.
    If tracked_chores is empty, use all chores for the kid.

    Uses timestamp-based tracking (last_approved field) instead of the deprecated approved_chores list (removed v0.4.0).
    A chore is considered approved today if its last_approved_time matches today's date.

    Args:
        kid_info: The kid's info dictionary.
        tracked_chores: List of chore IDs to check. If empty, all kid's chores are used.
        count_required: Minimum number of chores that must be completed today (overrides percent_required if set).
        percent_required: Float between 0 and 1.0 (e.g., 0.8 for 80%). Default is 1.0 (all required).
        require_no_overdue: If True, only return True if none of the tracked chores went overdue today.
        only_due_today: If True, only consider chores with a due date of today.

    Returns:
        (criteria_met: bool, approved_count: int, total_count: int)

    Example:
        criteria_met, approved_count, total_count = self._get_today_chore_completion_progress(
            kid_info, tracked_chores, count_required=3, percent_required=0.8, require_no_overdue=True, only_due_today=True
        )
    """
    today_local = get_now_local_time()
    today_iso = today_local.date().isoformat()
    chores_data = kid_info.get(const.DATA_KID_CHORE_DATA, {})

    # Use all kid's chores if tracked_chores is empty
    if not tracked_chores:
        tracked_chores = list(chores_data.keys())

    # Filter chores if only_due_today is set
    if only_due_today:
        chores_due_today = []
        for chore_id in tracked_chores:
            chore_data = chores_data.get(chore_id, {})
            due_date_iso = chore_data.get(const.DATA_KID_CHORE_DATA_DUE_DATE)
            if (
                due_date_iso
                and due_date_iso[: const.ISO_DATE_STRING_LENGTH] == today_iso
            ):
                chores_due_today.append(chore_id)
        chores_to_check = chores_due_today
    else:
        chores_to_check = tracked_chores

    total_count = len(chores_to_check)
    if total_count == 0:
        return False, 0, 0

    # Count approved chores using timestamp-based check (last_approved_time matches today)
    approved_count = 0
    for chore_id in chores_to_check:
        chore_data = chores_data.get(chore_id, {})
        last_approved = chore_data.get(const.DATA_KID_CHORE_DATA_LAST_APPROVED)
        if last_approved and last_approved[: const.ISO_DATE_STRING_LENGTH] == today_iso:
            approved_count += 1

    # Check count_required first (overrides percent_required if set)
    if count_required is not None:
        if approved_count < count_required:
            return False, approved_count, total_count
    else:
        percent_complete = approved_count / total_count
        if percent_complete < percent_required:
            return False, approved_count, total_count

    # Check for overdue if required
    if require_no_overdue:
        for chore_id in chores_to_check:
            chore_data = chores_data.get(chore_id, {})
            # Check if chore state is overdue (single source of truth)
            chore_state = chore_data.get(const.DATA_KID_CHORE_DATA_STATE)
            if chore_state == const.CHORE_STATE_OVERDUE:
                return False, approved_count, total_count
            # Also check if it was marked overdue today (for daily achievements)
            last_overdue_iso = chore_data.get(const.DATA_KID_CHORE_DATA_LAST_OVERDUE)
            if (
                last_overdue_iso
                and last_overdue_iso[: const.ISO_DATE_STRING_LENGTH] == today_iso
            ):
                return False, approved_count, total_count

    return True, approved_count, total_count


# 🕒 -------- Date & Time Helpers (Local, UTC, Parsing, Formatting, Add Interval) --------
# These functions provide reusable, timezone-safe utilities for:
# - Getting current date/time in local or ISO formats
# - Parsing date or datetime strings safely
# - Converting naive/local times to UTC
# - Adding intervals to dates/datetimes (e.g., days, weeks, months, years)
# - Supporting badge and chore scheduling logic


def get_today_local_date() -> date:
    """
    Return today's date in local timezone as a `datetime.date`.

    Example:
        datetime.date(2025, 4, 7)
    """
    return dt_util.as_local(dt_util.utcnow()).date()


def get_today_local_iso() -> str:
    """
    Return today's date in local timezone as ISO string (YYYY-MM-DD).

    Example:
        "2025-04-07"
    """
    return get_today_local_date().isoformat()


def get_now_local_time() -> datetime:
    """
    Return the current datetime in local timezone (timezone-aware).

    Example:
        datetime.datetime(2025, 4, 7, 14, 30, tzinfo=...)
    """
    return dt_util.as_local(dt_util.utcnow())


def get_now_local_iso() -> str:
    """
    Return the current local datetime as an ISO 8601 string.

    Example:
        "2025-04-07T14:30:00-05:00"
    """
    return get_now_local_time().isoformat()


def parse_datetime_to_utc(dt_str: str) -> Optional[datetime]:
    """
    Parse a datetime string, apply timezone if naive, and convert to UTC.

    Returns:
        UTC-aware datetime object, or None if parsing fails.

    Example:
        "2025-04-07T14:30:00" → datetime.datetime(2025, 4, 7, 19, 30, tzinfo=UTC)
    """
    return normalize_datetime_input(
        dt_str,
        default_tzinfo=const.DEFAULT_TIME_ZONE,
        return_type=const.HELPER_RETURN_DATETIME_UTC,
    )


def parse_date_safe(date_str: str) -> Optional[date]:
    """
    Safely parse a date string into a `datetime.date`.

    Accepts a variety of common formats, including:
    - "2025-04-07"
    - "04/07/2025"
    - "April 7, 2025"

    Returns:
        `datetime.date` or None if parsing fails.
    """
    try:
        return dt_util.parse_date(date_str)
    except (ValueError, TypeError, AttributeError):
        return None


def format_datetime_with_return_type(
    dt_obj: datetime,
    return_type: Optional[str] = const.HELPER_RETURN_DATETIME,
) -> Union[datetime, date, str]:
    """
    Format a datetime object according to the specified return_type.

    Parameters:
        dt_obj (datetime): The datetime object to format
        return_type (Optional[str]): The desired return format:
            - const.HELPER_RETURN_DATETIME: returns the datetime object unchanged
            - const.HELPER_RETURN_DATETIME_UTC: returns the datetime object converted to UTC
            - const.HELPER_RETURN_DATETIME_LOCAL: returns the datetime object in local timezone
            - const.HELPER_RETURN_DATE: returns the date portion as a date object
            - const.HELPER_RETURN_ISO_DATETIME: returns an ISO-formatted datetime string
            - const.HELPER_RETURN_ISO_DATE: returns an ISO-formatted date string
            - const.HELPER_RETURN_SELECTOR_DATETIME: returns local timezone string
              formatted for HA DateTimeSelector ("%Y-%m-%d %H:%M:%S")

    Returns:
        Union[datetime, date, str]: The formatted date/time value
    """
    if return_type == const.HELPER_RETURN_DATETIME:
        return dt_obj
    elif return_type == const.HELPER_RETURN_DATETIME_UTC:
        return dt_util.as_utc(dt_obj)
    elif return_type == const.HELPER_RETURN_DATETIME_LOCAL:
        return dt_util.as_local(dt_obj)
    elif return_type == const.HELPER_RETURN_DATE:
        return dt_obj.date()
    elif return_type == const.HELPER_RETURN_ISO_DATETIME:
        return dt_obj.isoformat()
    elif return_type == const.HELPER_RETURN_ISO_DATE:
        return dt_obj.date().isoformat()
    elif return_type == const.HELPER_RETURN_SELECTOR_DATETIME:
        # For HA DateTimeSelector: local timezone, "%Y-%m-%d %H:%M:%S" format
        return dt_util.as_local(dt_obj).strftime("%Y-%m-%d %H:%M:%S")
    else:
        # Default fallback is to return the datetime object unchanged
        return dt_obj


def normalize_datetime_input(  # pyright: ignore[reportReturnType]
    dt_input: Union[str, date, datetime],
    default_tzinfo: Optional[tzinfo] = None,
    return_type: Optional[str] = const.HELPER_RETURN_DATETIME,
) -> Union[datetime, date, str, None]:
    """
    Normalize various datetime input formats to a consistent format.

    This function handles various input formats (string, date, datetime) and
    ensures proper timezone awareness. It can output in various formats based
    on the return_type parameter.

    Parameters:
        dt_input: String, date or datetime to normalize
        default_tzinfo: Timezone to use if the input is naive
                        (defaults to const.DEFAULT_TIME_ZONE if None)
        return_type: Format for the returned value:
            - const.HELPER_RETURN_DATETIME: returns a datetime object (default)
            - const.HELPER_RETURN_DATETIME_UTC: returns a datetime object in UTC timezone
            - const.HELPER_RETURN_DATETIME_LOCAL: returns a datetime object in local timezone
            - const.HELPER_RETURN_DATE: returns a date object
            - const.HELPER_RETURN_ISO_DATETIME: returns an ISO-formatted datetime string
            - const.HELPER_RETURN_ISO_DATE: returns an ISO-formatted date string
            - const.HELPER_RETURN_SELECTOR_DATETIME: returns a local timezone string
              formatted for HA DateTimeSelector ("%Y-%m-%d %H:%M:%S")

    Returns:
        Normalized datetime, date, or string representation based on return_type,
        or None if the input could not be parsed.

    Example:
        >>> normalize_datetime_input("2025-04-15")
        datetime.datetime(2025, 4, 15, 0, 0, tzinfo=ZoneInfo('America/New_York'))

        >>> normalize_datetime_input("2025-04-15", return_type=const.HELPER_RETURN_ISO_DATETIME)
        '2025-04-15T00:00:00-04:00'
    """
    # Handle empty input
    if not dt_input:
        return None

    # Set default timezone if not specified
    tz_info = default_tzinfo or const.DEFAULT_TIME_ZONE

    # Initialize result variable
    result = None

    # Handle string inputs
    if isinstance(dt_input, str):
        try:
            # First try using Home Assistant's parser (handles more formats)
            result = dt_util.parse_datetime(dt_input)
            if result is None:
                # Fall back to ISO format parsing
                result = datetime.fromisoformat(dt_input)
        except ValueError:
            # If datetime parsing fails, try to parse as a date
            result = parse_date_safe(dt_input)
            if result:
                # Convert date to datetime for consistent handling
                result = datetime.combine(result, datetime.min.time())
            else:
                return None

    # Handle date objects
    elif isinstance(dt_input, date) and not isinstance(dt_input, datetime):
        result = datetime.combine(dt_input, datetime.min.time())

    # Handle datetime objects
    elif isinstance(dt_input, datetime):
        result = dt_input

    else:
        # Unsupported input type
        return None

    # Ensure timezone awareness
    if result.tzinfo is None:
        result = result.replace(tzinfo=tz_info)

    # Return in the requested format using the shared format function
    return format_datetime_with_return_type(result, return_type)


def adjust_datetime_by_interval(  # pyright: ignore[reportReturnType]
    base_date: Union[str, date, datetime],
    interval_unit: str,
    delta: int,
    end_of_period: Optional[str] = None,
    require_future: bool = False,
    reference_datetime: Optional[Union[str, date, datetime]] = None,
    return_type: Optional[str] = const.HELPER_RETURN_DATETIME,
) -> Union[str, date, datetime]:
    """
    Add or Subtract a time interval to a date or datetime and returns the result in the desired format.

    Parameters:
    - base_date: ISO string, datetime.date, or datetime.datetime.
    - interval_unit: One of the defined const.CONF_* constants:
        - const.TIME_UNIT_MINUTES, const.TIME_UNIT_HOURS, const.TIME_UNIT_DAYS, const.TIME_UNIT_WEEKS,
          const.TIME_UNIT_MONTHS, const.TIME_UNIT_QUARTERS, const.TIME_UNIT_YEARS.
    - delta: Number of time units to add.
    - end_of_period: Optional string to adjust the result to the end of the period.
                     Valid values are:
                        const.PERIOD_DAY_END (sets time to 23:59:00),
                        const.PERIOD_WEEK_END (advances to upcoming Sunday at 23:59:00),
                        const.PERIOD_MONTH_END (last day of the month at 23:59:00),
                        const.PERIOD_QUARTER_END (last day of quarter at 23:59:00),
                        const.PERIOD_YEAR_END (December 31 at 23:59:00).
    - require_future: If True, ensures the result is strictly after reference_datetime.
                     Default is True.
    - reference_datetime: The reference datetime to compare against when require_future is True.
                         If None, current time is used. Default is None.
    - return_type: Optional; one of the const.HELPER_RETURN_* constants:
        - const.HELPER_RETURN_ISO_DATE: returns "YYYY-MM-DD"
        - const.HELPER_RETURN_ISO_DATETIME: returns "YYYY-MM-DDTHH:MM:SS"
        - const.HELPER_RETURN_DATE: returns datetime.date
        - const.HELPER_RETURN_DATETIME: returns datetime.datetime
        - const.HELPER_RETURN_DATETIME_UTC: returns datetime.datetime in UTC timezone
        - const.HELPER_RETURN_DATETIME_LOCAL: returns datetime.datetime in local timezone
      Default is const.HELPER_RETURN_DATETIME.

    Notes:
    - Preserves timezone awareness if present in input.
    - If input is naive (no tzinfo), output will also be naive.
    - If require_future is True, interval will be added repeatedly until the result
      is later than reference_datetime.
    """
    if not base_date:
        const.LOGGER.error(
            "ERROR: Add Interval To DateTime - base_date is None. Cannot calculate next scheduled datetime."
        )
        return None

    # Get the local timezone for reference datetime handling
    local_tz = const.DEFAULT_TIME_ZONE

    # Use normalize_datetime_input for consistent handling of base_date
    base_dt = normalize_datetime_input(
        base_date, default_tzinfo=local_tz, return_type=const.HELPER_RETURN_DATETIME
    )

    if base_dt is None:
        const.LOGGER.error(
            "ERROR: Add Interval To DateTime - Could not parse base_date."
        )
        return None

    # Calculate the basic interval addition.
    if interval_unit == const.TIME_UNIT_MINUTES:
        result = base_dt + timedelta(minutes=delta)
    elif interval_unit == const.TIME_UNIT_HOURS:
        result = base_dt + timedelta(hours=delta)
    elif interval_unit == const.TIME_UNIT_DAYS:
        result = base_dt + timedelta(days=delta)
    elif interval_unit == const.TIME_UNIT_WEEKS:
        result = base_dt + timedelta(weeks=delta)
    elif interval_unit in {const.TIME_UNIT_MONTHS, const.TIME_UNIT_QUARTERS}:
        multiplier = (
            const.MONTH_INTERVAL_MULTIPLIER
            if interval_unit == const.TIME_UNIT_MONTHS
            else const.MONTHS_PER_QUARTER
        )
        total_months = base_dt.month - 1 + (delta * multiplier)
        year = int(base_dt.year + total_months // const.MONTHS_PER_YEAR)
        month = int(total_months % const.MONTHS_PER_YEAR + 1)
        day = min(base_dt.day, monthrange(year, month)[1])
        result = base_dt.replace(year=year, month=month, day=day)
    elif interval_unit == const.TIME_UNIT_YEARS:
        year = int(base_dt.year + delta)
        day = min(base_dt.day, monthrange(year, base_dt.month)[1])
        result = base_dt.replace(year=year, day=day)
    else:
        raise ValueError(f"Unsupported interval unit: {interval_unit}")

    # Adjust result to the end of the period, if specified.
    if end_of_period:
        if end_of_period == const.PERIOD_DAY_END:
            result = result.replace(
                hour=const.END_OF_DAY_HOUR,
                minute=const.END_OF_DAY_MINUTE,
                second=const.END_OF_DAY_SECOND,
                microsecond=0,
            )
        elif end_of_period == const.PERIOD_WEEK_END:
            # Assuming week ends on Sunday (weekday() returns 0 for Monday; Sunday is 6).
            days_until_sunday = (const.SUNDAY_WEEKDAY_INDEX - result.weekday()) % 7
            result = (result + timedelta(days=days_until_sunday)).replace(
                hour=const.END_OF_DAY_HOUR,
                minute=const.END_OF_DAY_MINUTE,
                second=const.END_OF_DAY_SECOND,
                microsecond=0,
            )
        elif end_of_period == const.PERIOD_MONTH_END:
            last_day = monthrange(result.year, result.month)[1]
            result = result.replace(
                day=last_day,
                hour=const.END_OF_DAY_HOUR,
                minute=const.END_OF_DAY_MINUTE,
                second=const.END_OF_DAY_SECOND,
                microsecond=0,
            )
        elif end_of_period == const.PERIOD_QUARTER_END:
            # Calculate the last month of the current quarter.
            last_month_of_quarter = (
                (result.month - 1) // const.MONTHS_PER_QUARTER + 1
            ) * const.MONTHS_PER_QUARTER
            last_day = monthrange(result.year, last_month_of_quarter)[1]
            result = result.replace(
                month=last_month_of_quarter,
                day=last_day,
                hour=const.END_OF_DAY_HOUR,
                minute=const.END_OF_DAY_MINUTE,
                second=const.END_OF_DAY_SECOND,
                microsecond=0,
            )
        elif end_of_period == const.PERIOD_YEAR_END:
            result = result.replace(
                month=const.LAST_MONTH_OF_YEAR,
                day=const.LAST_DAY_OF_DECEMBER,
                hour=const.END_OF_DAY_HOUR,
                minute=const.END_OF_DAY_MINUTE,
                second=const.END_OF_DAY_SECOND,
                microsecond=0,
            )
        else:
            raise ValueError(f"Unsupported end_of_period value: {end_of_period}")

    # Handle require_future logic
    if require_future:
        # Process reference_datetime using normalize_datetime_input
        reference_dt = (
            normalize_datetime_input(
                reference_datetime,
                default_tzinfo=local_tz,
                return_type=const.HELPER_RETURN_DATETIME,
            )
            or get_now_local_time()
        )

        # Convert to UTC for consistent comparison
        result_utc = dt_util.as_utc(result)
        reference_dt_utc = dt_util.as_utc(reference_dt)

        # Loop until we have a future date
        iteration_count = 0

        while (
            result_utc <= reference_dt_utc
            and iteration_count < const.MAX_DATE_CALCULATION_ITERATIONS
        ):
            iteration_count += 1
            previous_result = result  # Store before calculating new interval

            # Add the interval again
            if interval_unit == const.TIME_UNIT_MINUTES:
                result = result + timedelta(minutes=delta)
            elif interval_unit == const.TIME_UNIT_HOURS:
                result = result + timedelta(hours=delta)
            elif interval_unit == const.TIME_UNIT_DAYS:
                result = result + timedelta(days=delta)
            elif interval_unit == const.TIME_UNIT_WEEKS:
                result = result + timedelta(weeks=delta)
            elif interval_unit in {const.TIME_UNIT_MONTHS, const.TIME_UNIT_QUARTERS}:
                multiplier = (
                    const.MONTH_INTERVAL_MULTIPLIER
                    if interval_unit == const.TIME_UNIT_MONTHS
                    else const.MONTHS_PER_QUARTER
                )
                total_months = result.month - 1 + (delta * multiplier)
                year = result.year + total_months // 12
                month = total_months % 12 + 1
                day = min(result.day, monthrange(year, month)[1])
                result = result.replace(year=year, month=month, day=day)
            elif interval_unit == const.TIME_UNIT_YEARS:
                year = result.year + delta
                day = min(result.day, monthrange(year, result.month)[1])
                result = result.replace(year=year, day=day)

            # Re-apply end_of_period if needed
            if end_of_period:
                if end_of_period == const.PERIOD_DAY_END:
                    result = result.replace(
                        hour=const.END_OF_DAY_HOUR,
                        minute=const.END_OF_DAY_MINUTE,
                        second=const.END_OF_DAY_SECOND,
                        microsecond=0,
                    )
                elif end_of_period == const.PERIOD_WEEK_END:
                    days_until_sunday = (
                        const.SUNDAY_WEEKDAY_INDEX - result.weekday()
                    ) % 7
                    result = (result + timedelta(days=days_until_sunday)).replace(
                        hour=const.END_OF_DAY_HOUR,
                        minute=const.END_OF_DAY_MINUTE,
                        second=const.END_OF_DAY_SECOND,
                        microsecond=0,
                    )
                elif end_of_period == const.PERIOD_MONTH_END:
                    last_day = monthrange(result.year, result.month)[1]
                    result = result.replace(
                        day=last_day,
                        hour=const.END_OF_DAY_HOUR,
                        minute=const.END_OF_DAY_MINUTE,
                        second=const.END_OF_DAY_SECOND,
                        microsecond=0,
                    )
                elif end_of_period == const.PERIOD_QUARTER_END:
                    last_month_of_quarter = (
                        (result.month - 1) // const.MONTHS_PER_QUARTER + 1
                    ) * const.MONTHS_PER_QUARTER
                    last_day = monthrange(result.year, last_month_of_quarter)[1]
                    result = result.replace(
                        month=last_month_of_quarter,
                        day=last_day,
                        hour=const.END_OF_DAY_HOUR,
                        minute=const.END_OF_DAY_MINUTE,
                        second=const.END_OF_DAY_SECOND,
                        microsecond=0,
                    )
                elif end_of_period == const.PERIOD_YEAR_END:
                    result = result.replace(
                        month=const.LAST_MONTH_OF_YEAR,
                        day=const.LAST_DAY_OF_DECEMBER,
                        hour=const.END_OF_DAY_HOUR,
                        minute=const.END_OF_DAY_MINUTE,
                        second=const.END_OF_DAY_SECOND,
                        microsecond=0,
                    )

            # Check if we're in a loop (result didn't change)
            if result == previous_result:
                # Break the loop by adding 1 hour
                result = result + timedelta(hours=1)

            result_utc = dt_util.as_utc(result)

            if iteration_count >= const.MAX_DATE_CALCULATION_ITERATIONS:
                const.LOGGER.warning(
                    "WARN: Add Interval To DateTime - Maximum iterations (%d) reached! "
                    "Params: base_date=%s, interval_unit=%s, delta=%s, reference_datetime=%s",
                    const.MAX_DATE_CALCULATION_ITERATIONS,
                    base_dt,
                    interval_unit,
                    delta,
                    reference_dt,
                )

    # Use format_datetime_with_return_type for consistent return formatting
    final_result = format_datetime_with_return_type(result, return_type)

    return final_result


def get_next_scheduled_datetime(
    base_date: Union[str, date, datetime],
    interval_type: str,
    require_future: bool = True,
    reference_datetime: Optional[Union[str, date, datetime]] = None,
    return_type: Optional[str] = const.HELPER_RETURN_DATETIME,
) -> Union[date, datetime, str]:
    """
    Calculates the next scheduled datetime based on an interval type from a given start date.

    Supported interval types (using local timezone):
      - Daily:         const.FREQUENCY_DAILY
      - Weekly:        const.FREQUENCY_WEEKLY or const.FREQUENCY_CUSTOM_1_WEEK
      - Biweekly:      const.FREQUENCY_BIWEEKLY
      - Monthly:       const.FREQUENCY_MONTHLY or const.FREQUENCY_CUSTOM_1_MONTH
      - Quarterly:     const.FREQUENCY_QUARTERLY
      - Yearly:        const.FREQUENCY_YEARLY or const.FREQUENCY_CUSTOM_1_YEAR
      - Period-end types:
          - Day end:   const.PERIOD_DAY_END (sets time to 23:59:00)
          - Week end:  const.PERIOD_WEEK_END (advances to upcoming Sunday at 23:59:00)
          - Month end: const.PERIOD_MONTH_END (last day of the month at 23:59:00)
          - Quarter end: const.PERIOD_QUARTER_END (last day of quarter at 23:59:00)
          - Year end:  const.PERIOD_YEAR_END (December 31 at 23:59:00)

    Behavior:
      - Accepts a string, date, or datetime object for start_date.
      - For period-end types, the helper sets the time to 23:59:00.
      - For other types, the time portion from the input is preserved.
      - If require_future is True, the schedule is advanced until the resulting datetime is strictly after the given reference_datetime.
      - The reference_datetime (if provided) can be a string, date, or datetime; if omitted, the current local datetime is used.
      - The return_type is optional and defaults to returning a datetime object.

    Examples:
      - get_next_scheduled_datetime("2025-04-07", const.FREQUENCY_MONTHLY)
          → datetime.date(2025, 5, 7)
      - get_next_scheduled_datetime("2025-04-07T09:00:00", const.FREQUENCY_WEEKLY, return_type=const.HELPER_RETURN_ISO_DATETIME)
          → "2025-04-14T09:00:00"
      - get_next_scheduled_datetime("2025-04-07", const.PERIOD_MONTH_END, return_type=const.HELPER_RETURN_ISO_DATETIME)
          → "2025-04-30T23:59:00"
      - get_next_scheduled_datetime("2024-06-01", const.FREQUENCY_CUSTOM_1_YEAR, require_future=True)
          → datetime.date(2025, 6, 1)
    """
    if not base_date:
        const.LOGGER.error(
            "ERROR: Get Next Schedule DateTime - base_date is None. Cannot calculate next scheduled datetime."
        )
        return None

    # Get the local timezone.
    local_tz = const.DEFAULT_TIME_ZONE

    # Use normalize_datetime_input for consistent handling of base_date
    base_dt: Optional[Union[str, date, datetime]] = normalize_datetime_input(
        base_date, default_tzinfo=local_tz, return_type=const.HELPER_RETURN_DATETIME
    )

    if base_dt is None:
        const.LOGGER.error(
            "ERROR: Get Next Schedule DateTime - Could not parse base_date."
        )
        return None

    # Internal function to calculate the next interval.
    def calculate_next_interval(base_dt: datetime) -> datetime:
        """
        Calculate the next datetime based on the interval type using add_interval_to_datetime.
        """
        if interval_type in {const.FREQUENCY_DAILY}:
            return adjust_datetime_by_interval(
                base_dt,
                const.TIME_UNIT_DAYS,
                1,
                end_of_period=None,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type in {const.FREQUENCY_WEEKLY, const.FREQUENCY_CUSTOM_1_WEEK}:
            return adjust_datetime_by_interval(
                base_dt,
                const.TIME_UNIT_WEEKS,
                1,
                end_of_period=None,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.FREQUENCY_BIWEEKLY:
            return adjust_datetime_by_interval(
                base_dt,
                const.TIME_UNIT_WEEKS,
                2,
                end_of_period=None,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type in {const.FREQUENCY_MONTHLY, const.FREQUENCY_CUSTOM_1_MONTH}:
            return adjust_datetime_by_interval(
                base_dt,
                const.TIME_UNIT_MONTHS,
                1,
                end_of_period=None,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.FREQUENCY_QUARTERLY:
            return adjust_datetime_by_interval(
                base_dt,
                const.TIME_UNIT_QUARTERS,
                1,
                end_of_period=None,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type in {const.FREQUENCY_YEARLY, const.FREQUENCY_CUSTOM_1_YEAR}:
            return adjust_datetime_by_interval(
                base_dt,
                const.TIME_UNIT_YEARS,
                1,
                end_of_period=None,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.PERIOD_DAY_END:
            return adjust_datetime_by_interval(
                base_dt,
                const.TIME_UNIT_DAYS,
                0,
                end_of_period=const.PERIOD_DAY_END,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.PERIOD_WEEK_END:
            return adjust_datetime_by_interval(
                base_dt,
                const.TIME_UNIT_DAYS,
                0,
                end_of_period=const.PERIOD_WEEK_END,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.PERIOD_MONTH_END:
            return adjust_datetime_by_interval(
                base_dt,
                const.TIME_UNIT_DAYS,
                0,
                end_of_period=const.PERIOD_MONTH_END,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.PERIOD_QUARTER_END:
            return adjust_datetime_by_interval(
                base_dt,
                const.TIME_UNIT_DAYS,
                0,
                end_of_period=const.PERIOD_QUARTER_END,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.PERIOD_YEAR_END:
            return adjust_datetime_by_interval(
                base_dt,
                const.TIME_UNIT_DAYS,
                0,
                end_of_period=const.PERIOD_YEAR_END,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        else:
            raise ValueError(f"Unsupported interval type: {interval_type}")

    # Calculate the initial next scheduled datetime.
    result = calculate_next_interval(base_dt)

    # Process reference_datetime using normalize_datetime_input
    reference_dt = (
        normalize_datetime_input(
            reference_datetime,
            default_tzinfo=local_tz,
            return_type=const.HELPER_RETURN_DATETIME,
        )
        or get_now_local_time()
    )

    # Convert a copy of result and reference_dt to UTC for future comparison.
    # Prevents any inadvertent time changes to result
    result_utc = dt_util.as_utc(result)
    reference_dt_utc = dt_util.as_utc(reference_dt)

    # If require_future is True, loop until result_utc is strictly after reference_dt_utc.
    if require_future:
        iteration_count = 0

        while (
            result_utc <= reference_dt_utc
            and iteration_count < const.MAX_DATE_CALCULATION_ITERATIONS
        ):
            iteration_count += 1
            previous_result = result  # Store before calculating new result
            temp_base = result  # We keep result in local time.
            result = calculate_next_interval(temp_base)

            # Check if we're in a loop (result didn't change as can happen with period ends)
            if result == previous_result:
                # Break the loop by adding 1 hour and recalculating
                result = adjust_datetime_by_interval(
                    result,
                    const.TIME_UNIT_HOURS,
                    1,
                    end_of_period=None,
                    return_type=const.HELPER_RETURN_DATETIME,
                )
                result = calculate_next_interval(result)

            result_utc = dt_util.as_utc(result)

            if iteration_count >= const.MAX_DATE_CALCULATION_ITERATIONS:
                const.LOGGER.warning(
                    "WARN: Get Next Schedule DateTime - Maximum iterations (%d) reached! "
                    "Params: base_date=%s, interval_type=%s, reference_datetime=%s",
                    const.MAX_DATE_CALCULATION_ITERATIONS,
                    base_date,
                    interval_type,
                    reference_dt,
                )

    # Use format_datetime_with_return_type to handle the return type formatting
    final_result = format_datetime_with_return_type(result, return_type)

    return final_result


def get_next_applicable_day(
    dt: datetime,
    applicable_days: Iterable[int],
    local_tz: Optional[tzinfo] = None,
    return_type: Optional[str] = const.HELPER_RETURN_DATETIME,
) -> Union[datetime, date, str]:
    """
    Advances the provided datetime to the next day (or same day) where the day-of-week
    (as returned by dt.weekday()) is included in the applicable_days iterable.

    Parameters:
        dt (datetime): A timezone-aware datetime.
        applicable_days (Iterable[int]): An iterable of weekday numbers (0 = Monday, ... 6 = Sunday)
            that are considered valid.
        local_tz (Optional[tzinfo]): The local timezone to use for conversion. If not provided,
            defaults to const.DEFAULT_TIME_ZONE.
        return_type (Optional[str]): Specifies the return format. Options are:
            - const.HELPER_RETURN_DATETIME: returns a datetime object (default).
            - const.HELPER_RETURN_DATETIME_UTC: returns a datetime object in UTC timezone.
            - const.HELPER_RETURN_DATETIME_LOCAL: returns a datetime object in local timezone.
            - const.HELPER_RETURN_DATE: returns a date object.
            - const.HELPER_RETURN_ISO_DATETIME: returns an ISO-formatted datetime string.
            - const.HELPER_RETURN_ISO_DATE: returns an ISO-formatted date string.

    Returns:
        Union[datetime, date, str]: The adjusted datetime in the format specified by return_type.

    Note:
        This function is generic with respect to weekdays—it simply compares the numeric result
        of dt.weekday() against the provided applicable_days. Any mapping from names to numbers
        should be done before calling this helper.

    Example:
        Suppose you want the next applicable day to be Monday (0) or Wednesday (2):

            >>> dt_input = datetime(2025, 4, 12, 15, 0, tzinfo=const.DEFAULT_TIME_ZONE)
            >>> # 2025-04-12 is a Saturday (weekday() == 5), so the next applicable day is Monday (0)
            >>> get_next_applicable_day(dt_input, applicable_days=[0, 2])
            2025-04-14 15:00:00-04:00
    """
    local_tz = local_tz or const.DEFAULT_TIME_ZONE

    # Convert dt to local time.
    local_dt = dt_util.as_local(dt)
    if local_dt.tzinfo != local_tz:
        local_dt = dt.astimezone(local_tz)

    # Advance dt until its weekday (as an integer) is in applicable_days.
    while local_dt.weekday() not in applicable_days:
        # Guard against overflow: if dt is too near datetime.max, raise an error.
        max_dt = datetime.max.replace(tzinfo=local_tz)
        if dt >= (max_dt - timedelta(days=1)):
            const.LOGGER.error(
                "Overflow in get_next_applicable_day: dt is too close to datetime.max: %s",
                dt,
            )
            raise OverflowError("Date value out of range in get_next_applicable_day.")
        dt += timedelta(days=1)
        local_dt = dt_util.as_local(dt)
        if local_dt.tzinfo != local_tz:
            local_dt = dt.astimezone(local_tz)

    # Use format_datetime_with_return_type to handle the return type formatting
    final_result = format_datetime_with_return_type(dt, return_type)

    return final_result


def cleanup_period_data(
    self,
    periods_data: dict,
    period_keys: dict,
    retention_daily: int = None,
    retention_weekly: int = None,
    retention_monthly: int = None,
    retention_yearly: int = None,
):
    """
    Remove old period data to keep storage manageable for any period-based data (chore, point, etc).

    Args:
        periods_data: Dictionary containing period data (e.g., for a chore or points)
        period_keys: Dict mapping logical period names to their constant keys, e.g.:
            {
                "daily": const.DATA_KID_CHORE_DATA_PERIODS_DAILY,
                "weekly": const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY,
                "monthly": const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY,
                "yearly": const.DATA_KID_CHORE_DATA_PERIODS_YEARLY,
            }
        retention_daily: Number of days to retain (default: const.DEFAULT_RETENTION_DAILY)
        retention_weekly: Number of weeks to retain (default: const.DEFAULT_RETENTION_WEEKLY)
        retention_monthly: Number of months to retain (default: const.DEFAULT_RETENTION_MONTHLY)
        retention_yearly: Number of years to retain (default: const.DEFAULT_RETENTION_YEARLY)
    """
    today_local = get_today_local_date()

    # Use provided values or fall back to defaults
    retention_daily = (
        retention_daily
        if retention_daily is not None
        else const.DEFAULT_RETENTION_DAILY
    )
    retention_weekly = (
        retention_weekly
        if retention_weekly is not None
        else const.DEFAULT_RETENTION_WEEKLY
    )
    retention_monthly = (
        retention_monthly
        if retention_monthly is not None
        else const.DEFAULT_RETENTION_MONTHLY
    )
    retention_yearly = (
        retention_yearly
        if retention_yearly is not None
        else const.DEFAULT_RETENTION_YEARLY
    )

    # Daily: keep configured days
    cutoff_daily = adjust_datetime_by_interval(
        today_local.isoformat(),
        interval_unit=const.TIME_UNIT_DAYS,
        delta=-retention_daily,
        require_future=False,
        return_type=const.HELPER_RETURN_ISO_DATE,
    )
    daily_data = periods_data.get(period_keys["daily"], {})
    for day in list(daily_data.keys()):
        if day < cutoff_daily:
            del daily_data[day]

    # Weekly: keep configured weeks
    cutoff_date = adjust_datetime_by_interval(
        today_local.isoformat(),
        interval_unit=const.TIME_UNIT_WEEKS,
        delta=-retention_weekly,
        require_future=False,
        return_type=const.HELPER_RETURN_DATETIME,
    )
    cutoff_weekly = cutoff_date.strftime("%Y-W%V")
    weekly_data = periods_data.get(period_keys["weekly"], {})
    for week in list(weekly_data.keys()):
        if week < cutoff_weekly:
            del weekly_data[week]

    # Monthly: keep configured months
    cutoff_date = adjust_datetime_by_interval(
        today_local.isoformat(),
        interval_unit=const.TIME_UNIT_MONTHS,
        delta=-retention_monthly,
        require_future=False,
        return_type=const.HELPER_RETURN_DATETIME,
    )
    cutoff_monthly = cutoff_date.strftime("%Y-%m")
    monthly_data = periods_data.get(period_keys["monthly"], {})
    for month in list(monthly_data.keys()):
        if month < cutoff_monthly:
            del monthly_data[month]

    # Yearly: keep configured years
    cutoff_yearly = str(int(today_local.strftime("%Y")) - retention_yearly)
    yearly_data = periods_data.get(period_keys["yearly"], {})
    for year in list(yearly_data.keys()):
        if year < cutoff_yearly:
            del yearly_data[year]

    self._persist()  # type: ignore[attr-defined]  # pylint: disable=protected-access
    self.async_set_updated_data(self._data)  # type: ignore[attr-defined]  # pylint: disable=protected-access


# 📝 -------- Dashboard Translation Loaders --------
def _read_json_file(file_path: str) -> dict:
    """Read and parse a JSON file. Synchronous helper for executor."""
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


async def get_available_dashboard_languages(
    hass: HomeAssistant,
) -> list[str]:
    """Get list of available dashboard language codes.

    Scans the translations directory for dashboard translation files and filters
    against Home Assistant's master LANGUAGES set. Only language codes that have
    actual translation files are returned.

    Returns:
        List of language codes (e.g., ["en", "es", "de"]).
        If directory not found or empty, returns ["en"] as fallback.
    """
    from homeassistant.generated.languages import LANGUAGES

    translations_path = os.path.join(
        os.path.dirname(__file__), const.DASHBOARD_TRANSLATIONS_DIR
    )

    if not await hass.async_add_executor_job(os.path.exists, translations_path):
        const.LOGGER.debug(
            "Dashboard translations directory not found: %s, using English only",
            translations_path,
        )
        return ["en"]

    try:
        filenames = await hass.async_add_executor_job(os.listdir, translations_path)
        available_languages = []

        for filename in filenames:
            # Only process files matching *_dashboard.json pattern
            if not filename.endswith(f"{const.DASHBOARD_TRANSLATIONS_SUFFIX}.json"):
                continue

            # Extract language code from filename (e.g., es_dashboard.json -> es)
            lang_code = filename[
                : -len(".json") - len(const.DASHBOARD_TRANSLATIONS_SUFFIX)
            ]

            # Only include if valid in Home Assistant's LANGUAGES set
            if lang_code in LANGUAGES:
                available_languages.append(lang_code)
            else:
                const.LOGGER.debug(
                    "Ignoring unknown language code: %s (not in LANGUAGES set)",
                    lang_code,
                )

        # Ensure English is always available
        if "en" not in available_languages:
            available_languages.insert(0, "en")
        else:
            # Ensure English is first in the list
            available_languages.remove("en")
            available_languages.insert(0, "en")

        # Sort remaining languages (English stays first)
        if len(available_languages) > 1:
            available_languages = ["en"] + sorted(available_languages[1:])

        const.LOGGER.debug("Available dashboard languages: %s", available_languages)
        return available_languages

    except OSError as err:
        const.LOGGER.error("Error reading dashboard translations directory: %s", err)
        return ["en"]


async def load_dashboard_translation(
    hass: HomeAssistant,
    language: str = "en",
) -> dict[str, str]:
    """Load a specific dashboard translation file with English fallback.

    Args:
        hass: Home Assistant instance
        language: Language code to load (e.g., 'en', 'es', 'de')

    Returns:
        A dict with translation keys and values.
        If the requested language is not found, returns English translations.
    """
    translations_path = os.path.join(
        os.path.dirname(__file__), const.DASHBOARD_TRANSLATIONS_DIR
    )

    if not await hass.async_add_executor_job(os.path.exists, translations_path):
        const.LOGGER.error(
            "Dashboard translations directory not found: %s", translations_path
        )
        return {}

    # Try to load the requested language (with _dashboard suffix)
    lang_path = os.path.join(
        translations_path, f"{language}{const.DASHBOARD_TRANSLATIONS_SUFFIX}.json"
    )
    if await hass.async_add_executor_job(os.path.exists, lang_path):
        try:
            data = await hass.async_add_executor_job(_read_json_file, lang_path)
            const.LOGGER.debug("Loaded %s dashboard translations", language)
            return data
        except (OSError, json.JSONDecodeError) as err:
            const.LOGGER.error("Error loading %s translations: %s", language, err)

    # Fall back to English if requested language not found or errored
    if language != "en":
        const.LOGGER.warning(
            "Language '%s' not found, falling back to English", language
        )
        en_path = os.path.join(
            translations_path, f"en{const.DASHBOARD_TRANSLATIONS_SUFFIX}.json"
        )
        if await hass.async_add_executor_job(os.path.exists, en_path):
            try:
                data = await hass.async_add_executor_job(_read_json_file, en_path)
                const.LOGGER.debug("Loaded English dashboard translations as fallback")
                return data
            except (OSError, json.JSONDecodeError) as err:
                const.LOGGER.error("Error loading English translations: %s", err)

    return {}


async def load_notification_translation(
    hass: HomeAssistant,
    language: str = "en",
) -> dict[str, dict[str, str]]:
    """Load notification translations for a specific language with English fallback.

    Args:
        hass: Home Assistant instance
        language: Language code to load (e.g., 'en', 'es', 'de')

    Returns:
        A dict with notification keys mapping to {title, message} dicts.
        If the requested language is not found, returns English translations.
    """
    # Normalize language: default to English if empty/None
    if not language:
        language = "en"

    translations_path = os.path.join(
        os.path.dirname(__file__), const.CUSTOM_TRANSLATIONS_DIR
    )

    if not await hass.async_add_executor_job(os.path.exists, translations_path):
        const.LOGGER.error(
            "Custom translations directory not found: %s", translations_path
        )
        return {}

    # Try to load the requested language (with _notifications suffix)
    lang_path = os.path.join(
        translations_path, f"{language}{const.NOTIFICATION_TRANSLATIONS_SUFFIX}.json"
    )
    if await hass.async_add_executor_job(os.path.exists, lang_path):
        try:
            data = await hass.async_add_executor_job(_read_json_file, lang_path)
            const.LOGGER.debug("Loaded %s notification translations", language)
            return data
        except (OSError, json.JSONDecodeError) as err:
            const.LOGGER.error(
                "Error loading %s notification translations: %s", language, err
            )

    # Fall back to English if requested language not found or errored
    if language != "en":
        const.LOGGER.warning(
            "Notification language '%s' not found, falling back to English", language
        )
        en_path = os.path.join(
            translations_path, f"en{const.NOTIFICATION_TRANSLATIONS_SUFFIX}.json"
        )
        if await hass.async_add_executor_job(os.path.exists, en_path):
            try:
                data = await hass.async_add_executor_job(_read_json_file, en_path)
                const.LOGGER.debug(
                    "Loaded English notification translations as fallback"
                )
                return data
            except (OSError, json.JSONDecodeError) as err:
                const.LOGGER.error(
                    "Error loading English notification translations: %s", err
                )
    else:
        # If we get here, English was requested but file not found
        const.LOGGER.error(
            "English notification translations not found at: %s",
            os.path.join(
                translations_path,
                f"en{const.NOTIFICATION_TRANSLATIONS_SUFFIX}.json",
            ),
        )

    return {}


# 📱 -------- Device Info Helpers --------
def create_kid_device_info(kid_id: str, kid_name: str, config_entry):
    """Create device info for a kid profile.

    Args:
        kid_id: Internal ID (UUID) of the kid
        kid_name: Display name of the kid
        config_entry: Config entry for this integration instance

    Returns:
        DeviceInfo dict for the kid device
    """
    from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

    return DeviceInfo(
        identifiers={(const.DOMAIN, kid_id)},
        name=f"{kid_name} ({config_entry.title})",
        manufacturer="KidsChores",
        model="Kid Profile",
        entry_type=DeviceEntryType.SERVICE,
    )


def create_system_device_info(config_entry):
    """Create device info for system/global entities.

    Args:
        config_entry: Config entry for this integration instance

    Returns:
        DeviceInfo dict for the system device
    """
    from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

    return DeviceInfo(
        identifiers={(const.DOMAIN, f"{config_entry.entry_id}_system")},
        name=f"System ({config_entry.title})",
        manufacturer="KidsChores",
        model="System Controls",
        entry_type=DeviceEntryType.SERVICE,
    )


def get_entity_name_or_log_error(
    entity_type: str,
    entity_id: str,
    entity_data: dict,
    name_key: str,
) -> str | None:
    """Get entity name from data dict, log error if missing (data corruption detection).

    Args:
        entity_type: Type of entity (for logging) e.g. 'kid', 'chore', 'reward'
        entity_id: Entity ID (for logging)
        entity_data: Dict containing entity data
        name_key: Key to look up name in entity_data

    Returns:
        Entity name if present, None if missing (with error log)
    """
    name = entity_data.get(name_key)
    if not name:
        const.LOGGER.error(
            "Data corruption: %s %s missing %s. Entity will not be created. "
            "This indicates a storage issue or validation bypass.",
            entity_type,
            entity_id,
            name_key,
        )
        return None
    return name


def get_entity_id_from_unique_id(hass: HomeAssistant, unique_id: str) -> str | None:
    """Look up entity ID from unique ID via entity registry.

    This helper centralizes the entity registry lookup pattern that was
    duplicated ~10 times across sensor.py. Returns None if lookup fails.

    Args:
        hass: Home Assistant instance
        unique_id: The unique_id to search for

    Returns:
        Entity ID string if found, None otherwise
    """
    try:
        from homeassistant.helpers.entity_registry import async_get

        entity_registry = async_get(hass)
        for entity in entity_registry.entities.values():
            if entity.unique_id == unique_id:
                return entity.entity_id
    except (KeyError, ValueError, AttributeError, RuntimeError) as ex:
        const.LOGGER.debug(
            "Entity registry lookup failed for unique_id %s: %s", unique_id, ex
        )

    return None
