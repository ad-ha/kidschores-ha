# File: kc_helpers.py
"""KidsChores helper functions and shared logic."""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Union

from homeassistant.core import HomeAssistant
from homeassistant.auth.models import User
from homeassistant.helpers.label_registry import async_get
from datetime import datetime, date, timedelta, time
from calendar import monthrange
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


def add_interval_to_datetime(
    base_date: Union[str, date, datetime],
    interval_unit: str,
    amount: int,
    return_type: str = const.HELPER_RETURN_ISO_DATE,
) -> Union[str, date, datetime]:
    """
    Adds a time interval to a date or datetime and returns the result in the desired format.

    Parameters:
    - base_date: ISO string, datetime.date, or datetime.datetime
    - interval_unit: One of the defined const.CONF_* constants:
        - const.CONF_MINUTES, const.CONF_HOURS, const.CONF_DAYS, const.CONF_WEEKS,
          const.CONF_MONTHS, const.CONF_QUARTERS, const.CONF_YEARS
    - amount: Number of units to add
    - return_type: One of the const.HELPER_RETURN_* constants:
        - const.HELPER_RETURN_ISO_DATE: returns "YYYY-MM-DD"
        - const.HELPER_RETURN_ISO_DATETIME: returns "YYYY-MM-DDTHH:MM:SS"
        - const.HELPER_RETURN_DATE: returns datetime.date
        - const.HELPER_RETURN_DATETIME: returns datetime.datetime

    Notes:
    - Preserves timezone awareness if present in input.
    - If input is naive (no tzinfo), output will also be naive.
    """
    if isinstance(base_date, str):
        base_date = datetime.fromisoformat(base_date)
    elif isinstance(base_date, date) and not isinstance(base_date, datetime):
        base_date = datetime.combine(base_date, datetime.min.time())

    if interval_unit == const.CONF_MINUTES:
        result = base_date + timedelta(minutes=amount)
    elif interval_unit == const.CONF_HOURS:
        result = base_date + timedelta(hours=amount)
    elif interval_unit == const.CONF_DAYS:
        result = base_date + timedelta(days=amount)
    elif interval_unit == const.CONF_WEEKS:
        result = base_date + timedelta(weeks=amount)
    elif interval_unit in {const.CONF_MONTHS, const.CONF_QUARTERS}:
        multiplier = 1 if interval_unit == const.CONF_MONTHS else 3
        total_months = base_date.month - 1 + (amount * multiplier)
        year = base_date.year + total_months // 12
        month = total_months % 12 + 1
        day = min(base_date.day, monthrange(year, month)[1])
        result = base_date.replace(year=year, month=month, day=day)
    elif interval_unit == const.CONF_YEARS:
        year = base_date.year + amount
        day = min(base_date.day, monthrange(year, base_date.month)[1])
        result = base_date.replace(year=year, day=day)
    else:
        raise ValueError(f"Unsupported interval unit: {interval_unit}")

    if return_type == const.HELPER_RETURN_DATETIME:
        return result
    elif return_type == const.HELPER_RETURN_DATE:
        return result.date()
    elif return_type == const.HELPER_RETURN_ISO_DATETIME:
        return result.isoformat()
    return result.date().isoformat()  # Default to iso_date


