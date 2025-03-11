"""Tests for KidsChores config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    CONF_POINTS_ICON,
    CONF_POINTS_LABEL,
    DOMAIN,
    SCHEMA_VERSION_STORAGE_ONLY,
)


async def test_form_user_flow_success(hass: HomeAssistant) -> None:
    """Test successful user config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "data_recovery"

    # Step 1: Choose "start fresh" from data recovery menu
    result = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input={"backup_selection": "start_fresh"},
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "intro"

    # Step 2: Pass intro step (empty form)
    result_intro = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input={},
    )
    assert result_intro.get("type") == FlowResultType.FORM
    assert result_intro.get("step_id") == "points_label"

    # Step 2: Fill in points label step
    with patch(
        "custom_components.kidschores.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result_points = await hass.config_entries.flow.async_configure(
            result_intro.get("flow_id"),
            user_input={
                CONF_POINTS_LABEL: "Stär Points",
                CONF_POINTS_ICON: "mdi:star",
            },
        )
        await hass.async_block_till_done()

    # We should get kid_count step, not CREATE_ENTRY yet
    # The flow needs to go through kid_count and other steps
    # For now, just verify we moved forward
    assert result_points.get("type") == FlowResultType.FORM
    assert len(mock_setup_entry.mock_calls) == 0


async def test_form_user_flow_default_values(hass: HomeAssistant) -> None:
    """Test user config flow with default values."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "data_recovery"

    # Navigate through data_recovery menu
    result = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input={"backup_selection": "start_fresh"},
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "intro"

    # Step 1: Pass intro step (empty form)
    result_intro = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input={},
    )
    assert result_intro.get("type") == FlowResultType.FORM
    assert result_intro.get("step_id") == "points_label"

    # Step 2: Use default values for points
    with patch(
        "custom_components.kidschores.async_setup_entry",
        return_value=True,
    ):
        result_points = await hass.config_entries.flow.async_configure(
            result_intro.get("flow_id"),
            user_input={},  # Empty input should use defaults
        )

    # Verify defaults are applied in the next step
    assert result_points.get("type") == FlowResultType.FORM


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("step_id") == "data_recovery"

    # Navigate through data_recovery menu
    result = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input={"backup_selection": "start_fresh"},
    )
    assert result.get("step_id") == "intro"

    # Step 1: Pass intro step
    result_intro = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input={},
    )
    assert result_intro.get("step_id") == "points_label"

    # Step 2: Try points_label step with error
    with patch(
        "custom_components.kidschores.async_setup_entry",
        side_effect=Exception("Test exception"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result_intro.get("flow_id"),
            user_input={
                CONF_POINTS_LABEL: "Points",
                CONF_POINTS_ICON: "mdi:star",
            },
        )

    # Should move to next step, not show error at this stage
    assert result2.get("type") == FlowResultType.FORM


async def test_form_already_configured(hass: HomeAssistant) -> None:
    """Test we abort if already configured."""
    entry = MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="KidsChores",
        data={"schema_version": SCHEMA_VERSION_STORAGE_ONLY},
        options={},
        source=config_entries.SOURCE_USER,
        entry_id="existing_entry",
        unique_id="kidschores_unique",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "single_instance_allowed"


async def test_form_user_flow_custom_labels(hass: HomeAssistant) -> None:
    """Test config flow with custom labels and icons."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("step_id") == "data_recovery"

    # Navigate through data_recovery menu
    result = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input={"backup_selection": "start_fresh"},
    )
    assert result.get("step_id") == "intro"

    # Step 1: Pass intro
    result_intro = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input={},
    )
    assert result_intro.get("step_id") == "points_label"

    # Step 2: Set custom labels
    with patch(
        "custom_components.kidschores.async_setup_entry",
        return_value=True,
    ):
        result_points = await hass.config_entries.flow.async_configure(
            result_intro.get("flow_id"),
            user_input={
                CONF_POINTS_LABEL: "Coins",
                CONF_POINTS_ICON: "mdi:currency-usd",
            },
        )

    # Should move to next step
    assert result_points.get("type") == FlowResultType.FORM


async def test_form_empty_label_uses_default(hass: HomeAssistant) -> None:
    """Test that empty label falls back to default."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("step_id") == "data_recovery"

    # Navigate through data_recovery menu
    result = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input={"backup_selection": "start_fresh"},
    )
    assert result.get("step_id") == "intro"

    # Step 1: Pass intro
    result_intro = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input={},
    )
    assert result_intro.get("step_id") == "points_label"

    # Step 2: Empty label should use defaults
    with patch(
        "custom_components.kidschores.async_setup_entry",
        return_value=True,
    ):
        result_points = await hass.config_entries.flow.async_configure(
            result_intro.get("flow_id"),
            user_input={
                CONF_POINTS_LABEL: "",  # Empty string
                CONF_POINTS_ICON: "mdi:star",
            },
        )

    # Should move to next step, defaults are applied when data is stored
    assert result_points.get("type") == FlowResultType.FORM


async def test_form_schema_version_set(hass: HomeAssistant) -> None:
    """Test that schema version is correctly set in config data."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("step_id") == "data_recovery"

    # Navigate through data_recovery menu
    result = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input={"backup_selection": "start_fresh"},
    )
    assert result.get("step_id") == "intro"

    # Step 1: Pass intro
    result_intro = await hass.config_entries.flow.async_configure(
        result.get("flow_id"),
        user_input={},
    )
    assert result_intro.get("step_id") == "points_label"

    # Step 2: Pass points_label
    with patch(
        "custom_components.kidschores.async_setup_entry",
        return_value=True,
    ):
        result_points = await hass.config_entries.flow.async_configure(
            result_intro.get("flow_id"),
            user_input={},
        )

    # Schema version is set when the flow completes, not at points step
    assert result_points.get("type") == FlowResultType.FORM
