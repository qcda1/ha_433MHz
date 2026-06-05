# RTL-433 Sensor Bridge

A Home Assistant add-on that reads 433 MHz wireless sensor data via an RTL-SDR
dongle and pushes temperature, humidity and battery state to Home Assistant
through the REST API.

## Features

- Captures all 433 MHz devices supported by [rtl_433](https://github.com/merbanan/rtl_433)
- Relies on the [pbkhrv/rtl_433](https://github.com/pbkhrv/rtl_433-hass-addons) add-on for SDR hardware access
- Pushes temperature, humidity and battery state to Home Assistant
- Persistent sensor registry (`/config/rtl_433/rtl433_sensors.yaml`) — survives restarts
- YAML-style web configuration panel showing all sensor fields
- Sensors can be named and individually followed or ignored
- Low battery notifications — mobile push + persistent HA notification
- Configurable scan interval
- Logging to `/config/rtl_433/rtl433_bridge.log`
- Manage log file sizes

## Architecture

```text
RTL-SDR dongle
    └── pbkhrv/rtl_433 add-on
            └── /config/rtl_433/rtl_433_output.json
                    └── RTL-433 Sensor Bridge (this add-on)
                            ├── /config/rtl_433/rtl433_sensors.yaml  (sensor registry)
                            ├── Home Assistant REST API       (entity updates)
                            └── Bottle web panel (port 8099)  (configuration UI)
```

## File structure

```text
ha_433MHz/
├── Dockerfile
├── config.json
├── deploy.sh
├── main.py
├── rtl_reader.py
├── ha_api.py
├── sensor_store.py
├── web_server.py
├── views/
│   └── index.tpl
├── static/
│   └── style.css
└── README.md
```

## Prerequisites

This add-on requires the **pbkhrv/rtl_433** add-on to be installed and running.
It handles all USB and kernel driver access for the RTL-SDR dongle.

### Install pbkhrv/rtl_433

1. In HA: **Settings → Apps → App store → ⋮ → Repositories**
2. Add: `https://github.com/pbkhrv/rtl_433-hass-addons`
3. Install **rtl_433**
4. Create `/config/rtl_433/rtl_433.conf.template`:

```text
frequency 433920000
output json:/config/rtl_433/rtl_433_output.json
protocol -158
```

5. Start the add-on and confirm sensors appear in the log

## Installation

### First install

1. SSH into your Home Assistant instance
2. Clone the repo into the local add-ons directory:

```bash
mkdir -p /addons/dc_apps/rtl433_bridge
cd /addons/dc_apps/rtl433_bridge
git init
git remote add origin https://github.com/qcda1/ha_433MHz.git
git pull origin main
chmod +x deploy.sh
```

3. In HA: **Settings → Apps → App store → Local Apps**
4. Install **RTL-433 Sensor Bridge**
5. In the add-on info page, **disable Protected mode** — required to expose port 8099

### Configuration

Get a Long-Lived Access Token:
**HA Profile → Security tab → Long-Lived Access Tokens → Create token**

Configure the add-on:

| Option          | Default                     | Description                           |
|-----------------|-----------------------------|---------------------------------------|
| `scan_interval` | `60`                        | Seconds between scan cycles (10–3600) |
| `ha_url`        | `http://homeassistant:8123` | Home Assistant internal URL           |
| `ha_token`      | *(required)*                | Long-lived access token               |

### Subsequent updates

After each `git push` from Cursor, deploy to HA:

```bash
/addons/dc_apps/rtl433_bridge/deploy.sh
```

Pull without restarting:

```bash
/addons/dc_apps/rtl433_bridge/deploy.sh --no-restart
```

> **Note:** Changes to `config.json` require a full uninstall/reinstall —
> a restart alone is not sufficient.

## Development workflow

```text
Cursor (macOS) → git push → GitHub → deploy.sh on HA
```

## Web configuration panel

The add-on exposes its web UI directly on port 8099. Add it to a dashboard
using an iframe card:

```yaml
- type: panel
  path: RTL-433
  title: RTL-433
  cards:
    - type: iframe
      url: http://<ha-ip>:8099
      aspect_ratio: 50%
```

The panel displays all detected sensors in YAML style, showing every field
returned by rtl_433. For each sensor you can:

- Edit the display name
- Toggle **follow** to push the sensor to Home Assistant

> **First access on a new device:** open the panel once via
> **Settings → Apps → RTL-433 Sensor Bridge → Open Web UI**
> before using it in a dashboard. This initializes the HA ingress session.

Only sensors with a temperature reading and `follow: true` are pushed to HA.
All other detected devices are recorded in the sensor registry but ignored.

## Home Assistant entities

For each followed sensor:

| Entity | Description |
|--------|-------------|
| `sensor.rtl433_<id>_temperature`    | Temperature in °C |
| `sensor.rtl433_<id>_humidity`       | Humidity in % (if available) |
| `binary_sensor.rtl433_<id>_battery` | `on` = low battery |

Entities are visible in **Developer Tools → States** and can be added
to any Lovelace dashboard.

## Sensor registry

`/config/rtl433_sensors.yaml` is created automatically on first run.
User-managed fields (`name`, `follow`) are never overwritten by incoming data.
All native rtl_433 fields are stored as-is for identification purposes.

```yaml
sensors:
  79:
    name: Backyard
    follow: true
    last_reception: '2026-05-20 17:22:46'
    model: LaCrosse-TX141THBv2
    channel: 0
    battery_ok: 1
    temperature_C: 22.1
    humidity: 34
    mic: CRC
    test: 'No'
  2435056:
    name: Unknown sensor 2435056
    follow: false
    last_reception: '2026-05-20 17:09:45'
    model: DSC-Security
    battery_ok: 1
    closed: 1
    esn: 2527f0
    mic: CRC
```

## Kernel driver note

On Home Assistant OS, the `dvb_usb_rtl28xxu` kernel module loads automatically
when the RTL-SDR dongle is connected and prevents direct access to the device.
This is why this add-on delegates SDR access to pbkhrv/rtl_433, which handles
kernel driver detachment correctly within its privileged container.


## Hardware

Tested with Nooelec NESDR SMArt v5 (RTL2832U / R820T) on Raspberry Pi 4
running Home Assistant OS 17.x.

Any RTL-SDR dongle supported by rtl_433 should work.

## License

MIT
