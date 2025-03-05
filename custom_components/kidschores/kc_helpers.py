# File: kc_helpers.py
"""KidsChores helper functions and shared logic."""

from homeassistant.core import HomeAssistant
from homeassistant.auth.models import User
from homeassistant.helpers.label_registry import async_get
from typing import Optional

from .const import LOGGER, DOMAIN
from .coordinator import KidsChoresDataCoordinator


# -------- Get Coordinator --------
def _get_kidschores_coordinator(
    hass: HomeAssistant,
) -> KidsChoresDataCoordinator | None:
    """Retrieve KidsChores coordinator from hass.data."""
    domain_entries = hass.data.get(DOMAIN, {})
    if not domain_entries:
        return None

    entry_id = next(iter(domain_entries), None)
    if not entry_id:
        return None

    data = domain_entries.get(entry_id)
    if not data or "coordinator" not in data:
        return None

    return data["coordinator"]


# -------- Authorization for General Actions --------
async def is_user_authorized_for_global_action(
    hass: HomeAssistant,
    user_id: str,
    action: str,
) -> bool:
    """Check if the user is allowed to do a global action (penalty, reward, points adjust) that doesn't require a specific kid_id.

    By default:
      - Admin users => authorized
      - Everyone else => not authorized

    """
    if not user_id:
        return False  # no user context => not authorized

    user: User = await hass.auth.async_get_user(user_id)
    if not user:
        LOGGER.warning("%s: Invalid user ID '%s'", action, user_id)
        return False

    if user.is_admin:
        return True

    # Allow non-admin users if they are registered as a parent in KidsChores.
    coordinator = _get_kidschores_coordinator(hass)
    if coordinator:
        for parent in coordinator.parents_data.values():
            if parent.get("ha_user_id") == user.id:
                return True

    LOGGER.warning(
        "%s: Non-admin user '%s' is not authorized in this logic", action, user.name
    )
    return False


# -------- Authorization for Kid-Specific Actions --------
async def is_user_authorized_for_kid(
    hass: HomeAssistant,
    user_id: str,
    kid_id: str,
) -> bool:
    """Check if user is authorized to manage chores/rewards/etc. for the given kid.

    By default:
      - Admin => authorized
      - If kid_info['ha_user_id'] == user.id => authorized
      - Otherwise => not authorized
    """
    if not user_id:
        return False

    user: User = await hass.auth.async_get_user(user_id)
    if not user:
        LOGGER.warning("Authorization: Invalid user ID '%s'", user_id)
        return False

    # Admin => automatically allowed
    if user.is_admin:
        return True

    # Allow non-admin users if they are registered as a parent in KidsChores.
    coordinator = _get_kidschores_coordinator(hass)
    if coordinator:
        for parent in coordinator.parents_data.values():
            if parent.get("ha_user_id") == user.id:
                return True

    coordinator: KidsChoresDataCoordinator = _get_kidschores_coordinator(hass)
    if not coordinator:
        LOGGER.warning("Authorization: No KidsChores coordinator found")
        return False

    kid_info = coordinator.kids_data.get(kid_id)
    if not kid_info:
        LOGGER.warning(
            "Authorization: Kid ID '%s' not found in coordinator data", kid_id
        )
        return False

    linked_ha_id = kid_info.get("ha_user_id")
    if linked_ha_id and linked_ha_id == user.id:
        return True

    LOGGER.warning(
        "Authorization: Non-admin user '%s' attempted to manage kid '%s' but is not linked",
        user.name,
        kid_info.get("name"),
    )
    return False


# ------------------ Helper Functions ------------------
def _get_kid_id_by_name(self, kid_name: str) -> Optional[str]:
    """Help function to get kid_id by kid_name."""
    for kid_id, kid_info in self.kids_data.items():
        if kid_info.get("name") == kid_name:
            return kid_id
    return None


def _get_kid_name_by_id(self, kid_id: str) -> Optional[str]:
    """Help function to get kid_name by kid_id."""
    kid_info = self.kids_data.get(kid_id)
    if kid_info:
        return kid_info.get("name")
    return None


def get_friendly_label(hass, label_name: str) -> str:
    registry = async_get(hass)
    entries = registry.async_list_labels()
    label_entry = registry.async_get_label(label_name)
    return label_entry.name if label_entry else label_name
