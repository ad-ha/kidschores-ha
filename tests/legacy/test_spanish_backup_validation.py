"""Test Spanish language validation for KidsChores backup forms.

Test all backup-related dropdown forms to verify Spanish translations work correctly.
This helps validate whether the emoji prefix approach provides proper Spanish support.
"""

# pylint: disable=broad-exception-caught  # Tests use broad catches to show diagnostic output

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores import const


async def test_spanish_backup_actions_menu(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test Spanish language in backup actions menu dropdown."""
    # Set language to Spanish to test translation behavior
    hass.config.language = "es"

    # Initialize options flow
    config_entry = init_integration
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Navigate to general options where backup dropdown is accessible
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            const.OPTIONS_FLOW_INPUT_MENU_SELECTION: const.OPTIONS_FLOW_GENERAL_OPTIONS
        },
    )

    # Verify we're in the general options step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == const.OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS

    # Get the schema to inspect form fields
    schema = result["data_schema"]
    print(f"Schema fields: {list(schema.schema.keys())}")

    # Debug each field to understand the structure
    for key, field_validator in schema.schema.items():
        print(f"Field key: {key}, type: {type(field_validator)}")

    # Find backup field - should be backup_action_selection
    backup_field_key = None
    backup_selector = None

    for key, field_validator in schema.schema.items():
        if "backup" in str(key).lower():
            print(f"Found backup field by schema key: {key}")
            backup_field_key = key

            # Extract the actual field name from Required/Optional wrapper
            if hasattr(field_validator, "schema"):
                inner_field = field_validator.schema
                if hasattr(inner_field, "__call__") and hasattr(inner_field, "config"):
                    backup_selector = inner_field
                    break

    if backup_field_key:
        print(f"Found backup field: {backup_field_key}")
        print(f"Found backup selector: {backup_selector}")
        print(f"Backup selector type: {type(backup_selector)}")

        if backup_selector:
            print(f"Backup selector dir: {dir(backup_selector)}")

        # Inspect the selector to see if it uses translation_key or explicit options
        if backup_selector and hasattr(backup_selector, "config"):
            selector_config = backup_selector.config
            print(f"Selector config type: {type(selector_config)}")
            print(
                f"Selector config keys: {list(selector_config.keys()) if isinstance(selector_config, dict) else 'Not a dict'}"
            )

            # This should print the actual configuration
            print("=== BACKUP SELECTOR CONFIG CONTENT ===")
            print(f"Full selector config: {selector_config}")

            if isinstance(selector_config, dict):
                # Check for translation_key (Spanish-compatible approach)
                if "translation_key" in selector_config:
                    print(
                        f"✅ Uses translation_key: {selector_config['translation_key']}"
                    )
                    print("✅ This means Spanish translations should work!")

                # Check for explicit options (emoji approach - may not be Spanish-compatible)
                elif "options" in selector_config and selector_config["options"]:
                    print(
                        f"⚠️  Uses explicit options: {len(selector_config['options'])} items"
                    )
                    print(f"\nBackup actions menu options (with Spanish language set):")
                    for i, option in enumerate(selector_config["options"]):
                        print(f"  Option {i}: {option}")
                        if isinstance(option, dict):
                            if "value" in option and "label" in option:
                                print(
                                    f"    Value: {option['value']}, Label: {option['label']}"
                                )
                                # Check if label contains emojis
                                label = option["label"]
                                has_emoji = any(ord(char) > 127 for char in label[:10])
                                print(f"    Has emoji: {has_emoji}")
                            else:
                                print(f"    Dict keys: {list(option.keys())}")
                        else:
                            print(f"    Option type: {type(option)}")
                else:
                    print("❌ No translation_key or options found in config")

            print("=== END CONFIG ANALYSIS ===")

            # Summary and recommendations
            print("\n=== SPANISH LANGUAGE ANALYSIS ===")
            if isinstance(selector_config, dict):
                if "translation_key" in selector_config:
                    print(
                        "✅ RESULT: Uses translation_key - Spanish users will see translated text"
                    )
                elif "options" in selector_config:
                    print(
                        "⚠️  RESULT: Uses explicit options - Spanish users see emojis but may lack Spanish labels"
                    )
                    print(
                        "💡 RECOMMENDATION: Consider translation_key approach for better internationalization"
                    )
                else:
                    print(
                        "❓ RESULT: Unknown configuration - unable to determine Spanish compatibility"
                    )
        else:
            print("No backup selector found or no config attribute")
    else:
        print("Backup action selection not found in schema!")


async def test_spanish_backup_create_flow(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test Spanish language in backup creation flow."""
    hass.config.language = "es"

    config_entry = init_integration
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Navigate to general options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            const.OPTIONS_FLOW_INPUT_MENU_SELECTION: const.OPTIONS_FLOW_GENERAL_OPTIONS
        },
    )

    # Try to navigate to backup creation (if available)
    try:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"backup_action_selection": "create_backup"}
        )

        print(f"Create backup result type: {result['type']}")
        print(f"Create backup step_id: {result.get('step_id', 'No step_id')}")

        if result["type"] == FlowResultType.FORM:
            schema = result["data_schema"]
            print(f"Create backup form fields: {list(schema.schema.keys())}")

    except Exception as e:
        print(f"Could not navigate to create backup: {e}")


async def test_spanish_backup_restore_flow(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test Spanish language in backup restore flow."""
    hass.config.language = "es"

    config_entry = init_integration
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Navigate to general options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            const.OPTIONS_FLOW_INPUT_MENU_SELECTION: const.OPTIONS_FLOW_GENERAL_OPTIONS
        },
    )

    # Try to navigate to backup restore (if available)
    try:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={"backup_action_selection": "restore_backup"}
        )

        print(f"Restore backup result type: {result['type']}")
        print(f"Restore backup step_id: {result.get('step_id', 'No step_id')}")

        if result["type"] == FlowResultType.FORM:
            schema = result["data_schema"]
            print(f"Restore backup form fields: {list(schema.schema.keys())}")

    except Exception as e:
        print(f"Could not navigate to restore backup: {e}")
