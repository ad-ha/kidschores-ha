# File: button.py
"""Buttons for KidsChores integration.

Features:
1) Chore Buttons (Claim & Approve) with user-defined or default icons.
2) Reward Buttons using user-defined or default icons.
3) Penalty Buttons using user-defined or default icons.
4) Bonus Buttons using user-defined or default icons.
5) PointsAdjustButton: manually increments/decrements a kid's points.
6) ApproveRewardButton: allows parents to approve rewards claimed by kids.

"""

from homeassistant.auth.models import User
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.exceptions import HomeAssistantError

from . import const
from .coordinator import KidsChoresDataCoordinator
from . import kc_helpers as kh


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up dynamic buttons."""
    data = hass.data[const.DOMAIN][entry.entry_id]
    coordinator: KidsChoresDataCoordinator = data[const.COORDINATOR]

    points_label = entry.options.get(
        const.CONF_POINTS_LABEL, const.DEFAULT_POINTS_LABEL
    )

    entities = []

    # Create buttons for chores (Claim, Approve & Disapprove)
    for chore_id, chore_info in coordinator.chores_data.items():
        chore_name = chore_info.get(
            const.DATA_CHORE_NAME, f"{const.TRANS_KEY_LABEL_CHORE} {chore_id}"
        )
        assigned_kids_ids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])

        # If user defined an icon, use it; else fallback to default for chore claim
        chore_claim_icon = chore_info.get(
            const.DATA_CHORE_ICON, const.DEFAULT_CHORE_CLAIM_ICON
        )
        # For "approve," use a distinct icon
        chore_approve_icon = chore_info.get(
            const.DATA_CHORE_ICON, const.DEFAULT_CHORE_APPROVE_ICON
        )

        for kid_id in assigned_kids_ids:
            kid_name = (
                kh.get_kid_name_by_id(coordinator, kid_id)
                or f"{const.TRANS_KEY_LABEL_KID} {kid_id}"
            )
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
        kid_name = kid_info.get(
            const.DATA_KID_NAME, f"{const.TRANS_KEY_LABEL_KID} {kid_id}"
        )
        for reward_id, reward_info in coordinator.rewards_data.items():
            # If no user-defined icon, fallback to const.DEFAULT_REWARD_ICON
            reward_icon = reward_info.get(
                const.DATA_REWARD_ICON, const.DEFAULT_REWARD_ICON
            )
            # Redeem Reward Button
            entities.append(
                RewardButton(
                    coordinator=coordinator,
                    entry=entry,
                    kid_id=kid_id,
                    kid_name=kid_name,
                    reward_id=reward_id,
                    reward_name=reward_info.get(
                        const.DATA_REWARD_NAME,
                        f"{const.TRANS_KEY_LABEL_REWARD} {reward_id}",
                    ),
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
                    reward_name=reward_info.get(
                        const.DATA_REWARD_NAME,
                        f"{const.TRANS_KEY_LABEL_REWARD} {reward_id}",
                    ),
                    icon=reward_info.get(
                        const.DATA_REWARD_ICON, const.DEFAULT_REWARD_ICON
                    ),
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
                    reward_name=reward_info.get(
                        const.DATA_REWARD_NAME,
                        f"{const.TRANS_KEY_LABEL_REWARD} {reward_id}",
                    ),
                )
            )

    # Create penalty buttons
    for kid_id, kid_info in coordinator.kids_data.items():
        kid_name = kid_info.get(
            const.DATA_KID_NAME, f"{const.TRANS_KEY_LABEL_KID} {kid_id}"
        )
        for penalty_id, penalty_info in coordinator.penalties_data.items():
            # If no user-defined icon, fallback to const.DEFAULT_PENALTY_ICON
            penalty_icon = penalty_info.get(
                const.DATA_PENALTY_ICON, const.DEFAULT_PENALTY_ICON
            )
            entities.append(
                PenaltyButton(
                    coordinator=coordinator,
                    entry=entry,
                    kid_id=kid_id,
                    kid_name=kid_name,
                    penalty_id=penalty_id,
                    penalty_name=penalty_info.get(
                        const.DATA_PENALTY_NAME,
                        f"{const.TRANS_KEY_LABEL_PENALTY} {penalty_id}",
                    ),
                    icon=penalty_icon,
                )
            )

    # Create bonus buttons
    for kid_id, kid_info in coordinator.kids_data.items():
        kid_name = kid_info.get(
            const.DATA_KID_NAME, f"{const.TRANS_KEY_LABEL_KID} {kid_id}"
        )
        for bonus_id, bonus_info in coordinator.bonuses_data.items():
            # If no user-defined icon, fallback to const.DEFAULT_BONUS_ICON
            bonus_icon = bonus_info.get(const.DATA_BONUS_ICON, const.DEFAULT_BONUS_ICON)
            entities.append(
                BonusButton(
                    coordinator=coordinator,
                    entry=entry,
                    kid_id=kid_id,
                    kid_name=kid_name,
                    bonus_id=bonus_id,
                    bonus_name=bonus_info.get(
                        const.DATA_BONUS_NAME,
                        f"{const.TRANS_KEY_LABEL_BONUS} {bonus_id}",
                    ),
                    icon=bonus_icon,
                )
            )

    # Create "points adjustment" buttons for each kid (±1, ±2, ±10, etc.)
    raw_values = coordinator.config_entry.options.get(const.CONF_POINTS_ADJUST_VALUES)
    if not raw_values:
        points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES
        const.LOGGER.debug(
            "Using default points_adjust_values: %s", points_adjust_values
        )
    elif isinstance(raw_values, str):
        points_adjust_values = kh.parse_points_adjust_values(raw_values)
        if not points_adjust_values:
            points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES
            const.LOGGER.warning(
                "Parsed points_adjust_values empty; falling back to default"
            )
        else:
            const.LOGGER.debug(
                "Parsed points_adjust_values from string: %s", points_adjust_values
            )
    elif isinstance(raw_values, list):
        try:
            points_adjust_values = [float(v) for v in raw_values]
        except (ValueError, TypeError):
            points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES
            const.LOGGER.error("Error converting raw_values to floats; using default")
    else:
        points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES

    # Create a points adjust button for each kid and each delta value
    for kid_id, kid_info in coordinator.kids_data.items():
        kid_name = kid_info.get(
            const.DATA_KID_NAME, f"{const.TRANS_KEY_LABEL_KID} {kid_id}"
        )
        for delta in points_adjust_values:
            const.LOGGER.debug(
                "Creating PointsAdjustButton for kid %s with delta %s", kid_name, delta
            )
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
    _attr_translation_key = const.TRANS_KEY_BUTTON_CLAIM_CHORE_BUTTON

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
        self._attr_unique_id = (
            f"{entry.entry_id}_{kid_id}_{chore_id}{const.BUTTON_KC_UID_SUFFIX_CLAIM}"
        )
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            const.TRANS_KEY_BUTTON_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_BUTTON_ATTR_CHORE_NAME: chore_name,
        }
        self.entity_id = f"{const.BUTTON_KC_PREFIX}{kid_name}{const.BUTTON_KC_EID_MIDFIX_CHORE_CLAIM}{chore_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_kid(
                self.hass, user_id, self._kid_id
            ):
                raise HomeAssistantError(
                    const.ERROR_NOT_AUTHORIZED_ACTION_FMT.format(
                        const.TRANS_KEY_FMT_ERROR_CLAIM_CHORES
                    )
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            user_name = user_obj.name if user_obj else const.CONF_UNKNOWN

            self.coordinator.claim_chore(
                kid_id=self._kid_id,
                chore_id=self._chore_id,
                user_name=user_name,
            )
            const.LOGGER.info(
                "Chore '%s' claimed by kid '%s' (user: %s)",
                self._chore_name,
                self._kid_name,
                user_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "Authorization failed to claim chore '%s' for kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            const.LOGGER.error(
                "Failed to claim chore '%s' for kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        stored_labels = chore_info.get(const.DATA_CHORE_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


class ApproveChoreButton(CoordinatorEntity, ButtonEntity):
    """Button to approve a claimed chore for a kid (set chore state=approved or partial)."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_BUTTON_APPROVE_CHORE_BUTTON

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
        self._attr_unique_id = (
            f"{entry.entry_id}_{kid_id}_{chore_id}{const.BUTTON_KC_UID_SUFFIX_APPROVE}"
        )
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            const.TRANS_KEY_BUTTON_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_BUTTON_ATTR_CHORE_NAME: chore_name,
        }
        self.entity_id = f"{const.BUTTON_KC_PREFIX}{kid_name}{const.BUTTON_KC_EID_MIDFIX_CHORE_APPROVAL}{chore_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_global_action(
                self.hass, user_id, const.SERVICE_APPROVE_CHORE
            ):
                raise HomeAssistantError(
                    const.ERROR_NOT_AUTHORIZED_ACTION_FMT.format(
                        const.TRANS_KEY_FMT_ERROR_APPROVE_CHORES
                    )
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else const.CONF_UNKNOWN

            self.coordinator.approve_chore(
                parent_name=parent_name,
                kid_id=self._kid_id,
                chore_id=self._chore_id,
            )
            const.LOGGER.info(
                "Chore '%s' approved for kid '%s'",
                self._chore_name,
                self._kid_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "Authorization failed to approve chore '%s' for kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            const.LOGGER.error(
                "Failed to approve chore '%s' for kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        stored_labels = chore_info.get(const.DATA_CHORE_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


class DisapproveChoreButton(CoordinatorEntity, ButtonEntity):
    """Button to disapprove a chore."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_BUTTON_DISAPPROVE_CHORE_BUTTON

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        chore_id: str,
        chore_name: str,
        icon: str = const.DEFAULT_DISAPPROVE_ICON,
    ):
        """Initialize the disapprove chore button."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._chore_id = chore_id
        self._chore_name = chore_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{chore_id}{const.BUTTON_KC_UID_SUFFIX_DISAPPROVE}"
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            const.TRANS_KEY_BUTTON_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_BUTTON_ATTR_CHORE_NAME: chore_name,
        }
        self.entity_id = f"{const.BUTTON_KC_PREFIX}{kid_name}{const.BUTTON_KC_EID_MIDFIX_CHORE_DISAPPROVAL}{chore_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            # Check if there's a pending approval for this kid and chore.
            pending_approvals = self.coordinator._data.get(
                const.DATA_PENDING_CHORE_APPROVALS, []
            )
            if not any(
                approval[const.DATA_KID_ID] == self._kid_id
                and approval[const.DATA_CHORE_ID] == self._chore_id
                for approval in pending_approvals
            ):
                raise HomeAssistantError(
                    f"No pending approval found for chore '{self._chore_name}' for kid '{self._kid_name}'."
                )

            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_global_action(
                self.hass, user_id, const.SERVICE_DISAPPROVE_CHORE
            ):
                raise HomeAssistantError(
                    const.ERROR_NOT_AUTHORIZED_ACTION_FMT.format(
                        const.TRANS_KEY_FMT_ERROR_DISAPPROVE_CHORES
                    )
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else const.CONF_UNKNOWN

            self.coordinator.disapprove_chore(
                parent_name=parent_name,
                kid_id=self._kid_id,
                chore_id=self._chore_id,
            )
            const.LOGGER.info(
                "Chore '%s' disapproved for kid '%s' by parent '%s'",
                self._chore_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "Authorization failed to disapprove chore '%s' for kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            const.LOGGER.error(
                "Failed to disapprove chore '%s' for kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        stored_labels = chore_info.get(const.DATA_CHORE_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


# ------------------ Reward Buttons ------------------
class RewardButton(CoordinatorEntity, ButtonEntity):
    """Button to redeem a reward for a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_BUTTON_CLAIM_REWARD_BUTTON

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
            f"{entry.entry_id}_{const.BUTTON_REWARD_PREFIX}{kid_id}_{reward_id}"
        )
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            const.TRANS_KEY_BUTTON_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_BUTTON_ATTR_REWARD_NAME: reward_name,
        }
        self.entity_id = f"{const.BUTTON_KC_PREFIX}{kid_name}{const.BUTTON_KC_EID_MIDFIX_REWARD_CLAIM}{reward_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_kid(
                self.hass, user_id, self._kid_id
            ):
                raise HomeAssistantError(
                    const.ERROR_NOT_AUTHORIZED_ACTION_FMT.format(
                        const.TRANS_KEY_FMT_ERROR_REDEEM_REWARDS
                    )
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else const.CONF_UNKNOWN

            self.coordinator.redeem_reward(
                parent_name=parent_name,
                kid_id=self._kid_id,
                reward_id=self._reward_id,
            )
            const.LOGGER.info(
                "Reward '%s' redeemed for kid '%s' by parent '%s'",
                self._reward_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "Authorization failed to redeem reward '%s' for kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            const.LOGGER.error(
                "Failed to redeem reward '%s' for kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        stored_labels = reward_info.get(const.DATA_REWARD_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


class ApproveRewardButton(CoordinatorEntity, ButtonEntity):
    """Button for parents to approve a reward claimed by a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_BUTTON_APPROVE_REWARD_BUTTON

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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{reward_id}{const.BUTTON_KC_UID_SUFFIX_APPROVE_REWARD}"
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            const.TRANS_KEY_BUTTON_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_BUTTON_ATTR_REWARD_NAME: reward_name,
        }
        self.entity_id = f"{const.BUTTON_KC_PREFIX}{kid_name}{const.BUTTON_KC_EID_MIDFIX_REWARD_APPROVAL}{reward_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_global_action(
                self.hass, user_id, const.SERVICE_APPROVE_REWARD
            ):
                raise HomeAssistantError(
                    const.ERROR_NOT_AUTHORIZED_ACTION_FMT.format(
                        const.TRANS_KEY_FMT_ERROR_APPROVE_REWARDS
                    )
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else const.CONF_UNKNOWN

            # Approve the reward
            self.coordinator.approve_reward(
                parent_name=parent_name,
                kid_id=self._kid_id,
                reward_id=self._reward_id,
            )

            const.LOGGER.info(
                "Reward '%s' approved for kid '%s' by parent '%s'",
                self._reward_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "Authorization failed to approve reward '%s' for kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            const.LOGGER.error(
                "Failed to approve reward '%s' for kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        stored_labels = reward_info.get(const.DATA_REWARD_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


class DisapproveRewardButton(CoordinatorEntity, ButtonEntity):
    """Button to disapprove a reward."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_BUTTON_DISAPPROVE_REWARD_BUTTON

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        reward_id: str,
        reward_name: str,
        icon: str = const.DEFAULT_DISAPPROVE_ICON,
    ):
        """Initialize the disapprove reward button."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._reward_id = reward_id
        self._reward_name = reward_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{reward_id}{const.BUTTON_KC_UID_SUFFIX_DISAPPROVE_REWARD}"
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            const.TRANS_KEY_BUTTON_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_BUTTON_ATTR_REWARD_NAME: reward_name,
        }
        self.entity_id = f"{const.BUTTON_KC_PREFIX}{kid_name}{const.BUTTON_KC_EID_MIDFIX_REWARD_DISAPPROVAL}{reward_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            # Check if there's a pending approval for this kid and reward.
            pending_approvals = self.coordinator._data.get(
                const.DATA_PENDING_REWARD_APPROVALS, []
            )
            if not any(
                approval[const.DATA_KID_ID] == self._kid_id
                and approval[const.DATA_REWARD_ID] == self._reward_id
                for approval in pending_approvals
            ):
                raise HomeAssistantError(
                    f"No pending approval found for reward '{self._reward_name}' for kid '{self._kid_name}'."
                )

            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_global_action(
                self.hass, user_id, const.SERVICE_DISAPPROVE_REWARD
            ):
                raise HomeAssistantError(
                    const.ERROR_NOT_AUTHORIZED_ACTION_FMT.format(
                        const.TRANS_KEY_FMT_ERROR_DISAPPROVE_REWARDS
                    )
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else const.CONF_UNKNOWN

            self.coordinator.disapprove_reward(
                parent_name=parent_name,
                kid_id=self._kid_id,
                reward_id=self._reward_id,
            )
            const.LOGGER.info(
                "Reward '%s' disapproved for kid '%s' by parent '%s'",
                self._reward_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "Authorization failed to disapprove reward '%s' for kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            const.LOGGER.error(
                "Failed to disapprove reward '%s' for kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        stored_labels = reward_info.get(const.DATA_REWARD_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


# ------------------ Penalty Button ------------------
class PenaltyButton(CoordinatorEntity, ButtonEntity):
    """Button to apply a penalty for a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_BUTTON_PENALTY_BUTTON

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
            f"{entry.entry_id}_{const.BUTTON_PENALTY_PREFIX}{kid_id}_{penalty_id}"
        )
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            const.TRANS_KEY_BUTTON_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_BUTTON_ATTR_PENALTY_NAME: penalty_name,
        }
        self.entity_id = f"{const.BUTTON_KC_PREFIX}{kid_name}{const.BUTTON_KC_EID_MIDFIX_PENALTY}{penalty_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_global_action(
                self.hass, user_id, const.SERVICE_APPLY_PENALTY
            ):
                raise HomeAssistantError(
                    const.ERROR_NOT_AUTHORIZED_ACTION_FMT.format(
                        const.TRANS_KEY_FMT_ERROR_APPLY_PENALTIES
                    )
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else const.CONF_UNKNOWN

            self.coordinator.apply_penalty(
                parent_name=parent_name,
                kid_id=self._kid_id,
                penalty_id=self._penalty_id,
            )
            const.LOGGER.info(
                "Penalty '%s' applied to kid '%s' by '%s'",
                self._penalty_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "Authorization failed to apply penalty '%s' for kid '%s': %s",
                self._penalty_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            const.LOGGER.error(
                "Failed to apply penalty '%s' for kid '%s': %s",
                self._penalty_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        penalty_info = self.coordinator.penalties_data.get(self._penalty_id, {})
        stored_labels = penalty_info.get(const.DATA_PENALTY_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


# ------------------ Points Adjust Button ------------------
class PointsAdjustButton(CoordinatorEntity, ButtonEntity):
    """Button that increments or decrements a kid's points by 'delta'."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_BUTTON_MANUAL_ADJUSTMENT_BUTTON

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

        sign_label = (
            f"{const.TRANS_KEY_BUTTON_DELTA_PLUS_LABEL}{delta}"
            if delta >= 0
            else f"{delta}"
        )
        sign_text = (
            f"{const.TRANS_KEY_BUTTON_DELTA_PLUS_TEXT}{delta}"
            if delta >= 0
            else f"{const.TRANS_KEY_BUTTON_DELTA_MINUS_TEXT}{delta}"
        )
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}{const.BUTTON_KC_UID_MIDFIX_ADJUST_POINTS}{delta}"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_BUTTON_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_BUTTON_ATTR_SIGN_LABEL: sign_label,
            const.TRANS_KEY_BUTTON_ATTR_POINTS_LABEL: points_label,
        }
        self.entity_id = f"{const.BUTTON_KC_PREFIX}{kid_name}_{sign_text}{const.BUTTON_KC_EID_SUFFIX_POINTS}"

        # Decide the icon based on whether delta is positive or negative
        if delta >= 2:
            self._attr_icon = const.DEFAULT_POINTS_ADJUST_PLUS_MULTIPLE_ICON
        elif delta > 0:
            self._attr_icon = const.DEFAULT_POINTS_ADJUST_PLUS_ICON
        elif delta <= -2:
            self._attr_icon = const.DEFAULT_POINTS_ADJUST_MINUS_MULTIPLE_ICON
        elif delta < 0:
            self._attr_icon = const.DEFAULT_POINTS_ADJUST_MINUS_ICON
        else:
            self._attr_icon = const.DEFAULT_POINTS_ADJUST_PLUS_ICON

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_global_action(
                self.hass, user_id, const.SERVICE_ADJUST_POINTS
            ):
                raise HomeAssistantError(
                    const.ERROR_NOT_AUTHORIZED_ACTION_FMT.format(
                        const.TRANS_KEY_FMT_ERROR_ADJUST_POINTS
                    )
                )

            current_points = self.coordinator.kids_data[self._kid_id][
                const.DATA_KID_POINTS
            ]
            new_points = current_points + self._delta
            self.coordinator.update_kid_points(
                kid_id=self._kid_id,
                new_points=new_points,
            )
            const.LOGGER.info(
                "Adjusted points for kid '%s' by %d => total %d",
                self._kid_name,
                self._delta,
                new_points,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "Authorization failed to adjust points for kid '%s' by %d: %s",
                self._kid_name,
                self._delta,
                e,
            )
        except Exception as e:
            const.LOGGER.error(
                "Failed to adjust points for kid '%s' by %d: %s",
                self._kid_name,
                self._delta,
                e,
            )


class BonusButton(CoordinatorEntity, ButtonEntity):
    """Button to apply a bonus for a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_BUTTON_BONUS_BUTTON

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
            f"{entry.entry_id}_{const.BUTTON_BONUS_PREFIX}{kid_id}_{bonus_id}"
        )
        self._attr_icon = icon
        self._attr_translation_placeholders = {
            const.TRANS_KEY_BUTTON_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_BUTTON_ATTR_BONUS_NAME: bonus_name,
        }
        self.entity_id = f"{const.BUTTON_KC_PREFIX}{kid_name}{const.BUTTON_KC_EID_MIDFIX_BONUS}{bonus_name}"

    async def async_press(self):
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_global_action(
                self.hass, user_id, const.SERVICE_APPLY_BONUS
            ):
                raise HomeAssistantError(
                    const.ERROR_NOT_AUTHORIZED_ACTION_FMT.format(
                        const.TRANS_KEY_FMT_ERROR_APPLY_BONUS
                    )
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = user_obj.name if user_obj else const.CONF_UNKNOWN

            self.coordinator.apply_bonus(
                parent_name=parent_name,
                kid_id=self._kid_id,
                bonus_id=self._bonus_id,
            )
            const.LOGGER.info(
                "Bonus '%s' applied to kid '%s' by '%s'",
                self._bonus_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "Authorization failed to apply bonus '%s' for kid '%s': %s",
                self._bonus_name,
                self._kid_name,
                e,
            )
        except Exception as e:
            const.LOGGER.error(
                "Failed to apply bonus '%s' for kid '%s': %s",
                self._bonus_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self):
        """Include extra state attributes for the button."""
        bonus_info = self.coordinator.bonuses_data.get(self._bonus_id, {})
        stored_labels = bonus_info.get(const.DATA_BONUS_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes
