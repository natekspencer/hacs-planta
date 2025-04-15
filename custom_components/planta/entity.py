"""Planta entity."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PlantaCoordinator


class PlantaEntity(CoordinatorEntity[PlantaCoordinator]):
    """Base class for Planta entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PlantaCoordinator,
        description: EntityDescription,
        plant_id: str,
    ) -> None:
        """Construct a Planta entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self.plant_id = plant_id

        # strip user id from plant_id
        plant_id = plant_id.split(":")[-1]

        self._attr_unique_id = f"{plant_id}-{description.key}"
        names = self.plant.get("names", {})
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, plant_id)},
            name=names.get("custom") or names.get("localizedName"),
            manufacturer="Planta",
            model=names.get("scientific")
            + (f" '{variety}'" if (variety := names.get("variety")) else ""),
            suggested_area=self.plant["site"]["name"],
        )

    @property
    def plant(self) -> dict[str, Any]:
        """Get plant data."""
        return self.coordinator.get_plant(self.plant_id)
