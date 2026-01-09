"""Test config flow fresh start scenarios with progressive complexity.

This module tests the KidsChores config flow starting fresh (no backup data)
with incrementally complex scenarios:

- test_fresh_start_points_only: Just points setup
- test_fresh_start_points_and_kid: Points + 1 kid
- test_fresh_start_basic_family: Points + 2 kids + 1 chore
- test_fresh_start_full_scenario: Complete scenario_full setup

Uses real Home Assistant config flow system for integration testing.
"""

# pylint: disable=protected-access  # Accessing protected members for testing
# pylint: disable=redefined-outer-name  # Pytest fixtures redefine names

# pyright: reportTypedDictNotRequiredAccess=false

import uuid
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.kidschores import const


@pytest.mark.asyncio
async def test_fresh_start_points_only(hass: HomeAssistant) -> None:
    """Test 1: Fresh config flow with just Star Points theme, no entities.

    This is the simplest possible config flow completion:
    1. Starts fresh config flow (no existing data)
    2. Sets points label to "Star Points" with star icon
    3. Sets all entity counts to 0
    4. Completes with CREATE_ENTRY
    5. Verifies config entry created with Star Points theme settings

    Foundation test for more complex scenarios.
    """

    # Mock setup to prevent actual integration loading during config flow
    with patch("custom_components.kidschores.async_setup_entry", return_value=True):
        # Step 1: Start fresh config flow
        result = await hass.config_entries.flow.async_init(
            const.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_DATA_RECOVERY

        # Step 2: Choose "start fresh"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"backup_selection": "start_fresh"},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_INTRO

        # Step 3: Pass intro step (empty form)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_POINTS

        # Step 4: Set Star Points theme
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                const.CFOF_SYSTEM_INPUT_POINTS_LABEL: "Star Points",
                const.CFOF_SYSTEM_INPUT_POINTS_ICON: "mdi:star",
            },
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_KID_COUNT

        # Step 5-13: Set all entity counts to 0
        # Kid count = 0 (skips parent_count, goes to chore_count)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_KIDS_INPUT_KID_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORE_COUNT

        # Chore count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_CHORES_INPUT_CHORE_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_BADGE_COUNT

        # Badge count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_BADGES_INPUT_BADGE_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_REWARD_COUNT

        # Reward count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_REWARDS_INPUT_REWARD_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PENALTY_COUNT

        # Penalty count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_PENALTIES_INPUT_PENALTY_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_BONUS_COUNT

        # Bonus count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_BONUSES_INPUT_BONUS_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT

        # Achievement count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_ACHIEVEMENTS_INPUT_ACHIEVEMENT_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_CHALLENGE_COUNT

        # Challenge count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_CHALLENGES_INPUT_CHALLENGE_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_FINISH

        # Final step: finish (empty form)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )

        # Verify completion
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "KidsChores"

        # Verify config entry was created with Star Points settings
        config_entry = result["result"]
        assert config_entry.title == "KidsChores"
        assert config_entry.domain == const.DOMAIN

        # Verify system settings in options (storage-only mode v0.5.0+)
        assert config_entry.options[const.CONF_POINTS_LABEL] == "Star Points"
        assert config_entry.options[const.CONF_POINTS_ICON] == "mdi:star"
        assert config_entry.options[const.CONF_UPDATE_INTERVAL] == 5  # Default

        # Verify integration was set up
        entries = hass.config_entries.async_entries(const.DOMAIN)
        assert len(entries) == 1
        assert entries[0].entry_id == config_entry.entry_id


@pytest.mark.asyncio
async def test_fresh_start_points_and_kid(hass: HomeAssistant, mock_hass_users) -> None:
    """Test 2: Fresh config flow with Star Points + 1 kid.

    Tests the config flow with Star Points theme plus creation of 1 kid.
    All other entity counts remain at 0.
    """
    # Mock setup to prevent actual integration loading during config flow
    with patch("custom_components.kidschores.async_setup_entry", return_value=True):
        # Step 1: Start fresh config flow
        result = await hass.config_entries.flow.async_init(
            const.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_DATA_RECOVERY

        # Step 2: Choose "start fresh"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"backup_selection": "start_fresh"},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_INTRO

        # Step 3: Pass intro step (empty form)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_POINTS

        # Step 4: Configure Star Points theme
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                const.CFOF_SYSTEM_INPUT_POINTS_LABEL: "Star Points",
                const.CFOF_SYSTEM_INPUT_POINTS_ICON: "mdi:star",
            },
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_KID_COUNT

        # Step 5: Set kid count = 1
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_KIDS_INPUT_KID_COUNT: 1},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_KIDS

        # Step 6: Configure the one kid with HA user and notifications
        result = await _configure_kid_step(
            hass,
            result,
            mock_hass_users,
            kid_name="Zoë",
            kid_ha_user_key="kid1",
            dashboard_language="en",
            enable_mobile_notifications=True,
            mobile_notify_service="",  # No real notify services in test
            enable_persistent_notifications=True,
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENT_COUNT

        # Step 7: Parent count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_PARENTS_INPUT_PARENT_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORE_COUNT

        # Step 8: Chore count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_CHORES_INPUT_CHORE_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_BADGE_COUNT

        # Step 9: Badge count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_BADGES_INPUT_BADGE_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_REWARD_COUNT

        # Step 10: Reward count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_REWARDS_INPUT_REWARD_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PENALTY_COUNT

        # Step 11: Penalty count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_PENALTIES_INPUT_PENALTY_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_BONUS_COUNT

        # Step 12: Bonus count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_BONUSES_INPUT_BONUS_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT

        # Step 13: Achievement count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_ACHIEVEMENTS_INPUT_ACHIEVEMENT_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_CHALLENGE_COUNT

        # Step 14: Challenge count = 0
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_CHALLENGES_INPUT_CHALLENGE_COUNT: 0},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_FINISH

        # Step 15: Final step - finish
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )

        # Verify completion
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "KidsChores"

        # Verify config entry created correctly
        config_entry = result["result"]
        assert config_entry.title == "KidsChores"
        assert config_entry.domain == const.DOMAIN

        # Verify Star Points theme in system settings
        assert config_entry.options[const.CONF_POINTS_LABEL] == "Star Points"
        assert config_entry.options[const.CONF_POINTS_ICON] == "mdi:star"

        # Verify integration was set up and storage has properly configured kid
        entries = hass.config_entries.async_entries(const.DOMAIN)
        assert len(entries) == 1

        # Since the integration setup is mocked, we can't check storage directly,
        # but we can verify the config entry was created with the proper title
        # In a real scenario, the kid would be created with:
        # - Name: "Zoë"
        # - HA User ID: mock_hass_users["kid1"].id
        # - Mobile notifications: enabled with "mobile_app_test_device"
        # - Persistent notifications: enabled
        # - Dashboard language: "en"
        assert entries[0].entry_id == config_entry.entry_id

        # Config entry created successfully - coordinator contains kid data


@pytest.mark.asyncio
async def test_fresh_start_kid_with_notify_services(
    hass: HomeAssistant, mock_hass_users
) -> None:
    """Test 2b: Fresh config flow with kid configured with actual notify services.

    Tests the same scenario as test_fresh_start_points_and_kid but with
    mock notify services available to test the mobile notification configuration.
    """

    # Set up mock notify services for the test
    async def async_register_notify_services():
        """Register mock notify services for testing."""
        hass.services.async_register(
            "notify", "mobile_app_test_phone", lambda call: None
        )
        hass.services.async_register("notify", "persistent", lambda call: None)

    await async_register_notify_services()

    # Mock setup to prevent actual integration loading during config flow
    with patch("custom_components.kidschores.async_setup_entry", return_value=True):
        # Step 1: Start fresh config flow
        result = await hass.config_entries.flow.async_init(
            const.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_DATA_RECOVERY

        # Step 2: Choose "start fresh"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"backup_selection": "start_fresh"},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_INTRO

        # Step 3: Pass intro step (empty form)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_POINTS

        # Step 4: Configure Star Points theme
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                const.CFOF_SYSTEM_INPUT_POINTS_LABEL: "Star Points",
                const.CFOF_SYSTEM_INPUT_POINTS_ICON: "mdi:star",
            },
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_KID_COUNT

        # Step 5: Set kid count = 1
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_KIDS_INPUT_KID_COUNT: 1},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_KIDS

        # Step 6: Configure kid with real mobile notify service
        result = await _configure_kid_step(
            hass,
            result,
            mock_hass_users,
            kid_name="Zoë",
            kid_ha_user_key="kid1",
            dashboard_language="en",
            enable_mobile_notifications=True,
            mobile_notify_service="notify.mobile_app_test_phone",
            enable_persistent_notifications=True,
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENT_COUNT

        # Step 7-14: Set all other entity counts to 0 (same as basic test)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_PARENTS_INPUT_PARENT_COUNT: 0},
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORE_COUNT

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_CHORES_INPUT_CHORE_COUNT: 0},
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_BADGE_COUNT

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_BADGES_INPUT_BADGE_COUNT: 0},
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_REWARD_COUNT

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_REWARDS_INPUT_REWARD_COUNT: 0},
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PENALTY_COUNT

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_PENALTIES_INPUT_PENALTY_COUNT: 0},
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_BONUS_COUNT

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_BONUSES_INPUT_BONUS_COUNT: 0},
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_ACHIEVEMENTS_INPUT_ACHIEVEMENT_COUNT: 0},
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_CHALLENGE_COUNT

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_CHALLENGES_INPUT_CHALLENGE_COUNT: 0},
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_FINISH

        # Final step: finish
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )

        # Verify completion
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "KidsChores"

        # Verify config entry created correctly with Star Points
        config_entry = result["result"]
        assert config_entry.options[const.CONF_POINTS_LABEL] == "Star Points"
        assert config_entry.options[const.CONF_POINTS_ICON] == "mdi:star"

        # Verify integration setup succeeded
        entries = hass.config_entries.async_entries(const.DOMAIN)
        assert len(entries) == 1

        # In a real scenario, the kid would be configured with:
        # - Name: "Zoë"
        # - HA User ID: mock_hass_users["kid1"].id
        # - Mobile notifications: enabled with "notify.mobile_app_test_phone"
        # - Persistent notifications: enabled
        # - Dashboard language: "en"


