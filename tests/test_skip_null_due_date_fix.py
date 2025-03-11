"""Test skip service behavior when due date is null for a kid in independent chore."""

# pylint: disable=protected-access
# pylint: disable=redefined-outer-name

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.kidschores import const


@pytest.mark.asyncio
async def test_skip_service_ignores_null_due_date(
    hass: HomeAssistant,
    scenario_minimal: tuple[ConfigEntry, dict[str, str]],
) -> None:
    """Test skip service does nothing when kid's due date is already null.

    Bug reproduction:
    1. Clear due date for a kid in an INDEPENDENT chore (set to null)
    2. Call skip service with that kid's name and chore name
    3. Service should ignore the request (no-op)
    4. per_kid_due_dates should still contain the kid_id with null value

    Before fix: Kid entry was deleted from per_kid_due_dates
    After fix: Kid entry preserved with null value, skip ignored
    """
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # Get test entities
    kid_id = name_to_id_map["kid:Zoë"]
    chore_id = name_to_id_map["chore:Feed the cåts"]

    # Get the chore and verify it's INDEPENDENT
    chore_info = coordinator.chores_data[chore_id]
    assert (
        chore_info.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        == const.COMPLETION_CRITERIA_INDEPENDENT
    )

    # Clear Zoë's due date (set to null)
    per_kid_due_dates = chore_info.get(const.DATA_CHORE_PER_KID_DUE_DATES, {})
    per_kid_due_dates[kid_id] = None
    chore_info[const.DATA_CHORE_PER_KID_DUE_DATES] = per_kid_due_dates
    coordinator._persist()

    # Verify the due date is null
    assert chore_info[const.DATA_CHORE_PER_KID_DUE_DATES][kid_id] is None

    # Call skip service - should be ignored since due date is null
    coordinator.skip_chore_due_date(chore_id, kid_id)

    # Verify kid entry still exists in per_kid_due_dates with null value
    assert kid_id in chore_info[const.DATA_CHORE_PER_KID_DUE_DATES]
    assert chore_info[const.DATA_CHORE_PER_KID_DUE_DATES][kid_id] is None

    # Verify no error was raised (function returned successfully)
    # If we got here, the test passed!


@pytest.mark.asyncio
async def test_skip_service_works_when_due_date_exists(
    hass: HomeAssistant,
    scenario_minimal: tuple[ConfigEntry, dict[str, str]],
) -> None:
    """Test skip service still works correctly when kid has a valid due date."""
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # Get test entities
    kid_id = name_to_id_map["kid:Zoë"]
    chore_id = name_to_id_map["chore:Feed the cåts"]

    # Get the chore
    chore_info = coordinator.chores_data[chore_id]

    # Set a valid due date for Zoë
    per_kid_due_dates = chore_info.get(const.DATA_CHORE_PER_KID_DUE_DATES, {})
    original_date = "2026-01-10T12:00:00+00:00"
    per_kid_due_dates[kid_id] = original_date
    chore_info[const.DATA_CHORE_PER_KID_DUE_DATES] = per_kid_due_dates
    coordinator._persist()

    # Call skip service - should advance the due date
    coordinator.skip_chore_due_date(chore_id, kid_id)

    # Verify the due date was advanced (not null, not the same)
    new_date = chore_info[const.DATA_CHORE_PER_KID_DUE_DATES][kid_id]
    assert new_date is not None
    assert new_date != original_date

    # Verify kid entry still exists
    assert kid_id in chore_info[const.DATA_CHORE_PER_KID_DUE_DATES]
