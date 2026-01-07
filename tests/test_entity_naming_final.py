"""Test entity naming consistency - badges, rewards, buttons, and friendly names."""

# pylint: disable=protected-access,redefined-outer-name  # Pytest fixtures

from unittest.mock import AsyncMock

import pytest

from custom_components.kidschores import const
from custom_components.kidschores.button import (
    KidChoreClaimButton,
    ParentBonusApplyButton,
    ParentChoreDisapproveButton,
    ParentPenaltyApplyButton,
    ParentRewardDisapproveButton,
)
from custom_components.kidschores.coordinator import KidsChoresDataCoordinator
from custom_components.kidschores.sensor import (
    KidBadgeProgressSensor,
    KidBadgesSensor,
    KidChoreStatusSensor,
    KidRewardStatusSensor,
    SystemBadgeSensor,
)
from custom_components.kidschores.sensor_legacy import KidPenaltyAppliedSensor
from tests.conftest import MockConfigEntry


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        title="KidsChores",
        domain=const.DOMAIN,
        data={},
        version=1,
        minor_version=1,
    )


@pytest.mark.asyncio
async def test_badge_sensor_has_system_device_info(mock_config_entry):
    """Test that SystemBadgeSensor (global) uses system device info, not kid device."""
    coordinator = AsyncMock(spec=KidsChoresDataCoordinator)
    coordinator.badges_data = {
        "badge_1": {
            const.DATA_BADGE_NAME: "Star Badge",
        }
    }
    coordinator.kids_data = {}

    sensor = SystemBadgeSensor(
        coordinator=coordinator,
        entry=mock_config_entry,
        badge_id="badge_1",
        badge_name="Star Badge",
    )

    # Verify device_info is system device, not kid device
    assert sensor._attr_device_info is not None
    device_info = sensor._attr_device_info
    # System device should contain "system" in its identifiers
    identifiers = device_info.get("identifiers", set())
    # Check if any identifier tuple contains "system"
    assert any("system" in str(ident) for ident in identifiers)


@pytest.mark.asyncio
async def test_kid_badges_sensor_friendly_name():
    """Test that KidBadgesSensor has 'Highest Badge' in friendly name."""
    mock_config_entry = MockConfigEntry(
        title="KidsChores",
        domain=const.DOMAIN,
        data={},
    )

    coordinator = AsyncMock(spec=KidsChoresDataCoordinator)
    coordinator.kids_data = {
        "kid_1": {
            const.DATA_KID_NAME: "Alice",
            const.DATA_KID_BADGES_EARNED: {},
        }
    }

    sensor = KidBadgesSensor(
        coordinator=coordinator,
        entry=mock_config_entry,
        kid_id="kid_1",
        kid_name="Alice",
    )

    # Verify translation key is set correctly
    assert sensor._attr_translation_key == const.TRANS_KEY_SENSOR_KID_BADGES_SENSOR
    # Verify entity has name attribute for friendly name translation
    assert sensor._attr_has_entity_name is True


@pytest.mark.asyncio
async def test_badge_progress_sensor_has_kid_name():
    """Test that KidBadgeProgressSensor includes kid_name attribute."""
    mock_config_entry = MockConfigEntry(
        title="KidsChores",
        domain=const.DOMAIN,
        data={},
    )

    coordinator = AsyncMock(spec=KidsChoresDataCoordinator)
    coordinator.kids_data = {
        "kid_1": {
            const.DATA_KID_NAME: "Alice",
        }
    }
    coordinator.badges_data = {
        "badge_1": {
            const.DATA_BADGE_NAME: "Star Badge",
            const.DATA_BADGE_TARGET: 10,
        }
    }

    sensor = KidBadgeProgressSensor(
        coordinator=coordinator,
        entry=mock_config_entry,
        kid_id="kid_1",
        kid_name="Alice",
        badge_id="badge_1",
        badge_name="Star Badge",
    )

    # Verify kid_name is in initialization
    assert sensor._kid_name == "Alice"


