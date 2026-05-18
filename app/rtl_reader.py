"""
rtl_reader.py
Runs rtl_433 as a subprocess and parses its JSON output.
"""

import subprocess
import json
import logging

log = logging.getLogger(__name__)


def read_sensors(duration: int, frequency: int) -> dict:
    """
    Run rtl_433 for <duration> seconds on <frequency> Hz.
    Returns a dict of {sensor_id: raw_data} with the last
    reading per sensor.
    """
    cmd = [
        "rtl_433",
        "-f", str(frequency),
        "-F", "json",
        "-T", str(duration),
    ]

    log.info(f"Starting rtl_433 | freq={frequency}Hz | duration={duration}s")

    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=duration + 30,   # Safety margin
        )
    except subprocess.TimeoutExpired:
        log.error("rtl_433 timed out — check SDR hardware.")
        return {}
    except FileNotFoundError:
        log.error("rtl_433 not found — is it installed?")
        return {}

    devices_seen = {}

    for line in process.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data      = json.loads(line)
            sensor_id = data.get("id")
            if sensor_id is None:
                continue

            # Keep only the last reading per sensor
            devices_seen[sensor_id] = data

            temp    = data.get("temperature_C")
            hum     = data.get("humidity")
            model   = data.get("model", "?")
            channel = data.get("channel", "?")
            battery = data.get("battery_ok", 1)

            log.info(
                f"Received: ID={sensor_id} | {model} | channel={channel} | "
                f"temp={temp}°C | hum={hum if hum is not None else 'N/A'}% | "
                f"battery={'OK' if battery else 'LOW'}"
            )

        except json.JSONDecodeError:
            pass

    log.info(f"Scan complete — {len(devices_seen)} device(s) detected.")
    return devices_seen
