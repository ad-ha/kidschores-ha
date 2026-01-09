"""Setup helpers for KidsChores test configuration.

This module provides declarative test setup that navigates the config flow
based on scenario dictionaries, allowing tests to focus on behavior rather
than flow navigation boilerplate.

Example:
    # Instead of 50+ lines of config flow navigation:
    result = await setup_scenario(hass, mock_hass_users, {
        "points": {"label": "Stars", "icon": "mdi:star"},
        "kids": [{"name": "Zoë", "ha_user": "kid1"}],
        "parents": [{"name": "Mom", "ha_user": "parent1", "kids": ["Zoë"]}],
        "chores": [{"name": "Clean Room", "assigned_to": ["Zoë"], "points": 10}],
    })
    # Access: result.config_entry, result.coordinator, result.kid_ids["Zoë"]

YAML-based setup:
    # Load scenario from YAML file:
    result = await setup_from_yaml(
        hass,
        mock_hass_users,
        "tests/scenarios/scenario_full.yaml"
    )
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.kidschores import const
from custom_components.kidschores.coordinator import KidsChoresDataCoordinator

# =============================================================================
# DATACLASSES
# =============================================================================


@dataclass
class SetupResult:
    """Result from setup_scenario containing all configured entities.

    Attributes:
        config_entry: The created ConfigEntry
        coordinator: The KidsChoresCoordinator instance
        kid_ids: Map of kid names to their internal UUIDs
        parent_ids: Map of parent names to their internal UUIDs
        chore_ids: Map of chore names to their internal UUIDs
        final_result: The final config flow result
    """

    config_entry: ConfigEntry
    coordinator: KidsChoresDataCoordinator
    kid_ids: dict[str, str] = field(default_factory=dict)
    parent_ids: dict[str, str] = field(default_factory=dict)
    chore_ids: dict[str, str] = field(default_factory=dict)
    final_result: ConfigFlowResult | None = None


# =============================================================================
# INTERNAL HELPERS
# =============================================================================


def _require_data_schema(result: ConfigFlowResult) -> Any:
    """Return the data_schema ensuring it exists."""
    data_schema = result.get("data_schema")
    assert data_schema is not None, f"data_schema missing from result: {result}"
    return data_schema


def _extract_kid_ids_from_schema(result: ConfigFlowResult) -> list[str]:
    """Extract kid IDs from the parent step schema.

    When on parent configuration step, the associated_kids field contains
    the options with kid UUIDs that were created in previous steps.

    Args:
        result: Config flow result on parent_count or parents step

    Returns:
        List of kid internal UUIDs available in the form
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


def _extract_kid_names_from_schema(result: ConfigFlowResult) -> list[str]:
    """Extract kid names from the chore step schema.

    When on chore configuration step, the assigned_kids field contains
    the options with kid names for assignment.

    Args:
        result: Config flow result on chores step

    Returns:
        List of kid names available in the form
    """
    data_schema = _require_data_schema(result)
    assigned_kids_field = data_schema.schema.get(const.CFOF_CHORES_INPUT_ASSIGNED_KIDS)
    assert assigned_kids_field is not None, "assigned_kids field not found in schema"

    kid_options = assigned_kids_field.config["options"]
    return [option["value"] for option in kid_options]


# =============================================================================
# STEP CONFIGURATION HELPERS
# =============================================================================


async def _configure_points_step(
    hass: HomeAssistant,
    result: ConfigFlowResult,
    points_config: dict[str, Any],
) -> ConfigFlowResult:
    """Configure the points/system settings step.

    Args:
        hass: Home Assistant instance
        result: Current flow result on POINTS step
        points_config: Dict with optional keys:
            - label: Points label (default: "Points")
            - icon: Points icon (default: "mdi:star-outline")

    Returns:
        Updated flow result at KID_COUNT step
    """
    assert result.get("step_id") == const.CONFIG_FLOW_STEP_POINTS

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            const.CFOF_SYSTEM_INPUT_POINTS_LABEL: points_config.get("label", "Points"),
            const.CFOF_SYSTEM_INPUT_POINTS_ICON: points_config.get(
                "icon", "mdi:star-outline"
            ),
        },
    )

    assert result.get("step_id") == const.CONFIG_FLOW_STEP_KID_COUNT
    return result