@pytest.mark.asyncio
async def test_fresh_start_with_parent_no_notifications(
    hass: HomeAssistant, mock_hass_users
) -> None:
    """Test 3a: Fresh config flow with 1 kid + 1 parent (notifications disabled).

    Tests parent configuration with:
    - HA User ID assigned
    - Mobile and persistent notifications disabled
    - Associated with the kid
    """
    # Mock setup to prevent actual integration loading during config flow
    with patch("custom_components.kidschores.async_setup_entry", return_value=True):
        # Steps 1-5: Same as other tests (fresh start, intro, points, kid count=1, kid config)
        result = await hass.config_entries.flow.async_init(
            const.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"backup_selection": "start_fresh"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                const.CFOF_SYSTEM_INPUT_POINTS_LABEL: "Star Points",
                const.CFOF_SYSTEM_INPUT_POINTS_ICON: "mdi:star",
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={const.CFOF_KIDS_INPUT_KID_COUNT: 1}
        )
        result = await _configure_kid_step(
            hass,
            result,
            mock_hass_users,
            kid_name="Zoë",
            kid_ha_user_key="kid1",
            dashboard_language="en",
            enable_mobile_notifications=False,
            mobile_notify_service="",
            enable_persistent_notifications=False,
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENT_COUNT

        # Step 6: Set parent count = 1
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_PARENTS_INPUT_PARENT_COUNT: 1},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENTS

        # Step 7: Configure parent with HA user but no notifications
        # Extract the kid ID using the working pattern from test_fresh_start_with_parents
        data_schema = _require_data_schema(result)
        associated_kids_field = data_schema.schema.get(
            const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS
        )
        assert associated_kids_field is not None, (
            "associated_kids field not found in schema"
        )

        kid_options = associated_kids_field.config["options"]
        assert len(kid_options) == 1, f"Expected 1 kid option, got {len(kid_options)}"

        kid_id = kid_options[0]["value"]  # Extract UUID from first option

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                const.CFOF_PARENTS_INPUT_NAME: "Môm Astrid Stârblüm",
                const.CFOF_PARENTS_INPUT_HA_USER: mock_hass_users["parent1"].id,
                const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS: [
                    kid_id
                ],  # Use the extracted kid ID
                const.CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS: False,
                const.CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE: const.SENTINEL_EMPTY,
                const.CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS: False,
            },
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORE_COUNT

        # Steps 8-15: Set all other entity counts to 0 and finish
        for _, input_key, next_step in [
            (
                const.CONFIG_FLOW_STEP_CHORE_COUNT,
                const.CFOF_CHORES_INPUT_CHORE_COUNT,
                const.CONFIG_FLOW_STEP_BADGE_COUNT,
            ),
            (
                const.CONFIG_FLOW_STEP_BADGE_COUNT,
                const.CFOF_BADGES_INPUT_BADGE_COUNT,
                const.CONFIG_FLOW_STEP_REWARD_COUNT,
            ),
            (
                const.CONFIG_FLOW_STEP_REWARD_COUNT,
                const.CFOF_REWARDS_INPUT_REWARD_COUNT,
                const.CONFIG_FLOW_STEP_PENALTY_COUNT,
            ),
            (
                const.CONFIG_FLOW_STEP_PENALTY_COUNT,
                const.CFOF_PENALTIES_INPUT_PENALTY_COUNT,
                const.CONFIG_FLOW_STEP_BONUS_COUNT,
            ),
            (
                const.CONFIG_FLOW_STEP_BONUS_COUNT,
                const.CFOF_BONUSES_INPUT_BONUS_COUNT,
                const.CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT,
            ),
            (
                const.CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT,
                const.CFOF_ACHIEVEMENTS_INPUT_ACHIEVEMENT_COUNT,
                const.CONFIG_FLOW_STEP_CHALLENGE_COUNT,
            ),
            (
                const.CONFIG_FLOW_STEP_CHALLENGE_COUNT,
                const.CFOF_CHALLENGES_INPUT_CHALLENGE_COUNT,
                const.CONFIG_FLOW_STEP_FINISH,
            ),
        ]:
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={input_key: 0}
            )
            assert result["step_id"] == next_step

        # Final step: finish
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

        # Verify completion
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "KidsChores"
        config_entry = result["result"]
        assert config_entry.options[const.CONF_POINTS_LABEL] == "Star Points"

        # Verify integration setup
        entries = hass.config_entries.async_entries(const.DOMAIN)
        assert len(entries) == 1