def get_next_scheduled_datetime(
    start_date: Union[str, date, datetime],
    interval_type: str,
    return_type: str = const.HELPER_RETURN_DATE,
    require_future: bool = True,
    reference_datetime: Optional[Union[str, date, datetime]] = None,
) -> Union[date, datetime, str]:
    """
    Calculates the next scheduled datetime based on an interval type from a given start date.

    Supported interval types (using local timezone):
      - Daily:         const.CONF_DAILY
      - Weekly:        const.CONF_WEEKLY or const.CONF_CUSTOM_1_WEEK
      - Biweekly:      const.CONF_BIWEEKLY
      - Monthly:       const.CONF_MONTHLY or const.CONF_CUSTOM_1_MONTH
      - Quarterly:     const.CONF_QUARTERLY
      - Yearly:        const.CONF_YEARLY or const.CONF_CUSTOM_1_YEAR
      - Period-end types:
          - Day end:   const.CONF_DAY_END (sets time to 23:59:00)
          - Week end:  const.CONF_WEEK_END (advances to upcoming Sunday at 23:59:00)
          - Month end: const.CONF_MONTH_END (last day of the month at 23:59:00)
          - Quarter end: const.CONF_QUARTER_END (last day of quarter at 23:59:00)
          - Year end:  const.CONF_YEAR_END (December 31 at 23:59:00)

    Behavior:
      - Accepts a string, date, or datetime object for start_date.
      - For period-end types, the result time is set to 23:59:00.
      - For other types, the time portion from the input is preserved.
      - If require_future is True, the schedule is advanced until the resulting datetime is strictly after the given reference_datetime.
      - The reference_datetime (if provided) can be a string, date, or datetime; if omitted, the current local datetime is used.

    Examples:
      - get_next_scheduled_datetime("2025-04-07", const.CONF_MONTHLY)
          → datetime.date(2025, 5, 7)
      - get_next_scheduled_datetime("2025-04-07T09:00:00", const.CONF_WEEKLY, const.HELPER_RETURN_ISO_DATETIME)
          → "2025-04-14T09:00:00"
      - get_next_scheduled_datetime("2025-04-07", const.CONF_MONTH_END, const.HELPER_RETURN_ISO_DATETIME)
          → "2025-04-30T23:59:00"
      - get_next_scheduled_datetime("2024-06-01", const.CONF_CUSTOM_1_YEAR, require_future=True)
          → datetime.date(2025, 6, 1)
    """
    const.LOGGER.debug(
        "DEBUG: Get Next Schedule DateTime - Helper called with start_date=%s, interval_type=%s, return_type=%s, require_future=%s, reference_datetime=%s",
        start_date,
        interval_type,
        return_type,
        require_future,
        reference_datetime,
    )

    # Get the local timezone.
    local_tz = dt_util.as_local(dt_util.utcnow()).tzinfo

    # Convert start_date to a timezone-aware datetime if required
    if isinstance(start_date, str):
        dt_obj = parse_datetime_to_utc(None, start_date) or datetime.fromisoformat(
            start_date
        )
        # If the parsed datetime is naive, assign local timezone.
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=local_tz)
        start_date = dt_obj
    elif isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_date = datetime.combine(start_date, datetime.min.time()).replace(
            tzinfo=local_tz
        )
    else:
        # If start_date is already a datetime but might be naive, ensure it is tz-aware.
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=local_tz)

    # Determine if the interval type is an "end" type that sets the time to the end of day.
    is_end_type = interval_type.endswith("_end")
    # Preserve the original time from start_date if available; otherwise, use minimal time.
    time_part = start_date.timetz() if start_date.tzinfo else start_date.time()
    # Define the constant for the end-of-day time (23:59:00).
    end_time = time(23, 59, 0)

    def calculate_next(base_dt: datetime) -> datetime:
        """
        Calculate the next datetime based on the interval type using add_interval_to_datetime.
        """
        if interval_type in {const.CONF_DAILY}:
            # Daily increment: add 1 day.
            return add_interval_to_datetime(
                base_dt, const.CONF_DAYS, 1, const.HELPER_RETURN_DATETIME
            )
        elif interval_type in {const.CONF_WEEKLY, const.CONF_CUSTOM_1_WEEK}:
            # Weekly increment: add 1 week.
            return add_interval_to_datetime(
                base_dt, const.CONF_WEEKS, 1, const.HELPER_RETURN_DATETIME
            )
        elif interval_type == const.CONF_BIWEEKLY:
            # Biweekly increment: add 2 weeks.
            return add_interval_to_datetime(
                base_dt, const.CONF_WEEKS, 2, const.HELPER_RETURN_DATETIME
            )
        elif interval_type in {const.CONF_MONTHLY, const.CONF_CUSTOM_1_MONTH}:
            # Monthly increment: add 1 month.
            return add_interval_to_datetime(
                base_dt, const.CONF_MONTHS, 1, const.HELPER_RETURN_DATETIME
            )
        elif interval_type == const.CONF_QUARTERLY:
            # Quarterly increment: add 1 quarter (3 months).
            return add_interval_to_datetime(
                base_dt, const.CONF_QUARTERS, 1, const.HELPER_RETURN_DATETIME
            )
        elif interval_type in {const.CONF_YEARLY, const.CONF_CUSTOM_1_YEAR}:
            # Yearly increment: add 1 year.
            return add_interval_to_datetime(
                base_dt, const.CONF_YEARS, 1, const.HELPER_RETURN_DATETIME
            )
        elif interval_type == const.CONF_DAY_END:
            # For day_end, simply set the time to end of day (23:59:00) without changing the date.
            return base_dt.replace(hour=end_time.hour, minute=end_time.minute, second=0)
        elif interval_type == const.CONF_WEEK_END:
            # For week_end, advance to the upcoming Sunday and set the time to end of day.
            days_until_sunday = (6 - base_dt.weekday()) % 7
            dt_next = add_interval_to_datetime(
                base_dt,
                const.CONF_DAYS,
                days_until_sunday,
                const.HELPER_RETURN_DATETIME,
            )
            return dt_next.replace(hour=end_time.hour, minute=end_time.minute, second=0)
        elif interval_type == const.CONF_MONTH_END:
            # For month_end, set the day to the last day of the month and time to end of day.
            last_day = monthrange(base_dt.year, base_dt.month)[1]
            return base_dt.replace(
                day=last_day, hour=end_time.hour, minute=end_time.minute, second=0
            )
        elif interval_type == const.CONF_QUARTER_END:
            # For quarter_end, determine the last month of the current quarter and set time to end of day.
            next_q_month = ((base_dt.month - 1) // 3 + 1) * 3
            year = base_dt.year
            if next_q_month > 12:
                next_q_month = 12
            last_day = monthrange(year, next_q_month)[1]
            return base_dt.replace(
                month=next_q_month,
                day=last_day,
                hour=end_time.hour,
                minute=end_time.minute,
                second=0,
            )
        elif interval_type == const.CONF_YEAR_END:
            # For year_end, set to December 31 and time to end of day.
            return base_dt.replace(
                month=12, day=31, hour=end_time.hour, minute=end_time.minute, second=0
            )
        else:
            raise ValueError(f"Unsupported interval type: {interval_type}")

    # Calculate the initial next scheduled datetime.
    result = calculate_next(start_date)

    # Process the reference_datetime and ensure it is timezone-aware.
    if reference_datetime is not None:
        if isinstance(reference_datetime, str):
            try:
                reference_dt = datetime.fromisoformat(reference_datetime)
                if reference_dt.tzinfo is None:
                    reference_dt = reference_dt.replace(tzinfo=local_tz)
            except Exception:
                parsed_date = parse_date_safe(reference_datetime)
                if parsed_date:
                    reference_dt = datetime.combine(
                        parsed_date, datetime.min.time()
                    ).replace(tzinfo=local_tz)
                else:
                    reference_dt = dt_util.as_local(dt_util.utcnow())
        elif isinstance(reference_datetime, date) and not isinstance(
            reference_datetime, datetime
        ):
            reference_dt = datetime.combine(
                reference_datetime, datetime.min.time()
            ).replace(tzinfo=local_tz)
        elif isinstance(reference_datetime, datetime):
            if reference_datetime.tzinfo is None:
                reference_dt = reference_datetime.replace(tzinfo=local_tz)
            else:
                reference_dt = reference_datetime
        else:
            reference_dt = dt_util.as_local(dt_util.utcnow())
    else:
        reference_dt = dt_util.as_local(dt_util.utcnow())

    # Ensure both result and reference_dt are converted to UTC for a valid comparison.
    if result.tzinfo is None:
        result = result.replace(tzinfo=local_tz)
    result = dt_util.as_utc(result)
    reference_dt = dt_util.as_utc(reference_dt)

    # If require_future is True, loop until result is strictly after reference_dt.
    if require_future:
        while result <= reference_dt:
            start_date = result
            result = calculate_next(start_date)

    # For non "end" types, restore the original time part from the initial start_date.
    if not is_end_type:
        result = result.replace(
            hour=time_part.hour, minute=time_part.minute, second=time_part.second
        )

    # For non "end" types, restore the original time part from the initial start_date.
    if not is_end_type:
        result = result.replace(
            hour=time_part.hour, minute=time_part.minute, second=time_part.second
        )

    # Prepare final result based on requested return_type.
    if return_type == const.HELPER_RETURN_DATETIME:
        final_result = result
    elif return_type == const.HELPER_RETURN_DATE:
        final_result = result.date()
    elif return_type == const.HELPER_RETURN_ISO_DATETIME:
        final_result = result.isoformat()
    else:
        final_result = result.date().isoformat()

    # DEBUG CHANGE: Log the final result before returning.
    const.LOGGER.debug(
        "DEBUG: Get Next Schedule DateTime - Final result: %s", final_result
    )

    # Default to ISO date string.
    return final_result
