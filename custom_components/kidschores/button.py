# File: button.py
# pyright: reportIncompatibleVariableOverride=false
# ^ Suppresses Pylance warnings about @property overriding @cached_property from base classes.
#   This is intentional: our entities compute dynamic values on each access,
#   so we use @property instead of @cached_property to avoid stale cached data.
"""Buttons for KidsChores integration.

Features:
1) Chore Buttons (Claim & Approve) with user-defined or default icons.
2) Reward Buttons using user-defined or default icons.
3) Penalty Buttons using user-defined or default icons.
4) Bonus Buttons using user-defined or default icons.
5) ParentPointsAdjustButton: manually increments/decrements a kid's points.
6) ParentRewardApproveButton: allows parents to approve rewards claimed by kids.

"""

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import const
from . import kc_helpers as kh
from .coordinator import KidsChoresDataCoordinator
from .entity import KidsChoresCoordinatorEntity

# Silver requirement: Parallel Updates
# Set to 1 (serialized) for action buttons that modify state
PARALLEL_UPDATES = 1


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
                KidChoreClaimButton(
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
                ParentChoreApproveButton(
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
                ParentChoreDisapproveButton(
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
                KidRewardRedeemButton(
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
                ParentRewardApproveButton(
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
                ParentRewardDisapproveButton(
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
                ParentPenaltyApplyButton(
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
                ParentBonusApplyButton(
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
    # IMPORTANT: Always normalize to floats for consistent entity unique IDs
    # (restored data may have integers, options flow saves as floats)
    raw_values = coordinator.config_entry.options.get(const.CONF_POINTS_ADJUST_VALUES)
    if not raw_values:
        points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES
        const.LOGGER.debug(
            "DEBUG: Button - PointsAdjustValue - Using default points adjust values: %s",
            points_adjust_values,
        )
    elif isinstance(raw_values, str):
        points_adjust_values = kh.parse_points_adjust_values(raw_values)
        if not points_adjust_values:
            points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES
            const.LOGGER.warning(
                "WARNING: Parsed points adjust values empty. Falling back to defaults"
            )
        else:
            const.LOGGER.debug(
                "DEBUG: Parsed points adjust values from string: %s",
                points_adjust_values,
            )
    elif isinstance(raw_values, list):
        try:
            # Always convert to floats for consistent unique IDs
            points_adjust_values = [float(v) for v in raw_values]
        except (ValueError, TypeError):
            points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES
            const.LOGGER.error(
                "ERROR: Failed converting RAW values to floats. Falling back to defaults"
            )
    else:
        points_adjust_values = const.DEFAULT_POINTS_ADJUST_VALUES

    # Create a points adjust button for each kid and each delta value
    for kid_id, kid_info in coordinator.kids_data.items():
        kid_name = kid_info.get(
            const.DATA_KID_NAME, f"{const.TRANS_KEY_LABEL_KID} {kid_id}"
        )
        for delta in points_adjust_values:
            const.LOGGER.debug(
                "DEBUG: Creating ParentPointsAdjustButton for Kid '%s' with delta %s",
                kid_name,
                delta,
            )
            entities.append(
                ParentPointsAdjustButton(
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
class KidChoreClaimButton(KidsChoresCoordinatorEntity, ButtonEntity):
    """Button to claim a chore as done (set chore state=claimed).

    Allows kids to mark chores as completed. Validates user authorization
    against kid ID, calls coordinator.claim_chore(), and triggers refresh.
    """

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
        """Initialize the claim chore button.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access and updates.
            entry: ConfigEntry for this integration instance.
            kid_id: Unique identifier for the kid.
            kid_name: Display name of the kid.
            chore_id: Unique identifier for the chore.
            chore_name: Display name of the chore.
            icon: Icon override from chore configuration or default.
        """

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
        self._attr_device_info = kh.create_kid_device_info(kid_id, kid_name, entry)

    def press(self) -> None:
        """Synchronous press - not used, Home Assistant calls async_press."""

    async def async_press(self) -> None:
        """Handle the button press event."""
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_kid(
                self.hass, user_id, self._kid_id
            ):
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION,
                    translation_placeholders={
                        "action": const.ERROR_ACTION_CLAIM_CHORES
                    },
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            user_name = (user_obj.name if user_obj else None) or const.DISPLAY_UNKNOWN

            self.coordinator.claim_chore(
                kid_id=self._kid_id,
                chore_id=self._chore_id,
                user_name=user_name,
            )
            const.LOGGER.info(
                "INFO: Chore '%s' claimed by Kid '%s' (User: %s)",
                self._chore_name,
                self._kid_name,
                user_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "ERROR: Authorization failed to Claim Chore '%s' for Kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )
        except (KeyError, ValueError, AttributeError) as e:
            const.LOGGER.error(
                "ERROR: Failed to Claim Chore '%s' for Kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Include extra state attributes for the button."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        stored_labels = chore_info.get(const.DATA_CHORE_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes: dict[str, Any] = {
            const.ATTR_PURPOSE: const.TRANS_KEY_PURPOSE_BUTTON_CHORE_CLAIM,
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_CHORE_NAME: self._chore_name,
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


class ParentChoreApproveButton(KidsChoresCoordinatorEntity, ButtonEntity):
    """Button to approve a claimed chore for a kid (set chore state=approved or partial).

    Parent-only button that approves claimed chores, awards points, triggers badge
    calculations, and handles multi-kid shared chore logic (partial vs full approval).
    Validates global parent authorization before execution.
    """

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
        """Initialize the approve chore button.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access and updates.
            entry: ConfigEntry for this integration instance.
            kid_id: Unique identifier for the kid.
            kid_name: Display name of the kid.
            chore_id: Unique identifier for the chore.
            chore_name: Display name of the chore.
            icon: Icon override from chore configuration or default approval icon.
        """

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
        self._attr_device_info = kh.create_kid_device_info(kid_id, kid_name, entry)

    def press(self) -> None:
        """Synchronous press - not used, Home Assistant calls async_press."""

    async def async_press(self) -> None:
        """Handle the button press event.

        Validates global parent authorization, retrieves parent name from context,
        calls coordinator.approve_chore() to award points and update state, triggers
        badge calculations and notifications, and refreshes all dependent entities.

        Raises:
            HomeAssistantError: If user not authorized for global parent actions.
        """
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_global_action(
                self.hass, user_id, const.SERVICE_APPROVE_CHORE
            ):
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL,
                    translation_placeholders={
                        "action": const.ERROR_ACTION_APPROVE_CHORES
                    },
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = (user_obj.name if user_obj else None) or const.DISPLAY_UNKNOWN

            self.coordinator.approve_chore(
                parent_name=parent_name,
                kid_id=self._kid_id,
                chore_id=self._chore_id,
            )
            const.LOGGER.info(
                "INFO: Chore '%s' approved for Kid '%s'",
                self._chore_name,
                self._kid_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "ERROR: Authorization failed to Approve Chore '%s' for Kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )
        except (KeyError, ValueError, AttributeError) as e:
            const.LOGGER.error(
                "ERROR: Failed to approve Chore '%s' for Kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Include extra state attributes for the button."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        stored_labels = chore_info.get(const.DATA_CHORE_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes: dict[str, Any] = {
            const.ATTR_PURPOSE: const.TRANS_KEY_PURPOSE_BUTTON_CHORE_APPROVE,
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_CHORE_NAME: self._chore_name,
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


class ParentChoreDisapproveButton(KidsChoresCoordinatorEntity, ButtonEntity):
    """Button to disapprove a chore.

    Parent-only button that rejects pending chore approvals, removes from approval queue,
    and resets chore state to available. Validates pending approval exists before execution.
    """

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
        """Initialize the disapprove chore button.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access and updates.
            entry: ConfigEntry for this integration instance.
            kid_id: Unique identifier for the kid.
            kid_name: Display name of the kid.
            chore_id: Unique identifier for the chore.
            chore_name: Display name of the chore.
            icon: Icon override, defaults to disapprove icon.
        """

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
        self._attr_device_info = kh.create_kid_device_info(kid_id, kid_name, entry)

    def press(self) -> None:
        """Synchronous press - not used, Home Assistant calls async_press."""

    async def async_press(self) -> None:
        """Handle the button press event.

        Validates pending approval exists for this kid/chore combination, checks
        global parent authorization, retrieves parent name from context, calls
        coordinator.disapprove_chore() to remove from approval queue and reset state.

        Raises:
            HomeAssistantError: If no pending approval found or user not authorized.
        """
        try:
            # Check if there's a pending approval for this kid and chore.
            pending_approvals = self.coordinator.pending_chore_approvals
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
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL,
                    translation_placeholders={
                        "action": const.ERROR_ACTION_DISAPPROVE_CHORES
                    },
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = (user_obj.name if user_obj else None) or const.DISPLAY_UNKNOWN

            self.coordinator.disapprove_chore(
                parent_name=parent_name,
                kid_id=self._kid_id,
                chore_id=self._chore_id,
            )
            const.LOGGER.info(
                "INFO: Chore '%s' disapproved for Kid '%s' by parent '%s'",
                self._chore_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "ERROR: Authorization failed to Disapprove Chore '%s' for Kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )
        except (KeyError, ValueError, AttributeError) as e:
            const.LOGGER.error(
                "ERROR: Failed to Disapprove Chore '%s' for Kid '%s': %s",
                self._chore_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Include extra state attributes for the button."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        stored_labels = chore_info.get(const.DATA_CHORE_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes: dict[str, Any] = {
            const.ATTR_PURPOSE: const.TRANS_KEY_PURPOSE_BUTTON_CHORE_DISAPPROVE,
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_CHORE_NAME: self._chore_name,
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


# ------------------ Reward Buttons ------------------
class KidRewardRedeemButton(KidsChoresCoordinatorEntity, ButtonEntity):
    """Button to redeem a reward for a kid.

    Allows kids to spend points on rewards. Validates user authorization against kid ID,
    checks sufficient points balance, deducts points, creates pending reward approval,
    and triggers coordinator refresh.
    """

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
        """Initialize the reward button.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access and updates.
            entry: ConfigEntry for this integration instance.
            kid_id: Unique identifier for the kid.
            kid_name: Display name of the kid.
            reward_id: Unique identifier for the reward.
            reward_name: Display name of the reward.
            icon: Icon override from reward configuration or default.
        """
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
        self._attr_device_info = kh.create_kid_device_info(kid_id, kid_name, entry)

    def press(self) -> None:
        """Synchronous press - not used, Home Assistant calls async_press."""

    async def async_press(self) -> None:
        """Handle the button press event.

        Validates user authorization for kid, retrieves user name from context,
        calls coordinator.redeem_reward() to deduct points and create pending approval,
        and triggers coordinator refresh to update all dependent entities.

        Raises:
            HomeAssistantError: If user not authorized or insufficient points balance.
        """
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_kid(
                self.hass, user_id, self._kid_id
            ):
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION,
                    translation_placeholders={
                        "action": const.ERROR_ACTION_REDEEM_REWARDS
                    },
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = (user_obj.name if user_obj else None) or const.DISPLAY_UNKNOWN

            self.coordinator.redeem_reward(
                parent_name=parent_name,
                kid_id=self._kid_id,
                reward_id=self._reward_id,
            )
            const.LOGGER.info(
                "INFO: Reward '%s' redeemed for Kid '%s' by Parent '%s'",
                self._reward_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "ERROR: Authorization failed to Redeem Reward '%s' for Kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )
        except (KeyError, ValueError, AttributeError) as e:
            const.LOGGER.error(
                "ERROR: Failed to Redeem Reward '%s' for Kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Include extra state attributes for the button."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        stored_labels = reward_info.get(const.DATA_REWARD_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes: dict[str, Any] = {
            const.ATTR_PURPOSE: const.TRANS_KEY_PURPOSE_BUTTON_REWARD_REDEEM,
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_REWARD_NAME: self._reward_name,
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


class ParentRewardApproveButton(KidsChoresCoordinatorEntity, ButtonEntity):
    """Button for parents to approve a reward claimed by a kid.

    Parent-only button that confirms reward redemption, removes from pending approval
    queue, and triggers notifications. Validates global parent authorization before execution.
    """

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
        """Initialize the approve reward button.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access and updates.
            entry: ConfigEntry for this integration instance.
            kid_id: Unique identifier for the kid.
            kid_name: Display name of the kid.
            reward_id: Unique identifier for the reward.
            reward_name: Display name of the reward.
            icon: Icon override from reward configuration or default.
        """

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
        self._attr_device_info = kh.create_kid_device_info(kid_id, kid_name, entry)

    def press(self) -> None:
        """Synchronous press - not used, Home Assistant calls async_press."""

    async def async_press(self) -> None:
        """Handle the button press event.

        Validates global parent authorization, retrieves parent name from context,
        calls coordinator.approve_reward() to confirm redemption and remove from pending
        queue, triggers notifications, and refreshes all dependent entities.

        Raises:
            HomeAssistantError: If user not authorized for global parent actions.
        """
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_global_action(
                self.hass, user_id, const.SERVICE_APPROVE_REWARD
            ):
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL,
                    translation_placeholders={
                        "action": const.ERROR_ACTION_APPROVE_REWARDS
                    },
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = (user_obj.name if user_obj else None) or const.DISPLAY_UNKNOWN

            # Approve the reward
            self.coordinator.approve_reward(
                parent_name=parent_name,
                kid_id=self._kid_id,
                reward_id=self._reward_id,
            )

            const.LOGGER.info(
                "INFO: Reward '%s' approved for Kid '%s' by Parent '%s'",
                self._reward_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "ERROR: Authorization failed to Approve Reward '%s' for Kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )
        except (KeyError, ValueError, AttributeError) as e:
            const.LOGGER.error(
                "ERROR: Failed to Approve Reward '%s' for Kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Include extra state attributes for the button."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        stored_labels = reward_info.get(const.DATA_REWARD_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes: dict[str, Any] = {
            const.ATTR_PURPOSE: const.TRANS_KEY_PURPOSE_BUTTON_REWARD_APPROVE,
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_REWARD_NAME: self._reward_name,
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


class ParentRewardDisapproveButton(KidsChoresCoordinatorEntity, ButtonEntity):
    """Button to disapprove a reward.

    Parent-only button that rejects pending reward redemptions, refunds points to kid,
    and removes from approval queue. Validates pending approval exists before execution.
    """

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
        """Initialize the disapprove reward button.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access and updates.
            entry: ConfigEntry for this integration instance.
            kid_id: Unique identifier for the kid.
            kid_name: Display name of the kid.
            reward_id: Unique identifier for the reward.
            reward_name: Display name of the reward.
            icon: Icon override, defaults to disapprove icon.
        """

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
        self._attr_device_info = kh.create_kid_device_info(kid_id, kid_name, entry)

    def press(self) -> None:
        """Synchronous press - not used, Home Assistant calls async_press."""

    async def async_press(self) -> None:
        """Handle the button press event.

        Validates pending approval exists for this kid/reward combination, checks
        global parent authorization, retrieves parent name from context, calls
        coordinator.disapprove_reward() to refund points and remove from approval queue.

        Raises:
            HomeAssistantError: If no pending approval found or user not authorized.
        """
        try:
            # Check if there's a pending approval for this kid and reward.
            pending_approvals = self.coordinator.pending_reward_approvals
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
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL,
                    translation_placeholders={
                        "action": const.ERROR_ACTION_DISAPPROVE_REWARDS
                    },
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = (user_obj.name if user_obj else None) or const.DISPLAY_UNKNOWN

            self.coordinator.disapprove_reward(
                parent_name=parent_name,
                kid_id=self._kid_id,
                reward_id=self._reward_id,
            )
            const.LOGGER.info(
                "INFO: Reward '%s' disapproved for Kid '%s' by Parent '%s'",
                self._reward_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "ERROR: Authorization failed to Disapprove Reward '%s' for Kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )
        except (KeyError, ValueError, AttributeError) as e:
            const.LOGGER.error(
                "ERROR: Failed to Disapprove Reward '%s' for Kid '%s': %s",
                self._reward_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Include extra state attributes for the button."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        stored_labels = reward_info.get(const.DATA_REWARD_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes: dict[str, Any] = {
            const.ATTR_PURPOSE: const.TRANS_KEY_PURPOSE_BUTTON_REWARD_DISAPPROVE,
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_REWARD_NAME: self._reward_name,
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


# ------------------ Penalty Button ------------------
class ParentPenaltyApplyButton(KidsChoresCoordinatorEntity, ButtonEntity):
    """Button to apply a penalty for a kid.

    Parent-only button that deducts points from kid's balance based on penalty
    configuration. Validates global parent authorization before execution.
    """

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
        """Initialize the penalty button.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access and updates.
            entry: ConfigEntry for this integration instance.
            kid_id: Unique identifier for the kid.
            kid_name: Display name of the kid.
            penalty_id: Unique identifier for the penalty.
            penalty_name: Display name of the penalty.
            icon: Icon override from penalty configuration or default.
        """

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
        self._attr_device_info = kh.create_kid_device_info(kid_id, kid_name, entry)

    def press(self) -> None:
        """Synchronous press - not used, Home Assistant calls async_press."""

    async def async_press(self) -> None:
        """Handle the button press event.

        Validates global parent authorization, retrieves parent name from context,
        calls coordinator.apply_penalty() to deduct points from kid's balance based
        on penalty configuration, and triggers coordinator refresh.

        Raises:
            HomeAssistantError: If user not authorized for global parent actions.
        """
        try:
            const.LOGGER.debug(
                "DEBUG: ParentPenaltyApplyButton.async_press called for kid=%s, penalty=%s",
                self._kid_id,
                self._penalty_id,
            )
            user_id = self._context.user_id if self._context else None
            const.LOGGER.debug("Context user_id=%s", user_id)

            if user_id and not await kh.is_user_authorized_for_global_action(
                self.hass, user_id, const.SERVICE_APPLY_PENALTY
            ):
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL,
                    translation_placeholders={
                        "action": const.ERROR_ACTION_APPLY_PENALTIES
                    },
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = (user_obj.name if user_obj else None) or const.DISPLAY_UNKNOWN
            const.LOGGER.debug("About to call coordinator.apply_penalty")

            self.coordinator.apply_penalty(
                parent_name=parent_name,
                kid_id=self._kid_id,
                penalty_id=self._penalty_id,
            )
            const.LOGGER.debug("coordinator.apply_penalty completed")
            const.LOGGER.info(
                "INFO: Penalty '%s' applied to Kid '%s' by Parent '%s'",
                self._penalty_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "ERROR: Authorization failed to Apply Penalty '%s' for Kid '%s': %s",
                self._penalty_name,
                self._kid_name,
                e,
            )
        except (KeyError, ValueError, AttributeError) as e:
            const.LOGGER.error(
                "ERROR: Failed to Apply Penalty '%s' for Kid '%s': %s",
                self._penalty_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Include extra state attributes for the button."""
        penalty_info = self.coordinator.penalties_data.get(self._penalty_id, {})
        stored_labels = penalty_info.get(const.DATA_PENALTY_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes: dict[str, Any] = {
            const.ATTR_PURPOSE: const.TRANS_KEY_PURPOSE_BUTTON_PENALTY_APPLY,
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_PENALTY_NAME: self._penalty_name,
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes


# ------------------ Points Adjust Button ------------------
class ParentPointsAdjustButton(KidsChoresCoordinatorEntity, ButtonEntity):
    """Button that increments or decrements a kid's points by 'delta'.

    Parent-only button for manual points adjustments. Creates multiple button instances
    per kid based on configured delta values (e.g., +1, +10, -2). Validates global
    parent authorization before execution.
    """

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_BUTTON_MANUAL_ADJUSTMENT_BUTTON

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        delta: int | float,
        points_label: str,
    ):
        """Initialize the points adjust buttons.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access and updates.
            entry: ConfigEntry for this integration instance.
            kid_id: Unique identifier for the kid.
            kid_name: Display name of the kid.
            delta: Points adjustment value (positive for increment, negative for decrement).
            points_label: User-configured label for points (e.g., "Points", "Stars").
        """

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
        self.entity_id = f"{const.BUTTON_KC_PREFIX}{kid_name}{const.BUTTON_KC_EID_SUFFIX_POINTS}_{sign_text}"
        self._attr_device_info = kh.create_kid_device_info(kid_id, kid_name, entry)

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

    def press(self) -> None:
        """Synchronous press - not used, Home Assistant calls async_press."""

    async def async_press(self) -> None:
        """Handle the button press event.

        Validates global parent authorization, calls coordinator.update_kid_points()
        with delta value and manual source, logs adjustment, and triggers coordinator
        refresh to update points balance and all dependent entities.

        Raises:
            HomeAssistantError: If user not authorized for global parent actions.
        """
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_global_action(
                self.hass, user_id, const.SERVICE_ADJUST_POINTS
            ):
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL,
                    translation_placeholders={
                        "action": const.ERROR_ACTION_ADJUST_POINTS
                    },
                )

            self.coordinator.update_kid_points(
                kid_id=self._kid_id,
                delta=self._delta,
                source=const.POINTS_SOURCE_MANUAL,
            )
            const.LOGGER.info(
                "INFO: Adjusted points for Kid '%s' by %d.",
                self._kid_name,
                self._delta,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "ERROR: Authorization failed to adjust points for Kid '%s' by %d: %s",
                self._kid_name,
                self._delta,
                e,
            )
        except (KeyError, ValueError, AttributeError) as e:
            const.LOGGER.error(
                "ERROR: Failed to adjust points for Kid '%s' by %d: %s",
                self._kid_name,
                self._delta,
                e,
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            const.ATTR_PURPOSE: const.TRANS_KEY_PURPOSE_BUTTON_POINTS_ADJUST,
            const.ATTR_KID_NAME: self._kid_name,
        }


class ParentBonusApplyButton(KidsChoresCoordinatorEntity, ButtonEntity):
    """Button to apply a bonus for a kid.

    Parent-only button that adds points to kid's balance based on bonus configuration.
    Validates global parent authorization before execution.
    """

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
        """Initialize the bonus button.

        Args:
            coordinator: KidsChoresDataCoordinator instance for data access and updates.
            entry: ConfigEntry for this integration instance.
            kid_id: Unique identifier for the kid.
            kid_name: Display name of the kid.
            bonus_id: Unique identifier for the bonus.
            bonus_name: Display name of the bonus.
            icon: Icon override from bonus configuration or default.
        """
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
        # Strip redundant "bonus" suffix from entity_id (bonus_name often ends with "Bonus")
        bonus_slug = bonus_name.lower().replace(" ", "_")
        if bonus_slug.endswith("_bonus"):
            bonus_slug = bonus_slug[:-6]  # Remove "_bonus" suffix
        self.entity_id = f"{const.BUTTON_KC_PREFIX}{kid_name}{const.BUTTON_KC_EID_MIDFIX_BONUS}{bonus_slug}"
        self._attr_device_info = kh.create_kid_device_info(kid_id, kid_name, entry)

    def press(self) -> None:
        """Synchronous press - not used, Home Assistant calls async_press."""

    async def async_press(self) -> None:
        """Handle the button press event.

        Validates global parent authorization, retrieves parent name from context,
        calls coordinator.apply_bonus() to add points to kid's balance based on bonus
        configuration, and triggers coordinator refresh.

        Raises:
            HomeAssistantError: If user not authorized for global parent actions.
        """
        try:
            user_id = self._context.user_id if self._context else None
            if user_id and not await kh.is_user_authorized_for_global_action(
                self.hass, user_id, const.SERVICE_APPLY_BONUS
            ):
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL,
                    translation_placeholders={
                        "action": const.ERROR_ACTION_APPLY_BONUSES
                    },
                )

            user_obj = await self.hass.auth.async_get_user(user_id) if user_id else None
            parent_name = (user_obj.name if user_obj else None) or const.DISPLAY_UNKNOWN

            self.coordinator.apply_bonus(
                parent_name=parent_name,
                kid_id=self._kid_id,
                bonus_id=self._bonus_id,
            )
            const.LOGGER.info(
                "INFO: Bonus '%s' applied to Kid '%s' by Parent '%s'",
                self._bonus_name,
                self._kid_name,
                parent_name,
            )
            await self.coordinator.async_request_refresh()

        except HomeAssistantError as e:
            const.LOGGER.error(
                "ERROR: Authorization failed to Apply Bonus '%s' for Kid '%s': %s",
                self._bonus_name,
                self._kid_name,
                e,
            )
        except (KeyError, ValueError, AttributeError) as e:
            const.LOGGER.error(
                "ERROR: Failed to Apply Bonus '%s' for Kid '%s': %s",
                self._bonus_name,
                self._kid_name,
                e,
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Include extra state attributes for the button."""
        bonus_info = self.coordinator.bonuses_data.get(self._bonus_id, {})
        stored_labels = bonus_info.get(const.DATA_BONUS_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes: dict[str, Any] = {
            const.ATTR_PURPOSE: const.TRANS_KEY_PURPOSE_BUTTON_BONUS_APPLY,
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_BONUS_NAME: self._bonus_name,
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes
