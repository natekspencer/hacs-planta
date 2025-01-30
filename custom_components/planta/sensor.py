"""Planta sensor entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .coordinator import PlantaConfigEntry, PlantaCoordinator, PlantaPlantCoordinator
from .entity import PlantaEntity

_LOGGER = logging.getLogger(__name__)

PLANT_HEALTH_LIST = ["notset", "poor", "fair", "good", "verygood", "excellent"]


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
    """Planta sensor entity description."""

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
        key="scheduled_cleaning",
        field="cleaning",
        is_action=True,
        translation_key="scheduled_cleaning",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    PlantaSensorEntityDescription(
        key="scheduled_fertilizing",
        field="fertilizingRecurring",
        is_action=True,
        translation_key="scheduled_fertilizing",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    PlantaSensorEntityDescription(
        key="scheduled_misting",
        field="misting",
        is_action=True,
        translation_key="scheduled_misting",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    PlantaSensorEntityDescription(
        key="scheduled_repotting",
        field="repotting",
        is_action=True,
        translation_key="scheduled_repotting",
        device_class=SensorDeviceClass.TIMESTAMP,
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
        key="last_fertilizing",
        field="fertilizing",
        translation_key="last_fertilizing",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    PlantaSensorEntityDescription(
        key="last_repotting",
        field="repotting",
        translation_key="last_repotting",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    PlantaSensorEntityDescription(
        key="last_watering",
        field="watering",
        translation_key="last_watering",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    PlantaSensorEntityDescription(
        key="time_since_last_fertilizing",
        field="fertilizing",
        translation_key="time_since_last_fertilizing",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PlantaSensorEntityDescription(
        key="time_since_last_repotting",
        field="repotting",
        translation_key="time_since_last_repotting",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PlantaSensorEntityDescription(
        key="time_since_last_watering",
        field="watering",
        translation_key="time_since_last_watering",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


class PlantaSensorEntity(PlantaEntity, SensorEntity):
    """Planta sensor entity."""

    entity_description: PlantaSensorEntityDescription

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return self.native_value is not None

    @property
    def native_value(self) -> int | str | datetime | None:
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
        if value is None:
            return value
        if self.device_class == SensorDeviceClass.TIMESTAMP:
            return datetime.fromisoformat(value)
        if isinstance(value, str):
            value = value.lower()
        if self.device_class == SensorDeviceClass.ENUM and value not in self.options:
            _LOGGER.warning("%s has an unknown value: %s", self.name, value)
            self.entity_description.options.append(value)
        return value


class PlantaHistorySensorEntity(PlantaEntity, SensorEntity):
    """Planta history sensor entity."""

    entity_description: PlantaSensorEntityDescription
    coordinator: PlantaPlantCoordinator

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return self.native_value is not None

    async def async_added_to_hass(self) -> None:
        self._handle_coordinator_update()
        await super().async_added_to_hass()
        if self.device_class == SensorDeviceClass.DURATION:
            self.async_on_remove(
                async_track_time_interval(
                    self.hass, self._update_entity_state, timedelta(minutes=15)
                )
            )

    async def _update_entity_state(self, now: datetime | None = None) -> None:
        """Update the state of the entity."""
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.data:
            return
        if not (field := self.coordinator.data["stats"][self.entity_description.field]):
            return
        value = field["latest"]
        self._attr_native_value = datetime.fromisoformat(value) if value else None
        if self._attr_native_value and self.device_class == SensorDeviceClass.DURATION:
            self._attr_native_value = (
                datetime.now(timezone.utc) - self._attr_native_value
            ).total_seconds()
        super()._handle_coordinator_update()
