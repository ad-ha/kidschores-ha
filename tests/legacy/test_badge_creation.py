"""Test badge creation functionality following testing agent instructions."""

import asyncio

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    AWARD_ITEMS_KEY_POINTS,
    AWARD_ITEMS_KEY_POINTS_MULTIPLIER,
    BADGE_TYPE_CUMULATIVE,
    BADGE_TYPE_DAILY,
    BADGE_TYPE_PERIODIC,
    BADGE_TYPE_SPECIAL_OCCASION,
    CFOF_BADGES_INPUT_ASSIGNED_TO,
    CFOF_BADGES_INPUT_AWARD_ITEMS,
    CFOF_BADGES_INPUT_AWARD_POINTS,
    CFOF_BADGES_INPUT_END_DATE,
    CFOF_BADGES_INPUT_ICON,
    CFOF_BADGES_INPUT_MAINTENANCE_RULES,
    CFOF_BADGES_INPUT_NAME,
    CFOF_BADGES_INPUT_OCCASION_TYPE,
    CFOF_BADGES_INPUT_POINTS_MULTIPLIER,
    CFOF_BADGES_INPUT_RESET_SCHEDULE_RECURRING_FREQUENCY,
    CFOF_BADGES_INPUT_START_DATE,
    CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE,
    CFOF_BADGES_INPUT_TYPE,
    COORDINATOR,
    DATA_BADGE_AWARDS,
    DATA_BADGE_AWARDS_POINT_MULTIPLIER,
    DATA_BADGE_ICON,
    DATA_BADGE_MAINTENANCE_RULES,
    DATA_BADGE_NAME,
    DATA_BADGE_RESET_SCHEDULE,
    DATA_BADGE_RESET_SCHEDULE_END_DATE,
    DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY,
    DATA_BADGE_RESET_SCHEDULE_START_DATE,
    DATA_BADGE_SPECIAL_OCCASION_TYPE,
    DATA_BADGE_TARGET,
    DATA_BADGE_TARGET_THRESHOLD_VALUE,
    DATA_BADGE_TYPE,
    DATA_BADGES,
    DOMAIN,
    FREQUENCY_CUSTOM,
    OPTIONS_FLOW_ACTIONS_ADD,
    OPTIONS_FLOW_BADGES,
    OPTIONS_FLOW_INPUT_MANAGE_ACTION,
    OPTIONS_FLOW_INPUT_MENU_SELECTION,
    OPTIONS_FLOW_STEP_ADD_BADGE_CUMULATIVE,
    OPTIONS_FLOW_STEP_ADD_BADGE_DAILY,
    OPTIONS_FLOW_STEP_ADD_BADGE_PERIODIC,
    OPTIONS_FLOW_STEP_ADD_BADGE_SPECIAL,
    OPTIONS_FLOW_STEP_INIT,
    OPTIONS_FLOW_STEP_MANAGE_ENTITY,
)

# pylint: disable=protected-access  # Accessing coordinator internals for testing


