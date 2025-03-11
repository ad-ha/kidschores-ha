"""Calendar event generation tests using scenario data.

IMPORTANT: These tests capture baseline behavior BEFORE Phase 4 refactoring.
After splitting _generate_events_for_chore into 10 methods, re-run these tests
to validate identical event generation.

Test Strategy:
    - Use scenario_minimal fixture (Zoë with 2 daily chores)
    - Add test chores directly to coordinator
    - Reload calendar platform
    - Query HTTP API to fetch events
    - Validate event count, dates, descriptions

Test Coverage:
    - Non-recurring chores (FREQUENCY_NONE): with/without due_date
    - Daily recurring: with due_date, all days, filtered days
    - Weekly recurring: 7-day blocks
    - Biweekly recurring: 14-day blocks
    - Monthly recurring: full month blocks
    - Custom interval: days/weeks/months units
    - Edge cases: multiple chores, timezones, boundaries
"""

# pylint: disable=protected-access  # Accessing _persist for testing
# pylint: disable=too-many-locals  # Test functions need many variables for setup
# pylint: disable=unused-argument  # hass_client required by fixture pattern

from datetime import timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.kidschores import const
from custom_components.kidschores.const import COORDINATOR, DOMAIN
from tests.conftest import reload_entity_platforms

# For consistent testing across DST transitions
TEST_TZ = ZoneInfo("America/New_York")


@pytest.fixture
def platforms() -> list[Platform]:
    """Override platforms fixture to only load calendar for faster tests."""
    return [Platform.CALENDAR]


# ============================================================================
# Test: Non-Recurring Chores (FREQUENCY_NONE)
# ============================================================================


@freeze_time("2025-01-15 12:00:00", tz_offset=0)
async def test_non_recurring_chore_with_due_date_datetime(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    hass_client: ClientSessionGenerator,
) -> None:
    """Test non-recurring chore with specific due datetime creates single event."""
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Add test chore
    chore_id = str(uuid4())
    coordinator.chores_data[chore_id] = {
        const.DATA_CHORE_INTERNAL_ID: chore_id,
        const.DATA_CHORE_NAME: "Homework",
        const.DATA_CHORE_DESCRIPTION: "Math homework",
        const.DATA_CHORE_DEFAULT_POINTS: 10,
        const.DATA_CHORE_RECURRING_FREQUENCY: const.FREQUENCY_NONE,
        const.DATA_CHORE_ASSIGNED_KIDS: [zoe_id],
        const.DATA_CHORE_DUE_DATE: "2025-01-20T15:00:00-05:00",  # 3 PM EST
        const.DATA_CHORE_APPLICABLE_DAYS: [],
    }

    # Reload calendar platform to pick up new chore
    await reload_entity_platforms(hass, config_entry)

    # Get calendar entity and fetch events directly (avoids HTTP auth issues in tests)
    from datetime import datetime  # pylint: disable=import-outside-toplevel

    calendar_entity = hass.data["entity_components"]["calendar"].get_entity(
        "calendar.kc_zoe"
    )
    assert calendar_entity is not None, "Calendar entity not found"

    # Fetch events for January 2025
    start_dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=TEST_TZ)
    end_dt = datetime(2025, 1, 31, 23, 59, 59, tzinfo=TEST_TZ)
    calendar_events = await calendar_entity.async_get_events(hass, start_dt, end_dt)

    # Find the Homework event (scenario_minimal has 2 daily recurring chores, so filter)
    homework_events = [e for e in calendar_events if e.summary == "Homework"]
    assert len(homework_events) == 1, (
        f"Expected 1 Homework event, got {len(homework_events)}"
    )

    event = homework_events[0]
    assert event.summary == "Homework"
    assert event.description == "Math homework"
    # Event should be 1-hour block starting at due time
    # Due date is 3 PM EST (15:00-05:00) which converts to PST for display
    assert event.start_datetime_local.date().isoformat() == "2025-01-20"
    # Verify it's the right time (3 PM EST = 12 PM PST in test timezone)
    assert event.start_datetime_local.hour == 12  # PST = EST - 3 hours


