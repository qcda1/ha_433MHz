# RTL-433 Sensor Bridge

A Home Assistant add-on that reads 433 MHz temperature and humidity sensors
via an RTL-SDR dongle and pushes them to Home Assistant through the REST API.

## Features

- Reads all 433 MHz devices supported by [rtl_433](https://github.com/merbanan/rtl_433)
- Pushes temperature, humidity and battery state to Home Assistant
- Persistent sensor registry (`/config/rtl433_sensors.yaml`) — survives restarts
- Web configuration panel (HA ingress) to name sensors and toggle follow
- Low battery notifications — mobile push + persistent HA notification
- Configurable scan interval, scan duration and frequency
- Logging to `/config/rtl433_bridge.log`

## Architecture

```
ha_433MHz/
├── Dockerfile
├── config.json
├── run.sh
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

## Development workflow

```
Cursor (macOS) → VM Debian ~/devel/ha_433MHz → GitHub → HA (deploy.sh)
```

## Installation on Home Assistant

### First install

1. SSH into your Home Assistant instance
2. Create the add-on directory and clone the repo:

```bash
mkdir -p /addons/dc_apps/rtl433_bridge
cd /addons/dc_apps/rtl433_bridge
git init
git remote add origin https://github.com/qcda1/ha_433MHz.git
git pull origin main
chmod +x run.sh deploy.sh
```

3. In HA: **Settings → Apps → App store → Local Apps**
4. Install **RTL-433 Sensor Bridge**

### Configuration

Get a Long-Lived Access Token:
**HA Profile → Security tab → Long-Lived Access Tokens → Create token**

Configure the add-on:

| Option          | Default                     | Description                              |
|-----------------|-----------------------------|------------------------------------------|
| `scan_interval` | `300`                       | Seconds between scan cycles (60–3600)    |
| `scan_duration` | `90`                        | Seconds rtl_433 listens per cycle        |
| `frequency`     | `433920000`                 | Frequency in Hz                          |
| `ha_url`        | `http://homeassistant:8123` | Home Assistant URL                       |
| `ha_token`      | *(required)*                | Long-lived access token                  |

### Subsequent updates

After each `git push` from Cursor, deploy to HA:

```bash
/addons/dc_apps/rtl433_bridge/deploy.sh
```

Pull without restarting:

```bash
/addons/dc_apps/rtl433_bridge/deploy.sh --no-restart
```

## Home Assistant entities

For each followed sensor:

| Entity | Description |
|--------|-------------|
| `sensor.rtl433_<id>_temperature` | Temperature in °C |
| `sensor.rtl433_<id>_humidity`    | Humidity in % (if available) |
| `binary_sensor.rtl433_<id>_battery` | `on` = low battery |

Entities are visible in **Developer Tools → States** and can be added
to any Lovelace dashboard.

## Sensor configuration file

`/config/rtl433_sensors.yaml` is created automatically.
User-managed fields (`name`, `follow`) are never overwritten by incoming data.

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

## Hardware

Tested with Nooelec NESDR SMArt v5 (RTL2832U / R820T).
Any RTL-SDR dongle supported by rtl_433 should work.

## License

MIT
