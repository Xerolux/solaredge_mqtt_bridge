"""SolarEdge MQTT Bridge - Reads data from SolarEdge energy meter via Modbus and publishes to MQTT broker."""

import logging
import time
import yaml
from pymodbus.client.sync import ModbusTcpClient
from paho.mqtt import client as mqtt_client

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
MQTT_BROKER = config['mqtt']['broker']
MQTT_PORT = config['mqtt']['port']
MQTT_TOPIC = config['mqtt']['topic']
MQTT_USERNAME = config['mqtt'].get('username')
MQTT_PASSWORD = config['mqtt'].get('password')

# General settings
INTERVAL = config['general']['interval']
RECONNECT_ATTEMPTS = config['general']['reconnect_attempts']
RECONNECT_DELAY = config['general']['reconnect_delay']

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

    client.on_connect = on_connect
    client.connect(MQTT_BROKER, MQTT_PORT)
    return client

def fetch_data(modbus_client):
    """Fetch data from Modbus and return a dictionary of values."""
    data = {}
    try:
        data[1] = modbus_client.read_input_registers(
            100, 2, unit=MODBUS_UNIT_ID).registers  # Example for energy consumption
        data[2] = modbus_client.read_input_registers(
            200, 2, unit=MODBUS_UNIT_ID).registers  # Example for current power
        # Add other register addresses here...
    except (ConnectionError, ValueError) as e:
        logger.error("Error fetching data: %s", e)
    return data

def publish_data(mqtt_client_instance, data):
    """Publish fetched data to the MQTT broker."""
    for key, values in data.items():
        payload = f"{key}\n"
        for i, value in enumerate(values, 1):
            payload += f"{i}. Value: {value}\n"
        mqtt_client_instance.publish(f"{MQTT_TOPIC}/{key}", payload)

def main():
    """Main program to fetch and publish data periodically."""
    mqtt_client_instance = connect_mqtt()
    mqtt_client_instance.loop_start()
    modbus_client = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)

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

if __name__ == "__main__":
    main()