async def _configure_kid_step(
    hass: HomeAssistant,
    result: ConfigFlowResult,
    mock_hass_users: dict[str, Any],
    kid_config: dict[str, Any],
) -> ConfigFlowResult:
    """Configure a single kid step.

    Args:
        hass: Home Assistant instance
        result: Current flow result on KIDS step
        mock_hass_users: Mock users dict from fixture
        kid_config: Dict with keys:
            - name: Kid name (required)
            - ha_user: Key in mock_hass_users (required)
            - dashboard_language: Language code (default: "en")
            - enable_mobile_notifications: bool (default: False)
            - mobile_notify_service: str (default: "")
            - enable_persistent_notifications: bool (default: False)

    Returns:
        Updated flow result
    """
    return await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            const.CFOF_KIDS_INPUT_KID_NAME: kid_config["name"],
            const.CFOF_KIDS_INPUT_HA_USER: mock_hass_users[kid_config["ha_user"]].id,
            const.CFOF_KIDS_INPUT_DASHBOARD_LANGUAGE: kid_config.get(
                "dashboard_language", "en"
            ),
            const.CFOF_KIDS_INPUT_ENABLE_MOBILE_NOTIFICATIONS: kid_config.get(
                "enable_mobile_notifications", False
            ),
            const.CFOF_KIDS_INPUT_MOBILE_NOTIFY_SERVICE: kid_config.get(
                "mobile_notify_service", ""
            ),
            const.CFOF_KIDS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS: kid_config.get(
                "enable_persistent_notifications", False
            ),
        },
    )


async def _configure_parent_step(
    hass: HomeAssistant,
    result: ConfigFlowResult,
    mock_hass_users: dict[str, Any],
    parent_config: dict[str, Any],
    kid_name_to_id: dict[str, str],
) -> ConfigFlowResult:
    """Configure a single parent step.

    Args:
        hass: Home Assistant instance
        result: Current flow result on PARENTS step
        mock_hass_users: Mock users dict from fixture
        parent_config: Dict with keys:
            - name: Parent name (required)
            - ha_user: Key in mock_hass_users (required)
            - kids: List of kid names to associate (default: all)
            - enable_mobile_notifications: bool (default: False)
            - mobile_notify_service: str (default: "")
            - enable_persistent_notifications: bool (default: False)
        kid_name_to_id: Map of kid names to their UUIDs

    Returns:
        Updated flow result
    """
    # Determine associated kid IDs
    associated_kid_names = parent_config.get("kids", list(kid_name_to_id.keys()))
    associated_kid_ids = [
        kid_name_to_id[name] for name in associated_kid_names if name in kid_name_to_id
    ]

    # Mobile notify service handling
    enable_mobile = parent_config.get("enable_mobile_notifications", False)
    mobile_service = parent_config.get("mobile_notify_service", "")
    if not enable_mobile:
        mobile_service = const.SENTINEL_EMPTY

    return await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            const.CFOF_PARENTS_INPUT_NAME: parent_config["name"],
            const.CFOF_PARENTS_INPUT_HA_USER: mock_hass_users[
                parent_config["ha_user"]
            ].id,
            const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS: associated_kid_ids,
            const.CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS: enable_mobile,
            const.CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE: mobile_service,
            const.CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS: parent_config.get(
                "enable_persistent_notifications", False
            ),
        },
    )


def _build_chore_notifications(chore_config: dict[str, Any]) -> list[str]:
    """Build notification list from chore config.

    Handles both formats:
    - notifications: ["notify_on_claim", "notify_on_approval"]  (list format)
    - notify_on_claim: true  (legacy boolean format)

    Args:
        chore_config: Chore configuration dict

    Returns:
        List of notification event constants
    """
    notifications = chore_config.get("notifications", [])

    # Also check for legacy boolean format (notify_on_claim: true)
    if chore_config.get("notify_on_claim", False):
        if const.DATA_CHORE_NOTIFY_ON_CLAIM not in notifications:
            notifications.append(const.DATA_CHORE_NOTIFY_ON_CLAIM)

    return notifications


