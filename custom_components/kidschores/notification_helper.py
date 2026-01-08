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

from . import const


async def async_send_notification(
    hass: HomeAssistant,
    notify_service: str,
    title: str,
    message: str,
    actions: Optional[list[dict[str, str]]] = None,
    extra_data: Optional[dict[str, str]] = None,
) -> None:
    """Send a notification using the specified notify service.

    Gracefully handles missing notification services (common in fresh installs,
    migrations, or when mobile app isn't configured yet). If the service doesn't
    exist, logs a warning and returns without raising an exception.
    """

    # Parse service name into domain and service components
    if const.DISPLAY_DOT not in notify_service:
        domain = const.NOTIFY_DOMAIN
        service = notify_service
    else:
        domain, service = notify_service.split(".", 1)

    # Validate service exists before attempting to send
    if not hass.services.has_service(domain, service):
        const.LOGGER.warning(
            "Notification service '%s.%s' not available - skipping notification. "
            "This is normal during migration or if the mobile app/notification "
            "integration isn't configured yet. To enable notifications, configure "
            "the '%s' integration and set up the notification service.",
            domain,
            service,
            domain,
        )
        return  # Gracefully skip instead of raising

    # Build notification payload
    payload: dict[str, Any] = {const.NOTIFY_TITLE: title, const.NOTIFY_MESSAGE: message}

    if actions:
        data = payload.setdefault(const.NOTIFY_DATA, {})
        data[const.NOTIFY_ACTIONS] = actions  # type: ignore[index]

    if extra_data:
        data = payload.setdefault(const.NOTIFY_DATA, {})
        data.update(extra_data)  # type: ignore[attr-defined]

    # Log full payload for debugging (useful for testing translations)
    const.LOGGER.debug(
        "DEBUG: Notification payload for '%s.%s': title='%s', message='%s', actions=%s",
        domain,
        service,
        title,
        message,
        actions,
    )

    try:
        await hass.services.async_call(domain, service, payload, blocking=True)
        const.LOGGER.debug("DEBUG: Notification sent via '%s.%s'", domain, service)

    except Exception as err:  # pylint: disable=broad-exception-caught
        # Broad exception allowed: This runs in fire-and-forget background tasks
        # per AGENTS.md guidelines. We must catch all exceptions to prevent
        # "Task exception was never retrieved" errors in logs.
        const.LOGGER.error(
            "ERROR: Unexpected error sending notification via '%s.%s': %s. Payload: %s",
            domain,
            service,
            err,
            payload,
        )
        # Don't re-raise - log and skip gracefully to prevent task exceptions
        # from cluttering logs during migration or service configuration issues
