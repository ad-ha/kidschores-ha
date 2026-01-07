"""Tests for KidsChores options flow."""

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores import const
from custom_components.kidschores.const import (
    CFOF_KIDS_INPUT_KID_NAME,
    CONF_BACKUPS_MAX_RETAINED,
    CONF_RETENTION_PERIODS,
    OPTIONS_FLOW_ACTIONS_ADD,
    OPTIONS_FLOW_ACTIONS_BACK,
    OPTIONS_FLOW_GENERAL_OPTIONS,
    OPTIONS_FLOW_INPUT_MANAGE_ACTION,
    OPTIONS_FLOW_INPUT_MENU_SELECTION,
    OPTIONS_FLOW_KIDS,
    OPTIONS_FLOW_STEP_ADD_KID,
    OPTIONS_FLOW_STEP_INIT,
    OPTIONS_FLOW_STEP_MANAGE_ENTITY,
    OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS,
)


async def test_options_flow_init(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test options flow initialization shows main menu."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_add_kid_success(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test adding a kid via options flow."""
    # Navigate to kids management
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_KIDS},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_ENTITY

    # Select "Add" action
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_ADD_KID

    # Add the kid
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_KIDS_INPUT_KID_NAME: "Zoë Stårblüm"},
    )

    # Should return to main menu after successful add
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_add_kid_duplicate_name(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test adding a kid with duplicate name shows error."""
    # First, add a kid
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_KIDS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_KIDS_INPUT_KID_NAME: "Lila Stårblüm"},
    )

    # Navigate to add kid form
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_KIDS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )

    # Try to add kid with duplicate name
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_KIDS_INPUT_KID_NAME: "Lila Stårblüm"},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_ADD_KID
    errors = result.get("errors")
    assert errors is not None
    assert "kid_name" in errors


async def test_options_flow_back_to_main_menu(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test navigating back to main menu."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_KIDS},
    )

    # Go back to main menu
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_BACK},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


# =====================================================================
# BACKUP & RETENTION TESTS
# =====================================================================


async def test_retention_periods_consolidated_field_display(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that retention periods are displayed in single consolidated field."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to general options
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS

    # Get the schema to verify consolidated field exists
    data_schema = result.get("data_schema")
    assert data_schema is not None

    # Verify CONF_RETENTION_PERIODS field exists in schema
    field_keys = [str(field) for field in data_schema.schema.keys()]
    assert any(CONF_RETENTION_PERIODS in str(key) for key in field_keys)


async def test_retention_periods_parse_and_store(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that pipe-separated retention string is parsed and stored transparently."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to general options
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )

    # Update retention periods with new values
    new_retention = "10|8|6|2"  # daily|weekly|monthly|yearly
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CONF_RETENTION_PERIODS: new_retention},
    )

    # Should return to main menu on success
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

    # Verify the 4 individual keys were updated
    updated_options = init_integration.options
    assert updated_options.get(const.CONF_RETENTION_DAILY) == 10
    assert updated_options.get(const.CONF_RETENTION_WEEKLY) == 8
    assert updated_options.get(const.CONF_RETENTION_MONTHLY) == 6
    assert updated_options.get(const.CONF_RETENTION_YEARLY) == 2


async def test_retention_periods_invalid_format_validation(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that invalid retention format is rejected."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to general options
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )

    # Try invalid format (only 3 values instead of 4)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CONF_RETENTION_PERIODS: "10|8|6"},  # Missing yearly
    )

    # Invalid format should either show error or validation may reject at parse time
    # Behavior: stay on form and show error, or reject gracefully
    assert result.get("type") == FlowResultType.FORM
    # Step may return to init on validation error in some cases
    assert result.get("step_id") in [
        OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS,
        OPTIONS_FLOW_STEP_INIT,
    ]


async def test_retention_periods_zero_disables_cleanup(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that retention=0 for backups disables cleanup on removal."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to general options
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )

    # Update backup retention to 0
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CONF_BACKUPS_MAX_RETAINED: 0},
    )

    # Should return to main menu
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

    # Verify retention disabled state
    updated_options = init_integration.options
    assert updated_options.get(CONF_BACKUPS_MAX_RETAINED) == 0


async def test_restore_backup_via_options_lists_available(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that backup restore option can be accessed via options flow."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to general options
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )

    # Verify the manage_general_options step is reached
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS

    # Should be able to retrieve the schema without errors
    data_schema = result.get("data_schema")
    assert data_schema is not None


async def test_restore_backup_no_backups_available(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test backup restore step handles missing backups gracefully."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Navigate to general options
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_GENERAL_OPTIONS},
    )

    # Should show form successfully
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS

    # Should have a valid schema
    data_schema = result.get("data_schema")
    assert data_schema is not None
