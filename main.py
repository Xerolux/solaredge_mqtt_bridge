
import logging
import time
from datetime import datetime
import yaml
from pymodbus.client import ModbusTcpClient
from paho.mqtt import client as mqtt_client
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from sklearn.ensemble import RandomForestRegressor
import numpy as np
import json
from flask import Flask, jsonify, render_template
import matplotlib.pyplot as plt
import io
import base64

# Konfiguriere Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SolarEdgeReader")

# Konfigurationsdatei laden
with open("config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# InfluxDB-Einstellungen
INFLUXDB_URL = config['influxdb']['url']
INFLUXDB_TOKEN = config['influxdb']['token']
INFLUXDB_ORG = config['influxdb']['org']
INFLUXDB_BUCKET = config['influxdb']['bucket']
VISUALIZATION_QUERY_RANGE = config['influxdb'].get('visualization_query_range', "7d")
TRAINING_QUERY_RANGE = config['influxdb'].get('training_query_range', "all")

# Initialisiere InfluxDB-Client
influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

# Vorhersageeinstellungen
PREDICTION_ENABLED = config['prediction'].get('enabled', False)
FORECAST_INTERVAL = config['prediction'].get('forecast_interval', 60)

# API Einstellungen
API_ENABLED = config['api'].get('enabled', False)
API_PORT = config['api'].get('port', 5000)

# ZusÃ¤tzliche Funktionen
ANOMALY_DETECTION_ENABLED = config['features'].get('anomaly_detection', False)
ANOMALY_THRESHOLD = config['features'].get('anomaly_threshold', 10)
AGGREGATION_ENABLED = config['features'].get('aggregation', False)
BACKUP_MQTT_ENABLED = config['features'].get('backup_mqtt', False)
COMPRESSION_ENABLED = config['features'].get('compression', False)

# MQTT- und Modbus-Einstellungen (aus vorherigen Beispielen Ã¼bernommen)

# Initialisiere das Vorhersagemodell und Flask-App
forecast_model = RandomForestRegressor()
app = Flask(__name__) if API_ENABLED else None

def save_data_to_influxdb(timestamp, energy, power):
    """Speichert Daten in InfluxDB."""
    point = Point("solar_edge_data")         .tag("source", "solar_edge")         .field("energy", energy)         .field("power", power)         .time(timestamp, WritePrecision.S)
    write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
    logger.info(f"Data written to InfluxDB: energy={energy}, power={power}")

def fetch_data_for_visualization():
    """Liest historische Daten aus InfluxDB fÃ¼r die Visualisierung."""
    query = f'from(bucket:"{INFLUXDB_BUCKET}") |> range(start: -{VISUALIZATION_QUERY_RANGE}) |> filter(fn: (r) => r._measurement == "solar_edge_data")'
    result = influx_client.query_api().query(query, org=INFLUXDB_ORG)
    data = []
    for table in result:
        for record in table.records:
            data.append((record.get_time().isoformat(), record.get_value_by_key("energy"), record.get_value_by_key("power")))
    return data

def fetch_data_for_training():
    """Liest alle oder eine bestimmte Anzahl historischer Daten fÃ¼r das Modelltraining aus InfluxDB."""
    if TRAINING_QUERY_RANGE == "all":
        query = f'from(bucket:"{INFLUXDB_BUCKET}") |> range(start: 0) |> filter(fn: (r) => r._measurement == "solar_edge_data")'
    else:
        query = f'from(bucket:"{INFLUXDB_BUCKET}") |> range(start: -{TRAINING_QUERY_RANGE}) |> filter(fn: (r) => r._measurement == "solar_edge_data")'
    
    result = influx_client.query_api().query(query, org=INFLUXDB_ORG)
    data = []
    for table in result:
        for record in table.records:
            data.append((record.get_time().isoformat(), record.get_value_by_key("energy"), record.get_value_by_key("power")))
    return data

def train_forecast_model():
    """Trainiert das Vorhersagemodell basierend auf den fÃ¼r das Training konfigurierten Daten."""
    training_data = fetch_data_for_training()
    if len(training_data) < 10:
        return
    X = np.array([d[1:] for d in training_data[:-1]])
    y = np.array([d[1] for d in training_data[1:]])
    forecast_model.fit(X, y)

@app.route('/')
def dashboard():
    """Web-Dashboard, das die aktuellen, vorhergesagten und historischen Daten anzeigt."""
    latest_data = fetch_data_for_visualization()[-1] if fetch_data_for_visualization() else ("N/A", "N/A", "N/A")
    forecast = predict_future_values()
    historical_data = fetch_data_for_visualization()
    timestamps = [d[0] for d in historical_data]
    energies = [d[1] for d in historical_data]
    powers = [d[2] for d in historical_data]
    fig, ax = plt.subplots()
    ax.plot(timestamps, energies, label='Energy')
    ax.plot(timestamps, powers, label='Power')
    ax.set_xlabel('Time')
    ax.set_ylabel('Value')
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    chart_data = base64.b64encode(img.getvalue()).decode()
    plt.close()

    return render_template('dashboard.html', 
                           current_data=latest_data, 
                           forecast=forecast, 
                           chart_data=chart_data)
