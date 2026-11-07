"""
sensor_store.py
Persistent sensor registry stored as YAML.

Design notes
------------
- Every read-modify-write goes through a module-level RLock, so the web
  panel thread and the scanner thread never interleave on the same file.
- Writes are atomic: content goes to a temp file in the same directory,
  is flushed and fsynced, then renamed over the target. A crash or a
  container kill can never leave a truncated YAML file behind.
- User-managed fields (name, follow) always win over incoming telemetry.
  The scanner re-reads the file immediately before writing and merges,
  so a toggle made in the web UI mid-cycle is never clobbered.
- An unexpected follow=true -> false transition is logged as a warning,
  so a silent reset leaves a trace instead of going unnoticed for days.
"""

import os
import tempfile
import threading
import logging
import yaml
from datetime import datetime

log = logging.getLogger(__name__)

# Fields the user owns — never overwritten by rtl_433 telemetry
USER_FIELDS = ("name", "follow")

# Guards every read-modify-write sequence on the YAML file
_lock = threading.RLock()

# Last known follow state per sensor, used to detect unexpected resets
_follow_snapshot: dict = {}

# Sensor IDs whose follow flag was just changed on purpose (web UI),
# so the integrity check does not flag our own write as suspicious.
_intentional_follow_changes: set = set()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _resolve_key(sensors: dict, sensor_id):
    """
    Return the key that actually exists in <sensors> for this sensor ID.

    rtl_433 emits IDs as int (79, 2029) or str ('E', '09acff'), and the
    web panel always sends them as str. Try the value as given, then as
    str, then as int.
    """
    if sensor_id in sensors:
        return sensor_id

    str_id = str(sensor_id)
    if str_id in sensors:
        return str_id

    try:
        int_id = int(sensor_id)
        if int_id in sensors:
            return int_id
    except (ValueError, TypeError):
        pass

    return sensor_id          # Not found — caller treats it as new


def _check_follow_integrity(config: dict) -> None:
    """
    Compare the follow flags just read from disk against the last state we
    knew about. Any true -> false transition we did not make ourselves is
    logged loudly: it means the file was corrupted, hand-edited, or
    rewritten by another process.
    """
    global _follow_snapshot

    sensors = config.get("sensors", {})
    current = {str(sid): bool(d.get("follow", False))
               for sid, d in sensors.items()}

    for sid, was_followed in _follow_snapshot.items():
        if not was_followed:
            continue
        if sid in _intentional_follow_changes:
            continue
        if sid not in current:
            log.warning(
                f"INTEGRITY: sensor {sid} had follow=true but has "
                f"disappeared from the registry."
            )
        elif not current[sid]:
            log.warning(
                f"INTEGRITY: sensor {sid} had follow=true but now reads "
                f"follow=false, and no web UI change was made. The registry "
                f"may have been corrupted or edited externally."
            )

    _intentional_follow_changes.clear()
    _follow_snapshot = current


# ── Public API ────────────────────────────────────────────────────────────────

def load_config(config_file: str) -> dict:
    """Load the registry from YAML, creating an empty one if needed."""
    with _lock:
        if not os.path.exists(config_file):
            default = {"sensors": {}}
            save_config(default, config_file)
            log.info(f"Created new config file: {config_file}")
            return default

        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            # Never silently start from scratch — that would wipe the
            # user's names and follow flags on the next write.
            log.error(f"Config file is not valid YAML: {e}")
            raise

        if "sensors" not in config or not isinstance(config["sensors"], dict):
            log.warning("Config file has no usable 'sensors' section — "
                        "treating it as empty.")
            config["sensors"] = {}

        _check_follow_integrity(config)
        return config


def save_config(config: dict, config_file: str) -> None:
    """
    Write the registry atomically: temp file in the same directory,
    fsync, then rename over the target.
    """
    with _lock:
        directory = os.path.dirname(config_file) or "."
        os.makedirs(directory, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(dir=directory,
                                        prefix=".rtl433_sensors_",
                                        suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                yaml.dump(config, f,
                          default_flow_style=False,
                          allow_unicode=True,
                          sort_keys=True)
                f.flush()
                os.fsync(f.fileno())

            # Atomic on POSIX: readers see either the old file or the
            # new one in full, never a partial write.
            os.replace(tmp_path, config_file)

        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            raise


def apply_scan_results(devices: dict, config_file: str) -> dict:
    """
    Merge a full scan cycle into the registry in a single atomic write.

    <devices> is {sensor_id: raw_rtl_433_dict}. For each device the native
    rtl_433 fields are refreshed while name and follow are preserved from
    whatever is currently on disk — which may include a toggle the user
    made in the web UI since this cycle started.

    Returns the merged registry so the caller can read name/follow without
    a second read.
    """
    with _lock:
        config  = load_config(config_file)
        sensors = config["sensors"]

        new_count = 0

        for sensor_id, data in devices.items():
            key      = _resolve_key(sensors, sensor_id)
            is_new   = key not in sensors
            existing = sensors.get(key, {})

            entry = dict(existing)

            # User-managed fields: keep what is on disk, default on first sight
            entry["name"]   = existing.get("name", f"Unknown sensor {key}")
            entry["follow"] = existing.get("follow", False)

            # Telemetry: every native rtl_433 field except id and time
            for field, value in data.items():
                if field in ("id", "time"):
                    continue
                entry[field] = value

            entry["last_reception"] = data.get(
                "time",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            sensors[key] = entry

            if is_new:
                new_count += 1
                log.info(
                    f"New sensor registered: ID={key} | "
                    f"{data.get('model', 'unknown')} | "
                    f"channel={data.get('channel', '?')} | "
                    f"temp={data.get('temperature_C')}°C | "
                    f"hum={data.get('humidity')}%"
                )

        save_config(config, config_file)

        if new_count:
            log.info(f"{new_count} new sensor(s) added to the registry.")

        # Refresh the snapshot from what we just wrote, so the next read
        # compares against reality rather than a pre-merge state.
        _follow_snapshot.update({
            str(sid): bool(d.get("follow", False))
            for sid, d in sensors.items()
        })

        return config


def get_sensor(config: dict, sensor_id) -> dict:
    """Return one sensor's entry, matching int or str keys."""
    sensors = config.get("sensors", {})
    return sensors.get(_resolve_key(sensors, sensor_id), {})


def update_sensor_field(config: dict, sensor_id, field: str,
                        value, config_file: str) -> bool:
    """
    Update a single user-managed field (called by the web panel).

    The <config> argument is accepted for backwards compatibility but is
    ignored: the file is re-read under the lock so the write is always
    based on the current content, never on a stale copy.
    """
    with _lock:
        fresh   = load_config(config_file)
        sensors = fresh["sensors"]
        key     = _resolve_key(sensors, sensor_id)

        if key not in sensors:
            log.warning(f"Sensor ID={sensor_id} not found in registry.")
            return False

        if field == "follow":
            # Mark it so the integrity check does not flag our own change
            _intentional_follow_changes.add(str(key))

        sensors[key][field] = value
        save_config(fresh, config_file)

        _follow_snapshot[str(key)] = bool(sensors[key].get("follow", False))

        log.info(f"Sensor ID={key}: {field} set to {value}")
        return True
