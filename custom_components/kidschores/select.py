# File: select.py
# pyright: reportIncompatibleVariableOverride=false
# ^ Suppresses Pylance warnings about @property overriding @cached_property from base classes.
#   This is intentional: our entities compute dynamic values on each access,
#   so we use @property instead of @cached_property to avoid stale cached data.
"""Select entities for the KidsChores integration.

Allows the user to pick from all chores, all rewards, or all penalties
in a global manner. This is useful for automations or scripts where a
user wishes to select a chore/reward/penalty dynamically.
"""

from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import const
from . import kc_helpers as kh
from .coordinator import KidsChoresDataCoordinator
from .entity import KidsChoresCoordinatorEntity

# Silver requirement: Parallel Updates
# Set to 0 (unlimited) for coordinator-based entities that don't poll
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the KidsChores select entities from a config entry."""
    data = hass.data[const.DOMAIN][entry.entry_id]
    coordinator: KidsChoresDataCoordinator = data[const.COORDINATOR]

    selects = []

    # Legacy system-wide select entities (disabled by default)
    show_legacy_entities = entry.options.get(
        const.CONF_SHOW_LEGACY_ENTITIES, const.DEFAULT_SHOW_LEGACY_ENTITIES
    )
    if show_legacy_entities:
        selects.extend(
            [
                SystemChoresSelect(coordinator, entry),
                SystemRewardsSelect(coordinator, entry),
                SystemPenaltiesSelect(coordinator, entry),
                SystemBonusesSelect(coordinator, entry),
            ]
        )

    # Kid-specific dashboard helper selects
    for kid_id in coordinator.kids_data.keys():
        selects.append(KidDashboardHelperChoresSelect(coordinator, entry, kid_id))

    async_add_entities(selects)


class KidsChoresSelectBase(KidsChoresCoordinatorEntity, SelectEntity):
    """Base class for the KidsChores select entities.

    Provides common select functionality for choosing chores, rewards, penalties,
    or bonuses from dropdown lists. Stores selected option and updates state.
    Used by both legacy system-wide selects and kid-specific dashboard helpers.
    """

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SELECT_BASE

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the base select entity.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access.
            entry: ConfigEntry for this integration instance.
        """
        super().__init__(coordinator)
        self._entry = entry
        self._selected_option: Optional[str] = None

    @property
    def current_option(self) -> Optional[str]:
        """Return the currently selected option (chore/reward/penalty name)."""
        return self._selected_option

    async def async_select_option(self, option: str) -> None:
        """When the user selects an option from the dropdown, store it.

        Args:
            option: The selected option name (chore/reward/penalty/bonus name).
        """
        self._selected_option = option
        self.async_write_ha_state()

    def select_option(self, option: str) -> None:
        """Select an option (synchronous wrapper for abstract method)."""
        # This method is required by the SelectEntity abstract class
        # but Home Assistant will call async_select_option instead
        self._selected_option = option


class SystemChoresSelect(KidsChoresSelectBase):
    """Global select entity listing all defined chores by name (legacy).

    NOTE: Legacy entity disabled by default. Provides system-wide chore selection
    for automations. Consider using kid-specific selects for better organization.
    """

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SELECT_CHORES

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the Chores select entity.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access.
            entry: ConfigEntry for this integration instance.
        """
        super().__init__(coordinator, entry)
        self._attr_unique_id = (
            f"{entry.entry_id}{const.SELECT_KC_UID_SUFFIX_CHORES_SELECT}"
        )
        self._attr_name = (
            f"{const.KIDSCHORES_TITLE}: {const.TRANS_KEY_SELECT_LABEL_ALL_CHORES}"
        )
        self.entity_id = (
            f"{const.SELECT_KC_PREFIX}{const.SELECT_KC_EID_SUFFIX_ALL_CHORES}"
        )
        self._attr_device_info = kh.create_system_device_info(entry)

    @property
    def options(self) -> list[str]:
        """Return a list of chore names from the coordinator."""
        return [
            chore_info.get(
                const.DATA_CHORE_NAME,
                f"{const.TRANS_KEY_LABEL_CHORE} {chore_id}",
            )
            for chore_id, chore_info in self.coordinator.chores_data.items()
        ]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            const.ATTR_PURPOSE: const.PURPOSE_SELECT_CHORES,
        }


class SystemRewardsSelect(KidsChoresSelectBase):
    """Global select entity listing all defined rewards by name (legacy).

    NOTE: Legacy entity disabled by default. Provides system-wide reward selection
    for automations. Consider using kid-specific reward buttons for better organization.
    """

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SELECT_REWARDS

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the Rewards select entity.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access.
            entry: ConfigEntry for this integration instance.
        """
        super().__init__(coordinator, entry)
        self._attr_unique_id = (
            f"{entry.entry_id}{const.SELECT_KC_UID_SUFFIX_REWARDS_SELECT}"
        )
        self._attr_name = (
            f"{const.KIDSCHORES_TITLE}: {const.TRANS_KEY_SELECT_LABEL_ALL_REWARDS}"
        )
        self.entity_id = (
            f"{const.SELECT_KC_PREFIX}{const.SELECT_KC_EID_SUFFIX_ALL_REWARDS}"
        )
        self._attr_device_info = kh.create_system_device_info(entry)

    @property
    def options(self) -> list[str]:
        """Return a list of reward names from the coordinator."""
        return [
            reward_info.get(
                const.DATA_REWARD_NAME,
                f"{const.TRANS_KEY_LABEL_REWARD} {reward_id}",
            )
            for reward_id, reward_info in self.coordinator.rewards_data.items()
        ]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            const.ATTR_PURPOSE: const.PURPOSE_SELECT_REWARDS,
        }


