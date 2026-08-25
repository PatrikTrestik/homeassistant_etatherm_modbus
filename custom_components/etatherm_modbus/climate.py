"""Etatherm Modbus climate platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, CONF_HOST, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EtathermCoordinator
from .const import CONF_UNIQUE_BASE, DOMAIN, HVACPreset_AUTO

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Etatherm climate entities from a config entry."""
    coordinator: EtathermCoordinator = hass.data[DOMAIN][entry.entry_id]
    params = await coordinator.etherm.get_parameters()
    if not params:
        _LOGGER.warning("No used heating positions found on %s", entry.data[CONF_HOST])
        return

    thermostats = [
        EtathermThermostat(coordinator, entry, idx, name)
        for idx, name in params.items()
    ]
    async_add_entities(thermostats)


class EtathermThermostat(CoordinatorEntity, ClimateEntity):
    """Representation of a thermostat."""

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.AUTO]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: EtathermCoordinator,
        entry: ConfigEntry,
        idx: int,
        params: dict[str, Any],
    ) -> None:
        """Initialize the thermostat."""
        super().__init__(coordinator, context=idx)
        self._id = idx
        unique_id = entry.unique_id or entry.entry_id
        unique_base = entry.data.get(CONF_UNIQUE_BASE)
        self._attr_unique_id = unique_base or f"{unique_id}-{idx}"
        self._name = params["name"]
        self._attr_name = params["name"]
        self._current_temperature = None
        self._target_temperature = None
        self._attr_hvac_mode = HVACMode.AUTO
        self._attr_preset_mode = HVACPreset_AUTO
        self._attr_target_temperature_high = params["max"]
        self._attr_target_temperature_low = params["min"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name=f"Etatherm {entry.data[CONF_HOST]}",
            manufacturer="Etatherm",
            model="Modbus TCP",
        )

    async def async_added_to_hass(self) -> None:
        """Register for coordinator updates and apply current data."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @property
    def name(self) -> str:
        """Return the name of the thermostat."""
        return self._name

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new mode."""
        if hvac_mode not in self._attr_hvac_modes:
            return
        await self.coordinator.setHVACMode(self._id, hvac_mode)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        self._target_temperature = int(temperature)
        await self.coordinator.setTemperature(self._id, temperature)
        if (hvac_mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            await self.coordinator.setHVACMode(self._id, hvac_mode)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data is not None:
            self._current_temperature = self.coordinator.data[self._id]["curr"]
            self._target_temperature = self.coordinator.data[self._id]["req"]["temp"]
            if self._current_temperature < self._target_temperature:
                self._attr_hvac_action = HVACAction.HEATING
            else:
                self._attr_hvac_action = HVACAction.IDLE
            flag = self.coordinator.data[self._id]["req"]["flag"]
            match flag:
                case 0:
                    self._attr_hvac_mode = HVACMode.OFF
                case 1 | 4:
                    self._attr_hvac_mode = HVACMode.AUTO
                case 2 | 3:
                    self._attr_hvac_mode = HVACMode.HEAT
            self.async_write_ha_state()
