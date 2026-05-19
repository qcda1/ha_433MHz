"""
main.py
RTL-433 Sensor Bridge — Main entry point.
Scheduler that periodically reads 433MHz sensors and pushes
data to Home Assistant via REST API.
Web configuration panel served via Bottle.
"""

import os
import logging
import schedule
import time
import threading
import json

from rtl_reader   import read_sensors
from ha_api       import HAClient
from sensor_store import load_config, register_sensor
from web_server   import start_web

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = os.environ.get("LOG_FILE", "/config/rtl433_bridge.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# Read add-on options from HAOS Supervisor
_options = {}
_options_path = "/data/options.json"
if os.path.exists(_options_path):
    with open(_options_path) as f:
        _options = json.load(f)

SCAN_INTERVAL = int(_options.get("scan_interval", 300))
SCAN_DURATION = int(_options.get("scan_duration", 90))
FREQUENCY     = int(_options.get("frequency",     433920000))
HA_URL        = _options.get("ha_url",   "http://homeassistant:8123")
HA_TOKEN      = _options.get("ha_token", "")
CONFIG_FILE   = "/config/rtl433_sensors.yaml"
LOG_FILE      = "/config/rtl433_bridge.log"

# Track sensors that already triggered a low-battery alert
battery_alerted: set = set()


def scan_and_push() -> None:
    """
    Core task: scan 433MHz, register all devices, push followed
    temperature sensors to Home Assistant.
    """
    log.info("=" * 60)
    log.info("Scan cycle starting...")

    config = load_config(CONFIG_FILE)
    ha     = HAClient(HA_URL, HA_TOKEN)

    devices = read_sensors(SCAN_DURATION, FREQUENCY)

    if not devices:
        log.warning("No devices detected during this scan cycle.")
        return

    for sensor_id, data in devices.items():
        sensor_cfg  = register_sensor(config, data, CONFIG_FILE)

        temperature = data.get("temperature_C")
        humidity    = data.get("humidity")
        battery     = data.get("battery_ok", 1)
        model       = data.get("model", "unknown")
        channel     = data.get("channel", "?")
        name        = sensor_cfg.get("name",   f"Sensor {sensor_id}")
        follow      = sensor_cfg.get("follow", False)

        if not follow:
            log.debug(f"Ignored: {name} (ID={sensor_id})")
            continue

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
    """Run the scan on a fixed interval."""
    log.info(f"Scheduler started — scan every {SCAN_INTERVAL}s.")
    scan_and_push()
    schedule.every(SCAN_INTERVAL).seconds.do(scan_and_push)
    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    log.info("RTL-433 Sensor Bridge starting...")
    log.info(f"Scan interval : {SCAN_INTERVAL}s")
    log.info(f"Scan duration : {SCAN_DURATION}s")
    log.info(f"Frequency     : {FREQUENCY} Hz")
    log.info(f"HA URL        : {HA_URL}")
    log.info(f"Config file   : {CONFIG_FILE}")

    # Web panel in background thread
    web_thread = threading.Thread(
        target=start_web,
        args=(CONFIG_FILE,),
        daemon=True
    )
    web_thread.start()

    # Scheduler in main thread
    run_scheduler()
