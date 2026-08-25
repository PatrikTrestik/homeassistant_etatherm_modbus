"""Config flow for Etatherm Modbus."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_MODBUS_ADDR, DEFAULT_MODBUS_ADDR, DEFAULT_PORT, DOMAIN
from .etathermmodbus import EtathermModbus

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_MODBUS_ADDR, default=DEFAULT_MODBUS_ADDR): int,
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
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Etatherm {user_input[CONF_HOST]}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
