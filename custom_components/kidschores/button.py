# File: button.py
"""Buttons for KidsChores integration.

Features:
1) Chore Buttons (Claim & Approve) with user-defined or default icons.
2) Reward Buttons using user-defined or default icons.
3) Penalty Buttons using user-defined or default icons.
4) Bonus Buttons using user-defined or default icons.
5) PointsAdjustButton: manually increments/decrements a kid's points (e.g., +1, -1, +2, -2, etc.).
6) ApproveRewardButton: allows parents to approve rewards claimed by kids.

"""

from homeassistant.auth.models import User
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.exceptions import HomeAssistantError

from .const import (
    ATTR_LABELS,
    BUTTON_BONUS_PREFIX,
    BUTTON_DISAPPROVE_CHORE_PREFIX,
    BUTTON_DISAPPROVE_REWARD_PREFIX,
    BUTTON_PENALTY_PREFIX,
    BUTTON_REWARD_PREFIX,
    CONF_POINTS_LABEL,
    DATA_PENDING_CHORE_APPROVALS,
    DATA_PENDING_REWARD_APPROVALS,
    DEFAULT_BONUS_ICON,
    DEFAULT_CHORE_APPROVE_ICON,
    DEFAULT_CHORE_CLAIM_ICON,
    DEFAULT_DISAPPROVE_ICON,
    DEFAULT_PENALTY_ICON,
    DEFAULT_POINTS_ADJUST_MINUS_ICON,
    DEFAULT_POINTS_ADJUST_MINUS_MULTIPLE_ICON,
    DEFAULT_POINTS_ADJUST_PLUS_ICON,
    DEFAULT_POINTS_ADJUST_PLUS_MULTIPLE_ICON,
    DEFAULT_POINTS_LABEL,
    DEFAULT_REWARD_ICON,
    DOMAIN,
    ERROR_NOT_AUTHORIZED_ACTION_FMT,
    LOGGER,
)
from .coordinator import KidsChoresDataCoordinator
from .kc_helpers import (
    is_user_authorized_for_global_action,
    is_user_authorized_for_kid,
    get_friendly_label,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up dynamic buttons.

    - Chores (Claim & Approve & Disapprove)
    - Rewards (Redeem & Approve & Disapprove)
    - Penalties
    - Kid points adjustments (e.g., +1, -1, +10, -10, etc.)
    - Approve Reward Workflow

    """
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: KidsChoresDataCoordinator = data["coordinator"]

    points_label = entry.options.get(CONF_POINTS_LABEL, DEFAULT_POINTS_LABEL)

    entities = []

    # Create buttons for chores (Claim, Approve & Disapprove)
    for chore_id, chore_info in coordinator.chores_data.items():
        chore_name = chore_info.get("name", f"Chore {chore_id}")
        assigned_kids_ids = chore_info.get("assigned_kids", [])

        # If user defined an icon, use it; else fallback to default for chore claim
        chore_claim_icon = chore_info.get("icon", DEFAULT_CHORE_CLAIM_ICON)
        # For "approve," use a distinct icon
        chore_approve_icon = chore_info.get("icon", DEFAULT_CHORE_APPROVE_ICON)

        for kid_id in assigned_kids_ids:
            kid_name = coordinator._get_kid_name_by_id(kid_id) or f"Kid {kid_id}"
            # Claim Button
            entities.append(
                ClaimChoreButton(
                    coordinator=coordinator,
                    entry=entry,
                    kid_id=kid_id,
                    kid_name=kid_name,
                    chore_id=chore_id,
                    chore_name=chore_name,
                    icon=chore_claim_icon,
                )
            )
            # Approve Button
            entities.append(
                ApproveChoreButton(
                    coordinator=coordinator,
                    entry=entry,
                    kid_id=kid_id,
                    kid_name=kid_name,
                    chore_id=chore_id,
                    chore_name=chore_name,
                    icon=chore_approve_icon,
                )
            )
            # Disapprove Button
            entities.append(
                DisapproveChoreButton(
                    coordinator=coordinator,
                    entry=entry,
                    kid_id=kid_id,
                    kid_name=kid_name,
                    chore_id=chore_id,
                    chore_name=chore_name,
                )
            )

    # Create reward buttons (Redeem, Approve & Disapprove)
    for kid_id, kid_info in coordinator.kids_data.items():
        kid_name = kid_info.get("name", f"Kid {kid_id}")
        for reward_id, reward_info in coordinator.rewards_data.items():
            # If no user-defined icon, fallback to DEFAULT_REWARD_ICON
            reward_icon = reward_info.get("icon", DEFAULT_REWARD_ICON)
            # Redeem Reward Button
            entities.append(
                RewardButton(
                    coordinator=coordinator,
                    entry=entry,
                    kid_id=kid_id,
                    kid_name=kid_name,
                    reward_id=reward_id,
                    reward_name=reward_info.get("name", f"Reward {reward_id}"),
                    icon=reward_icon,
                )
            )
            # Approve Reward Button
            entities.append(
                ApproveRewardButton(
                    coordinator=coordinator,
                    entry=entry,
                    kid_id=kid_id,
                    kid_name=kid_name,
                    reward_id=reward_id,
                    reward_name=reward_info.get("name", f"Reward {reward_id}"),
                    icon=reward_info.get("icon", DEFAULT_REWARD_ICON),
                )
            )
            # Disapprove Reward Button
            entities.append(
                DisapproveRewardButton(
                    coordinator=coordinator,
                    entry=entry,
                    kid_id=kid_id,
                    kid_name=kid_name,
                    reward_id=reward_id,
                    reward_name=reward_info.get("name", f"Reward {reward_id}"),
                )
            )

    # Create penalty buttons
    for kid_id, kid_info in coordinator.kids_data.items():
        kid_name = kid_info.get("name", f"Kid {kid_id}")
        for penalty_id, penalty_info in coordinator.penalties_data.items():
            # If no user-defined icon, fallback to DEFAULT_PENALTY_ICON
            penalty_icon = penalty_info.get("icon", DEFAULT_PENALTY_ICON)
            entities.append(
                PenaltyButton(
                    coordinator=coordinator,
                    entry=entry,
                    kid_id=kid_id,
                    kid_name=kid_name,
                    penalty_id=penalty_id,
                    penalty_name=penalty_info.get("name", f"Penalty {penalty_id}"),
                    icon=penalty_icon,
                )
            )

    # Create bonus buttons
    for kid_id, kid_info in coordinator.kids_data.items():
        kid_name = kid_info.get("name", f"Kid {kid_id}")
        for bonus_id, bonus_info in coordinator.bonuses_data.items():
            # If no user-defined icon, fallback to DEFAULT_BONUS_ICON
            bonus_icon = bonus_info.get("icon", DEFAULT_BONUS_ICON)
            entities.append(
                BonusButton(
                    coordinator=coordinator,
                    entry=entry,
                    kid_id=kid_id,
                    kid_name=kid_name,
                    bonus_id=bonus_id,
                    bonus_name=bonus_info.get("name", f"Bonus {bonus_id}"),
                    icon=bonus_icon,
                )
            )

    # Create "points adjustment" buttons for each kid (±1, ±2, ±10, etc.)
    POINT_DELTAS = [+1, -1, +2, -2, +10, -10]
    for kid_id, kid_info in coordinator.kids_data.items():
        kid_name = kid_info.get("name", f"Kid {kid_id}")
        for delta in POINT_DELTAS:
            entities.append(
                PointsAdjustButton(
                    coordinator=coordinator,
                    entry=entry,
                    kid_id=kid_id,
                    kid_name=kid_name,
                    delta=delta,
                    points_label=points_label,
                )
            )

    async_add_entities(entities)


# ------------------ Chore Buttons ------------------
class ClaimChoreButton(CoordinatorEntity, ButtonEntity):
    """Button to claim a chore as done (set chore state=claimed)."""

    _attr_has_entity_name = True
    _attr_translation_key = "claim_chore_button"

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        chore_id: str,
        chore_name: str,
        icon: str,
    ):
        """Initialize the claim chore button."""

        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._chore_id = chore_id
        self._chore_name = chore_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{chore_id}_claim"
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "chore_name": chore_name,
        }
        self.entity_id = f"button.kc_{kid_name}_chore_claim_{chore_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await is_user_authorized_for_kid(
                self.hass, user_id, self._kid_id
            ):
                raise HomeAssistantError(
                    ERROR_NOT_AUTHORIZED_ACTION_FMT.format("claim chores")
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            user_name = user_obj.name if user_obj else "Unknown"

            self.coordinator.claim_chore(
                kid_id=self._kid_id,
                chore_id=self._chore_id,
                user_name=user_name,
            )
            LOGGER.info(
                "Chore '%s' claimed by kid '%s' (user: %s)",
                self._chore_name,
                self._kid_name,
                user_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            LOGGER.error(
                "Authorization failed to claim chore '%s' for kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            LOGGER.error(
                "Failed to claim chore '%s' for kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        stored_labels = chore_info.get("chore_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            ATTR_LABELS: friendly_labels,
        }

        return attributes


class ApproveChoreButton(CoordinatorEntity, ButtonEntity):
    """Button to approve a claimed chore for a kid (set chore state=approved or partial)."""

    _attr_has_entity_name = True
    _attr_translation_key = "approve_chore_button"

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        chore_id: str,
        chore_name: str,
        icon: str,
    ):
        """Initialize the approve chore button."""

        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._chore_id = chore_id
        self._chore_name = chore_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{chore_id}_approve"
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "chore_name": chore_name,
        }
        self.entity_id = f"button.kc_{kid_name}_chore_approval_{chore_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await is_user_authorized_for_global_action(
                self.hass, user_id, "approve_chore"
            ):
                raise HomeAssistantError(
                    ERROR_NOT_AUTHORIZED_ACTION_FMT.format("approve chores")
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else "ParentOrAdmin"

            self.coordinator.approve_chore(
                parent_name=parent_name,
                kid_id=self._kid_id,
                chore_id=self._chore_id,
            )
            LOGGER.info(
                "Chore '%s' approved for kid '%s'",
                self._chore_name,
                self._kid_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            LOGGER.error(
                "Authorization failed to approve chore '%s' for kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            LOGGER.error(
                "Failed to approve chore '%s' for kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        stored_labels = chore_info.get("chore_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            ATTR_LABELS: friendly_labels,
        }

        return attributes


class DisapproveChoreButton(CoordinatorEntity, ButtonEntity):
    """Button to disapprove a chore."""

    _attr_has_entity_name = True
    _attr_translation_key = "disapprove_chore_button"

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        chore_id: str,
        chore_name: str,
        icon: str = DEFAULT_DISAPPROVE_ICON,
    ):
        """Initialize the disapprove chore button."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._chore_id = chore_id
        self._chore_name = chore_name
        self._attr_unique_id = (
            f"{entry.entry_id}_{BUTTON_DISAPPROVE_CHORE_PREFIX}{kid_id}_{chore_id}"
        )
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "chore_name": chore_name,
        }
        self.entity_id = f"button.kc_{kid_name}_chore_disapproval_{chore_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            # Check if there's a pending approval for this kid and chore.
            pending_approvals = self.coordinator._data.get(
                DATA_PENDING_CHORE_APPROVALS, []
            )
            if not any(
                approval["kid_id"] == self._kid_id
                and approval["chore_id"] == self._chore_id
                for approval in pending_approvals
            ):
                raise HomeAssistantError(
                    f"No pending approval found for chore '{self._chore_name}' for kid '{self._kid_name}'."
                )

            user_id = self._context.user_id if self._context else None
            if user_id and not await is_user_authorized_for_global_action(
                self.hass, user_id, "disapprove_chore"
            ):
                raise HomeAssistantError(
                    ERROR_NOT_AUTHORIZED_ACTION_FMT.format("disapprove chores")
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else "ParentOrAdmin"

            self.coordinator.disapprove_chore(
                parent_name=parent_name,
                kid_id=self._kid_id,
                chore_id=self._chore_id,
            )
            LOGGER.info(
                "Chore '%s' disapproved for kid '%s' by parent '%s'",
                self._chore_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            LOGGER.error(
                "Authorization failed to disapprove chore '%s' for kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            LOGGER.error(
                "Failed to disapprove chore '%s' for kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        stored_labels = chore_info.get("chore_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            ATTR_LABELS: friendly_labels,
        }

        return attributes


# ------------------ Reward Buttons ------------------
class RewardButton(CoordinatorEntity, ButtonEntity):
    """Button to redeem a reward for a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = "claim_reward_button"

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        reward_id: str,
        reward_name: str,
        icon: str,
    ):
        """Initialize the reward button."""
        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._reward_id = reward_id
        self._reward_name = reward_name
        self._attr_unique_id = (
            f"{entry.entry_id}_{BUTTON_REWARD_PREFIX}{kid_id}_{reward_id}"
        )
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "reward_name": reward_name,
        }
        self.entity_id = f"button.kc_{kid_name}_reward_claim_{reward_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await is_user_authorized_for_kid(
                self.hass, user_id, self._kid_id
            ):
                raise HomeAssistantError(
                    ERROR_NOT_AUTHORIZED_ACTION_FMT.format("redeem rewards")
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else "Unknown"

            self.coordinator.redeem_reward(
                parent_name=parent_name,
                kid_id=self._kid_id,
                reward_id=self._reward_id,
            )
            LOGGER.info(
                "Reward '%s' redeemed for kid '%s' by parent '%s'",
                self._reward_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            LOGGER.error(
                "Authorization failed to redeem reward '%s' for kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            LOGGER.error(
                "Failed to redeem reward '%s' for kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        stored_labels = reward_info.get("reward_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            ATTR_LABELS: friendly_labels,
        }

        return attributes


class ApproveRewardButton(CoordinatorEntity, ButtonEntity):
    """Button for parents to approve a reward claimed by a kid.

    Prevents unauthorized or premature reward approvals.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "approve_reward_button"

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        reward_id: str,
        reward_name: str,
        icon: str,
    ):
        """Initialize the approve reward button."""

        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._reward_id = reward_id
        self._reward_name = reward_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{reward_id}_approve_reward"
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "reward_name": reward_name,
        }
        self.entity_id = f"button.kc_{kid_name}_reward_approval_{reward_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await is_user_authorized_for_global_action(
                self.hass, user_id, "approve_reward"
            ):
                raise HomeAssistantError(
                    ERROR_NOT_AUTHORIZED_ACTION_FMT.format("approve rewards")
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else "ParentOrAdmin"

            # Approve the reward
            self.coordinator.approve_reward(
                parent_name=parent_name,
                kid_id=self._kid_id,
                reward_id=self._reward_id,
            )

            LOGGER.info(
                "Reward '%s' approved for kid '%s' by parent '%s'",
                self._reward_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            LOGGER.error(
                "Authorization failed to approve reward '%s' for kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )
            # Send a persistent notification for the error
            if user_id:
                self.hass.components.persistent_notification.create(
                    f"Failed to approve reward '{self._reward_name}' for {self._kid_name}: {e}",
                    title="Reward Approval Failed",
                    notification_id=f"approve_reward_error_{self._reward_id}",
                )
        except Exception as e:
            LOGGER.error(
                "Failed to approve reward '%s' for kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )
            # Send a persistent notification for the unexpected error
            if user_id:
                self.hass.components.persistent_notification.create(
                    f"An unexpected error occurred while approving reward '{self._reward_name}' for {self._kid_name}",
                    title="Reward Approval Error",
                    notification_id=f"approve_reward_unexpected_error_{self._reward_id}",
                )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        stored_labels = reward_info.get("reward_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            ATTR_LABELS: friendly_labels,
        }

        return attributes


class DisapproveRewardButton(CoordinatorEntity, ButtonEntity):
    """Button to disapprove a reward."""

    _attr_has_entity_name = True
    _attr_translation_key = "disapprove_reward_button"

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        reward_id: str,
        reward_name: str,
        icon: str = DEFAULT_DISAPPROVE_ICON,
    ):
        """Initialize the disapprove reward button."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._reward_id = reward_id
        self._reward_name = reward_name
        self._attr_unique_id = (
            f"{entry.entry_id}_{BUTTON_DISAPPROVE_REWARD_PREFIX}{kid_id}_{reward_id}"
        )
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "reward_name": reward_name,
        }
        self.entity_id = f"button.kc_{kid_name}_reward_disapproval_{reward_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            # Check if there's a pending approval for this kid and reward.
            pending_approvals = self.coordinator._data.get(
                DATA_PENDING_REWARD_APPROVALS, []
            )
            if not any(
                approval["kid_id"] == self._kid_id
                and approval["reward_id"] == self._reward_id
                for approval in pending_approvals
            ):
                raise HomeAssistantError(
                    f"No pending approval found for reward '{self._reward_name}' for kid '{self._kid_name}'."
                )

            user_id = self._context.user_id if self._context else None
            if user_id and not await is_user_authorized_for_global_action(
                self.hass, user_id, "disapprove_reward"
            ):
                raise HomeAssistantError(
                    ERROR_NOT_AUTHORIZED_ACTION_FMT.format("disapprove rewards")
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else "ParentOrAdmin"

            self.coordinator.disapprove_reward(
                parent_name=parent_name,
                kid_id=self._kid_id,
                reward_id=self._reward_id,
            )
            LOGGER.info(
                "Reward '%s' disapproved for kid '%s' by parent '%s'",
                self._reward_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            LOGGER.error(
                "Authorization failed to disapprove reward '%s' for kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            LOGGER.error(
                "Failed to disapprove reward '%s' for kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        stored_labels = reward_info.get("reward_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            ATTR_LABELS: friendly_labels,
        }

        return attributes


# ------------------ Penalty Button ------------------
class PenaltyButton(CoordinatorEntity, ButtonEntity):
    """Button to apply a penalty for a kid.

    Uses user-defined or default penalty icon.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "penalty_button"

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        penalty_id: str,
        penalty_name: str,
        icon: str,
    ):
        """Initialize the penalty button."""

        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._penalty_id = penalty_id
        self._penalty_name = penalty_name
        self._attr_unique_id = (
            f"{entry.entry_id}_{BUTTON_PENALTY_PREFIX}{kid_id}_{penalty_id}"
        )
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "penalty_name": penalty_name,
        }
        self.entity_id = f"button.kc_{kid_name}_penalty_{penalty_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await is_user_authorized_for_global_action(
                self.hass, user_id, "apply_penalty"
            ):
                raise HomeAssistantError(
                    ERROR_NOT_AUTHORIZED_ACTION_FMT.format("apply penalties")
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else "Unknown"

            self.coordinator.apply_penalty(
                parent_name=parent_name,
                kid_id=self._kid_id,
                penalty_id=self._penalty_id,
            )
            LOGGER.info(
                "Penalty '%s' applied to kid '%s' by '%s'",
                self._penalty_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            LOGGER.error(
                "Authorization failed to apply penalty '%s' for kid '%s': %s",
                self._penalty_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            LOGGER.error(
                "Failed to apply penalty '%s' for kid '%s': %s",
                self._penalty_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        penalty_info = self.coordinator.penalties_data.get(self._penalty_id, {})
        stored_labels = penalty_info.get("penalty_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            ATTR_LABELS: friendly_labels,
        }

        return attributes


# ------------------ Points Adjust Button ------------------
class PointsAdjustButton(CoordinatorEntity, ButtonEntity):
    """Button that increments or decrements a kid's points by 'delta'.

    For example: +1, -1, +10, -10, etc.
    Uses icons from const.py for plus/minus, or fallback if desired.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "manual_adjustment_button"

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        delta: int,
        points_label: str,
    ):
        """Initialize the points adjust buttons."""

        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._delta = delta
        self._points_label = str(points_label)

        sign_label = f"+{delta}" if delta >= 0 else f"-{delta}"
        sign_text = f"plus_{delta}" if delta >= 0 else f"minus_{delta}"
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_adjust_points_{delta}"
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "sign_label": sign_label,
            "points_label": points_label,
        }
        self.entity_id = f"button.kc_{kid_name}_{sign_text}_points"

        # Decide the icon based on whether delta is positive or negative
        if delta >= 2:
            self._attr_icon = DEFAULT_POINTS_ADJUST_PLUS_MULTIPLE_ICON
        elif delta > 0:
            self._attr_icon = DEFAULT_POINTS_ADJUST_PLUS_ICON
        elif delta <= -2:
            self._attr_icon = DEFAULT_POINTS_ADJUST_MINUS_MULTIPLE_ICON
        elif delta < 0:
            self._attr_icon = DEFAULT_POINTS_ADJUST_MINUS_ICON
        else:
            self._attr_icon = DEFAULT_POINTS_ADJUST_PLUS_ICON

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await is_user_authorized_for_global_action(
                self.hass, user_id, "adjust_points"
            ):
                raise HomeAssistantError(
                    ERROR_NOT_AUTHORIZED_ACTION_FMT.format("adjust points")
                )

            current_points = self.coordinator.kids_data[self._kid_id]["points"]
            new_points = current_points + self._delta
            self.coordinator.update_kid_points(
                kid_id=self._kid_id,
                new_points=new_points,
            )
            LOGGER.info(
                "Adjusted points for kid '%s' by %d => total %d",
                self._kid_name,
                self._delta,
                new_points,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            LOGGER.error(
                "Authorization failed to adjust points for kid '%s' by %d: %s",
                self._kid_name,
                self._delta,
                e,
            )
        except Exception as e:
            LOGGER.error(
                "Failed to adjust points for kid '%s' by %d: %s",
                self._kid_name,
                self._delta,
                e,
            )


class BonusButton(CoordinatorEntity, ButtonEntity):
    """Button to apply a bonus for a kid.

    Uses user-defined or default bonus icon.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "bonus_button"

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        bonus_id: str,
        bonus_name: str,
        icon: str,
    ):
        """Initialize the bonus button."""
        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._bonus_id = bonus_id
        self._bonus_name = bonus_name
        self._attr_unique_id = (
            f"{entry.entry_id}_{BUTTON_BONUS_PREFIX}{kid_id}_{bonus_id}"
        )
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "bonus_name": bonus_name,
        }
        self.entity_id = f"button.kc_{kid_name}_bonus_{bonus_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await is_user_authorized_for_global_action(
                self.hass, user_id, "apply_bonus"
            ):
                raise HomeAssistantError(
                    ERROR_NOT_AUTHORIZED_ACTION_FMT.format("apply bonus")
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else "Unknown"

            self.coordinator.apply_bonus(
                parent_name=parent_name,
                kid_id=self._kid_id,
                bonus_id=self._bonus_id,
            )
            LOGGER.info(
                "Bonus '%s' applied to kid '%s' by '%s'",
                self._bonus_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            LOGGER.error(
                "Authorization failed to apply bonus '%s' for kid '%s': %s",
                self._bonus_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            LOGGER.error(
                "Failed to apply bonus '%s' for kid '%s': %s",
                self._bonus_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        bonus_info = self.coordinator.bonuses_data.get(self._bonus_id, {})
        stored_labels = bonus_info.get("bonus_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            ATTR_LABELS: friendly_labels,
        }

        return attributes