@pytest.mark.asyncio
async def test_chore_status_sensor_has_kid_name_and_device():
    """Test that KidChoreStatusSensor has kid_name attribute and kid device info."""
    mock_config_entry = MockConfigEntry(
        title="KidsChores",
        domain=const.DOMAIN,
        data={},
    )

    coordinator = AsyncMock(spec=KidsChoresDataCoordinator)
    coordinator.kids_data = {
        "kid_1": {
            const.DATA_KID_NAME: "Alice",
        }
    }
    coordinator.chores_data = {
        "chore_1": {
            const.DATA_CHORE_NAME: "Wash Dishes",
            const.DATA_CHORE_LABELS: [],
        }
    }

    sensor = KidChoreStatusSensor(
        coordinator=coordinator,
        entry=mock_config_entry,
        kid_id="kid_1",
        kid_name="Alice",
        chore_id="chore_1",
        chore_name="Wash Dishes",
    )

    # Verify device_info is kid-specific
    assert sensor._attr_device_info is not None
    device_info = sensor._attr_device_info
    # Kid device should have kid_id in identifiers
    assert (const.DOMAIN, "kid_1") in device_info.get("identifiers", [])


@pytest.mark.asyncio
async def test_reward_status_sensor_has_kid_name():
    """Test that KidRewardStatusSensor includes kid_name attribute."""
    mock_config_entry = MockConfigEntry(
        title="KidsChores",
        domain=const.DOMAIN,
        data={},
    )

    coordinator = AsyncMock(spec=KidsChoresDataCoordinator)
    coordinator.kids_data = {
        "kid_1": {
            const.DATA_KID_NAME: "Alice",
            const.DATA_KID_REWARD_DATA: {},  # Modern structure - no legacy fields
        }
    }
    coordinator.rewards_data = {
        "reward_1": {
            const.DATA_REWARD_NAME: "Ice Cream",
            const.DATA_REWARD_LABELS: [],
            const.DATA_REWARD_DESCRIPTION: "Ice cream reward",
            const.DATA_REWARD_COST: 100,
            const.DATA_REWARD_ICON: "mdi:ice-cream",
        }
    }

    sensor = KidRewardStatusSensor(
        coordinator=coordinator,
        entry=mock_config_entry,
        kid_id="kid_1",
        kid_name="Alice",
        reward_id="reward_1",
        reward_name="Ice Cream",
    )

    # Verify kid_name is in extra_state_attributes
    attrs = sensor.extra_state_attributes
    assert const.ATTR_KID_NAME in attrs
    assert attrs[const.ATTR_KID_NAME] == "Alice"


@pytest.mark.asyncio
async def test_penalty_applies_sensor_has_kid_name():
    """Test that KidPenaltyAppliedSensor includes kid_name attribute."""
    mock_config_entry = MockConfigEntry(
        title="KidsChores",
        domain=const.DOMAIN,
        data={},
    )

    coordinator = AsyncMock(spec=KidsChoresDataCoordinator)
    coordinator.kids_data = {
        "kid_1": {
            const.DATA_KID_NAME: "Alice",
            const.DATA_KID_PENALTY_APPLIES: {},
        }
    }
    coordinator.penalties_data = {
        "penalty_1": {
            const.DATA_PENALTY_NAME: "No dessert",
            const.DATA_PENALTY_LABELS: [],
            const.DATA_PENALTY_DESCRIPTION: "No dessert for a week",
            const.DATA_PENALTY_POINTS: 10,
            const.DATA_PENALTY_ICON: "mdi:block-helper",
        }
    }

    sensor = KidPenaltyAppliedSensor(
        coordinator=coordinator,
        entry=mock_config_entry,
        kid_id="kid_1",
        kid_name="Alice",
        penalty_id="penalty_1",
        penalty_name="No dessert",
    )

    # Verify kid_name is in extra_state_attributes
    attrs = sensor.extra_state_attributes
    assert const.ATTR_KID_NAME in attrs
    assert attrs[const.ATTR_KID_NAME] == "Alice"


@pytest.mark.asyncio
async def test_claim_chore_button_has_kid_name():
    """Test that KidChoreClaimButton includes kid_name in extra_state_attributes."""
    mock_config_entry = MockConfigEntry(
        title="KidsChores",
        domain=const.DOMAIN,
        data={},
    )

    coordinator = AsyncMock(spec=KidsChoresDataCoordinator)
    coordinator.chores_data = {
        "chore_1": {
            const.DATA_CHORE_NAME: "Wash Dishes",
            const.DATA_CHORE_LABELS: [],
        }
    }

    button = KidChoreClaimButton(
        coordinator=coordinator,
        entry=mock_config_entry,
        kid_id="kid_1",
        kid_name="Alice",
        chore_id="chore_1",
        chore_name="Wash Dishes",
        icon="mdi:checkbox-marked-circle",
    )

    # Verify kid_name is in extra_state_attributes
    attrs = button.extra_state_attributes
    assert const.ATTR_KID_NAME in attrs
    assert attrs[const.ATTR_KID_NAME] == "Alice"


