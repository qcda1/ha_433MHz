"""
sensor_store.py
Manages persistent sensor configuration in a YAML file.
"""

import yaml
import os
import logging
from datetime import datetime

log = logging.getLogger(__name__)


def load_config(config_file: str) -> dict:
    """Load sensor config from YAML, create it if it does not exist."""
    if not os.path.exists(config_file):
        default = {"sensors": {}}
        with open(config_file, "w") as f:
            yaml.dump(default, f, default_flow_style=False)
        log.info(f"Created new config file: {config_file}")

    with open(config_file, "r") as f:
        return yaml.safe_load(f) or {"sensors": {}}


def save_config(config: dict, config_file: str) -> None:
    """Save sensor config to YAML."""
    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def register_sensor(config: dict, data: dict, config_file: str) -> dict:
    """
    Add or update a sensor entry in the YAML config.
    Preserves user-defined fields (name, follow).
    Stores all native rtl_433 fields as-is.
    Returns the sensor config dict.
    """
    sensor_id = data.get("id")
    time_str  = data.get("time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    is_new = sensor_id not in config["sensors"]
    sensor = config["sensors"].get(sensor_id, {})

    # User-managed fields — never overwritten by incoming data
    sensor_update = {
        "name"          : sensor.get("name", f"Unknown sensor {sensor_id}"),
        "follow"        : sensor.get("follow", False),
        "last_reception": time_str,
    }

    # All native rtl_433 fields except id and time
    excluded = {"id", "time"}
    for key, value in data.items():
        if key not in excluded:
            sensor_update[key] = value

    sensor.update(sensor_update)
    config["sensors"][sensor_id] = sensor
    save_config(config, config_file)

    if is_new:
        temp    = data.get("temperature_C")
        hum     = data.get("humidity")
        model   = data.get("model", "unknown")
        channel = data.get("channel", "?")
        log.info(
            f"New sensor registered: ID={sensor_id} | {model} | "
            f"channel={channel} | temp={temp}°C | hum={hum}%"
        )

    return sensor


def get_sensor(config: dict, sensor_id) -> dict:
    """Return sensor config by ID."""
    return config["sensors"].get(sensor_id, {})


def update_sensor_field(config: dict, sensor_id, field: str,
                        value, config_file: str) -> bool:
    """Update a single user-managed field for a sensor."""
    if sensor_id not in config["sensors"]:
        log.warning(f"Sensor ID={sensor_id} not found in config.")
        return False
    config["sensors"][sensor_id][field] = value
    save_config(config, config_file)
    log.info(f"Sensor ID={sensor_id}: {field} set to {value}")
    return True
