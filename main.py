"""
main.py
RTL-433 Sensor Bridge — Main entry point.

Reads sensor data from the JSON file produced by the pbkhrv/rtl_433
Home Assistant add-on, registers all detected devices in a YAML config
file, and pushes followed temperature sensors to Home Assistant via
the REST API.

A Bottle web panel (port 8099) allows naming sensors and toggling
which ones are followed in Home Assistant.

Architecture:
    pbkhrv/rtl_433 add-on → /config/rtl_433_output.json
        → this app → HA REST API
"""

import json
import os
import logging
from logging.handlers import RotatingFileHandler
import schedule
import time
import threading

from rtl_reader   import read_sensors, reset_position, trim_json_file
from ha_api       import HAClient
from sensor_store import load_config, register_sensor
from web_server   import start_web

# ── Read add-on options from HAOS Supervisor ──────────────────────────────────
_options: dict = {}
_options_path  = "/data/options.json"

if os.path.exists(_options_path):
    with open(_options_path) as _f:
        _options = json.load(_f)

SCAN_INTERVAL = int(_options.get("scan_interval", 300))
LOG_LEVEL_STR = _options.get("log_level", "INFO").upper()
HA_URL        = _options.get("ha_url",   "http://homeassistant:8123")
HA_TOKEN      = _options.get("ha_token", "")
CONFIG_FILE   = "/config/rtl_433/rtl433_sensors.yaml"
LOG_FILE      = "/config/rtl_433/rtl433_bridge.log"

# Conversion string → niveau logging
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)
# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        RotatingFileHandler(
            LOG_FILE,
            maxBytes=1 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# Track sensors that already triggered a low-battery alert
# Reset when battery recovers to avoid repeated notifications.
battery_alerted: set = set()


def scan_and_push() -> None:
    """
    Core task: read new data from the rtl_433 JSON file, register
    all detected devices, push followed temperature sensors to HA.
    """
    log.info("=" * 60)
    log.info("Scan cycle starting...")

    # Trim JSON file if too large
    trim_json_file(max_size_mb=10)
    
    config  = load_config(CONFIG_FILE)
    ha      = HAClient(HA_URL, HA_TOKEN)
    devices = read_sensors()

    if not devices:
        log.debug("No new sensor data in this scan cycle.")
        return

    for sensor_id, data in devices.items():
        # Always register/update the sensor in YAML regardless of type
        sensor_cfg  = register_sensor(config, data, CONFIG_FILE)

        temperature = data.get("temperature_C")
        humidity    = data.get("humidity")
        battery     = data.get("battery_ok", 1)
        model       = data.get("model",   "unknown")
        channel     = data.get("channel", "?")
        name        = sensor_cfg.get("name",   f"Sensor {sensor_id}")
        follow      = sensor_cfg.get("follow", False)

        if not follow:
            log.debug(f"Ignored: {name} (ID={sensor_id})")
            continue

        # Followed sensor must have a temperature reading
        if temperature is None:
            log.warning(
                f"Sensor '{name}' (ID={sensor_id}) is marked follow=true "
                f"but has no temperature reading — skipped."
            )
            continue

        ha.push_sensor(sensor_id, name, temperature,
                       humidity, battery, model, channel)

        # Low battery — notify once until battery recovers
        if battery == 0 and sensor_id not in battery_alerted:
            ha.notify_low_battery(sensor_id, name)
            battery_alerted.add(sensor_id)
        elif battery == 1 and sensor_id in battery_alerted:
            battery_alerted.discard(sensor_id)
            log.info(f"Battery recovered for {name} (ID={sensor_id})")

    log.info("Scan cycle complete.")


def run_scheduler() -> None:
    """Run scan_and_push on a fixed interval."""
    log.info(f"Scheduler started — scan every {SCAN_INTERVAL}s.")
    scan_and_push()                                      # Run immediately
    schedule.every(SCAN_INTERVAL).seconds.do(scan_and_push)
    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    log.info("RTL-433 Sensor Bridge starting...")
    log.info(f"Scan interval : {SCAN_INTERVAL}s")
    log.info(f"HA URL        : {HA_URL}")
    log.info(f"Config file   : {CONFIG_FILE}")

    # Skip historical data — only process new readings from now on
    reset_position()

    # Web configuration panel in a background thread
    web_thread = threading.Thread(
        target=start_web,
        args=(CONFIG_FILE,),
        daemon=True
    )
    web_thread.start()

    # Scheduler in main thread
    run_scheduler()
