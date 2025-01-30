"""Planta coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .pyplanta import Planta

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=5)

type PlantaConfigEntry = ConfigEntry[PlantaCoordinator]


class PlantaCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Planta data update coordinator."""

    def __init__(
        self, hass: HomeAssistant, config_entry: PlantaConfigEntry, client: Planta
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.client = client
        self.plant_coordinators: dict[str, PlantaPlantCoordinator] = {}

    def generate_plant_coordinators(self) -> None:
        """Generate coordinators for each plant."""
        if not self.data:
            return
        for plant in self.data:
            if (plant_id := plant["id"]) not in self.plant_coordinators:
                self.plant_coordinators[plant_id] = PlantaPlantCoordinator(
                    self.hass, self, plant_id
                )

    def get_plant(self, plant_id: str) -> dict[str, Any] | None:
        """Get a plant by it's id."""
        if not self.data:
            return None
        return next((plant for plant in self.data if plant["id"] == plant_id), None)

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch the latest data."""
        try:
            async with async_timeout.timeout(10):
                data = await self.client.get_plants()
        except Exception as ex:
            _LOGGER.error(ex)
            raise UpdateFailed("Couldn't read from Planta") from ex
        if data is None:
            raise ConfigEntryAuthFailed
        return data


class PlantaPlantCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Planta plant data update coordinator."""

    def __init__(
        self, hass: HomeAssistant, coordinator: PlantaCoordinator, plant_id: str
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=coordinator.config_entry,
            name=f"{DOMAIN} plant",
            always_update=False,
        )
        self.coordinator = coordinator
        self.plant_id = plant_id
        self.plant_data = coordinator.get_plant(plant_id)

        coordinator.async_add_listener(self.schedule_refresh)

    @callback
    def schedule_refresh(self) -> None:
        """Schedule a refresh."""
        if (
            self.plant_data != (new_data := self.coordinator.get_plant(self.plant_id))
            or not self.last_update_success
        ):
            self.plant_data = new_data
            self.config_entry.async_create_background_task(
                self.hass,
                self._handle_refresh_interval(),
                name=f"{self.name} - {self.config_entry.title} - refresh",
                eager_start=True,
            )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest data."""
        client = self.coordinator.client
        try:
            async with async_timeout.timeout(10):
                state = await client.get_plant_state(self.plant_id)
                state["images"] = await client.get_plant_images_and_notes(self.plant_id)
        except Exception as ex:
            _LOGGER.error(ex)
            self.update_interval = UPDATE_INTERVAL
            raise UpdateFailed("Couldn't read from Planta") from ex
        self.update_interval = None
        return state