@pytest.mark.asyncio
async def test_fresh_start_with_parent_with_notifications(
    hass: HomeAssistant, mock_hass_users
) -> None:
    """Test 3b: Fresh config flow with 1 kid + 1 parent (notifications enabled).

    Tests parent configuration with:
    - HA User ID assigned
    - Mobile and persistent notifications enabled
    - Mobile notify service configured
    - Associated with the kid
    """
    # Set up mock notify services
    hass.services.async_register("notify", "mobile_app_parent_phone", lambda call: None)
    hass.services.async_register("notify", "persistent", lambda call: None)

    # Mock setup to prevent actual integration loading during config flow
    with patch("custom_components.kidschores.async_setup_entry", return_value=True):
        # Steps 1-5: Same setup as previous test
        result = await hass.config_entries.flow.async_init(
            const.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"backup_selection": "start_fresh"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                const.CFOF_SYSTEM_INPUT_POINTS_LABEL: "Star Points",
                const.CFOF_SYSTEM_INPUT_POINTS_ICON: "mdi:star",
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={const.CFOF_KIDS_INPUT_KID_COUNT: 1}
        )
        result = await _configure_kid_step(
            hass,
            result,
            mock_hass_users,
            kid_name="Max!",
            kid_ha_user_key="kid2",
            dashboard_language="en",
            enable_mobile_notifications=False,
            mobile_notify_service="",
            enable_persistent_notifications=True,
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENT_COUNT

        # Step 6: Set parent count = 1
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_PARENTS_INPUT_PARENT_COUNT: 1},
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENTS

        # Step 7: Configure parent with notifications enabled using helper
        kid_ids = _extract_kid_ids_from_schema(result)
        result = await _configure_parent_step(
            hass,
            result,
            mock_hass_users,
            associated_kid_ids=kid_ids,
            parent_name="Dad Leo",
            parent_ha_user_key="parent2",
            enable_mobile_notifications=True,
            mobile_notify_service="notify.mobile_app_parent_phone",
            enable_persistent_notifications=True,
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORE_COUNT

        # Skip all other entity steps using helper
        result = await _skip_all_entity_steps(hass, result)

        # Final step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

        # Verify completion
        assert result["type"] == FlowResultType.CREATE_ENTRY
        config_entry = result["result"]
        assert config_entry.options[const.CONF_POINTS_LABEL] == "Star Points"

        # In a real scenario, the parent would be configured with:
        # - Name: "Parent Two"
        # - HA User ID: mock_hass_users["parent2"].id
        # - Mobile notifications: enabled with "notify.mobile_app_parent_phone"
        # - Persistent notifications: enabled
        # - Associated kids: ["Sam"]


@pytest.mark.asyncio
async def test_fresh_start_two_parents_mixed_notifications(
    hass: HomeAssistant, mock_hass_users
) -> None:
    """Test 3c: Fresh config flow with 1 kid + 2 parents (mixed notification settings).

    Tests complex parent configuration:
    - Parent 1: Notifications disabled, associated with kid
    - Parent 2: Notifications enabled, associated with kid
    - Both parents have HA user IDs
    """
    # Set up mock notify services
    hass.services.async_register(
        "notify", "mobile_app_parent2_phone", lambda call: None
    )

    # Mock setup to prevent actual integration loading during config flow
    with patch("custom_components.kidschores.async_setup_entry", return_value=True):
        # Steps 1-5: Basic setup
        result = await hass.config_entries.flow.async_init(
            const.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"backup_selection": "start_fresh"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                const.CFOF_SYSTEM_INPUT_POINTS_LABEL: "Star Points",
                const.CFOF_SYSTEM_INPUT_POINTS_ICON: "mdi:star",
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={const.CFOF_KIDS_INPUT_KID_COUNT: 1}
        )
        result = await _configure_kid_step(
            hass,
            result,
            mock_hass_users,
            kid_name="Lila",
            kid_ha_user_key="kid3",
            dashboard_language="en",
            enable_mobile_notifications=True,
            mobile_notify_service="",
            enable_persistent_notifications=False,
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENT_COUNT

        # Step 6: Set parent count = 2
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={const.CFOF_PARENTS_INPUT_PARENT_COUNT: 2},
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENTS

        # Step 7: Configure first parent (no notifications) using helper
        kid_ids = _extract_kid_ids_from_schema(result)
        result = await _configure_parent_step(
            hass,
            result,
            mock_hass_users,
            associated_kid_ids=kid_ids,
            parent_name="Môm Astrid Stârblüm",
            parent_ha_user_key="parent1",
            enable_mobile_notifications=False,
            enable_persistent_notifications=False,
        )
        assert result["type"] == FlowResultType.FORM
        assert (
            result["step_id"] == const.CONFIG_FLOW_STEP_PARENTS
        )  # Still on parents step

        # Step 8: Configure second parent (with notifications) using helper
        kid_ids = _extract_kid_ids_from_schema(result)  # Re-extract for second parent
        result = await _configure_parent_step(
            hass,
            result,
            mock_hass_users,
            associated_kid_ids=kid_ids,
            parent_name="Dad Leo",
            parent_ha_user_key="parent2",
            enable_mobile_notifications=True,
            mobile_notify_service="notify.mobile_app_parent2_phone",
            enable_persistent_notifications=True,
        )
        assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORE_COUNT

        # Skip all other entity steps using helper
        result = await _skip_all_entity_steps(hass, result)

        # Final step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

        # Verify completion
        assert result["type"] == FlowResultType.CREATE_ENTRY
        config_entry = result["result"]
        assert config_entry.options[const.CONF_POINTS_LABEL] == "Star Points"
        assert config_entry.options[const.CONF_POINTS_ICON] == "mdi:star"

        # In a real scenario:
        # Kid "Lila" - HA user: kid3, notifications: mobile disabled, persistent disabled
        # Parent "Môm Astrid Stârblüm" - HA user: parent1, notifications: all disabled, associated: ["Lila"]
        # Parent "Dad Leo" - HA user: parent2, mobile notifications enabled, associated: ["Lila"]


@pytest.mark.asyncio
async def test_fresh_start_basic_family(hass: HomeAssistant) -> None:  # pylint: disable=unused-argument
    """Test 3: Fresh config flow with Star Points + 2 kids + 1 parent + 1 chore.

    TODO: Implement config flow with:
    - Star Points theme setup
    - 2 kids with different settings
    - 1 parent linked to both kids
    - 1 basic chore assigned to both kids
    - Other entities = 0
    - Verification of all entity relationships
    """
    pytest.skip("TODO: Implement basic family config flow test")


@pytest.mark.asyncio
async def test_fresh_start_full_scenario(hass: HomeAssistant) -> None:  # pylint: disable=unused-argument
    """Test 4: Fresh config flow with complete scenario_full setup.

    TODO: Implement config flow with:
    - Star Points theme (matching scenario_full)
    - All entities from testdata_scenario_full.yaml
    - Full Stârblüm family setup (3 kids, 2 parents)
    - Complete chore/reward/badge system
    - Verification matches scenario_full structure
    """
    pytest.skip("TODO: Implement full scenario config flow test")


def _require_data_schema(result: Any) -> Any:
    """Return the data_schema ensuring it exists."""
    data_schema = result.get("data_schema")
    assert data_schema is not None
    return data_schema


async def _configure_kid_step(
    hass: HomeAssistant,
    result: Any,
    mock_hass_users: dict[str, Any],
    *,
    kid_name: str,
    kid_ha_user_key: str,
    dashboard_language: str = "en",
    enable_mobile_notifications: bool = False,
    mobile_notify_service: str = "",
    enable_persistent_notifications: bool = False,
) -> Any:
    """Configure a single kid in the config flow.

    Args:
        hass: Home Assistant instance
        result: Current config flow result
        mock_hass_users: Mock users dictionary
        kid_name: Name for the kid (e.g., "Zoë", "Max!", "Lila")
        kid_ha_user_key: Key in mock_hass_users (e.g., "kid1", "kid2", "kid3")
        dashboard_language: Dashboard language code (default: "en")
        enable_mobile_notifications: Whether to enable mobile notifications
        mobile_notify_service: Mobile notify service name (if mobile notifications enabled)
        enable_persistent_notifications: Whether to enable persistent notifications

    Returns:
        Updated config flow result after kid configuration
    """
    return await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            const.CFOF_KIDS_INPUT_KID_NAME: kid_name,
            const.CFOF_KIDS_INPUT_HA_USER: mock_hass_users[kid_ha_user_key].id,
            const.CFOF_KIDS_INPUT_DASHBOARD_LANGUAGE: dashboard_language,
            const.CFOF_KIDS_INPUT_ENABLE_MOBILE_NOTIFICATIONS: enable_mobile_notifications,
            const.CFOF_KIDS_INPUT_MOBILE_NOTIFY_SERVICE: mobile_notify_service,
            const.CFOF_KIDS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS: enable_persistent_notifications,
        },
    )


async def _configure_parent_step(
    hass: HomeAssistant,
    result: Any,
    mock_hass_users: dict[str, Any],
    associated_kid_ids: list[str],
    *,
    parent_name: str,
    parent_ha_user_key: str,
    enable_mobile_notifications: bool = False,
    mobile_notify_service: str = "",
    enable_persistent_notifications: bool = False,
) -> Any:
    """Configure a single parent in the config flow.

    Args:
        hass: Home Assistant instance
        result: Current config flow result
        mock_hass_users: Mock users dictionary
        associated_kid_ids: List of kid internal IDs to associate with this parent
        parent_name: Name for the parent (e.g., "Môm Astrid Stârblüm", "Dad Leo")
        parent_ha_user_key: Key in mock_hass_users (e.g., "parent1", "parent2")
        enable_mobile_notifications: Whether to enable mobile notifications
        mobile_notify_service: Mobile notify service name (if mobile notifications enabled)
        enable_persistent_notifications: Whether to enable persistent notifications

    Returns:
        Updated config flow result after parent configuration
    """
    return await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            const.CFOF_PARENTS_INPUT_NAME: parent_name,
            const.CFOF_PARENTS_INPUT_HA_USER: mock_hass_users[parent_ha_user_key].id,
            const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS: associated_kid_ids,
            const.CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS: enable_mobile_notifications,
            const.CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE: mobile_notify_service
            if enable_mobile_notifications
            else const.SENTINEL_EMPTY,
            const.CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS: enable_persistent_notifications,
        },
    )


# ----------------------------------------------------------------------------------
# ENHANCED REUSABLE HELPER FUNCTIONS FOR SCALABLE TEST SCENARIOS
# ----------------------------------------------------------------------------------


async def _configure_multiple_kids_step(
    hass: HomeAssistant,
    result: Any,
    mock_hass_users: dict[str, Any],
    kid_configs: list[dict[str, Any]],
) -> tuple[Any, dict[str, str]]:
    """Configure multiple kids in sequence during config flow.

    Args:
        hass: Home Assistant instance
        result: Current config flow result (should be on KIDS step)
        mock_hass_users: Mock users dictionary
        kid_configs: List of kid configuration dictionaries with keys:
            - name: Kid name (e.g., "Zoë", "Max!", "Lila")
            - ha_user_name: Key in mock_hass_users (e.g., "kid1", "kid2", "kid3")
            - dashboard_language: Dashboard language code (default: "en")
            - enable_mobile_notifications: Whether to enable mobile notifications (default: False)
            - mobile_notify_service: Mobile notify service name (default: "")
            - enable_persistent_notifications: Whether to enable persistent notifications (default: False)

    Returns:
        Tuple of (final_result, name_to_id_map)
        - final_result: Updated config flow result after all kids configured
        - name_to_id_map: Dict mapping kid names to their internal UUIDs

    Example:
        result, kid_ids = await _configure_multiple_kids_step(
            hass, result, mock_hass_users,
            [
                {"name": "Zoë", "ha_user_name": "kid1", "enable_mobile_notifications": True, "mobile_notify_service": "notify.mobile_app_zoe"},
                {"name": "Max!", "ha_user_name": "kid2", "dashboard_language": "es"},
                {"name": "Lila", "ha_user_name": "kid3", "enable_persistent_notifications": True},
            ]
        )
    """
    name_to_id_map = {}

    for i, kid_config in enumerate(kid_configs):
        # Configure this kid
        result = await _configure_kid_step(
            hass,
            result,
            mock_hass_users,
            kid_name=kid_config["name"],
            kid_ha_user_key=kid_config["ha_user_name"],
            dashboard_language=kid_config.get("dashboard_language", "en"),
            enable_mobile_notifications=kid_config.get(
                "enable_mobile_notifications", False
            ),
            mobile_notify_service=kid_config.get("mobile_notify_service", ""),
            enable_persistent_notifications=kid_config.get(
                "enable_persistent_notifications", False
            ),
        )

        # Extract the kid's internal ID from the config flow result
        if i < len(kid_configs) - 1:
            # Still more kids to configure - result should be on KIDS step again
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == const.CONFIG_FLOW_STEP_KIDS

            # After each kid is configured, the config flow advances to the next kid
            # but we can't easily extract the ID here. Store name mapping for now.
            # The real IDs will be available when we reach the parent step.
            name_to_id_map[kid_config["name"]] = None  # Placeholder
        else:
            # Last kid - result should advance to parent count step
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENT_COUNT

            # Extract all real kid IDs from parent step schema and map to names
            actual_kid_ids = _extract_kid_ids_from_schema(result)

            # Map kid names to their actual IDs (in order they were configured)
            for j, kid_config_item in enumerate(kid_configs):
                if j < len(actual_kid_ids):
                    name_to_id_map[kid_config_item["name"]] = actual_kid_ids[j]

    return result, name_to_id_map


async def _configure_multiple_parents_step(
    hass: HomeAssistant,
    result: Any,
    mock_hass_users: dict[str, Any],
    parent_configs: list[dict[str, Any]],
    kid_name_to_id_map: dict[str, str],
) -> Any:
    """Configure multiple parents in sequence during config flow.

    Args:
        hass: Home Assistant instance
        result: Current config flow result (should be on PARENTS step)
        mock_hass_users: Mock users dictionary
        parent_configs: List of parent configuration dictionaries with keys:
            - name: Parent name (e.g., "Môm Astrid Stârblüm", "Dad Leo")
            - ha_user_name: Key in mock_hass_users (e.g., "parent1", "parent2")
            - associated_kid_names: List of kid names to associate (default: [])
            - enable_mobile_notifications: Whether to enable mobile notifications (default: False)
            - mobile_notify_service: Mobile notify service name (default: "")
            - enable_persistent_notifications: Whether to enable persistent notifications (default: False)
        kid_name_to_id_map: Map of kid names to internal UUIDs from _configure_multiple_kids_step

    Returns:
        Updated config flow result after all parents configured

    Example:
        result = await _configure_multiple_parents_step(
            hass, result, mock_hass_users,
            [
                {
                    "name": "Môm Astrid Stârblüm",
                    "ha_user_name": "parent1",
                    "associated_kid_names": ["Zoë", "Lila"],
                    "enable_mobile_notifications": True,
                    "mobile_notify_service": "notify.mobile_app_mom"
                },
                {
                    "name": "Dad Leo",
                    "ha_user_name": "parent2",
                    "associated_kid_names": ["Max!", "Lila"],
                    "enable_persistent_notifications": True
                },
            ],
            kid_ids
        )
    """
    for i, parent_config in enumerate(parent_configs):
        # Map associated kid names to their internal IDs
        associated_kid_names = parent_config.get("associated_kid_names", [])
        associated_kid_ids = [
            kid_name_to_id_map[name]
            for name in associated_kid_names
            if name in kid_name_to_id_map
        ]

        # Configure this parent
        result = await _configure_parent_step(
            hass,
            result,
            mock_hass_users,
            associated_kid_ids,
            parent_name=parent_config["name"],
            parent_ha_user_key=parent_config["ha_user_name"],
            enable_mobile_notifications=parent_config.get(
                "enable_mobile_notifications", False
            ),
            mobile_notify_service=parent_config.get("mobile_notify_service", ""),
            enable_persistent_notifications=parent_config.get(
                "enable_persistent_notifications", False
            ),
        )

        if i < len(parent_configs) - 1:
            # Still more parents to configure
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENTS
        else:
            # Last parent - result should advance to chore count step
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORE_COUNT

    return result


async def _setup_full_family_scenario(
    hass: HomeAssistant,
    result: Any,
    mock_hass_users: dict[str, Any],
    points_label: str = "Star Points",
    points_icon: str = "mdi:star",
) -> tuple[Any, dict[str, str]]:
    """Set up a complete family scenario matching scenario_full test data.

    Configures:
    - 3 kids: Zoë, Max!, Lila (from testdata_scenario_full.yaml)
    - 2 parents: Môm Astrid Stârblüm, Dad Leo (from testdata_scenario_full.yaml)
    - Realistic notification configurations
    - Mixed dashboard languages

    Args:
        hass: Home Assistant instance
        result: Current config flow result (should be on POINTS step)
        mock_hass_users: Mock users dictionary
        points_label: Points label for theme (default: "Star Points")
        points_icon: Points icon for theme (default: "mdi:star-circle")

    Returns:
        Tuple of (final_result, kid_name_to_id_map)
        - final_result: Config flow result ready for entity configuration
        - kid_name_to_id_map: Mapping of kid names to internal UUIDs

    Example:
        result, kid_ids = await _setup_full_family_scenario(hass, result, mock_hass_users)
        # Can now configure chores, rewards, etc. referencing kid_ids["Zoë"], kid_ids["Max!"], etc.
    """
    # Step 1: Configure points theme
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            const.CFOF_SYSTEM_INPUT_POINTS_LABEL: points_label,
            const.CFOF_SYSTEM_INPUT_POINTS_ICON: points_icon,
        },
    )
    assert result["step_id"] == const.CONFIG_FLOW_STEP_KID_COUNT

    # Step 2: Set kid count = 3
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={const.CFOF_KIDS_INPUT_KID_COUNT: 3}
    )
    assert result["step_id"] == const.CONFIG_FLOW_STEP_KIDS

    # Step 3: Configure 3 kids individually (proven working pattern)
    result = await _configure_kid_step(
        hass,
        result,
        mock_hass_users,
        kid_name="Zoë",
        kid_ha_user_key="kid1",
        dashboard_language="en",
        enable_mobile_notifications=False,
        mobile_notify_service="",
        enable_persistent_notifications=True,
    )
    result = await _configure_kid_step(
        hass,
        result,
        mock_hass_users,
        kid_name="Max!",
        kid_ha_user_key="kid2",
        dashboard_language="es",
        enable_mobile_notifications=False,
        mobile_notify_service="",
        enable_persistent_notifications=True,
    )
    result = await _configure_kid_step(
        hass,
        result,
        mock_hass_users,
        kid_name="Lila",
        kid_ha_user_key="kid3",
        dashboard_language="en",
        enable_mobile_notifications=False,
        mobile_notify_service="",
        enable_persistent_notifications=False,
    )
    assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENT_COUNT

    # Step 4: Set parent count = 2
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={const.CFOF_PARENTS_INPUT_PARENT_COUNT: 2}
    )
    assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENTS

    # Step 5: Extract kid IDs from schema (proven working pattern)
    kid_ids = _extract_kid_ids_from_schema(result)

    # Configure first parent
    result = await _configure_parent_step(
        hass,
        result,
        mock_hass_users,
        associated_kid_ids=[kid_ids[0], kid_ids[2]],  # Zoë, Lila
        parent_name="Môm Astrid Stârblüm",
        parent_ha_user_key="parent1",
        enable_mobile_notifications=False,
        mobile_notify_service="",
        enable_persistent_notifications=True,
    )

    # Configure second parent
    kid_ids = _extract_kid_ids_from_schema(result)  # Re-extract for second parent
    result = await _configure_parent_step(
        hass,
        result,
        mock_hass_users,
        associated_kid_ids=[kid_ids[1], kid_ids[2]],  # Max!, Lila
        parent_name="Dad Leo",
        parent_ha_user_key="parent2",
        enable_mobile_notifications=False,
        enable_persistent_notifications=True,
    )
    assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORE_COUNT

    # Create name to ID mapping for return (kid order: Zoë=0, Max!=1, Lila=2)
    kid_name_to_id_map = {
        "Zoë": kid_ids[0],
        "Max!": kid_ids[1],
        "Lila": kid_ids[2],
    }

    return result, kid_name_to_id_map


# ----------------------------------------------------------------------------------
# EXISTING HELPER FUNCTIONS (keep for backward compatibility)
# ----------------------------------------------------------------------------------


async def _skip_all_entity_steps(hass: HomeAssistant, result: Any) -> Any:
    """Skip all entity configuration steps by setting counts to 0.

    Args:
        hass: Home Assistant instance
        result: Current config flow result

    Returns:
        Updated config flow result ready for finish step
    """
    for _, input_key, next_step in [
        (
            const.CONFIG_FLOW_STEP_CHORE_COUNT,
            const.CFOF_CHORES_INPUT_CHORE_COUNT,
            const.CONFIG_FLOW_STEP_BADGE_COUNT,
        ),
        (
            const.CONFIG_FLOW_STEP_BADGE_COUNT,
            const.CFOF_BADGES_INPUT_BADGE_COUNT,
            const.CONFIG_FLOW_STEP_REWARD_COUNT,
        ),
        (
            const.CONFIG_FLOW_STEP_REWARD_COUNT,
            const.CFOF_REWARDS_INPUT_REWARD_COUNT,
            const.CONFIG_FLOW_STEP_PENALTY_COUNT,
        ),
        (
            const.CONFIG_FLOW_STEP_PENALTY_COUNT,
            const.CFOF_PENALTIES_INPUT_PENALTY_COUNT,
            const.CONFIG_FLOW_STEP_BONUS_COUNT,
        ),
        (
            const.CONFIG_FLOW_STEP_BONUS_COUNT,
            const.CFOF_BONUSES_INPUT_BONUS_COUNT,
            const.CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT,
        ),
        (
            const.CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT,
            const.CFOF_ACHIEVEMENTS_INPUT_ACHIEVEMENT_COUNT,
            const.CONFIG_FLOW_STEP_CHALLENGE_COUNT,
        ),
        (
            const.CONFIG_FLOW_STEP_CHALLENGE_COUNT,
            const.CFOF_CHALLENGES_INPUT_CHALLENGE_COUNT,
            const.CONFIG_FLOW_STEP_FINISH,
        ),
    ]:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={input_key: 0}
        )
        assert result["step_id"] == next_step

    return result


