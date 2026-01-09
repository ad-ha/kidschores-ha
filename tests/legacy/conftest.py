"""Shared fixtures for KidsChores tests."""

# pylint: disable=redefined-outer-name  # Pytest fixtures redefine outer scope names
# pylint: disable=reimported  # Some modules imported multiple times in complex fixtures

import uuid
from typing import TYPE_CHECKING, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

if TYPE_CHECKING:
    from custom_components.kidschores.coordinator import KidsChoresDataCoordinator
else:
    # Runtime placeholder for type checking
    KidsChoresDataCoordinator = "KidsChoresDataCoordinator"

from custom_components.kidschores import const
from custom_components.kidschores.const import (
    CONF_POINTS_ICON,
    CONF_POINTS_LABEL,
    CONF_SHOW_LEGACY_ENTITIES,
    DATA_ACHIEVEMENTS,
    DATA_BADGES,
    DATA_BONUSES,
    DATA_CHALLENGES,
    DATA_CHORES,
    DATA_KIDS,
    DATA_PARENTS,
    DATA_PENALTIES,
    DATA_REWARDS,
    DEFAULT_POINTS_ICON,
    DEFAULT_POINTS_LABEL,
    DOMAIN,
    SCHEMA_VERSION_STORAGE_ONLY,
)


def pytest_addoption(parser):
    """Add command line options for tests."""
    parser.addoption(
        "--migration-file",
        action="store",
        default=None,
        help="Path to v40 data file to test migration (for test_migration_generic.py)",
    )


# NOTE: pytest_plugins removed - must be defined at top-level tests/conftest.py only


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> Any:
    """Enable custom integrations in tests."""
    # pylint: disable=unused-argument
    yield


@pytest.fixture
async def mock_hass_users(hass: HomeAssistant) -> dict[str, Any]:
    """Create mock Home Assistant users for testing.

    User names match ha_user_name values in test YAML files:
    - parent1, parent2 (parents)
    - kid1, kid2, kid3 (kids)
    """
    # Create admin user
    admin_user = await hass.auth.async_create_user(
        "Admin User",
        group_ids=["system-admin"],
    )

    # Create parent users (match YAML ha_user_name values)
    parent1_user = await hass.auth.async_create_user(
        "Parent One",
        group_ids=["system-users"],
    )
    parent2_user = await hass.auth.async_create_user(
        "Parent Two",
        group_ids=["system-users"],
    )

    # Create kid users (match YAML ha_user_name values)
    kid1_user = await hass.auth.async_create_user(
        "Kid One",
        group_ids=["system-users"],
    )
    kid2_user = await hass.auth.async_create_user(
        "Kid Two",
        group_ids=["system-users"],
    )
    kid3_user = await hass.auth.async_create_user(
        "Kid Three",
        group_ids=["system-users"],
    )

    return {
        "admin": admin_user,
        "parent1": parent1_user,
        "parent2": parent2_user,
        "kid1": kid1_user,
        "kid2": kid2_user,
        "kid3": kid3_user,
    }


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="KidsChores",
        data={
            "schema_version": SCHEMA_VERSION_STORAGE_ONLY,
        },
        options={
            CONF_POINTS_LABEL: DEFAULT_POINTS_LABEL,
            CONF_POINTS_ICON: DEFAULT_POINTS_ICON,
            CONF_SHOW_LEGACY_ENTITIES: True,
        },
        entry_id="test_entry_id",
        unique_id="test_unique_id",
    )


@pytest.fixture
def mock_storage_data() -> dict[str, dict]:
    """Return mock storage data structure."""
    return {
        DATA_KIDS: {},
        DATA_PARENTS: {},
        DATA_CHORES: {},
        DATA_BADGES: {},
        DATA_REWARDS: {},
        DATA_BONUSES: {},
        DATA_PENALTIES: {},
        DATA_ACHIEVEMENTS: {},
        DATA_CHALLENGES: {},
    }


@pytest.fixture
def mock_storage_manager(
    mock_storage_data: dict[str, dict],  # pylint: disable=redefined-outer-name
) -> MagicMock:
    """Return a mock storage manager."""
    mock = MagicMock()
    mock.data = mock_storage_data
    mock.async_load = AsyncMock(return_value=mock_storage_data)
    mock.async_save = AsyncMock()
    return mock


@pytest.fixture
def mock_coordinator(
    mock_storage_data: dict[str, dict],  # pylint: disable=redefined-outer-name
) -> MagicMock:
    """Return a mock coordinator."""
    mock = MagicMock()
    mock.data = mock_storage_data
    mock.kids_data = mock_storage_data[DATA_KIDS]
    mock.parents_data = mock_storage_data[DATA_PARENTS]
    mock.chores_data = mock_storage_data[DATA_CHORES]
    mock.badges_data = mock_storage_data[DATA_BADGES]
    mock.rewards_data = mock_storage_data[DATA_REWARDS]
    mock.bonuses_data = mock_storage_data[DATA_BONUSES]
    mock.penalties_data = mock_storage_data[DATA_PENALTIES]
    mock.achievements_data = mock_storage_data[DATA_ACHIEVEMENTS]
    mock.challenges_data = mock_storage_data[DATA_CHALLENGES]
    mock.async_refresh = AsyncMock()
    mock.async_update_listeners = MagicMock()
    # pylint: disable=protected-access
    mock._persist = AsyncMock()

    # Add test kid for calendar tests
    test_kid_id = str(uuid.uuid4())
    mock.test_kid_id = test_kid_id
    mock.kids_data[test_kid_id] = {
        "internal_id": test_kid_id,
        "name": "Test Kid",
        "points": 100.0,
        "ha_user_id": "",
        "enable_notifications": True,
        "mobile_notify_service": "",
        "use_persistent_notifications": True,
        "dashboard_language": "en",
        "chore_states": {},
        "badges_earned": {},
        "claimed_chores": [],
        "approved_chores": [],
        "reward_claims": {},
        "bonus_applies": {},
        "penalty_applies": {},
        "overdue_notifications": {},
    }

    # Mock CRUD methods
    mock._create_kid = MagicMock()
    mock._create_parent = MagicMock()
    mock._create_chore = MagicMock()
    mock._create_badge = MagicMock()
    mock._create_reward = MagicMock()
    mock._create_bonus = MagicMock()
    mock._create_penalty = MagicMock()
    mock._create_achievement = MagicMock()
    mock._create_challenge = MagicMock()
    # pylint: enable=protected-access

    mock.update_kid_entity = MagicMock()
    mock.update_parent_entity = MagicMock()
    mock.update_chore_entity = MagicMock()
    mock.update_badge_entity = MagicMock()
    mock.update_reward_entity = MagicMock()
    mock.update_bonus_entity = MagicMock()
    mock.update_penalty_entity = MagicMock()
    mock.update_achievement_entity = MagicMock()
    mock.update_challenge_entity = MagicMock()

    mock.delete_kid_entity = MagicMock()
    mock.delete_parent_entity = MagicMock()
    mock.delete_chore_entity = MagicMock()
    mock.delete_badge_entity = MagicMock()
    mock.delete_reward_entity = MagicMock()
    mock.delete_bonus_entity = MagicMock()
    mock.delete_penalty_entity = MagicMock()
    mock.delete_achievement_entity = MagicMock()
    mock.delete_challenge_entity = MagicMock()

    return mock


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,  # pylint: disable=redefined-outer-name
    mock_storage_data: dict[str, Any],  # pylint: disable=redefined-outer-name
) -> AsyncGenerator[MockConfigEntry, None]:
    """Set up the KidsChores integration for testing with mocked storage."""
    mock_config_entry.add_to_hass(hass)

    # Mock the Store's async_load to return our test data
    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        return_value=mock_storage_data,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    yield mock_config_entry

    # Cleanup: unload the integration
    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()


def create_mock_kid_data(
    name: str = "Test Kid", points: float = 100.0
) -> dict[str, Any]:
    """Create mock kid data for testing."""
    kid_id = str(uuid.uuid4())
    return {
        "internal_id": kid_id,
        "name": name,
        "points": points,
        "ha_user_id": "",
        "enable_notifications": True,
        "mobile_notify_service": "",
        "use_persistent_notifications": True,
        "dashboard_language": "en",
        "chore_states": {},
        "badges_earned": {},  # Dict with badge_id as key, not list
        "claimed_chores": [],
        "approved_chores": [],
        "reward_claims": {},
        "bonus_applies": {},
        "penalty_applies": {},
        "overdue_notifications": {},
        "badge_progress": {},  # Badge progress tracking (periodic badges)
        "cumulative_badge_progress": {},  # Cumulative badge progress
    }


def create_mock_chore_data(
    name: str = "Test Chore",
    default_points: int | float = 10,
    assigned_kids: list[str] | None = None,
    completion_criteria: str = "independent",
) -> dict[str, Any]:
    """Create mock chore data for testing."""
    chore_id = str(uuid.uuid4())
    return {
        "internal_id": chore_id,
        "name": name,
        "default_points": default_points,
        "assigned_kids": assigned_kids or [],
        "partial_allowed": False,
        "allow_multiple_claims_per_day": False,
        "description": "",
        "labels": [],
        "icon": "mdi:broom",
        "recurring_frequency": "",
        "custom_interval": None,
        "custom_interval_unit": None,
        "due_date": None,
        "applicable_days": [],  # Empty list = all days applicable
        "notify_on_claim": True,
        "notify_on_approval": True,
        "notify_on_disapproval": True,
        "show_on_calendar": True,
        "auto_approve": False,
        "completion_criteria": completion_criteria,
    }


