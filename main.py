"""SolarEdge MQTT Bridge - Reads data from SolarEdge energy meter via Modbus 
and publishes to MQTT broker, storing last known values if data retrieval fails.
"""

import logging
import time
from datetime import datetime
import yaml
from pymodbus.client import ModbusTcpClient  # Direct import to avoid pylint error
from paho.mqtt import client as mqtt_client
from collections import deque
import os
import json
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SolarEdgeReader")

# Load configuration file
with open("config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# Modbus settings
MODBUS_HOST = config['modbus']['host']
MODBUS_PORT = config['modbus']['port']
MODBUS_UNIT_ID = config['modbus']['unit_id']

# MQTT settings
MQTT_BROKER = os.getenv("MQTT_BROKER", config['mqtt']['broker'])
MQTT_PORT = int(os.getenv("MQTT_PORT", config['mqtt']['port']))
MQTT_TOPIC = config['mqtt']['topic']
MQTT_USERNAME = os.getenv("MQTT_USERNAME", config['mqtt'].get('username'))
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", config['mqtt'].get('password'))

# General settings
INTERVAL = int(os.getenv("INTERVAL", config['general']['interval']))
RECONNECT_ATTEMPTS = int(os.getenv("RECONNECT_ATTEMPTS", config['general']['reconnect_attempts']))
RECONNECT_DELAY = int(os.getenv("RECONNECT_DELAY", config['general']['reconnect_delay']))

# Optional API settings
API_ENABLED = config['api'].get('enabled', False)
API_PORT = int(config['api'].get('port', 5000))

# Ring buffer for last 5 known values
last_known_values = deque(maxlen=5)
last_known_timestamp = None
status = "OK"

# Initialize Flask app if API is enabled
app = Flask(__name__) if API_ENABLED else None


def connect_mqtt():
    """Connect to MQTT broker and return client instance."""
    client = mqtt_client.Client()
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    def on_connect(_client, _userdata, _flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT Broker")
        else:
            logger.error("Failed to connect to MQTT Broker. Code: %d", rc)

    def on_disconnect(_client, _userdata, rc):
        logger.warning("Disconnected from MQTT Broker, attempting to reconnect")
        reconnect_mqtt(client)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(MQTT_BROKER, MQTT_PORT)
    return client


def reconnect_mqtt(client):
    """Reconnect to the MQTT broker with retry logic."""
    for attempt in range(RECONNECT_ATTEMPTS):
        try:
            client.reconnect()
            logger.info("Reconnected to MQTT Broker")
            return
        except Exception as e:
            logger.error("Reconnect attempt %d failed: %s", attempt + 1, e)
            time.sleep(RECONNECT_DELAY)


def fetch_device_info(modbus_client):
    """Fetch device information such as serial number, manufacturer, and model."""
    info = {}
    try:
        # Example register addresses; replace these with actual addresses from SolarEdge documentation
        info['serial_number'] = modbus_client.read_input_registers(40000, 2, unit=MODBUS_UNIT_ID).registers
        info['model'] = modbus_client.read_input_registers(40010, 2, unit=MODBUS_UNIT_ID).registers
        info['manufacturer'] = modbus_client.read_input_registers(40020, 2, unit=MODBUS_UNIT_ID).registers
    except Exception as e:
        logger.error("Error fetching device information: %s", e)
    return info


def fetch_data(modbus_client):
    """Fetch data from Modbus and return a dictionary of values, or last known values if fetch fails."""
    global last_known_timestamp, status
    data = {}
    try:
        # Fetch data from Modbus registers
        data['energy'] = modbus_client.read_input_registers(
            100, 2, unit=MODBUS_UNIT_ID).registers  # Example for energy consumption
        data['power'] = modbus_client.read_input_registers(
            200, 2, unit=MODBUS_UNIT_ID).registers  # Example for current power

        # Update last known values and timestamp
        last_known_values.append(data)
        last_known_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "OK"
    except (ConnectionError, ValueError) as e:
        logger.error("Error fetching data: %s", e)
        # Use last known values if fetch fails
        if last_known_values:
            data = last_known_values[-1]
            status = "Last value"
        else:
            status = "Error"
            last_known_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return data


def publish_data(mqtt_client_instance, data):
    """Publish fetched data along with timestamp and status to the MQTT broker."""
    global last_known_timestamp, status

    # Publish data with timestamp and status
    for key, values in data.items():
        payload = {
            "data": values,
            "timestamp": last_known_timestamp,
            "status": status
        }
        mqtt_client_instance.publish(f"{MQTT_TOPIC}/data/{key}", json.dumps(payload))


def main():
    """Main program to fetch and publish data periodically."""
    mqtt_client_instance = connect_mqtt()
    mqtt_client_instance.loop_start()
    modbus_client = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)

    # Fetch device information once at startup
    device_info = fetch_device_info(modbus_client)
    logger.info("Device Info: %s", device_info)
    mqtt_client_instance.publish(f"{MQTT_TOPIC}/device_info", json.dumps(device_info))

    try:
        while True:
            if not modbus_client.connect():
                logger.warning("Modbus connection failed, retrying...")
                for _ in range(RECONNECT_ATTEMPTS):
                    if modbus_client.connect():
                        break
                    time.sleep(RECONNECT_DELAY)
                else:
                    logger.error("Failed to reconnect, exiting.")
                    break
            
            # Fetch data and publish via MQTT
            data = fetch_data(modbus_client)
            publish_data(mqtt_client_instance, data)
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        mqtt_client_instance.loop_stop()
        modbus_client.close()


if API_ENABLED:
    @app.route('/data', methods=['GET'])
    def get_data():
        """Endpoint to get current data in JSON format."""
        return jsonify({
            "last_known_values": list(last_known_values),
            "timestamp": last_known_timestamp,
            "status": status
        })

    def run_api():
        """Run the API server."""
        app.run(host="0.0.0.0", port=API_PORT)


if __name__ == "__main__":
    if API_ENABLED:
        from threading import Thread
        api_thread = Thread(target=run_api)
        api_thread.start()
    main()
