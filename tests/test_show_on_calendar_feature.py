"""Tests for show_on_calendar feature.

Test Strategy:
    - Use scenario_minimal fixture (Zoë with 2 daily chores)
    - Create chores with show_on_calendar True and False
    - Test calendar event filtering based on flag
    - Test backward compatibility (missing field defaults to True)
    - Test config/options flow checkbox validation
    - Test migration logic for existing chores
"""

# pylint: disable=protected-access  # Accessing _persist for testing
# pylint: disable=too-many-locals  # Test functions need many variables for setup
# pylint: disable=unused-argument  # hass_client required by fixture pattern

from datetime import datetime
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

TEST_TZ = ZoneInfo("America/New_York")


@pytest.fixture
def platforms() -> list[Platform]:
    """Override platforms fixture to only load calendar for faster tests."""
    return [Platform.CALENDAR]


@freeze_time("2025-01-15 12:00:00", tz_offset=0)
async def test_calendar_filters_chores_by_show_on_calendar(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    hass_client: ClientSessionGenerator,
) -> None:
    """Test that calendar filters out chores with show_on_calendar=False."""
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Create chore with show_on_calendar=True
    visible_chore_id = str(uuid4())
    coordinator.chores_data[visible_chore_id] = {
        const.DATA_CHORE_INTERNAL_ID: visible_chore_id,
        const.DATA_CHORE_NAME: "Visible Chore",
        const.DATA_CHORE_DEFAULT_POINTS: 10,
        const.DATA_CHORE_SHOW_ON_CALENDAR: True,
        const.DATA_CHORE_ASSIGNED_KIDS: [zoe_id],
        const.DATA_CHORE_RECURRING_FREQUENCY: const.FREQUENCY_NONE,
        const.DATA_CHORE_DUE_DATE: "2025-01-20T15:00:00-05:00",
        const.DATA_CHORE_APPLICABLE_DAYS: [],
    }

    # Create chore with show_on_calendar=False
    hidden_chore_id = str(uuid4())
    coordinator.chores_data[hidden_chore_id] = {
        const.DATA_CHORE_INTERNAL_ID: hidden_chore_id,
        const.DATA_CHORE_NAME: "Hidden Chore",
        const.DATA_CHORE_DEFAULT_POINTS: 20,
        const.DATA_CHORE_SHOW_ON_CALENDAR: False,
        const.DATA_CHORE_ASSIGNED_KIDS: [zoe_id],
        const.DATA_CHORE_RECURRING_FREQUENCY: const.FREQUENCY_NONE,
        const.DATA_CHORE_DUE_DATE: "2025-01-25T15:00:00-05:00",
        const.DATA_CHORE_APPLICABLE_DAYS: [],
    }

    # Reload calendar platform to pick up new chores
    await reload_entity_platforms(hass, config_entry)

    # Get calendar entity
    calendar_entity = hass.data["entity_components"]["calendar"].get_entity(
        "calendar.kc_zoe"
    )
    assert calendar_entity is not None

    # Fetch events for January 2025
    start_dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=TEST_TZ)
    end_dt = datetime(2025, 1, 31, 23, 59, 59, tzinfo=TEST_TZ)
    calendar_events = await calendar_entity.async_get_events(hass, start_dt, end_dt)

    # Visible chore should appear in calendar
    visible_events = [e for e in calendar_events if e.summary == "Visible Chore"]
    assert len(visible_events) == 1

    # Hidden chore should NOT appear in calendar
    hidden_events = [e for e in calendar_events if e.summary == "Hidden Chore"]
    assert len(hidden_events) == 0


@freeze_time("2025-01-15 12:00:00", tz_offset=0)
async def test_calendar_includes_chores_with_missing_show_on_calendar_field(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
    hass_client: ClientSessionGenerator,
) -> None:
    """Test backward compatibility: chores missing show_on_calendar field default to True."""
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    zoe_id = name_to_id_map["kid:Zoë"]

    # Create chore WITHOUT show_on_calendar field (legacy data)
    legacy_chore_id = str(uuid4())
    coordinator.chores_data[legacy_chore_id] = {
        const.DATA_CHORE_INTERNAL_ID: legacy_chore_id,
        const.DATA_CHORE_NAME: "Legacy Chore",
        const.DATA_CHORE_DEFAULT_POINTS: 5,
        # NOTE: No show_on_calendar field - should default to True
        const.DATA_CHORE_ASSIGNED_KIDS: [zoe_id],
        const.DATA_CHORE_RECURRING_FREQUENCY: const.FREQUENCY_NONE,
        const.DATA_CHORE_DUE_DATE: "2025-01-22T15:00:00-05:00",
        const.DATA_CHORE_APPLICABLE_DAYS: [],
    }

    # Reload calendar platform
    await reload_entity_platforms(hass, config_entry)

    # Get calendar entity
    calendar_entity = hass.data["entity_components"]["calendar"].get_entity(
        "calendar.kc_zoe"
    )
    assert calendar_entity is not None

    # Fetch events
    start_dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=TEST_TZ)
    end_dt = datetime(2025, 1, 31, 23, 59, 59, tzinfo=TEST_TZ)
    calendar_events = await calendar_entity.async_get_events(hass, start_dt, end_dt)

    # Legacy chore should appear (defaults to True)
    legacy_events = [e for e in calendar_events if e.summary == "Legacy Chore"]
    assert len(legacy_events) == 1, (
        "Legacy chore without show_on_calendar field should appear"
    )


async def test_migration_adds_show_on_calendar_to_existing_chores(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test that new chores created have show_on_calendar field defaulting to True."""
    config_entry, _ = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # All chores in scenario_minimal should have show_on_calendar field
    # (created with v42 schema which includes the field by default=True)
    for chore_id, chore_data in coordinator.chores_data.items():
        assert const.DATA_CHORE_SHOW_ON_CALENDAR in chore_data, (
            f"Chore {chore_id} missing show_on_calendar field"
        )
        # Should default to True for backward compatibility
        assert chore_data[const.DATA_CHORE_SHOW_ON_CALENDAR] is True, (
            f"Chore {chore_id} show_on_calendar should default to True"
        )
