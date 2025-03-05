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

from .const import DOMAIN, LOGGER
from .coordinator import KidsChoresDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the KidsChores select entities from a config entry.

    Creates three global selects:
      1) ChoresSelect: lists all chore names
      2) RewardsSelect: lists all reward names
      3) PenaltiesSelect: lists all penalty names

    """
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: KidsChoresDataCoordinator = data["coordinator"]

    # Create one global select entity for each category
    selects = [
        ChoresSelect(coordinator, entry),
        RewardsSelect(coordinator, entry),
        PenaltiesSelect(coordinator, entry),
    ]

    for kid_id in coordinator.kids_data.keys():
        selects.append(ChoresKidSelect(coordinator, entry, kid_id))

    async_add_entities(selects)


class KidsChoresSelectBase(CoordinatorEntity, SelectEntity):
    """Base class for the KidsChores select entities."""

    _attr_has_entity_name = True
    _attr_translation_key = "kc_select_base"

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the base select entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._selected_option: Optional[str] = None

    @property
    def current_option(self) -> Optional[str]:
        """Return the currently selected option (chore/reward/penalty name).

        None if nothing has been selected.
        """
        return self._selected_option

    async def async_select_option(self, option: str) -> None:
        """When the user selects an option from the dropdown, store it.

        By default, no further action is taken.
        """
        self._selected_option = option
        LOGGER.debug(
            "%s: User selected option '%s'",
            self._attr_name,
            option,
        )
        self.async_write_ha_state()


class ChoresSelect(KidsChoresSelectBase):
    """Global select entity listing all defined chores by name."""

    _attr_has_entity_name = True
    _attr_translation_key = "chores_select"

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the Chores select entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_chores_select"
        self._attr_name = "KidsChores: All Chores"
        self.entity_id = f"select.kc_all_chores"

    @property
    def options(self) -> list[str]:
        """Return a list of chore names from the coordinator.

        If no chores exist, returns an empty list.
        """
        return [
            chore_info.get("name", f"Chore {chore_id}")
            for chore_id, chore_info in self.coordinator.chores_data.items()
        ]


class RewardsSelect(KidsChoresSelectBase):
    """Global select entity listing all defined rewards by name."""

    _attr_has_entity_name = True
    _attr_translation_key = "rewards_select"

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the Rewards select entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_rewards_select"
        self._attr_name = "KidsChores: All Rewards"
        self.entity_id = f"select.kc_all_rewards"

    @property
    def options(self) -> list[str]:
        """Return a list of reward names from the coordinator.

        If no rewards exist, returns an empty list.
        """
        return [
            reward_info.get("name", f"Reward {reward_id}")
            for reward_id, reward_info in self.coordinator.rewards_data.items()
        ]


class PenaltiesSelect(KidsChoresSelectBase):
    """Global select entity listing all defined penalties by name."""

    _attr_has_entity_name = True
    _attr_translation_key = "penalties_select"

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the Penalties select entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_penalties_select"
        self._attr_name = "KidsChores: All Penalties"
        self.entity_id = f"select.kc_all_penalties"

    @property
    def options(self) -> list[str]:
        """Return a list of penalty names from the coordinator.

        If no penalties exist, returns an empty list.
        """
        return [
            penalty_info.get("name", f"Penalty {penalty_id}")
            for penalty_id, penalty_info in self.coordinator.penalties_data.items()
        ]


class ChoresKidSelect(KidsChoresSelectBase):
    """Select entity listing only the chores assigned to a specific kid."""

    _attr_has_entity_name = True
    _attr_translation_key = "chores_kid_select"

    def __init__(
        self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry, kid_id: str
    ):
        """Initialize the ChoresKidSelect."""
        super().__init__(coordinator, entry)
        self._kid_id = kid_id
        kid_name = coordinator.kids_data.get(kid_id, {}).get("name", f"Kid {kid_id}")
        self._attr_unique_id = f"{entry.entry_id}_chores_select_{kid_id}"
        self._attr_name = f"KidsChores: Chores for {kid_name}"
        self.entity_id = f"select.kc_{kid_name}_chore_list"

    @property
    def options(self) -> list[str]:
        """Return a list of chore names assigned to this kid, with a 'None' option."""
        # Start with a "None" entry
        options = ["None"]
        for chore_id, chore in self.coordinator.chores_data.items():
            if self._kid_id in chore.get("assigned_kids", []):
                options.append(chore.get("name", f"Chore {chore_id}"))
        return options


class BonusesSelect(KidsChoresSelectBase):
    """Global select entity listing all defined bonuses by name."""

    _attr_has_entity_name = True
    _attr_translation_key = "bonuses_select"

    def __init__(self, coordinator: KidsChoresDataCoordinator, entry: ConfigEntry):
        """Initialize the Bonuses select entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_bonuses_select"
        self._attr_name = "KidsChores: All Bonuses"
        self.entity_id = f"select.kc_all_bonuses"

    @property
    def options(self) -> list[str]:
        """Return a list of bonus names from the coordinator.

        If no bonuses exist, returns an empty list.
        """
        return [
            bonus_info.get("name", f"Bonus {bonus_id}")
            for bonus_id, bonus_info in self.coordinator.bonuses_data.items()
        ]
