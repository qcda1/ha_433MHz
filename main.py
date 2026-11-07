"""
main.py
RTL-433 Sensor Bridge — Main entry point.

Reads sensor data from the JSON file produced by the pbkhrv/rtl_433
Home Assistant add-on, registers all detected devices in a YAML registry,
and pushes followed temperature sensors to Home Assistant via the REST API.

A Bottle web panel (port 8099) allows naming sensors and toggling
which ones are followed in Home Assistant.

Architecture:
    pbkhrv/rtl_433 add-on → /config/rtl_433/rtl_433_output.json
        → this app → HA REST API
"""

import json
import os
import logging
import schedule
import time
import threading
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

from rtl_reader   import read_sensors, reset_position, trim_json_file
from ha_api       import HAClient
from sensor_store import apply_scan_results, get_sensor
from web_server   import start_web

# ── Read add-on options from HAOS Supervisor ──────────────────────────────────
_options: dict = {}
_options_path  = "/data/options.json"

if os.path.exists(_options_path):
    with open(_options_path) as _f:
        _options = json.load(_f)

SCAN_INTERVAL = int(_options.get("scan_interval", 60))
LOG_LEVEL_STR = _options.get("log_level", "INFO").upper()
HA_URL        = _options.get("ha_url",   "http://homeassistant:8123")
HA_TOKEN      = _options.get("ha_token", "")
CONFIG_FILE   = "/config/rtl_433/rtl433_sensors.yaml"
LOG_FILE      = "/config/rtl_433/rtl433_bridge.log"

LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

# Alert when no sensor data has arrived for this long
STALE_THRESHOLD_MIN = 30

# ── Logging (rotating: 1 MB x 4 files max) ────────────────────────────────────
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        RotatingFileHandler(
            LOG_FILE,
            maxBytes=1 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

log.info("RTL-433 Sensor Bridge starting...")

# Sensors that already triggered a low-battery alert, cleared on recovery
battery_alerted: set = set()

# Data-flow watchdog state
_last_data_time = datetime.now()
_stale_alerted  = False


def check_data_freshness(ha: HAClient) -> None:
    """Notify once if no sensor data has been received for a while."""
    global _stale_alerted

    elapsed = datetime.now() - _last_data_time
    minutes = int(elapsed.total_seconds() / 60)

    if elapsed > timedelta(minutes=STALE_THRESHOLD_MIN):
        if not _stale_alerted:
            title = "RTL-433: no sensor data"
            msg   = (f"No 433 MHz data received for {minutes} minutes. "
                     f"Check the rtl_433 add-on and the SDR dongle.")
            ha.send_persistent_notification(title, msg)
            ha.send_mobile_notification(title, msg)
            _stale_alerted = True
            log.warning(f"Stale data alert sent — {minutes} min without readings.")
    elif _stale_alerted:
        _stale_alerted = False
        log.info("Data flow recovered.")


def scan_and_push() -> None:
    """
    One cycle: read new data from the rtl_433 JSON file, merge the whole
    batch into the registry in a single atomic write, then push followed
    temperature sensors to Home Assistant.
    """
    global _last_data_time

    log.info("=" * 60)
    log.info("Scan cycle starting...")

    ha = HAClient(HA_URL, HA_TOKEN)

    # Keep the rtl_433 output file from growing without bound
    trim_json_file(max_size_mb=10)

    devices = read_sensors()

    if not devices:
        log.debug("No new sensor data in this scan cycle.")
        check_data_freshness(ha)
        return

    _last_data_time = datetime.now()
    check_data_freshness(ha)          # clears a pending stale alert

    # Single read-merge-write for the whole batch, under the store lock.
    # Returns the merged registry, so name/follow come from what is
    # actually on disk right now — including any web UI toggle made
    # while this cycle was running.
    config = apply_scan_results(devices, CONFIG_FILE)

    for sensor_id, data in devices.items():
        sensor_cfg = get_sensor(config, sensor_id)

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

        if temperature is None:
            log.warning(
                f"Sensor '{name}' (ID={sensor_id}) is marked follow=true "
                f"but has no temperature reading — skipped."
            )
            continue

        ha.push_sensor(sensor_id, name, temperature,
                       humidity, battery, model, channel)

        # Low battery — notify once until the battery recovers
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
    scan_and_push()
    schedule.every(SCAN_INTERVAL).seconds.do(scan_and_push)
    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    log.info("RTL-433 Sensor Bridge starting...")
    log.info(f"Scan interval : {SCAN_INTERVAL}s")
    log.info(f"Log level     : {LOG_LEVEL_STR}")
    log.info(f"HA URL        : {HA_URL}")
    log.info(f"Config file   : {CONFIG_FILE}")

    # Skip historical data — only process readings from now on
    reset_position()

    # Web configuration panel in a background thread
    web_thread = threading.Thread(
        target=start_web,
        args=(CONFIG_FILE,),
        daemon=True,
    )
    web_thread.start()

    run_scheduler()