async def _configure_chore_step(
    hass: HomeAssistant,
    result: ConfigFlowResult,
    chore_config: dict[str, Any],
) -> ConfigFlowResult:
    """Configure a single chore step.

    Args:
        hass: Home Assistant instance
        result: Current flow result on CHORES step
        chore_config: Dict with keys:
            - name: Chore name (required)
            - assigned_to: List of kid names (required)
            - points: Points value (default: 10.0)
            - description: Chore description (default: "")
            - icon: MDI icon (default: "mdi:check")
            - completion_criteria: "independent"/"shared_all"/"shared_first"
              (default: "independent")
            - recurring_frequency: "daily"/"weekly"/"monthly"/"custom"/"none"
              (default: "daily")
            - auto_approve: bool (default: False)
            - show_on_calendar: bool (default: True)
            - notify_on_claim: bool (default: True) - Send notification when claimed
            - labels: List of labels (default: [])
            - applicable_days: List of day codes (default: all days for daily)
            - notifications: List of notification events (default: [])
            - due_date: ISO date string (default: None)
            - custom_interval: int (default: None)
            - custom_interval_unit: str (default: None)
            - approval_reset_type: str (default: "automatic")
            - approval_reset_pending_claim_action: str (default: from const)
            - overdue_handling_type: str (default: "none")

    Returns:
        Updated flow result
    """
    # Determine applicable days
    recurring_freq = chore_config.get("recurring_frequency", "daily")
    applicable_days = chore_config.get("applicable_days")
    if applicable_days is None:
        if recurring_freq == "daily":
            applicable_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        else:
            applicable_days = ["mon"]

    user_input = {
        const.CFOF_CHORES_INPUT_NAME: chore_config["name"],
        const.CFOF_CHORES_INPUT_ASSIGNED_KIDS: chore_config["assigned_to"],
        const.CFOF_CHORES_INPUT_DEFAULT_POINTS: chore_config.get("points", 10.0),
        const.CFOF_CHORES_INPUT_DESCRIPTION: chore_config.get("description", ""),
        const.CFOF_CHORES_INPUT_ICON: chore_config.get("icon", "mdi:check"),
        const.CFOF_CHORES_INPUT_COMPLETION_CRITERIA: chore_config.get(
            "completion_criteria", "independent"
        ),
        const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY: recurring_freq,
        const.CFOF_CHORES_INPUT_AUTO_APPROVE: chore_config.get("auto_approve", False),
        const.CFOF_CHORES_INPUT_SHOW_ON_CALENDAR: chore_config.get(
            "show_on_calendar", True
        ),
        const.CFOF_CHORES_INPUT_LABELS: chore_config.get("labels", []),
        const.CFOF_CHORES_INPUT_APPLICABLE_DAYS: applicable_days,
        const.CFOF_CHORES_INPUT_NOTIFICATIONS: _build_chore_notifications(chore_config),
        const.CFOF_CHORES_INPUT_APPROVAL_RESET_TYPE: chore_config.get(
            "approval_reset_type", const.DEFAULT_APPROVAL_RESET_TYPE
        ),
        const.CFOF_CHORES_INPUT_APPROVAL_RESET_PENDING_CLAIM_ACTION: chore_config.get(
            "approval_reset_pending_claim_action",
            const.DEFAULT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
        ),
        const.CFOF_CHORES_INPUT_OVERDUE_HANDLING_TYPE: chore_config.get(
            "overdue_handling_type", const.DEFAULT_OVERDUE_HANDLING_TYPE
        ),
    }

    # Add optional fields if provided
    # Handle relative due dates in multiple formats
    due_dt = None
    if "due_date_relative" in chore_config:
        # Simple format: "past" (yesterday) or "future" (tomorrow)
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        if chore_config["due_date_relative"] == "past":
            due_dt = now - timedelta(days=1)
        else:  # "future"
            due_dt = now + timedelta(days=1)
        # Set to 5 PM for consistency
        due_dt = due_dt.replace(hour=17, minute=0, second=0, microsecond=0)
    elif "due_date" in chore_config and chore_config["due_date"] is not None:
        due_date_val = chore_config["due_date"]
        # Handle relative format: "+1d17:00" (future) or "-3d17:00" (past)
        if isinstance(due_date_val, str) and due_date_val[0] in "+-":
            import re
            from datetime import datetime, timedelta, timezone

            match = re.match(r"([+-])(\d+)d(\d{2}):(\d{2})", due_date_val)
            if match:
                sign, days, hour, minute = match.groups()
                now = datetime.now(timezone.utc)
                delta = timedelta(days=int(days))
                due_dt = now + delta if sign == "+" else now - delta
                due_dt = due_dt.replace(
                    hour=int(hour), minute=int(minute), second=0, microsecond=0
                )
            else:
                # Static date string - parse it
                from datetime import datetime, timezone

                try:
                    due_dt = datetime.fromisoformat(due_date_val)
                except ValueError:
                    due_dt = None
        else:
            # Static date string - parse it
            from datetime import datetime, timezone

            try:
                if isinstance(due_date_val, str):
                    due_dt = datetime.fromisoformat(due_date_val)
                else:
                    due_dt = due_date_val
            except (ValueError, TypeError):
                due_dt = None

    # If we have a due_dt, check if it's in the past and adjust
    if due_dt is not None:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        if due_dt < now:
            # Past due date - adjust to 1 week from now, keeping same time
            original_dt = due_dt
            due_dt = now + timedelta(weeks=1)
            due_dt = due_dt.replace(
                hour=original_dt.hour,
                minute=original_dt.minute,
                second=0,
                microsecond=0,
            )
            print(
                f"⚠️  WARNING: Chore '{chore_config['name']}' has past due date "
                f"{original_dt.isoformat()}. Adjusted to {due_dt.isoformat()} "
                f"(1 week from now) for config flow validation."
            )
        user_input[const.CFOF_CHORES_INPUT_DUE_DATE] = due_dt.isoformat()
    if "custom_interval" in chore_config:
        user_input[const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL] = chore_config[
            "custom_interval"
        ]
    if "custom_interval_unit" in chore_config:
        user_input[const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL_UNIT] = chore_config[
            "custom_interval_unit"
        ]

    return await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=user_input
    )


