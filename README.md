# solaredge_mqtt_bridge


SolarEdge MQTT Bridge

A Python script that reads data from a SolarEdge energy meter via Modbus and publishes it to an MQTT broker. This allows integration of SolarEdge energy data with IoT systems and energy management platforms.

Features

Reads data like energy consumption, power, and grid parameters from a SolarEdge meter

Publishes data in a structured format via MQTT

Configurable settings via a YAML file

Automatic reconnection for Modbus and MQTT if the connection is lost


Prerequisites

Python 3.7+

SolarEdge energy meter with Modbus TCP enabled

MQTT broker for publishing data


Required Python Libraries

Install the necessary libraries via pip:

pip install pymodbus paho-mqtt pyyaml

Installation

1. Clone the repository:

git clone https://github.com/yourusername/solaredge-mqtt-bridge.git
cd solaredge-mqtt-bridge


2. Install dependencies:

pip install -r requirements.txt


3. Configure settings:

Edit the config.yaml file with the correct settings for your Modbus and MQTT connections:

modbus:
  host: "192.168.x.x"         # SolarEdge energy meter IP
  port: 502                    # Modbus port (default: 502)
  unit_id: 1                   # Modbus unit ID (default: 1)

mqtt:
  broker: "mqtt_broker_ip"     # MQTT broker IP
  port: 1883                   # MQTT port (default: 1883)
  topic: "WPZaehler"           # Root topic for MQTT data
  username: "mqtt_user"        # MQTT username (optional)
  password: "mqtt_password"    # MQTT password (optional)

general:
  interval: 10                 # Data fetch interval in seconds
  reconnect_attempts: 3        # Number of reconnect attempts
  reconnect_delay: 5           # Delay between reconnect attempts in seconds




Usage

Run the script to start reading data and publishing to MQTT:

python main.py

Configuration File (config.yaml)

Modbus settings: Configure IP, port, and unit ID for connecting to the SolarEdge energy meter.

MQTT settings: Configure broker IP, port, topic, and optionally, credentials.

General settings: Set the data retrieval interval, and parameters for reconnection if connections drop.


Troubleshooting

Ensure Modbus TCP is enabled on the SolarEdge energy meter.

Verify MQTT broker credentials and network connectivity.

Check config.yaml for correct IP addresses and ports.


License

This project is licensed under the MIT License. See the LICENSE file for more details.

Contribution

Contributions are welcome! Please open an issue to discuss any changes or improvements.
