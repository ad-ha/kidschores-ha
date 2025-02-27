# File: services.py
"""Defines custom services for the KidsChores integration.

These services allow direct actions through scripts or automations.
Includes UI editor support with selectors for dropdowns and text inputs.
"""

import asyncio
import voluptuous as vol

from typing import Optional
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    CHORE_STATE_OVERDUE,
    CHORE_STATE_PENDING,
    DATA_CHORES,
    DATA_PENDING_CHORE_APPROVALS,
    DOMAIN,
    ERROR_CHORE_NOT_FOUND_FMT,
    ERROR_KID_NOT_FOUND_FMT,
    ERROR_NOT_AUTHORIZED_FMT,
    FIELD_CHORE_ID,
    FIELD_CHORE_NAME,
    FIELD_KID_NAME,
    FIELD_PARENT_NAME,
    FIELD_PENALTY_NAME,
    FIELD_POINTS_AWARDED,
    FIELD_REWARD_NAME,
    FIELD_BONUS_NAME,
    LOGGER,
    MSG_NO_ENTRY_FOUND,
    SERVICE_APPLY_PENALTY,
    SERVICE_APPLY_BONUS,
    SERVICE_APPROVE_CHORE,
    SERVICE_APPROVE_REWARD,
    SERVICE_CLAIM_CHORE,
    SERVICE_DISAPPROVE_CHORE,
    SERVICE_DISAPPROVE_REWARD,
    SERVICE_REDEEM_REWARD,
    SERVICE_RESET_ALL_CHORES,
    SERVICE_RESET_ALL_DATA,
    SERVICE_RESET_OVERDUE_CHORES,
    SERVICE_SET_CHORE_DUE_DATE,
    SERVICE_SKIP_CHORE_DUE_DATE,
)
from .coordinator import KidsChoresDataCoordinator
from .kc_helpers import is_user_authorized_for_global_action, is_user_authorized_for_kid
from .flow_helpers import ensure_utc_datetime


# --- Service Schemas ---
CLAIM_CHORE_SCHEMA = vol.Schema(
    {
        vol.Required(FIELD_KID_NAME): cv.string,
        vol.Required(FIELD_CHORE_NAME): cv.string,
    }
)

APPROVE_CHORE_SCHEMA = vol.Schema(
    {
        vol.Required(FIELD_PARENT_NAME): cv.string,
        vol.Required(FIELD_KID_NAME): cv.string,
        vol.Required(FIELD_CHORE_NAME): cv.string,
        vol.Optional(FIELD_POINTS_AWARDED): vol.Coerce(float),
    }
)

DISAPPROVE_CHORE_SCHEMA = vol.Schema(
    {
        vol.Required(FIELD_PARENT_NAME): cv.string,
        vol.Required(FIELD_KID_NAME): cv.string,
        vol.Required(FIELD_CHORE_NAME): cv.string,
    }
)

REDEEM_REWARD_SCHEMA = vol.Schema(
    {
        vol.Required(FIELD_PARENT_NAME): cv.string,
        vol.Required(FIELD_KID_NAME): cv.string,
        vol.Required(FIELD_REWARD_NAME): cv.string,
    }
)

APPROVE_REWARD_SCHEMA = vol.Schema(
    {
        vol.Required(FIELD_PARENT_NAME): cv.string,
        vol.Required(FIELD_KID_NAME): cv.string,
        vol.Required(FIELD_REWARD_NAME): cv.string,
    }
)

DISAPPROVE_REWARD_SCHEMA = vol.Schema(
    {
        vol.Required(FIELD_PARENT_NAME): cv.string,
        vol.Required(FIELD_KID_NAME): cv.string,
        vol.Required(FIELD_REWARD_NAME): cv.string,
    }
)

APPLY_PENALTY_SCHEMA = vol.Schema(
    {
        vol.Required(FIELD_PARENT_NAME): cv.string,
        vol.Required(FIELD_KID_NAME): cv.string,
        vol.Required(FIELD_PENALTY_NAME): cv.string,
    }
)