async def _skip_remaining_counts(
    hass: HomeAssistant,
    result: ConfigFlowResult,
    start_step: str,  # pylint: disable=unused-argument
) -> ConfigFlowResult:
    """Skip all remaining count steps from the given start step to FINISH.

    Args:
        hass: Home Assistant instance
        result: Current flow result
        start_step: Current step ID (e.g., BADGE_COUNT, CHORE_COUNT)

    Returns:
        Flow result at FINISH step
    """
    # Define the count steps sequence after chores
    skip_sequence = [
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
    ]

    # Find starting point in sequence
    started = False
    for step_id, input_key, next_step in skip_sequence:
        if result.get("step_id") == step_id:
            started = True
        if started and result.get("step_id") == step_id:
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={input_key: 0}
            )
            assert result.get("step_id") == next_step

    return result


# =============================================================================
# MAIN SETUP FUNCTION
# =============================================================================


async def setup_scenario(
    hass: HomeAssistant,
    mock_hass_users: dict[str, Any],
    scenario: dict[str, Any],
) -> SetupResult:
    """Set up a complete KidsChores scenario via config flow.

    This function navigates the entire config flow based on a declarative
    scenario dictionary, creating the specified kids, parents, and chores.

    Args:
        hass: Home Assistant instance
        mock_hass_users: Mock users dictionary from fixture
        scenario: Configuration dict with optional keys:
            - points: {"label": str, "icon": str}
            - kids: List of kid configs (see _configure_kid_step)
            - parents: List of parent configs (see _configure_parent_step)
            - chores: List of chore configs (see _configure_chore_step)

    Returns:
        SetupResult with config_entry, coordinator, and ID mappings

    Example:
        result = await setup_scenario(hass, mock_hass_users, {
            "points": {"label": "Stars", "icon": "mdi:star"},
            "kids": [
                {"name": "Zoë", "ha_user": "kid1"},
                {"name": "Max", "ha_user": "kid2"},
            ],
            "parents": [
                {"name": "Mom", "ha_user": "parent1", "kids": ["Zoë", "Max"]},
            ],
            "chores": [
                {"name": "Clean Room", "assigned_to": ["Zoë"], "points": 15},
                {"name": "Do Dishes", "assigned_to": ["Zoë", "Max"], "points": 10},
            ],
        })

        # Access created entities:
        kid_id = result.kid_ids["Zoë"]
        chore_id = result.chore_ids["Clean Room"]
        coordinator = result.coordinator
    """
    kids_config = scenario.get("kids", [])
    parents_config = scenario.get("parents", [])
    chores_config = scenario.get("chores", [])
    points_config = scenario.get("points", {})

    kid_name_to_id: dict[str, str] = {}
    parent_name_to_id: dict[str, str] = {}
    chore_name_to_id: dict[str, str] = {}

    # -----------------------------------------------------------------
    # Start config flow
    # Note: No mock of async_setup_entry - we want real setup to run
    # so that coordinator and hass.data are properly populated
    # -----------------------------------------------------------------
    result = await hass.config_entries.flow.async_init(
        const.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == const.CONFIG_FLOW_STEP_DATA_RECOVERY

    # Skip data recovery (fresh start)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"backup_selection": "start_fresh"}
    )
    assert result.get("step_id") == const.CONFIG_FLOW_STEP_INTRO

    # Skip intro
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result.get("step_id") == const.CONFIG_FLOW_STEP_POINTS

    # -----------------------------------------------------------------
    # Configure points
    # -----------------------------------------------------------------
    result = await _configure_points_step(hass, result, points_config)

    # -----------------------------------------------------------------
    # Configure kids
    # -----------------------------------------------------------------
    kid_count = len(kids_config)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={const.CFOF_KIDS_INPUT_KID_COUNT: kid_count},
    )

    if kid_count > 0:
        assert result.get("step_id") == const.CONFIG_FLOW_STEP_KIDS

        for i, kid_config in enumerate(kids_config):
            result = await _configure_kid_step(
                hass, result, mock_hass_users, kid_config
            )

            if i < kid_count - 1:
                # More kids to configure
                assert result.get("step_id") == const.CONFIG_FLOW_STEP_KIDS
            else:
                # Last kid - should advance to parent count
                assert result.get("step_id") == const.CONFIG_FLOW_STEP_PARENT_COUNT

        # Note: kid IDs will be extracted after we enter the PARENTS step
        # (they're embedded in the associated_kids selector, not available here)
    else:
        assert result.get("step_id") == const.CONFIG_FLOW_STEP_PARENT_COUNT

    # -----------------------------------------------------------------
    # Configure parents
    # -----------------------------------------------------------------
    parent_count = len(parents_config)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={const.CFOF_PARENTS_INPUT_PARENT_COUNT: parent_count},
    )

    if parent_count > 0:
        assert result.get("step_id") == const.CONFIG_FLOW_STEP_PARENTS

        # NOW extract kid IDs from the PARENTS step schema
        # (only available when on actual parents form, not parent_count form)
        if kid_count > 0:
            actual_kid_ids = _extract_kid_ids_from_schema(result)
            for j, kid_config in enumerate(kids_config):
                if j < len(actual_kid_ids):
                    kid_name_to_id[kid_config["name"]] = actual_kid_ids[j]

        for i, parent_config in enumerate(parents_config):
            result = await _configure_parent_step(
                hass, result, mock_hass_users, parent_config, kid_name_to_id
            )

            if i < parent_count - 1:
                # More parents to configure
                assert result.get("step_id") == const.CONFIG_FLOW_STEP_PARENTS
            else:
                # Last parent - should advance to chore count
                assert result.get("step_id") == const.CONFIG_FLOW_STEP_CHORE_COUNT
    else:
        assert result.get("step_id") == const.CONFIG_FLOW_STEP_CHORE_COUNT

    # -----------------------------------------------------------------
    # Configure chores
    # -----------------------------------------------------------------
    chore_count = len(chores_config)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={const.CFOF_CHORES_INPUT_CHORE_COUNT: chore_count},
    )

    if chore_count > 0:
        assert result.get("step_id") == const.CONFIG_FLOW_STEP_CHORES

        for i, chore_config in enumerate(chores_config):
            result = await _configure_chore_step(hass, result, chore_config)

            if i < chore_count - 1:
                # More chores to configure
                assert result.get("step_id") == const.CONFIG_FLOW_STEP_CHORES
            else:
                # Last chore - should advance to badge count
                assert result.get("step_id") == const.CONFIG_FLOW_STEP_BADGE_COUNT
    else:
        assert result.get("step_id") == const.CONFIG_FLOW_STEP_BADGE_COUNT

    # -----------------------------------------------------------------
    # Skip remaining steps (badges, rewards, penalties, bonuses, etc.)
    # -----------------------------------------------------------------
    result = await _skip_remaining_counts(
        hass, result, const.CONFIG_FLOW_STEP_BADGE_COUNT
    )
    assert result.get("step_id") == const.CONFIG_FLOW_STEP_FINISH

    # -----------------------------------------------------------------
    # Finish config flow
    # -----------------------------------------------------------------
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    config_entry = result.get("result")
    assert config_entry is not None, "Config entry not created"

    # -------------------------------------------------------------------------
    # Wait for integration setup to complete
    # CREATE_ENTRY triggers async_setup_entry automatically
    # -------------------------------------------------------------------------
    await hass.async_block_till_done()

    # Get coordinator
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # -------------------------------------------------------------------------
    # Map names to IDs from coordinator data
    # -------------------------------------------------------------------------
    # Update kid IDs from coordinator (they should match but let's be sure)
    for kid_id, kid_data in coordinator.kids_data.items():
        kid_name = kid_data.get(const.DATA_KID_NAME)
        if kid_name:
            kid_name_to_id[kid_name] = kid_id

    # Map parent names to IDs
    for parent_id, parent_data in coordinator.parents_data.items():
        parent_name = parent_data.get(const.DATA_PARENT_NAME)
        if parent_name:
            parent_name_to_id[parent_name] = parent_id

    # Map chore names to IDs
    for chore_id, chore_data in coordinator.chores_data.items():
        chore_name = chore_data.get(const.DATA_CHORE_NAME)
        if chore_name:
            chore_name_to_id[chore_name] = chore_id

    return SetupResult(
        config_entry=config_entry,
        coordinator=coordinator,
        kid_ids=kid_name_to_id,
        parent_ids=parent_name_to_id,
        chore_ids=chore_name_to_id,
        final_result=result,
    )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


