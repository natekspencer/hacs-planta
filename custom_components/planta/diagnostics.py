"""Diagnostics support for the Planta integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import PlantaConfigEntry
from .coordinator import PlantaCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PlantaConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: PlantaCoordinator = entry.runtime_data
    data = []
    for plant in coordinator.data:
        plant_data = plant.copy()
        if plant_coordinator := coordinator.plant_coordinators.get(plant["id"]):
            plant_data |= {"state": plant_coordinator.data}
        data.append(plant_data)
    return data
