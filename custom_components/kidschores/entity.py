"""Base entity classes for KidsChores integration."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import KidsChoresDataCoordinator


class KidsChoresCoordinatorEntity(CoordinatorEntity[KidsChoresDataCoordinator]):
    """Base entity class for KidsChores sensors with typed coordinator access.

    This base class provides a typed coordinator property pattern that eliminates
    duplication across all 26 sensor classes. By inheriting from this class, sensors
    automatically get proper type hints for self.coordinator without boilerplate code.
    """

    @property
    def coordinator(self) -> KidsChoresDataCoordinator:
        """Return typed coordinator.

        Uses object.__getattribute__ to access the private _coordinator attribute
        set by the parent CoordinatorEntity class, providing strong typing for
        autocomplete and type checking throughout sensor implementations.
        """
        return object.__getattribute__(self, "_coordinator")

    @coordinator.setter
    def coordinator(self, value: KidsChoresDataCoordinator) -> None:
        """Set coordinator with proper typing.

        Args:
            value: The KidsChoresDataCoordinator instance to set.
        """
        object.__setattr__(self, "_coordinator", value)
