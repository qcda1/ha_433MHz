"""
web_server.py
Bottle web application — sensor configuration panel.
Uses Bottle + Paste, consistent with Ha-image-viewer.
Served as a Home Assistant ingress panel on port 8099.
"""

import os
import json
import logging
import bottle
from bottle import Bottle, template, request, response, static_file

from sensor_store import load_config, update_sensor_field

log          = logging.getLogger(__name__)
app          = Bottle()
_config_file = None

# Fields managed by the user — shown as interactive controls
USER_FIELDS = {"name", "follow"}

# Fields to always exclude from the raw YAML display
EXCLUDED_FIELDS = {"name", "follow"}


def start_web(config_file: str) -> None:
    """Start the Bottle web server using Paste."""
    global _config_file
    _config_file = config_file
    log.info("Web configuration panel starting on port 8099...")
    bottle.run(
        app,
        server="paste",
        host="0.0.0.0",
        port=8099,
        quiet=True,
    )

def get_base_path():
    """Get ingress prefix from HA header X-Ingress-Path."""
    ingress_path = request.headers.get('X-Ingress-Path', '')
    if ingress_path:
        if not ingress_path.endswith('/'):
            ingress_path += '/'
        return ingress_path
    return '/'

@app.route("/")
def index():
    config    = load_config(_config_file)
    base_path = get_base_path()
    sensors   = []
    # ... reste inchangé ...
    return template("index", sensors=sensors, base_path=base_path)


@app.route("/")
def index():
    config  = load_config(_config_file)
    sensors = []

    for sid, data in config.get("sensors", {}).items():
        # Build the raw YAML fields — everything except user-managed fields
        raw_fields = {
            k: v for k, v in data.items()
            if k not in EXCLUDED_FIELDS
        }
        sensors.append({
            "id"        : sid,
            "name"      : data.get("name",   f"Unknown sensor {sid}"),
            "follow"    : data.get("follow",  False),
            "battery_ok": data.get("battery_ok", 1),
            "has_temp"  : data.get("temperature_C") is not None,
            "raw"       : raw_fields,
        })

    # Sort: followed first, then by last_reception descending
    sensors.sort(
        key=lambda s: (
            not s["follow"],
            s["raw"].get("last_reception", ""),
        ),
        reverse=False,
    )

    return template("index", sensors=sensors)


@app.route("/api/sensor/<sensor_id>/follow", method="POST")
def toggle_follow(sensor_id):
    response.content_type = "application/json"
    try:
        body   = json.loads(request.body.read())
        follow = bool(body.get("follow", False))
        config = load_config(_config_file)
        ok     = update_sensor_field(config, sensor_id, "follow",
                                     follow, _config_file)
        if ok:
            return json.dumps({"status": "ok", "follow": follow})
        response.status = 404
        return json.dumps({"status": "error", "message": "Sensor not found"})
    except Exception as e:
        log.error(f"toggle_follow error: {e}")
        response.status = 500
        return json.dumps({"status": "error", "message": str(e)})


@app.route("/api/sensor/<sensor_id>/name", method="POST")
def update_name(sensor_id):
    response.content_type = "application/json"
    try:
        body = json.loads(request.body.read())
        name = body.get("name", "").strip()
        if not name:
            response.status = 400
            return json.dumps({"status": "error",
                               "message": "Name cannot be empty"})
        config = load_config(_config_file)
        ok     = update_sensor_field(config, sensor_id, "name",
                                     name, _config_file)
        if ok:
            return json.dumps({"status": "ok", "name": name})
        response.status = 404
        return json.dumps({"status": "error", "message": "Sensor not found"})
    except Exception as e:
        log.error(f"update_name error: {e}")
        response.status = 500
        return json.dumps({"status": "error", "message": str(e)})


@app.route("/api/sensors")
def list_sensors():
    response.content_type = "application/json"
    config = load_config(_config_file)
    return json.dumps(config.get("sensors", {}))
