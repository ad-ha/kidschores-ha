# File: kc_helpers.py
"""KidsChores helper functions and shared logic."""

# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false, reportCallIssue=false, reportReturnType=false, reportOperatorIssue=false

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta, tzinfo
from typing import TYPE_CHECKING, Iterable, Optional, Union

import homeassistant.util.dt as dt_util
from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.helpers.label_registry import async_get

from . import const

if TYPE_CHECKING:
    from .coordinator import KidsChoresDataCoordinator  # Used for type checking only


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
    label_entry = registry.async_get_label(label_name)
    return label_entry.name if label_entry else label_name


# ────────────────────────────────────────────────────────────────
# 🧮 KidsChores Progress & Completion Helpers
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
    approved_chores = set(kid_info.get(const.DATA_KID_APPROVED_CHORES, []))
    overdue_chores = set(kid_info.get(const.DATA_KID_OVERDUE_CHORES, []))
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
            if due_date_iso and due_date_iso[:10] == today_iso:
                chores_due_today.append(chore_id)
        chores_to_check = chores_due_today
    else:
        chores_to_check = tracked_chores

    total_count = len(chores_to_check)
    if total_count == 0:
        return False, 0, 0

    # Count approved chores
    approved_count = sum(
        1 for chore_id in chores_to_check if chore_id in approved_chores
    )

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
            last_overdue_iso = chore_data.get(const.DATA_KID_CHORE_DATA_LAST_OVERDUE)
            if last_overdue_iso and last_overdue_iso[:10] == today_iso:
                return False, approved_count, total_count
            if chore_id in overdue_chores:
                return False, approved_count, total_count

    return True, approved_count, total_count


