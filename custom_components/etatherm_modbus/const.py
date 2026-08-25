"""Constants definition."""

from homeassistant.const import Platform

DOMAIN = "etatherm_modbus"

PLATFORMS = [Platform.CLIMATE]

HVACPreset_AUTO = "auto"
HVACPreset_KEEP = "keep"

CONF_MODBUS_ADDR = "modbus_addr"
DEFAULT_PORT = 50001
DEFAULT_MODBUS_ADDR = 0
