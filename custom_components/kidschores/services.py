# File: services.py
"""Defines custom services for the KidsChores integration.

These services allow direct actions through scripts or automations.
Includes UI editor support with selectors for dropdowns and text inputs.
"""

from typing import Optional
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from . import const
from . import flow_helpers as fh
from . import kc_helpers as kh
from .coordinator import KidsChoresDataCoordinator

# --- Service Schemas ---
CLAIM_CHORE_SCHEMA = vol.Schema(
    {
        vol.Required(const.FIELD_KID_NAME): cv.string,
        vol.Required(const.FIELD_CHORE_NAME): cv.string,
    }
)

APPROVE_CHORE_SCHEMA = vol.Schema(
    {
        vol.Required(const.FIELD_PARENT_NAME): cv.string,
        vol.Required(const.FIELD_KID_NAME): cv.string,
        vol.Required(const.FIELD_CHORE_NAME): cv.string,
        vol.Optional(const.FIELD_POINTS_AWARDED): vol.Coerce(float),
    }
)

DISAPPROVE_CHORE_SCHEMA = vol.Schema(
    {
        vol.Required(const.FIELD_PARENT_NAME): cv.string,
        vol.Required(const.FIELD_KID_NAME): cv.string,
        vol.Required(const.FIELD_CHORE_NAME): cv.string,
    }
)

REDEEM_REWARD_SCHEMA = vol.Schema(
    {
        vol.Required(const.FIELD_PARENT_NAME): cv.string,
        vol.Required(const.FIELD_KID_NAME): cv.string,
        vol.Required(const.FIELD_REWARD_NAME): cv.string,
    }
)

APPROVE_REWARD_SCHEMA = vol.Schema(
    {
        vol.Required(const.FIELD_PARENT_NAME): cv.string,
        vol.Required(const.FIELD_KID_NAME): cv.string,
        vol.Required(const.FIELD_REWARD_NAME): cv.string,
    }
)

DISAPPROVE_REWARD_SCHEMA = vol.Schema(
    {
        vol.Required(const.FIELD_PARENT_NAME): cv.string,
        vol.Required(const.FIELD_KID_NAME): cv.string,
        vol.Required(const.FIELD_REWARD_NAME): cv.string,
    }
)

APPLY_PENALTY_SCHEMA = vol.Schema(
    {
        vol.Required(const.FIELD_PARENT_NAME): cv.string,
        vol.Required(const.FIELD_KID_NAME): cv.string,
        vol.Required(const.FIELD_PENALTY_NAME): cv.string,
    }
)

APPLY_BONUS_SCHEMA = vol.Schema(
    {
        vol.Required(const.FIELD_PARENT_NAME): cv.string,
        vol.Required(const.FIELD_KID_NAME): cv.string,
        vol.Required(const.FIELD_BONUS_NAME): cv.string,
    }
)

RESET_OVERDUE_CHORES_SCHEMA = vol.Schema(
    {
        vol.Optional(const.FIELD_CHORE_ID): cv.string,
        vol.Optional(const.FIELD_CHORE_NAME): cv.string,
        vol.Optional(const.FIELD_KID_NAME): cv.string,
    }
)

RESET_PENALTIES_SCHEMA = vol.Schema(
    {
        vol.Optional(const.FIELD_KID_NAME): cv.string,
        vol.Optional(const.FIELD_PENALTY_NAME): cv.string,
    }
)

RESET_BONUSES_SCHEMA = vol.Schema(
    {
        vol.Optional(const.FIELD_KID_NAME): cv.string,
        vol.Optional(const.FIELD_BONUS_NAME): cv.string,
    }
)

RESET_REWARDS_SCHEMA = vol.Schema(
    {
        vol.Optional(const.FIELD_KID_NAME): cv.string,
        vol.Optional(const.FIELD_REWARD_NAME): cv.string,
    }
)

RESET_ALL_DATA_SCHEMA = vol.Schema({})