class TestBadgeCreation:
    """Test badge creation through options flow and coordinator."""

    async def test_create_cumulative_badge_via_options_flow(
        self,
        hass: HomeAssistant,
        scenario_medium: tuple[MockConfigEntry, dict[str, str]],
    ) -> None:
        """Test creating a cumulative badge via options flow creates badge in coordinator."""
        # Arrange: Use medium scenario with kids pre-loaded
        config_entry, name_to_id_map = scenario_medium
        assert config_entry.state == ConfigEntryState.LOADED
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        initial_badges = coordinator._data.get(DATA_BADGES, {}).copy()
        zoe_id = name_to_id_map["kid:Zoë"]

        # Act: Navigate to badge creation flow
        result = await hass.config_entries.options.async_init(config_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_BADGES},
        )

        assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_ENTITY

        # Select "Add" action to create new badge
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
        )

        # Select cumulative badge type
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input={CFOF_BADGES_INPUT_TYPE: BADGE_TYPE_CUMULATIVE},
        )

        assert result.get("step_id") == OPTIONS_FLOW_STEP_ADD_BADGE_CUMULATIVE

        # Create the cumulative badge with test data
        badge_test_data = {
            CFOF_BADGES_INPUT_NAME: "Test Star Badge",
            CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE: 100,
            CFOF_BADGES_INPUT_ICON: "mdi:star-outline",
            CFOF_BADGES_INPUT_AWARD_POINTS: 25.0,
            CFOF_BADGES_INPUT_ASSIGNED_TO: [zoe_id],
        }

        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input=badge_test_data,
        )

        # Assert: Flow completes successfully
        assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

        # Assert: Badge was created in coordinator data
        current_badges = coordinator._data.get(DATA_BADGES, {})
        assert len(current_badges) == len(initial_badges) + 1

        # Find the new badge by comparing with initial badges
        new_badge_id = None
        for badge_id in current_badges:
            if badge_id not in initial_badges:
                new_badge_id = badge_id
                break

        assert new_badge_id is not None, "New badge should be created"

        # Assert: Badge has correct data structure and values
        new_badge = current_badges[new_badge_id]
        assert new_badge[DATA_BADGE_NAME] == "Test Star Badge"
        assert new_badge[DATA_BADGE_TYPE] == BADGE_TYPE_CUMULATIVE
        # Check nested target structure
        assert DATA_BADGE_TARGET in new_badge
        assert new_badge[DATA_BADGE_TARGET][DATA_BADGE_TARGET_THRESHOLD_VALUE] == 100
        assert new_badge[DATA_BADGE_ICON] == "mdi:star-outline"
        # Award points may be stored in awards structure
        assert (
            new_badge.get("awards", {}).get(DATA_BADGE_AWARDS_POINT_MULTIPLIER)
            is not None
            or new_badge.get("awards", {}).get("award_points") is not None
        )

    async def test_create_periodic_badge_via_options_flow(
        self,
        hass: HomeAssistant,
        scenario_medium: tuple[MockConfigEntry, dict[str, str]],
    ) -> None:
        """Test creating a periodic badge via options flow creates badge in coordinator."""
        # Arrange: Use medium scenario with kids pre-loaded
        config_entry, name_to_id_map = scenario_medium
        assert config_entry.state == ConfigEntryState.LOADED
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        initial_badges = coordinator._data.get(DATA_BADGES, {}).copy()
        zoe_id = name_to_id_map["kid:Zoë"]

        # Act: Navigate to badge creation flow
        result = await hass.config_entries.options.async_init(config_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_BADGES},
        )

        # Select "Add" action to create new badge
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
        )

        # Select periodic badge type
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input={CFOF_BADGES_INPUT_TYPE: BADGE_TYPE_PERIODIC},
        )

        # Create the periodic badge with test data
        badge_test_data = {
            CFOF_BADGES_INPUT_NAME: "Weekly Wonder",
            CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE: 7,
            CFOF_BADGES_INPUT_ICON: "mdi:calendar-week",
            CFOF_BADGES_INPUT_AWARD_POINTS: 50.0,
            CFOF_BADGES_INPUT_ASSIGNED_TO: [zoe_id],
        }

        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input=badge_test_data,
        )

        # Assert: Flow completes successfully
        assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

        # Assert: Badge was created in coordinator data
        current_badges = coordinator._data.get(DATA_BADGES, {})
        assert len(current_badges) == len(initial_badges) + 1

        # Find the new badge by comparing with initial badges
        new_badge_id = None
        for badge_id in current_badges:
            if badge_id not in initial_badges:
                new_badge_id = badge_id
                break

        assert new_badge_id is not None, "New badge should be created"

        # Assert: Badge has correct data structure and values
        new_badge = current_badges[new_badge_id]
        assert new_badge[DATA_BADGE_NAME] == "Weekly Wonder"
        assert new_badge[DATA_BADGE_TYPE] == BADGE_TYPE_PERIODIC
        # Check nested target structure
        assert DATA_BADGE_TARGET in new_badge
        assert new_badge[DATA_BADGE_TARGET][DATA_BADGE_TARGET_THRESHOLD_VALUE] == 7
        assert new_badge[DATA_BADGE_ICON] == "mdi:calendar-week"

    async def test_badge_creation_minimal_scenario(
        self,
        hass: HomeAssistant,
        scenario_medium: tuple[MockConfigEntry, dict[str, str]],
    ) -> None:
        """Test badge creation via options flow with medium scenario data loaded."""
        # Arrange: Use medium scenario fixture with kids pre-loaded
        config_entry, name_to_id_map = scenario_medium
        zoe_id = name_to_id_map["kid:Zoë"]
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

        # Assert: Minimal scenario has the expected existing badge count
        initial_badges = coordinator._data.get(DATA_BADGES, {}).copy()
        initial_badge_count = len(initial_badges)

        # Find the Brønze Står badge from minimal scenario to verify it exists
        bronze_star_badge = None
        for badge_id, badge_data in initial_badges.items():
            if badge_data.get(DATA_BADGE_NAME) == "Brønze Står":
                bronze_star_badge = badge_data
                break

        assert bronze_star_badge is not None, (
            "Minimal scenario should include Brønze Står badge"
        )
        assert bronze_star_badge[DATA_BADGE_TYPE] == BADGE_TYPE_CUMULATIVE
        # Check nested target structure
        assert DATA_BADGE_TARGET in bronze_star_badge
        assert (
            bronze_star_badge[DATA_BADGE_TARGET][DATA_BADGE_TARGET_THRESHOLD_VALUE]
            == 400
        )
        assert bronze_star_badge[DATA_BADGE_ICON] == "mdi:star"

        # Act: Create additional badge via options flow
        result = await hass.config_entries.options.async_init(config_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_BADGES},
        )

        # Navigate to add badge option
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
        )

        # Step 1: Select badge type
        badge_type_input = {
            CFOF_BADGES_INPUT_TYPE: BADGE_TYPE_CUMULATIVE,
        }
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], badge_type_input
        )
        assert result.get("type") == FlowResultType.FORM

        # Step 2: Complete badge details form
        badge_details_input = {
            CFOF_BADGES_INPUT_NAME: "Silver Star",
            CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE: 800,
            CFOF_BADGES_INPUT_ICON: "mdi:star-circle",
            CFOF_BADGES_INPUT_POINTS_MULTIPLIER: 1.15,
            CFOF_BADGES_INPUT_ASSIGNED_TO: [zoe_id],
        }

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], badge_details_input
        )
        # Options flow returns to main menu after creating badge (not CREATE_ENTRY)
        assert result.get("type") == FlowResultType.FORM
        assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

        # Wait for coordinator to update
        await hass.async_block_till_done()
        await coordinator.async_request_refresh()
        await hass.async_block_till_done()

        # Assert: Badge was created successfully
        current_badges = coordinator._data.get(DATA_BADGES, {})

        assert len(current_badges) == initial_badge_count + 1, (
            f"Expected {initial_badge_count + 1} badges, got {len(current_badges)}. "
            f"Initial: {list(initial_badges.keys())}, "
            f"Current: {list(current_badges.keys())}"
        )

        # Find the newly created badge
        new_badge_id = None
        for badge_id in current_badges:
            if badge_id not in initial_badges:
                new_badge_id = badge_id
                break

        assert new_badge_id is not None, (
            f"New badge should be created. "
            f"Initial badge count: {initial_badge_count}, "
            f"Current badge count: {len(current_badges)}. "
            f"Initial badges: {list(initial_badges.keys())}, "
            f"Current badges: {list(current_badges.keys())}"
        )

        # Assert: Badge has correct data structure and values
        new_badge = current_badges[new_badge_id]
        assert new_badge[DATA_BADGE_NAME] == "Silver Star"
        assert new_badge[DATA_BADGE_TYPE] == BADGE_TYPE_CUMULATIVE
        # Check nested target structure
        assert DATA_BADGE_TARGET in new_badge
        assert new_badge[DATA_BADGE_TARGET][DATA_BADGE_TARGET_THRESHOLD_VALUE] == 800
        assert new_badge[DATA_BADGE_ICON] == "mdi:star-circle"

    async def test_comprehensive_badge_creation_all_types(
        self,
        hass: HomeAssistant,
        scenario_medium: tuple[MockConfigEntry, dict[str, str]],
    ) -> None:
        """Test comprehensive badge creation covering all badge types from scenarios."""
        # Arrange: Use medium scenario fixture with comprehensive test data
        config_entry, name_to_id_map = scenario_medium
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        zoe_id = name_to_id_map["kid:Zoë"]

        # Define all badge types to test (based on medium/full scenarios)
        badge_test_cases = [
            {
                "name": "Platinum Achievement",
                "type": BADGE_TYPE_CUMULATIVE,
                "step_id": OPTIONS_FLOW_STEP_ADD_BADGE_CUMULATIVE,
                "data": {
                    CFOF_BADGES_INPUT_NAME: "Platinum Achievement",
                    CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE: 400,
                    CFOF_BADGES_INPUT_ICON: "mdi:star",
                    CFOF_BADGES_INPUT_AWARD_ITEMS: [AWARD_ITEMS_KEY_POINTS_MULTIPLIER],
                    CFOF_BADGES_INPUT_POINTS_MULTIPLIER: 1.05,
                    CFOF_BADGES_INPUT_MAINTENANCE_RULES: 300,
                    CFOF_BADGES_INPUT_ASSIGNED_TO: [zoe_id],
                },
                "entity_id": "sensor.kc_platinum_achievement_badge",
            },
            {
                "name": "Diamond Excellence",
                "type": BADGE_TYPE_CUMULATIVE,
                "step_id": OPTIONS_FLOW_STEP_ADD_BADGE_CUMULATIVE,
                "data": {
                    CFOF_BADGES_INPUT_NAME: "Diamond Excellence",
                    CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE: 800,
                    CFOF_BADGES_INPUT_ICON: "mdi:star-circle",
                    CFOF_BADGES_INPUT_AWARD_ITEMS: [AWARD_ITEMS_KEY_POINTS_MULTIPLIER],
                    CFOF_BADGES_INPUT_POINTS_MULTIPLIER: 1.15,
                    CFOF_BADGES_INPUT_MAINTENANCE_RULES: 600,
                    CFOF_BADGES_INPUT_ASSIGNED_TO: [zoe_id],
                },
                "entity_id": "sensor.kc_diamond_excellence_badge",
            },
            {
                "name": "Titanium Master",
                "type": BADGE_TYPE_CUMULATIVE,
                "step_id": OPTIONS_FLOW_STEP_ADD_BADGE_CUMULATIVE,
                "data": {
                    CFOF_BADGES_INPUT_NAME: "Titanium Master",
                    CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE: 1600,
                    CFOF_BADGES_INPUT_ICON: "mdi:star-four-points",
                    CFOF_BADGES_INPUT_AWARD_ITEMS: [AWARD_ITEMS_KEY_POINTS_MULTIPLIER],
                    CFOF_BADGES_INPUT_POINTS_MULTIPLIER: 1.25,
                    CFOF_BADGES_INPUT_MAINTENANCE_RULES: 1200,
                    CFOF_BADGES_INPUT_ASSIGNED_TO: [zoe_id],
                },
                "entity_id": "sensor.kc_titanium_master_badge",
            },
            {
                "name": "Monday Master",
                "type": BADGE_TYPE_PERIODIC,
                "step_id": OPTIONS_FLOW_STEP_ADD_BADGE_PERIODIC,
                "data": {
                    CFOF_BADGES_INPUT_NAME: "Monday Master",
                    CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE: 10,
                    CFOF_BADGES_INPUT_ICON: "mdi:calendar-week",
                    CFOF_BADGES_INPUT_RESET_SCHEDULE_RECURRING_FREQUENCY: "weekly",
                    CFOF_BADGES_INPUT_START_DATE: "2025-10-01",
                    CFOF_BADGES_INPUT_END_DATE: "2025-12-31",
                    CFOF_BADGES_INPUT_ASSIGNED_TO: [zoe_id],
                },
                "entity_id": "sensor.kc_monday_master_badge",
            },
            {
                "name": "Morning Champion",
                "type": BADGE_TYPE_DAILY,
                "step_id": OPTIONS_FLOW_STEP_ADD_BADGE_DAILY,
                "data": {
                    CFOF_BADGES_INPUT_NAME: "Morning Champion",
                    CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE: 2,
                    CFOF_BADGES_INPUT_ICON: "mdi:emoticon-happy",
                    CFOF_BADGES_INPUT_AWARD_ITEMS: [AWARD_ITEMS_KEY_POINTS],
                    CFOF_BADGES_INPUT_AWARD_POINTS: 3.0,
                    CFOF_BADGES_INPUT_ASSIGNED_TO: [zoe_id],
                },
                "entity_id": "sensor.kc_morning_champion_badge",
            },
            {
                "name": "Celebration Star",
                "type": BADGE_TYPE_SPECIAL_OCCASION,
                "step_id": OPTIONS_FLOW_STEP_ADD_BADGE_SPECIAL,
                "data": {
                    CFOF_BADGES_INPUT_NAME: "Celebration Star",
                    CFOF_BADGES_INPUT_ICON: "mdi:party-popper",
                    CFOF_BADGES_INPUT_OCCASION_TYPE: "birthday",
                    CFOF_BADGES_INPUT_RESET_SCHEDULE_RECURRING_FREQUENCY: "none",
                    CFOF_BADGES_INPUT_ASSIGNED_TO: [zoe_id],
                },
                "entity_id": "sensor.kc_celebration_star_badge",
            },
        ]

        initial_badges = coordinator._data.get(DATA_BADGES, {}).copy()
        initial_badge_count = len(initial_badges)
        created_badge_ids = []

        # Act: Create each badge type through options flow
        for test_case in badge_test_cases:
            coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
            badges_before = set(coordinator._data.get(DATA_BADGES, {}).keys())

            # Navigate to badge creation flow
            result = await hass.config_entries.options.async_init(config_entry.entry_id)
            result = await hass.config_entries.options.async_configure(
                result.get("flow_id"),
                user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_BADGES},
            )

            # Select "Add" action
            result = await hass.config_entries.options.async_configure(
                result.get("flow_id"),
                user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
            )

            # Select badge type
            result = await hass.config_entries.options.async_configure(
                result.get("flow_id"),
                user_input={CFOF_BADGES_INPUT_TYPE: test_case["type"]},
            )

            assert result.get("step_id") == test_case["step_id"]

            # Create badge with test data
            result = await hass.config_entries.options.async_configure(
                result.get("flow_id"),
                user_input=test_case["data"],
            )

            # Flow should return to main menu
            assert result.get("type") == FlowResultType.FORM, (
                f"Expected form result for {test_case['name']}, got {result.get('type')}. "
                f"Errors: {result.get('errors', {})}"
            )
            assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT, (
                f"Expected step_id {OPTIONS_FLOW_STEP_INIT} for {test_case['name']}, got {result.get('step_id')}"
            )

            # Options flow reloads the config entry; re-fetch the coordinator
            await hass.async_block_till_done()
            coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

            # Wait for coordinator to update
            await asyncio.sleep(
                0.3
            )  # Allow time for data propagation and storage flush
            await coordinator.async_refresh()
            await hass.async_block_till_done()

            # Additional wait for storage to be persisted to disk
            await asyncio.sleep(0.2)

            # Verify badge was created by checking if entity exists in registry
            entity_registry = er.async_get(hass)
            badge_entity = entity_registry.async_get(test_case["entity_id"])

            assert badge_entity is not None, (
                f"Expected badge entity {test_case['entity_id']} not found in entity registry"
            )
            assert badge_entity.domain == "sensor", (
                f"Expected sensor domain, got {badge_entity.domain}"
            )

            badges_after = set(coordinator._data.get(DATA_BADGES, {}).keys())
            new_badge_ids = badges_after - badges_before
            assert len(new_badge_ids) == 1, (
                f"Expected exactly one new badge for {test_case['name']}, got {new_badge_ids}"
            )
            created_badge_ids.append(next(iter(new_badge_ids)))

        # Assert: All badges were created in coordinator data
        coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
        final_badges = coordinator._data.get(DATA_BADGES, {})
        assert len(final_badges) == initial_badge_count + len(badge_test_cases), (
            "All badges should be created"
        )

        # Validate each created badge's data and entity
        for badge_id, test_case in zip(created_badge_ids, badge_test_cases):
            badge_data = final_badges[badge_id]

            # Common assertions for all badge types
            assert badge_data[DATA_BADGE_NAME] == test_case["name"]
            assert badge_data[DATA_BADGE_TYPE] == test_case["type"]
            assert (
                badge_data[DATA_BADGE_ICON] == test_case["data"][CFOF_BADGES_INPUT_ICON]
            )

            # Type-specific assertions
            if test_case["type"] == BADGE_TYPE_CUMULATIVE:
                assert (
                    badge_data[DATA_BADGE_TARGET][DATA_BADGE_TARGET_THRESHOLD_VALUE]
                    == (test_case["data"][CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE])
                )
                if CFOF_BADGES_INPUT_POINTS_MULTIPLIER in test_case["data"]:
                    assert (
                        badge_data[DATA_BADGE_AWARDS][
                            DATA_BADGE_AWARDS_POINT_MULTIPLIER
                        ]
                        == (test_case["data"][CFOF_BADGES_INPUT_POINTS_MULTIPLIER])
                    )
                if CFOF_BADGES_INPUT_MAINTENANCE_RULES in test_case["data"]:
                    assert (
                        badge_data[DATA_BADGE_TARGET][DATA_BADGE_MAINTENANCE_RULES]
                        == (test_case["data"][CFOF_BADGES_INPUT_MAINTENANCE_RULES])
                    )

            elif test_case["type"] == BADGE_TYPE_PERIODIC:
                assert (
                    badge_data[DATA_BADGE_TARGET][DATA_BADGE_TARGET_THRESHOLD_VALUE]
                    == (test_case["data"][CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE])
                )
                if (
                    CFOF_BADGES_INPUT_RESET_SCHEDULE_RECURRING_FREQUENCY
                    in test_case["data"]
                ):
                    expected_frequency = test_case["data"][
                        CFOF_BADGES_INPUT_RESET_SCHEDULE_RECURRING_FREQUENCY
                    ]
                    assert (
                        badge_data[DATA_BADGE_RESET_SCHEDULE][
                            DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY
                        ]
                        == expected_frequency
                    )

                    # Reset schedule dates are only persisted for custom frequency.
                    # For other modes (weekly/monthly/etc), validation clears the start
                    # date and the integration treats dates as unset.
                    if expected_frequency == FREQUENCY_CUSTOM:
                        if CFOF_BADGES_INPUT_START_DATE in test_case["data"]:
                            assert (
                                badge_data[DATA_BADGE_RESET_SCHEDULE][
                                    DATA_BADGE_RESET_SCHEDULE_START_DATE
                                ]
                                == (test_case["data"][CFOF_BADGES_INPUT_START_DATE])
                            )
                        if CFOF_BADGES_INPUT_END_DATE in test_case["data"]:
                            assert (
                                badge_data[DATA_BADGE_RESET_SCHEDULE][
                                    DATA_BADGE_RESET_SCHEDULE_END_DATE
                                ]
                                == (test_case["data"][CFOF_BADGES_INPUT_END_DATE])
                            )
                    else:
                        assert (
                            badge_data[DATA_BADGE_RESET_SCHEDULE][
                                DATA_BADGE_RESET_SCHEDULE_START_DATE
                            ]
                            is None
                        )

            elif test_case["type"] == BADGE_TYPE_DAILY:
                assert (
                    badge_data[DATA_BADGE_TARGET][DATA_BADGE_TARGET_THRESHOLD_VALUE]
                    == (test_case["data"][CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE])
                )

            elif test_case["type"] == BADGE_TYPE_SPECIAL_OCCASION:
                assert (
                    badge_data[DATA_BADGE_TARGET][DATA_BADGE_TARGET_THRESHOLD_VALUE]
                    == 1
                ), "Special occasion badges force threshold to 1"
                assert (
                    badge_data[DATA_BADGE_SPECIAL_OCCASION_TYPE]
                    == test_case["data"][CFOF_BADGES_INPUT_OCCASION_TYPE]
                )

            # Assert: Badge entity was created
            badge_entity_state = hass.states.get(test_case["entity_id"])
            assert badge_entity_state is not None, (
                f"Badge entity {test_case['entity_id']} should exist"
            )
            assert badge_entity_state.attributes.get("badge_type") == test_case["type"]
            assert (
                badge_entity_state.attributes.get("icon")
                == (test_case["data"][CFOF_BADGES_INPUT_ICON])
            )

        # Assert: Kid badge sensor exists and is updated
        kid_badge_entity_id = "sensor.kc_zoe_badges"  # Normalized entity ID
        kid_badge_state = hass.states.get(kid_badge_entity_id)
        assert kid_badge_state is not None, (
            f"Kid badge sensor {kid_badge_entity_id} should exist"
        )

        # Note: Individual badge entities and kid badge progress validation
        # completed above in the per-badge validation loop
