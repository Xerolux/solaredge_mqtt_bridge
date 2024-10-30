
# SolarEdge MQTT Bridge

A Python script that reads data from a SolarEdge energy meter via Modbus and publishes it to an MQTT broker. This tool enables integration of SolarEdge energy data into IoT systems and energy management platforms for real-time monitoring and predictive energy management.

## Features
- **Real-time Modbus Data Retrieval**: Collects energy metrics such as consumption, power, voltage, and current from a SolarEdge meter.
- **MQTT Publishing**: Publishes data to an MQTT broker in a structured format, suitable for integration with home automation or industrial systems.
- **Modular Configuration**: Customizable settings via a YAML file.
- **Automatic Reconnection**: Automatically reconnects for Modbus and MQTT if connections drop.
- **Weather Integration**: Optional weather data retrieval to combine with energy data.
- **Predictive Modeling**: Includes an optional forecasting model to predict future energy usage based on historical data.
- **Backup Data Handling**: Option to save old data to a file to support backup and training.

## Prerequisites
- **Python 3.7+ (Compatible with Python 3.12)**
- SolarEdge energy meter with Modbus TCP enabled
- MQTT broker for data publishing (e.g., Mosquitto)

## Required Python Libraries
Install the required libraries:
```bash
pip install -r requirements.txt
```

## Installation and Setup

### Python 3.12 Compatibility
This script supports Python 3.12. Hereâ€™s how to set it up:

1. **Install Python 3.12** and create a virtual environment:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies** from `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the script** to check compatibility:
   ```bash
   python main.py
   ```

### Running as a Systemd Service
1. **Create a Systemd service** file:
   ```bash
   sudo nano /etc/systemd/system/solaredge_mqtt.service
   ```

2. **Configure the service** by adding the following lines (replace `/path/to/venv` and `/path/to/project` with your paths):

   ```ini
   [Unit]
   Description=SolarEdge MQTT Bridge Service
   After=network.target

   [Service]
   ExecStart=/path/to/venv/bin/python /path/to/project/main.py
   WorkingDirectory=/path/to/project
   Restart=always
   User=your-username
   Environment="PYTHONUNBUFFERED=1"

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start** the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable solaredge_mqtt.service
   sudo systemctl start solaredge_mqtt.service
   ```

4. **Check the status** of the service:
   ```bash
   sudo systemctl status solaredge_mqtt.service
   ```

5. **Manage the service** (stop, restart, and view logs):
   ```bash
   sudo systemctl stop solaredge_mqtt.service
   sudo systemctl restart solaredge_mqtt.service
   journalctl -u solaredge_mqtt.service
   ```

## Usage
To start reading data and publishing to MQTT, run the script:
```bash
python main.py
```

## Configuration File (`config.yaml`)
The `config.yaml` file contains all necessary settings. Customize the following sections:

### Modbus Settings
```yaml
modbus:
  host: "192.168.1.100"    # IP address of the SolarEdge energy meter
  port: 502                # Modbus TCP port, typically 502
  unit_id: 1               # Modbus unit ID for the energy meter
```

### MQTT Settings
```yaml
mqtt:
  broker: "mqtt.example.com"    # MQTT broker address
  port: 1883                    # Broker port
  topic: "solaredge"            # Base topic for publishing data
  use_ssl: true                 # Optional, enable SSL/TLS if required
  ca_cert: "/path/to/ca_cert.pem"  # Path to CA certificate for SSL (if applicable)
```

### InfluxDB Settings
```yaml
influxdb:
  host: "localhost"             # InfluxDB server address
  database: "energy_data"       # Database name to store energy data
```

### Weather Settings (Optional)
```yaml
weather:
  enabled: true                  # Enable/disable weather data retrieval
  api_key: "your_openweathermap_api_key" # API key for OpenWeather
  location: "Zorneding,DE"       # Location for weather data retrieval
  cache_path: "weather_cache.json" # Path to cache weather data
```

### Training Settings (Optional)
```yaml
training:
  enabled: true                  # Enable/disable model training
  interval: 86400                # Training interval in seconds (default is daily)
  learning_rate: 0.01            # Learning rate for model training
  model_path: "energy_model.pkl" # Path to save/load the model
  drift_threshold: 100           # Threshold for retraining due to drift
```

### Notifications Settings (Optional)
```yaml
notifications:
  enabled: true                      # Enable/disable email notifications
  email_sender: "your_email@example.com" # Sender email address
  email_recipient: "recipient@example.com" # Recipient email address
  smtp_server: "smtp.example.com"    # SMTP server for email
  email_password: "your_email_password" # Password for email sender account
```

### General Settings
```yaml
general:
  interval: 10                   # Main loop interval in seconds
  reconnect_attempts: 3          # Number of reconnection attempts if a connection fails
  reconnect_delay: 5             # Delay in seconds between reconnection attempts
```

## Troubleshooting
1. **Check Modbus TCP**: Ensure Modbus TCP is enabled on your SolarEdge energy meter.
2. **Verify MQTT Broker Connection**: Check the broker address and credentials.
3. **Validate Configuration**: Review the `config.yaml` file for correct IPs, ports, and keys.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contribution
Contributions are welcome! Please open an issue to discuss any improvements or new features.
