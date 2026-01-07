# pyright: reportIncompatibleVariableOverride=false
# ^ Suppresses Pylance warnings about @property overriding @cached_property from base classes.
#   This is intentional: our entities compute dynamic values on each access,
#   so we use @property instead of @cached_property to avoid stale cached data.
"""Calendar platform for KidsChores integration.

Provides a read-only calendar view of chore due dates and schedule information.
"""

import datetime
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from . import const
from . import kc_helpers as kh

# Silver requirement: Parallel Updates
# Set to 0 (unlimited) for coordinator-based entities that don't poll
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the KidsChores calendar platform."""
    try:
        coordinator = hass.data[const.DOMAIN][entry.entry_id][const.COORDINATOR]
    except KeyError:
        const.LOGGER.error("Coordinator not found for entry %s", entry.entry_id)
        return

    calendar_show_period_days = entry.options.get(
        const.CONF_CALENDAR_SHOW_PERIOD, const.DEFAULT_CALENDAR_SHOW_PERIOD
    )
    calendar_duration = datetime.timedelta(days=calendar_show_period_days)

    entities = []
    for kid_id, kid_info in coordinator.kids_data.items():
        kid_name = kid_info.get(
            const.DATA_KID_NAME, f"{const.TRANS_KEY_LABEL_KID} {kid_id}"
        )
        entities.append(
            KidScheduleCalendar(coordinator, kid_id, kid_name, entry, calendar_duration)
        )
    async_add_entities(entities)


class KidScheduleCalendar(CalendarEntity):
    """Calendar entity representing a kid's combined chores + challenges."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_CALENDAR_NAME

    def __init__(
        self, coordinator, kid_id: str, kid_name: str, config_entry, calendar_duration
    ):
        """Initialize the calendar entity.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access.
            kid_id: Unique identifier for the kid.
            kid_name: Display name of the kid.
            config_entry: ConfigEntry for this integration instance.
            calendar_duration: Duration (in days) for calendar event generation window.
        """
        super().__init__()
        self.coordinator = coordinator
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._config_entry = config_entry
        self._calendar_duration = calendar_duration
        self._attr_unique_id = (
            f"{config_entry.entry_id}_{kid_id}{const.CALENDAR_KC_UID_SUFFIX_CALENDAR}"
        )
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = f"{const.CALENDAR_KC_PREFIX}{kid_name}"
        self._attr_device_info = kh.create_kid_device_info(
            kid_id, kid_name, config_entry
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """
        Return CalendarEvent objects for:
         - chores assigned to this kid
         - challenges assigned to this kid
        overlapping [start_date, end_date].
        """
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=local_tz)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=local_tz)

        events: list[CalendarEvent] = []

        # 1) Generate chore events (filtered by show_on_calendar flag)
        for chore in self.coordinator.chores_data.values():
            # Skip chores not assigned to this kid
            if self._kid_id not in chore.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                continue

            # Skip chores with show_on_calendar set to False
            if not chore.get(const.DATA_CHORE_SHOW_ON_CALENDAR, True):
                continue

            events.extend(self._generate_events_for_chore(chore, start_date, end_date))

        # 2) Generate challenge events
        for challenge in self.coordinator.challenges_data.values():
            if self._kid_id in challenge.get(const.DATA_CHALLENGE_ASSIGNED_KIDS, []):
                evs = self._generate_events_for_challenge(
                    challenge, start_date, end_date
                )
                events.extend(evs)

        return events

    async def async_create_event(self, **kwargs) -> None:
        """Create a new event - not supported for read-only calendar."""
        raise HomeAssistantError(
            translation_domain=const.DOMAIN,
            translation_key=const.TRANS_KEY_ERROR_CALENDAR_CREATE_NOT_SUPPORTED,
        )

    async def async_delete_event(
        self,
        uid: str,
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        """Delete an event - not supported for read-only calendar."""
        raise HomeAssistantError(
            translation_domain=const.DOMAIN,
            translation_key=const.TRANS_KEY_ERROR_CALENDAR_DELETE_NOT_SUPPORTED,
        )

    async def async_update_event(
        self,
        uid: str,
        event: dict,
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        """Update an event - not supported for read-only calendar."""
        raise HomeAssistantError(
            translation_domain=const.DOMAIN,
            translation_key=const.TRANS_KEY_ERROR_CALENDAR_UPDATE_NOT_SUPPORTED,
        )

    def _event_overlaps_window(
        self,
        event: CalendarEvent,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> bool:
        """Check if event overlaps [window_start, window_end]."""
        sdt = event.start
        edt = event.end
        if isinstance(sdt, datetime.date) and not isinstance(sdt, datetime.datetime):
            tz = dt_util.get_time_zone(self.hass.config.time_zone)
            sdt = datetime.datetime.combine(sdt, datetime.time.min, tzinfo=tz)
        if isinstance(edt, datetime.date) and not isinstance(edt, datetime.datetime):
            tz = dt_util.get_time_zone(self.hass.config.time_zone)
            edt = datetime.datetime.combine(edt, datetime.time.min, tzinfo=tz)
        if not sdt or not edt:
            return False
        return (edt > window_start) and (sdt < window_end)

    def _add_event_if_overlaps(
        self,
        events: list[CalendarEvent],
        event: CalendarEvent,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> None:
        """Add event to list if it overlaps the window."""
        if self._event_overlaps_window(event, window_start, window_end):
            events.append(event)

    def _generate_non_recurring_with_due_date(
        self,
        events: list[CalendarEvent],
        summary: str,
        description: str,
        due_dt: datetime.datetime,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> None:
        """Generate event for non-recurring chore with due date."""
        if window_start <= due_dt <= window_end:
            # All chores with due_date create 1-hour timed events
            e = CalendarEvent(
                summary=summary,
                start=due_dt,
                end=due_dt + datetime.timedelta(hours=1),
                description=description,
            )
            self._add_event_if_overlaps(events, e, window_start, window_end)

    def _generate_non_recurring_without_due_date(
        self,
        events: list[CalendarEvent],
        summary: str,
        description: str,
        applicable_days: list[int],
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> None:
        """Generate events for non-recurring chore without due date on applicable days."""
        if not applicable_days:
            return

        gen_start = window_start
        gen_end = min(
            window_end,
            kh.get_now_local_time() + self._calendar_duration,
        )
        current = gen_start
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
        while current <= gen_end:
            if current.weekday() in applicable_days:
                # Create full-day event from 00:00:00 to 23:59:59 in local timezone
                day_start = datetime.datetime.combine(
                    current.date(), datetime.time(0, 0, 0), tzinfo=local_tz
                )
                day_end = datetime.datetime.combine(
                    current.date(), datetime.time(23, 59, 59), tzinfo=local_tz
                )
                e = CalendarEvent(
                    summary=summary,
                    start=day_start,
                    end=day_end,
                    description=description,
                )
                self._add_event_if_overlaps(events, e, window_start, window_end)
            current += datetime.timedelta(days=1)

    def _generate_recurring_daily_with_due_date(
        self,
        events: list[CalendarEvent],
        summary: str,
        description: str,
        due_dt: datetime.datetime,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> None:
        """Generate event for daily recurring chore with due date."""
        if window_start <= due_dt <= window_end:
            # All chores with due_date create 1-hour timed events
            e = CalendarEvent(
                summary=summary,
                start=due_dt,
                end=due_dt + datetime.timedelta(hours=1),
                description=description,
            )
            self._add_event_if_overlaps(events, e, window_start, window_end)

    def _generate_recurring_weekly_with_due_date(
        self,
        events: list[CalendarEvent],
        summary: str,
        description: str,
        due_dt: datetime.datetime,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> None:
        """Generate event for weekly recurring chore with due date."""
        start_event = due_dt - datetime.timedelta(weeks=1)
        end_event = due_dt
        if start_event < window_end and end_event > window_start:
            e = CalendarEvent(
                summary=summary,
                start=start_event.date(),
                end=(end_event.date() + datetime.timedelta(days=1)),
                description=description,
            )
            self._add_event_if_overlaps(events, e, window_start, window_end)

    def _generate_recurring_biweekly_with_due_date(
        self,
        events: list[CalendarEvent],
        summary: str,
        description: str,
        due_dt: datetime.datetime,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> None:
        """Generate event for biweekly recurring chore with due date."""
        start_event = due_dt - datetime.timedelta(weeks=2)
        end_event = due_dt
        if start_event < window_end and end_event > window_start:
            e = CalendarEvent(
                summary=summary,
                start=start_event.date(),
                end=(end_event.date() + datetime.timedelta(days=1)),
                description=description,
            )
            self._add_event_if_overlaps(events, e, window_start, window_end)

    def _generate_recurring_monthly_with_due_date(
        self,
        events: list[CalendarEvent],
        summary: str,
        description: str,
        due_dt: datetime.datetime,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> None:
        """Generate event for monthly recurring chore with due date."""
        first_day = due_dt.replace(day=1)
        if first_day < window_end and due_dt > window_start:
            e = CalendarEvent(
                summary=summary,
                start=first_day.date(),
                end=(due_dt.date() + datetime.timedelta(days=1)),
                description=description,
            )
            self._add_event_if_overlaps(events, e, window_start, window_end)

    def _generate_recurring_custom_with_due_date(
        self,
        events: list[CalendarEvent],
        summary: str,
        description: str,
        due_dt: datetime.datetime,
        interval: int,
        unit: str,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> None:
        """Generate event for custom interval recurring chore with due date."""
        if unit == const.TIME_UNIT_DAYS:
            start_event = due_dt - datetime.timedelta(days=interval)
        elif unit == const.TIME_UNIT_WEEKS:
            start_event = due_dt - datetime.timedelta(weeks=interval)
        elif unit == const.TIME_UNIT_MONTHS:
            start_event = due_dt - datetime.timedelta(days=30 * interval)
        else:
            start_event = due_dt

        if start_event < window_end and due_dt > window_start:
            e = CalendarEvent(
                summary=summary,
                start=start_event.date(),
                end=(due_dt.date() + datetime.timedelta(days=1)),
                description=description,
            )
            self._add_event_if_overlaps(events, e, window_start, window_end)

    def _generate_recurring_daily_without_due_date(
        self,
        events: list[CalendarEvent],
        summary: str,
        description: str,
        applicable_days: list[int],
        gen_start: datetime.datetime,
        cutoff: datetime.datetime,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> None:
        """Generate full-day events for daily recurring chore without due date."""
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
        current = gen_start
        while current <= cutoff:
            if applicable_days and current.weekday() not in applicable_days:
                current += datetime.timedelta(days=1)
                continue
            # Create full-day event from 00:00:00 to 23:59:59 in local timezone
            day_start = datetime.datetime.combine(
                current.date(), datetime.time(0, 0, 0), tzinfo=local_tz
            )
            day_end = datetime.datetime.combine(
                current.date(), datetime.time(23, 59, 59), tzinfo=local_tz
            )
            e = CalendarEvent(
                summary=summary,
                start=day_start,
                end=day_end,
                description=description,
            )
            self._add_event_if_overlaps(events, e, window_start, window_end)
            current += datetime.timedelta(days=1)

    def _generate_recurring_weekly_biweekly_without_due_date(
        self,
        events: list[CalendarEvent],
        summary: str,
        description: str,
        recurring: str,
        gen_start: datetime.datetime,
        cutoff: datetime.datetime,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> None:
        """Generate multi-day block events for weekly/biweekly recurring chore without due date."""
        week_delta = 7 if recurring == const.FREQUENCY_WEEKLY else 14
        current = gen_start
        # align to Monday
        while current.weekday() != 0:
            current += datetime.timedelta(days=1)
        while current <= cutoff:
            # multi-day block from Monday..Sunday (or 2 weeks for biweekly)
            block_days = 6 if recurring == const.FREQUENCY_WEEKLY else 13
            start_block = current
            end_block = current + datetime.timedelta(days=block_days)
            e = CalendarEvent(
                summary=summary,
                start=start_block.date(),
                end=end_block.date() + datetime.timedelta(days=1),
                description=description,
            )
            self._add_event_if_overlaps(events, e, window_start, window_end)
            current += datetime.timedelta(days=week_delta)

    def _generate_recurring_monthly_without_due_date(
        self,
        events: list[CalendarEvent],
        summary: str,
        description: str,
        gen_start: datetime.datetime,
        cutoff: datetime.datetime,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> None:
        """Generate full-month block events for monthly recurring chore without due date."""
        cur = gen_start
        while cur <= cutoff:
            first_day = cur.replace(day=1)
            next_month = first_day + datetime.timedelta(days=32)
            next_month = next_month.replace(day=1)
            last_day = next_month - datetime.timedelta(days=1)

            e = CalendarEvent(
                summary=summary,
                start=first_day.date(),
                end=last_day.date() + datetime.timedelta(days=1),
                description=description,
            )
            self._add_event_if_overlaps(events, e, window_start, window_end)
            cur = next_month

    def _generate_recurring_custom_without_due_date(
        self,
        events: list[CalendarEvent],
        summary: str,
        description: str,
        applicable_days: list[int],
        interval: int,
        unit: str,
        gen_start: datetime.datetime,
        cutoff: datetime.datetime,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> None:
        """Generate custom interval events for custom recurring chore without due date."""
        if unit == const.TIME_UNIT_DAYS:
            step = datetime.timedelta(days=interval)
        elif unit == const.TIME_UNIT_WEEKS:
            step = datetime.timedelta(weeks=interval)
        elif unit == const.TIME_UNIT_MONTHS:
            step = datetime.timedelta(days=30 * interval)
        else:
            step = datetime.timedelta(days=interval)

        current = gen_start
        while current <= cutoff:
            # Check applicable days
            if applicable_days and current.weekday() not in applicable_days:
                current += step
                continue
            e = CalendarEvent(
                summary=summary,
                start=current.date(),
                end=current.date() + step,
                description=description,
            )
            self._add_event_if_overlaps(events, e, window_start, window_end)
            current += step

    def _generate_events_for_chore(
        self,
        chore: dict,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Generate calendar events for a chore within the given time window.

        This method dispatches to specialized helper methods based on chore type:
        - Non-recurring: with/without due_date
        - Recurring with due_date: daily/weekly/biweekly/monthly/custom
        - Recurring without due_date: daily/weekly/biweekly/monthly/custom

        Args:
            chore: Chore dictionary with configuration data
            window_start: Start of calendar window
            window_end: End of calendar window

        Returns:
            List of CalendarEvent objects for this chore
        """
        events: list[CalendarEvent] = []

        summary = chore.get(
            const.DATA_CHORE_NAME, const.TRANS_KEY_DISPLAY_UNKNOWN_CHORE
        )
        description = chore.get(const.DATA_CHORE_DESCRIPTION, const.SENTINEL_EMPTY)
        recurring = chore.get(
            const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
        )
        applicable_days = chore.get(const.DATA_CHORE_APPLICABLE_DAYS, [])

        # Parse chore due_date using battle-tested helper
        # For INDEPENDENT chores, use per-kid due date; for SHARED, use chore-level
        completion_criteria = chore.get(
            const.DATA_CHORE_COMPLETION_CRITERIA, const.SENTINEL_EMPTY
        )
        if completion_criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
            per_kid_due_dates = chore.get(const.DATA_CHORE_PER_KID_DUE_DATES, {})
            due_date_str = per_kid_due_dates.get(self._kid_id)
        else:
            due_date_str = chore.get(const.DATA_CHORE_DUE_DATE)
        due_dt: datetime.datetime | None = None
        if due_date_str:
            parsed = kh.normalize_datetime_input(due_date_str)
            if isinstance(parsed, datetime.datetime):
                due_dt = parsed

        # --- Non-recurring chores ---
        if recurring == const.FREQUENCY_NONE:
            if due_dt:
                self._generate_non_recurring_with_due_date(
                    events, summary, description, due_dt, window_start, window_end
                )
            else:
                self._generate_non_recurring_without_due_date(
                    events,
                    summary,
                    description,
                    applicable_days,
                    window_start,
                    window_end,
                )
            return events

        # --- Recurring chores with a due_date ---
        if due_dt:
            cutoff = min(due_dt, window_end)
            if cutoff < window_start:
                return events

            if recurring == const.FREQUENCY_DAILY:
                self._generate_recurring_daily_with_due_date(
                    events, summary, description, due_dt, window_start, window_end
                )
            elif recurring == const.FREQUENCY_WEEKLY:
                self._generate_recurring_weekly_with_due_date(
                    events, summary, description, due_dt, window_start, window_end
                )
            elif recurring == const.FREQUENCY_BIWEEKLY:
                self._generate_recurring_biweekly_with_due_date(
                    events, summary, description, due_dt, window_start, window_end
                )
            elif recurring == const.FREQUENCY_MONTHLY:
                self._generate_recurring_monthly_with_due_date(
                    events, summary, description, due_dt, window_start, window_end
                )
            elif recurring == const.FREQUENCY_CUSTOM:
                interval = chore.get(const.DATA_CHORE_CUSTOM_INTERVAL, 1)
                unit = chore.get(
                    const.DATA_CHORE_CUSTOM_INTERVAL_UNIT, const.TIME_UNIT_DAYS
                )
                self._generate_recurring_custom_with_due_date(
                    events,
                    summary,
                    description,
                    due_dt,
                    interval,
                    unit,
                    window_start,
                    window_end,
                )
            return events

        # --- Recurring chores without a due_date => next 3 months
        gen_start = window_start
        future_limit = dt_util.as_local(
            datetime.datetime.now() + self._calendar_duration
        )
        cutoff = min(window_end, future_limit)

        if recurring == const.FREQUENCY_DAILY:
            self._generate_recurring_daily_without_due_date(
                events,
                summary,
                description,
                applicable_days,
                gen_start,
                cutoff,
                window_start,
                window_end,
            )
        elif recurring in (const.FREQUENCY_WEEKLY, const.FREQUENCY_BIWEEKLY):
            self._generate_recurring_weekly_biweekly_without_due_date(
                events,
                summary,
                description,
                recurring,
                gen_start,
                cutoff,
                window_start,
                window_end,
            )
        elif recurring == const.FREQUENCY_MONTHLY:
            self._generate_recurring_monthly_without_due_date(
                events,
                summary,
                description,
                gen_start,
                cutoff,
                window_start,
                window_end,
            )
        elif recurring == const.FREQUENCY_CUSTOM:
            interval = chore.get(const.DATA_CHORE_CUSTOM_INTERVAL, 1)
            unit = chore.get(
                const.DATA_CHORE_CUSTOM_INTERVAL_UNIT, const.TIME_UNIT_DAYS
            )
            self._generate_recurring_custom_without_due_date(
                events,
                summary,
                description,
                applicable_days,
                interval,
                unit,
                gen_start,
                cutoff,
                window_start,
                window_end,
            )

        return events

    def _generate_events_for_challenge(
        self,
        challenge: dict,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> list[CalendarEvent]:
        """
        Produce a single multi-day event for each challenge that has valid start_date/end_date.
        Only if it overlaps the requested [window_start, window_end].
        """
        events: list[CalendarEvent] = []

        challenge_name = challenge.get(
            const.DATA_CHALLENGE_NAME, const.TRANS_KEY_DISPLAY_UNKNOWN_CHALLENGE
        )
        description = challenge.get(
            const.DATA_CHALLENGE_DESCRIPTION, const.SENTINEL_EMPTY
        )
        start_str = challenge.get(const.DATA_CHALLENGE_START_DATE)
        end_str = challenge.get(const.DATA_CHALLENGE_END_DATE)
        if not start_str or not end_str:
            return events  # no valid date range => skip

        # Parse to local timezone directly
        local_start = kh.normalize_datetime_input(
            start_str,
            default_tzinfo=const.DEFAULT_TIME_ZONE,
            return_type=const.HELPER_RETURN_DATETIME_LOCAL,
        )
        local_end = kh.normalize_datetime_input(
            end_str,
            default_tzinfo=const.DEFAULT_TIME_ZONE,
            return_type=const.HELPER_RETURN_DATETIME_LOCAL,
        )
        if not local_start or not local_end:
            return events  # parsing failed => skip

        # If the challenge times are midnight-based, we can treat them as all-day.
        # But let's keep it simpler => always treat as an all-day block from date(start) to date(end)+1
        # so the user sees a big multi-day block.
        # Type guard: narrow datetime | date | str | None to datetime before comparisons and .date() calls
        if not isinstance(local_start, datetime.datetime) or not isinstance(
            local_end, datetime.datetime
        ):
            return events  # type check failed => skip
        if local_start > window_end or local_end < window_start:
            return events  # out of range

        # Build an all-day event from local_start.date() to local_end.date() + 1 day
        ev = CalendarEvent(
            summary=f"{const.TRANS_KEY_LABEL_CHALLENGE}: {challenge_name}",
            start=local_start.date(),
            end=local_end.date() + datetime.timedelta(days=1),
            description=description,
        )

        # Overlap check (similar logic):
        def overlaps(e: CalendarEvent) -> bool:
            sdt = e.start
            edt = e.end
            # convert if needed
            tz = dt_util.get_time_zone(self.hass.config.time_zone)
            if isinstance(sdt, datetime.date) and not isinstance(
                sdt, datetime.datetime
            ):
                sdt = datetime.datetime.combine(sdt, datetime.time.min, tzinfo=tz)
            if isinstance(edt, datetime.date) and not isinstance(
                edt, datetime.datetime
            ):
                edt = datetime.datetime.combine(edt, datetime.time.min, tzinfo=tz)
            return bool(sdt and edt and (edt > window_start) and (sdt < window_end))

        if overlaps(ev):
            events.append(ev)

        return events

    @property
    def event(self) -> CalendarEvent | None:
        """Return a single "current" event (chore or challenge) if one is active now (±1h)."""
        now = dt_util.as_local(dt_util.now())
        window_start = now - datetime.timedelta(hours=1)
        window_end = now + datetime.timedelta(hours=1)
        all_events = self._generate_all_events(window_start, window_end)
        for e in all_events:
            # Convert date->datetime for comparison
            tz = dt_util.get_time_zone(self.hass.config.time_zone)
            sdt = e.start
            edt = e.end
            if isinstance(sdt, datetime.date) and not isinstance(
                sdt, datetime.datetime
            ):
                sdt = datetime.datetime.combine(sdt, datetime.time.min, tzinfo=tz)
            if isinstance(edt, datetime.date) and not isinstance(
                edt, datetime.datetime
            ):
                edt = datetime.datetime.combine(edt, datetime.time.min, tzinfo=tz)
            if sdt and edt and sdt <= now < edt:
                return e
        return None

    def _generate_all_events(
        self, window_start: datetime.datetime, window_end: datetime.datetime
    ) -> list[CalendarEvent]:
        """Generate chores + challenges for this kid in the given window."""
        events = []
        # chores
        for chore in self.coordinator.chores_data.values():
            if self._kid_id in chore.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                events.extend(
                    self._generate_events_for_chore(chore, window_start, window_end)
                )
        # challenges
        for challenge in self.coordinator.challenges_data.values():
            if self._kid_id in challenge.get(const.DATA_CHALLENGE_ASSIGNED_KIDS, []):
                events.extend(
                    self._generate_events_for_challenge(
                        challenge, window_start, window_end
                    )
                )
        return events

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            const.ATTR_PURPOSE: const.TRANS_KEY_PURPOSE_CALENDAR_SCHEDULE,
            const.ATTR_KID_NAME: self._kid_name,
        }