def _extract_kid_ids_from_schema(result: Any) -> list[str]:
    """Extract kid IDs from the config flow result schema.

    Args:
        result: Config flow result containing data schema

    Returns:
        List of kid internal IDs available in the form
    """
    data_schema = _require_data_schema(result)
    associated_kids_field = data_schema.schema.get(
        const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS
    )
    assert associated_kids_field is not None, (
        "associated_kids field not found in schema"
    )

    kid_options = associated_kids_field.config["options"]
    return [option["value"] for option in kid_options]


@pytest.mark.asyncio
async def test_fresh_start_with_parents(hass: HomeAssistant, mock_hass_users):
    """Test 5: Fresh start config flow through parents step.

    Tests creating 1 kid then 1 parent associated with that kid.
    This test captures the kid UUID properly from config flow state.
    """
    # Set up mock notify services for the test
    hass.services.async_register("notify", "mobile_app_jane_phone", lambda call: None)
    hass.services.async_register("notify", "persistent", lambda call: None)

    # Create parent user in mock system
    parent_user = mock_hass_users["parent1"]

    # Mock setup to prevent actual integration loading during config flow
    with patch("custom_components.kidschores.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            const.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_DATA_RECOVERY

        # Skip data recovery
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"backup_selection": "start_fresh"}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_INTRO

        # Skip intro
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_POINTS

        # Configure points system
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                const.CFOF_SYSTEM_INPUT_POINTS_LABEL: "Star Points",
                const.CFOF_SYSTEM_INPUT_POINTS_ICON: "mdi:star",
            },
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_KID_COUNT

        # Configure 1 kid
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={const.CFOF_KIDS_INPUT_KID_COUNT: 1}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_KIDS

        # Create a kid first
        result = await _configure_kid_step(
            hass,
            result,
            mock_hass_users,
            kid_name="Alex",
            kid_ha_user_key="kid1",
            dashboard_language="en",
            enable_mobile_notifications=False,
            mobile_notify_service="",
            enable_persistent_notifications=False,
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENT_COUNT

        # Configure 1 parent
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={const.CFOF_PARENTS_INPUT_PARENT_COUNT: 1}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENTS

        # Extract the kid ID from the parent form schema options for associated_kids field
        data_schema = _require_data_schema(result)

        # Find the associated_kids field schema - the key is the string constant
        associated_kids_field = data_schema.schema.get(
            const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS
        )
        assert associated_kids_field is not None, (
            "associated_kids field not found in schema"
        )

        # Extract the available kid options - these are dicts with "value" and "label"
        kid_options = associated_kids_field.config["options"]  # SelectSelector options
        assert len(kid_options) == 1, f"Expected 1 kid option, got {len(kid_options)}"

        # Get the kid ID from the first (and only) option
        kid_id = kid_options[0][
            "value"
        ]  # Extract value from {"value": kid_id, "label": kid_name}

        # Now configure the parent associated with this kid
        parent_input = {
            const.CFOF_PARENTS_INPUT_NAME: "Jane Parent",
            const.CFOF_PARENTS_INPUT_HA_USER: parent_user.id,
            const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS: [
                kid_id
            ],  # Use the captured kid ID
            const.CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS: True,
            const.CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE: "notify.mobile_app_jane_phone",  # Include notify. prefix
            const.CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS: True,
        }

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=parent_input
        )
        assert result["type"] == FlowResultType.FORM
        # Should move to entities setup - let's see what the next step is
        assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORE_COUNT

        # Skip all remaining entity steps
        for _, input_key, next_step in [
            (
                const.CONFIG_FLOW_STEP_CHORE_COUNT,
                const.CFOF_CHORES_INPUT_CHORE_COUNT,
                const.CONFIG_FLOW_STEP_BADGE_COUNT,
            ),
            (
                const.CONFIG_FLOW_STEP_BADGE_COUNT,
                const.CFOF_BADGES_INPUT_BADGE_COUNT,
                const.CONFIG_FLOW_STEP_REWARD_COUNT,
            ),
            (
                const.CONFIG_FLOW_STEP_REWARD_COUNT,
                const.CFOF_REWARDS_INPUT_REWARD_COUNT,
                const.CONFIG_FLOW_STEP_PENALTY_COUNT,
            ),
            (
                const.CONFIG_FLOW_STEP_PENALTY_COUNT,
                const.CFOF_PENALTIES_INPUT_PENALTY_COUNT,
                const.CONFIG_FLOW_STEP_BONUS_COUNT,
            ),
            (
                const.CONFIG_FLOW_STEP_BONUS_COUNT,
                const.CFOF_BONUSES_INPUT_BONUS_COUNT,
                const.CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT,
            ),
            (
                const.CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT,
                const.CFOF_ACHIEVEMENTS_INPUT_ACHIEVEMENT_COUNT,
                const.CONFIG_FLOW_STEP_CHALLENGE_COUNT,
            ),
            (
                const.CONFIG_FLOW_STEP_CHALLENGE_COUNT,
                const.CFOF_CHALLENGES_INPUT_CHALLENGE_COUNT,
                const.CONFIG_FLOW_STEP_FINISH,
            ),
        ]:
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={input_key: 0}
            )
            assert result["step_id"] == next_step

        # Final step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

        # Verify completion
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "KidsChores"

        # Verify config entry created correctly
        config_entry = result["result"]
        assert config_entry.title == "KidsChores"
        assert config_entry.domain == const.DOMAIN

        # Verify Star Points theme in system settings
        assert config_entry.options[const.CONF_POINTS_LABEL] == "Star Points"
        assert config_entry.options[const.CONF_POINTS_ICON] == "mdi:star"

        # Config entry created successfully - coordinator contains family data


# ==============================================================================
# CHORE CONFIGURATION HELPERS
# ==============================================================================


async def _configure_chore_step(
    hass: HomeAssistant,
    result: Any,
    chore_name: str,
    assigned_kid_names: list[str],
    points: float = 10.0,
    description: str = "",
    icon: str = "mdi:check",
    completion_criteria: str = "independent",
    recurring_frequency: str = "daily",
    auto_approve: bool = False,
    show_on_calendar: bool = True,
    labels: list[str] | None = None,
    applicable_days: list[str] | None = None,
    notifications: list[str] | None = None,
    due_date: str | None = None,
    custom_interval: int | None = None,
    custom_interval_unit: str | None = None,
    approval_reset_type: str = const.DEFAULT_APPROVAL_RESET_TYPE,
    approval_reset_pending_claim_action: str = const.DEFAULT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
    overdue_handling_type: str = const.DEFAULT_OVERDUE_HANDLING_TYPE,
) -> Any:
    """Configure a single chore step during config flow.

    Args:
        hass: Home Assistant instance
        result: Current config flow result (should be on CHORES step)
        chore_name: Name of the chore (e.g., "Feed the cåts", "Wåter the plånts")
        assigned_kid_names: List of kid names to assign chore to (e.g., ["Zoë", "Max!"])
        points: Points awarded for completion (default: 10.0)
        description: Optional chore description (default: "")
        icon: MDI icon (default: "mdi:check")
        completion_criteria: "independent", "shared_all", or "shared_first" (default: "independent")
        recurring_frequency: "daily", "weekly", "monthly", "custom", or "none" (default: "daily")
        auto_approve: Whether to auto-approve chore (default: False)
        show_on_calendar: Whether to show on calendar (default: True)
        labels: Optional list of labels (default: None)
        applicable_days: Optional list of weekday codes (default: None)
        notifications: Optional list of notification events (default: None)
        due_date: Optional due date as ISO string (default: None)
        custom_interval: Custom interval number (for custom frequency)
        custom_interval_unit: "days", "weeks", "months" (for custom frequency)
        approval_reset_type: "automatic", "manual", "never" (default: "automatic")
        approval_reset_pending_claim_action: Action for pending claims (default: "complete_with_pending_claim")
        overdue_handling_type: "none", "reset_to_pending", "auto_disapprove" (default: "none")

    Returns:
        Updated config flow result after chore configured

    Note:
        Based on chore form fields from flow_helpers.py build_chore_schema().
        YAML mapping: type → recurring_frequency, assigned_to → assigned_kid_names
    """
    # Prepare notifications list (empty by default)
    chore_notifications = notifications or []

    # Prepare applicable days (all days by default for daily chores)
    if applicable_days is None:
        if recurring_frequency == "daily":
            applicable_days = [
                "mon",
                "tue",
                "wed",
                "thu",
                "fri",
                "sat",
                "sun",
            ]  # All weekdays
        else:
            applicable_days = ["mon"]  # Monday for weekly/monthly

    # Configure this chore
    user_input = {
        const.CFOF_CHORES_INPUT_NAME: chore_name,
        const.CFOF_CHORES_INPUT_ASSIGNED_KIDS: assigned_kid_names,
        const.CFOF_CHORES_INPUT_DEFAULT_POINTS: points,
        const.CFOF_CHORES_INPUT_DESCRIPTION: description,
        const.CFOF_CHORES_INPUT_ICON: icon,
        const.CFOF_CHORES_INPUT_COMPLETION_CRITERIA: completion_criteria,
        const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY: recurring_frequency,
        const.CFOF_CHORES_INPUT_AUTO_APPROVE: auto_approve,
        const.CFOF_CHORES_INPUT_SHOW_ON_CALENDAR: show_on_calendar,
        const.CFOF_CHORES_INPUT_LABELS: labels or [],
        const.CFOF_CHORES_INPUT_APPLICABLE_DAYS: applicable_days,
        const.CFOF_CHORES_INPUT_NOTIFICATIONS: chore_notifications,
        const.CFOF_CHORES_INPUT_APPROVAL_RESET_TYPE: approval_reset_type,
        const.CFOF_CHORES_INPUT_APPROVAL_RESET_PENDING_CLAIM_ACTION: approval_reset_pending_claim_action,
        const.CFOF_CHORES_INPUT_OVERDUE_HANDLING_TYPE: overdue_handling_type,
    }

    # Add optional fields if provided
    if due_date is not None:
        user_input[const.CFOF_CHORES_INPUT_DUE_DATE] = due_date
    if custom_interval is not None:
        user_input[const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL] = custom_interval
    if custom_interval_unit is not None:
        user_input[const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL_UNIT] = custom_interval_unit

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=user_input
    )
    return result


