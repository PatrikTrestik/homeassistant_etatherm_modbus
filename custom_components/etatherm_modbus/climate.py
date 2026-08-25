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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from . import EtathermCoordinator
from .const import CONF_LEGACY_ENTITY_IDS, DOMAIN, HVACPreset_AUTO

# YAML domain of the proprietary Etatherm integration (etatherm_ha).
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

    keep_legacy = bool(entry.data.get(CONF_LEGACY_ENTITY_IDS))
    _LOGGER.debug(
        "Setting up climate for %s keep_legacy=%s positions=%s",
        entry.data[CONF_HOST],
        keep_legacy,
        list(params),
    )
    if keep_legacy:
        _park_legacy_entity_ids(hass, entry, params)

    thermostats = [
        EtathermThermostat(coordinator, entry, idx, name)
        for idx, name in params.items()
    ]
    async_add_entities(thermostats)


def _unused_entity_id(registry: er.EntityRegistry, base_entity_id: str) -> str:
    """Return base_entity_id, or base_entity_id_2, ... if already taken."""
    if registry.async_get(base_entity_id) is None:
        return base_entity_id
    index = 2
    while registry.async_get(f"{base_entity_id}_{index}") is not None:
        index += 1
    return f"{base_entity_id}_{index}"


def _park_legacy_entity_ids(
    hass: HomeAssistant,
    entry: ConfigEntry,
    params: dict[int, Any],
) -> None:
    """Rename occupants of climate.{slug} to climate.{slug}_old. Do not adopt them."""
    registry = er.async_get(hass)
    new_uid_prefix = entry.unique_id or entry.entry_id
    for idx, position in params.items():
        slug = slugify(position["name"])
        desired_entity_id = f"climate.{slug}"
        new_uid = f"{new_uid_prefix}-{idx}"
        occupant = registry.async_get(desired_entity_id)
        if occupant is None:
            continue
        if occupant.platform == DOMAIN and occupant.unique_id == new_uid:
            continue
        parked_id = _unused_entity_id(registry, f"{desired_entity_id}_old")
        _LOGGER.debug("Renaming legacy %s -> %s", desired_entity_id, parked_id)
        try:
            registry.async_update_entity(desired_entity_id, new_entity_id=parked_id)
        except ValueError as err:
            _LOGGER.debug(
                "Could not rename %s -> %s: %s", desired_entity_id, parked_id, err
            )


class EtathermThermostat(CoordinatorEntity, ClimateEntity):
    """Representation of a thermostat."""

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.AUTO]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_has_entity_name = False

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
        slug = slugify(params["name"])
        self._attr_unique_id = f"{unique_id}-{idx}"
        self._attr_suggested_object_id = slug
        if entry.data.get(CONF_LEGACY_ENTITY_IDS):
            self.entity_id = f"climate.{slug}"
        _LOGGER.debug(
            "Climate %s unique_id=%s entity_id=%s",
            params["name"],
            self._attr_unique_id,
            getattr(self, "entity_id", None),
        )
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
