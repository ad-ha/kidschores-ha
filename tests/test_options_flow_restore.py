"""Tests for KidsChores options flow restore functionality.

This test suite validates the restore-from-backup options available in the
general options menu for existing users. Tests cover:
- Restoring from specific backup file
- Starting fresh (backup current and delete)
- Pasting JSON from diagnostics
- Entity reload after restore
"""

# pylint: disable=redefined-outer-name  # Pytest fixtures shadow names

import json
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    CFOF_BACKUP_ACTION_SELECTION,
    CFOF_DATA_RECOVERY_INPUT_JSON_DATA,
    CFOF_DATA_RECOVERY_INPUT_SELECTION,
    OPTIONS_FLOW_GENERAL_OPTIONS,
    OPTIONS_FLOW_INPUT_MENU_SELECTION,
    OPTIONS_FLOW_STEP_BACKUP_ACTIONS,
    OPTIONS_FLOW_STEP_INIT,
    OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS,
    OPTIONS_FLOW_STEP_PASTE_JSON_RESTORE,
    OPTIONS_FLOW_STEP_SELECT_BACKUP_TO_RESTORE,
)

# Production JSON sample (Zoë with UTF-8 characters)
PRODUCTION_JSON_DATA = {
    "schema_version": 42,
    "kids": {
        "kid-1": {
            "internal_id": "kid-1",
            "name": "Zoë",
            "points": 100.0,
            "point_stats": {"points_net_all_time": 500.0},
            "badges_earned": {},
            "claimed_chores": [],
            "approved_chores": [],
            "ha_user_id": "",
            "enable_notifications": True,
            "mobile_notify_service": "",
            "use_persistent_notifications": True,
            "dashboard_language": "en",
        },
    },
    "chores": {
        "chore-1": {
            "internal_id": "chore-1",
            "name": "Feed the cåts",
            "points": 10.0,
            "assigned_kids": ["kid-1"],
            "due_date": "2025-12-31T23:59:00+00:00",
            "frequency": "daily",
            "is_recurring": True,
            "shared_by_kids": False,
            "multi_claimable": False,
            "badges": [],
            "description": "",
            "start_from_zero": False,
        },
    },
    "rewards": [],
    "badges": [],
    "bonuses": [],
    "penalties": [],
    "parents": [],
    "achievements": [],
    "challenges": [],
}


async def test_options_flow_restore_menu_navigation(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test navigating to general options shows restore option."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

    # Navigate to general options
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS


async def test_options_flow_restore_backup_navigation(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that selecting restore_backup navigates to restore menu."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to general options
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )

    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS

    # Select restore_backup action
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_BACKUP_ACTION_SELECTION: "restore_backup"},
    )

    # Should navigate to select backup to restore menu
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_SELECT_BACKUP_TO_RESTORE


@pytest.mark.skip(
    reason="paste_json option not available in select_backup_to_restore step - "
    "tests designed for deprecated restore_from_options flow"
)
async def test_options_flow_paste_json_option_available(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that paste JSON option is available in restore menu."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to restore backup menu
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_BACKUP_ACTION_SELECTION: "restore_backup"},
    )

    assert result.get("step_id") == OPTIONS_FLOW_STEP_SELECT_BACKUP_TO_RESTORE

    # Select paste_json from the restore menu
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_DATA_RECOVERY_INPUT_SELECTION: "paste_json"},
    )

    # Should navigate to paste JSON form
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_PASTE_JSON_RESTORE


@pytest.mark.skip(
    reason="paste_json option not available in select_backup_to_restore step - "
    "tests designed for deprecated restore_from_options flow"
)
async def test_options_flow_paste_json_empty_shows_error(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that pasting empty JSON shows error."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to paste JSON form
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_BACKUP_ACTION_SELECTION: "restore_backup"},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_DATA_RECOVERY_INPUT_SELECTION: "paste_json"},
    )

    # Try to submit empty JSON
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_DATA_RECOVERY_INPUT_JSON_DATA: ""},
    )

    # Should show error and stay on same form
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_PASTE_JSON_RESTORE
    assert "errors" in result


