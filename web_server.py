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

log    = logging.getLogger(__name__)
app    = Bottle()
_config_file = None


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


@app.route("/static/<filepath:path>")
def serve_static(filepath):
    return static_file(filepath, root="/app/static")


@app.route("/")
def index():
    config  = load_config(_config_file)
    sensors = []
    for sid, data in config.get("sensors", {}).items():
        sensors.append({
            "id"            : sid,
            "name"          : data.get("name", f"Unknown {sid}"),
            "follow"        : data.get("follow", False),
            "model"         : data.get("model", "—"),
            "channel"       : data.get("channel", "—"),
            "temperature_C" : data.get("temperature_C"),
            "humidity"      : data.get("humidity"),
            "battery_ok"    : data.get("battery_ok", 1),
            "last_reception": data.get("last_reception", "—"),
        })
    sensors.sort(key=lambda s: (not s["follow"], s["last_reception"]))
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
        response.status = 500
        return json.dumps({"status": "error", "message": str(e)})


@app.route("/api/sensors")
def list_sensors():
    response.content_type = "application/json"
    config = load_config(_config_file)
    return json.dumps(config.get("sensors", {}))
