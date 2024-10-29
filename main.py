import logging
import time
import sqlite3
from datetime import datetime, timedelta
import yaml
from pymodbus.client import ModbusTcpClient
from paho.mqtt import client as mqtt_client
from sklearn.ensemble import RandomForestRegressor
import numpy as np
import json
from flask import Flask, jsonify, render_template
import matplotlib.pyplot as plt
import io
import base64
from collections import deque

# Konfiguriere Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SolarEdgeReader")

# Konfigurationsdatei laden
with open("config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# Datenbankeinstellungen
DB_PATH = config['database']['path']
BUFFER_SIZE = config['database']['buffer_size']

# Vorhersageeinstellungen
PREDICTION_ENABLED = config['prediction'].get('enabled', False)
FORECAST_INTERVAL = config['prediction'].get('forecast_interval', 60)

# API Einstellungen
API_ENABLED = config['api'].get('enabled', False)
API_PORT = config['api'].get('port', 5000)

# Zusätzliche Funktionen
ANOMALY_DETECTION_ENABLED = config['features'].get('anomaly_detection', False)
ANOMALY_THRESHOLD = config['features'].get('anomaly_threshold', 10)
AGGREGATION_ENABLED = config['features'].get('aggregation', False)
BACKUP_MQTT_ENABLED = config['features'].get('backup_mqtt', False)
COMPRESSION_ENABLED = config['features'].get('compression', False)

# MQTT- und Modbus-Einstellungen (aus vorherigen Beispielen übernommen)

# Initialisiere das Vorhersagemodell und Flask-App
forecast_model = RandomForestRegressor()
app = Flask(__name__) if API_ENABLED else None
hourly_data = []
daily_data = []

def initialize_database():
    """Initialisiert die SQLite-Datenbank und erstellt die Tabelle falls noch nicht vorhanden."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            energy REAL,
            power REAL
        )
    ''')
    conn.commit()
    conn.close()

def save_data_to_db(timestamp, energy, power):
    """Speichert Daten in der SQLite-Datenbank als Ringpuffer."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO sensor_data (timestamp, energy, power) VALUES (?, ?, ?)',
                   (timestamp, energy, power))
    cursor.execute('DELETE FROM sensor_data WHERE id NOT IN (SELECT id FROM sensor_data ORDER BY id DESC LIMIT ?)', 
                   (BUFFER_SIZE,))
    conn.commit()
    conn.close()

def fetch_historical_data():
    """Liest historische Daten aus der Datenbank."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, energy, power FROM sensor_data ORDER BY timestamp')
    data = cursor.fetchall()
    conn.close()
    return data

def train_forecast_model():
    """Trainiert das Vorhersagemodell basierend auf historischen Daten."""
    historical_data = fetch_historical_data()
    if len(historical_data) < 10:
        return
    X = np.array([d[1:] for d in historical_data[:-1]])
    y = np.array([d[1] for d in historical_data[1:]])
    forecast_model.fit(X, y)

def predict_future_values():
    """Sagt zukünftige Werte basierend auf dem trainierten Modell vorher."""
    historical_data = fetch_historical_data()
    if len(historical_data) < 1:
        return None
    last_record = np.array([historical_data[-1][1:]]).reshape(1, -1)
    prediction = forecast_model.predict(last_record)
    return prediction[0] if prediction else None

def check_for_anomalies(current_data):
    """Überprüft die aktuellen Daten auf Anomalien basierend auf dem Schwellenwert."""
    if ANOMALY_DETECTION_ENABLED and len(hourly_data) > 1:
        last_data = hourly_data[-1]
        for key in ['energy', 'power']:
            change = abs(current_data[key] - last_data[key]) / last_data[key] * 100
            if change > ANOMALY_THRESHOLD:
                logger.warning("Anomaly detected in %s: %.2f%% change", key, change)
                return True
    return False

def aggregate_data(timestamp, energy, power):
    """Aggregiert Daten auf Stunden- und Tagesbasis."""
    global hourly_data, daily_data
    if AGGREGATION_ENABLED:
        # Beispiel für stündliche Aggregation
        if len(hourly_data) == 0 or hourly_data[-1]['timestamp'].hour != timestamp.hour:
            hourly_data.append({'timestamp': timestamp, 'energy': energy, 'power': power})
        # Beispiel für tägliche Aggregation
        if len(daily_data) == 0 or daily_data[-1]['timestamp'].day != timestamp.day:
            daily_data.append({'timestamp': timestamp, 'energy': energy, 'power': power})

def publish_current_data(mqtt_client_instance, timestamp, energy, power):
    """Veröffentlicht aktuelle Messwerte über MQTT, optional komprimiert."""
    payload = {
        "timestamp": timestamp,
        "energy": energy,
        "power": power
    }
    if COMPRESSION_ENABLED:
        payload = json.dumps(payload).encode('utf-8')
    mqtt_client_instance.publish(f"{MQTT_TOPIC}/current", payload)

def publish_forecast(mqtt_client_instance, forecast):
    """Veröffentlicht Vorhersagedaten über MQTT."""
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "forecast": forecast
    }
    mqtt_client_instance.publish(f"{MQTT_TOPIC}/forecast", json.dumps(payload))

@app.route('/')
def dashboard():
    """Web-Dashboard, das die aktuellen, vorhergesagten und historischen Daten anzeigt."""
    latest_data = fetch_historical_data()[-1] if fetch_historical_data() else ("N/A", "N/A", "N/A")
    forecast = predict_future_values()
    historical_data = fetch_historical_data()
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

def main():
    """Hauptprogramm, um Daten zu erfassen, in die Datenbank zu speichern, das Modell zu trainieren und Vorhersagen zu veröffentlichen."""
    mqtt_client_instance = connect_mqtt()
    mqtt_client_instance.loop_start()
    modbus_client = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)

    initialize_database()

    try:
        last_forecast_time = time.time()
        while True:
            timestamp = datetime.now()
            energy = np.random.uniform(100, 200)
            power = np.random.uniform(10, 20)
            save_data_to_db(timestamp.strftime("%Y-%m-%d %H:%M:%S"), energy, power)
            aggregate_data(timestamp, energy, power)
            if check_for_anomalies({"energy": energy, "power": power}):
                logger.warning("Anomaly detected in the data!")
            publish_current_data(mqtt_client_instance, timestamp.strftime("%Y-%m-%d %H:%M:%S"), energy, power)
            if PREDICTION_ENABLED:
                train_forecast_model()
                if time.time() - last_forecast_time >= FORECAST_INTERVAL:
                    forecast = predict_future_values()
                    if forecast:
                        publish_forecast(mqtt_client_instance, forecast)
                    last_forecast_time = time.time()
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        logger.info("Vom Benutzer gestoppt")
    finally:
        mqtt_client_instance.loop_stop()
        modbus_client.close()

if __name__ == "__main__":
    if API_ENABLED:
        from threading import Thread
        api_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=API_PORT))
        api_thread.start()
    main()