def create_mock_reward_data(
    name: str = "Test Reward", cost: int = 50
) -> dict[str, Any]:
    """Create mock reward data for testing."""
    reward_id = str(uuid.uuid4())
    return {
        "internal_id": reward_id,
        "name": name,
        "cost": cost,
        "description": "",
        "labels": [],
        "icon": "mdi:gift",
    }


@pytest.fixture
async def init_integration_with_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,  # pylint: disable=redefined-outer-name
    mock_hass_users: dict,  # pylint: disable=redefined-outer-name
) -> AsyncGenerator[MockConfigEntry, None]:
    """Set up a fully configured KidsChores integration with sample data."""
    # Create sample kid data
    kid1_id = str(uuid.uuid4())
    kid2_id = str(uuid.uuid4())

    sample_kids = {
        kid1_id: create_mock_kid_data("Test Kid 1", 100.0),
        kid2_id: create_mock_kid_data("Test Kid 2", 50.0),
    }
    sample_kids[kid1_id]["internal_id"] = kid1_id
    sample_kids[kid2_id]["internal_id"] = kid2_id
    sample_kids[kid1_id]["ha_user_id"] = mock_hass_users["kid1"].id
    sample_kids[kid2_id]["ha_user_id"] = mock_hass_users["kid2"].id

    # Create sample chore data
    chore1_id = str(uuid.uuid4())
    sample_chores = {
        chore1_id: create_mock_chore_data(
            "Test Chore",
            10,
            [kid1_id, kid2_id],
        ),
    }
    sample_chores[chore1_id]["internal_id"] = chore1_id

    # Create sample reward data
    reward1_id = str(uuid.uuid4())
    sample_rewards = {
        reward1_id: create_mock_reward_data("Test Reward", 50),
    }
    sample_rewards[reward1_id]["internal_id"] = reward1_id

    # Mock storage data
    storage_data = {
        DATA_KIDS: sample_kids,
        DATA_PARENTS: {},
        DATA_CHORES: sample_chores,
        DATA_BADGES: {},
        DATA_REWARDS: sample_rewards,
        DATA_BONUSES: {},
        DATA_PENALTIES: {},
        DATA_ACHIEVEMENTS: {},
        DATA_CHALLENGES: {},
    }

    mock_config_entry.add_to_hass(hass)

    # Patch storage to return our sample data
    with patch(
        "custom_components.kidschores.storage_manager.KidsChoresStorageManager.async_load",
        return_value=storage_data,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    yield mock_config_entry


# ============================================================================
# Scenario Loading Infrastructure
# ============================================================================


def load_scenario_yaml(scenario_name: str) -> dict[str, Any]:
    """Load a test scenario YAML file.

    Args:
        scenario_name: Name of the scenario (minimal, medium, full, or performance_stress)

    Returns:
        Dictionary containing the scenario data with keys:
        - family: Dict with parents and kids lists
        - chores: List of chore entities
        - badges: List of badge entities
        - bonuses: List of bonus entities
        - penalties: List of penalty entities
        - rewards: List of reward entities
        - progress: Dict mapping kid names to progress data

    Example:
        >>> scenario = load_scenario_yaml("minimal")
        >>> parents = scenario["family"]["parents"]
        >>> kids = scenario["family"]["kids"]
    """
    import os

    import yaml

    scenario_path = os.path.join(
        os.path.dirname(__file__), f"testdata_scenario_{scenario_name}.yaml"
    )

    with open(scenario_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ==============================================================================
# Storage Inspection Helpers
# ==============================================================================


def get_storage_data(hass: HomeAssistant) -> dict[str, Any]:
    """Get current kidschores_data from storage for debugging.

    Returns:
        Dictionary containing all coordinator data from storage
    """
    from custom_components.kidschores.const import COORDINATOR

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state.name == "LOADED":
            coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
            return {
                "kids": coordinator.kids_data,
                "parents": coordinator.parents_data,
                "chores": coordinator.chores_data,
                "rewards": coordinator.rewards_data,
                "penalties": coordinator.penalties_data,
                "bonuses": coordinator.bonuses_data,
                "badges": coordinator.badges_data,
                "achievements": coordinator.achievements_data,
                "challenges": coordinator.challenges_data,
            }
    return {}


def dump_storage_for_debug(hass: HomeAssistant, label: str = "") -> None:
    """Pretty print storage data for debugging.

    Args:
        hass: Home Assistant instance
        label: Optional label to identify this dump
    """
    import json

    data = get_storage_data(hass)
    print(f"\n{'=' * 80}")
    print(f"STORAGE DUMP: {label}")
    print("=" * 80)
    print(json.dumps(data, indent=2, default=str))
    print("=" * 80)


async def reload_entity_platforms(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Reload entity platforms to create entities for newly added coordinator data.

    This is needed when data is loaded directly into the coordinator after the
    initial platform setup. The platforms need to be reloaded so they can
    create entities for the new data (penalties, bonuses, kids, etc.).

    Args:
        hass: Home Assistant instance
        config_entry: Config entry for the integration
    """
    from homeassistant.const import Platform

    # Unload platforms first
    await hass.config_entries.async_unload_platforms(
        config_entry,
        [Platform.BUTTON, Platform.SENSOR, Platform.CALENDAR, Platform.SELECT],
    )
    await hass.async_block_till_done()

    # Reload platforms - this will recreate entities based on current coordinator data
    await hass.config_entries.async_forward_entry_setups(
        config_entry,
        [Platform.BUTTON, Platform.SENSOR, Platform.CALENDAR, Platform.SELECT],
    )
    await hass.async_block_till_done()


# ==============================================================================
# Options Flow-Based Scenario Loading (EXPERIMENTAL - NOT CURRENTLY USED)
# ==============================================================================


async def apply_scenario_via_options_flow(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    scenario_data: dict[str, Any],
) -> dict[str, str]:
    """Apply scenario data using options flow (proper entity lifecycle).

    This uses the real options flow to add entities, ensuring:
    - Entity platforms are notified and create entities automatically
    - All HA lifecycle events fire correctly
    - Tests match real user workflow

    Args:
        hass: Home Assistant instance
        config_entry: Config entry for the integration
        scenario_data: Scenario data loaded from YAML

    Returns:
        Dictionary mapping entity names to internal IDs for reference in tests

    Note:
        This is slower than direct coordinator manipulation but more realistic
        and avoids entity platform reload issues.
    """
    from custom_components.kidschores.const import COORDINATOR

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    name_to_id_map = {}

    # Mock notifications during setup
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        # Phase 1: Add kids via options flow
        family = scenario_data.get("family", {})
        for kid in family.get("kids", []):
            result = await hass.config_entries.options.async_init(config_entry.entry_id)
            assert result.get("type") == "menu"

            # Navigate to add kid
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], {"next_step": "add_kid"}
            )

            # Fill kid form
            kid_data = {
                "kid_name": kid["name"],
                "kid_initial_points": 0.0,
            }
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], kid_data
            )

            # Extract kid_id from coordinator (just added)
            kid_id = None
            for k_id, k_info in coordinator.kids_data.items():
                if k_info.get("name") == kid["name"]:
                    kid_id = k_id
                    break
            if kid_id:
                name_to_id_map[f"kid:{kid['name']}"] = kid_id

        # Phase 2: Add parents
        for parent in family.get("parents", []):
            result = await hass.config_entries.options.async_init(config_entry.entry_id)
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], {"next_step": "add_parent"}
            )

            parent_data = {
                "parent_name": parent["name"],
            }
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], parent_data
            )

            # Extract parent_id
            parent_id = None
            for p_id, p_info in coordinator.parents_data.items():
                if p_info.get("name") == parent["name"]:
                    parent_id = p_id
                    break
            if parent_id:
                name_to_id_map[f"parent:{parent['name']}"] = parent_id

        # Phase 3: Add chores
        for chore in scenario_data.get("chores", []):
            result = await hass.config_entries.options.async_init(config_entry.entry_id)
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], {"next_step": "add_chore"}
            )

            # Map assigned kid names to IDs
            assigned_kid_ids = [
                name_to_id_map[f"kid:{name}"]
                for name in chore.get("assigned_to", [])
                if f"kid:{name}" in name_to_id_map
            ]

            chore_data = {
                "chore_name": chore["name"],
                "chore_default_points": chore.get("points", 10),
                "chore_assigned_kids": assigned_kid_ids,
                "chore_icon": chore.get("icon", "mdi:check"),
                "chore_recurring_frequency": chore.get("type", "once"),
            }
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], chore_data
            )

            # Extract chore_id
            chore_id = None
            for c_id, c_info in coordinator.chores_data.items():
                if c_info.get("name") == chore["name"]:
                    chore_id = c_id
                    break
            if chore_id:
                name_to_id_map[f"chore:{chore['name']}"] = chore_id

        # Phase 4: Add penalties
        for penalty in scenario_data.get("penalties", []):
            result = await hass.config_entries.options.async_init(config_entry.entry_id)
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], {"next_step": "add_penalty"}
            )

            penalty_data = {
                "penalty_name": penalty["name"],
                "penalty_points": abs(penalty["points"]),  # Store as positive
                "penalty_description": penalty.get("description", ""),
                "penalty_icon": penalty.get("icon", "mdi:alert"),
            }
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], penalty_data
            )

            # Extract penalty_id
            penalty_id = None
            for pen_id, pen_info in coordinator.penalties_data.items():
                if pen_info.get("name") == penalty["name"]:
                    penalty_id = pen_id
                    break
            if penalty_id:
                name_to_id_map[f"penalty:{penalty['name']}"] = penalty_id

        # Phase 5: Add bonuses
        for bonus in scenario_data.get("bonuses", []):
            result = await hass.config_entries.options.async_init(config_entry.entry_id)
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], {"next_step": "add_bonus"}
            )

            bonus_data = {
                "bonus_name": bonus["name"],
                "bonus_points": bonus["points"],
                "bonus_description": bonus.get("description", ""),
                "bonus_icon": bonus.get("icon", "mdi:plus-circle"),
            }
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], bonus_data
            )

            # Extract bonus_id
            bonus_id = None
            for b_id, b_info in coordinator.bonuses_data.items():
                if b_info.get("name") == bonus["name"]:
                    bonus_id = b_id
                    break
            if bonus_id:
                name_to_id_map[f"bonus:{bonus['name']}"] = bonus_id

        # Phase 6: Add rewards
        for reward in scenario_data.get("rewards", []):
            result = await hass.config_entries.options.async_init(config_entry.entry_id)
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], {"next_step": "add_reward"}
            )

            reward_data = {
                "reward_name": reward["name"],
                "reward_cost": reward["cost"],
                "reward_description": reward.get("description", ""),
                "reward_icon": reward.get("icon", "mdi:gift"),
            }
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], reward_data
            )

            # Extract reward_id
            reward_id = None
            for r_id, r_info in coordinator.rewards_data.items():
                if r_info.get("name") == reward["name"]:
                    reward_id = r_id
                    break
            if reward_id:
                name_to_id_map[f"reward:{reward['name']}"] = reward_id

        # Phase 7: Add badges (complex, cumulative type only for now)
        for badge in scenario_data.get("badges", []):
            if badge["type"] == "cumulative":
                result = await hass.config_entries.options.async_init(
                    config_entry.entry_id
                )
                result = await hass.config_entries.options.async_configure(
                    result["flow_id"], {"next_step": "add_badge"}
                )

                # Select cumulative type
                result = await hass.config_entries.options.async_configure(
                    result["flow_id"], {"badge_type": "cumulative"}
                )

                # Extract threshold value (handle both number and dict formats)
                threshold = badge.get("threshold", 100)
                if isinstance(threshold, dict):
                    threshold_value = threshold.get("value", 100)
                else:
                    threshold_value = threshold

                badge_data = {
                    "badge_name": badge["name"],
                    "badge_icon": badge.get("icon", "mdi:medal"),
                    "badge_description": badge.get("award", ""),
                    "badge_threshold_value": threshold_value,
                    "badge_point_multiplier": badge.get("points_multiplier", 1.0),
                }
                result = await hass.config_entries.options.async_configure(
                    result["flow_id"], badge_data
                )

                # Extract badge_id
                badge_id = None
                for bg_id, bg_info in coordinator.badges_data.items():
                    if bg_info.get("name") == badge["name"]:
                        badge_id = bg_id
                        break
                if badge_id:
                    name_to_id_map[f"badge:{badge['name']}"] = badge_id

        # Phase 8: Apply progress state (if any)
        progress = scenario_data.get("progress", {})
        for kid_name, kid_progress in progress.items():
            kid_id = name_to_id_map.get(f"kid:{kid_name}")
            if not kid_id:
                continue

            # Set points
            if "points" in kid_progress:
                coordinator.kids_data[kid_id]["points"] = float(kid_progress["points"])

            # Set lifetime points (points_net_all_time in point_stats)
            if "lifetime_points" in kid_progress:
                if "point_stats" not in coordinator.kids_data[kid_id]:
                    coordinator.kids_data[kid_id]["point_stats"] = {}
                coordinator.kids_data[kid_id]["point_stats"]["points_net_all_time"] = (
                    float(kid_progress["lifetime_points"])
                )
            # Also support direct point_stats structure
            elif (
                "point_stats" in kid_progress
                and "points_net_all_time" in kid_progress["point_stats"]
            ):
                if "point_stats" not in coordinator.kids_data[kid_id]:
                    coordinator.kids_data[kid_id]["point_stats"] = {}
                coordinator.kids_data[kid_id]["point_stats"]["points_net_all_time"] = (
                    float(kid_progress["point_stats"]["points_net_all_time"])
                )

            # Mark chores as completed
            for chore_name in kid_progress.get("chores_completed", []):
                chore_id = name_to_id_map.get(f"chore:{chore_name}")
                if (
                    chore_id
                    and chore_id not in coordinator.kids_data[kid_id]["approved_chores"]
                ):
                    coordinator.kids_data[kid_id]["approved_chores"].append(chore_id)

        # Persist changes and refresh
        coordinator._persist()  # pylint: disable=protected-access
        await coordinator.async_request_refresh()
        await hass.async_block_till_done()

    return name_to_id_map


async def apply_scenario_direct(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    scenario_data: dict[str, Any],
    mock_users: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Apply scenario data using direct coordinator calls (fast path).

    This bypasses the options flow UI and directly populates the coordinator
    using internal methods. Use this for workflow tests where you need fast
    setup with realistic data.

    Args:
        hass: Home Assistant instance
        config_entry: Config entry for the integration
        scenario_data: Scenario data loaded from YAML
        mock_users: Optional dict of mock HA users to link to parents/kids

    Returns:
        Dictionary mapping entity names to internal IDs for reference in tests

    Note:
        This function creates entities in dependency order:
        1. Kids (no dependencies)
        2. Parents (reference kid IDs)
        3. Chores (reference kid IDs)
        4. Badges, Bonuses, Penalties, Rewards
        5. Apply progress state (claimed chores, points, badges earned)
    """
    from custom_components.kidschores.const import COORDINATOR

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    name_to_id_map = {}

    # Mock notification to prevent ServiceNotFound errors during scenario loading
    # The _notify_kid method tries to call persistent_notification.create which
    # isn't available in test environment
    with (
        patch.object(coordinator, "_notify_kid_translated", new=AsyncMock()),
        patch.object(coordinator, "_notify_parents_translated", new=AsyncMock()),
    ):
        return await _apply_scenario_data(
            coordinator, scenario_data, name_to_id_map, hass, mock_users
        )


async def _apply_scenario_data(
    coordinator, scenario_data, name_to_id_map, hass, mock_users=None
):
    """Internal helper to apply scenario data with notification mocking."""
    # Phase 1: Create kids
    family = scenario_data.get("family", {})
    for kid in family.get("kids", []):
        kid_id = str(uuid.uuid4())
        kid_name = kid["name"]
        kid_data = create_mock_kid_data(name=kid_name, points=0.0)
        kid_data["internal_id"] = kid_id

        # Assign HA user if ha_user_name specified in YAML
        ha_user_name = kid.get("ha_user_name", "")
        if ha_user_name and mock_users and ha_user_name in mock_users:
            kid_data["ha_user_id"] = mock_users[ha_user_name].id

        # pylint: disable=protected-access
        coordinator._create_kid(kid_id, kid_data)
        name_to_id_map[f"kid:{kid_name}"] = kid_id

    # Phase 2: Create parents (they may reference kids)
    for parent in family.get("parents", []):
        parent_id = str(uuid.uuid4())
        parent_name = parent["name"]

        # Assign HA user if ha_user_name specified in YAML
        parent_ha_user_id = ""
        ha_user_name = parent.get("ha_user_name", "")
        if ha_user_name and mock_users and ha_user_name in mock_users:
            parent_ha_user_id = mock_users[ha_user_name].id

        parent_data = {
            "internal_id": parent_id,
            "name": parent_name,
            "ha_user_id": parent_ha_user_id,
            "associated_kids": [],  # Could map kid names to IDs if needed
            "enable_notifications": False,
            "mobile_notify_service": "",
            "use_persistent_notifications": False,
        }
        # pylint: disable=protected-access
        coordinator._create_parent(parent_id, parent_data)
        name_to_id_map[f"parent:{parent_name}"] = parent_id

    # Phase 3: Create chores (convert kid names to UUIDs)
    for chore in scenario_data.get("chores", []):
        chore_id = str(uuid.uuid4())
        chore_name = chore["name"]
        assigned_kid_names = chore.get("assigned_to", [])
        # Convert kid names to UUIDs
        assigned_kid_ids = [
            name_to_id_map[f"kid:{kid_name}"]
            for kid_name in assigned_kid_names
            if f"kid:{kid_name}" in name_to_id_map
        ]
        chore_data = create_mock_chore_data(
            name=chore_name,
            default_points=chore.get("points", 10),
            assigned_kids=assigned_kid_ids,  # Pass UUIDs, not names
            completion_criteria=chore.get("completion_criteria", "independent"),
        )
        chore_data["internal_id"] = chore_id
        chore_data["icon"] = chore.get("icon", "mdi:check")
        chore_data["recurring_frequency"] = chore.get("type", "once")
        chore_data["auto_approve"] = chore.get("auto_approve", False)

        # Phase 2+ scheduling fields (optional, for scenario_scheduling)
        if "approval_reset_type" in chore:
            chore_data["approval_reset_type"] = chore["approval_reset_type"]
        if "overdue_handling_type" in chore:
            chore_data["overdue_handling_type"] = chore["overdue_handling_type"]
        if "approval_reset_pending_claim_action" in chore:
            chore_data["approval_reset_pending_claim_action"] = chore[
                "approval_reset_pending_claim_action"
            ]
        # Handle relative due dates: "past" = yesterday, "future" = tomorrow
        if "due_date_relative" in chore:
            from datetime import datetime, timedelta, timezone

            now = datetime.now(timezone.utc)
            if chore["due_date_relative"] == "past":
                due_dt = now - timedelta(days=1)
            else:  # "future"
                due_dt = now + timedelta(days=1)
            # Set to 5 PM for consistency
            due_dt = due_dt.replace(hour=17, minute=0, second=0, microsecond=0)
            chore_data["due_date"] = due_dt.isoformat()

            # For INDEPENDENT chores, also populate per_kid_due_dates
            # (required for _check_overdue_independent to work)
            completion_criteria = chore.get("completion_criteria", "independent")
            if completion_criteria == "independent":
                per_kid_due_dates = {}
                for kid_id in assigned_kid_ids:
                    per_kid_due_dates[kid_id] = due_dt.isoformat()
                chore_data["per_kid_due_dates"] = per_kid_due_dates

        # pylint: disable=protected-access
        coordinator._create_chore(chore_id, chore_data)
        name_to_id_map[f"chore:{chore_name}"] = chore_id

    # Phase 4: Create bonuses
    for bonus in scenario_data.get("bonuses", []):
        bonus_id = str(uuid.uuid4())
        bonus_name = bonus["name"]
        bonus_data = {
            "internal_id": bonus_id,
            "name": bonus_name,
            "points": bonus.get(
                "points", bonus.get("points_value", 10)
            ),  # Handle both field names
            "description": bonus.get("description", ""),
            "icon": bonus.get("icon", "mdi:plus-circle"),
        }
        # pylint: disable=protected-access
        coordinator._create_bonus(bonus_id, bonus_data)
        name_to_id_map[f"bonus:{bonus_name}"] = bonus_id

    # Phase 5: Create penalties
    for penalty in scenario_data.get("penalties", []):
        penalty_id = str(uuid.uuid4())
        penalty_name = penalty["name"]
        penalty_data = {
            "internal_id": penalty_id,
            "name": penalty_name,
            "points": penalty.get(
                "points", penalty.get("points_value", -10)
            ),  # Handle both field names, store as negative
            "description": penalty.get("description", ""),
            "icon": penalty.get("icon", "mdi:alert"),
        }
        # pylint: disable=protected-access
        coordinator._create_penalty(penalty_id, penalty_data)
        name_to_id_map[f"penalty:{penalty_name}"] = penalty_id

    # Phase 6: Create rewards
    for reward in scenario_data.get("rewards", []):
        reward_id = str(uuid.uuid4())
        reward_name = reward["name"]
        reward_data = create_mock_reward_data(reward_name, reward["cost"])
        reward_data["internal_id"] = reward_id
        reward_data["icon"] = reward.get("icon", "mdi:gift")
        # pylint: disable=protected-access
        coordinator._create_reward(reward_id, reward_data)
        name_to_id_map[f"reward:{reward_name}"] = reward_id

    # Phase 7: Create badges (optional, complex structure)
    for badge in scenario_data.get("badges", []):
        badge_id = str(uuid.uuid4())
        badge_name = badge["name"]
        badge_data = {
            "internal_id": badge_id,
            "name": badge_name,
            "badge_type": badge["type"],  # Use badge_type, not type
            "icon": badge.get("icon", "mdi:medal"),
            "description": badge.get("award", ""),
            "badge_labels": [],
            "target": {
                "threshold_value": badge.get("threshold", 100),
                "maintenance_rules": badge.get("maintenance_rules", 0),
            },
            "awards": {
                "award_points": badge.get("award_points", 0),
                "award_reward": badge.get("award_reward", ""),
                "award_items": [],
                "point_multiplier": badge.get("points_multiplier", 1.0),
            },
            "assigned_to": [
                name_to_id_map.get(f"kid:{kid_name}")
                for kid_name in badge.get("assigned_to", [])
                if f"kid:{kid_name}" in name_to_id_map
            ],
            "earned_by": [],
            "reset_schedule": {
                "frequency": "none",
                "applicable_days": [],
                "custom_interval": None,
                "custom_interval_unit": None,
            },
        }
        # pylint: disable=protected-access
        coordinator._create_badge(badge_id, badge_data)
        name_to_id_map[f"badge:{badge_name}"] = badge_id

    # Phase 8: Apply progress state
    progress = scenario_data.get("progress", {})
    for kid_name, kid_progress in progress.items():
        kid_id = name_to_id_map.get(f"kid:{kid_name}")
        if not kid_id:
            continue

        # Set points and lifetime points
        if "points" in kid_progress:
            coordinator.kids_data[kid_id]["points"] = float(kid_progress["points"])
        if "lifetime_points" in kid_progress:
            if "point_stats" not in coordinator.kids_data[kid_id]:
                coordinator.kids_data[kid_id]["point_stats"] = {}
            coordinator.kids_data[kid_id]["point_stats"]["points_net_all_time"] = float(
                kid_progress["lifetime_points"]
            )
        # Also support direct point_stats structure
        elif (
            "point_stats" in kid_progress
            and "points_net_all_time" in kid_progress["point_stats"]
        ):
            if "point_stats" not in coordinator.kids_data[kid_id]:
                coordinator.kids_data[kid_id]["point_stats"] = {}
            coordinator.kids_data[kid_id]["point_stats"]["points_net_all_time"] = float(
                kid_progress["point_stats"]["points_net_all_time"]
            )

        # Mark chores as completed (using timestamp-based tracking v0.4.0+)
        for chore_name in kid_progress.get("chores_completed", []):
            chore_id = name_to_id_map.get(f"chore:{chore_name}")
            if chore_id:
                chore_info = coordinator.chores_data.get(chore_id, {})
                completion_criteria = chore_info.get(
                    "completion_criteria", const.COMPLETION_CRITERIA_INDEPENDENT
                )
                now_iso = dt_util.utcnow().isoformat()

                if completion_criteria == const.COMPLETION_CRITERIA_INDEPENDENT:
                    # INDEPENDENT: Store per-kid approval_period_start in kid_chore_data
                    if const.DATA_KID_CHORE_DATA not in coordinator.kids_data[kid_id]:
                        coordinator.kids_data[kid_id][const.DATA_KID_CHORE_DATA] = {}
                    kid_chore_data = coordinator.kids_data[kid_id][
                        const.DATA_KID_CHORE_DATA
                    ]
                    if chore_id not in kid_chore_data:
                        # v0.4.0+: Create COMPLETE structure with all required fields
                        kid_chore_data[chore_id] = {
                            const.DATA_KID_CHORE_DATA_NAME: chore_info.get(
                                const.DATA_CHORE_NAME, ""
                            ),
                            const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_APPROVED,
                            const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
                            const.DATA_KID_CHORE_DATA_LAST_APPROVED: now_iso,
                            const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
                            const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
                            const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
                            const.DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START: now_iso,
                            const.DATA_KID_CHORE_DATA_PERIODS: {
                                const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
                                const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
                                const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
                                const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
                                const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
                            },
                            const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
                        }
                    else:
                        # Structure exists, just update the approval fields
                        kid_chore_data[chore_id][
                            const.DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START
                        ] = now_iso
                        kid_chore_data[chore_id][
                            const.DATA_KID_CHORE_DATA_LAST_APPROVED
                        ] = now_iso
                else:
                    # SHARED: Store at chore level
                    chore_info[const.DATA_CHORE_APPROVAL_PERIOD_START] = now_iso
                    chore_info[const.DATA_CHORE_LAST_COMPLETED] = now_iso

        # Award badges
        for badge_name in kid_progress.get("badges_earned", []):
            badge_id = name_to_id_map.get(f"badge:{badge_name}")
            if badge_id:
                badge_entry = {
                    "badge_name": badge_name,
                    "last_awarded_date": "2024-01-01",
                    "award_count": 1,
                    "periods": {
                        "daily": {"2024-01-01": 1},
                        "weekly": {"2024-W01": 1},
                        "monthly": {"2024-01": 1},
                        "yearly": {"2024": 1},
                    },
                }
                if badge_id not in coordinator.kids_data[kid_id]["badges_earned"]:
                    coordinator.kids_data[kid_id]["badges_earned"][badge_id] = (
                        badge_entry
                    )

    # Persist and refresh
    # pylint: disable=protected-access
    coordinator._persist()  # Not async
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    # Note: Entity platforms (button, sensor) were already set up during init_integration
    # but with empty data. After loading scenario data, we need to trigger entity creation
    # for the new penalties, bonuses, etc. The platforms will be reloaded when the config
    # entry is reloaded, but for testing we manually add the entities here.
    # Note: Platform reload is handled by reload_entity_platforms() fixture.

    return name_to_id_map


def get_button_entity_id(
    hass: HomeAssistant,
    kid_name: str,
    action_type: str,
    entity_name: str,
) -> str | None:
    """Find button entity ID by pattern matching.

    Args:
        hass: Home Assistant instance
        kid_name: Name of the kid (will be slugified)
        action_type: Type of action (claim_chore, approve_chore, disapprove_chore, apply_bonus, etc.)
        entity_name: Name of the chore/reward/bonus/penalty

    Returns:
        Entity ID string if found, None otherwise

    Example:
        >>> button_id = get_button_entity_id(hass, "Zoë", "claim_chore", "Feed the cåts")
        >>> # Returns: "button.kc_zoe_chore_claim_feed_the_cats"
    """
    from homeassistant.util import slugify

    kid_slug = slugify(kid_name)
    entity_slug = slugify(entity_name)

    # Map action types to button patterns
    action_map = {
        "claim_chore": "chore_claim",
        "approve_chore": "chore_approval",
        "disapprove_chore": "chore_disapproval",
        "apply_bonus": "bonus_apply",
        "apply_penalty": "penalty_apply",
        "claim_reward": "reward_claim",
        "approve_reward": "reward_approval",
    }

    button_action = action_map.get(action_type, action_type)

    # Pattern: button.kc_{kid}_{button_action}_{entity}
    pattern = f"button.kc_{kid_slug}_{button_action}_{entity_slug}"

    # Check if entity exists
    state = hass.states.get(pattern)
    if state:
        return pattern

    # Fallback: search all button entities
    for entity_id in hass.states.async_entity_ids("button"):
        if (
            kid_slug in entity_id
            and entity_slug in entity_id
            and action_type in entity_id
        ):
            return entity_id

    return None


@pytest.fixture
async def scenario_minimal(  # pylint: disable=redefined-outer-name
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_hass_users: dict
) -> tuple[MockConfigEntry, dict[str, str]]:
    """Fixture providing minimal scenario with proper entity creation.

    Returns:
        Tuple of (config_entry, name_to_id_map)

    Scenario Contents:
        - 1 parent: Môm Astrid (linked to parent1 mock user)
        - 1 kid: Zoë (10 points, 10 lifetime)
        - 2 chores: Feed the cåts, Wåter the plänts
        - 1 badge: Brønze Står
        - 1 bonus: Stär Sprïnkle Bonus
        - 1 penalty: Førget Chöre
        - 1 reward: Ice Créam!

    Use for: Basic workflow tests, simple point tracking

    Note: Loads scenario data then reloads platforms to create entities
    """
    # Load scenario data into the already-initialized integration
    scenario_data = load_scenario_yaml("minimal")
    name_to_id_map = await apply_scenario_direct(
        hass, init_integration, scenario_data, mock_hass_users
    )

    # Reload platforms so they create entities with the new data
    await reload_entity_platforms(hass, init_integration)

    return init_integration, name_to_id_map


@pytest.fixture
async def scenario_medium(  # pylint: disable=redefined-outer-name
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> tuple[MockConfigEntry, dict[str, str]]:
    """Fixture providing medium scenario loaded into coordinator.

    Returns:
        Tuple of (config_entry, name_to_id_map)

    Scenario Contents:
        - 2 parents: Môm Astrid, Dad Leo
        - 2 kids: Zoë (35 points, 350 lifetime), Max! (15 points, 180 lifetime)
        - 4 chores: Including shared chore "Stär sweep"
        - 2 badges: Brønze Står, Dåily Dëlight (Zoë earned)
        - 2 bonuses, 2 penalties, 2 rewards

    Use for: Multi-kid coordination, shared chore tests
    """
    scenario_data = load_scenario_yaml("medium")
    name_to_id_map = await apply_scenario_direct(hass, init_integration, scenario_data)
    return init_integration, name_to_id_map


@pytest.fixture
async def scenario_full(  # pylint: disable=redefined-outer-name
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_hass_users: dict
) -> tuple[MockConfigEntry, dict[str, str]]:
    """Fixture providing full scenario loaded into coordinator.

    Returns:
        Tuple of (config_entry, name_to_id_map)

    Scenario Contents:
        - 2 parents: Môm Astrid (linked to parent1), Dad Leo (linked to parent2)
        - 3 kids: Zoë (520 lifetime), Max! (280 lifetime), Lila (310 lifetime)
        - 7 chores: Mix of daily, weekly, periodic, shared
        - 5 badges: Multiple cumulative badges with multipliers
        - 2 bonuses, 3 penalties, 5 rewards

    Use for: Badge maintenance, complex workflows, performance testing
    """
    scenario_data = load_scenario_yaml("full")
    name_to_id_map = await apply_scenario_direct(
        hass, init_integration, scenario_data, mock_hass_users
    )
    return init_integration, name_to_id_map


@pytest.fixture
async def scenario_scheduling(  # pylint: disable=redefined-outer-name
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_hass_users: dict
) -> tuple[MockConfigEntry, dict[str, str]]:
    """Fixture providing scheduling scenario for Phases 3-6 tests.

    Returns:
        Tuple of (config_entry, name_to_id_map)

    Scenario Contents:
        - 1 parent: Test Parent
        - 1 kid: Zoë (isolates scheduling from shared chore complexity)
        - 15 chores covering all scheduling configurations:
          - 5 approval_reset_type variations
          - 3 overdue_handling_type variations (with past due dates)
          - 3 pending_claim_action variations
          - 2 frequency variations (once, weekly overdue)

    Use for:
        - Phase 3: Due date calculation tests
        - Phase 4: Approval reset type tests (at_midnight_once bug)
        - Phase 5: Overdue handling tests
        - Phase 6: Pending claim action tests
    """
    scenario_data = load_scenario_yaml("scheduling")
    name_to_id_map = await apply_scenario_direct(
        hass, init_integration, scenario_data, mock_hass_users
    )

    # Reload platforms so entities are created with the new data
    await reload_entity_platforms(hass, init_integration)

    return init_integration, name_to_id_map


@pytest.fixture
async def scenario_stress(  # pylint: disable=redefined-outer-name
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> tuple[MockConfigEntry, dict[str, str]]:
    """Fixture providing stress test scenario loaded into coordinator.

    Returns:
        Tuple of (config_entry, name_to_id_map)

    Scenario Contents:
        - 25 parents across 5 estate zones
        - 100 kids across 4 age cohorts (25 each)
        - 500+ chores (mix of individual/multi-assigned, heavy use of shared chores)
        - 18 badges (8 cumulative + 10 periodic with different frequencies)
        - Expected ~1,500+ entities for performance testing

    Use for: Performance baseline capture, optimization validation, stress testing
    """
    scenario_data = load_scenario_yaml("performance_stress")
    name_to_id_map = await apply_scenario_direct(hass, init_integration, scenario_data)
    return init_integration, name_to_id_map


# ============================================================================
# HELPER FUNCTIONS - Testing Standards Maturity Initiative (Phase 1)
# ============================================================================
# Added: 2025-12-20
# Purpose: Reduce boilerplate, eliminate hardcoded values, standardize patterns
# See: docs/in-process/TESTING_STANDARDS_MATURITY_PLAN.md
# ============================================================================


def construct_entity_id(domain: str, kid_name: str, entity_type: str) -> str:
    """
    Construct entity ID matching integration's slugification logic.

    Args:
        domain: Entity domain (e.g., "sensor", "button")
        kid_name: Kid's display name from testdata (e.g., "Alex", "Sarah")
        entity_type: Entity type suffix (e.g., "points", "lifetime_points")

    Returns:
        Complete entity ID (e.g., "sensor.kc_alex_points")

    Examples:
        >>> construct_entity_id("sensor", "Alex", "points")
        "sensor.kc_alex_points"
        >>> construct_entity_id("button", "Sarah Jane", "approve_all_chores")
        "button.kc_sarah_jane_approve_all_chores"
        >>> construct_entity_id("sensor", "Zoë", "points")
        "sensor.kc_zoe_points"
    """
    from homeassistant.util import slugify

    # Use HA's slugify to match entity registry normalization (removes diacritics)
    kid_slug = slugify(kid_name)
    return f"{domain}.kc_{kid_slug}_{entity_type}"


async def assert_entity_state(
    hass: HomeAssistant,
    entity_id: str,
    expected_state: str,
    expected_attrs: dict[str, Any] | None = None,
) -> Any:
    """
    Assert entity exists with expected state and optionally attributes.

    Args:
        hass: Home Assistant instance
        entity_id: Full entity ID to check
        expected_state: Expected state value
        expected_attrs: Optional dict of attribute keys/values to verify

    Returns:
        State object (for further assertions if needed)

    Raises:
        AssertionError: If entity not found or state/attributes don't match

    Examples:
        >>> await assert_entity_state(hass, "sensor.kc_alex_points", "100")
        >>> await assert_entity_state(
        ...     hass,
        ...     "sensor.kc_alex_points",
        ...     "100",
        ...     {"unit_of_measurement": "points", "icon": "mdi:star"}
        ... )
    """
    state = hass.states.get(entity_id)
    assert state is not None, f"Entity {entity_id} not found in state machine"
    assert state.state == expected_state, (
        f"Entity {entity_id} state mismatch: "
        f"expected '{expected_state}', got '{state.state}'"
    )
    if expected_attrs:
        for key, value in expected_attrs.items():
            actual = state.attributes.get(key)
            assert actual == value, (
                f"Entity {entity_id} attribute '{key}' mismatch: "
                f"expected '{value}', got '{actual}'"
            )
    return state


def get_kid_by_name(data: dict[str, Any], name: str) -> dict[str, Any]:
    """
    Find kid in coordinator data by name (avoids hardcoded indices).

    Args:
        data: Coordinator data dict (from coordinator.data)
        name: Kid's display name (e.g., "Alex", "Zoë")

    Returns:
        Kid data dict

    Raises:
        ValueError: If kid not found

    Examples:
        >>> kid = get_kid_by_name(coordinator.data, "Alex")
        >>> assert kid["points"] == 100
    """
    kids = data.get(DATA_KIDS, {})
    for _, kid_data in kids.items():
        if kid_data.get("name") == name:
            return kid_data
    raise ValueError(f"Kid '{name}' not found in coordinator data")


def get_chore_by_name(
    data: dict[str, Any],
    chore_name: str,
    kid_name: str | None = None,
) -> dict[str, Any]:
    """
    Find chore in coordinator data by name, optionally filtered by kid.

    Args:
        data: Coordinator data dict (from coordinator.data)
        chore_name: Chore's display name (e.g., "Clean Room")
        kid_name: Optional kid name filter (for shared chores)

    Returns:
        Chore data dict

    Raises:
        ValueError: If chore not found

    Examples:
        >>> chore = get_chore_by_name(coordinator.data, "Clean Room")
        >>> chore = get_chore_by_name(coordinator.data, "Set Table", kid_name="Alex")
    """
    chores = data.get(DATA_CHORES, {})
    candidates = [c for c in chores.values() if c.get("name") == chore_name]

    if not candidates:
        raise ValueError(f"Chore '{chore_name}' not found in coordinator data")

    if kid_name and len(candidates) > 1:
        # Filter by kid if multiple matches (e.g., shared chores)
        kid = get_kid_by_name(data, kid_name)
        candidates = [
            c for c in candidates if c.get("assigned_to") == kid["internal_id"]
        ]
        if not candidates:
            raise ValueError(f"Chore '{chore_name}' not found for kid '{kid_name}'")

    return candidates[0]


def get_reward_by_name(
    data: dict[str, Any],
    reward_name: str,
    kid_name: str | None = None,
) -> dict[str, Any]:
    """
    Find reward in coordinator data by name, optionally filtered by kid.

    Args:
        data: Coordinator data dict (from coordinator.data)
        reward_name: Reward's display name (e.g., "Ice Cream")
        kid_name: Optional kid name filter

    Returns:
        Reward data dict

    Raises:
        ValueError: If reward not found

    Examples:
        >>> reward = get_reward_by_name(coordinator.data, "Ice Cream")
        >>> reward = get_reward_by_name(coordinator.data, "Movie", kid_name="Alex")
    """
    rewards = data.get(DATA_REWARDS, {})
    candidates = [r for r in rewards.values() if r.get("name") == reward_name]

    if not candidates:
        raise ValueError(f"Reward '{reward_name}' not found in coordinator data")

    if kid_name and len(candidates) > 1:
        # Filter by kid if multiple matches
        kid = get_kid_by_name(data, kid_name)
        candidates = [
            r for r in candidates if r.get("assigned_to") == kid["internal_id"]
        ]
        if not candidates:
            raise ValueError(f"Reward '{reward_name}' not found for kid '{kid_name}'")

    return candidates[0]


def get_penalty_by_name(data: dict[str, Any], penalty_name: str) -> dict[str, Any]:
    """Find penalty in coordinator data by name (avoids hardcoded indices).

    Args:
        data: Coordinator data dict (from coordinator.data)
        penalty_name: Penalty's display name (e.g., "Late to bed", "Room messy")

    Returns:
        Penalty data dict

    Raises:
        ValueError: If penalty not found

    Examples:
        >>> penalty = get_penalty_by_name(coordinator.data, "Late to bed")
        >>> assert penalty["points"] == -10
    """
    penalties = data.get(DATA_PENALTIES, {})
    for _, penalty_data in penalties.items():
        if penalty_data.get("name") == penalty_name:
            return penalty_data
    raise ValueError(f"Penalty '{penalty_name}' not found in coordinator data")


def get_badge_by_name(data: dict[str, Any], badge_name: str) -> dict[str, Any]:
    """Find badge in coordinator data by name (avoids hardcoded indices).

    Args:
        data: Coordinator data dict (from coordinator.data)
        badge_name: Badge's display name (e.g., "Chore Champion", "5-Day Streak")

    Returns:
        Badge data dict

    Raises:
        ValueError: If badge not found

    Examples:
        >>> badge = get_badge_by_name(coordinator.data, "Chore Champion")
        >>> assert badge["badge_type"] == "cumulative"
    """
    badges = data.get(DATA_BADGES, {})
    for _, badge_data in badges.items():
        if badge_data.get("name") == badge_name:
            return badge_data
    raise ValueError(f"Badge '{badge_name}' not found in coordinator data")


def get_bonus_by_name(data: dict[str, Any], bonus_name: str) -> dict[str, Any]:
    """Find bonus in coordinator data by name (avoids hardcoded indices).

    Args:
        data: Coordinator data dict (from coordinator.data)
        bonus_name: Bonus's display name (e.g., "Good behavior", "Extra help")

    Returns:
        Bonus data dict

    Raises:
        ValueError: If bonus not found

    Examples:
        >>> bonus = get_bonus_by_name(coordinator.data, "Good behavior")
        >>> assert bonus["points"] == 5
    """
    bonuses = data.get(DATA_BONUSES, {})
    for _, bonus_data in bonuses.items():
        if bonus_data.get("name") == bonus_name:
            return bonus_data
    raise ValueError(f"Bonus '{bonus_name}' not found in coordinator data")


def get_parent_by_name(data: dict[str, Any], parent_name: str) -> dict[str, Any]:
    """Find parent in coordinator data by name (avoids hardcoded indices).

    Args:
        data: Coordinator data dict (from coordinator.data)
        parent_name: Parent's display name (e.g., "Mom", "Dad")

    Returns:
        Parent data dict

    Raises:
        ValueError: If parent not found

    Examples:
        >>> parent = get_parent_by_name(coordinator.data, "Mom")
        >>> assert parent["ha_user_id"] == "user_123"
    """
    parents = data.get(DATA_PARENTS, {})
    for _, parent_data in parents.items():
        if parent_data.get("name") == parent_name:
            return parent_data
    raise ValueError(f"Parent '{parent_name}' not found in coordinator data")


def get_achievement_by_name(
    data: dict[str, Any], achievement_name: str
) -> dict[str, Any]:
    """Find achievement in coordinator data by name (avoids hardcoded indices).

    Args:
        data: Coordinator data dict (from coordinator.data)
        achievement_name: Achievement's display name (e.g., "First Chore", "100 Points")

    Returns:
        Achievement data dict

    Raises:
        ValueError: If achievement not found

    Examples:
        >>> achievement = get_achievement_by_name(coordinator.data, "First Chore")
        >>> assert achievement["target_count"] == 1
    """
    achievements = data.get(DATA_ACHIEVEMENTS, {})
    for _, achievement_data in achievements.items():
        if achievement_data.get("name") == achievement_name:
            return achievement_data
    raise ValueError(f"Achievement '{achievement_name}' not found in coordinator data")


def get_challenge_by_name(data: dict[str, Any], challenge_name: str) -> dict[str, Any]:
    """Find challenge in coordinator data by name (avoids hardcoded indices).

    Args:
        data: Coordinator data dict (from coordinator.data)
        challenge_name: Challenge's display name (e.g., "Daily Goal", "Weekly Target")

    Returns:
        Challenge data dict

    Raises:
        ValueError: If challenge not found

    Examples:
        >>> challenge = get_challenge_by_name(coordinator.data, "Daily Goal")
        >>> assert challenge["target_count"] == 5
    """
    challenges = data.get(DATA_CHALLENGES, {})
    for _, challenge_data in challenges.items():
        if challenge_data.get("name") == challenge_name:
            return challenge_data
    raise ValueError(f"Challenge '{challenge_name}' not found in coordinator data")


def create_test_datetime(days_offset: int = 0, hours_offset: int = 0) -> str:
    """
    Create UTC ISO datetime string for testing, offset from now.

    Args:
        days_offset: Days to offset from current time (negative = past)
        hours_offset: Hours to offset from current time (negative = past)

    Returns:
        UTC ISO datetime string compatible with testdata format

    Examples:
        >>> overdue_date = create_test_datetime(days_offset=-7)  # 7 days ago
        >>> future_date = create_test_datetime(days_offset=7)     # 7 days from now
        >>> soon = create_test_datetime(hours_offset=2)            # 2 hours from now
    """
    from datetime import datetime, timedelta, timezone

    test_dt = datetime.now(timezone.utc) + timedelta(
        days=days_offset, hours=hours_offset
    )
    return test_dt.isoformat()


def make_overdue(base_date: str | None = None, days: int = 7) -> str:
    """
    Create an overdue datetime string N days in the past.

    Args:
        base_date: Optional base date to offset from (ISO format)
        days: Number of days in the past (default: 7)

    Returns:
        UTC ISO datetime string representing overdue date

    Examples:
        >>> overdue = make_overdue()  # 7 days ago from now
        >>> overdue = make_overdue(days=14)  # 14 days ago
        >>> overdue = make_overdue(base_date="2024-12-25T00:00:00+00:00", days=3)
    """
    from datetime import datetime, timedelta, timezone

    if base_date:
        # Parse the base date and offset it
        base_dt = datetime.fromisoformat(base_date.replace("Z", "+00:00"))
        result_dt = base_dt - timedelta(days=days)
    else:
        # Offset from now
        result_dt = datetime.now(timezone.utc) - timedelta(days=days)

    return result_dt.isoformat()


def reset_chore_state_for_kid(
    coordinator: "KidsChoresDataCoordinator",
    kid_id: str,
    chore_id: str,
) -> None:
    """
    Reset chore state for a kid to PENDING with no pending claim or approval.

    v0.4.0+ uses timestamp-based tracking in kid_chore_data instead of the
    deprecated claimed_chores/approved_chores lists.

    This helper clears timestamps and sets state to PENDING so the chore
    can be claimed/approved again for testing.

    Args:
        coordinator: The KidsChores coordinator instance
        kid_id: The kid's internal ID
        chore_id: The chore's internal ID

    Usage:
        reset_chore_state_for_kid(coordinator, zoe_id, chore_id)
        coordinator._persist()
        # Now the chore can be claimed/approved again
    """
    from custom_components.kidschores import const

    kid_info = coordinator.kids_data.get(kid_id, {})

    # Initialize kid_chore_data if it doesn't exist
    if const.DATA_KID_CHORE_DATA not in kid_info:
        kid_info[const.DATA_KID_CHORE_DATA] = {}

    kid_chore_data = kid_info[const.DATA_KID_CHORE_DATA]

    # Get chore name for the entry
    chore_info = coordinator.chores_data.get(chore_id, {})
    chore_name = chore_info.get(const.DATA_CHORE_NAME, "")

    # Create or update the chore entry with reset state
    if chore_id not in kid_chore_data:
        kid_chore_data[chore_id] = {
            const.DATA_KID_CHORE_DATA_NAME: chore_name,
            const.DATA_KID_CHORE_DATA_STATE: const.CHORE_STATE_PENDING,
            const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT: 0,
            const.DATA_KID_CHORE_DATA_LAST_CLAIMED: None,
            const.DATA_KID_CHORE_DATA_LAST_APPROVED: None,
            const.DATA_KID_CHORE_DATA_LAST_DISAPPROVED: None,
            const.DATA_KID_CHORE_DATA_LAST_OVERDUE: None,
            const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: None,
            const.DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START: None,
            const.DATA_KID_CHORE_DATA_PERIODS: {
                const.DATA_KID_CHORE_DATA_PERIODS_DAILY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_WEEKLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_MONTHLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_YEARLY: {},
                const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: {},
            },
            const.DATA_KID_CHORE_DATA_BADGE_REFS: [],
        }
    else:
        # Reset existing entry
        kid_chore_data[chore_id][const.DATA_KID_CHORE_DATA_STATE] = (
            const.CHORE_STATE_PENDING
        )
        kid_chore_data[chore_id][const.DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT] = 0
        kid_chore_data[chore_id][const.DATA_KID_CHORE_DATA_LAST_CLAIMED] = None
        kid_chore_data[chore_id][const.DATA_KID_CHORE_DATA_LAST_APPROVED] = None
        kid_chore_data[chore_id][const.DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START] = None


def get_chore_state_for_kid(
    coordinator: "KidsChoresDataCoordinator",
    kid_id: str,
    chore_id: str,
) -> str:
    """
    Get the current chore state for a kid from the timestamp-based tracking.

    v0.4.0+ uses chore_data[chore_id]["state"] instead of deprecated lists.

    Args:
        coordinator: The KidsChores coordinator instance
        kid_id: The kid's internal ID
        chore_id: The chore's internal ID

    Returns:
        The chore state string: "pending", "claimed", "approved", or ""
    """
    from custom_components.kidschores import const

    kid_info = coordinator.kids_data.get(kid_id, {})
    chore_data = kid_info.get(const.DATA_KID_CHORE_DATA, {})
    chore_entry = chore_data.get(chore_id, {})
    return chore_entry.get(const.DATA_KID_CHORE_DATA_STATE, "")


def is_chore_claimed_for_kid(
    coordinator: "KidsChoresDataCoordinator",
    kid_id: str,
    chore_id: str,
) -> bool:
    """Check if a chore is in 'claimed' state for a kid (v0.4.0+ timestamp-based)."""
    from custom_components.kidschores import const

    return (
        get_chore_state_for_kid(coordinator, kid_id, chore_id)
        == const.CHORE_STATE_CLAIMED
    )


def is_chore_approved_for_kid(
    coordinator: "KidsChoresDataCoordinator",
    kid_id: str,
    chore_id: str,
) -> bool:
    """Check if a chore is in 'approved' state for a kid (v0.4.0+ timestamp-based)."""
    from custom_components.kidschores import const

    return (
        get_chore_state_for_kid(coordinator, kid_id, chore_id)
        == const.CHORE_STATE_APPROVED
    )


def is_chore_pending_for_kid(
    coordinator: "KidsChoresDataCoordinator",
    kid_id: str,
    chore_id: str,
) -> bool:
    """Check if a chore is in 'pending' state for a kid (v0.4.0+ timestamp-based)."""
    from custom_components.kidschores import const

    return (
        get_chore_state_for_kid(coordinator, kid_id, chore_id)
        == const.CHORE_STATE_PENDING
    )


# =============================================================================
# SENSOR-BASED ENTITY DISCOVERY HELPERS
# =============================================================================
#
# These helpers query the integration's sensors to discover entity IDs and state,
# eliminating guesswork about entity ID patterns. Use these in workflow tests
# AFTER entities have been created via config/options flow.
#
# The dashboard helper sensor (sensor.kc_<kid>_ui_dashboard_helper) is the
# single source of truth for all entity IDs. It contains pre-computed lists
# with entity IDs already resolved.
#
# Key attributes on dashboard helper:
#   - chores: list of {eid, name, status, can_claim, can_approve, ...}
#   - rewards: list of {eid, name, status, cost, ...}
#   - pending_approvals: {chores: [{approve_button_eid, disapprove_button_eid}], rewards: [...]}
#   - points_buttons: list of button entity IDs for point adjustments
#
# The chore/reward status sensors contain button eids in their attributes:
#   - approve_button_eid, disapprove_button_eid, claim_button_eid
#
# =============================================================================


def get_dashboard_helper_sensor_id(kid_name: str) -> str:
    """
    Get the entity ID for a kid's dashboard helper sensor.

    Args:
        kid_name: Kid's display name (e.g., "Alex", "Zoë")

    Returns:
        Entity ID (e.g., "sensor.kc_alex_ui_dashboard_helper")

    Example:
        >>> helper_id = get_dashboard_helper_sensor_id("Alex")
        >>> state = hass.states.get(helper_id)
        >>> chores = state.attributes.get("chores", [])
    """
    from homeassistant.util import slugify

    kid_slug = slugify(kid_name)
    return f"sensor.kc_{kid_slug}_ui_dashboard_helper"


def get_chore_eid_from_dashboard(
    hass: "HomeAssistant",  # noqa: F821
    kid_name: str,
    chore_name: str,
) -> str | None:
    """
    Get chore status sensor entity ID from dashboard helper.

    The dashboard helper's "chores" attribute contains pre-computed
    entity IDs - no need to guess the slugification pattern.

    Args:
        hass: Home Assistant instance
        kid_name: Kid's display name
        chore_name: Chore's display name

    Returns:
        Entity ID (e.g., "sensor.kc_alex_chore_status_clean_room") or None

    Example:
        >>> eid = get_chore_eid_from_dashboard(hass, "Alex", "Clean room!")
        >>> state = hass.states.get(eid)
    """
    helper_id = get_dashboard_helper_sensor_id(kid_name)
    state = hass.states.get(helper_id)
    if not state:
        return None

    chores = state.attributes.get("chores", [])
    for chore in chores:
        if chore.get("name") == chore_name:
            return chore.get("eid")
    return None


def get_reward_eid_from_dashboard(
    hass: "HomeAssistant",  # noqa: F821
    kid_name: str,
    reward_name: str,
) -> str | None:
    """
    Get reward status sensor entity ID from dashboard helper.

    Args:
        hass: Home Assistant instance
        kid_name: Kid's display name
        reward_name: Reward's display name

    Returns:
        Entity ID or None
    """
    helper_id = get_dashboard_helper_sensor_id(kid_name)
    state = hass.states.get(helper_id)
    if not state:
        return None

    rewards = state.attributes.get("rewards", [])
    for reward in rewards:
        if reward.get("name") == reward_name:
            return reward.get("eid")
    return None


async def get_chore_button_eids(
    hass: "HomeAssistant",  # noqa: F821
    kid_name: str,
    chore_name: str,
) -> dict[str, str | None]:
    """
    Get claim/approve/disapprove button entity IDs for a chore.

    First finds the chore status sensor via dashboard helper, then reads
    button entity IDs from its attributes.

    Args:
        hass: Home Assistant instance
        kid_name: Kid's display name (e.g., "Alex")
        chore_name: Chore's display name (e.g., "Clean room!")

    Returns:
        Dict with keys: "claim", "approve", "disapprove"
        Values are entity IDs or None if not found.

    Example:
        >>> buttons = await get_chore_button_eids(hass, "Alex", "Clean room!")
        >>> await hass.services.async_call("button", "press",
        ...     {"entity_id": buttons["claim"]})

    Raises:
        ValueError: If chore sensor not found
    """
    from custom_components.kidschores.const import (
        ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID,
        ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID,
        ATTR_CHORE_DISAPPROVE_BUTTON_ENTITY_ID,
    )

    # Get chore sensor eid from dashboard helper
    chore_eid = get_chore_eid_from_dashboard(hass, kid_name, chore_name)
    if not chore_eid:
        raise ValueError(
            f"Chore '{chore_name}' not found for kid '{kid_name}' in dashboard helper. "
            f"Ensure entities are set up before calling this helper."
        )

    state = hass.states.get(chore_eid)
    if state is None:
        raise ValueError(f"Chore status sensor not found: {chore_eid}")

    return {
        "claim": state.attributes.get(ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID),
        "approve": state.attributes.get(ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID),
        "disapprove": state.attributes.get(ATTR_CHORE_DISAPPROVE_BUTTON_ENTITY_ID),
    }


async def get_reward_button_eids(
    hass: "HomeAssistant",  # noqa: F821
    kid_name: str,
    reward_name: str,
) -> dict[str, str | None]:
    """
    Get claim/approve/disapprove button entity IDs for a reward.

    Args:
        hass: Home Assistant instance
        kid_name: Kid's display name
        reward_name: Reward's display name

    Returns:
        Dict with keys: "claim", "approve", "disapprove"

    Raises:
        ValueError: If reward sensor not found
    """
    from custom_components.kidschores.const import (
        ATTR_REWARD_APPROVE_BUTTON_ENTITY_ID,
        ATTR_REWARD_CLAIM_BUTTON_ENTITY_ID,
        ATTR_REWARD_DISAPPROVE_BUTTON_ENTITY_ID,
    )

    # Get reward sensor eid from dashboard helper
    reward_eid = get_reward_eid_from_dashboard(hass, kid_name, reward_name)
    if not reward_eid:
        raise ValueError(
            f"Reward '{reward_name}' not found for kid '{kid_name}' in dashboard helper."
        )

    state = hass.states.get(reward_eid)
    if state is None:
        raise ValueError(f"Reward status sensor not found: {reward_eid}")

    return {
        "claim": state.attributes.get(ATTR_REWARD_CLAIM_BUTTON_ENTITY_ID),
        "approve": state.attributes.get(ATTR_REWARD_APPROVE_BUTTON_ENTITY_ID),
        "disapprove": state.attributes.get(ATTR_REWARD_DISAPPROVE_BUTTON_ENTITY_ID),
    }


def get_chore_state_from_dashboard(
    hass: "HomeAssistant",  # noqa: F821
    kid_name: str,
    chore_name: str,
) -> str | None:
    """
    Get chore status directly from dashboard helper (no sensor lookup needed).

    The dashboard helper already has status pre-computed in its chores list.

    Args:
        hass: Home Assistant instance
        kid_name: Kid's display name
        chore_name: Chore's display name

    Returns:
        Status string (e.g., "pending", "claimed", "approved") or None

    Example:
        >>> status = get_chore_state_from_dashboard(hass, "Alex", "Clean room!")
        >>> assert status == "pending"
    """
    helper_id = get_dashboard_helper_sensor_id(kid_name)
    state = hass.states.get(helper_id)
    if not state:
        return None

    chores = state.attributes.get("chores", [])
    for chore in chores:
        if chore.get("name") == chore_name:
            return chore.get("status")
    return None


def get_reward_state_from_dashboard(
    hass: "HomeAssistant",  # noqa: F821
    kid_name: str,
    reward_name: str,
) -> str | None:
    """
    Get reward status directly from dashboard helper.

    Args:
        hass: Home Assistant instance
        kid_name: Kid's display name
        reward_name: Reward's display name

    Returns:
        Status string or None
    """
    helper_id = get_dashboard_helper_sensor_id(kid_name)
    state = hass.states.get(helper_id)
    if not state:
        return None

    rewards = state.attributes.get("rewards", [])
    for reward in rewards:
        if reward.get("name") == reward_name:
            return reward.get("status")
    return None


def get_chore_can_claim(
    hass: "HomeAssistant",  # noqa: F821
    kid_name: str,
    chore_name: str,
) -> bool | None:
    """
    Check if chore can be claimed (from dashboard helper).

    Args:
        hass: Home Assistant instance
        kid_name: Kid's display name
        chore_name: Chore's display name

    Returns:
        True if can_claim, False if not, None if not found
    """
    helper_id = get_dashboard_helper_sensor_id(kid_name)
    state = hass.states.get(helper_id)
    if not state:
        return None

    chores = state.attributes.get("chores", [])
    for chore in chores:
        if chore.get("name") == chore_name:
            return chore.get("can_claim")
    return None


def get_chore_can_approve(
    hass: "HomeAssistant",  # noqa: F821
    kid_name: str,
    chore_name: str,
) -> bool | None:
    """
    Check if chore can be approved (from dashboard helper).

    Args:
        hass: Home Assistant instance
        kid_name: Kid's display name
        chore_name: Chore's display name

    Returns:
        True if can_approve, False if not, None if not found
    """
    helper_id = get_dashboard_helper_sensor_id(kid_name)
    state = hass.states.get(helper_id)
    if not state:
        return None

    chores = state.attributes.get("chores", [])
    for chore in chores:
        if chore.get("name") == chore_name:
            return chore.get("can_approve")
    return None


async def press_chore_button(
    hass: "HomeAssistant",  # noqa: F821
    kid_name: str,
    chore_name: str,
    button_type: str,
) -> None:
    """
    Press a chore button (claim/approve/disapprove) by discovering its entity ID.

    This is a convenience wrapper that combines get_chore_button_eids()
    with service calls.

    Args:
        hass: Home Assistant instance
        kid_name: Kid's display name
        chore_name: Chore's display name
        button_type: One of "claim", "approve", "disapprove"

    Raises:
        ValueError: If button_type invalid or button entity not found

    Example:
        >>> await press_chore_button(hass, "Alex", "Clean room!", "claim")
        >>> await hass.async_block_till_done()
        >>> status = get_chore_state_from_dashboard(hass, "Alex", "Clean room!")
        >>> assert status == "claimed"
    """
    if button_type not in ("claim", "approve", "disapprove"):
        raise ValueError(f"Invalid button_type: {button_type}")

    buttons = await get_chore_button_eids(hass, kid_name, chore_name)
    button_id = buttons.get(button_type)

    if not button_id:
        raise ValueError(
            f"Button entity not found for {button_type} "
            f"(kid={kid_name}, chore={chore_name})"
        )

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": button_id},
        blocking=True,
    )


async def press_reward_button(
    hass: "HomeAssistant",  # noqa: F821
    kid_name: str,
    reward_name: str,
    button_type: str,
) -> None:
    """
    Press a reward button (claim/approve/disapprove) by discovering its entity ID.

    Args:
        hass: Home Assistant instance
        kid_name: Kid's display name
        reward_name: Reward's display name
        button_type: One of "claim", "approve", "disapprove"

    Raises:
        ValueError: If button_type invalid or button entity not found
    """
    if button_type not in ("claim", "approve", "disapprove"):
        raise ValueError(f"Invalid button_type: {button_type}")

    buttons = await get_reward_button_eids(hass, kid_name, reward_name)
    button_id = buttons.get(button_type)

    if not button_id:
        raise ValueError(
            f"Button entity not found for {button_type} "
            f"(kid={kid_name}, reward={reward_name})"
        )

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": button_id},
        blocking=True,
    )


def list_all_chores_for_kid(
    hass: "HomeAssistant",  # noqa: F821
    kid_name: str,
) -> list[dict]:
    """
    Get all chores for a kid from dashboard helper (for debugging/introspection).

    Returns:
        List of chore dicts with eid, name, status, can_claim, can_approve, etc.

    Example:
        >>> chores = list_all_chores_for_kid(hass, "Alex")
        >>> for c in chores:
        ...     print(f"{c['name']}: {c['status']} (eid={c['eid']})")
    """
    helper_id = get_dashboard_helper_sensor_id(kid_name)
    state = hass.states.get(helper_id)
    if not state:
        return []
    return state.attributes.get("chores", [])


def list_all_rewards_for_kid(
    hass: "HomeAssistant",  # noqa: F821
    kid_name: str,
) -> list[dict]:
    """
    Get all rewards for a kid from dashboard helper (for debugging/introspection).

    Returns:
        List of reward dicts with eid, name, status, cost, etc.
    """
    helper_id = get_dashboard_helper_sensor_id(kid_name)
    state = hass.states.get(helper_id)
    if not state:
        return []
    return state.attributes.get("rewards", [])
