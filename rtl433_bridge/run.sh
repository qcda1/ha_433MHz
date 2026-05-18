#!/usr/bin/with-contenv bashio

bashio::log.info "Starting RTL-433 Sensor Bridge..."

# Export add-on options as environment variables
export SCAN_INTERVAL=$(bashio::config 'scan_interval')
export SCAN_DURATION=$(bashio::config 'scan_duration')
export FREQUENCY=$(bashio::config 'frequency')
export HA_URL=$(bashio::config 'ha_url')
export HA_TOKEN=$(bashio::config 'ha_token')

bashio::log.info "Scan interval : ${SCAN_INTERVAL}s"
bashio::log.info "Scan duration : ${SCAN_DURATION}s"
bashio::log.info "Frequency     : ${FREQUENCY} Hz"

# Sensors config file location (persistent in /config)
export CONFIG_FILE="/config/rtl433_sensors.yaml"
export LOG_FILE="/config/rtl433_bridge.log"

bashio::log.info "Sensors config: ${CONFIG_FILE}"

# Start the main Python application
exec python3 /app/main.py
