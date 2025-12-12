# File: notification_helper.py
"""Sends notifications using Home Assistant's notify services.

This module implements a helper for sending notifications in the KidsChores integration.
It supports sending notifications via Home Assistant’s notify services (HA Companion notifications)
and includes an optional payload of actions. For actionable notifications, you must encode extra
context (like kid_id and chore_id) directly into the action string.
All texts and labels are referenced from constants.
"""

from __future__ import annotations

from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import const


async def async_send_notification(
    hass: HomeAssistant,
    notify_service: str,
    title: str,
    message: str,
    actions: Optional[list[dict[str, str]]] = None,
    extra_data: Optional[dict[str, str]] = None,
) -> None:
    """Send a notification using the specified notify service."""

    payload: dict[str, Any] = {const.NOTIFY_TITLE: title, const.NOTIFY_MESSAGE: message}

    if actions:
        data = payload.setdefault(const.NOTIFY_DATA, {})
        data[const.NOTIFY_ACTIONS] = actions  # type: ignore[index]

    if extra_data:
        data = payload.setdefault(const.NOTIFY_DATA, {})
        data.update(extra_data)  # type: ignore[attr-defined]

    try:
        if const.CONF_DOT not in notify_service:
            domain = const.NOTIFY_DOMAIN
            service = notify_service
        else:
            domain, service = notify_service.split(".", 1)
        await hass.services.async_call(domain, service, payload, blocking=True)
        const.LOGGER.debug(
            "DEBUG: Notification sent via '%s': %s", notify_service, payload
        )

    except Exception as err:
        const.LOGGER.error(
            "ERROR: Failed to send notification via '%s': %s. Payload: %s",
            notify_service,
            err,
            payload,
        )
        raise HomeAssistantError(
            f"Failed to send notification via '{notify_service}': {err}"
        ) from err