async def setup_minimal_scenario(
    hass: HomeAssistant,
    mock_hass_users: dict[str, Any],
    kid_name: str = "Zoë",
    parent_name: str = "Mom",
    chore_name: str = "Clean Room",
    chore_points: float = 10.0,
) -> SetupResult:
    """Set up a minimal scenario with 1 kid, 1 parent, 1 chore.

    This is a convenience wrapper around setup_scenario for simple test cases.

    Args:
        hass: Home Assistant instance
        mock_hass_users: Mock users dictionary from fixture
        kid_name: Name for the kid (default: "Zoë")
        parent_name: Name for the parent (default: "Mom")
        chore_name: Name for the chore (default: "Clean Room")
        chore_points: Points for the chore (default: 10.0)

    Returns:
        SetupResult with created entities
    """
    return await setup_scenario(
        hass,
        mock_hass_users,
        {
            "kids": [{"name": kid_name, "ha_user": "kid1"}],
            "parents": [{"name": parent_name, "ha_user": "parent1"}],
            "chores": [
                {
                    "name": chore_name,
                    "assigned_to": [kid_name],
                    "points": chore_points,
                }
            ],
        },
    )


async def setup_multi_kid_scenario(
    hass: HomeAssistant,
    mock_hass_users: dict[str, Any],
    kid_names: list[str] | None = None,
    parent_name: str = "Mom",
    shared_chore_name: str = "Shared Chore",
) -> SetupResult:
    """Set up a scenario with multiple kids sharing chores.

    Args:
        hass: Home Assistant instance
        mock_hass_users: Mock users dictionary from fixture
        kid_names: List of kid names (default: ["Zoë", "Max"])
        parent_name: Name for the parent (default: "Mom")
        shared_chore_name: Name for the shared chore (default: "Shared Chore")

    Returns:
        SetupResult with created entities
    """
    if kid_names is None:
        kid_names = ["Zoë", "Max"]

    kids = [
        {"name": name, "ha_user": f"kid{i + 1}"} for i, name in enumerate(kid_names)
    ]

    return await setup_scenario(
        hass,
        mock_hass_users,
        {
            "kids": kids,
            "parents": [{"name": parent_name, "ha_user": "parent1"}],
            "chores": [
                {
                    "name": shared_chore_name,
                    "assigned_to": kid_names,
                    "points": 15.0,
                    "completion_criteria": "shared_all",
                }
            ],
        },
    )


