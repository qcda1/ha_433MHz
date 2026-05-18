"""
ha_api.py
Handles all interactions with the Home Assistant REST API.
"""

import requests
import logging

log = logging.getLogger(__name__)


class HAClient:
    """Simple Home Assistant REST API client."""

    def __init__(self, ha_url: str, ha_token: str):
        self.ha_url = ha_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json",
        }

    def _post(self, endpoint: str, payload: dict) -> bool:
        """POST to HA API. Returns True on success."""
        url = f"{self.ha_url}/api/{endpoint}"
        try:
            r = requests.post(url, headers=self.headers,
                              json=payload, timeout=10)
            if r.status_code in (200, 201):
                return True
            log.error(f"HA API error {r.status_code} on {endpoint}: {r.text}")
            return False
        except requests.RequestException as e:
            log.error(f"HA API request failed: {e}")
            return False

    def push_sensor(self, sensor_id, name: str, temperature: float,
                    humidity, battery_ok: int, model: str, channel) -> None:
        """Create or update temperature, humidity and battery entities in HA."""

        battery_low = battery_ok == 0

        # Temperature — always sent
        self._post(
            f"states/sensor.rtl433_{sensor_id}_temperature",
            {
                "state": temperature,
                "attributes": {
                    "unit_of_measurement": "°C",
                    "friendly_name"      : f"{name} Temperature",
                    "device_class"       : "temperature",
                    "state_class"        : "measurement",
                    "battery_low"        : battery_low,
                    "model"              : model,
                    "channel"            : str(channel),
                },
            },
        )

        # Humidity — only if available
        if humidity is not None:
            self._post(
                f"states/sensor.rtl433_{sensor_id}_humidity",
                {
                    "state": humidity,
                    "attributes": {
                        "unit_of_measurement": "%",
                        "friendly_name"      : f"{name} Humidity",
                        "device_class"       : "humidity",
                        "state_class"        : "measurement",
                        "battery_low"        : battery_low,
                        "model"              : model,
                        "channel"            : str(channel),
                    },
                },
            )

        # Battery binary sensor
        self._post(
            f"states/binary_sensor.rtl433_{sensor_id}_battery",
            {
                "state": "on" if battery_low else "off",
                "attributes": {
                    "friendly_name": f"{name} Low battery",
                    "device_class" : "battery",
                    "model"        : model,
                    "channel"      : str(channel),
                },
            },
        )

        hum_str = f"{humidity}%" if humidity is not None else "N/A"
        log.info(
            f"Pushed to HA: {name} (ID={sensor_id}) | "
            f"{temperature}°C | {hum_str} | "
            f"battery={'LOW' if battery_low else 'OK'}"
        )

    def send_persistent_notification(self, title: str, message: str) -> None:
        """Create a persistent notification in HA."""
        self._post(
            "services/persistent_notification/create",
            {"title": title, "message": message},
        )

    def send_mobile_notification(self, title: str, message: str) -> None:
        """Send a mobile push notification via HA notify service."""
        self._post(
            "services/notify/notify",
            {"title": title, "message": message},
        )

    def notify_low_battery(self, sensor_id, name: str) -> None:
        """Send both persistent and mobile notifications for low battery."""
        title   = "RTL-433: Low battery warning"
        message = f"Sensor '{name}' (ID={sensor_id}) has a low battery."
        self.send_persistent_notification(title, message)
        self.send_mobile_notification(title, message)
        log.warning(f"Low battery notification sent for {name} (ID={sensor_id})")
