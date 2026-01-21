# File: select.py
"""Select entities for the KidsChores integration.

Allows the user to pick from all chores, all rewards, or all penalties
in a global manner. This is useful for automations or scripts where a
user wishes to select a chore/reward/penalty dynamically.
"""

from __future__ import annotations

from typing import Optional
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import const
from .coordinator import KidsChoresDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the KidsChores select entities from a config entry."""
    data = hass.data[const.DOMAIN][entry.entry_id]
    coordinator: KidsChoresDataCoordinator = data[const.COORDINATOR]

    # Create one global select entity for each category
    selects = [
        ChoresSelect(coordinator, entry),
        RewardsSelect(coordinator, entry),
        PenaltiesSelect(coordinator, entry),
        BonusesSelect(coordinator, entry),
    ]

    for kid_id in coordinator.kids_data.keys():
        selects.append(ChoresKidSelect(coordinator, entry, kid_id))

    async_add_entities(selects)


class KidsChoresSelectBase(CoordinatorEntity, SelectEntity):
    """Base class for the KidsChores select entities."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SELECT_BASE

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the base select entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._selected_option: Optional[str] = None

    @property
    def current_option(self) -> Optional[str]:
        """Return the currently selected option (chore/reward/penalty name)."""
        return self._selected_option

    async def async_select_option(self, option: str) -> None:
        """When the user selects an option from the dropdown, store it."""
        self._selected_option = option
        self.async_write_ha_state()


class ChoresSelect(KidsChoresSelectBase):
    """Global select entity listing all defined chores by name."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SELECT_CHORES

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the Chores select entity."""
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


class RewardsSelect(KidsChoresSelectBase):
    """Global select entity listing all defined rewards by name."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SELECT_REWARDS

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the Rewards select entity."""
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


class PenaltiesSelect(KidsChoresSelectBase):
    """Global select entity listing all defined penalties by name."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SELECT_PENALTIES

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the Penalties select entity."""
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


class BonusesSelect(KidsChoresSelectBase):
    """Global select entity listing all defined bonuses by name."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SELECT_BONUSES

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the Bonuses select entity."""
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


class ChoresKidSelect(KidsChoresSelectBase):
    """Select entity listing only the chores assigned to a specific kid."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SELECT_CHORES_KID

    def __init__(
        self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry, kid_id: str
    ):
        """Initialize the ChoresKidSelect."""
        super().__init__(coordinator, entry)
        self._kid_id = kid_id
        kid_name = coordinator.kids_data.get(kid_id, {}).get(
            const.DATA_KID_NAME, f"{const.TRANS_KEY_LABEL_KID} {kid_id}"
        )
        self._attr_unique_id = (
            f"{entry.entry_id}{const.SELECT_KC_UID_MIDFIX_CHORES_SELECT}{kid_id}"
        )
        self._attr_name = f"{const.KIDSCHORES_TITLE}: {const.TRANS_KEY_SELECT_LABEL_CHORES_FOR} {kid_name}"
        self.entity_id = (
            f"{const.SELECT_KC_PREFIX}{kid_name}{const.SELECT_KC_EID_SUFFIX_CHORE_LIST}"
        )

    @property
    def options(self) -> list[str]:
        """Return a list of chore names assigned to this kid, with a 'None' option."""
        # Start with a "None" entry
        options = [const.CONF_NONE_TEXT]
        for chore_id, chore_info in self.coordinator.chores_data.items():
            if self._kid_id in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                options.append(
                    chore_info.get(
                        const.DATA_CHORE_NAME,
                        f"{const.TRANS_KEY_LABEL_CHORE} {chore_id}",
                    )
                )
        return options
