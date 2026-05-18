#!/usr/bin/with-contenv bash

echo "Starting RTL-433 Sensor Bridge..."

export SCAN_INTERVAL=$(python3 -c "import json; d=json.load(open('/data/options.json')); print(d.get('scan_interval', 300))")
export SCAN_DURATION=$(python3 -c "import json; d=json.load(open('/data/options.json')); print(d.get('scan_duration', 90))")
export FREQUENCY=$(python3 -c "import json; d=json.load(open('/data/options.json')); print(d.get('frequency', 433920000))")
export HA_URL=$(python3 -c "import json; d=json.load(open('/data/options.json')); print(d.get('ha_url', 'http://homeassistant:8123'))")
export HA_TOKEN=$(python3 -c "import json; d=json.load(open('/data/options.json')); print(d.get('ha_token', ''))")
export CONFIG_FILE="/config/rtl433_sensors.yaml"
export LOG_FILE="/config/rtl433_bridge.log"

exec python3 -u /app/main.py