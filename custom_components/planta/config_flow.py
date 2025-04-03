"""Config flow for Planta integration."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aiohttp import ClientConnectorError
from httpx import ConnectError, HTTPStatusError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .pyplanta import Planta

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
)


class PlantaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Planta."""

    VERSION = 1

    token: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        return await self._async_step("user", STEP_USER_DATA_SCHEMA, user_input)

    async def _async_step(
        self,
        step_id: str,
        schema: vol.Schema,
        user_input: dict[str, Any] | None = None,
        suggested_values: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle step setup."""
        if abort := self._abort_if_configured(user_input):
            return abort

        errors = {}

        if user_input is not None:
            if not (errors := await self.validate_client(user_input)):
                data = {
                    CONF_EMAIL: user_input[CONF_EMAIL],
                    CONF_TOKEN: json.dumps(self.token),
                }
                if existing_entry := self.hass.config_entries.async_get_entry(
                    self.context.get("entry_id")
                ):
                    self.hass.config_entries.async_update_entry(
                        existing_entry, data=data
                    )
                    await self.hass.config_entries.async_reload(existing_entry.entry_id)
                    return self.async_abort(reason="reconfigure_successful")

                return self.async_create_entry(title=user_input[CONF_EMAIL], data=data)

        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(schema, suggested_values),
            errors=errors,
        )

    async def validate_client(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Validate client setup."""
        errors = {}
        try:
            client = Planta(session=async_get_clientsession(self.hass))
            await client.login(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
            if not client.token:
                errors["base"] = "invalid_auth"
            self.token = client.token
        except asyncio.TimeoutError:
            errors["base"] = "timeout_connect"
        except ConnectError:
            errors["base"] = "invalid_host"
        except ClientConnectorError:
            errors["base"] = "invalid_host"
        except HTTPStatusError as err:
            errors["base"] = str(err)
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.error(ex)
            errors["base"] = "unknown"
        finally:
            await client.close()
        return errors

    @callback
    def _abort_if_configured(
        self, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult | None:
        """Abort if configured."""
        if user_input:
            for entry in self._async_current_entries():
                if entry.data[CONF_EMAIL] == user_input[CONF_EMAIL]:
                    return self.async_abort(reason="already_configured")
        return None
