"""Planta sensor entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PlantaConfigEntry
from .coordinator import PlantaCoordinator
from .entity import PlantaEntity

PLANT_HEALTH_LIST = ["notSet", "poor", "fair", "good", "veryGood", "excellent"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlantaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Planta sensors using config entry."""
    coordinator: PlantaCoordinator = entry.runtime_data
    entities = [
        PlantaSensorEntity(coordinator, descriptor, plant["id"])
        for plant in coordinator.data
        for descriptor in DESCRIPTORS
    ]

    async_add_entities(entities)
    entities = [
        PlantaHistorySensorEntity(plant_coordinator, descriptor, plant_id)
        for plant_id, plant_coordinator in coordinator.plant_coordinators.items()
        for descriptor in HISTORY_DESCRIPTORS
    ]
    async_add_entities(entities, True)


@dataclass(frozen=True, kw_only=True)
class PlantaSensorEntityDescription(SensorEntityDescription):
    """Planta sensor entity description"""

    field: str
    is_action: bool = False
    is_pot: bool = False


DESCRIPTORS = (
    PlantaSensorEntityDescription(
        key="health",
        field="plantHealth",
        translation_key="health",
        icon="mdi:clipboard-pulse",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=PLANT_HEALTH_LIST,
    ),
    PlantaSensorEntityDescription(
        key="scheduled_watering",
        field="watering",
        is_action=True,
        translation_key="scheduled_watering",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    PlantaSensorEntityDescription(
        key="size",
        field="size",
        translation_key="size",
        device_class=SensorDeviceClass.DISTANCE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:arrow-up-down",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PlantaSensorEntityDescription(
        key="growing_medium",
        field="soil",
        is_pot=True,
        translation_key="growing_medium",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pot",
    ),
    PlantaSensorEntityDescription(
        key="pot_size",
        field="size",
        is_pot=True,
        translation_key="pot_size",
        device_class=SensorDeviceClass.DISTANCE,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PlantaSensorEntityDescription(
        key="pot_type",
        field="type",
        is_pot=True,
        translation_key="pot_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pot-outline",
    ),
)
HISTORY_DESCRIPTORS = (
    PlantaSensorEntityDescription(
        key="last_watering",
        field="watering",
        translation_key="last_watering",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


class PlantaSensorEntity(PlantaEntity, SensorEntity):
    """Planta sensor entity."""

    entity_description: PlantaSensorEntityDescription

    @property
    def native_value(self) -> int | str | None:
        """Return the value reported by the sensor."""
        if not self.plant:
            return None
        if self.entity_description.is_action:
            value = next(
                (
                    action["scheduled"]
                    for action in self.plant["actions"]
                    if action["type"] == self.entity_description.field
                ),
                None,
            )
        elif self.entity_description.is_pot:
            value = self.plant["environment"]["pot"][self.entity_description.field]
        else:
            value = self.plant[self.entity_description.field]
        if self.device_class == SensorDeviceClass.TIMESTAMP:
            return datetime.fromisoformat(value)
        if self.device_class == SensorDeviceClass.ENUM and value not in self.options:
            return None
        return value


class PlantaHistorySensorEntity(PlantaEntity, SensorEntity):
    """Planta history sensor entity."""

    entity_description: PlantaSensorEntityDescription

    async def async_added_to_hass(self) -> None:
        self._handle_coordinator_update()
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.data:
            return
        value = self.coordinator.data["stats"][self.entity_description.field]["latest"]
        self._attr_native_value = datetime.fromisoformat(value) if value else None
        super()._handle_coordinator_update()
