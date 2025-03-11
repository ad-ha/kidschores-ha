"""Diagnostics support for KidsChores integration.

Provides comprehensive data export for troubleshooting and backup/restore.
The diagnostics JSON returns raw storage data - byte-for-byte identical to
the kidschores_data file for direct paste during data recovery.
"""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from . import const
from .coordinator import KidsChoresDataCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Returns the raw storage data directly - byte-for-byte identical to the
    kidschores_data file. This can be pasted directly during data recovery
    with no transformation needed.

    Benefits:
    - No parsing/reformatting overhead
    - Future-proof (all storage keys automatically included)
    - Direct paste during recovery
    - Coordinator migration handles schema differences
    """
    coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry.entry_id][
        const.COORDINATOR
    ]

    # Return raw storage data - no transformation needed
    # Coordinator's migration logic handles all schema differences on load
    return coordinator.storage_manager.data


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device entry.

    Provides kid-specific view of data for troubleshooting individual kids.
    """
    coordinator: KidsChoresDataCoordinator = hass.data[const.DOMAIN][entry.entry_id][
        const.COORDINATOR
    ]

    # Extract kid_id from device identifiers
    kid_id = None
    for identifier in device.identifiers:
        if identifier[0] == const.DOMAIN:
            kid_id = identifier[1]
            break

    if not kid_id:
        return {"error": "Could not determine kid_id from device identifiers"}

    kid_data = coordinator.kids_data.get(kid_id)
    if not kid_data:
        return {"error": f"Kid data not found for kid_id: {kid_id}"}

    # Return kid-specific data snapshot
    return {
        "kid_id": kid_id,
        "kid_data": kid_data,
    }