class SystemPenaltiesSelect(KidsChoresSelectBase):
    """Global select entity listing all defined penalties by name (legacy).

    NOTE: Legacy entity disabled by default. Provides system-wide penalty selection
    for automations. Consider using penalty buttons for better organization.
    """

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SELECT_PENALTIES

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the Penalties select entity.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access.
            entry: ConfigEntry for this integration instance.
        """
        super().__init__(coordinator, entry)
        self._attr_unique_id = (
            f"{entry.entry_id}{const.SELECT_KC_UID_SUFFIX_PENALTIES_SELECT}"
        )
        self._attr_name = (
            f"{const.KIDSCHORES_TITLE}: {const.TRANS_KEY_SELECT_LABEL_ALL_PENALTIES}"
        )
        self.entity_id = (
            f"{const.SELECT_KC_PREFIX}{const.SELECT_KC_EID_SUFFIX_ALL_PENALTIES}"
        )
        self._attr_device_info = kh.create_system_device_info(entry)

    @property
    def options(self) -> list[str]:
        """Return a list of penalty names from the coordinator."""
        return [
            penalty_info.get(
                const.DATA_PENALTY_NAME,
                f"{const.TRANS_KEY_LABEL_PENALTY} {penalty_id}",
            )
            for penalty_id, penalty_info in self.coordinator.penalties_data.items()
        ]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            const.ATTR_PURPOSE: const.PURPOSE_SELECT_PENALTIES,
        }


class SystemBonusesSelect(KidsChoresSelectBase):
    """Global select entity listing all defined bonuses by name (legacy).

    NOTE: Legacy entity disabled by default. Provides system-wide bonus selection
    for automations. Consider using bonus buttons for better organization.
    """

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SELECT_BONUSES

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the Bonuses select entity.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access.
            entry: ConfigEntry for this integration instance.
        """
        super().__init__(coordinator, entry)
        self._attr_unique_id = (
            f"{entry.entry_id}{const.SELECT_KC_UID_SUFFIX_BONUSES_SELECT}"
        )
        self._attr_name = (
            f"{const.KIDSCHORES_TITLE}: {const.TRANS_KEY_SELECT_LABEL_ALL_BONUSES}"
        )
        self.entity_id = (
            f"{const.SELECT_KC_PREFIX}{const.SELECT_KC_EID_SUFFIX_ALL_BONUSES}"
        )
        self._attr_device_info = kh.create_system_device_info(entry)

    @property
    def options(self) -> list[str]:
        """Return a list of bonus names from the coordinator."""
        return [
            bonus_info.get(
                const.DATA_BONUS_NAME,
                f"{const.TRANS_KEY_LABEL_BONUS} {bonus_id}",
            )
            for bonus_id, bonus_info in self.coordinator.bonuses_data.items()
        ]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            const.ATTR_PURPOSE: const.PURPOSE_SELECT_BONUSES,
        }


class KidDashboardHelperChoresSelect(KidsChoresSelectBase):
    """Select entity listing only the chores assigned to a specific kid (dashboard helper).

    Filters chore list to show only assignments for this kid. Used by dashboard
    automations to dynamically select kid-specific chores. Includes 'None' option
    for clearing selection.
    """

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SELECT_CHORES_KID

    def __init__(
        self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry, kid_id: str
    ):
        """Initialize the KidDashboardHelperChoresSelect.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access.
            entry: ConfigEntry for this integration instance.
            kid_id: Unique identifier for the kid to filter chores.
        """
        super().__init__(coordinator, entry)
        self._kid_id = kid_id
        kid_name = coordinator.kids_data.get(kid_id, {}).get(
            const.DATA_KID_NAME, f"{const.TRANS_KEY_LABEL_KID} {kid_id}"
        )
        self._attr_unique_id = (
            f"{entry.entry_id}{const.SELECT_KC_UID_MIDFIX_CHORES_SELECT}{kid_id}"
        )
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = (
            f"{const.SELECT_KC_PREFIX}{kid_name}{const.SELECT_KC_EID_SUFFIX_CHORE_LIST}"
        )
        self._attr_device_info = kh.create_kid_device_info(kid_id, kid_name, entry)

    @property
    def options(self) -> list[str]:
        """Return a list of chore names assigned to this kid, with a 'None' option.

        Filters coordinator.chores_data to include only chores where kid_id is in
        the assigned_kids list. Prepends 'None' option for clearing selection.
        """
        # Start with a "None" entry
        options = [const.SENTINEL_NONE_TEXT]
        for chore_id, chore_info in self.coordinator.chores_data.items():
            if self._kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                options.append(
                    chore_info.get(
                        const.DATA_CHORE_NAME,
                        f"{const.TRANS_KEY_LABEL_CHORE} {chore_id}",
                    )
                )
        return options

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        kid_name = kid_info.get(
            const.DATA_KID_NAME, f"{const.TRANS_KEY_LABEL_KID} {self._kid_id}"
        )
        return {
            const.ATTR_PURPOSE: const.TRANS_KEY_PURPOSE_SELECT_KID_CHORES,
            const.ATTR_KID_NAME: kid_name,
        }
