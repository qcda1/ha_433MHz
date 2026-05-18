"""
web/server.py
Flask web application — sensor configuration panel.
Served as a Home Assistant ingress panel.
"""

from flask import Flask, render_template, request, jsonify
import logging

from sensor_store import load_config, update_sensor_field

log = logging.getLogger(__name__)


def create_app(config_file: str) -> Flask:
    app = Flask(__name__, template_folder="templates",
                static_folder="static")
    app.config["CONFIG_FILE"] = config_file

    @app.route("/")
    def index():
        config  = load_config(config_file)
        sensors = []
        for sid, data in config.get("sensors", {}).items():
            sensors.append({
                "id"              : sid,
                "name"            : data.get("name", f"Unknown {sid}"),
                "follow"          : data.get("follow", False),
                "model"           : data.get("model", "—"),
                "channel"         : data.get("channel", "—"),
                "temperature_C"   : data.get("temperature_C"),
                "humidity"        : data.get("humidity"),
                "battery_ok"      : data.get("battery_ok", 1),
                "last_reception"  : data.get("last_reception", "—"),
            })
        # Sort: followed sensors first, then by last reception desc
        sensors.sort(key=lambda s: (not s["follow"], s["last_reception"]),
                     reverse=False)
        return render_template("index.html", sensors=sensors)

    @app.route("/api/sensor/<sensor_id>/follow", methods=["POST"])
    def toggle_follow(sensor_id):
        """Toggle the follow flag for a sensor."""
        body   = request.get_json()
        follow = bool(body.get("follow", False))
        config = load_config(config_file)
        ok     = update_sensor_field(config, sensor_id, "follow",
                                     follow, config_file)
        if ok:
            return jsonify({"status": "ok", "follow": follow})
        return jsonify({"status": "error", "message": "Sensor not found"}), 404

    @app.route("/api/sensor/<sensor_id>/name", methods=["POST"])
    def update_name(sensor_id):
        """Update the display name for a sensor."""
        body = request.get_json()
        name = body.get("name", "").strip()
        if not name:
            return jsonify({"status": "error",
                            "message": "Name cannot be empty"}), 400
        config = load_config(config_file)
        ok     = update_sensor_field(config, sensor_id, "name",
                                     name, config_file)
        if ok:
            return jsonify({"status": "ok", "name": name})
        return jsonify({"status": "error", "message": "Sensor not found"}), 404

    @app.route("/api/sensors")
    def list_sensors():
        """Return all sensors as JSON."""
        config = load_config(config_file)
        return jsonify(config.get("sensors", {}))

    return app