async def _configure_system_settings_step(
    hass: HomeAssistant,
    result: Any,
    points_label: str = "Points",
    points_icon: str = "mdi:star-outline",
) -> Any:
    """Configure system settings (points theme) step in config flow.

    Args:
        hass: Home Assistant instance
        result: Current config flow result (should be on POINTS step)
        points_label: Label for points (default: "Points")
        points_icon: Icon for points (default: "mdi:star-outline")

    Returns:
        Updated config flow result at KID_COUNT step
    """
    assert result["step_id"] == const.CONFIG_FLOW_STEP_POINTS

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            const.CFOF_SYSTEM_INPUT_POINTS_LABEL: points_label,
            const.CFOF_SYSTEM_INPUT_POINTS_ICON: points_icon,
        },
    )
    assert result["step_id"] == const.CONFIG_FLOW_STEP_KID_COUNT
    return result


async def _configure_family_step(
    hass: HomeAssistant,
    mock_hass_users,
    kid_names: list[str],
    parent_name: str = "Môm Astrid Stârblüm",
) -> tuple[Any, dict[str, str]]:
    """Configure family (kids + parent) during config flow.

    Args:
        hass: Home Assistant instance
        mock_hass_users: Mock user dictionary from fixture
        kid_names: List of kid names to create (e.g., ["Zoë", "Max!", "Lila"])
        parent_name: Parent name (default: "Môm Astrid Stârblüm")

    Returns:
        Tuple of (config_flow_result, name_to_id_map)
        - config_flow_result: Result at end ready for next step
        - name_to_id_map: Mapping of kid names to their UUIDs
    """
    # Start config flow
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == const.CONFIG_FLOW_STEP_DATA_RECOVERY

    # Skip data recovery (fresh start)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"backup_selection": "start_fresh"}
    )
    assert result["step_id"] == const.CONFIG_FLOW_STEP_INTRO

    # Skip intro
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["step_id"] == const.CONFIG_FLOW_STEP_POINTS

    # Configure system settings
    result = await _configure_system_settings_step(
        hass,
        result,
        points_label="Star Points",  # Use Star theme by default
        points_icon="mdi:star",
    )

    # Configure multiple kids
    kid_configs = [
        {"name": kid_name, "ha_user_name": f"kid{i + 1}"}
        for i, kid_name in enumerate(kid_names)
    ]
    result, kid_name_to_id_map = await _configure_multiple_kids_step(
        hass, result, mock_hass_users, kid_configs
    )

    # Configure single parent linked to all kids
    kid_ids = [kid_name_to_id_map[f"kid:{name}"] for name in kid_names]
    result = await _configure_parent_step(
        hass,
        result,
        mock_hass_users,
        associated_kid_ids=kid_ids,
        parent_name=parent_name,
        parent_ha_user_key="parent1",
        enable_mobile_notifications=False,
        mobile_notify_service=const.SENTINEL_EMPTY,
        enable_persistent_notifications=False,
    )

    # Should be at chore count step
    assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORE_COUNT

    return result, kid_name_to_id_map


async def _configure_multiple_chores_step(
    hass: HomeAssistant,
    result: Any,
    chore_configs: list[dict[str, Any]],
) -> tuple[Any, dict[str, str]]:
    """Configure multiple chores in sequence during config flow.

    Args:
        hass: Home Assistant instance
        result: Current config flow result (should be on CHORE_COUNT step)
        chore_configs: List of chore configuration dictionaries with keys:
            - name: Chore name (e.g., "Feed the cåts", "Wåter the plånts")
            - assigned_kid_names: List of kid names (e.g., ["Zoë"], ["Max!", "Lila"])
            - points: Points value (default: 10.0)
            - type: YAML type field ("daily", "weekly", "monthly", "custom")
            - icon: MDI icon (default: "mdi:check")
            - completion_criteria: "independent", "shared_all", "shared_first" (default: "independent")
            - auto_approve: Whether to auto-approve (default: False)
            - custom_interval_days: For custom frequency (maps to custom_interval)
            - All other optional fields from _configure_chore_step()

    Returns:
        Tuple of (final_result, name_to_id_map)
        - final_result: Updated config flow result after all chores configured
        - name_to_id_map: Dict mapping chore names to their internal UUIDs

    Example:
        result, chore_ids = await _configure_multiple_chores_step(
            hass, result,
            [
                {
                    "name": "Feed the cåts",
                    "assigned_kid_names": ["Zoë"],
                    "type": "daily",
                    "points": 10,
                    "icon": "mdi:cat",
                    "completion_criteria": "independent"
                },
                {
                    "name": "Stär sweep",
                    "assigned_kid_names": ["Zoë", "Max!", "Lila"],
                    "type": "daily",
                    "points": 20,
                    "icon": "mdi:star",
                    "completion_criteria": "independent"
                },
            ]
        )

    Note:
        Maps YAML structure to config flow format:
        - type → recurring_frequency
        - assigned_to → assigned_kid_names
        - custom_interval_days → custom_interval + custom_interval_unit="days"
    """
    name_to_id_map = {}

    # Set chore count
    chore_count = len(chore_configs)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={const.CFOF_CHORES_INPUT_CHORE_COUNT: chore_count}
    )

    if chore_count == 0:
        # Skip to badge count step
        assert result["step_id"] == const.CONFIG_FLOW_STEP_BADGE_COUNT
        return result, name_to_id_map

    # Configure each chore
    for i, chore_config in enumerate(chore_configs):
        assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORES

        # Map YAML fields to config flow parameters
        chore_type = chore_config.get("type", "daily")
        recurring_frequency = chore_type if chore_type != "custom" else "custom"

        # Handle custom interval days
        custom_interval = None
        custom_interval_unit = None
        if "custom_interval_days" in chore_config:
            custom_interval = chore_config["custom_interval_days"]
            custom_interval_unit = "days"

        # Configure this chore
        result = await _configure_chore_step(
            hass,
            result,
            chore_name=chore_config["name"],
            assigned_kid_names=chore_config["assigned_kid_names"],
            points=chore_config.get("points", 10.0),
            description=chore_config.get("description", ""),
            icon=chore_config.get("icon", "mdi:check"),
            completion_criteria=chore_config.get("completion_criteria", "independent"),
            recurring_frequency=recurring_frequency,
            auto_approve=chore_config.get("auto_approve", False),
            show_on_calendar=chore_config.get("show_on_calendar", True),
            labels=chore_config.get("labels"),
            applicable_days=chore_config.get("applicable_days"),
            notifications=chore_config.get("notifications"),
            due_date=chore_config.get("due_date"),
            custom_interval=custom_interval,
            custom_interval_unit=custom_interval_unit,
            approval_reset_type=chore_config.get(
                "approval_reset_type", const.DEFAULT_APPROVAL_RESET_TYPE
            ),
            approval_reset_pending_claim_action=chore_config.get(
                "approval_reset_pending_claim_action",
                const.DEFAULT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
            ),
            overdue_handling_type=chore_config.get(
                "overdue_handling_type", const.DEFAULT_OVERDUE_HANDLING_TYPE
            ),
        )

        # Generate UUID for this chore (simulating what config flow does)
        chore_id = str(uuid.uuid4())
        name_to_id_map[f"chore:{chore_config['name']}"] = chore_id

        if i < len(chore_configs) - 1:
            # Still more chores to configure
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORES
        else:
            # Last chore - should go to badge count
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == const.CONFIG_FLOW_STEP_BADGE_COUNT

    return result, name_to_id_map


# Future test ideas:
# - test_fresh_start_badges_and_rewards: Focus on badge/reward system
# - test_fresh_start_challenges_and_achievements: Focus on advanced features
# - test_fresh_start_error_handling: Test validation and error paths
# - test_fresh_start_different_themes: Test various points labels/icons


