
# SolarEdge MQTT Bridge

A Python script that reads data from a SolarEdge energy meter via Modbus and publishes it to an MQTT broker. This allows integration of SolarEdge energy data with IoT systems and energy management platforms.

## Features
- Reads data like energy consumption, power, and grid parameters from a SolarEdge meter
- Publishes data in a structured format via MQTT
- Configurable settings via a YAML file
- Automatic reconnection for Modbus and MQTT if the connection is lost

## Prerequisites
- **Python 3.7+ (including compatibility with Python 3.12)**
- SolarEdge energy meter with Modbus TCP enabled
- MQTT broker for publishing data

## Required Python Libraries
Install the necessary libraries via pip:
```bash
pip install pymodbus paho-mqtt pyyaml
```

## Installation and Setup

### Python 3.12 Compatibility
This script is compatible with Python 3.12. To ensure compatibility:
1. Install Python 3.12 and create a virtual environment:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the script to confirm there are no compatibility issues:
   ```bash
   python main.py
   ```

### Running as a Systemd Service
To run the script as a Systemd service, follow these steps:

1. Create a Systemd service file:
   ```bash
   sudo nano /etc/systemd/system/solaredge_mqtt.service
   ```

2. Add the following configuration, replacing `/path/to/venv` and `/path/to/project` with your actual paths:

   ```ini
   [Unit]
   Description=SolarEdge MQTT Bridge Service
   After=network.target

   [Service]
   ExecStart=/path/to/venv/bin/python /path/to/main.py
   WorkingDirectory=/path/to/project
   Restart=always
   User=your-username
   Environment="PYTHONUNBUFFERED=1"

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable solaredge_mqtt.service
   sudo systemctl start solaredge_mqtt.service
   ```

4. Check the status of the service:
   ```bash
   sudo systemctl status solaredge_mqtt.service
   ```

5. To stop, restart, or view logs for the service:
   ```bash
   sudo systemctl stop solaredge_mqtt.service
   sudo systemctl restart solaredge_mqtt.service
   journalctl -u solaredge_mqtt.service
   ```

## Usage
Run the script to start reading data and publishing to MQTT:
```bash
python main.py
```

## Configuration File (`config.yaml`)
- **Modbus settings**: Configure IP, port, and unit ID for connecting to the SolarEdge energy meter.
- **MQTT settings**: Configure broker IP, port, topic, and optionally, credentials.
- **General settings**: Set the data retrieval interval, and parameters for reconnection if connections drop.

## Troubleshooting
- Ensure Modbus TCP is enabled on the SolarEdge energy meter.
- Verify MQTT broker credentials and network connectivity.
- Check `config.yaml` for correct IP addresses and ports.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Contribution
Contributions are welcome! Please open an issue to discuss any changes or improvements.
