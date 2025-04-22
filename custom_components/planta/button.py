"""Planta button entity."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PlantaConfigEntry, PlantaCoordinator
from .entity import PlantaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlantaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Planta todo using config entry."""
    coordinator: PlantaCoordinator = entry.runtime_data
    async_add_entities(
        [
            PlantaButtonEntity(coordinator, descriptor, plant_id)
            for plant_id in coordinator.data
            for descriptor in BUTTONS
        ]
    )


@dataclass(frozen=True, kw_only=True)
class PlantaButtonEntityDescription(ButtonEntityDescription):
    """Planta button entity description."""

    field: str


BUTTONS = (
    PlantaButtonEntityDescription(
        key="complete_cleaning",
        translation_key="complete_cleaning",
        field="cleaning",
    ),
    PlantaButtonEntityDescription(
        key="complete_fertilizing",
        translation_key="complete_fertilizing",
        field="fertilizing",
    ),
    PlantaButtonEntityDescription(
        key="complete_misting",
        translation_key="complete_misting",
        field="misting",
    ),
    PlantaButtonEntityDescription(
        key="complete_watering",
        translation_key="complete_watering",
        field="watering",
    ),
)


class PlantaButtonEntity(PlantaEntity, ButtonEntity):
    """Planta button entity."""

    entity_description: PlantaButtonEntityDescription

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return self.plant["actions"][self.entity_description.field]["next"] is not None

    async def async_press(self) -> None:
        """Handle the button press."""
        if not self.plant_id or not (action := self.entity_description.field):
            raise ServiceValidationError(
                f"{self.name} cannot be performed on {self.device_entry.name}"
            )

        await self.coordinator.client.plant_action_complete(self.plant_id, action)
        await self.coordinator.async_refresh_plant(self.plant_id)
