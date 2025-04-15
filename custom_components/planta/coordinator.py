"""Planta coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .pyplanta import Planta
from .pyplanta.utils import UnauthorizedError

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
        except UnauthorizedError as err:
            raise ConfigEntryAuthFailed from err
        except Exception as ex:
            _LOGGER.error(ex)
            raise UpdateFailed("Couldn't read from Planta") from ex
        if data is None:
            raise ConfigEntryAuthFailed
        return data.get("plants", [])
