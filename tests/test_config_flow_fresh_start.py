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

from typing import Any
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType

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

        # TODO: Verify that storage contains 1 kid (Zoë) with correct data
        # This will require accessing the coordinator after setup completes


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
        for step, input_key, next_step in [
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
                const.CFOF_SYSTEM_INPUT_POINTS_LABEL: "Family Points",
                const.CFOF_SYSTEM_INPUT_POINTS_ICON: "mdi:star-circle",
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
        assert result["step_id"] == const.CONFIG_FLOW_STEP_PARENTS  # Still on parents step

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
        assert config_entry.options[const.CONF_POINTS_LABEL] == "Family Points"
        assert config_entry.options[const.CONF_POINTS_ICON] == "mdi:star-circle"

        # In a real scenario:
        # Kid "Lila" - HA user: kid3, notifications: mobile disabled, persistent disabled
        # Parent "Môm Astrid Stârblüm" - HA user: parent1, notifications: all disabled, associated: ["Lila"]
        # Parent "Dad Leo" - HA user: parent2, mobile notifications enabled, associated: ["Lila"]


@pytest.mark.asyncio
async def test_fresh_start_basic_family(hass: HomeAssistant) -> None:
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
async def test_fresh_start_full_scenario(hass: HomeAssistant) -> None:
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
            const.CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE: mobile_notify_service if enable_mobile_notifications else const.SENTINEL_EMPTY,
            const.CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS: enable_persistent_notifications,
        },
    )


async def _skip_all_entity_steps(hass: HomeAssistant, result: Any) -> Any:
    """Skip all entity configuration steps by setting counts to 0.

    Args:
        hass: Home Assistant instance
        result: Current config flow result

    Returns:
        Updated config flow result ready for finish step
    """
    for step, input_key, next_step in [
        (const.CONFIG_FLOW_STEP_CHORE_COUNT, const.CFOF_CHORES_INPUT_CHORE_COUNT, const.CONFIG_FLOW_STEP_BADGE_COUNT),
        (const.CONFIG_FLOW_STEP_BADGE_COUNT, const.CFOF_BADGES_INPUT_BADGE_COUNT, const.CONFIG_FLOW_STEP_REWARD_COUNT),
        (const.CONFIG_FLOW_STEP_REWARD_COUNT, const.CFOF_REWARDS_INPUT_REWARD_COUNT, const.CONFIG_FLOW_STEP_PENALTY_COUNT),
        (const.CONFIG_FLOW_STEP_PENALTY_COUNT, const.CFOF_PENALTIES_INPUT_PENALTY_COUNT, const.CONFIG_FLOW_STEP_BONUS_COUNT),
        (const.CONFIG_FLOW_STEP_BONUS_COUNT, const.CFOF_BONUSES_INPUT_BONUS_COUNT, const.CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT),
        (const.CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT, const.CFOF_ACHIEVEMENTS_INPUT_ACHIEVEMENT_COUNT, const.CONFIG_FLOW_STEP_CHALLENGE_COUNT),
        (const.CONFIG_FLOW_STEP_CHALLENGE_COUNT, const.CFOF_CHALLENGES_INPUT_CHALLENGE_COUNT, const.CONFIG_FLOW_STEP_FINISH),
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
    associated_kids_field = data_schema.schema.get(const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS)
    assert associated_kids_field is not None, "associated_kids field not found in schema"

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
        associated_kids_field = data_schema.schema.get(const.CONF_ASSOCIATED_KIDS_LEGACY)
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
            const.CONF_PARENT_NAME_LEGACY: "Jane Parent",
            const.CONF_HA_USER_ID_LEGACY: parent_user.id,
            const.CONF_ASSOCIATED_KIDS_LEGACY: [kid_id],  # Use the captured kid ID
            const.CONF_ENABLE_MOBILE_NOTIFICATIONS_LEGACY: True,
            const.CONF_MOBILE_NOTIFY_SERVICE_LEGACY: "notify.mobile_app_jane_phone",  # Include notify. prefix
            const.CONF_ENABLE_PERSISTENT_NOTIFICATIONS_LEGACY: True,
        }

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=parent_input
        )
        assert result["type"] == FlowResultType.FORM
        # Should move to entities setup - let's see what the next step is
        assert result["step_id"] == const.CONFIG_FLOW_STEP_CHORE_COUNT

        # Skip all remaining entity steps
        for step, input_key, next_step in [
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

        # TODO: Verify that storage contains:
        # - 1 kid: "Alex" with HA user ID and no notifications
        # - 1 parent: "Jane Parent" with HA user ID, mobile notifications, associated with Alex
        # This will require accessing the coordinator after setup completes


# Future test ideas:
# - test_fresh_start_badges_and_rewards: Focus on badge/reward system
# - test_fresh_start_challenges_and_achievements: Focus on advanced features
# - test_fresh_start_error_handling: Test validation and error paths
# - test_fresh_start_different_themes: Test various points labels/icons
