# RTL-433 Sensor Bridge

A Home Assistant add-on that reads 433 MHz temperature and humidity sensors
via an RTL-SDR dongle and pushes them to Home Assistant through the REST API.

## Features

- Reads all 433 MHz devices supported by [rtl_433](https://github.com/merbanan/rtl_433)
- Pushes temperature, humidity and battery state to Home Assistant
- Persistent sensor registry (`rtl433_sensors.yaml`) — survives restarts
- Web configuration panel (HA ingress) to name sensors and toggle follow
- Low battery notifications — mobile push + persistent HA notification
- Configurable scan interval, scan duration and frequency
- Logging to `/config/rtl433_bridge.log`

## Supported sensor types

Any sensor that broadcasts temperature is supported. Humidity is optional.
Sensors without a temperature reading are registered in the YAML but never
sent to Home Assistant, even if `follow: true`.

## Installation

### 1. Add the repository to Home Assistant

In Home Assistant:
**Settings → Add-ons → Add-on store → ⋮ → Repositories**

Add:
```
https://github.com/qcda1/ha_433MHz
```

### 2. Install the add-on

Search for **RTL-433 Sensor Bridge** in the add-on store and install it.

### 3. Configure

Edit the add-on configuration:

| Option          | Default         | Description                              |
|-----------------|-----------------|------------------------------------------|
| `scan_interval` | `300`           | Seconds between scan cycles (60–3600)    |
| `scan_duration` | `90`            | Seconds rtl_433 listens per cycle (30–300) |
| `frequency`     | `433920000`     | Frequency in Hz                          |
| `ha_url`        | `http://homeassistant:8123` | Home Assistant URL          |
| `ha_token`      | *(required)*    | Long-lived access token                  |

### 4. Get a Long-Lived Access Token

In Home Assistant:
**Profile → Long-Lived Access Tokens → Create token**

Copy the token and paste it in the add-on configuration.

### 5. Start the add-on

Start the add-on. On first run it will scan for 433 MHz devices and
populate `/config/rtl433_sensors.yaml`.

## Configuration panel

Open the add-on web UI via **Settings → Add-ons → RTL-433 Sensor Bridge → Open Web UI**.

From here you can:
- See all detected sensors with their latest readings
- Toggle **Follow** to push a sensor to Home Assistant
- Edit the display name used in HA entities

## Home Assistant entities

For each followed sensor, three entities are created:

| Entity | Description |
|--------|-------------|
| `sensor.rtl433_<id>_temperature` | Temperature in °C |
| `sensor.rtl433_<id>_humidity`    | Humidity in % (if available) |
| `binary_sensor.rtl433_<id>_battery` | `on` = low battery |

These entities are visible in **Developer Tools → States** and can be
added to any Lovelace dashboard.

## Sensor configuration file

`/config/rtl433_sensors.yaml` is created automatically and contains
all detected sensors. You can edit it directly or use the web panel.

```yaml
sensors:
  79:
    name: Backyard
    follow: true
    last_reception: '2026-05-14 13:00:02'
    model: LaCrosse-TX141THBv2
    channel: 0
    battery_ok: true
    temperature_C: 13.5
    humidity: 87
```

User-managed fields (`name`, `follow`) are never overwritten by incoming data.

## Hardware

Tested with:
- Nooelec NESDR SMArt v5 (RTL2832U / R820T)

Any RTL-SDR dongle supported by rtl_433 should work.

## License

MIT