# ────────────────────────────────────────────────────────────────
# 🕒 Date & Time Helpers (Local, UTC, Parsing, Formatting, Add Interval)
# These functions provide reusable, timezone-safe utilities for:
# - Getting current date/time in local or ISO formats
# - Parsing date or datetime strings safely
# - Converting naive/local times to UTC
# - Adding intervals to dates/datetimes (e.g., days, weeks, months, years)
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
        - const.CONF_MINUTES, const.CONF_HOURS, const.CONF_DAYS, const.CONF_WEEKS,
          const.CONF_MONTHS, const.CONF_QUARTERS, const.CONF_YEARS.
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
    # Debug flag - set to False to disable debug logging for this function
    DEBUG = False

    if DEBUG:
        const.LOGGER.debug(
            "DEBUG: Add Interval To DateTime - Helper called with base_date=%s, interval_unit=%s, delta=%s, end_of_period=%s, require_future=%s, reference_datetime=%s, return_type=%s",
            base_date,
            interval_unit,
            delta,
            end_of_period,
            require_future,
            reference_datetime,
            return_type,
        )

    # Handle the case where base_date is None
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
    if interval_unit == const.CONF_MINUTES:
        result = base_dt + timedelta(minutes=delta)
    elif interval_unit == const.CONF_HOURS:
        result = base_dt + timedelta(hours=delta)
    elif interval_unit == const.CONF_DAYS:
        result = base_dt + timedelta(days=delta)
    elif interval_unit == const.CONF_WEEKS:
        result = base_dt + timedelta(weeks=delta)
    elif interval_unit in {const.CONF_MONTHS, const.CONF_QUARTERS}:
        multiplier = 1 if interval_unit == const.CONF_MONTHS else 3
        total_months = base_dt.month - 1 + (delta * multiplier)
        year = int(base_dt.year + total_months // 12)
        month = int(total_months % 12 + 1)
        day = min(base_dt.day, monthrange(year, month)[1])
        result = base_dt.replace(year=year, month=month, day=day)
    elif interval_unit == const.CONF_YEARS:
        year = int(base_dt.year + delta)
        day = min(base_dt.day, monthrange(year, base_dt.month)[1])
        result = base_dt.replace(year=year, day=day)
    else:
        raise ValueError(f"Unsupported interval unit: {interval_unit}")

    # Adjust result to the end of the period, if specified.
    if end_of_period:
        if end_of_period == const.PERIOD_DAY_END:
            result = result.replace(hour=23, minute=59, second=0, microsecond=0)
        elif end_of_period == const.PERIOD_WEEK_END:
            # Assuming week ends on Sunday (weekday() returns 0 for Monday; Sunday is 6).
            days_until_sunday = (6 - result.weekday()) % 7
            result = (result + timedelta(days=days_until_sunday)).replace(
                hour=23, minute=59, second=0, microsecond=0
            )
        elif end_of_period == const.PERIOD_MONTH_END:
            last_day = monthrange(result.year, result.month)[1]
            result = result.replace(
                day=last_day, hour=23, minute=59, second=0, microsecond=0
            )
        elif end_of_period == const.PERIOD_QUARTER_END:
            # Calculate the last month of the current quarter.
            last_month_of_quarter = ((result.month - 1) // 3 + 1) * 3
            last_day = monthrange(result.year, last_month_of_quarter)[1]
            result = result.replace(
                month=last_month_of_quarter,
                day=last_day,
                hour=23,
                minute=59,
                second=0,
                microsecond=0,
            )
        elif end_of_period == const.PERIOD_YEAR_END:
            result = result.replace(
                month=12, day=31, hour=23, minute=59, second=0, microsecond=0
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
        max_iterations = 1000  # Safety limit
        iteration_count = 0

        while result_utc <= reference_dt_utc and iteration_count < max_iterations:
            iteration_count += 1
            if DEBUG:
                const.LOGGER.debug(
                    "DEBUG: Add Interval To DateTime - Iteration %d, result=%s <= reference=%s",
                    iteration_count,
                    result_utc,
                    reference_dt_utc,
                )

            previous_result = result  # Store before calculating new interval

            # Add the interval again
            if interval_unit == const.CONF_MINUTES:
                result = result + timedelta(minutes=delta)
            elif interval_unit == const.CONF_HOURS:
                result = result + timedelta(hours=delta)
            elif interval_unit == const.CONF_DAYS:
                result = result + timedelta(days=delta)
            elif interval_unit == const.CONF_WEEKS:
                result = result + timedelta(weeks=delta)
            elif interval_unit in {const.CONF_MONTHS, const.CONF_QUARTERS}:
                multiplier = 1 if interval_unit == const.CONF_MONTHS else 3
                total_months = result.month - 1 + (delta * multiplier)
                year = result.year + total_months // 12
                month = total_months % 12 + 1
                day = min(result.day, monthrange(year, month)[1])
                result = result.replace(year=year, month=month, day=day)
            elif interval_unit == const.CONF_YEARS:
                year = result.year + delta
                day = min(result.day, monthrange(year, result.month)[1])
                result = result.replace(year=year, day=day)

            # Re-apply end_of_period if needed
            if end_of_period:
                if end_of_period == const.PERIOD_DAY_END:
                    result = result.replace(hour=23, minute=59, second=0, microsecond=0)
                elif end_of_period == const.PERIOD_WEEK_END:
                    days_until_sunday = (6 - result.weekday()) % 7
                    result = (result + timedelta(days=days_until_sunday)).replace(
                        hour=23, minute=59, second=0, microsecond=0
                    )
                elif end_of_period == const.PERIOD_MONTH_END:
                    last_day = monthrange(result.year, result.month)[1]
                    result = result.replace(
                        day=last_day, hour=23, minute=59, second=0, microsecond=0
                    )
                elif end_of_period == const.PERIOD_QUARTER_END:
                    last_month_of_quarter = ((result.month - 1) // 3 + 1) * 3
                    last_day = monthrange(result.year, last_month_of_quarter)[1]
                    result = result.replace(
                        month=last_month_of_quarter,
                        day=last_day,
                        hour=23,
                        minute=59,
                        second=0,
                        microsecond=0,
                    )
                elif end_of_period == const.PERIOD_YEAR_END:
                    result = result.replace(
                        month=12, day=31, hour=23, minute=59, second=0, microsecond=0
                    )

            # Check if we're in a loop (result didn't change)
            if result == previous_result:
                if DEBUG:
                    const.LOGGER.debug(
                        "DEBUG: Add Interval To DateTime - Detected loop! Result didn't change. Adding 1 hour to break the loop."
                    )
                # Break the loop by adding 1 hour
                result = result + timedelta(hours=1)

            result_utc = dt_util.as_utc(result)

            if iteration_count >= max_iterations:
                const.LOGGER.warning(
                    "WARN: Add Interval To DateTime - Maximum iterations (%d) reached! "
                    "Params: base_date=%s, interval_unit=%s, delta=%s, reference_datetime=%s",
                    max_iterations,
                    base_dt,
                    interval_unit,
                    delta,
                    reference_dt,
                )

        if DEBUG and iteration_count > 0:
            const.LOGGER.debug(
                "DEBUG: Add Interval To DateTime - After %d iterations, final result=%s",
                iteration_count,
                result,
            )

    # Use format_datetime_with_return_type for consistent return formatting
    final_result = format_datetime_with_return_type(result, return_type)

    if DEBUG:
        const.LOGGER.debug(
            "DEBUG: Add Interval To DateTime - Final result: %s", final_result
        )

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
    # Debug flag - set to False to disable debug logging for this function
    DEBUG = False

    if DEBUG:
        const.LOGGER.debug(
            "DEBUG: Get Next Schedule DateTime - Helper called with base_date=%s, interval_type=%s, require_future=%s, reference_datetime=%s, return_type=%s",
            base_date,
            interval_type,
            require_future,
            reference_datetime,
            return_type,
        )

    # Handle the case where base_date is None
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
                const.CONF_DAYS,
                1,
                end_of_period=None,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type in {const.FREQUENCY_WEEKLY, const.FREQUENCY_CUSTOM_1_WEEK}:
            return adjust_datetime_by_interval(
                base_dt,
                const.CONF_WEEKS,
                1,
                end_of_period=None,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.FREQUENCY_BIWEEKLY:
            return adjust_datetime_by_interval(
                base_dt,
                const.CONF_WEEKS,
                2,
                end_of_period=None,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type in {const.FREQUENCY_MONTHLY, const.FREQUENCY_CUSTOM_1_MONTH}:
            return adjust_datetime_by_interval(
                base_dt,
                const.CONF_MONTHS,
                1,
                end_of_period=None,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.FREQUENCY_QUARTERLY:
            return adjust_datetime_by_interval(
                base_dt,
                const.CONF_QUARTERS,
                1,
                end_of_period=None,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type in {const.FREQUENCY_YEARLY, const.FREQUENCY_CUSTOM_1_YEAR}:
            return adjust_datetime_by_interval(
                base_dt,
                const.CONF_YEARS,
                1,
                end_of_period=None,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.PERIOD_DAY_END:
            return adjust_datetime_by_interval(
                base_dt,
                const.CONF_DAYS,
                0,
                end_of_period=const.PERIOD_DAY_END,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.PERIOD_WEEK_END:
            return adjust_datetime_by_interval(
                base_dt,
                const.CONF_DAYS,
                0,
                end_of_period=const.PERIOD_WEEK_END,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.PERIOD_MONTH_END:
            return adjust_datetime_by_interval(
                base_dt,
                const.CONF_DAYS,
                0,
                end_of_period=const.PERIOD_MONTH_END,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.PERIOD_QUARTER_END:
            return adjust_datetime_by_interval(
                base_dt,
                const.CONF_DAYS,
                0,
                end_of_period=const.PERIOD_QUARTER_END,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        elif interval_type == const.PERIOD_YEAR_END:
            return adjust_datetime_by_interval(
                base_dt,
                const.CONF_DAYS,
                0,
                end_of_period=const.PERIOD_YEAR_END,
                return_type=const.HELPER_RETURN_DATETIME,
            )
        else:
            raise ValueError(f"Unsupported interval type: {interval_type}")

    # Calculate the initial next scheduled datetime.
    result = calculate_next_interval(base_dt)
    if DEBUG:
        const.LOGGER.debug(
            "DEBUG: Get Next Schedule DateTime - After calculate_next_interval, result=%s",
            result,
        )

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
        max_iterations = 1000  # Safety limit
        iteration_count = 0

        while result_utc <= reference_dt_utc and iteration_count < max_iterations:
            iteration_count += 1
            if DEBUG:
                const.LOGGER.debug(
                    "DEBUG: Get Next Schedule DateTime - Iteration %d, result=%s <= reference=%s",
                    iteration_count,
                    result_utc,
                    reference_dt_utc,
                )

            previous_result = result  # Store before calculating new result
            temp_base = result  # We keep result in local time.
            result = calculate_next_interval(temp_base)

            # Check if we're in a loop (result didn't change as can happen with period ends)
            if result == previous_result:
                if DEBUG:
                    const.LOGGER.debug(
                        "DEBUG: Get Next Schedule DateTime - Detected loop! Result didn't change. Adding 1 hour to break the loop."
                    )
                # Break the loop by adding 1 hour and recalculating
                result = adjust_datetime_by_interval(
                    result,
                    const.CONF_HOURS,
                    1,
                    end_of_period=None,
                    return_type=const.HELPER_RETURN_DATETIME,
                )
                result = calculate_next_interval(result)

            result_utc = dt_util.as_utc(result)

            if iteration_count >= max_iterations:
                const.LOGGER.warning(
                    "WARN: Get Next Schedule DateTime - Maximum iterations (%d) reached! "
                    "Params: base_date=%s, interval_type=%s, reference_datetime=%s",
                    max_iterations,
                    base_date,
                    interval_type,
                    reference_dt,
                )

        if DEBUG:
            const.LOGGER.debug(
                "DEBUG: Get Next Schedule DateTime - After %d iterations, final result=%s",
                iteration_count,
                result,
            )

    # Use format_datetime_with_return_type to handle the return type formatting
    final_result = format_datetime_with_return_type(result, return_type)

    if DEBUG:
        const.LOGGER.debug(
            "DEBUG: Get Next Schedule DateTime - Final result: %s", final_result
        )

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
    # Debug flag - set to False to disable debug logging for this function
    DEBUG = False

    local_tz = local_tz or const.DEFAULT_TIME_ZONE

    if DEBUG:
        # Debug logging for function entry
        const.LOGGER.debug(
            "DEBUG: HELPER Get Next Applicable Day - Helper called with dt=%s, applicable_days=%s, local_tz=%s, return_type=%s",
            dt,
            applicable_days,
            local_tz,
            return_type,
        )

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

    if DEBUG:
        # Debug logging for function exit
        const.LOGGER.debug(
            "DEBUG: HELPER Get Next Applicable Day - Final result: %s", final_result
        )

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
        interval_unit=const.CONF_DAYS,
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
        interval_unit=const.CONF_WEEKS,
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
        interval_unit=const.CONF_MONTHS,
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
