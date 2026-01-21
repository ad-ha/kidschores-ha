# File: notification_action_handler.py
"""Handle notification actions from HA companion notifications."""

from homeassistant.core import HomeAssistant, Event
from homeassistant.exceptions import HomeAssistantError

from . import const
from .coordinator import KidsChoresDataCoordinator


async def async_handle_notification_action(hass: HomeAssistant, event: Event) -> None:
    """Handle notification actions from HA companion notifications."""

    action_field = event.data.get(const.NOTIFY_ACTION)
    if not action_field:
        const.LOGGER.error("ERROR: No action found in event data: %s", event.data)
        return

    parts = action_field.split("|")
    base_action = parts[0]
    kid_id = None
    chore_id = None
    reward_id = None
    notif_id = None

    # Decide what to expect based on the base action.
    if base_action in (const.ACTION_APPROVE_REWARD, const.ACTION_DISAPPROVE_REWARD):
        if len(parts) < 3:
            const.LOGGER.error(
                "ERROR: Not enough context in reward action field: %s", action_field
            )
            return
        kid_id = parts[1]
        reward_id = parts[2]
        notif_id = parts[3]

    elif base_action in (
        const.ACTION_APPROVE_CHORE,
        const.ACTION_DISAPPROVE_CHORE,
        const.ACTION_REMIND_30,
    ):
        if len(parts) < 3:
            const.LOGGER.error(
                "ERROR: Not enough context in chore action field: %s", action_field
            )
            return
        kid_id = parts[1]
        chore_id = parts[2]
    else:
        const.LOGGER.error("ERROR: Unknown base action: %s", base_action)
        return

    # Parent name may be provided in the event data or use a default.
    parent_name = event.data.get(
        const.NOTIFY_PARENT_NAME, const.NOTIFY_DEFAULT_PARENT_NAME
    )

    if not kid_id or not base_action:
        const.LOGGER.error(
            "ERROR: Notification action event missing required data: %s", event.data
        )
        return

    # Retrieve the coordinator.
    domain_data = hass.data.get(const.DOMAIN, {})
    if not domain_data:
        const.LOGGER.error("ERROR: KidsChores data not found")
        return
    entry_id = next(iter(domain_data))
    coordinator: KidsChoresDataCoordinator = domain_data[entry_id].get(
        const.COORDINATOR
    )
    if not coordinator:
        const.LOGGER.error("ERROR: KidsChores coordinator not found")
        return

    try:
        if base_action == const.ACTION_APPROVE_CHORE:
            await coordinator.approve_chore(
                parent_name=parent_name,
                kid_id=kid_id,
                chore_id=chore_id,
            )
        elif base_action == const.ACTION_DISAPPROVE_CHORE:
            await coordinator.disapprove_chore(
                parent_name=parent_name,
                kid_id=kid_id,
                chore_id=chore_id,
            )
        elif base_action == const.ACTION_APPROVE_REWARD:
            await coordinator.approve_reward(
                parent_name=parent_name,
                kid_id=kid_id,
                reward_id=reward_id,
                notif_id=notif_id,
            )
        elif base_action == const.ACTION_DISAPPROVE_REWARD:
            await coordinator.disapprove_reward(
                parent_name=parent_name,
                kid_id=kid_id,
                reward_id=reward_id,
            )
        elif base_action == const.ACTION_REMIND_30:
            await coordinator.remind_in_minutes(
                kid_id=kid_id,
                chore_id=chore_id,
                reward_id=reward_id,
                minutes=const.DEFAULT_REMINDER_DELAY,
            )
        else:
            const.LOGGER.error(
                "ERROR: Received unknown notification action: %s", base_action
            )
    except HomeAssistantError as err:
        const.LOGGER.error(
            "ERROR: Failed processing notification action %s: %s", base_action, err
        )
