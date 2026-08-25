"""The Etatherm Modbus integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.components.climate.const import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_MODBUS_ADDR, DOMAIN, PLATFORMS
from .etathermmodbus import EtathermModbus

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Etatherm Modbus from a config entry."""
    client = EtathermModbus(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_MODBUS_ADDR],
    )
    coordinator = EtathermCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: EtathermCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.etherm.async_close()
    return unload_ok


class EtathermCoordinator(DataUpdateCoordinator):
    """Etatherm coordinator."""

    def __init__(self, hass: HomeAssistant, etherm: EtathermModbus) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Etatherm",
            update_interval=timedelta(seconds=15),
        )
        self.etherm = etherm

    async def setTemperature(self, pos, temperature) -> None:
        await self.etherm.set_temporary_temperature(pos, temperature, 120)

    async def setHVACMode(self, pos, hvac_mode) -> None:
        await self.etherm.set_mode(pos, hvac_mode == HVACMode.AUTO)

    async def _async_update_data(self):
        """Fetch data from the controller."""
        async with asyncio.timeout(10):
            current = await self.etherm.get_current_temperatures()
            required = await self.etherm.get_required_temperatures()
            if current is None or required is None:
                raise UpdateFailed("Error communicating with Etatherm")
            return {
                iid: {"curr": curr, "req": required[iid]}
                for iid, curr in current.items()
            }
