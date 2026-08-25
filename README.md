# Etatherm Modbus for Home Assistant

Custom integration for [Etatherm](https://etatherm.cz) heating over **Modbus TCP**.

This replaces the legacy [Etatherm](https://github.com/PatrikTrestik/etatherm_ha) integration, which used the proprietary protocol.

## Installation
This repository is compatible with HACS. You can use this link to install the integration.
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=PatrikTrestik&repository=homeassistant_etatherm_modbus&category=integration)

Alternatively, copy `custom_components/etatherm_modbus` into your Home Assistant `custom_components` folder, then restart.

## Configuration

Add the integration from the UI:

**Settings → Devices & services → Add Integration → Etatherm Modbus**

| Field | Description | Default |
|-------|-------------|---------|
| Host | IP address of the Eth1eC/D (or a serial/TCP converter that exposes Modbus TCP) | — |
| Port | Modbus TCP port | 50001 |
| Modbus unit ID | Modbus slave/unit address | 0 |

Serial and Modbus RTU are not supported. The device speaks **Modbus TCP** only.

Each used heating position (up to 16) is created as a climate entity under one controller device.
