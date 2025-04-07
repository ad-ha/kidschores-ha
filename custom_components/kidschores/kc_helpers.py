# File: kc_helpers.py
"""KidsChores helper functions and shared logic."""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.auth.models import User
from homeassistant.helpers.label_registry import async_get
from datetime import datetime, date, timedelta

import homeassistant.util.dt as dt_util

from . import const

if TYPE_CHECKING:
    from .coordinator import KidsChoresDataCoordinator


# -------- Get Coordinator --------
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


# -------- Authorization for General Actions --------
async def is_user_authorized_for_global_action(
    hass: HomeAssistant,
    user_id: str,
    action: str,
) -> bool:
    """Check if the user is allowed to do a global action (penalty, reward, points adjust) that doesn't require a specific kid_id.

    By default:
      - Admin users => authorized
      - Everyone else => not authorized
    """
    if not user_id:
        return False  # no user context => not authorized

    user: User = await hass.auth.async_get_user(user_id)
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


# -------- Authorization for Kid-Specific Actions --------
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

    user: User = await hass.auth.async_get_user(user_id)
    if not user:
        const.LOGGER.warning("WARNING: Authorization: Invalid user ID '%s'", user_id)
        return False

    # Admin => automatically allowed
    if user.is_admin:
        return True

    # Allow non-admin users if they are registered as a parent in KidsChores.
    coordinator = _get_kidschores_coordinator(hass)
    if coordinator:
        for parent in coordinator.parents_data.values():
            if parent.get(const.DATA_PARENT_HA_USER_ID) == user.id:
                return True

    coordinator: KidsChoresDataCoordinator = _get_kidschores_coordinator(hass)
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


# ----------- Parse Points Adjustment Values -----------
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


# ------------------ Helper Functions ------------------
def get_first_kidschores_entry(hass: HomeAssistant) -> Optional[str]:
    """Retrieve the first KidsChores config entry ID."""
    domain_entries = hass.data.get(const.DOMAIN)
    if not domain_entries:
        return None
    return next(iter(domain_entries.keys()), None)


def get_kid_id_by_name(
    coordinator: KidsChoresDataCoordinator, kid_name: str
) -> Optional[str]:
    """Retrieve the kid_id for a given kid_name."""
    for kid_id, kid_info in coordinator.kids_data.items():
        if kid_info.get(const.DATA_KID_NAME) == kid_name:
            return kid_id
    return None


def get_kid_name_by_id(
    coordinator: KidsChoresDataCoordinator, kid_id: str
) -> Optional[str]:
    """Retrieve the kid_name for a given kid_id."""
    kid_info = coordinator.kids_data.get(kid_id)
    if kid_info:
        return kid_info.get(const.DATA_KID_NAME)
    return None


def get_chore_id_by_name(
    coordinator: KidsChoresDataCoordinator, chore_name: str
) -> Optional[str]:
    """Retrieve the chore_id for a given chore_name."""
    for chore_id, chore_info in coordinator.chores_data.items():
        if chore_info.get(const.DATA_CHORE_NAME) == chore_name:
            return chore_id
    return None


def get_reward_id_by_name(
    coordinator: KidsChoresDataCoordinator, reward_name: str
) -> Optional[str]:
    """Retrieve the reward_id for a given reward_name."""
    for reward_id, reward_info in coordinator.rewards_data.items():
        if reward_info.get(const.DATA_REWARD_NAME) == reward_name:
            return reward_id
    return None


def get_penalty_id_by_name(
    coordinator: KidsChoresDataCoordinator, penalty_name: str
) -> Optional[str]:
    """Retrieve the penalty_id for a given penalty_name."""
    for penalty_id, penalty_info in coordinator.penalties_data.items():
        if penalty_info.get(const.DATA_PENALTY_NAME) == penalty_name:
            return penalty_id
    return None


def get_badge_id_by_name(
    coordinator: KidsChoresDataCoordinator, badge_name: str
) -> Optional[str]:
    """Retrieve the badge_id for a given badge_name."""
    for badge_id, badges_info in coordinator.badges_data.items():
        if badges_info.get(const.DATA_BADGE_NAME) == badge_name:
            return badge_id
    return None


def get_bonus_id_by_name(
    coordinator: KidsChoresDataCoordinator, bonus_name: str
) -> Optional[str]:
    """Retrieve the bonus_id for a given bonus_name."""
    for bonus_id, bonus_info in coordinator.bonuses_data.items():
        if bonus_info.get(const.DATA_BONUS_NAME) == bonus_name:
            return bonus_id
    return None


def get_friendly_label(hass, label_name: str) -> str:
    """Retrieve the friendly name for a given label_name."""
    registry = async_get(hass)
    entries = registry.async_list_labels()
    label_entry = registry.async_get_label(label_name)
    return label_entry.name if label_entry else label_name


# ────────────────────────────────────────────────────────────────
# 🕒 Date & Time Helpers (Local, UTC, Parsing, Formatting)
# These functions provide reusable, timezone-safe utilities for:
# - Getting current date/time in local or ISO formats
# - Parsing date or datetime strings safely
# - Converting naive/local times to UTC
# - Supporting badge and chore scheduling logic
# ────────────────────────────────────────────────────────────────


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


def parse_datetime_to_utc(hass, dt_str: str) -> Optional[datetime]:
    """
    Parse a datetime string, apply timezone if naive, and convert to UTC.

    Returns:
        UTC-aware datetime object, or None if parsing fails.

    Example:
        "2025-04-07T14:30:00" → datetime.datetime(2025, 4, 7, 19, 30, tzinfo=UTC)
    """
    if not isinstance(dt_str, str):
        return None

    try:
        dt_obj = dt_util.parse_datetime(dt_str)
        if dt_obj is None:
            dt_obj = datetime.fromisoformat(dt_str)

        if dt_obj.tzinfo is None:
            local_tz = dt_util.get_time_zone(hass.config.time_zone)
            dt_obj = dt_obj.replace(tzinfo=local_tz)

        return dt_util.as_utc(dt_obj)
    except Exception:
        return None


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
    except Exception:
        return None
