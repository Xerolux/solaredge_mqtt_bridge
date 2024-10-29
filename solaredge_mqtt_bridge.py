import time
import yaml
from pymodbus.client.sync import ModbusTcpClient
from paho.mqtt import client as mqtt_client
import logging

# Logging einrichten
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SolarEdgeReader")

# Konfigurationsdatei laden
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# Modbus-Einstellungen
MODBUS_HOST = config['modbus']['host']
MODBUS_PORT = config['modbus']['port']
MODBUS_UNIT_ID = config['modbus']['unit_id']

# MQTT-Einstellungen
MQTT_BROKER = config['mqtt']['broker']
MQTT_PORT = config['mqtt']['port']
MQTT_TOPIC = config['mqtt']['topic']
MQTT_USERNAME = config['mqtt'].get('username')
MQTT_PASSWORD = config['mqtt'].get('password')

# Allgemeine Einstellungen
INTERVAL = config['general']['interval']
RECONNECT_ATTEMPTS = config['general']['reconnect_attempts']
RECONNECT_DELAY = config['general']['reconnect_delay']

# MQTT-Client einrichten
def connect_mqtt():
    client = mqtt_client.Client()
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info("Verbunden mit MQTT Broker")
        else:
            logger.error("Fehler beim Verbinden mit MQTT Broker. Code: %d", rc)

    client.on_connect = on_connect
    client.connect(MQTT_BROKER, MQTT_PORT)
    return client

# Modbus-Daten abrufen
def fetch_data(client):
    data = {}
    try:
        # Beispiel: Registeradressen entsprechend den gewünschten Datenpunkten
        data[1] = client.read_input_registers(100, 2, unit=MODBUS_UNIT_ID).registers  # Beispiel für Energieverbrauch
        data[2] = client.read_input_registers(200, 2, unit=MODBUS_UNIT_ID).registers  # Beispiel für Momentanleistung
        # Weitere Registeradressen hier hinzufügen...
    except Exception as e:
        logger.error("Fehler beim Abrufen der Daten: %s", e)
    return data

# Daten veröffentlichen
def publish_data(mqtt_client, data):
    for key, values in data.items():
        payload = f"{key}\n"
        for i, value in enumerate(values, 1):
            payload += f"{i}. Wert: {value}\n"
        mqtt_client.publish(f"{MQTT_TOPIC}/{key}", payload)

# Hauptprogramm
def main():
    mqtt_client = connect_mqtt()
    mqtt_client.loop_start()
    modbus_client = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)

    try:
        while True:
            if not modbus_client.connect():
                logger.warning("Modbus-Verbindung fehlgeschlagen, erneuter Versuch...")
                for _ in range(RECONNECT_ATTEMPTS):
                    if modbus_client.connect():
                        break
                    time.sleep(RECONNECT_DELAY)
                else:
                    logger.error("Verbindung nicht wiederhergestellt, Abbruch.")
                    break
            
            # Daten abrufen und über MQTT veröffentlichen
            data = fetch_data(modbus_client)
            publish_data(mqtt_client, data)
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        logger.info("Beendet durch Benutzer")
    finally:
        mqtt_client.loop_stop()
        modbus_client.close()

if __name__ == "__main__":
    main()