@pytest.mark.asyncio
async def test_disapprove_chore_button_has_kid_name():
    """Test that DisapproveChoreButton includes kid_name in extra_state_attributes."""
    mock_config_entry = MockConfigEntry(
        title="KidsChores",
        domain=const.DOMAIN,
        data={},
    )

    coordinator = AsyncMock(spec=KidsChoresDataCoordinator)
    coordinator.chores_data = {
        "chore_1": {
            const.DATA_CHORE_NAME: "Wash Dishes",
            const.DATA_CHORE_LABELS: [],
        }
    }

    button = ParentChoreDisapproveButton(
        coordinator=coordinator,
        entry=mock_config_entry,
        kid_id="kid_1",
        kid_name="Alice",
        chore_id="chore_1",
        chore_name="Wash Dishes",
        icon="mdi:close-circle",
    )

    # Verify kid_name is in extra_state_attributes
    attrs = button.extra_state_attributes
    assert const.ATTR_KID_NAME in attrs
    assert attrs[const.ATTR_KID_NAME] == "Alice"


@pytest.mark.asyncio
async def test_bonus_button_has_kid_name():
    """Test that BonusButton includes kid_name in extra_state_attributes."""
    mock_config_entry = MockConfigEntry(
        title="KidsChores",
        domain=const.DOMAIN,
        data={},
    )

    coordinator = AsyncMock(spec=KidsChoresDataCoordinator)
    coordinator.bonuses_data = {
        "bonus_1": {
            const.DATA_BONUS_NAME: "Extra points",
            const.DATA_BONUS_LABELS: [],
        }
    }

    button = ParentBonusApplyButton(
        coordinator=coordinator,
        entry=mock_config_entry,
        kid_id="kid_1",
        kid_name="Alice",
        bonus_id="bonus_1",
        bonus_name="Extra points",
        icon="mdi:star",
    )

    # Verify kid_name is in extra_state_attributes
    attrs = button.extra_state_attributes
    assert const.ATTR_KID_NAME in attrs
    assert attrs[const.ATTR_KID_NAME] == "Alice"


@pytest.mark.asyncio
async def test_penalty_button_has_kid_name():
    """Test that PenaltyButton includes kid_name in extra_state_attributes."""
    mock_config_entry = MockConfigEntry(
        title="KidsChores",
        domain=const.DOMAIN,
        data={},
    )

    coordinator = AsyncMock(spec=KidsChoresDataCoordinator)
    coordinator.penalties_data = {
        "penalty_1": {
            const.DATA_PENALTY_NAME: "No dessert",
            const.DATA_PENALTY_LABELS: [],
        }
    }

    button = ParentPenaltyApplyButton(
        coordinator=coordinator,
        entry=mock_config_entry,
        kid_id="kid_1",
        kid_name="Alice",
        penalty_id="penalty_1",
        penalty_name="No dessert",
        icon="mdi:block-helper",
    )

    # Verify kid_name is in extra_state_attributes
    attrs = button.extra_state_attributes
    assert const.ATTR_KID_NAME in attrs
    assert attrs[const.ATTR_KID_NAME] == "Alice"


@pytest.mark.asyncio
async def test_disapprove_reward_button_has_kid_name():
    """Test that DisapproveRewardButton includes kid_name in extra_state_attributes."""
    mock_config_entry = MockConfigEntry(
        title="KidsChores",
        domain=const.DOMAIN,
        data={},
    )

    coordinator = AsyncMock(spec=KidsChoresDataCoordinator)
    coordinator.rewards_data = {
        "reward_1": {
            const.DATA_REWARD_NAME: "Ice Cream",
            const.DATA_REWARD_LABELS: [],
        }
    }

    button = ParentRewardDisapproveButton(
        coordinator=coordinator,
        entry=mock_config_entry,
        kid_id="kid_1",
        kid_name="Alice",
        reward_id="reward_1",
        reward_name="Ice Cream",
        icon="mdi:close-circle",
    )

    # Verify kid_name is in extra_state_attributes
    attrs = button.extra_state_attributes
    assert const.ATTR_KID_NAME in attrs
    assert attrs[const.ATTR_KID_NAME] == "Alice"
