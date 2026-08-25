"""Constants definition."""

from homeassistant.const import Platform

DOMAIN = "etatherm_modbus"

PLATFORMS = [Platform.CLIMATE]

HVACPreset_AUTO = "auto"
HVACPreset_KEEP = "keep"

CONF_MODBUS_ADDR = "modbus_addr"
DEFAULT_PORT = 50001
DEFAULT_MODBUS_ADDR = 0
CONF_MODBUS_RETR = 10
CONF_MODBUS_RETR_WAIT = 1
CONF_MODBUS_TIMEOUT = 15
