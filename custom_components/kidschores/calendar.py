# File: calendar.py

import datetime
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    FREQUENCY_BIWEEKLY,
    FREQUENCY_CUSTOM,
    FREQUENCY_DAILY,
    FREQUENCY_MONTHLY,
    FREQUENCY_NONE,
    FREQUENCY_WEEKLY,
    LOGGER,
    WEEKDAY_OPTIONS,
    ATTR_KID_NAME,
)

# Map weekday integers (0=Monday, …) to e.g. "mon","tue","wed" in WEEKDAY_OPTIONS.
WEEKDAY_MAP = {i: key for i, key in enumerate(WEEKDAY_OPTIONS.keys())}

# For chores without a due_date, we generate up to 3 months
FOREVER_DURATION = datetime.timedelta(days=90)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the KidsChores calendar platform."""
    try:
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    except KeyError:
        LOGGER.error("Coordinator not found in hass.data for entry %s", entry.entry_id)
        return

    entities = []
    for kid_id, kid_info in coordinator.kids_data.items():
        kid_name = kid_info.get("name", f"Kid {kid_id}")
        entities.append(KidsChoresCalendarEntity(coordinator, kid_id, kid_name, entry))
    async_add_entities(entities)


class KidsChoresCalendarEntity(CalendarEntity):
    """Calendar entity representing a kid's combined chores + challenges."""

    def __init__(self, coordinator, kid_id: str, kid_name: str, config_entry):
        super().__init__()
        self.coordinator = coordinator
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._config_entry = config_entry
        self._attr_name = f"KidsChores Calendar: {kid_name}"
        self._attr_unique_id = f"{config_entry.entry_id}_{kid_id}_calendar"
        self.entity_id = f"calendar.kc_{kid_name}"

    async def async_get_events(
        self, hass: HomeAssistant, start: datetime.datetime, end: datetime.datetime
    ) -> list[CalendarEvent]:
        """
        Return CalendarEvent objects for:
         - chores assigned to this kid
         - challenges assigned to this kid
        overlapping [start, end].
        """
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
        if start.tzinfo is None:
            start = start.replace(tzinfo=local_tz)
        if end.tzinfo is None:
            end = end.replace(tzinfo=local_tz)

        events: list[CalendarEvent] = []

        # 1) Generate chore events
        for chore in self.coordinator.chores_data.values():
            if self._kid_id in chore.get("assigned_kids", []):
                events.extend(self._generate_events_for_chore(chore, start, end))

        # 2) Generate challenge events
        for challenge in self.coordinator.challenges_data.values():
            if self._kid_id in challenge.get("assigned_kids", []):
                evs = self._generate_events_for_challenge(challenge, start, end)
                events.extend(evs)

        return events

    def _generate_events_for_chore(
        self,
        chore: dict,
        window_start: datetime.datetime,
        window_end: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Same recurring-chores logic from earlier solutions."""
        events: list[CalendarEvent] = []

        summary = chore.get("name", "Unnamed Chore")
        description = chore.get("description", "")
        recurring = chore.get("recurring_frequency", FREQUENCY_NONE)
        applicable_days = chore.get("applicable_days", [])

        # Parse chore due_date if any
        due_date_str = chore.get("due_date")
        due_dt: datetime.datetime | None = None
        if due_date_str:
            dt_parsed = dt_util.parse_datetime(due_date_str)
            if dt_parsed:
                due_dt = dt_util.as_local(dt_parsed)

        def is_midnight(dt_obj: datetime.datetime) -> bool:
            return (dt_obj.hour, dt_obj.minute, dt_obj.second) == (0, 0, 0)

        def overlaps(ev: CalendarEvent) -> bool:
            """Check if event overlaps [window_start, window_end]."""
            sdt = ev.start
            edt = ev.end
            if isinstance(sdt, datetime.date) and not isinstance(
                sdt, datetime.datetime
            ):
                tz = dt_util.get_time_zone(self.hass.config.time_zone)
                sdt = datetime.datetime.combine(sdt, datetime.time.min, tzinfo=tz)
            if isinstance(edt, datetime.date) and not isinstance(
                edt, datetime.datetime
            ):
                tz = dt_util.get_time_zone(self.hass.config.time_zone)
                edt = datetime.datetime.combine(edt, datetime.time.min, tzinfo=tz)
            if not sdt or not edt:
                return False
            return (edt > window_start) and (sdt < window_end)

        # --- Non-recurring chores ---
        if recurring == FREQUENCY_NONE:
            if due_dt:
                # single event if in window
                if window_start <= due_dt <= window_end:
                    if is_midnight(due_dt):
                        e = CalendarEvent(
                            summary=summary,
                            start=due_dt.date(),
                            end=due_dt.date() + datetime.timedelta(days=1),
                            description=description,
                        )
                    else:
                        e = CalendarEvent(
                            summary=summary,
                            start=due_dt,
                            end=due_dt + datetime.timedelta(hours=1),
                            description=description,
                        )
                    if overlaps(e):
                        events.append(e)
            else:
                # No due_date => possibly show on applicable_days for next 3 months
                if applicable_days:
                    gen_start = window_start
                    gen_end = min(
                        window_end,
                        dt_util.as_local(datetime.datetime.now() + FOREVER_DURATION),
                    )
                    current = gen_start
                    while current <= gen_end:
                        if WEEKDAY_MAP[current.weekday()] in applicable_days:
                            e = CalendarEvent(
                                summary=summary,
                                start=current.date(),
                                end=current.date() + datetime.timedelta(days=1),
                                description=description,
                            )
                            if overlaps(e):
                                events.append(e)
                        current += datetime.timedelta(days=1)

            return events

        # --- Recurring chores with a due_date ---
        if due_dt:
            cutoff = min(due_dt, window_end)
            if cutoff < window_start:
                return events

            if recurring == FREQUENCY_DAILY:
                if window_start <= due_dt <= window_end:
                    if is_midnight(due_dt):
                        e = CalendarEvent(
                            summary=summary,
                            start=due_dt.date(),
                            end=due_dt.date() + datetime.timedelta(days=1),
                            description=description,
                        )
                    else:
                        e = CalendarEvent(
                            summary=summary,
                            start=due_dt,
                            end=due_dt + datetime.timedelta(hours=1),
                            description=description,
                        )
                    if overlaps(e):
                        events.append(e)

            elif recurring == FREQUENCY_WEEKLY:
                start_event = due_dt - datetime.timedelta(weeks=1)
                end_event = due_dt
                if start_event < window_end and end_event > window_start:
                    e = CalendarEvent(
                        summary=summary,
                        start=start_event.date(),
                        end=(end_event.date() + datetime.timedelta(days=1)),
                        description=description,
                    )
                    if overlaps(e):
                        events.append(e)

            elif recurring == FREQUENCY_BIWEEKLY:
                start_event = due_dt - datetime.timedelta(weeks=2)
                end_event = due_dt
                if start_event < window_end and end_event > window_start:
                    e = CalendarEvent(
                        summary=summary,
                        start=start_event.date(),
                        end=(end_event.date() + datetime.timedelta(days=1)),
                        description=description,
                    )
                    if overlaps(e):
                        events.append(e)

            elif recurring == FREQUENCY_MONTHLY:
                first_day = due_dt.replace(day=1)
                if first_day < window_end and due_dt > window_start:
                    e = CalendarEvent(
                        summary=summary,
                        start=first_day.date(),
                        end=(due_dt.date() + datetime.timedelta(days=1)),
                        description=description,
                    )
                    if overlaps(e):
                        events.append(e)

            elif recurring == FREQUENCY_CUSTOM:
                interval = chore.get("custom_interval", 1)
                unit = chore.get("custom_interval_unit", "days")
                if unit == "days":
                    start_event = due_dt - datetime.timedelta(days=interval)
                elif unit == "weeks":
                    start_event = due_dt - datetime.timedelta(weeks=interval)
                elif unit == "months":
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
                    if overlaps(e):
                        events.append(e)

            return events

        # --- Recurring chores without a due_date => next 3 months
        gen_start = window_start
        future_limit = dt_util.as_local(datetime.datetime.now() + FOREVER_DURATION)
        cutoff = min(window_end, future_limit)

        if recurring == FREQUENCY_DAILY:
            current = gen_start
            while current <= cutoff:
                if (
                    applicable_days
                    and WEEKDAY_MAP[current.weekday()] not in applicable_days
                ):
                    current += datetime.timedelta(days=1)
                    continue
                e = CalendarEvent(
                    summary=summary,
                    start=current.date(),
                    end=current.date() + datetime.timedelta(days=1),
                    description=description,
                )
                if overlaps(e):
                    events.append(e)
                current += datetime.timedelta(days=1)
            return events

        if recurring in (FREQUENCY_WEEKLY, FREQUENCY_BIWEEKLY):
            week_delta = 7 if recurring == FREQUENCY_WEEKLY else 14
            current = gen_start
            # align to Monday
            while current.weekday() != 0:
                current += datetime.timedelta(days=1)
            while current <= cutoff:
                # multi-day block from Monday..Sunday (or 2 weeks for biweekly)
                block_days = 6 if recurring == FREQUENCY_WEEKLY else 13
                start_block = current
                end_block = current + datetime.timedelta(days=block_days)
                e = CalendarEvent(
                    summary=summary,
                    start=start_block.date(),
                    end=end_block.date() + datetime.timedelta(days=1),
                    description=description,
                )
                if overlaps(e):
                    events.append(e)
                current += datetime.timedelta(days=week_delta)
            return events

        if recurring == FREQUENCY_MONTHLY:
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
                if overlaps(e):
                    events.append(e)
                cur = next_month
            return events

        if recurring == FREQUENCY_CUSTOM:
            interval = chore.get("custom_interval", 1)
            unit = chore.get("custom_interval_unit", "days")
            if unit == "days":
                step = datetime.timedelta(days=interval)
            elif unit == "weeks":
                step = datetime.timedelta(weeks=interval)
            elif unit == "months":
                step = datetime.timedelta(days=30 * interval)
            else:
                step = datetime.timedelta(days=interval)

            current = gen_start
            while current <= cutoff:
                # Check applicable days
                if (
                    applicable_days
                    and WEEKDAY_MAP[current.weekday()] not in applicable_days
                ):
                    current += step
                    continue
                e = CalendarEvent(
                    summary=summary,
                    start=current.date(),
                    end=current.date() + step,
                    description=description,
                )
                if overlaps(e):
                    events.append(e)
                current += step
            return events

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

        challenge_name = challenge.get("name", "Unnamed Challenge")
        description = challenge.get("description", "")
        start_str = challenge.get("start_date")
        end_str = challenge.get("end_date")
        if not start_str or not end_str:
            return events  # no valid date range => skip

        start_dt = dt_util.parse_datetime(start_str)
        end_dt = dt_util.parse_datetime(end_str)
        if not start_dt or not end_dt:
            return events  # parsing failed => skip

        # Convert to local
        local_start = dt_util.as_local(start_dt)
        local_end = dt_util.as_local(end_dt)

        # If the challenge times are midnight-based, we can treat them as all-day.
        # But let's keep it simpler => always treat as an all-day block from date(start) to date(end)+1
        # so the user sees a big multi-day block.
        if local_start > window_end or local_end < window_start:
            return events  # out of range

        # Build an all-day event from local_start.date() to local_end.date() + 1 day
        ev = CalendarEvent(
            summary=f"Challenge: {challenge_name}",
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
        """
        Return a single "current" event (chore or challenge) if one is active now (±1h).
        Otherwise None.
        """
        now = dt_util.as_local(datetime.datetime.utcnow())
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
            if self._kid_id in chore.get("assigned_kids", []):
                events.extend(
                    self._generate_events_for_chore(chore, window_start, window_end)
                )
        # challenges
        for challenge in self.coordinator.challenges_data.values():
            if self._kid_id in challenge.get("assigned_kids", []):
                events.extend(
                    self._generate_events_for_challenge(
                        challenge, window_start, window_end
                    )
                )
        return events

    @property
    def extra_state_attributes(self):
        return {ATTR_KID_NAME: self._kid_name}