@pytest.mark.skip(
    reason="paste_json option not available in select_backup_to_restore step - "
    "tests designed for deprecated restore_from_options flow"
)
async def test_options_flow_paste_invalid_json_shows_error(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that pasting invalid JSON shows error."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to paste JSON form
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_BACKUP_ACTION_SELECTION: "restore_backup"},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_DATA_RECOVERY_INPUT_SELECTION: "paste_json"},
    )

    # Try to submit invalid JSON
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_DATA_RECOVERY_INPUT_JSON_DATA: "{ invalid json }"},
    )

    # Should show error
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_PASTE_JSON_RESTORE
    assert "errors" in result


@pytest.mark.skip(
    reason="paste_json option not available in select_backup_to_restore step - "
    "tests designed for deprecated restore_from_options flow"
)
async def test_options_flow_paste_json_with_diagnostic_format(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that pasting JSON in diagnostic format (with home_assistant wrapper) works."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to paste JSON form
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_BACKUP_ACTION_SELECTION: "restore_backup"},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_DATA_RECOVERY_INPUT_SELECTION: "paste_json"},
    )

    # Paste JSON in diagnostic format
    diagnostic_json = {
        "home_assistant": {
            "version": "2026.1.0",
        },
        "data": PRODUCTION_JSON_DATA,
    }

    with patch("asyncio.sleep"):  # Speed up test
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input={
                CFOF_DATA_RECOVERY_INPUT_JSON_DATA: json.dumps(diagnostic_json)
            },
        )

    # Should return to init after successful import
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


@pytest.mark.skip(
    reason="paste_json option not available in select_backup_to_restore step - "
    "tests designed for deprecated restore_from_options flow"
)
async def test_options_flow_paste_json_with_store_format(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that pasting JSON in Store format (v3.0/3.1/4.0beta1) works."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to paste JSON form
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_BACKUP_ACTION_SELECTION: "restore_backup"},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_DATA_RECOVERY_INPUT_SELECTION: "paste_json"},
    )

    # Paste JSON in Store format
    store_json = {"version": 1, "data": PRODUCTION_JSON_DATA}

    with patch("asyncio.sleep"):  # Speed up test
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input={CFOF_DATA_RECOVERY_INPUT_JSON_DATA: json.dumps(store_json)},
        )

    # Should return to init
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


@pytest.mark.skip(
    reason="start_fresh option not available in select_backup_to_restore step - "
    "tests designed for deprecated restore_from_options flow"
)
async def test_options_flow_start_fresh_navigation(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that selecting start_fresh navigates and completes."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to restore backup menu
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_BACKUP_ACTION_SELECTION: "restore_backup"},
    )

    # Select start_fresh
    with patch("asyncio.sleep"):  # Speed up test
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input={CFOF_DATA_RECOVERY_INPUT_SELECTION: "start_fresh"},
        )

    # Should return to init
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


@pytest.mark.skip(
    reason="start_fresh option not available in select_backup_to_restore step - "
    "tests designed for deprecated restore_from_options flow"
)
async def test_options_flow_start_fresh_works(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that start fresh completes successfully."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to restore backup menu
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_BACKUP_ACTION_SELECTION: "restore_backup"},
    )

    # Select start_fresh option - should complete successfully
    with patch("asyncio.sleep"):  # Speed up test
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input={CFOF_DATA_RECOVERY_INPUT_SELECTION: "start_fresh"},
        )

    # Should return to init after start_fresh completes
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_restore_cancel_returns_to_menu(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that selecting cancel returns to backup menu without making changes."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to general options
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS

    # Select restore_backup action to navigate to restore menu
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_BACKUP_ACTION_SELECTION: "restore_backup"},
    )
    assert result.get("step_id") == OPTIONS_FLOW_STEP_SELECT_BACKUP_TO_RESTORE

    # Select cancel option
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_DATA_RECOVERY_INPUT_SELECTION: "cancel"},
    )

    # Should return to backup_actions_menu form
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_BACKUP_ACTIONS


async def test_options_flow_restore_cancel_shows_cancel_option(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that cancel option is available in restore menu."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to restore backup menu
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_BACKUP_ACTION_SELECTION: "restore_backup"},
    )

    assert result.get("step_id") == OPTIONS_FLOW_STEP_SELECT_BACKUP_TO_RESTORE

    # Check that description/form data includes mention of cancel
    # The form should have the schema with cancel as an option
    # We verify by attempting to submit the cancel option and checking it's accepted
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_DATA_RECOVERY_INPUT_SELECTION: "cancel"},
    )

    # Cancel should be accepted and return to backup_actions_menu
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_BACKUP_ACTIONS
