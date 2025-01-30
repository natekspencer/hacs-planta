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
            PlantaButtonEntity(coordinator, descriptor, plant["id"])
            for plant in coordinator.data
            for descriptor in BUTTONS
            for action in plant["actions"]
            if action["type"] == descriptor.field
        ],
        True,
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
        field="fertilizingRecurring",
    ),
    PlantaButtonEntityDescription(
        key="complete_misting",
        translation_key="complete_misting",
        field="misting",
    ),
    PlantaButtonEntityDescription(
        key="complete_repotting",
        translation_key="complete_repotting",
        field="repotting",
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

    async def async_press(self) -> None:
        """Handle the button press."""
        action_id = next(
            (
                action["id"]
                for action in self.plant["actions"]
                if action["type"] == self.entity_description.field
            ),
            None,
        )
        if not action_id:
            raise ServiceValidationError(
                f"{self.name} cannot be performed on {self.device_entry.name}"
            )

        await self.coordinator.client.plant_action_complete(action_id)
        await self.coordinator.async_refresh()