APPLY_BONUS_SCHEMA = vol.Schema(
    {
        vol.Required(FIELD_PARENT_NAME): cv.string,
        vol.Required(FIELD_KID_NAME): cv.string,
        vol.Required(FIELD_BONUS_NAME): cv.string,
    }
)

RESET_OVERDUE_CHORES_SCHEMA = vol.Schema(
    {
        vol.Optional(FIELD_CHORE_ID): cv.string,
        vol.Optional(FIELD_CHORE_NAME): cv.string,
        vol.Optional(FIELD_KID_NAME): cv.string,
    }
)

RESET_ALL_DATA_SCHEMA = vol.Schema({})

RESET_ALL_CHORES_SCHEMA = vol.Schema({})

SET_CHORE_DUE_DATE_SCHEMA = vol.Schema(
    {
        vol.Required("chore_name"): cv.string,
        vol.Optional("due_date"): vol.Any(cv.string, None),
    }
)

SKIP_CHORE_DUE_DATE_SCHEMA = vol.Schema(
    {
        vol.Optional("chore_id"): cv.string,
        vol.Optional("chore_name"): cv.string,
    }
)


def async_setup_services(hass: HomeAssistant):
    """Register KidsChores services."""

    async def handle_claim_chore(call: ServiceCall):
        """Handle claiming a chore."""
        entry_id = _get_first_kidschores_entry(hass)
        if not entry_id:
            LOGGER.warning("Claim Chore: %s", MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[DOMAIN][entry_id][
            "coordinator"
        ]
        user_id = call.context.user_id
        kid_name = call.data[FIELD_KID_NAME]
        chore_name = call.data[FIELD_CHORE_NAME]

        # Map kid_name and chore_name to internal_ids
        kid_id = _get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            LOGGER.warning("Claim Chore: " + ERROR_KID_NOT_FOUND_FMT, kid_name)
            raise HomeAssistantError(ERROR_KID_NOT_FOUND_FMT.format(kid_name))

        chore_id = _get_chore_id_by_name(coordinator, chore_name)
        if not chore_id:
            LOGGER.warning("Claim Chore: " + ERROR_CHORE_NOT_FOUND_FMT, chore_name)
            raise HomeAssistantError(ERROR_CHORE_NOT_FOUND_FMT.format(chore_name))

        # Check if user is authorized
        if user_id and not await is_user_authorized_for_kid(hass, user_id, kid_id):
            LOGGER.warning("Claim Chore: %s", ERROR_NOT_AUTHORIZED_FMT)
            raise HomeAssistantError(ERROR_NOT_AUTHORIZED_FMT.format("claim chores"))

        # Process chore claim
        coordinator.claim_chore(
            kid_id=kid_id, chore_id=chore_id, user_name=f"user:{user_id}"
        )

        LOGGER.info(
            "Chore '%s' claimed by kid '%s' by user '%s'",
            chore_name,
            kid_name,
            user_id,
        )
        await coordinator.async_request_refresh()

    async def handle_approve_chore(call: ServiceCall):
        """Handle approving a claimed chore."""
        entry_id = _get_first_kidschores_entry(hass)

        if not entry_id:
            LOGGER.warning("Approve Chore: %s", MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[DOMAIN][entry_id][
            "coordinator"
        ]
        user_id = call.context.user_id
        parent_name = call.data[FIELD_PARENT_NAME]
        kid_name = call.data[FIELD_KID_NAME]
        chore_name = call.data[FIELD_CHORE_NAME]
        points_awarded = call.data.get(FIELD_POINTS_AWARDED)

        # Map kid_name and chore_name to internal_ids
        kid_id = _get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            LOGGER.warning("Approve Chore: Kid '%s' not found", kid_name)
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        chore_id = _get_chore_id_by_name(coordinator, chore_name)
        if not chore_id:
            LOGGER.warning("Approve Chore: Chore '%s' not found", chore_name)
            raise HomeAssistantError(f"Chore '{chore_name}' not found")

        # Check if user is authorized
        if user_id and not await is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            LOGGER.warning("Approve Chore: User not authorized")
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
            LOGGER.info(
                "Chore '%s' approved for kid '%s' by parent '%s'. Points Awarded: %s",
                chore_name,
                kid_name,
                parent_name,
                points_awarded,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError as e:
            LOGGER.error("Approve Chore: %s", e)
            raise
        except Exception as e:
            LOGGER.error(
                "Approve Chore: Failed to approve chore '%s' for kid '%s': %s",
                chore_name,
                kid_name,
                e,
            )
            raise HomeAssistantError(
                f"Failed to approve chore '{chore_name}' for kid '{kid_name}'."
            )

    async def handle_disapprove_chore(call: ServiceCall):
        """Handle disapproving a chore."""
        entry_id = _get_first_kidschores_entry(hass)
        if not entry_id:
            LOGGER.warning("Disapprove Chore: %s", MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[DOMAIN][entry_id][
            "coordinator"
        ]
        parent_name = call.data[FIELD_PARENT_NAME]
        kid_name = call.data[FIELD_KID_NAME]
        chore_name = call.data[FIELD_CHORE_NAME]

        # Map kid_name and chore_name to internal_ids
        kid_id = _get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            LOGGER.warning("Disapprove Chore: Kid '%s' not found", kid_name)
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        chore_id = _get_chore_id_by_name(coordinator, chore_name)
        if not chore_id:
            LOGGER.warning("Disapprove Chore: Chore '%s' not found", chore_name)
            raise HomeAssistantError(f"Chore '{chore_name}' not found")

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            LOGGER.warning("Disapprove Chore: User not authorized")
            raise HomeAssistantError(
                "You are not authorized to disapprove chores for this kid."
            )

        # Disapprove the chore
        coordinator.disapprove_chore(
            parent_name=parent_name,
            kid_id=kid_id,
            chore_id=chore_id,
        )
        LOGGER.info(
            "Chore '%s' disapproved for kid '%s' by parent '%s'",
            chore_name,
            kid_name,
            parent_name,
        )
        await coordinator.async_request_refresh()

    async def handle_redeem_reward(call: ServiceCall):
        """Handle redeeming a reward (claiming without deduction)."""
        entry_id = _get_first_kidschores_entry(hass)
        if not entry_id:
            LOGGER.warning("Redeem Reward: %s", MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[DOMAIN][entry_id][
            "coordinator"
        ]
        parent_name = call.data[FIELD_PARENT_NAME]
        kid_name = call.data[FIELD_KID_NAME]
        reward_name = call.data[FIELD_REWARD_NAME]

        # Map kid_name and reward_name to internal_ids
        kid_id = _get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            LOGGER.warning("Redeem Reward: Kid '%s' not found", kid_name)
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        reward_id = _get_reward_id_by_name(coordinator, reward_name)
        if not reward_id:
            LOGGER.warning("Redeem Reward: Reward '%s' not found", reward_name)
            raise HomeAssistantError(f"Reward '{reward_name}' not found")

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await is_user_authorized_for_kid(hass, user_id, kid_id):
            LOGGER.warning("Redeem Reward: User not authorized")
            raise HomeAssistantError(
                "You are not authorized to redeem rewards for this kid."
            )

        # Check if kid has enough points
        kid_info = coordinator.kids_data.get(kid_id)
        reward = coordinator.rewards_data.get(reward_id)
        if not kid_info or not reward:
            LOGGER.warning("Redeem Reward: Invalid kid or reward")
            raise HomeAssistantError("Invalid kid or reward")

        if kid_info["points"] < reward.get("cost", 0):
            LOGGER.warning(
                "Redeem Reward: Kid '%s' does not have enough points to redeem reward '%s'",
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
            LOGGER.info(
                "Reward '%s' claimed by kid '%s' and pending approval by parent '%s'",
                reward_name,
                kid_name,
                parent_name,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError as e:
            LOGGER.error("Redeem Reward: %s", e)
            raise
        except Exception as e:
            LOGGER.error(
                "Redeem Reward: Failed to claim reward '%s' for kid '%s': %s",
                reward_name,
                kid_name,
                e,
            )
            raise HomeAssistantError(
                f"Failed to claim reward '{reward_name}' for kid '{kid_name}'."
            )

    async def handle_approve_reward(call: ServiceCall):
        """Handle approving a reward claimed by a kid."""
        entry_id = _get_first_kidschores_entry(hass)
        if not entry_id:
            LOGGER.warning("Approve Reward: %s", MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[DOMAIN][entry_id][
            "coordinator"
        ]
        user_id = call.context.user_id
        parent_name = call.data[FIELD_PARENT_NAME]
        kid_name = call.data[FIELD_KID_NAME]
        reward_name = call.data[FIELD_REWARD_NAME]

        # Map kid_name and reward_name to internal_ids
        kid_id = _get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            LOGGER.warning("Approve Reward: Kid '%s' not found", kid_name)
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        reward_id = _get_reward_id_by_name(coordinator, reward_name)
        if not reward_id:
            LOGGER.warning("Approve Reward: Reward '%s' not found", reward_name)
            raise HomeAssistantError(f"Reward '{reward_name}' not found")

        # Check if user is authorized
        if user_id and not await is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            LOGGER.warning("Approve Reward: User not authorized")
            raise HomeAssistantError(
                "You are not authorized to approve rewards for this kid."
            )

        # Approve reward redemption and deduct points
        try:
            coordinator.approve_reward(
                parent_name=parent_name, kid_id=kid_id, reward_id=reward_id
            )
            LOGGER.info(
                "Reward '%s' approved for kid '%s' by parent '%s'",
                reward_name,
                kid_name,
                parent_name,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError as e:
            LOGGER.error("Approve Reward: %s", e)
            raise
        except Exception as e:
            LOGGER.error(
                "Approve Reward: Failed to approve reward '%s' for kid '%s': %s",
                reward_name,
                kid_name,
                e,
            )
            raise HomeAssistantError(
                f"Failed to approve reward '{reward_name}' for kid '{kid_name}'."
            )

    async def handle_disapprove_reward(call: ServiceCall):
        """Handle disapproving a reward."""
        entry_id = _get_first_kidschores_entry(hass)
        if not entry_id:
            LOGGER.warning("Disapprove Reward: %s", MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[DOMAIN][entry_id][
            "coordinator"
        ]
        parent_name = call.data[FIELD_PARENT_NAME]
        kid_name = call.data[FIELD_KID_NAME]
        reward_name = call.data[FIELD_REWARD_NAME]

        # Map kid_name and reward_name to internal_ids
        kid_id = _get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            LOGGER.warning("Disapprove Reward: Kid '%s' not found", kid_name)
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        reward_id = _get_reward_id_by_name(coordinator, reward_name)
        if not reward_id:
            LOGGER.warning("Disapprove Reward: Reward '%s' not found", reward_name)
            raise HomeAssistantError(f"Reward '{reward_name}' not found")

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            LOGGER.warning("Disapprove Reward: User not authorized")
            raise HomeAssistantError(
                "You are not authorized to disapprove rewards for this kid."
            )

        # Disapprove the reward
        coordinator.disapprove_reward(
            parent_name=parent_name,
            kid_id=kid_id,
            reward_id=reward_id,
        )
        LOGGER.info(
            "Reward '%s' disapproved for kid '%s' by parent '%s'",
            reward_name,
            kid_name,
            parent_name,
        )
        await coordinator.async_request_refresh()

    async def handle_apply_penalty(call: ServiceCall):
        """Handle applying a penalty."""
        entry_id = _get_first_kidschores_entry(hass)
        if not entry_id:
            LOGGER.warning("Apply Penalty: %s", MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[DOMAIN][entry_id][
            "coordinator"
        ]
        parent_name = call.data[FIELD_PARENT_NAME]
        kid_name = call.data[FIELD_KID_NAME]
        penalty_name = call.data[FIELD_PENALTY_NAME]

        # Map kid_name and penalty_name to internal_ids
        kid_id = _get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            LOGGER.warning("Apply Penalty: Kid '%s' not found", kid_name)
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        penalty_id = _get_penalty_id_by_name(coordinator, penalty_name)
        if not penalty_id:
            LOGGER.warning("Apply Penalty: Penalty '%s' not found", penalty_name)
            raise HomeAssistantError(f"Penalty '{penalty_name}' not found")

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            LOGGER.warning("Apply Penalty: User not authorized")
            raise HomeAssistantError(
                "You are not authorized to apply penalties for this kid."
            )

        # Apply penalty
        try:
            coordinator.apply_penalty(
                parent_name=parent_name, kid_id=kid_id, penalty_id=penalty_id
            )
            LOGGER.info(
                "Penalty '%s' applied for kid '%s' by parent '%s'",
                penalty_name,
                kid_name,
                parent_name,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError as e:
            LOGGER.error("Apply Penalty: %s", e)
            raise
        except Exception as e:
            LOGGER.error(
                "Apply Penalty: Failed to apply penalty '%s' for kid '%s': %s",
                penalty_name,
                kid_name,
                e,
            )
            raise HomeAssistantError(
                f"Failed to apply penalty '{penalty_name}' for kid '{kid_name}'."
            )

    async def handle_apply_bonus(call: ServiceCall):
        """Handle applying a bonus."""
        entry_id = _get_first_kidschores_entry(hass)
        if not entry_id:
            LOGGER.warning("Apply Bonus: %s", MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[DOMAIN][entry_id][
            "coordinator"
        ]
        parent_name = call.data[FIELD_PARENT_NAME]
        kid_name = call.data[FIELD_KID_NAME]
        bonus_name = call.data[FIELD_BONUS_NAME]

        # Map kid_name and bonus_name to internal_ids
        kid_id = _get_kid_id_by_name(coordinator, kid_name)
        if not kid_id:
            LOGGER.warning("Apply Bonus: Kid '%s' not found", kid_name)
            raise HomeAssistantError(f"Kid '{kid_name}' not found")

        bonus_id = _get_bonus_id_by_name(coordinator, bonus_name)
        if not bonus_id:
            LOGGER.warning("Apply Bonus: Bonus '%s' not found", bonus_name)
            raise HomeAssistantError(f"Bonus '{bonus_name}' not found")

        # Check if user is authorized
        user_id = call.context.user_id
        if user_id and not await is_user_authorized_for_global_action(
            hass, user_id, kid_id
        ):
            LOGGER.warning("Apply Bonus: User not authorized")
            raise HomeAssistantError(
                "You are not authorized to apply bonuses for this kid."
            )

        # Apply bonus
        try:
            coordinator.apply_bonus(
                parent_name=parent_name, kid_id=kid_id, bonus_id=bonus_id
            )
            LOGGER.info(
                "Bonus '%s' applied for kid '%s' by parent '%s'",
                bonus_name,
                kid_name,
                parent_name,
            )
            await coordinator.async_request_refresh()
        except HomeAssistantError as e:
            LOGGER.error("Apply Bonus: %s", e)
            raise
        except Exception as e:
            LOGGER.error(
                "Apply Bonus: Failed to apply bonus '%s' for kid '%s': %s",
                bonus_name,
                kid_name,
                e,
            )
            raise HomeAssistantError(
                f"Failed to apply bonus '{bonus_name}' for kid '{kid_name}'."
            )

    async def handle_reset_all_data(call: ServiceCall):
        """Handle manually resetting ALL data in KidsChores."""
        entry_id = _get_first_kidschores_entry(hass)
        if not entry_id:
            LOGGER.warning("Reset All Data: No KidsChores entry found")
            return

        data = hass.data[DOMAIN].get(entry_id)
        if not data:
            LOGGER.warning("Reset All Data: No coordinator data found")
            return

        coordinator: KidsChoresDataCoordinator = data["coordinator"]

        # Clear everything from storage
        await coordinator.storage_manager.async_clear_data()

        # Re-init the coordinator with reload config entry
        await hass.config_entries.async_reload(entry_id)

        coordinator.async_set_updated_data(coordinator._data)
        LOGGER.info("Manually reset all KidsChores data. Integration is now cleared")

    async def handle_reset_all_chores(call: ServiceCall):
        """Handle manually resetting all chores to pending, clearing claims/approvals."""

        entry_id = _get_first_kidschores_entry(hass)
        if not entry_id:
            LOGGER.warning("Reset All Chores: No KidsChores entry found")
            return

        data = hass.data[DOMAIN].get(entry_id)
        if not data:
            LOGGER.warning("Reset All Chores: No coordinator data found")
            return

        coordinator: KidsChoresDataCoordinator = data["coordinator"]

        # Loop over all chores, reset them to pending
        for chore_id, chore_info in coordinator.chores_data.items():
            chore_info["state"] = CHORE_STATE_PENDING

        # Remove all chore approvals/claims for each kid
        for kid_id, kid_info in coordinator.kids_data.items():
            kid_info["claimed_chores"] = []
            kid_info["approved_chores"] = []
            kid_info["overdue_chores"] = []
            kid_info["overdue_notifications"] = {}

        # Clear the pending approvals queue
        coordinator._data[DATA_PENDING_CHORE_APPROVALS] = []

        # Persist & notify
        coordinator._persist()
        coordinator.async_set_updated_data(coordinator._data)
        LOGGER.info("Manually reset all chores to pending, removed claims/approvals")

    async def handle_reset_overdue_chores(call: ServiceCall) -> None:
        """Handle resetting overdue chores."""

        entry_id = _get_first_kidschores_entry(hass)
        if not entry_id:
            LOGGER.warning("Reset Overdue Chores: %s", MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[DOMAIN][entry_id][
            "coordinator"
        ]

        # Get parameters
        chore_id = call.data.get("chore_id")
        chore_name = call.data.get("chore_name")
        kid_name = call.data.get("kid_name")

        # If chore_id not provided but chore_name is, map it to chore_id.
        if not chore_id and chore_name:
            chore_id = _get_chore_id_by_name(coordinator, chore_name)
            if not chore_id:
                LOGGER.warning("Reset Overdue Chores: Chore '%s' not found", chore_name)
                raise HomeAssistantError(f"Chore '{chore_name}' not found.")

        # If kid_name provided, map it to kid_id.
        kid_id: Optional[str] = None
        if kid_name:
            kid_id = _get_kid_id_by_name(coordinator, kid_name)
            if not kid_id:
                LOGGER.warning("Reset Overdue Chores: Kid '%s' not found", kid_name)
                raise HomeAssistantError(f"Kid '{kid_name}' not found.")

        coordinator.reset_overdue_chores(chore_id=chore_id, kid_id=kid_id)
        LOGGER.info("Reset overdue chores (chore_id=%s, kid_id=%s)", chore_id, kid_id)
        await coordinator.async_request_refresh()

    async def handle_set_chore_due_date(call: ServiceCall):
        """Handle setting (or clearing) the due date of a chore."""
        entry_id = _get_first_kidschores_entry(hass)
        if not entry_id:
            LOGGER.warning("Set Chore Due Date: %s", MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[DOMAIN][entry_id][
            "coordinator"
        ]
        chore_name = call.data["chore_name"]
        due_date_input = call.data.get("due_date")

        # Look up the chore by name:
        chore_id = _get_chore_id_by_name(coordinator, chore_name)
        if not chore_id:
            LOGGER.warning("Set Chore Due Date: Chore '%s' not found", chore_name)
            raise HomeAssistantError(ERROR_CHORE_NOT_FOUND_FMT.format(chore_name))

        if due_date_input:
            try:
                # Convert the provided date
                due_date_str = ensure_utc_datetime(hass, due_date_input)
                due_dt = dt_util.parse_datetime(due_date_str)
                if due_dt and due_dt < dt_util.utcnow():
                    raise HomeAssistantError("Due date cannot be set in the past.")

            except Exception as err:
                LOGGER.error(
                    "Set Chore Due Date: Invalid due date '%s': %s", due_date_input, err
                )
                raise HomeAssistantError("Invalid due date provided.")

            # Update the chore’s due_date:
            coordinator.chores_data[chore_id]["due_date"] = due_date_str
            LOGGER.info(
                "Set due date for chore '%s' (ID: %s) to %s",
                chore_name,
                chore_id,
                due_date_str,
            )
        else:
            # Clear the due date by setting it to None
            coordinator.chores_data[chore_id]["due_date"] = None
            LOGGER.info(
                "Cleared due date for chore '%s' (ID: %s)", chore_name, chore_id
            )

        # Update the chore state if it is currently pending or overdue.
        current_state = coordinator.chores_data[chore_id].get(
            "state", CHORE_STATE_PENDING
        )
        if current_state in [CHORE_STATE_PENDING, CHORE_STATE_OVERDUE]:
            # If a new due date was provided and it's in the future, set state to pending.
            if due_date_input and due_dt and due_dt > dt_util.utcnow():
                coordinator.update_chore_state(chore_id, CHORE_STATE_PENDING)

            # If the due date was cleared, also set state to pending.
            elif not due_date_input:
                coordinator.update_chore_state(chore_id, CHORE_STATE_PENDING)

        # Update the config entry options with new due date
        updated_options = dict(coordinator.config_entry.options)

        chores_conf = dict(updated_options.get(DATA_CHORES, {}))

        existing_chore_options = dict(chores_conf.get(chore_id, {}))
        existing_chore_options["due_date"] = coordinator.chores_data[chore_id][
            "due_date"
        ]

        chores_conf[chore_id] = existing_chore_options
        updated_options[DATA_CHORES] = chores_conf

        new_data = dict(coordinator.config_entry.data)
        new_data["last_change"] = dt_util.utcnow().isoformat()

        coordinator.hass.config_entries.async_update_entry(
            coordinator.config_entry, data=new_data, options=updated_options
        )

        coordinator._persist()
        coordinator.async_set_updated_data(coordinator._data)
        await coordinator.async_request_refresh()

    async def handle_skip_chore_due_date(call: ServiceCall) -> None:
        """Handle skipping the due date on a chore by rescheduling it to the next due date."""
        entry_id = _get_first_kidschores_entry(hass)
        if not entry_id:
            LOGGER.warning("Skip Chore Due Date: %s", MSG_NO_ENTRY_FOUND)
            return

        coordinator: KidsChoresDataCoordinator = hass.data[DOMAIN][entry_id][
            "coordinator"
        ]

        # Get parameters: either chore_id or chore_name must be provided.
        chore_id = call.data.get("chore_id")
        chore_name = call.data.get("chore_name")

        if not chore_id and chore_name:
            chore_id = _get_chore_id_by_name(coordinator, chore_name)
            if not chore_id:
                LOGGER.warning("Skip Chore Due Date: Chore '%s' not found", chore_name)
                raise HomeAssistantError(f"Chore '{chore_name}' not found.")

        if not chore_id:
            raise HomeAssistantError(
                "You must provide either a chore_id or chore_name."
            )

        coordinator.skip_chore_due_date(chore_id)
        LOGGER.info("Skipped due date for chore (chore_id=%s)", chore_id)
        await coordinator.async_request_refresh()

    # --- Register Services ---
    hass.services.async_register(
        DOMAIN, SERVICE_CLAIM_CHORE, handle_claim_chore, schema=CLAIM_CHORE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_APPROVE_CHORE, handle_approve_chore, schema=APPROVE_CHORE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DISAPPROVE_CHORE,
        handle_disapprove_chore,
        schema=DISAPPROVE_CHORE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REDEEM_REWARD, handle_redeem_reward, schema=REDEEM_REWARD_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_APPROVE_REWARD,
        handle_approve_reward,
        schema=APPROVE_REWARD_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DISAPPROVE_REWARD,
        handle_disapprove_reward,
        schema=DISAPPROVE_REWARD_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_APPLY_PENALTY, handle_apply_penalty, schema=APPLY_PENALTY_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_ALL_DATA,
        handle_reset_all_data,
        schema=RESET_ALL_DATA_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_ALL_CHORES,
        handle_reset_all_chores,
        schema=RESET_ALL_CHORES_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_OVERDUE_CHORES,
        handle_reset_overdue_chores,
        schema=RESET_OVERDUE_CHORES_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CHORE_DUE_DATE,
        handle_set_chore_due_date,
        schema=SET_CHORE_DUE_DATE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SKIP_CHORE_DUE_DATE,
        handle_skip_chore_due_date,
        schema=SKIP_CHORE_DUE_DATE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN, SERVICE_APPLY_BONUS, handle_apply_bonus, schema=APPLY_BONUS_SCHEMA
    )

    LOGGER.info("KidsChores services have been registered successfully")


async def async_unload_services(hass: HomeAssistant):
    """Unregister KidsChores services when unloading the integration."""
    services = [
        SERVICE_CLAIM_CHORE,
        SERVICE_APPROVE_CHORE,
        SERVICE_DISAPPROVE_CHORE,
        SERVICE_REDEEM_REWARD,
        SERVICE_DISAPPROVE_REWARD,
        SERVICE_APPLY_PENALTY,
        SERVICE_APPLY_BONUS,
        SERVICE_APPROVE_REWARD,
        SERVICE_RESET_ALL_DATA,
        SERVICE_RESET_ALL_CHORES,
        SERVICE_RESET_OVERDUE_CHORES,
        SERVICE_SET_CHORE_DUE_DATE,
        SERVICE_SKIP_CHORE_DUE_DATE,
    ]

    for service in services:
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)

    LOGGER.info("KidsChores services have been unregistered")


def _get_first_kidschores_entry(hass: HomeAssistant) -> Optional[str]:
    """Retrieve the first KidsChores config entry ID."""
    domain_entries = hass.data.get(DOMAIN)
    if not domain_entries:
        return None
    return next(iter(domain_entries.keys()), None)


def _get_kid_id_by_name(
    coordinator: KidsChoresDataCoordinator, kid_name: str
) -> Optional[str]:
    """Help function to get kid_id by kid_name."""
    for kid_id, kid_info in coordinator.kids_data.items():
        if kid_info.get("name") == kid_name:
            return kid_id
    return None


def _get_chore_id_by_name(
    coordinator: KidsChoresDataCoordinator, chore_name: str
) -> Optional[str]:
    """Help function to get chore_id by chore_name."""
    for chore_id, chore_info in coordinator.chores_data.items():
        if chore_info.get("name") == chore_name:
            return chore_id
    return None


def _get_reward_id_by_name(
    coordinator: KidsChoresDataCoordinator, reward_name: str
) -> Optional[str]:
    """Help function to get reward_id by reward_name."""
    for reward_id, reward_info in coordinator.rewards_data.items():
        if reward_info.get("name") == reward_name:
            return reward_id
    return None


def _get_penalty_id_by_name(
    coordinator: KidsChoresDataCoordinator, penalty_name: str
) -> Optional[str]:
    """Help function to get penalty_id by penalty_name."""
    for penalty_id, penalty_info in coordinator.penalties_data.items():
        if penalty_info.get("name") == penalty_name:
            return penalty_id
    return None


def _get_bonus_id_by_name(
    coordinator: KidsChoresDataCoordinator, bonus_name: str
) -> Optional[str]:
    """Help function to get bonus_id by bonus_name."""
    for bonus_id, bonus_info in coordinator.bonuses_data.items():
        if bonus_info.get("name") == bonus_name:
            return bonus_id
    return None