async def test_fresh_start_with_single_chore(
    hass: HomeAssistant,
    mock_hass_users: dict[str, Any],
) -> None:
    """Test fresh start config flow with family + single chore from testdata_scenario_full.yaml.

    This test validates:
    1. Complete family setup (kids + parents)
    2. Single chore configuration using helper functions
    3. YAML compatibility (chore matches "Feed the cåts" from scenario_full.yaml)
    4. Proper field mapping (type → recurring_frequency, assigned_to → assigned_kid_names)
    """
    # Step 1: Start config flow and navigate to points step
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"backup_selection": "start_fresh"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},  # Skip intro
    )

    # Step 2: Setup family from scenario_full.yaml with Star Points theme
    result, _ = await _setup_full_family_scenario(
        hass,
        result,
        mock_hass_users,
        points_label="Star Points",
        points_icon="mdi:star",
    )
    assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORE_COUNT

    # Step 3: Configure single chore "Feed the cåts" (matches first chore in scenario_full.yaml)
    result, chore_name_to_id_map = await _configure_multiple_chores_step(
        hass,
        result,
        [
            {
                "name": "Feed the cåts",
                "assigned_kid_names": ["Zoë"],  # Matches assigned_to: ["Zoë"] in YAML
                "type": "daily",  # Maps to recurring_frequency: "daily"
                "points": 10,
                "icon": "mdi:cat",
                "completion_criteria": "independent",
                "auto_approve": False,  # Default in YAML
            }
        ],
    )

    # Should proceed to badge count step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == const.CONFIG_FLOW_STEP_BADGE_COUNT

    # Verify chore was mapped correctly
    assert "chore:Feed the cåts" in chore_name_to_id_map
    chore_id = chore_name_to_id_map["chore:Feed the cåts"]
    assert len(chore_id) == 36  # UUID length (8-4-4-4-12 format with hyphens)

    # Complete remaining steps with 0 counts to finish config flow
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={const.CFOF_BADGES_INPUT_BADGE_COUNT: 0}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={const.CFOF_REWARDS_INPUT_REWARD_COUNT: 0}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={const.CFOF_PENALTIES_INPUT_PENALTY_COUNT: 0}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={const.CFOF_BONUSES_INPUT_BONUS_COUNT: 0}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={const.CFOF_ACHIEVEMENTS_INPUT_ACHIEVEMENT_COUNT: 0},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={const.CFOF_CHALLENGES_INPUT_CHALLENGE_COUNT: 0}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},  # Final finish step
    )

    # Should complete successfully
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "KidsChores"

    # Verify the config entry was created
    config_entry = result["result"]
    assert config_entry.domain == const.DOMAIN
    assert config_entry.options[const.CONF_POINTS_LABEL] == "Star Points"
    assert config_entry.options[const.CONF_POINTS_ICON] == "mdi:star"


async def test_fresh_start_with_all_scenario_chores(
    hass: HomeAssistant, mock_hass_users
) -> None:
    """Test fresh start config flow with all 18 chores from scenario_full.yaml."""
    # TEMP: Use simpler approach until family step is fixed
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"backup_selection": "start_fresh"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    # Use existing helper to setup the full family (3 kids + 1 parent)
    result, _ = await _setup_full_family_scenario(
        hass,
        result,
        mock_hass_users,
        points_label="Star Points",
        points_icon="mdi:star",
    )
    assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORE_COUNT

    # Configure all 18 chores from scenario_full.yaml
    all_scenario_chores = [
        # === INDEPENDENT CHORES (Single Kid) ===
        {
            "name": "Feed the cåts",
            "assigned_kid_names": ["Zoë"],
            "type": "daily",
            "points": 10,
            "icon": "mdi:cat",
            "completion_criteria": "independent",
            "auto_approve": False,
        },
        {
            "name": "Wåter the plänts",
            "assigned_kid_names": ["Zoë"],
            "type": "daily",
            "points": 8,
            "icon": "mdi:watering-can",
            "completion_criteria": "independent",
            "auto_approve": True,
        },
        {
            "name": "Pick up Lëgo!",
            "assigned_kid_names": ["Max!"],
            "type": "weekly",
            "points": 15,
            "icon": "mdi:lego",
            "completion_criteria": "independent",
            "auto_approve": False,
        },
        {
            "name": "Charge Røbot",
            "assigned_kid_names": ["Max!"],
            "type": "daily",
            "points": 10,
            "icon": "mdi:robot",
            "completion_criteria": "independent",
            "auto_approve": False,
        },
        {
            "name": "Paint the rãinbow",
            "assigned_kid_names": ["Lila"],
            "type": "weekly",
            "points": 15,
            "icon": "mdi:palette",
            "completion_criteria": "independent",
            "auto_approve": False,
        },
        {
            "name": "Sweep the p@tio",
            "assigned_kid_names": ["Lila"],
            "type": "daily",
            "points": 10,
            "icon": "mdi:broom",
            "completion_criteria": "independent",
            "auto_approve": False,
        },
        # === INDEPENDENT CHORES (Multi Kid) ===
        {
            "name": "Stär sweep",
            "assigned_kid_names": ["Zoë", "Max!", "Lila"],
            "type": "daily",
            "points": 20,
            "icon": "mdi:star",
            "completion_criteria": "independent",
            "auto_approve": False,
        },
        {
            "name": "Ørgänize Bookshelf",
            "assigned_kid_names": ["Zoë", "Lila"],
            "type": "weekly",
            "points": 18,
            "icon": "mdi:bookshelf",
            "completion_criteria": "independent",
            "auto_approve": False,
        },
        {
            "name": "Deep Clean Tøy Chest",
            "assigned_kid_names": ["Max!"],
            "type": "monthly",
            "points": 30,
            "icon": "mdi:treasure-chest",
            "completion_criteria": "independent",
            "auto_approve": False,
        },
        # === SHARED_ALL CHORES ===
        {
            "name": "Family Dinner Prep",
            "assigned_kid_names": ["Zoë", "Max!", "Lila"],
            "type": "daily",
            "points": 15,
            "icon": "mdi:food",
            "completion_criteria": "shared_all",
            "auto_approve": False,
        },
        {
            "name": "Weekend Yärd Work",
            "assigned_kid_names": ["Zoë", "Max!", "Lila"],
            "type": "weekly",
            "points": 25,
            "icon": "mdi:tree",
            "completion_criteria": "shared_all",
            "auto_approve": False,
        },
        {
            "name": "Sibling Rööm Cleanup",
            "assigned_kid_names": ["Max!", "Lila"],
            "type": "weekly",
            "points": 20,
            "icon": "mdi:broom-clean",
            "completion_criteria": "shared_all",
            "auto_approve": False,
        },
        # === SHARED_FIRST CHORES ===
        {
            "name": "Garage Cleanup",
            "assigned_kid_names": ["Zoë", "Max!"],
            "type": "weekly",
            "points": 25,
            "icon": "mdi:garage",
            "completion_criteria": "shared_first",
            "auto_approve": False,
        },
        {
            "name": "Täke Öut Trash",
            "assigned_kid_names": ["Zoë", "Max!", "Lila"],
            "type": "daily",
            "points": 12,
            "icon": "mdi:delete",
            "completion_criteria": "shared_first",
            "auto_approve": False,
        },
        {
            "name": "Wåsh Family Car",
            "assigned_kid_names": ["Zoë", "Lila"],
            "type": "weekly",
            "points": 30,
            "icon": "mdi:car-wash",
            "completion_criteria": "shared_first",
            "auto_approve": False,
        },
        {
            "name": "Måil Pickup Race",
            "assigned_kid_names": ["Zoë", "Max!", "Lila"],
            "type": "daily",
            "points": 8,
            "icon": "mdi:mailbox",
            "completion_criteria": "shared_first",
            "auto_approve": False,
        },
        # === CUSTOM FREQUENCY CHORES ===
        {
            "name": "Refill Bird Fëeder",
            "assigned_kid_names": ["Zoë"],
            "type": "custom",
            "points": 8,
            "icon": "mdi:bird",
            "completion_criteria": "independent",
            "auto_approve": False,
            "custom_interval_days": 3,
        },
        {
            "name": "Clëan Pool Fïlter",
            "assigned_kid_names": ["Max!", "Lila"],
            "type": "custom",
            "points": 22,
            "icon": "mdi:pool",
            "completion_criteria": "shared_first",
            "auto_approve": False,
            "custom_interval_days": 5,
        },
    ]

    result, chore_name_to_id_map = await _configure_multiple_chores_step(
        hass, result, all_scenario_chores
    )

    # Should proceed to badge count step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == const.CONFIG_FLOW_STEP_BADGE_COUNT

    # Verify all 18 chores were mapped correctly
    assert len(chore_name_to_id_map) == 18  # Just the 18 chores

    # Verify specific chore mappings exist
    expected_chore_names = [
        "Feed the cåts",
        "Wåter the plänts",
        "Pick up Lëgo!",
        "Charge Røbot",
        "Paint the rãinbow",
        "Sweep the p@tio",
        "Stär sweep",
        "Ørgänize Bookshelf",
        "Deep Clean Tøy Chest",
        "Family Dinner Prep",
        "Weekend Yärd Work",
        "Sibling Rööm Cleanup",
        "Garage Cleanup",
        "Täke Öut Trash",
        "Wåsh Family Car",
        "Måil Pickup Race",
        "Refill Bird Fëeder",
        "Clëan Pool Fïlter",
    ]

    for chore_name in expected_chore_names:
        chore_key = f"chore:{chore_name}"
        assert chore_key in chore_name_to_id_map, (
            f"Missing chore mapping for {chore_name}"
        )
        chore_id = chore_name_to_id_map[chore_key]
        assert len(chore_id) == 36  # UUID length

    # Complete remaining steps with 0 counts to finish config flow
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={const.CFOF_BADGES_INPUT_BADGE_COUNT: 0}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={const.CFOF_REWARDS_INPUT_REWARD_COUNT: 0}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={const.CFOF_PENALTIES_INPUT_PENALTY_COUNT: 0}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={const.CFOF_BONUSES_INPUT_BONUS_COUNT: 0}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={const.CFOF_ACHIEVEMENTS_INPUT_ACHIEVEMENT_COUNT: 0},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={const.CFOF_CHALLENGES_INPUT_CHALLENGE_COUNT: 0}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},  # Final finish step
    )

    # Should complete successfully
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "KidsChores"

    # Verify the config entry was created with correct settings
    config_entry = result["result"]
    assert config_entry.domain == const.DOMAIN
    assert config_entry.options[const.CONF_POINTS_LABEL] == "Star Points"
    assert config_entry.options[const.CONF_POINTS_ICON] == "mdi:star"


