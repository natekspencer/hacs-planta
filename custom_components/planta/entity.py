"""Planta entity."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PlantaCoordinator, PlantaPlantCoordinator


class PlantaEntity(CoordinatorEntity[PlantaCoordinator | PlantaPlantCoordinator]):
    """Base class for Planta entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PlantaCoordinator | PlantaPlantCoordinator,
        description: EntityDescription,
        plant_id: str,
    ) -> None:
        """Construct a Planta entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self.plant_id = plant_id

        self._attr_unique_id = f"{plant_id}-{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, plant_id)},
            name=self.plant["nameCustom"] or self.plant["plantName"],
            manufacturer="Planta",
            model=self.plant["nameScientific"]
            + (f" '{variety}'" if (variety := self.plant["nameVariety"]) else ""),
            suggested_area=self.plant["site"]["name"],
        )

    @property
    def plant(self) -> dict[str, Any]:
        """Get plant data."""
        coordinator = self.coordinator
        if isinstance(self.coordinator, PlantaPlantCoordinator):
            coordinator = coordinator.coordinator
        return coordinator.get_plant(self.plant_id)