RESET_ALL_CHORES_SCHEMA = vol.Schema({})

SET_CHORE_DUE_DATE_SCHEMA = vol.Schema(
    {
        vol.Required(const.FIELD_CHORE_NAME): cv.string,
        vol.Optional(const.FIELD_DUE_DATE): vol.Any(cv.string, None),
    }
)

SKIP_CHORE_DUE_DATE_SCHEMA = vol.Schema(
    {
        vol.Optional(const.FIELD_CHORE_ID): cv.string,
        vol.Optional(const.FIELD_CHORE_NAME): cv.string,
    }
)


def async_setup_services(hass: HomeAssistant):
    """Register KidsChores services."""

    async def handle_claim_chore(call: ServiceCall):
        """Handle claiming a chore."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning("WARNING: Claim Chore: %s", const.MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        user_id = call.context.user_id
        kid_name = call.data[const.FIELD_KID_NAME]
        chore_name = call.data[const.FIELD_CHORE_NAME]

        # Map kid_name and chore_name to internal_ids
        kid_id = kh.get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            const.LOGGER.warning(
                "WARNING: Claim Chore: " + const.ERROR_KID_NOT_FOUND_FMT, kid_name
            )
            raise HomeAssistantError(const.ERROR_KID_NOT_FOUND_FMT.format(kid_name))

        chore_id = kh.get_chore_id_by_name(coordinator, chore_name)
        if not chore_id:
            const.LOGGER.warning(
                "WARNING: Claim Chore: " + const.ERROR_CHORE_NOT_FOUND_FMT, chore_name
            )
            raise HomeAssistantError(const.ERROR_CHORE_NOT_FOUND_FMT.format(chore_name))

        # Check if user is authorized
        if user_id and not await kh.is_user_authorized_for_kid(hass, user_id, kid_id):
            const.LOGGER.warning(
                "WARNING: Claim Chore: %s", const.ERROR_NOT_AUTHORIZED_FMT
            )
            raise HomeAssistantError(
                const.ERROR_NOT_AUTHORIZED_FMT.format(
                    const.TRANS_KEY_FMT_ERROR_CLAIM_CHORES
                )
            )

        # Process chore claim
        coordinator.claim_chore(
            kid_id=kid_id, chore_id=chore_id, user_name=f"user:{user_id}"
        )

        const.LOGGER.info(
            "INFO: Chore '%s' claimed by kid '%s' by user '%s'",
            chore_name,
            kid_name,
            user_id,
        )
        await coordinator.async_request_refresh()

    async def handle_approve_chore(call: ServiceCall):
        """Handle approving a claimed chore."""
        entry_id = kh.get_first_kidschores_entry(hass)

        if not entry_id:
            const.LOGGER.warning("WARNING: Approve Chore: %s", const.MSG_NO_ENTRY_FOUND)
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
        kid_id = kh.get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            const.LOGGER.warning("WARNING: Approve Chore: Kid '%s' not found", kid_name)
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        chore_id = kh.get_chore_id_by_name(coordinator, chore_name)
        if not chore_id:
            const.LOGGER.warning(
                "WARNING: Approve Chore: Chore '%s' not found", chore_name
            )
            raise HomeAssistantError(f"Chore '{chore_name}' not found")

        # Check if user is authorized
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            const.LOGGER.warning("WARNING: Approve Chore: User not authorized")
            raise HomeAssistantError(
                "You are not authorized to approve chores for this kid."
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
                "INFO: Chore '%s' approved for kid '%s' by parent '%s'. Points Awarded: %s",
                chore_name,
                kid_name,
                parent_name,
                points_awarded,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError as e:
            const.LOGGER.info("ERROR: Approve Chore: %s", e)
            raise
        except Exception as e:
            const.LOGGER.error(
                "ERROR: Approve Chore: Failed to approve chore '%s' for kid '%s': %s",
                chore_name,
                kid_name,
                e,
            )
            raise HomeAssistantError(
                f"Failed to approve chore '{chore_name}' for kid '{kid_name}'."
            )

    async def handle_disapprove_chore(call: ServiceCall):
        """Handle disapproving a chore."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "WARNING: Disapprove Chore: %s", const.MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        parent_name = call.data[const.FIELD_PARENT_NAME]
        kid_name = call.data[const.FIELD_KID_NAME]
        chore_name = call.data[const.FIELD_CHORE_NAME]

        # Map kid_name and chore_name to internal_ids
        kid_id = kh.get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            const.LOGGER.warning(
                "WARNING: Disapprove Chore: Kid '%s' not found", kid_name
            )
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        chore_id = kh.get_chore_id_by_name(coordinator, chore_name)
        if not chore_id:
            const.LOGGER.warning(
                "WARNING: Disapprove Chore: Chore '%s' not found", chore_name
            )
            raise HomeAssistantError(f"Chore '{chore_name}' not found")

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            const.LOGGER.warning("WARNING: Disapprove Chore: User not authorized")
            raise HomeAssistantError(
                "You are not authorized to disapprove chores for this kid."
            )

        # Disapprove the chore
        coordinator.disapprove_chore(
            parent_name=parent_name,
            kid_id=kid_id,
            chore_id=chore_id,
        )
        const.LOGGER.info(
            "INFO: Chore '%s' disapproved for kid '%s' by parent '%s'",
            chore_name,
            kid_name,
            parent_name,
        )
        await coordinator.async_request_refresh()

    async def handle_redeem_reward(call: ServiceCall):
        """Handle redeeming a reward (claiming without deduction)."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning("WARNING: Redeem Reward: %s", const.MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        parent_name = call.data[const.FIELD_PARENT_NAME]
        kid_name = call.data[const.FIELD_KID_NAME]
        reward_name = call.data[const.FIELD_REWARD_NAME]

        # Map kid_name and reward_name to internal_ids
        kid_id = kh.get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            const.LOGGER.warning("WARNING: Redeem Reward: Kid '%s' not found", kid_name)
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        reward_id = kh.get_reward_id_by_name(coordinator, reward_name)
        if not reward_id:
            const.LOGGER.warning(
                "WARNING: Redeem Reward: Reward '%s' not found", reward_name
            )
            raise HomeAssistantError(f"Reward '{reward_name}' not found")

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_kid(hass, user_id, kid_id):
            const.LOGGER.warning("WARNING: Redeem Reward: User not authorized")
            raise HomeAssistantError(
                "You are not authorized to redeem rewards for this kid."
            )

        # Check if kid has enough points
        kid_info = coordinator.kids_data.get(kid_id)
        reward = coordinator.rewards_data.get(reward_id)
        if not kid_info or not reward:
            const.LOGGER.warning("WARNING: Redeem Reward: Invalid kid or reward")
            raise HomeAssistantError("Invalid kid or reward")

        if kid_info[const.DATA_KID_POINTS] < reward.get(
            const.DATA_REWARD_COST, const.DEFAULT_ZERO
        ):
            const.LOGGER.warning(
                "WARNING: Redeem Reward: Kid '%s' does not have enough points to redeem reward '%s'",
                kid_name,
                reward_name,
            )
            raise HomeAssistantError(
                f"Kid '{kid_name}' does not have enough points to redeem '{reward_name}'."
            )

        # Process reward claim without deduction
        try:
            coordinator.redeem_reward(
                parent_name=parent_name, kid_id=kid_id, reward_id=reward_id
            )
            const.LOGGER.info(
                "INFO: Reward '%s' claimed by kid '%s' and pending approval by parent '%s'",
                reward_name,
                kid_name,
                parent_name,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError as e:
            const.LOGGER.info("ERROR: Redeem Reward: %s", e)
            raise
        except Exception as e:
            const.LOGGER.error(
                "ERROR: Redeem Reward: Failed to claim reward '%s' for kid '%s': %s",
                reward_name,
                kid_name,
                e,
            )
            raise HomeAssistantError(
                f"Failed to claim reward '{reward_name}' for kid '{kid_name}'."
            )

    async def handle_approve_reward(call: ServiceCall):
        """Handle approving a reward claimed by a kid."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "WARNING: Approve Reward: %s", const.MSG_NO_ENTRY_FOUND
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
        kid_id = kh.get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            const.LOGGER.warning(
                "WARNING: Approve Reward: Kid '%s' not found", kid_name
            )
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        reward_id = kh.get_reward_id_by_name(coordinator, reward_name)
        if not reward_id:
            const.LOGGER.warning(
                "WARNING: Approve Reward: Reward '%s' not found", reward_name
            )
            raise HomeAssistantError(f"Reward '{reward_name}' not found")

        # Check if user is authorized
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            const.LOGGER.warning("WARNING: Approve Reward: User not authorized")
            raise HomeAssistantError(
                "You are not authorized to approve rewards for this kid."
            )

        # Approve reward redemption and deduct points
        try:
            coordinator.approve_reward(
                parent_name=parent_name, kid_id=kid_id, reward_id=reward_id
            )
            const.LOGGER.info(
                "INFO: Reward '%s' approved for kid '%s' by parent '%s'",
                reward_name,
                kid_name,
                parent_name,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError as e:
            const.LOGGER.info("ERROR: Approve Reward: %s", e)
            raise
        except Exception as e:
            const.LOGGER.error(
                "ERROR: Approve Reward: Failed to approve reward '%s' for kid '%s': %s",
                reward_name,
                kid_name,
                e,
            )
            raise HomeAssistantError(
                f"Failed to approve reward '{reward_name}' for kid '{kid_name}'."
            )

    async def handle_disapprove_reward(call: ServiceCall):
        """Handle disapproving a reward."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "WARNING: Disapprove Reward: %s", const.MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        parent_name = call.data[const.FIELD_PARENT_NAME]
        kid_name = call.data[const.FIELD_KID_NAME]
        reward_name = call.data[const.FIELD_REWARD_NAME]

        # Map kid_name and reward_name to internal_ids
        kid_id = kh.get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            const.LOGGER.warning(
                "WARNING: Disapprove Reward: Kid '%s' not found", kid_name
            )
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        reward_id = kh.get_reward_id_by_name(coordinator, reward_name)
        if not reward_id:
            const.LOGGER.warning(
                "Disapprove Reward: Reward '%s' not found", reward_name
            )
            raise HomeAssistantError(f"Reward '{reward_name}' not found")

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            const.LOGGER.warning("WARNING: Disapprove Reward: User not authorized")
            raise HomeAssistantError(
                "You are not authorized to disapprove rewards for this kid."
            )

        # Disapprove the reward
        coordinator.disapprove_reward(
            parent_name=parent_name,
            kid_id=kid_id,
            reward_id=reward_id,
        )
        const.LOGGER.info(
            "INFO: Reward '%s' disapproved for kid '%s' by parent '%s'",
            reward_name,
            kid_name,
            parent_name,
        )
        await coordinator.async_request_refresh()

    async def handle_apply_penalty(call: ServiceCall):
        """Handle applying a penalty."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning("WARNING: Apply Penalty: %s", const.MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        parent_name = call.data[const.FIELD_PARENT_NAME]
        kid_name = call.data[const.FIELD_KID_NAME]
        penalty_name = call.data[const.FIELD_PENALTY_NAME]

        # Map kid_name and penalty_name to internal_ids
        kid_id = kh.get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            const.LOGGER.warning("WARNING: Apply Penalty: Kid '%s' not found", kid_name)
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        penalty_id = kh.get_penalty_id_by_name(coordinator, penalty_name)
        if not penalty_id:
            const.LOGGER.warning(
                "WARNING: Apply Penalty: Penalty '%s' not found", penalty_name
            )
            raise HomeAssistantError(f"Penalty '{penalty_name}' not found")

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            const.LOGGER.warning("WARNING: Apply Penalty: User not authorized")
            raise HomeAssistantError(
                "You are not authorized to apply penalties for this kid."
            )

        # Apply penalty
        try:
            coordinator.apply_penalty(
                parent_name=parent_name, kid_id=kid_id, penalty_id=penalty_id
            )
            const.LOGGER.info(
                "INFO: Penalty '%s' applied for kid '%s' by parent '%s'",
                penalty_name,
                kid_name,
                parent_name,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError as e:
            const.LOGGER.info("ERROR: Apply Penalty: %s", e)
            raise
        except Exception as e:
            const.LOGGER.error(
                "ERROR: Apply Penalty: Failed to apply penalty '%s' for kid '%s': %s",
                penalty_name,
                kid_name,
                e,
            )
            raise HomeAssistantError(
                f"Failed to apply penalty '{penalty_name}' for kid '{kid_name}'."
            )

    async def handle_reset_penalties(call: ServiceCall):
        """Handle resetting penalties."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "WARNING: Reset Penalties: %s", const.MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]

        kid_name = call.data.get(const.FIELD_KID_NAME)
        penalty_name = call.data.get(const.FIELD_PENALTY_NAME)

        kid_id = kh.get_kid_id_by_name(coordinator, kid_name) if kid_name else None
        penalty_id = (
            kh.get_penalty_id_by_name(coordinator, penalty_name)
            if penalty_name
            else None
        )

        if kid_name and not kid_id:
            const.LOGGER.warning(
                "WARNING: Reset Penalties: Kid '%s' not found.", kid_name
            )
            raise HomeAssistantError(f"Kid '{kid_name}' not found.")

        if penalty_name and not penalty_id:
            const.LOGGER.warning(
                "WARNING: Reset Penalties: Penalty '%s' not found.", penalty_name
            )
            raise HomeAssistantError(f"Penalty '{penalty_name}' not found.")

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            const.LOGGER.warning("WARNING: Reset Penalties: User not authorized.")
            raise HomeAssistantError("You are not authorized to reset penalties.")

        # Log action based on parameters provided
        if kid_id is None and penalty_id is None:
            const.LOGGER.info("INFO: Resetting all penalties for all kids.")
        elif kid_id is None:
            const.LOGGER.info(
                "INFO: Resetting penalty '%s' for all kids.", penalty_name
            )
        elif penalty_id is None:
            const.LOGGER.info("INFO: Resetting all penalties for kid '%s'.", kid_name)
        else:
            const.LOGGER.info(
                "INFO: Resetting penalty '%s' for kid '%s'.", penalty_name, kid_name
            )

        # Reset penalties
        coordinator.reset_penalties(kid_id=kid_id, penalty_id=penalty_id)
        await coordinator.async_request_refresh()

    async def handle_reset_bonuses(call: ServiceCall):
        """Handle resetting bonuses."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning("WARNING: Reset Bonuses: %s", const.MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]

        kid_name = call.data.get(const.FIELD_KID_NAME)
        bonus_name = call.data.get(const.FIELD_BONUS_NAME)

        kid_id = kh.get_kid_id_by_name(coordinator, kid_name) if kid_name else None
        bonus_id = (
            kh.get_bonus_id_by_name(coordinator, bonus_name) if bonus_name else None
        )

        if kid_name and not kid_id:
            const.LOGGER.warning(
                "WARNING: Reset Bonuses: Kid '%s' not found.", kid_name
            )
            raise HomeAssistantError(f"Kid '{kid_name}' not found.")

        if bonus_name and not bonus_id:
            const.LOGGER.warning(
                "WARNING: Reset Bonuses: Bonus '%s' not found.", bonus_name
            )
            raise HomeAssistantError(f"Bonus '{bonus_name}' not found.")

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            const.LOGGER.warning("WARNING: Reset Bonuses: User not authorized.")
            raise HomeAssistantError("You are not authorized to reset bonuses.")

        # Log action based on parameters provided
        if kid_id is None and bonus_id is None:
            const.LOGGER.info("INFO: Resetting all bonuses for all kids.")
        elif kid_id is None:
            const.LOGGER.info("INFO: Resetting bonus '%s' for all kids.", bonus_name)
        elif bonus_id is None:
            const.LOGGER.info("INFO: Resetting all bonuses for kid '%s'.", kid_name)
        else:
            const.LOGGER.info(
                "INFO: Resetting bonus '%s' for kid '%s'.", bonus_name, kid_name
            )

        # Reset bonuses
        coordinator.reset_bonuses(kid_id=kid_id, bonus_id=bonus_id)
        await coordinator.async_request_refresh()

    async def handle_reset_rewards(call: ServiceCall):
        """Handle resetting rewards counts."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning("WARNING: Reset Rewards: %s", const.MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]

        kid_name = call.data.get(const.FIELD_KID_NAME)
        reward_name = call.data.get(const.FIELD_REWARD_NAME)

        kid_id = kh.get_kid_id_by_name(coordinator, kid_name) if kid_name else None
        reward_id = (
            kh.get_reward_id_by_name(coordinator, reward_name) if reward_name else None
        )

        if kid_name and not kid_id:
            const.LOGGER.warning(
                "WARNING: Reset Rewards: Kid '%s' not found.", kid_name
            )
            raise HomeAssistantError(f"Kid '{kid_name}' not found.")

        if reward_name and not reward_id:
            const.LOGGER.warning(
                "WARNING: Reset Rewards: Reward '%s' not found.", reward_name
            )
            raise HomeAssistantError(f"Reward '{reward_name}' not found.")

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            const.LOGGER.warning("WARNING: Reset Rewards: User not authorized.")
            raise HomeAssistantError("You are not authorized to reset rewards.")

        # Log action based on parameters provided
        if kid_id is None and reward_id is None:
            const.LOGGER.info("INFO: Resetting all rewards for all kids.")
        elif kid_id is None:
            const.LOGGER.info("INFO: Resetting reward '%s' for all kids.", reward_name)
        elif reward_id is None:
            const.LOGGER.info("INFO: Resetting all rewards for kid '%s'.", kid_name)
        else:
            const.LOGGER.info(
                "INFO: Resetting reward '%s' for kid '%s'.", reward_name, kid_name
            )

        # Reset rewards
        coordinator.reset_rewards(kid_id=kid_id, reward_id=reward_id)
        await coordinator.async_request_refresh()

    async def handle_apply_bonus(call: ServiceCall):
        """Handle applying a bonus."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning("WARNING: Apply Bonus: %s", const.MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        parent_name = call.data[const.FIELD_PARENT_NAME]
        kid_name = call.data[const.FIELD_KID_NAME]
        bonus_name = call.data[const.FIELD_BONUS_NAME]

        # Map kid_name and bonus_name to internal_ids
        kid_id = kh.get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            const.LOGGER.warning("WARNING: Apply Bonus: Kid '%s' not found", kid_name)
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        bonus_id = kh.get_bonus_id_by_name(coordinator, bonus_name)
        if not bonus_id:
            const.LOGGER.warning(
                "WARNING: Apply Bonus: Bonus '%s' not found", bonus_name
            )
            raise HomeAssistantError(f"Bonus '{bonus_name}' not found")

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await kh.is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            const.LOGGER.warning("WARNING: Apply Bonus: User not authorized")
            raise HomeAssistantError(
                "You are not authorized to apply bonuses for this kid."
            )

        # Apply bonus
        try:
            coordinator.apply_bonus(
                parent_name=parent_name, kid_id=kid_id, bonus_id=bonus_id
            )
            const.LOGGER.info(
                "INFO: Bonus '%s' applied for kid '%s' by parent '%s'",
                bonus_name,
                kid_name,
                parent_name,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError as e:
            const.LOGGER.info("ERROR: Apply Bonus: %s", e)
            raise
        except Exception as e:
            const.LOGGER.error(
                "ERROR: Apply Bonus: Failed to apply bonus '%s' for kid '%s': %s",
                bonus_name,
                kid_name,
                e,
            )
            raise HomeAssistantError(
                f"Failed to apply bonus '{bonus_name}' for kid '{kid_name}'."
            )

    async def handle_reset_all_data(call: ServiceCall):
        """Handle manually resetting ALL data in KidsChores."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning("WARNING: Reset All Data: No KidsChores entry found")
            return

        data = hass.data[const.DOMAIN].get(entry_id)
        if not data:
            const.LOGGER.warning("WARNING: Reset All Data: No coordinator data found")
            return

        coordinator: KidsChoresDataCoordinator = data[const.COORDINATOR]

        # Clear everything from storage
        await coordinator.storage_manager.async_clear_data()

        # Re-init the coordinator with reload config entry
        await hass.config_entries.async_reload(entry_id)

        coordinator.async_set_updated_data(coordinator._data)
        const.LOGGER.info(
            "INFO: Manually reset all KidsChores data. Integration is now cleared"
        )

    async def handle_reset_all_chores(call: ServiceCall):
        """Handle manually resetting all chores to pending, clearing claims/approvals."""

        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning("WARNING: Reset All Chores: No KidsChores entry found")
            return

        data = hass.data[const.DOMAIN].get(entry_id)
        if not data:
            const.LOGGER.warning("WARNING: Reset All Chores: No coordinator data found")
            return

        coordinator: KidsChoresDataCoordinator = data[const.COORDINATOR]

        # Loop over all chores, reset them to pending
        for chore_id, chore_info in coordinator.chores_data.items():
            chore_info[const.DATA_CHORE_STATE] = const.CHORE_STATE_PENDING

        # Remove all chore approvals/claims for each kid
        for kid_id, kid_info in coordinator.kids_data.items():
            kid_info[const.DATA_KID_CLAIMED_CHORES] = []
            kid_info[const.DATA_KID_APPROVED_CHORES] = []
            kid_info[const.DATA_KID_OVERDUE_CHORES] = []
            kid_info[const.DATA_KID_OVERDUE_NOTIFICATIONS] = {}

        # Clear the pending approvals queue
        coordinator._data[const.DATA_PENDING_CHORE_APPROVALS] = []

        # Persist & notify
        coordinator._persist()
        coordinator.async_set_updated_data(coordinator._data)
        const.LOGGER.info(
            "INFO: Manually reset all chores to pending, removed claims/approvals"
        )

    async def handle_reset_overdue_chores(call: ServiceCall) -> None:
        """Handle resetting overdue chores."""

        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "WARNING: Reset Overdue Chores: %s", const.MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]

        # Get parameters
        chore_id = call.data.get(const.FIELD_CHORE_ID)
        chore_name = call.data.get(const.FIELD_CHORE_NAME)
        kid_name = call.data.get(const.FIELD_KID_NAME)

        # If chore_id not provided but chore_name is, map it to chore_id.
        if not chore_id and chore_name:
            chore_id = kh.get_chore_id_by_name(coordinator, chore_name)

            if not chore_id:
                const.LOGGER.warning(
                    "WARNING: Reset Overdue Chores: Chore '%s' not found", chore_name
                )
                raise HomeAssistantError(f"Chore '{chore_name}' not found.")

        # If kid_name provided, map it to kid_id.
        kid_id: Optional[str] = None
        if kid_name:
            kid_id = kh.get_kid_id_by_name(coordinator, kid_name)

            if not kid_id:
                const.LOGGER.warning(
                    "WARNING: Reset Overdue Chores: Kid '%s' not found", kid_name
                )
                raise HomeAssistantError(f"Kid '{kid_name}' not found.")

        coordinator.reset_overdue_chores(chore_id=chore_id, kid_id=kid_id)

        const.LOGGER.info(
            "INFO: Reset overdue chores (chore_id=%s, kid_id=%s)", chore_id, kid_id
        )

        await coordinator.async_request_refresh()
        await coordinator._check_overdue_chores()

    async def handle_set_chore_due_date(call: ServiceCall):
        """Handle setting (or clearing) the due date of a chore."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "WARNING: Set Chore Due Date: %s", const.MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]
        chore_name = call.data[const.FIELD_CHORE_NAME]
        due_date_input = call.data.get(const.FIELD_DUE_DATE)

        # Look up the chore by name:
        chore_id = kh.get_chore_id_by_name(coordinator, chore_name)
        if not chore_id:
            const.LOGGER.warning(
                "WARNING: Set Chore Due Date: Chore '%s' not found", chore_name
            )
            raise HomeAssistantError(const.ERROR_CHORE_NOT_FOUND_FMT.format(chore_name))

        if due_date_input:
            try:
                # Convert the provided date
                due_date_str = fh.ensure_utc_datetime(hass, due_date_input)
                due_dt = dt_util.parse_datetime(due_date_str)
                if due_dt and due_dt < dt_util.utcnow():
                    raise HomeAssistantError("Due date cannot be set in the past.")

            except Exception as err:
                const.LOGGER.error(
                    "ERROR: Set Chore Due Date: Invalid due date '%s': %s",
                    due_date_input,
                    err,
                )
                raise HomeAssistantError("Invalid due date provided.")

            # Update the chore’s due_date:
            coordinator.set_chore_due_date(chore_id, due_dt)
            const.LOGGER.info(
                "INFO: Set due date for chore '%s' (ID: %s) to %s",
                chore_name,
                chore_id,
                due_date_str,
            )
        else:
            # Clear the due date by setting it to None
            coordinator.set_chore_due_date(chore_id, None)
            const.LOGGER.info(
                "INFO: Cleared due date for chore '%s' (ID: %s)", chore_name, chore_id
            )

        await coordinator.async_request_refresh()

    async def handle_skip_chore_due_date(call: ServiceCall) -> None:
        """Handle skipping the due date on a chore by rescheduling it to the next due date."""
        entry_id = kh.get_first_kidschores_entry(hass)
        if not entry_id:
            const.LOGGER.warning(
                "WARNING: Skip Chore Due Date: %s", const.MSG_NO_ENTRY_FOUND
            )
            return

        coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry_id][
            const.COORDINATOR
        ]

        # Get parameters: either chore_id or chore_name must be provided.
        chore_id = call.data.get(const.FIELD_CHORE_ID)
        chore_name = call.data.get(const.FIELD_CHORE_NAME)

        if not chore_id and chore_name:
            chore_id = kh.get_chore_id_by_name(coordinator, chore_name)
            if not chore_id:
                const.LOGGER.warning(
                    "WARNING: Skip Chore Due Date: Chore '%s' not found", chore_name
                )
                raise HomeAssistantError(f"Chore '{chore_name}' not found.")

        if not chore_id:
            raise HomeAssistantError(
                "You must provide either a chore_id or chore_name."
            )

        coordinator.skip_chore_due_date(chore_id)
        const.LOGGER.info("INFO: Skipped due date for chore (chore_id=%s)", chore_id)
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

    const.LOGGER.info("INFO: KidsChores services have been registered successfully")


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
        const.SERVICE_SET_CHORE_DUE_DATE,
        const.SERVICE_SKIP_CHORE_DUE_DATE,
    ]

    for service in services:
        if hass.services.has_service(const.DOMAIN, service):
            hass.services.async_remove(const.DOMAIN, service)

    const.LOGGER.info("INFO: KidsChores services have been unregistered")