# =============================================================================
# YAML-BASED SETUP
# =============================================================================


def _transform_yaml_to_scenario(yaml_data: dict[str, Any]) -> dict[str, Any]:
    """Transform YAML data to setup_scenario() format.

    The YAML format uses more descriptive keys that need to be mapped to
    the setup_scenario() expected format.

    YAML format (example):
        system:
          points_label: "Star Points"
          points_icon: "mdi:star"
        kids:
          - name: "Zoë"
            ha_user: "kid1"
            dashboard_language: "en"
        parents:
          - name: "Mom"
            ha_user: "parent1"
            kids: ["Zoë"]
        chores:
          - name: "Clean Room"
            assigned_to: ["Zoë"]
            points: 10.0

    setup_scenario format:
        points: {"label": "Star Points", "icon": "mdi:star"}
        kids: [{"name": "Zoë", "ha_user": "kid1", ...}]
        parents: [{"name": "Mom", "ha_user": "parent1", "kids": ["Zoë"]}]
        chores: [{"name": "Clean Room", "assigned_to": ["Zoë"], "points": 10.0}]

    Args:
        yaml_data: Raw YAML data from file

    Returns:
        Transformed scenario dict for setup_scenario()
    """
    scenario: dict[str, Any] = {}

    # Transform system -> points
    system = yaml_data.get("system", {})
    if system:
        scenario["points"] = {
            "label": system.get("points_label", "Points"),
            "icon": system.get("points_icon", "mdi:star-outline"),
        }

    # Kids: direct passthrough (keys already match)
    kids = yaml_data.get("kids", [])
    if kids:
        scenario["kids"] = kids

    # Parents: direct passthrough (keys already match)
    parents = yaml_data.get("parents", [])
    if parents:
        scenario["parents"] = parents

    # Chores: direct passthrough (keys already match)
    chores = yaml_data.get("chores", [])
    if chores:
        scenario["chores"] = chores

    return scenario


