"""Planta sensor entity."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .coordinator import PlantaConfigEntry, PlantaCoordinator
from .entity import PlantaEntity

_LOGGER = logging.getLogger(__name__)

PLANT_HEALTH_LIST = ["notset", "poor", "fair", "good", "verygood", "excellent"]


def get_plant_action_date(
    plant: dict[str, Any], action_type: str, last: bool = False
) -> datetime | None:
    """Get plant action date."""
    action = plant.get("actions", {}).get(action_type, {})
    record = action.get("last" if last else "next") or {}
    if record_date := (
        record.get("date") if not last or record.get("action") == "completed" else None
    ):
        return datetime.fromisoformat(record_date)
    return None


def time_since_last_completed(plant: dict[str, Any], action_type: str) -> float | None:
    """Get time since last completed action."""
    if action_date := get_plant_action_date(plant, action_type, True):
        return (datetime.now(timezone.utc) - action_date).total_seconds()
    return None


@dataclass(frozen=True, kw_only=True)
class PlantaSensorEntityDescription(SensorEntityDescription):
    """Planta sensor entity description."""

    field: str
    is_pot: bool = False
    value_fn: Callable[[dict[str, Any]], datetime | None] | None = None


DESCRIPTORS = (
    PlantaSensorEntityDescription(
        key="health",
        field="health",
        translation_key="health",
        icon="mdi:clipboard-pulse",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=PLANT_HEALTH_LIST,
    ),
    PlantaSensorEntityDescription(
        key="scheduled_cleaning",
        field="cleaning",
        translation_key="scheduled_cleaning",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda plant: get_plant_action_date(plant, "cleaning"),
    ),
    PlantaSensorEntityDescription(
        key="scheduled_fertilizing",
        field="fertilizing",
        translation_key="scheduled_fertilizing",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda plant: get_plant_action_date(plant, "fertilizing"),
    ),
    PlantaSensorEntityDescription(
        key="last_fertilizing",
        field="fertilizing",
        translation_key="last_fertilizing",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda plant: get_plant_action_date(plant, "fertilizing", True),
    ),
    PlantaSensorEntityDescription(
        key="time_since_last_fertilizing",
        field="fertilizing",
        translation_key="time_since_last_fertilizing",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda plant: time_since_last_completed(plant, "fertilizing"),
    ),
    PlantaSensorEntityDescription(
        key="scheduled_misting",
        field="misting",
        translation_key="scheduled_misting",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda plant: get_plant_action_date(plant, "misting"),
    ),
    PlantaSensorEntityDescription(
        key="scheduled_repotting",
        field="repotting",
        translation_key="scheduled_repotting",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda plant: get_plant_action_date(plant, "repotting"),
    ),
    PlantaSensorEntityDescription(
        key="last_repotting",
        field="repotting",
        translation_key="last_repotting",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda plant: get_plant_action_date(plant, "repotting", True),
    ),
    PlantaSensorEntityDescription(
        key="time_since_last_repotting",
        field="repotting",
        translation_key="time_since_last_repotting",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda plant: time_since_last_completed(plant, "repotting"),
    ),
    PlantaSensorEntityDescription(
        key="scheduled_watering",
        field="watering",
        translation_key="scheduled_watering",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda plant: get_plant_action_date(plant, "watering"),
    ),
    PlantaSensorEntityDescription(
        key="last_watering",
        field="watering",
        translation_key="last_watering",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda plant: get_plant_action_date(plant, "watering", True),
    ),
    PlantaSensorEntityDescription(
        key="time_since_last_watering",
        field="watering",
        translation_key="time_since_last_watering",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda plant: time_since_last_completed(plant, "watering"),
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlantaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Planta sensors using config entry."""
    coordinator: PlantaCoordinator = entry.runtime_data
    async_add_entities(
        PlantaSensorEntity(coordinator, descriptor, plant_id)
        for plant_id in coordinator.data
        for descriptor in DESCRIPTORS
    )


class PlantaSensorEntity(PlantaEntity, SensorEntity):
    """Planta sensor entity."""

    entity_description: PlantaSensorEntityDescription

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return (
            self.entity_description.entity_registry_enabled_default
            and self.native_value is not None
        )

    @property
    def native_value(self) -> int | str | datetime | None:
        """Return the value reported by the sensor."""
        if not self.plant:
            return None
        if value_fn := self.entity_description.value_fn:
            return value_fn(self.plant)
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

    async def async_added_to_hass(self) -> None:
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
