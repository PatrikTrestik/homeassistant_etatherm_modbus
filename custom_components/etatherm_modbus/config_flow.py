"""Config flow for Etatherm Modbus."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_LEGACY_ENTITY_IDS,
    CONF_MODBUS_ADDR,
    DEFAULT_MODBUS_ADDR,
    DEFAULT_PORT,
    DOMAIN,
)
from .etathermmodbus import EtathermModbus

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_MODBUS_ADDR, default=DEFAULT_MODBUS_ADDR): int,
        vol.Required(CONF_LEGACY_ENTITY_IDS, default=False): bool,
    }
)


async def _validate_input(data: dict[str, Any]) -> None:
    """Validate that we can connect to the controller."""
    client = EtathermModbus(
        data[CONF_HOST], data[CONF_PORT], data[CONF_MODBUS_ADDR]
    )
    try:
        if not await client.async_test_connection():
            raise CannotConnect
    finally:
        await client.async_close()


class EtathermModbusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Etatherm Modbus."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return EtathermModbusOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}_{user_input[CONF_MODBUS_ADDR]}"
            )
            self._abort_if_unique_id_configured()
            try:
                await _validate_input(user_input)
            except CannotConnect:
                _LOGGER.warning(
                    "Cannot connect to Etatherm at %s:%s unit %s",
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    user_input[CONF_MODBUS_ADDR],
                )
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                data = {
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                    CONF_MODBUS_ADDR: user_input[CONF_MODBUS_ADDR],
                    CONF_LEGACY_ENTITY_IDS: bool(
                        user_input.get(CONF_LEGACY_ENTITY_IDS)
                    ),
                }
                return self.async_create_entry(
                    title=f"Etatherm {user_input[CONF_HOST]}",
                    data=data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class EtathermModbusOptionsFlow(OptionsFlow):
    """Handle Etatherm Modbus options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage legacy entity ID option for an existing entry."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, **user_input},
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LEGACY_ENTITY_IDS,
                        default=bool(
                            self.config_entry.data.get(CONF_LEGACY_ENTITY_IDS)
                        ),
                    ): bool,
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
