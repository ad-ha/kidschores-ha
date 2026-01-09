# File: services.py
# pylint: disable=too-many-lines  # Service registration module with 17 handlers
"""Defines custom services for the KidsChores integration.

These services allow direct actions through scripts or automations.
Includes UI editor support with selectors for dropdowns and text inputs.
"""

from datetime import datetime
from typing import Optional

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from . import const
from . import flow_helpers as fh
from . import kc_helpers as kh
from .coordinator import KidsChoresDataCoordinator

# --- Service Schemas ---

# Common schema base patterns for DRY principle
_KID_CHORE_BASE = {
    vol.Required(const.FIELD_KID_NAME): cv.string,
    vol.Required(const.FIELD_CHORE_NAME): cv.string,
}

_PARENT_KID_CHORE_BASE = {
    vol.Required(const.FIELD_PARENT_NAME): cv.string,
    vol.Required(const.FIELD_KID_NAME): cv.string,
    vol.Required(const.FIELD_CHORE_NAME): cv.string,
}

_PARENT_KID_REWARD_BASE = {
    vol.Required(const.FIELD_PARENT_NAME): cv.string,
    vol.Required(const.FIELD_KID_NAME): cv.string,
    vol.Required(const.FIELD_REWARD_NAME): cv.string,
}

_PARENT_KID_PENALTY_BASE = {
    vol.Required(const.FIELD_PARENT_NAME): cv.string,
    vol.Required(const.FIELD_KID_NAME): cv.string,
    vol.Required(const.FIELD_PENALTY_NAME): cv.string,
}

_PARENT_KID_BONUS_BASE = {
    vol.Required(const.FIELD_PARENT_NAME): cv.string,
    vol.Required(const.FIELD_KID_NAME): cv.string,
    vol.Required(const.FIELD_BONUS_NAME): cv.string,
}

# Service schemas using base patterns
CLAIM_CHORE_SCHEMA = vol.Schema(_KID_CHORE_BASE)

APPROVE_CHORE_SCHEMA = vol.Schema(
    {
        **_PARENT_KID_CHORE_BASE,
        vol.Optional(const.FIELD_POINTS_AWARDED): vol.Coerce(float),
    }
)

DISAPPROVE_CHORE_SCHEMA = vol.Schema(_PARENT_KID_CHORE_BASE)

REDEEM_REWARD_SCHEMA = vol.Schema(_PARENT_KID_REWARD_BASE)

APPROVE_REWARD_SCHEMA = vol.Schema(_PARENT_KID_REWARD_BASE)

DISAPPROVE_REWARD_SCHEMA = vol.Schema(_PARENT_KID_REWARD_BASE)

APPLY_PENALTY_SCHEMA = vol.Schema(_PARENT_KID_PENALTY_BASE)

APPLY_BONUS_SCHEMA = vol.Schema(_PARENT_KID_BONUS_BASE)

# Optional filter base patterns for reset operations
_OPTIONAL_KID_FILTER = {vol.Optional(const.FIELD_KID_NAME): cv.string}

_OPTIONAL_KID_PENALTY_FILTER = {
    vol.Optional(const.FIELD_KID_NAME): cv.string,
    vol.Optional(const.FIELD_PENALTY_NAME): cv.string,
}

_OPTIONAL_KID_BONUS_FILTER = {
    vol.Optional(const.FIELD_KID_NAME): cv.string,
    vol.Optional(const.FIELD_BONUS_NAME): cv.string,
}

_OPTIONAL_KID_REWARD_FILTER = {
    vol.Optional(const.FIELD_KID_NAME): cv.string,
    vol.Optional(const.FIELD_REWARD_NAME): cv.string,
}

RESET_OVERDUE_CHORES_SCHEMA = vol.Schema(
    {
        vol.Optional(const.FIELD_CHORE_ID): cv.string,
        vol.Optional(const.FIELD_CHORE_NAME): cv.string,
        vol.Optional(const.FIELD_KID_NAME): cv.string,
    }
)

RESET_PENALTIES_SCHEMA = vol.Schema(_OPTIONAL_KID_PENALTY_FILTER)

RESET_BONUSES_SCHEMA = vol.Schema(_OPTIONAL_KID_BONUS_FILTER)

RESET_REWARDS_SCHEMA = vol.Schema(_OPTIONAL_KID_REWARD_FILTER)

REMOVE_AWARDED_BADGES_SCHEMA = vol.Schema(
    {
        vol.Optional(const.FIELD_KID_NAME): vol.Any(cv.string, None),
        vol.Optional(const.FIELD_BADGE_NAME): vol.Any(cv.string, None),
    }
)