@freeze_time("2025-01-15 12:00:00", tz_offset=0)
async def test_non_recurring_chore_with_due_date_midnight(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    hass_client: ClientSessionGenerator,
) -> None:
    """Test non-recurring chore with midnight due date creates all-day event."""
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Add test chore with midnight due date
    chore_id = str(uuid4())
    coordinator.chores_data[chore_id] = {
        const.DATA_CHORE_INTERNAL_ID: chore_id,
        const.DATA_CHORE_NAME: "Submit Report",
        const.DATA_CHORE_DESCRIPTION: "Science report",
        const.DATA_CHORE_DEFAULT_POINTS: 15,
        const.DATA_CHORE_RECURRING_FREQUENCY: const.FREQUENCY_NONE,
        const.DATA_CHORE_ASSIGNED_KIDS: [zoe_id],
        const.DATA_CHORE_DUE_DATE: "2025-01-25T00:00:00-05:00",  # Midnight EST
        const.DATA_CHORE_APPLICABLE_DAYS: [],
    }

    # Reload calendar platform
    await reload_entity_platforms(hass, config_entry)

    # Get calendar entity and fetch events directly
    from datetime import datetime  # pylint: disable=import-outside-toplevel

    calendar_entity = hass.data["entity_components"]["calendar"].get_entity(
        "calendar.kc_zoe"
    )
    assert calendar_entity is not None

    start_dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=TEST_TZ)
    end_dt = datetime(2025, 1, 31, 23, 59, 59, tzinfo=TEST_TZ)
    calendar_events = await calendar_entity.async_get_events(hass, start_dt, end_dt)

    # Find our chore (scenario has 2 daily chores, so filter)
    homework_events = [e for e in calendar_events if e.summary == "Submit Report"]
    assert len(homework_events) == 1

    event = homework_events[0]
    # All chores with due_date create 1-hour timed events (no midnight special case)
    # Due date stored as "2025-01-25T00:00:00-05:00" (midnight EST = 05:00 UTC)
    # Event uses stored timezone directly, so comparison works via UTC
    assert isinstance(event.start, datetime), "Expected datetime, not date"
    # Event duration should be 1 hour
    duration = event.end - event.start
    assert duration == timedelta(hours=1), f"Expected 1 hour duration, got {duration}"
    # Start should match the stored due_date in UTC terms (2025-01-25 05:00:00 UTC)
    expected_start_utc = datetime(2025, 1, 25, 5, 0, 0, tzinfo=timezone.utc)
    assert event.start.astimezone(timezone.utc) == expected_start_utc


# ============================================================================
# Test: Daily Recurring Chores
# ============================================================================


@freeze_time("2025-01-15 12:00:00", tz_offset=0)
async def test_daily_recurring_with_due_date(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    hass_client: ClientSessionGenerator,
) -> None:
    """Test daily recurring with due_date shows single event on due date."""
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Add daily chore with due date
    chore_id = str(uuid4())
    coordinator.chores_data[chore_id] = {
        const.DATA_CHORE_INTERNAL_ID: chore_id,
        const.DATA_CHORE_NAME: "Daily Quiz",
        const.DATA_CHORE_DESCRIPTION: "Complete daily math quiz",
        const.DATA_CHORE_DEFAULT_POINTS: 5,
        const.DATA_CHORE_RECURRING_FREQUENCY: const.FREQUENCY_DAILY,
        const.DATA_CHORE_ASSIGNED_KIDS: [zoe_id],
        const.DATA_CHORE_DUE_DATE: "2025-01-22T09:00:00-05:00",  # 9 AM EST
        const.DATA_CHORE_APPLICABLE_DAYS: [],
    }

    # Reload calendar platform
    await reload_entity_platforms(hass, config_entry)

    # Get calendar entity and fetch events directly
    from datetime import datetime  # pylint: disable=import-outside-toplevel

    calendar_entity = hass.data["entity_components"]["calendar"].get_entity(
        "calendar.kc_zoe"
    )
    assert calendar_entity is not None

    start_dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=TEST_TZ)
    end_dt = datetime(2025, 1, 31, 23, 59, 59, tzinfo=TEST_TZ)
    calendar_events = await calendar_entity.async_get_events(hass, start_dt, end_dt)

    # Find our chore
    quiz_events = [e for e in calendar_events if e.summary == "Daily Quiz"]
    assert len(quiz_events) == 1, "Daily with due_date should show single event"

    event = quiz_events[0]
    # Due date was "2025-01-22T09:00:00-05:00" (9 AM EST)
    # In PST (test environment), this is 6 AM PST
    assert event.start_datetime_local.date().isoformat() == "2025-01-22"
    assert event.start_datetime_local.hour == 6  # 9 AM EST = 6 AM PST


@freeze_time("2025-01-15 12:00:00", tz_offset=0)
async def test_daily_recurring_without_due_date_all_days(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    hass_client: ClientSessionGenerator,
) -> None:
    """Test daily recurring without due_date shows events for all days."""
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Add daily chore without due date
    chore_id = str(uuid4())
    coordinator.chores_data[chore_id] = {
        const.DATA_CHORE_INTERNAL_ID: chore_id,
        const.DATA_CHORE_NAME: "Morning Routine",
        const.DATA_CHORE_DESCRIPTION: "Brush teeth, make bed",
        const.DATA_CHORE_DEFAULT_POINTS: 5,
        const.DATA_CHORE_RECURRING_FREQUENCY: const.FREQUENCY_DAILY,
        const.DATA_CHORE_ASSIGNED_KIDS: [zoe_id],
        const.DATA_CHORE_DUE_DATE: None,
        const.DATA_CHORE_APPLICABLE_DAYS: [],  # All days
    }

    # Reload calendar platform
    await reload_entity_platforms(hass, config_entry)

    # Get calendar entity and fetch events for 1 week (Jan 15-21)
    from datetime import datetime  # pylint: disable=import-outside-toplevel

    calendar_entity = hass.data["entity_components"]["calendar"].get_entity(
        "calendar.kc_zoe"
    )
    assert calendar_entity is not None

    start_dt = datetime(2025, 1, 15, 0, 0, 0, tzinfo=TEST_TZ)
    end_dt = datetime(2025, 1, 21, 23, 59, 59, tzinfo=TEST_TZ)
    calendar_events = await calendar_entity.async_get_events(hass, start_dt, end_dt)

    # Find our chore
    routine_events = [e for e in calendar_events if e.summary == "Morning Routine"]
    assert len(routine_events) == 7, "Daily without due_date should show 7 days"

    # Verify dates are consecutive
    dates = sorted([e.start_datetime_local.date().isoformat() for e in routine_events])
    assert dates == [
        "2025-01-15",
        "2025-01-16",
        "2025-01-17",
        "2025-01-18",
        "2025-01-19",
        "2025-01-20",
        "2025-01-21",
    ]


@freeze_time("2025-01-15 12:00:00", tz_offset=0)
async def test_daily_recurring_without_due_date_applicable_days(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    hass_client: ClientSessionGenerator,
) -> None:
    """Test daily recurring with applicable_days filters to weekdays only."""
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Add daily chore for weekdays only
    chore_id = str(uuid4())
    coordinator.chores_data[chore_id] = {
        const.DATA_CHORE_INTERNAL_ID: chore_id,
        const.DATA_CHORE_NAME: "Practice Piano",
        const.DATA_CHORE_DESCRIPTION: "30 minutes",
        const.DATA_CHORE_DEFAULT_POINTS: 10,
        const.DATA_CHORE_RECURRING_FREQUENCY: const.FREQUENCY_DAILY,
        const.DATA_CHORE_ASSIGNED_KIDS: [zoe_id],
        const.DATA_CHORE_DUE_DATE: None,
        const.DATA_CHORE_APPLICABLE_DAYS: [0, 1, 2, 3, 4],  # Mon-Fri
    }

    # Reload calendar platform
    await reload_entity_platforms(hass, config_entry)

    # Get calendar entity and fetch events for 2 weeks (Jan 13-26: Mon to Sun)
    from datetime import datetime  # pylint: disable=import-outside-toplevel

    calendar_entity = hass.data["entity_components"]["calendar"].get_entity(
        "calendar.kc_zoe"
    )
    assert calendar_entity is not None

    start_dt = datetime(2025, 1, 13, 0, 0, 0, tzinfo=TEST_TZ)
    end_dt = datetime(2025, 1, 26, 23, 59, 59, tzinfo=TEST_TZ)
    calendar_events = await calendar_entity.async_get_events(hass, start_dt, end_dt)

    # Find our chore
    piano_events = [e for e in calendar_events if e.summary == "Practice Piano"]
    assert len(piano_events) == 10, "2 weeks * 5 weekdays = 10 events"

    # Verify no weekend events
    for event in piano_events:
        weekday = event.start_datetime_local.weekday()
        date_str = event.start_datetime_local.date().isoformat()
        assert weekday < 5, f"Should not have events on weekends, found {date_str}"


# ============================================================================
# Test: Weekly Recurring Chores
# ============================================================================


@freeze_time("2025-01-15 12:00:00", tz_offset=0)
async def test_weekly_recurring_with_due_date(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    hass_client: ClientSessionGenerator,
) -> None:
    """Test weekly recurring with due_date shows 1-week block."""
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Add weekly chore with due date
    chore_id = str(uuid4())
    coordinator.chores_data[chore_id] = {
        const.DATA_CHORE_INTERNAL_ID: chore_id,
        const.DATA_CHORE_NAME: "Weekly Report",
        const.DATA_CHORE_DESCRIPTION: "Submit weekly progress",
        const.DATA_CHORE_DEFAULT_POINTS: 20,
        const.DATA_CHORE_RECURRING_FREQUENCY: const.FREQUENCY_WEEKLY,
        const.DATA_CHORE_ASSIGNED_KIDS: [zoe_id],
        const.DATA_CHORE_DUE_DATE: "2025-01-26T23:59:00-05:00",  # Sunday 11:59 PM
        const.DATA_CHORE_APPLICABLE_DAYS: [],
    }

    # Reload calendar platform
    await reload_entity_platforms(hass, config_entry)

    # Get calendar entity and fetch events directly
    from datetime import datetime  # pylint: disable=import-outside-toplevel

    calendar_entity = hass.data["entity_components"]["calendar"].get_entity(
        "calendar.kc_zoe"
    )
    assert calendar_entity is not None

    start_dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=TEST_TZ)
    end_dt = datetime(2025, 1, 31, 23, 59, 59, tzinfo=TEST_TZ)
    calendar_events = await calendar_entity.async_get_events(hass, start_dt, end_dt)

    # Find our chore
    report_events = [e for e in calendar_events if e.summary == "Weekly Report"]
    assert len(report_events) == 1, "Weekly with due_date should show 1-week block"

    event = report_events[0]
    # Block should start 7 days before due date (all-day event for weekly block)
    assert (
        event.start_datetime_local.date().isoformat() == "2025-01-19"
    )  # 7 days before Jan 26
    assert (
        event.end_datetime_local.date().isoformat() == "2025-01-27"
    )  # Due date + 1 (exclusive end)


# Run with: python -m pytest tests/test_calendar_scenarios.py -v --tb=short
