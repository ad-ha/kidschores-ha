"""Comprehensive tests for KidsChores options flow - all entity types."""

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    ACHIEVEMENT_TYPE_TOTAL,
    BADGE_TYPE_CUMULATIVE,
    BADGE_TYPE_PERIODIC,
    CFOF_ACHIEVEMENTS_INPUT_ASSIGNED_KIDS,
    CFOF_ACHIEVEMENTS_INPUT_CRITERIA,
    CFOF_ACHIEVEMENTS_INPUT_DESCRIPTION,
    CFOF_ACHIEVEMENTS_INPUT_ICON,
    CFOF_ACHIEVEMENTS_INPUT_NAME,
    CFOF_ACHIEVEMENTS_INPUT_REWARD_POINTS,
    CFOF_ACHIEVEMENTS_INPUT_TARGET_VALUE,
    CFOF_ACHIEVEMENTS_INPUT_TYPE,
    CFOF_BADGES_INPUT_ASSIGNED_TO,
    CFOF_BADGES_INPUT_AWARD_POINTS,
    CFOF_BADGES_INPUT_END_DATE,
    CFOF_BADGES_INPUT_ICON,
    CFOF_BADGES_INPUT_NAME,
    CFOF_BADGES_INPUT_START_DATE,
    CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE,
    CFOF_BADGES_INPUT_TARGET_TYPE,
    CFOF_BADGES_INPUT_TYPE,
    CFOF_BONUSES_INPUT_DESCRIPTION,
    CFOF_BONUSES_INPUT_ICON,
    CFOF_BONUSES_INPUT_NAME,
    CFOF_BONUSES_INPUT_POINTS,
    CFOF_CHALLENGES_INPUT_ASSIGNED_KIDS,
    CFOF_CHALLENGES_INPUT_CRITERIA,
    CFOF_CHALLENGES_INPUT_DESCRIPTION,
    CFOF_CHALLENGES_INPUT_END_DATE,
    CFOF_CHALLENGES_INPUT_ICON,
    CFOF_CHALLENGES_INPUT_NAME,
    CFOF_CHALLENGES_INPUT_REWARD_POINTS,
    CFOF_CHALLENGES_INPUT_START_DATE,
    CFOF_CHALLENGES_INPUT_TARGET_VALUE,
    CFOF_CHALLENGES_INPUT_TYPE,
    CFOF_CHORES_INPUT_ASSIGNED_KIDS,
    CFOF_CHORES_INPUT_DEFAULT_POINTS,
    CFOF_CHORES_INPUT_NAME,
    CFOF_KIDS_INPUT_KID_NAME,
    CFOF_PARENTS_INPUT_NAME,
    CFOF_PENALTIES_INPUT_DESCRIPTION,
    CFOF_PENALTIES_INPUT_ICON,
    CFOF_PENALTIES_INPUT_NAME,
    CFOF_PENALTIES_INPUT_POINTS,
    CFOF_REWARDS_INPUT_COST,
    CFOF_REWARDS_INPUT_NAME,
    CHALLENGE_TYPE_DAILY_MIN,
    OPTIONS_FLOW_ACHIEVEMENTS,
    OPTIONS_FLOW_ACTIONS_ADD,
    OPTIONS_FLOW_ACTIONS_EDIT,
    OPTIONS_FLOW_BADGES,
    OPTIONS_FLOW_BONUSES,
    OPTIONS_FLOW_CHALLENGES,
    OPTIONS_FLOW_CHORES,
    OPTIONS_FLOW_INPUT_ENTITY_NAME,
    OPTIONS_FLOW_INPUT_MANAGE_ACTION,
    OPTIONS_FLOW_INPUT_MENU_SELECTION,
    OPTIONS_FLOW_KIDS,
    OPTIONS_FLOW_PARENTS,
    OPTIONS_FLOW_PENALTIES,
    OPTIONS_FLOW_REWARDS,
    OPTIONS_FLOW_STEP_ADD_ACHIEVEMENT,
    OPTIONS_FLOW_STEP_ADD_BADGE_CUMULATIVE,
    OPTIONS_FLOW_STEP_ADD_BADGE_PERIODIC,
    OPTIONS_FLOW_STEP_ADD_BONUS,
    OPTIONS_FLOW_STEP_ADD_CHALLENGE,
    OPTIONS_FLOW_STEP_ADD_CHORE,
    OPTIONS_FLOW_STEP_ADD_PARENT,
    OPTIONS_FLOW_STEP_ADD_PENALTY,
    OPTIONS_FLOW_STEP_ADD_REWARD,
    OPTIONS_FLOW_STEP_EDIT_CHORE,
    OPTIONS_FLOW_STEP_INIT,
    OPTIONS_FLOW_STEP_MANAGE_ENTITY,
)


async def test_options_flow_add_parent(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test adding a parent via options flow."""
    # Navigate to parents management
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_PARENTS},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_ENTITY

    # Select "Add" action
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_ADD_PARENT

    # Add the parent
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_PARENTS_INPUT_NAME: "Môm Astrid"},
    )

    # Should return to main menu after successful add
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_add_chore(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test adding a chore via options flow.

    Uses scenario_minimal fixture (testdata_scenario_minimal.yaml): Adds kid 'Zoë' first, then adds chore 'Feed the cåts'
    assigned to Zoë. Tests new validation requiring at least one kid assigned.
    """
    # First, add a kid so we have someone to assign the chore to
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_KIDS},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_ENTITY

    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )

    # Add kid "Zoë" from scenario_minimal (testdata_scenario_minimal.yaml)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_KIDS_INPUT_KID_NAME: "Zoë"},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

    # Now navigate to chores management
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_CHORES},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_ENTITY

    # Select "Add" action
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_ADD_CHORE

    # Add chore "Feed the cåts" from scenario_minimal (testdata_scenario_minimal.yaml), assigned to Zoë
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_CHORES_INPUT_NAME: "Feed the cåts",
            CFOF_CHORES_INPUT_DEFAULT_POINTS: 10,
            CFOF_CHORES_INPUT_ASSIGNED_KIDS: ["Zoë"],
        },
    )

    # Should return to main menu after successful add
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_add_reward(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test adding a reward via options flow."""
    # Navigate to rewards management
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_REWARDS},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_ENTITY

    # Select "Add" action
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_ADD_REWARD

    # Add the reward
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_REWARDS_INPUT_NAME: "Ice Créam!",
            CFOF_REWARDS_INPUT_COST: 50,
        },
    )

    # Should return to main menu after successful add
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_add_bonus(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test adding a bonus via options flow."""
    # Navigate to bonuses management
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_BONUSES},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_ENTITY

    # Select "Add" action
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_ADD_BONUS

    # Add the bonus
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_BONUSES_INPUT_NAME: "Stär Sprïnkle Bonus",
            CFOF_BONUSES_INPUT_POINTS: 15.0,
            CFOF_BONUSES_INPUT_DESCRIPTION: "Extra points for helping a sibling",
            CFOF_BONUSES_INPUT_ICON: "mdi:sparkles",
        },
    )

    # Should return to main menu after successful add
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_add_penalty(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test adding a penalty via options flow."""
    # Navigate to penalties management
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_PENALTIES},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_ENTITY

    # Select "Add" action
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_ADD_PENALTY

    # Add the penalty
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_PENALTIES_INPUT_NAME: "Førget Chöre",
            CFOF_PENALTIES_INPUT_POINTS: 5.0,  # Positive value, system stores as negative
            CFOF_PENALTIES_INPUT_DESCRIPTION: "Missed a daily chore",
            CFOF_PENALTIES_INPUT_ICON: "mdi:alert",
        },
    )

    # Should return to main menu after successful add
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_add_badge_cumulative(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test adding a cumulative badge via options flow."""
    # Arrange: Use scenario_medium which has pre-loaded kids
    config_entry, name_to_id_map = scenario_medium
    zoe_id = name_to_id_map["kid:Zoë"]

    # Navigate to badges management
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_BADGES},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_ENTITY

    # Select "Add" action - flow presents badge type selection
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )

    # Should show badge type selection form
    assert result.get("type") == FlowResultType.FORM
    # Flow shows type selection at OPTIONS_FLOW_STEP_ADD_BADGE
    # Then select cumulative type
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_BADGES_INPUT_TYPE: BADGE_TYPE_CUMULATIVE},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_ADD_BADGE_CUMULATIVE

    # Add the cumulative badge (badge_type not included - already selected in previous step)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_BADGES_INPUT_NAME: "Cleanup Champion",
            CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE: 10,
            CFOF_BADGES_INPUT_ICON: "mdi:broom",
            CFOF_BADGES_INPUT_AWARD_POINTS: 20.0,
            CFOF_BADGES_INPUT_ASSIGNED_TO: [zoe_id],
        },
    )

    # Should return to main menu after successful add
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_add_badge_periodic(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test adding a periodic badge via options flow."""
    # Arrange: Use scenario_medium which has pre-loaded kids
    config_entry, name_to_id_map = scenario_medium
    zoe_id = name_to_id_map["kid:Zoë"]

    # Navigate to badges management
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_BADGES},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_ENTITY

    # Select "Add" action - flow presents badge type selection
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )

    # Should show badge type selection form, select periodic
    assert result.get("type") == FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={CFOF_BADGES_INPUT_TYPE: BADGE_TYPE_PERIODIC},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_ADD_BADGE_PERIODIC

    # Add the periodic badge (badge_type not included - already selected in previous step)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_BADGES_INPUT_NAME: "Weekly Star",
            CFOF_BADGES_INPUT_TARGET_TYPE: "chore_count",
            CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE: 5,
            CFOF_BADGES_INPUT_ICON: "mdi:star-circle",
            CFOF_BADGES_INPUT_START_DATE: "2026-01-01",
            CFOF_BADGES_INPUT_END_DATE: "2026-12-31",
            CFOF_BADGES_INPUT_AWARD_POINTS: 15.0,
            CFOF_BADGES_INPUT_ASSIGNED_TO: [zoe_id],
        },
    )

    # Should return to main menu after successful add
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_add_achievement(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test adding an achievement via options flow."""
    # Navigate to achievements management
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_ACHIEVEMENTS},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_ENTITY

    # Select "Add" action
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_ADD_ACHIEVEMENT

    # Add the achievement
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_ACHIEVEMENTS_INPUT_NAME: "Test Achievement",
            CFOF_ACHIEVEMENTS_INPUT_TYPE: ACHIEVEMENT_TYPE_TOTAL,
            CFOF_ACHIEVEMENTS_INPUT_DESCRIPTION: "Complete 10 chores",
            CFOF_ACHIEVEMENTS_INPUT_CRITERIA: "chore_completion",
            CFOF_ACHIEVEMENTS_INPUT_TARGET_VALUE: 10,
            CFOF_ACHIEVEMENTS_INPUT_REWARD_POINTS: 50.0,
            CFOF_ACHIEVEMENTS_INPUT_ICON: "mdi:medal",
            CFOF_ACHIEVEMENTS_INPUT_ASSIGNED_KIDS: [],
        },
    )

    # Should return to main menu after successful add
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_add_challenge(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test adding a challenge via options flow."""
    # Navigate to challenges management
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_CHALLENGES},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_MANAGE_ENTITY

    # Select "Add" action
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_ADD_CHALLENGE

    # Add the challenge (dates must be in future, end after start)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_CHALLENGES_INPUT_NAME: "Summer Challenge",
            CFOF_CHALLENGES_INPUT_TYPE: CHALLENGE_TYPE_DAILY_MIN,
            CFOF_CHALLENGES_INPUT_DESCRIPTION: "Complete minimum chores daily",
            CFOF_CHALLENGES_INPUT_CRITERIA: "weekly_completion",
            CFOF_CHALLENGES_INPUT_TARGET_VALUE: 10,  # Required field
            CFOF_CHALLENGES_INPUT_START_DATE: "2026-06-01",
            CFOF_CHALLENGES_INPUT_END_DATE: "2026-08-31",
            CFOF_CHALLENGES_INPUT_REWARD_POINTS: 100.0,
            CFOF_CHALLENGES_INPUT_ICON: "mdi:flag-checkered",
            CFOF_CHALLENGES_INPUT_ASSIGNED_KIDS: [],  # Required field
        },
    )

    # Should return to main menu after successful add
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_edit_achievement(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test editing an existing achievement via options flow."""
    # First add an achievement to edit
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_ACHIEVEMENTS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_ACHIEVEMENTS_INPUT_NAME: "Initial Achievement",
            CFOF_ACHIEVEMENTS_INPUT_TYPE: ACHIEVEMENT_TYPE_TOTAL,
            CFOF_ACHIEVEMENTS_INPUT_DESCRIPTION: "Initial description",
            CFOF_ACHIEVEMENTS_INPUT_CRITERIA: "chore_completion",
            CFOF_ACHIEVEMENTS_INPUT_TARGET_VALUE: 5,
            CFOF_ACHIEVEMENTS_INPUT_REWARD_POINTS: 25.0,
            CFOF_ACHIEVEMENTS_INPUT_ICON: "mdi:star",
            CFOF_ACHIEVEMENTS_INPUT_ASSIGNED_KIDS: [],
        },
    )

    # Now edit it
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_ACHIEVEMENTS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_EDIT},
    )

    # Select the achievement to edit
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_ENTITY_NAME: "Initial Achievement"},
    )

    # Verify we're on the edit form
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "edit_achievement"

    # Submit updated data
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_ACHIEVEMENTS_INPUT_NAME: "Updated Achievement",
            CFOF_ACHIEVEMENTS_INPUT_TYPE: ACHIEVEMENT_TYPE_TOTAL,
            CFOF_ACHIEVEMENTS_INPUT_DESCRIPTION: "Updated description",
            CFOF_ACHIEVEMENTS_INPUT_CRITERIA: "chore_completion",
            CFOF_ACHIEVEMENTS_INPUT_TARGET_VALUE: 10,
            CFOF_ACHIEVEMENTS_INPUT_REWARD_POINTS: 50.0,
            CFOF_ACHIEVEMENTS_INPUT_ICON: "mdi:trophy",
            CFOF_ACHIEVEMENTS_INPUT_ASSIGNED_KIDS: [],
        },
    )

    # Should return to main menu after successful edit
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_edit_challenge(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test editing an existing challenge via options flow."""
    # First add a challenge to edit
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_CHALLENGES},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_CHALLENGES_INPUT_NAME: "Initial Challenge",
            CFOF_CHALLENGES_INPUT_TYPE: CHALLENGE_TYPE_DAILY_MIN,
            CFOF_CHALLENGES_INPUT_DESCRIPTION: "Initial challenge description",
            CFOF_CHALLENGES_INPUT_CRITERIA: "daily_completion",
            CFOF_CHALLENGES_INPUT_TARGET_VALUE: 5,
            CFOF_CHALLENGES_INPUT_START_DATE: "2026-06-01",
            CFOF_CHALLENGES_INPUT_END_DATE: "2026-07-31",
            CFOF_CHALLENGES_INPUT_REWARD_POINTS: 50.0,
            CFOF_CHALLENGES_INPUT_ICON: "mdi:flag",
            CFOF_CHALLENGES_INPUT_ASSIGNED_KIDS: [],
        },
    )

    # Now edit it
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_CHALLENGES},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_EDIT},
    )

    # Select the challenge to edit
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_ENTITY_NAME: "Initial Challenge"},
    )

    # Verify we're on the edit form
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "edit_challenge"

    # Submit updated data
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_CHALLENGES_INPUT_NAME: "Updated Challenge",
            CFOF_CHALLENGES_INPUT_TYPE: CHALLENGE_TYPE_DAILY_MIN,
            CFOF_CHALLENGES_INPUT_DESCRIPTION: "Updated challenge description",
            CFOF_CHALLENGES_INPUT_CRITERIA: "daily_completion",
            CFOF_CHALLENGES_INPUT_TARGET_VALUE: 10,
            CFOF_CHALLENGES_INPUT_START_DATE: "2026-06-01",
            CFOF_CHALLENGES_INPUT_END_DATE: "2026-08-31",
            CFOF_CHALLENGES_INPUT_REWARD_POINTS: 100.0,
            CFOF_CHALLENGES_INPUT_ICON: "mdi:flag-checkered",
            CFOF_CHALLENGES_INPUT_ASSIGNED_KIDS: [],
        },
    )

    # Should return to main menu after successful edit
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT


async def test_options_flow_edit_chore_preserves_assigned_kids(
    hass: HomeAssistant, init_integration: MockConfigEntry
):
    """Test editing a chore preserves assigned kids selection."""
    coordinator = hass.data["kidschores"][init_integration.entry_id]["coordinator"]

    # First, add a kid to assign to
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
        user_input={CFOF_KIDS_INPUT_KID_NAME: "Max! Stårblüm"},
    )

    # After adding kid, the reload is deferred until returning to menu
    # Complete the current flow to trigger the reload
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

    # Now start a new flow after the reload to add a chore with the kid assigned
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_CHORES},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_CHORES_INPUT_NAME: "Pick up Lëgo!",
            CFOF_CHORES_INPUT_DEFAULT_POINTS: 8.0,
            CFOF_CHORES_INPUT_ASSIGNED_KIDS: ["Max! Stårblüm"],
        },
    )

    # Verify we're back at the menu (this will trigger deferred reload)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

    # Wait for the deferred reload to complete (it happens when returning to menu)
    await hass.async_block_till_done()

    # After reload, get the fresh coordinator reference (old one is stale)
    coordinator = hass.data["kidschores"][init_integration.entry_id]["coordinator"]

    # Now start a new flow to verify the chore sensor was created
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    # Get the created chore's internal_id
    chore_id = None
    for cid, chore_data in coordinator.chores_data.items():
        if chore_data.get("name") == "Pick up Lëgo!":
            chore_id = cid
            # Verify assignment stored as internal_id
            assert len(chore_data.get("assigned_kids", [])) == 1
            break

    assert chore_id is not None, "Chore was not created"

    # Now edit the chore
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_CHORES},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_EDIT},
    )
    # Select the chore to edit
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_ENTITY_NAME: "Pick up Lëgo!"},
    )

    # The form should show with TestKid selected
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_EDIT_CHORE

    # Check if the schema has the correct default value for assigned_kids
    # The data_schema should have TestKid in the default
    data_schema = result.get("data_schema")
    assert data_schema is not None, "data_schema is None"
    schema_dict = data_schema.schema
    assigned_kids_field = None
    for key in schema_dict:
        if hasattr(key, "schema") and "assigned_kids" in str(key):
            assigned_kids_field = key
            break
        if hasattr(key, "key") and key.key == "assigned_kids":
            assigned_kids_field = key
            break

    assert assigned_kids_field is not None, (
        f"assigned_kids field not found in schema. "
        f"Keys: {[str(k) for k in schema_dict.keys()]}"
    )

    # The default should contain "Max! Stårblüm" (the name), not the internal_id
    default_value = assigned_kids_field.default()
    print(f"DEBUG: Default value for assigned_kids: {default_value}")
    print(f"DEBUG: Type: {type(default_value)}")
    print(
        f"DEBUG: Chore data keys: {list(coordinator.chores_data.get(chore_id, {}).keys())}"
    )
    print(
        f"DEBUG: Assigned kids in storage: {coordinator.chores_data.get(chore_id, {}).get('assigned_kids', [])}"
    )

    assert "Max! Stårblüm" in default_value, (
        f"Expected 'Max! Stårblüm' in assigned_kids default, got: {default_value}"
    )

    # Edit the chore (keeping the assignment)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_CHORES_INPUT_NAME: "Pick up Lëgo! (updated)",
            CFOF_CHORES_INPUT_DEFAULT_POINTS: 10.0,
            CFOF_CHORES_INPUT_ASSIGNED_KIDS: ["Max! Stårblüm"],
        },
    )

    # Handle per-kid dates step if shown (for INDEPENDENT chores)
    if result.get("step_id") == "edit_chore_per_kid_dates":
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input={},  # Accept defaults
        )

    # Should return to main menu
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

    # Verify the assignment was preserved
    updated_chore = coordinator.chores_data.get(chore_id)
    assert updated_chore is not None
    assert updated_chore.get("name") == "Pick up Lëgo! (updated)"
    assert len(updated_chore.get("assigned_kids", [])) == 1


async def test_options_flow_reward_sensor_creation_and_update(
    hass: HomeAssistant, init_integration: MockConfigEntry
):
    """Test that reward sensors are created on add and updated on edit.

    Reward sensors are created per kid-reward pair, so we need at least one kid first.
    """
    from homeassistant.helpers import entity_registry as er

    entity_registry = er.async_get(hass)
    coordinator = hass.data["kidschores"][init_integration.entry_id]["coordinator"]

    # Step 0: First add a kid (reward sensors are created per kid-reward pair)
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
        user_input={CFOF_KIDS_INPUT_KID_NAME: "TestKidForRewards"},
    )

    # Should return to main menu (triggers deferred reload)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

    # Wait for reload to complete
    await hass.async_block_till_done()

    # Get fresh coordinator reference after reload
    coordinator = hass.data["kidschores"][init_integration.entry_id]["coordinator"]

    # Get the kid_id we just created
    kid_id = None
    for k_id, kid_data in coordinator.kids_data.items():
        if kid_data.get("name") == "TestKidForRewards":
            kid_id = k_id
            break

    assert kid_id is not None, "Kid was not created"

    # Step 1: Now add a new reward via options flow
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_REWARDS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_REWARDS_INPUT_NAME: "Extra Plåytime",
            CFOF_REWARDS_INPUT_COST: 40,
        },
    )

    # Should return to main menu (triggers deferred reload)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

    # Wait for reload to complete
    await hass.async_block_till_done()

    # Get fresh coordinator reference after reload
    coordinator = hass.data["kidschores"][init_integration.entry_id]["coordinator"]

    # Step 2: Verify the reward exists in storage
    reward_id = None
    for rid, reward_data in coordinator.rewards_data.items():
        if reward_data.get("name") == "Extra Plåytime":
            reward_id = rid
            assert reward_data.get("cost") == 40
            break

    assert reward_id is not None, "Reward was not created in storage"

    # Step 3: Verify the reward sensor was created in entity registry
    # Reward sensors are created per kid-reward pair, so search for kid_id AND reward_id
    reward_entities = [
        entity
        for entity in entity_registry.entities.values()
        if entity.platform == "kidschores"
        and entity.domain == "sensor"
        and kid_id in entity.unique_id
        and reward_id in entity.unique_id
        and "reward" in entity.unique_id.lower()
    ]

    assert len(reward_entities) > 0, (
        f"Reward sensor not found for kid_id {kid_id} and reward_id {reward_id}. "
        f"Available entities: {[(e.unique_id, e.original_name) for e in entity_registry.entities.values() if e.platform == 'kidschores']}"
    )

    # Get the reward sensor entity
    reward_entity = reward_entities[0]
    original_entity_id = reward_entity.entity_id

    # Verify sensor name contains the reward name
    assert (
        "extra_playtime" in reward_entity.entity_id.lower()
        or "extra plåytime" in (reward_entity.original_name or "").lower()
    ), (
        f"Sensor name doesn't reflect reward name. Entity: {reward_entity.entity_id}, Name: {reward_entity.original_name}"
    )

    # Step 3a: Verify the sensor has state data immediately after reload (not null/unavailable)
    state = hass.states.get(original_entity_id)
    assert state is not None, f"State not found for {original_entity_id}"
    assert state.state not in [
        "unavailable",
        "unknown",
        "None",
        None,
    ], f"Sensor state is {state.state}, expected a valid state immediately after reload"

    # Step 4: Edit the reward name
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_REWARDS},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_EDIT},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_ENTITY_NAME: "Extra Plåytime"},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_REWARDS_INPUT_NAME: "Extra Plåytime (updated)",
            CFOF_REWARDS_INPUT_COST: 50,
        },
    )

    # Should return to main menu (triggers deferred reload)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

    # Wait for reload to complete
    await hass.async_block_till_done()

    # Get fresh coordinator reference after reload
    coordinator = hass.data["kidschores"][init_integration.entry_id]["coordinator"]

    # Step 5: Verify the reward name was updated in storage
    updated_reward = coordinator.rewards_data.get(reward_id)
    assert updated_reward is not None, "Reward disappeared from storage after edit"
    assert updated_reward.get("name") == "Extra Plåytime (updated)", (
        f"Reward name not updated in storage: {updated_reward.get('name')}"
    )
    assert updated_reward.get("cost") == 50, (
        f"Reward cost not updated: {updated_reward.get('cost')}"
    )

    # Step 6: Verify the sensor entity still exists (unique_id shouldn't change)
    reward_entity_after_edit = entity_registry.async_get(original_entity_id)
    assert reward_entity_after_edit is not None, (
        f"Reward sensor disappeared after edit. Original entity_id: {original_entity_id}"
    )

    # The unique_id should remain the same (based on internal_id)
    assert reward_entity_after_edit.unique_id == reward_entity.unique_id, (
        "Unique ID changed after edit (should be stable)"
    )

    # Step 7: Verify the sensor reflects the updated name
    # Note: The entity_id itself may not change (that's expected), but the state attributes should
    state = hass.states.get(original_entity_id)
    assert state is not None, f"State not found for {original_entity_id}"

    # The friendly_name or state attributes should reflect the new name
    friendly_name = state.attributes.get("friendly_name", "")
    assert (
        "Extra Plåytime (updated)" in friendly_name
        or "extra playtime (updated)" in friendly_name.lower()
    ), f"Sensor friendly_name doesn't reflect updated reward name. Got: {friendly_name}"


async def test_options_flow_chore_assignment_change_removes_old_sensors(
    hass: HomeAssistant, init_integration: MockConfigEntry
):
    """Test that changing chore assignments removes old kid-chore sensors properly."""
    from homeassistant.helpers import entity_registry as er

    entity_registry = er.async_get(hass)

    # Step 1: Add two kids
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
        user_input={CFOF_KIDS_INPUT_KID_NAME: "Kid1"},
    )
    await hass.async_block_till_done()

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
        user_input={CFOF_KIDS_INPUT_KID_NAME: "Kid2"},
    )
    await hass.async_block_till_done()

    coordinator = hass.data["kidschores"][init_integration.entry_id]["coordinator"]

    # Get kid IDs
    kid1_id = None
    kid2_id = None
    for kid_id, kid_data in coordinator.kids_data.items():
        if kid_data.get("name") == "Kid1":
            kid1_id = kid_id
        elif kid_data.get("name") == "Kid2":
            kid2_id = kid_id

    assert kid1_id is not None and kid2_id is not None, "Kids not created"

    # Step 2: Add a chore assigned to Kid1
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_CHORES},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_ADD},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_CHORES_INPUT_NAME: "Wåter the Plånts",
            CFOF_CHORES_INPUT_DEFAULT_POINTS: 7.0,
            CFOF_CHORES_INPUT_ASSIGNED_KIDS: ["Kid1"],
        },
    )
    await hass.async_block_till_done()

    coordinator = hass.data["kidschores"][init_integration.entry_id]["coordinator"]

    # Get chore ID
    chore_id = None
    for c_id, chore_data in coordinator.chores_data.items():
        if chore_data.get("name") == "Wåter the Plånts":
            chore_id = c_id
            break

    assert chore_id is not None, "Chore not created"

    # Step 3: Verify Kid1 has a chore status sensor
    # The unique_id format is: {entry_id}_{kid_id}_{chore_id}_status
    kid1_chore_sensors = [
        entity
        for entity in entity_registry.entities.values()
        if entity.platform == "kidschores"
        and entity.domain == "sensor"
        and kid1_id in entity.unique_id
        and chore_id in entity.unique_id
        and "_status" in entity.unique_id
    ]

    assert len(kid1_chore_sensors) > 0, (
        f"Chore sensor not found for kid1_id {kid1_id} and chore_id {chore_id}. "
        f"Found sensors: {[e.unique_id for e in entity_registry.entities.values() if e.platform == 'kidschores' and e.domain == 'sensor']}"
    )

    kid1_chore_entity_id = kid1_chore_sensors[0].entity_id

    # Verify sensor is available (has valid state)
    state = hass.states.get(kid1_chore_entity_id)
    assert state is not None
    assert state.state not in ["unavailable", "unknown"], (
        f"Kid1 chore sensor should be available, got: {state.state}"
    )

    # Step 4: Edit the chore to reassign from Kid1 to Kid2
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MENU_SELECTION: OPTIONS_FLOW_CHORES},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_MANAGE_ACTION: OPTIONS_FLOW_ACTIONS_EDIT},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={OPTIONS_FLOW_INPUT_ENTITY_NAME: "Wåter the Plånts"},
    )
    result = await hass.config_entries.options.async_configure(
        result.get("flow_id"),
        user_input={
            CFOF_CHORES_INPUT_NAME: "Wåter the Plånts",
            CFOF_CHORES_INPUT_DEFAULT_POINTS: 7.0,
            CFOF_CHORES_INPUT_ASSIGNED_KIDS: ["Kid2"],  # Changed from Kid1 to Kid2
        },
    )

    # Handle per-kid dates step if shown (for INDEPENDENT chores)
    if result.get("step_id") == "edit_chore_per_kid_dates":
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            user_input={},  # Accept defaults
        )

    # Should return to main menu (triggers deferred reload because assignments changed)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == OPTIONS_FLOW_STEP_INIT

    # Wait for reload
    await hass.async_block_till_done()

    # Step 5: Verify Kid1's chore sensor is removed from entity registry
    kid1_sensor_after_edit = entity_registry.async_get(kid1_chore_entity_id)
    assert kid1_sensor_after_edit is None, (
        f"Kid1 chore sensor should be removed after reassignment, "
        f"but still exists: {kid1_chore_entity_id}"
    )

    # Step 6: Verify Kid2 now has a chore status sensor
    coordinator = hass.data["kidschores"][init_integration.entry_id]["coordinator"]
    kid2_chore_sensors = [
        entity
        for entity in entity_registry.entities.values()
        if entity.platform == "kidschores"
        and entity.domain == "sensor"
        and kid2_id in entity.unique_id
        and chore_id in entity.unique_id
        and "_status" in entity.unique_id
    ]

    assert len(kid2_chore_sensors) > 0, (
        f"Chore sensor not found for kid2_id {kid2_id} and chore_id {chore_id}. "
        f"Found sensors: {[e.unique_id for e in entity_registry.entities.values() if e.platform == 'kidschores' and e.domain == 'sensor']}"
    )

    # Verify Kid2's sensor is available
    kid2_sensor_state = hass.states.get(kid2_chore_sensors[0].entity_id)
    assert kid2_sensor_state is not None
    assert kid2_sensor_state.state not in ["unavailable", "unknown"], (
        f"Kid2 chore sensor should be available, got: {kid2_sensor_state.state}"
    )
