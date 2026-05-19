"""
rtl_reader.py
Reads sensor data from the JSON output file produced by the
pbkhrv/rtl_433 Home Assistant add-on.

Architecture:
    RTL-SDR → pbkhrv/rtl_433 add-on → /config/rtl_433_output.json → this module

The pbkhrv add-on handles all USB access and kernel driver management.
This module simply tails the JSON file for new readings since the last call.
"""

import os
import json
import logging

log = logging.getLogger(__name__)

# Path to the JSON output file produced by pbkhrv/rtl_433 add-on
RTL_JSON_FILE = "/config/rtl_433_output.json"

# Track file position between calls — module-level state
_last_position: int = 0


def read_sensors() -> dict:
    """
    Read new sensor data from the rtl_433 JSON output file.

    Returns a dict of {sensor_id: raw_data} with the last reading
    per sensor ID since the previous call. Returns empty dict if
    no new data or file not found.
    """
    global _last_position

    if not os.path.exists(RTL_JSON_FILE):
        log.warning(f"JSON output file not found: {RTL_JSON_FILE}")
        log.warning("Is the pbkhrv/rtl_433 add-on installed and running?")
        return {}

    devices_seen = {}

    try:
        with open(RTL_JSON_FILE, "r") as f:
            # Jump to last known position — only read new lines
            f.seek(_last_position)
            new_lines  = f.readlines()
            _last_position = f.tell()

        if not new_lines:
            log.debug("No new data in JSON file since last read.")
            return {}

        for line in new_lines:
            line = line.strip()
            if not line:
                continue
            try:
                data      = json.loads(line)
                sensor_id = data.get("id")
                if sensor_id is None:
                    continue

                # Keep only the last reading per sensor in this batch
                devices_seen[sensor_id] = data

                temp    = data.get("temperature_C")
                hum     = data.get("humidity")
                model   = data.get("model", "?")
                channel = data.get("channel", "?")
                battery = data.get("battery_ok", 1)

                log.info(
                    f"Received: ID={sensor_id} | {model} | "
                    f"channel={channel} | "
                    f"temp={temp}°C | "
                    f"hum={hum if hum is not None else 'N/A'}% | "
                    f"battery={'OK' if battery else 'LOW'}"
                )

            except json.JSONDecodeError as e:
                log.warning(f"Invalid JSON line skipped: {e}")

        if devices_seen:
            log.info(f"Scan complete — {len(devices_seen)} device(s) detected.")

    except OSError as e:
        log.error(f"Error reading JSON file: {e}")

    return devices_seen


def reset_position() -> None:
    """
    Seek to the end of the JSON file so we only process
    readings that arrive after startup — ignores historical data.
    Call this once at application startup.
    """
    global _last_position
    if os.path.exists(RTL_JSON_FILE):
        with open(RTL_JSON_FILE, "r") as f:
            f.seek(0, 2)  # Seek to end of file
            _last_position = f.tell()
        log.info(
            f"JSON file position reset to end "
            f"({_last_position} bytes skipped)."
        )
    else:
        log.warning(
            f"JSON file not found at startup: {RTL_JSON_FILE} — "
            f"will retry on first scan cycle."
        )