async def setup_from_yaml(
    hass: HomeAssistant,
    mock_hass_users: dict[str, Any],
    yaml_path: str | Path,
) -> SetupResult:
    """Set up a KidsChores scenario from a YAML file.

    This function loads a scenario definition from YAML and passes it to
    setup_scenario() for config flow navigation.

    Args:
        hass: Home Assistant instance
        mock_hass_users: Mock users dictionary from fixture
        yaml_path: Path to YAML scenario file (absolute or relative to workspace)

    Returns:
        SetupResult with config_entry, coordinator, and ID mappings

    Example:
        result = await setup_from_yaml(
            hass,
            mock_hass_users,
            "tests/scenarios/scenario_full.yaml"
        )

        # Access created entities:
        kid_id = result.kid_ids["Zoë"]
        chore_id = result.chore_ids["Feed the cåts"]
        coordinator = result.coordinator

    YAML File Format:
        system:
          points_label: "Star Points"
          points_icon: "mdi:star"
        kids:
          - name: "Zoë"
            ha_user: "kid1"  # Key in mock_hass_users fixture
        parents:
          - name: "Mom"
            ha_user: "parent1"  # Key in mock_hass_users fixture
            kids: ["Zoë"]  # List of kid names to associate
        chores:
          - name: "Clean Room"
            assigned_to: ["Zoë"]  # List of kid names
            points: 10.0
            completion_criteria: "independent"  # or "shared_all", "shared_first"
    """
    # Resolve path
    path = Path(yaml_path)
    if not path.is_absolute():
        # Relative paths are resolved from the kidschores-ha workspace root
        workspace_root = Path(__file__).parent.parent.parent
        path = workspace_root / path

    if not path.exists():
        raise FileNotFoundError(f"Scenario YAML not found: {path}")

    # Load YAML
    with open(path, encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    # Transform to setup_scenario format
    scenario = _transform_yaml_to_scenario(yaml_data)

    # Run setup
    return await setup_scenario(hass, mock_hass_users, scenario)
