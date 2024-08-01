"""Planta image entity."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PlantaConfigEntry
from .coordinator import PlantaPlantCoordinator
from .entity import PlantaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlantaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Planta camera using config entry."""
    async_add_entities(
        [
            PlantaImageEntity(plant_coordinator, IMAGE, plant_id)
            for plant_id, plant_coordinator in entry.runtime_data.plant_coordinators.items()
        ],
        True,
    )


IMAGE = ImageEntityDescription(key="image", name=None)


class PlantaImageEntity(PlantaEntity, ImageEntity):
    """Planta image entity."""

    def __init__(
        self,
        coordinator: PlantaPlantCoordinator,
        description: ImageEntityDescription,
        plant_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, description, plant_id)
        ImageEntity.__init__(self, coordinator.hass)

    async def async_added_to_hass(self) -> None:
        self._handle_coordinator_update()
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.data or not self.coordinator.plant_data:
            return
        url = self.coordinator.plant_data.get("defaultImage", {}).get("url")
        if url != self._attr_image_url:
            self._attr_image_last_updated = next(
                (
                    datetime.fromisoformat(action["completed"])
                    for action in self.coordinator.data["images"]
                    if action.get("images")
                ),
                None,
            )
            self._attr_image_url = url
            self._cached_image = None
        super()._handle_coordinator_update()