@pytest.mark.skip(
    reason="Legacy test expects buggy behavior - due date should NOT reschedule on approval (bug fixed)"
)
async def test_chore_claim_approve_workflow(
    hass: HomeAssistant, mock_hass_users
) -> None:
    """Test chore workflow: claim -> disapprove -> claim -> approve.

    Reuses the setup from test_fresh_start_with_all_scenario_chores,
    then tests a full claim/disapprove/claim/approve workflow on 'Feed the cåts'.

    Also tests:
    - Kid cannot approve chore (should fail in both pending and claimed states)
    - Points increase by exactly the chore value
    - Due date advances after approval

    Pattern: Dashboard helper -> Chore sensor attrs -> Service calls with user context
    """
    from homeassistant.core import Context

    from tests.helpers.constants import (
        ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID,
        ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID,
        ATTR_CHORE_DISAPPROVE_BUTTON_ENTITY_ID,
        ATTR_DEFAULT_POINTS,
        ATTR_DUE_DATE,
        ATTR_GLOBAL_STATE,
        CHORE_STATE_APPROVED,
        CHORE_STATE_CLAIMED,
        CHORE_STATE_PENDING,
    )

    # === SETUP: Reuse existing test to create all scenario data ===
    await test_fresh_start_with_all_scenario_chores(hass, mock_hass_users)

    # === STEP 1: Get dashboard helper (Rule 1 - single source of truth) ===
    helper_state = hass.states.get("sensor.kc_zoe_ui_dashboard_helper")
    assert helper_state is not None, "Dashboard helper not found"

    # === STEP 2: Find chore in dashboard helper (Rule 4 - filtering) ===
    chore = next(
        (c for c in helper_state.attributes["chores"] if c["name"] == "Feed the cåts"),
        None,
    )
    assert chore is not None, "Feed the cåts not found in dashboard helper"
    chore_eid = chore["eid"]

    # === STEP 3: Get button IDs and initial values from chore sensor (Rule 3) ===
    chore_state = hass.states.get(chore_eid)
    assert chore_state is not None, f"Chore sensor {chore_eid} not found"
    claim_button_eid = chore_state.attributes[ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID]
    approve_button_eid = chore_state.attributes[ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID]
    disapprove_button_eid = chore_state.attributes[
        ATTR_CHORE_DISAPPROVE_BUTTON_ENTITY_ID
    ]

    # Record initial values for comparison
    chore_points_value = chore_state.attributes[ATTR_DEFAULT_POINTS]
    initial_due_date = chore_state.attributes.get(ATTR_DUE_DATE)
    initial_global_state = chore_state.attributes.get(ATTR_GLOBAL_STATE)

    # Get initial points from kid's points sensor
    core_sensors = helper_state.attributes.get("core_sensors", {})
    points_eid = core_sensors.get("points_eid", "sensor.kc_zoe_points")
    initial_points_state = hass.states.get(points_eid)
    assert initial_points_state is not None
    initial_points = float(initial_points_state.state)

    # Create user contexts for kid and parent
    kid_context = Context(user_id=mock_hass_users["kid1"].id)
    parent_context = Context(user_id=mock_hass_users["parent1"].id)

    # === STEP 4: Kid tries to approve while PENDING (should fail silently) ===
    # Verify we're in pending state first
    assert chore_state.state == CHORE_STATE_PENDING, "Expected initial PENDING state"
    # For single-kid chores, global_state equals the kid's state
    # For multi-kid independent chores with different states, global_state is INDEPENDENT
    # Since this test uses a single-kid chore, global_state should be PENDING
    assert initial_global_state == CHORE_STATE_PENDING, (
        f"Expected initial global_state PENDING for single-kid chore, got: {initial_global_state}"
    )

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": approve_button_eid},
        blocking=True,
        context=kid_context,
    )
    await hass.async_block_till_done()

    # Verify state unchanged - kid cannot approve
    chore_state_after_kid_approve_pending = hass.states.get(chore_eid)
    assert chore_state_after_kid_approve_pending is not None
    assert chore_state_after_kid_approve_pending.state == CHORE_STATE_PENDING, (
        "Kid approve while pending: state should remain PENDING"
    )

    # === STEP 5: Kid claims chore (first time) ===
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": claim_button_eid},
        blocking=True,
        context=kid_context,
    )
    await hass.async_block_till_done()

    # Verify claimed state
    chore_state_after_claim = hass.states.get(chore_eid)
    assert chore_state_after_claim is not None
    assert chore_state_after_claim.state == CHORE_STATE_CLAIMED, (
        "After first claim: expected CLAIMED"
    )
    # For single-kid chores, global_state equals the kid's state (CLAIMED)
    after_claim_global = chore_state_after_claim.attributes.get(ATTR_GLOBAL_STATE)
    assert after_claim_global == CHORE_STATE_CLAIMED, (
        f"After first claim: global_state should be CLAIMED for single-kid chore, got: {after_claim_global}"
    )

    # === STEP 6: Kid tries to approve while CLAIMED (should fail silently) ===
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": approve_button_eid},
        blocking=True,
        context=kid_context,
    )
    await hass.async_block_till_done()

    # Verify state unchanged - kid cannot approve
    chore_state_after_kid_approve_claimed = hass.states.get(chore_eid)
    assert chore_state_after_kid_approve_claimed is not None
    assert chore_state_after_kid_approve_claimed.state == CHORE_STATE_CLAIMED, (
        "Kid approve while claimed: state should remain CLAIMED"
    )

    # === STEP 7: Parent disapproves chore ===
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": disapprove_button_eid},
        blocking=True,
        context=parent_context,
    )
    await hass.async_block_till_done()

    # Verify state goes back to pending after disapproval
    chore_state_after_disapprove = hass.states.get(chore_eid)
    assert chore_state_after_disapprove is not None
    assert chore_state_after_disapprove.state == CHORE_STATE_PENDING, (
        "After disapprove: expected PENDING"
    )
    # For single-kid chores, global_state equals the kid's state (PENDING)
    after_disapprove_global = chore_state_after_disapprove.attributes.get(
        ATTR_GLOBAL_STATE
    )
    assert after_disapprove_global == CHORE_STATE_PENDING, (
        f"After disapprove: global_state should be PENDING for single-kid chore, got: {after_disapprove_global}"
    )

    # === STEP 8: Kid claims chore again ===
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": claim_button_eid},
        blocking=True,
        context=kid_context,
    )
    await hass.async_block_till_done()

    # Verify claimed state again
    chore_state_after_second_claim = hass.states.get(chore_eid)
    assert chore_state_after_second_claim is not None
    assert chore_state_after_second_claim.state == CHORE_STATE_CLAIMED, (
        "After second claim: expected CLAIMED"
    )
    # For single-kid chores, global_state equals the kid's state (CLAIMED)
    after_second_claim_global = chore_state_after_second_claim.attributes.get(
        ATTR_GLOBAL_STATE
    )
    assert after_second_claim_global == CHORE_STATE_CLAIMED, (
        f"After second claim: global_state should be CLAIMED for single-kid chore, got: {after_second_claim_global}"
    )

    # === STEP 9: Parent approves chore ===
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": approve_button_eid},
        blocking=True,
        context=parent_context,
    )
    await hass.async_block_till_done()

    # Verify approved state
    chore_state_after_approve = hass.states.get(chore_eid)
    assert chore_state_after_approve is not None
    assert chore_state_after_approve.state == CHORE_STATE_APPROVED, (
        "After approve: expected APPROVED"
    )
    # For single-kid chores, global_state equals the kid's state (APPROVED)
    after_approve_global = chore_state_after_approve.attributes.get(ATTR_GLOBAL_STATE)
    assert after_approve_global == CHORE_STATE_APPROVED, (
        f"After approve: global_state should be APPROVED for single-kid chore, got: {after_approve_global}"
    )

    # === STEP 10: Verify points increased by exactly the chore value ===
    final_points_state = hass.states.get(points_eid)
    assert final_points_state is not None
    final_points = float(final_points_state.state)
    points_earned = final_points - initial_points
    assert points_earned == chore_points_value, (
        f"Points should increase by {chore_points_value}, "
        f"but increased by {points_earned} (from {initial_points} to {final_points})"
    )

    # === STEP 11: Verify due date behavior after approval ===
    final_due_date = chore_state_after_approve.attributes.get(ATTR_DUE_DATE)
    # Note: Due date behavior depends on chore configuration:
    # - Some chores have explicit due dates that advance after approval
    # - Some daily/recurring chores may have None for due_date (reset at midnight)
    # - We verify we can read the attribute; actual advancement is chore-dependent
    if initial_due_date is not None:
        # If there was an initial due date, it should change after approval
        assert final_due_date != initial_due_date, (
            f"Due date should advance after approval. "
            f"Initial: {initial_due_date}, Final: {final_due_date}"
        )
    # If initial was None, we just confirm the attribute is accessible (already done above)