RESET_ALL_DATA_SCHEMA = vol.Schema({})

RESET_ALL_CHORES_SCHEMA = vol.Schema({})

SET_CHORE_DUE_DATE_SCHEMA = vol.Schema(
    {
        vol.Required(const.FIELD_CHORE_NAME): cv.string,
        vol.Optional(const.FIELD_DUE_DATE): vol.Any(cv.string, None),
        vol.Optional(const.FIELD_KID_NAME): cv.string,
        vol.Optional(const.FIELD_KID_ID): cv.string,
    }
)

SKIP_CHORE_DUE_DATE_SCHEMA = vol.Schema(
    {
        vol.Optional(const.FIELD_CHORE_ID): cv.string,
        vol.Optional(const.FIELD_CHORE_NAME): cv.string,
        vol.Optional(const.FIELD_KID_NAME): cv.string,
        vol.Optional(const.FIELD_KID_ID): cv.string,
    }
)


def async_setup_services(hass: HomeAssistant):
    """Register KidsChores services."""

    async def handle_claim_chore(call: ServiceCall):
        """Handle claiming a chore."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Claim Chore: %s", const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        user_id = call.context.user_id
        kid_name = call.data[const.FIELD_KID_NAME]
        chore_name = call.data[const.FIELD_CHORE_NAME]

        # Map kid_name and chore_name to internal_ids
        try:
            kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)
            chore_id = kh.get_chore_id_or_raise(coordinator, chore_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Claim Chore: %s", err)
            raise

        # Check if user is authorized
        if user_id and not await kh.is_user_authorized_for_kid(hass, user_id, kid_id):
            const.LOGGER.warning(
                "Claim Chore: %s", const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION
            )
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION,
                translation_placeholders={"action": const.ERROR_ACTION_CLAIM_CHORES},
            )

        # Process chore claim
        coordinator.claim_chore(
            kid_id=kid_id, chore_id=chore_id, user_name=f"user:{user_id}"
        )

        const.LOGGER.info(
            "Chore '%s' claimed by kid '%s' by user '%s'",
            chore_name,
            kid_name,
            user_id,
        )
        await coordinator.async_request_refresh()

    async def handle_approve_chore(call: ServiceCall):
        """Handle approving a claimed chore."""
        entry_id = kh.get_first_kidschores_entry(hass)

        if not entry_id:
            const.LOGGER.warning(
                "Approve Chore: %s", const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        user_id = call.context.user_id
        parent_name = call.data[const.FIELD_PARENT_NAME]
        kid_name = call.data[const.FIELD_KID_NAME]
        chore_name = call.data[const.FIELD_CHORE_NAME]
        points_awarded = call.data.get(const.FIELD_POINTS_AWARDED)

        # Map kid_name and chore_name to internal_ids
        try:
            kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)
            chore_id = kh.get_chore_id_or_raise(coordinator, chore_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Approve Chore: %s", err)
            raise

        # Check if user is authorized
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, const.SERVICE_APPROVE_CHORE
        ):
            const.LOGGER.warning(
                "Approve Chore: %s", const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION
            )
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION,
                translation_placeholders={"action": const.ERROR_ACTION_APPROVE_CHORES},
            )

        # Approve chore and assign points
        try:
            coordinator.approve_chore(
                parent_name=parent_name,
                kid_id=kid_id,
                chore_id=chore_id,
                points_awarded=points_awarded,
            )
            const.LOGGER.info(
                "Chore '%s' approved for kid '%s' by parent '%s'. Points Awarded: %s",
                chore_name,
                kid_name,
                parent_name,
                points_awarded,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError:  # pylint: disable=try-except-raise  # Log before re-raise
            raise

    async def handle_disapprove_chore(call: ServiceCall):
        """Handle disapproving a chore."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Disapprove Chore: %s",
                const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND,
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        parent_name = call.data[const.FIELD_PARENT_NAME]
        kid_name = call.data[const.FIELD_KID_NAME]
        chore_name = call.data[const.FIELD_CHORE_NAME]

        # Map kid_name and chore_name to internal_ids
        try:
            kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)
            chore_id = kh.get_chore_id_or_raise(coordinator, chore_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Disapprove Chore: %s", err)
            raise

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, const.SERVICE_DISAPPROVE_CHORE
        ):
            const.LOGGER.warning(
                "Disapprove Chore: %s", const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION
            )
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION,
                translation_placeholders={
                    "action": const.ERROR_ACTION_DISAPPROVE_CHORES
                },
            )

        # Disapprove the chore
        coordinator.disapprove_chore(
            parent_name=parent_name,
            kid_id=kid_id,
            chore_id=chore_id,
        )
        const.LOGGER.info(
            "Chore '%s' disapproved for kid '%s' by parent '%s'",
            chore_name,
            kid_name,
            parent_name,
        )
        await coordinator.async_request_refresh()

    async def handle_redeem_reward(call: ServiceCall):
        """Handle redeeming a reward (claiming without deduction)."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Redeem Reward: %s", const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        parent_name = call.data[const.FIELD_PARENT_NAME]
        kid_name = call.data[const.FIELD_KID_NAME]
        reward_name = call.data[const.FIELD_REWARD_NAME]

        # Map kid_name and reward_name to internal_ids
        try:
            kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)
            reward_id = kh.get_reward_id_or_raise(coordinator, reward_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Redeem Reward: %s", err)
            raise

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_kid(hass, user_id, kid_id):
            const.LOGGER.warning(
                "Redeem Reward: %s", const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION
            )
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION,
                translation_placeholders={"action": const.ERROR_ACTION_REDEEM_REWARDS},
            )

        # Check if kid has enough points
        kid_info = coordinator.kids_data.get(kid_id)
        reward_info = coordinator.rewards_data.get(reward_id)
        if not kid_info:
            const.LOGGER.warning("Redeem Reward: Kid not found")
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_KID,
                    "name": kid_name or "unknown",
                },
            )
        if not reward_info:
            const.LOGGER.warning("Redeem Reward: Reward not found")
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_FOUND,
                translation_placeholders={
                    "entity_type": const.LABEL_REWARD,
                    "name": reward_name or "unknown",
                },
            )

        if kid_info[const.DATA_KID_POINTS] < reward_info.get(
            const.DATA_REWARD_COST, const.DEFAULT_ZERO
        ):
            const.LOGGER.warning(
                "Redeem Reward: %s", const.TRANS_KEY_ERROR_INSUFFICIENT_POINTS
            )
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_INSUFFICIENT_POINTS,
                translation_placeholders={
                    "kid_name": kid_name,
                    "reward_name": reward_name,
                },
            )

        # Process reward claim without deduction
        try:
            coordinator.redeem_reward(
                parent_name=parent_name, kid_id=kid_id, reward_id=reward_id
            )
            const.LOGGER.info(
                "Reward '%s' claimed by kid '%s' and pending approval by parent '%s'",
                reward_name,
                kid_name,
                parent_name,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError:  # pylint: disable=try-except-raise  # Log before re-raise
            raise

    async def handle_approve_reward(call: ServiceCall):
        """Handle approving a reward claimed by a kid."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Approve Reward: %s", const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        user_id = call.context.user_id
        parent_name = call.data[const.FIELD_PARENT_NAME]
        kid_name = call.data[const.FIELD_KID_NAME]
        reward_name = call.data[const.FIELD_REWARD_NAME]

        # Map kid_name and reward_name to internal_ids
        try:
            kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)
            reward_id = kh.get_reward_id_or_raise(coordinator, reward_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Approve Reward: %s", err)
            raise

        # Check if user is authorized
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, const.SERVICE_APPROVE_REWARD
        ):
            const.LOGGER.warning(
                "Approve Reward: %s", const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION
            )
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION,
                translation_placeholders={"action": const.ERROR_ACTION_APPROVE_REWARDS},
            )

        # Approve reward redemption and deduct points
        try:
            coordinator.approve_reward(
                parent_name=parent_name, kid_id=kid_id, reward_id=reward_id
            )
            const.LOGGER.info(
                "Reward '%s' approved for kid '%s' by parent '%s'",
                reward_name,
                kid_name,
                parent_name,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError:  # pylint: disable=try-except-raise  # Log before re-raise
            raise

    async def handle_disapprove_reward(call: ServiceCall):
        """Handle disapproving a reward."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Disapprove Reward: %s",
                const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND,
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        parent_name = call.data[const.FIELD_PARENT_NAME]
        kid_name = call.data[const.FIELD_KID_NAME]
        reward_name = call.data[const.FIELD_REWARD_NAME]

        # Map kid_name and reward_name to internal_ids
        try:
            kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)
            reward_id = kh.get_reward_id_or_raise(coordinator, reward_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Disapprove Reward: %s", err)
            raise

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, const.SERVICE_DISAPPROVE_REWARD
        ):
            const.LOGGER.warning(
                "Disapprove Reward: %s", const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION
            )
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION,
                translation_placeholders={
                    "action": const.ERROR_ACTION_DISAPPROVE_REWARDS
                },
            )

        # Disapprove the reward
        coordinator.disapprove_reward(
            parent_name=parent_name,
            kid_id=kid_id,
            reward_id=reward_id,
        )
        const.LOGGER.info(
            "Reward '%s' disapproved for kid '%s' by parent '%s'",
            reward_name,
            kid_name,
            parent_name,
        )
        await coordinator.async_request_refresh()

    async def handle_apply_penalty(call: ServiceCall):
        """Handle applying a penalty."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Apply Penalty: %s", const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        parent_name = call.data[const.FIELD_PARENT_NAME]
        kid_name = call.data[const.FIELD_KID_NAME]
        penalty_name = call.data[const.FIELD_PENALTY_NAME]

        # Map kid_name and penalty_name to internal_ids
        try:
            kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)
            penalty_id = kh.get_penalty_id_or_raise(coordinator, penalty_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Apply Penalty: %s", err)
            raise

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, const.SERVICE_APPLY_PENALTY
        ):
            const.LOGGER.warning(
                "Apply Penalty: %s", const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION
            )
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION,
                translation_placeholders={"action": const.ERROR_ACTION_APPLY_PENALTIES},
            )

        # Apply penalty
        try:
            coordinator.apply_penalty(
                parent_name=parent_name, kid_id=kid_id, penalty_id=penalty_id
            )
            const.LOGGER.info(
                "Penalty '%s' applied for kid '%s' by parent '%s'",
                penalty_name,
                kid_name,
                parent_name,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError:  # pylint: disable=try-except-raise  # Log before re-raise
            raise

    async def handle_reset_penalties(call: ServiceCall):
        """Handle resetting penalties."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Reset Penalties: %s", const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]

        kid_name = call.data.get(const.FIELD_KID_NAME)
        penalty_name = call.data.get(const.FIELD_PENALTY_NAME)

        # Map names to IDs (optional parameters)
        kid_id = None
        penalty_id = None
        try:
            if kid_name:
                kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)
            if penalty_name:
                penalty_id = kh.get_penalty_id_or_raise(coordinator, penalty_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Reset Penalties: %s", err)
            raise

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, const.SERVICE_RESET_PENALTIES
        ):
            const.LOGGER.warning(
                "Reset Penalties: %s",
                const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL,
            )
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL,
                translation_placeholders={"action": const.ERROR_ACTION_RESET_PENALTIES},
            )

        # Log action based on parameters provided
        if kid_id is None and penalty_id is None:
            const.LOGGER.info("Resetting all penalties for all kids.")
        elif kid_id is None:
            const.LOGGER.info("Resetting penalty '%s' for all kids.", penalty_name)
        elif penalty_id is None:
            const.LOGGER.info("Resetting all penalties for kid '%s'.", kid_name)
        else:
            const.LOGGER.info(
                "Resetting penalty '%s' for kid '%s'.", penalty_name, kid_name
            )

        # Reset penalties
        coordinator.reset_penalties(kid_id=kid_id, penalty_id=penalty_id)
        await coordinator.async_request_refresh()

    async def handle_reset_bonuses(call: ServiceCall):
        """Handle resetting bonuses."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Reset Bonuses: %s", const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]

        kid_name = call.data.get(const.FIELD_KID_NAME)
        bonus_name = call.data.get(const.FIELD_BONUS_NAME)

        # Map names to IDs (optional parameters)
        kid_id = None
        bonus_id = None
        try:
            if kid_name:
                kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)
            if bonus_name:
                bonus_id = kh.get_bonus_id_or_raise(coordinator, bonus_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Reset Bonuses: %s", err)
            raise

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, const.SERVICE_RESET_BONUSES
        ):
            const.LOGGER.warning(
                "Reset Bonuses: %s", const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL
            )
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL,
                translation_placeholders={"action": const.ERROR_ACTION_RESET_BONUSES},
            )

        # Log action based on parameters provided
        if kid_id is None and bonus_id is None:
            const.LOGGER.info("Resetting all bonuses for all kids.")
        elif kid_id is None:
            const.LOGGER.info("Resetting bonus '%s' for all kids.", bonus_name)
        elif bonus_id is None:
            const.LOGGER.info("Resetting all bonuses for kid '%s'.", kid_name)
        else:
            const.LOGGER.info(
                "Resetting bonus '%s' for kid '%s'.", bonus_name, kid_name
            )

        # Reset bonuses
        coordinator.reset_bonuses(kid_id=kid_id, bonus_id=bonus_id)
        await coordinator.async_request_refresh()

    async def handle_reset_rewards(call: ServiceCall):
        """Handle resetting rewards counts."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Reset Rewards: %s", const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]

        kid_name = call.data.get(const.FIELD_KID_NAME)
        reward_name = call.data.get(const.FIELD_REWARD_NAME)

        # Map names to IDs (optional parameters)
        kid_id = None
        reward_id = None
        try:
            if kid_name:
                kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)
            if reward_name:
                reward_id = kh.get_reward_id_or_raise(coordinator, reward_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Reset Rewards: %s", err)
            raise

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, const.SERVICE_RESET_REWARDS
        ):
            const.LOGGER.warning(
                "Reset Rewards: %s", const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL
            )
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL,
                translation_placeholders={"action": const.ERROR_ACTION_RESET_REWARDS},
            )

        # Log action based on parameters provided
        if kid_id is None and reward_id is None:
            const.LOGGER.info("Resetting all rewards for all kids.")
        elif kid_id is None:
            const.LOGGER.info("Resetting reward '%s' for all kids.", reward_name)
        elif reward_id is None:
            const.LOGGER.info("Resetting all rewards for kid '%s'.", kid_name)
        else:
            const.LOGGER.info(
                "Resetting reward '%s' for kid '%s'.", reward_name, kid_name
            )

        # Reset rewards
        coordinator.reset_rewards(kid_id=kid_id, reward_id=reward_id)
        await coordinator.async_request_refresh()

    async def handle_remove_awarded_badges(call: ServiceCall):
        """Handle removing awarded badges."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Remove Awarded Badges: %s",
                const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND,
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]

        kid_name = call.data.get(const.FIELD_KID_NAME)
        badge_name = call.data.get(const.FIELD_BADGE_NAME)

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, const.SERVICE_REMOVE_AWARDED_BADGES
        ):
            const.LOGGER.warning("Remove Awarded Badges: User not authorized.")
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL,
                translation_placeholders={"action": const.ERROR_ACTION_REMOVE_BADGES},
            )

        # Log action based on parameters provided
        if kid_name is None and badge_name is None:
            const.LOGGER.info("Removing all badges for all kids.")
        elif kid_name is None:
            const.LOGGER.info("Removing badge '%s' for all kids.", badge_name)
        elif badge_name is None:
            const.LOGGER.info("Removing all badges for kid '%s'.", kid_name)
        else:
            const.LOGGER.info("Removing badge '%s' for kid '%s'.", badge_name, kid_name)

        # Remove awarded badges
        coordinator.remove_awarded_badges(kid_name=kid_name, badge_name=badge_name)
        await coordinator.async_request_refresh()

    async def handle_apply_bonus(call: ServiceCall):
        """Handle applying a bonus."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Apply Bonus: %s", const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        parent_name = call.data[const.FIELD_PARENT_NAME]
        kid_name = call.data[const.FIELD_KID_NAME]
        bonus_name = call.data[const.FIELD_BONUS_NAME]

        # Map kid_name and bonus_name to internal_ids
        try:
            kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)
            bonus_id = kh.get_bonus_id_or_raise(coordinator, bonus_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Apply Bonus: %s", err)
            raise

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, const.SERVICE_APPLY_BONUS
        ):
            const.LOGGER.warning("Apply Bonus: User not authorized")
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION,
                translation_placeholders={"action": const.ERROR_ACTION_APPLY_BONUSES},
            )

        # Apply bonus
        try:
            coordinator.apply_bonus(
                parent_name=parent_name, kid_id=kid_id, bonus_id=bonus_id
            )
            const.LOGGER.info(
                "Bonus '%s' applied for kid '%s' by parent '%s'",
                bonus_name,
                kid_name,
                parent_name,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError:  # pylint: disable=try-except-raise  # Log before re-raise
            raise

    async def handle_reset_all_data(_call: ServiceCall):
        """Handle manually resetting ALL data in KidsChores (factory reset)."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning("Reset All Data: No KidsChores entry found")
            return

        data = hass.data[const.DOMAIN].get(entry_id)
        if not data:
            const.LOGGER.warning("Reset All Data: No coordinator data found")
            return

        coordinator: KidsChoresDataCoordinator = data[const.COORDINATOR]

        # Step 1: Create backup before factory reset
        try:
            backup_name = await fh.create_timestamped_backup(
                hass, coordinator.storage_manager, const.BACKUP_TAG_RESET
            )
            if backup_name:
                const.LOGGER.info("Created pre-reset backup: %s", backup_name)
            else:
                const.LOGGER.warning("No data available to include in pre-reset backup")
        except Exception as err:  # pylint: disable=broad-exception-caught
            const.LOGGER.warning("Failed to create pre-reset backup: %s", err)

        # Step 2: Clean up entity registry BEFORE clearing storage
        # This prevents orphaned registry entries that cause _2 suffixes when re-adding entities
        ent_reg = er.async_get(hass)
        entity_count = 0
        for entity_entry in er.async_entries_for_config_entry(ent_reg, entry_id):
            ent_reg.async_remove(entity_entry.entity_id)
            entity_count += 1
            const.LOGGER.debug(
                "Removed entity registry entry: %s (unique_id: %s)",
                entity_entry.entity_id,
                entity_entry.unique_id,
            )

        const.LOGGER.info("Removed %d entity registry entries", entity_count)

        # Step 3: Clear everything from storage (resets to empty kids/chores/badges structure)
        await coordinator.storage_manager.async_clear_data()

        # Step 4: Reload config entry to clean up platforms and reinitialize
        # This ensures all internal state is properly reset
        await hass.config_entries.async_reload(entry_id)

        coordinator.async_set_updated_data(coordinator.data)
        const.LOGGER.info(
            "Factory reset complete. Backup created, entity registry cleaned, all data cleared."
        )

    async def handle_reset_all_chores(_call: ServiceCall):
        """Handle manually resetting all chores to pending, clearing claims/approvals."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning("Reset All Chores: No KidsChores entry found")
            return

        data = hass.data[const.DOMAIN].get(entry_id)
        if not data:
            const.LOGGER.warning("Reset All Chores: No coordinator data found")
            return

        coordinator: KidsChoresDataCoordinator = data[const.COORDINATOR]

        # Delegate to coordinator method
        coordinator.reset_all_chores()

    async def handle_reset_overdue_chores(call: ServiceCall) -> None:
        """Handle resetting overdue chores."""

        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Reset Overdue Chores: %s",
                const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND,
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]

        # Get parameters
        chore_id = call.data.get(const.FIELD_CHORE_ID)
        chore_name = call.data.get(const.FIELD_CHORE_NAME)
        kid_name = call.data.get(const.FIELD_KID_NAME)

        # Map names to IDs (optional parameters)
        try:
            if not chore_id and chore_name:
                chore_id = kh.get_chore_id_or_raise(coordinator, chore_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Reset Overdue Chores: %s", err)
            raise

        kid_id: Optional[str] = None
        try:
            if kid_name:
                kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Reset Overdue Chores: %s", err)
            raise

        coordinator.reset_overdue_chores(chore_id=chore_id, kid_id=kid_id)

        const.LOGGER.info(
            "Reset overdue chores (chore_id=%s, kid_id=%s)", chore_id, kid_id
        )

        await coordinator.async_request_refresh()

    async def handle_set_chore_due_date(call: ServiceCall):
        """Handle setting (or clearing) the due date of a chore.

        For INDEPENDENT chores, optionally specify kid_id or kid_name.
        For SHARED chores, kid_id is ignored (single due date for all kids).
        """
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Set Chore Due Date: %s",
                const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND,
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        chore_name = call.data[const.FIELD_CHORE_NAME]
        due_date_input = call.data.get(const.FIELD_DUE_DATE)
        kid_name = call.data.get(const.FIELD_KID_NAME)
        kid_id = call.data.get(const.FIELD_KID_ID)

        # Look up the chore by name:
        try:
            chore_id = kh.get_chore_id_or_raise(coordinator, chore_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Set Chore Due Date: %s", err)
            raise

        # If kid_name is provided, resolve it to kid_id
        if kid_name and not kid_id:
            try:
                kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)
            except HomeAssistantError as err:
                const.LOGGER.warning("Set Chore Due Date: %s", err)
                raise

        # Validate that if kid_id is provided, the chore is INDEPENDENT and kid is assigned
        if kid_id:
            chore_info = coordinator.chores_data.get(chore_id, {})
            completion_criteria = chore_info.get(
                const.DATA_CHORE_COMPLETION_CRITERIA,
                const.COMPLETION_CRITERIA_INDEPENDENT,
            )
            # Reject kid_id for SHARED and SHARED_FIRST chores
            # (they use chore-level due dates, not per-kid)
            if completion_criteria in (
                const.COMPLETION_CRITERIA_SHARED,
                const.COMPLETION_CRITERIA_SHARED_FIRST,
            ):
                const.LOGGER.warning(
                    "Set Chore Due Date: Cannot specify kid_id for %s chore '%s'",
                    completion_criteria,
                    chore_name,
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_SHARED_CHORE_KID,
                    translation_placeholders={"chore_name": str(chore_name)},
                )

            assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
            if kid_id not in assigned_kids:
                const.LOGGER.warning(
                    "Set Chore Due Date: Kid '%s' not assigned to chore '%s'",
                    kid_id,
                    chore_name,
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_ASSIGNED,
                    translation_placeholders={
                        "entity": str(kid_name or kid_id),
                        "kid": str(chore_name),
                    },
                )

        if due_date_input:
            try:
                # Convert the provided date to UTC-aware datetime
                due_dt_raw = kh.normalize_datetime_input(
                    due_date_input,
                    return_type=const.HELPER_RETURN_DATETIME_UTC,
                )
                # Ensure due_dt is a datetime object (not date or str)
                if due_dt_raw and not isinstance(due_dt_raw, datetime):
                    raise HomeAssistantError(
                        translation_domain=const.DOMAIN,
                        translation_key=const.TRANS_KEY_ERROR_INVALID_DATE_FORMAT,
                    )
                due_dt: datetime | None = due_dt_raw  # type: ignore[assignment]
                if (
                    due_dt
                    and isinstance(due_dt, datetime)
                    and due_dt < dt_util.utcnow()
                ):
                    raise HomeAssistantError(
                        translation_domain=const.DOMAIN,
                        translation_key=const.TRANS_KEY_ERROR_DATE_IN_PAST,
                    )

            except HomeAssistantError as err:
                const.LOGGER.error(
                    "Set Chore Due Date: Invalid due date '%s': %s",
                    due_date_input,
                    err,
                )
                raise

            # Update the chore’s due_date:
            coordinator.set_chore_due_date(chore_id, due_dt, kid_id)
            const.LOGGER.info(
                "Set due date for chore '%s' (ID: %s) to %s",
                chore_name,
                chore_id,
                due_date_input,
            )
        else:
            # Clear the due date by setting it to None
            coordinator.set_chore_due_date(chore_id, None, kid_id)
            const.LOGGER.info(
                "Cleared due date for chore '%s' (ID: %s)", chore_name, chore_id
            )

        await coordinator.async_request_refresh()

    async def handle_skip_chore_due_date(call: ServiceCall) -> None:
        """Handle skipping the due date on a chore by rescheduling it to the next due date.

        For INDEPENDENT chores, you can optionally specify kid_name or kid_id.
        For SHARED chores, you must not specify a kid.
        """
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "Skip Chore Due Date: %s",
                const.TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND,
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]

        # Get parameters: either chore_id or chore_name must be provided.
        chore_id = call.data.get(const.FIELD_CHORE_ID)
        chore_name = call.data.get(const.FIELD_CHORE_NAME)

        try:
            if not chore_id and chore_name:
                chore_id = kh.get_chore_id_or_raise(coordinator, chore_name)
        except HomeAssistantError as err:
            const.LOGGER.warning("Skip Chore Due Date: %s", err)
            raise

        if not chore_id:
            raise HomeAssistantError(
                translation_domain=const.DOMAIN,
                translation_key=const.TRANS_KEY_ERROR_MISSING_CHORE,
            )

        # Get kid parameters (for INDEPENDENT chores only)
        kid_name = call.data.get(const.FIELD_KID_NAME)
        kid_id = call.data.get(const.FIELD_KID_ID)

        # Resolve kid_name to kid_id if provided
        if kid_name and not kid_id:
            kid_id = kh.get_kid_id_or_raise(coordinator, kid_name)

        # Validate kid_id (if provided)
        if kid_id:
            chore_info = coordinator.chores_data.get(chore_id, {})
            completion_criteria = chore_info.get(
                const.DATA_CHORE_COMPLETION_CRITERIA,
                const.COMPLETION_CRITERIA_INDEPENDENT,
            )
            # Reject kid_id for SHARED and SHARED_FIRST chores
            # (they use chore-level due dates, not per-kid)
            if completion_criteria in (
                const.COMPLETION_CRITERIA_SHARED,
                const.COMPLETION_CRITERIA_SHARED_FIRST,
            ):
                const.LOGGER.warning(
                    "Skip Chore Due Date: Cannot specify kid_id for %s chore '%s'",
                    completion_criteria,
                    chore_name,
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_SHARED_CHORE_KID,
                    translation_placeholders={"chore_name": str(chore_name)},
                )

            assigned_kids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
            if kid_id not in assigned_kids:
                const.LOGGER.warning(
                    "Skip Chore Due Date: Kid '%s' not assigned to chore '%s'",
                    kid_id,
                    chore_name,
                )
                raise HomeAssistantError(
                    translation_domain=const.DOMAIN,
                    translation_key=const.TRANS_KEY_ERROR_NOT_ASSIGNED,
                    translation_placeholders={
                        "entity": str(kid_name or kid_id),
                        "kid": str(chore_name),
                    },
                )

        coordinator.skip_chore_due_date(chore_id, kid_id)
        kid_context = f" for kid '{kid_name or kid_id}'" if kid_id else ""
        const.LOGGER.info(
            "Skipped due date for chore '%s' (ID: %s)%s",
            chore_name or chore_id,
            chore_id,
            kid_context,
        )
        await coordinator.async_request_refresh()

    # --- Register Services ---
    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_CLAIM_CHORE,
        handle_claim_chore,
        schema=CLAIM_CHORE_SCHEMA,
    )
    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_APPROVE_CHORE,
        handle_approve_chore,
        schema=APPROVE_CHORE_SCHEMA,
    )
    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_DISAPPROVE_CHORE,
        handle_disapprove_chore,
        schema=DISAPPROVE_CHORE_SCHEMA,
    )
    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_REDEEM_REWARD,
        handle_redeem_reward,
        schema=REDEEM_REWARD_SCHEMA,
    )
    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_APPROVE_REWARD,
        handle_approve_reward,
        schema=APPROVE_REWARD_SCHEMA,
    )
    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_DISAPPROVE_REWARD,
        handle_disapprove_reward,
        schema=DISAPPROVE_REWARD_SCHEMA,
    )
    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_APPLY_PENALTY,
        handle_apply_penalty,
        schema=APPLY_PENALTY_SCHEMA,
    )
    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_RESET_ALL_DATA,
        handle_reset_all_data,
        schema=RESET_ALL_DATA_SCHEMA,
    )

    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_RESET_ALL_CHORES,
        handle_reset_all_chores,
        schema=RESET_ALL_CHORES_SCHEMA,
    )

    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_RESET_OVERDUE_CHORES,
        handle_reset_overdue_chores,
        schema=RESET_OVERDUE_CHORES_SCHEMA,
    )

    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_RESET_PENALTIES,
        handle_reset_penalties,
        schema=RESET_PENALTIES_SCHEMA,
    )

    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_RESET_BONUSES,
        handle_reset_bonuses,
        schema=RESET_BONUSES_SCHEMA,
    )

    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_RESET_REWARDS,
        handle_reset_rewards,
        schema=RESET_REWARDS_SCHEMA,
    )

    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_REMOVE_AWARDED_BADGES,
        handle_remove_awarded_badges,
        schema=REMOVE_AWARDED_BADGES_SCHEMA,
    )

    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_SET_CHORE_DUE_DATE,
        handle_set_chore_due_date,
        schema=SET_CHORE_DUE_DATE_SCHEMA,
    )

    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_SKIP_CHORE_DUE_DATE,
        handle_skip_chore_due_date,
        schema=SKIP_CHORE_DUE_DATE_SCHEMA,
    )

    hass.services.async_register(
        const.DOMAIN,
        const.SERVICE_APPLY_BONUS,
        handle_apply_bonus,
        schema=APPLY_BONUS_SCHEMA,
    )

    const.LOGGER.info("KidsChores services have been registered successfully")


async def async_unload_services(hass: HomeAssistant):
    """Unregister KidsChores services when unloading the integration."""
    services = [
        const.SERVICE_CLAIM_CHORE,
        const.SERVICE_APPROVE_CHORE,
        const.SERVICE_DISAPPROVE_CHORE,
        const.SERVICE_REDEEM_REWARD,
        const.SERVICE_DISAPPROVE_REWARD,
        const.SERVICE_APPLY_PENALTY,
        const.SERVICE_APPLY_BONUS,
        const.SERVICE_APPROVE_REWARD,
        const.SERVICE_RESET_ALL_DATA,
        const.SERVICE_RESET_ALL_CHORES,
        const.SERVICE_RESET_OVERDUE_CHORES,
        const.SERVICE_RESET_PENALTIES,
        const.SERVICE_RESET_BONUSES,
        const.SERVICE_RESET_REWARDS,
        const.SERVICE_REMOVE_AWARDED_BADGES,
        const.SERVICE_SET_CHORE_DUE_DATE,
        const.SERVICE_SKIP_CHORE_DUE_DATE,
    ]

    for service in services:
        if hass.services.has_service(const.DOMAIN, service):
            hass.services.async_remove(const.DOMAIN, service)

    const.LOGGER.info("KidsChores services have been unregistered")
