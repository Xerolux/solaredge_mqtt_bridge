import logging
import time
import yaml
import numpy as np
import pickle
from datetime import datetime
from pymodbus.client import ModbusTcpClient
from paho.mqtt import client as mqtt_client
from influxdb_client import InfluxDBClient, Point, WritePrecision
from sklearn.linear_model import SGDRegressor  # Inkremetelles Modell
import requests
import json
from flask import Flask, render_template
import matplotlib.pyplot as plt
import io
import base64
import os

# Logging Konfiguration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SolarEdgeReader")

# Konfiguration laden
with open("config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# InfluxDB-Einstellungen
INFLUXDB_CLIENT = InfluxDBClient(
    url=config['influxdb']['url'], 
    token=config['influxdb']['token'], 
    org=config['influxdb']['org']
)
INFLUXDB_BUCKET = config['influxdb']['bucket']
VISUALIZATION_QUERY_RANGE = config['influxdb'].get('visualization_query_range', "7d")
TRAINING_QUERY_RANGE = config['influxdb'].get('training_query_range', "all")

# Wetter-API-Einstellungen
WEATHER_ENABLED = config['prediction'].get('include_weather', False)
WEATHER_API_KEY = config['prediction']['weather'].get('api_key')
WEATHER_LOCATION = config['prediction']['weather'].get('location')
WEATHER_UPDATE_INTERVAL = config['prediction']['weather'].get('update_interval', 3600)
ERROR_HANDLING_ENABLED = config['prediction']['weather'].get('error_handling', True)
MAX_WEATHER_RETRY = 3
last_weather_update = 0
current_weather = {}

# Modell-Speicherpfad und letzte Trainingszeit
MODEL_PATH = "trained_model.pkl"
LAST_TRAINED_TIMESTAMP_PATH = "last_trained_timestamp.txt"

# Initialisiere das inkrementelle Vorhersagemodell und Flask
forecast_model = SGDRegressor()
app = Flask(__name__) if config['api'].get('enabled', False) else None

# Laden des letzten Trainingszeitpunkts
def load_last_trained_timestamp():
    if os.path.exists(LAST_TRAINED_TIMESTAMP_PATH):
        with open(LAST_TRAINED_TIMESTAMP_PATH, "r") as f:
            return datetime.fromisoformat(f.read().strip())
    return None

# Speichern des letzten Trainingszeitpunkts
def save_last_trained_timestamp(timestamp):
    with open(LAST_TRAINED_TIMESTAMP_PATH, "w") as f:
        f.write(timestamp.isoformat())

# Wetterdaten abrufen und speichern
def fetch_weather_data():
    global current_weather, last_weather_update
    if not WEATHER_ENABLED:
        return {}
    
    retries = 0
    while retries < MAX_WEATHER_RETRY:
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={WEATHER_LOCATION}&appid={WEATHER_API_KEY}&units=metric"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            current_weather = {
                "temperature": data["main"]["temp"],
                "cloudiness": data["clouds"]["all"]
            }
            last_weather_update = time.time()
            logger.info("Weather data updated.")
            save_weather_data_to_influxdb(current_weather["temperature"], current_weather["cloudiness"])
            return current_weather
        except requests.exceptions.RequestException as e:
            retries += 1
            if ERROR_HANDLING_ENABLED:
                logger.error(f"Weather data fetch failed (attempt {retries}): {e}")
            time.sleep(5)
            
    if retries == MAX_WEATHER_RETRY:
        logger.warning("Using last cached weather data after 3 failed attempts.")
        return current_weather

def save_weather_data_to_influxdb(temperature, cloudiness):
    """Speichert Wetterdaten in InfluxDB."""
    point = Point("weather_data") \
        .tag("source", "openweather") \
        .field("temperature", temperature) \
        .field("cloudiness", cloudiness) \
        .time(datetime.utcnow(), WritePrecision.S)
    INFLUXDB_CLIENT.write_api(write_options=SYNCHRONOUS).write(
        bucket=INFLUXDB_BUCKET, org=config['influxdb']['org'], record=point
    )
    logger.info(f"Weather data written to InfluxDB: temperature={temperature}, cloudiness={cloudiness}")

def save_model():
    """Speichert das trainierte Modell als Datei."""
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(forecast_model, f)
    logger.info("Model saved successfully.")

def load_model():
    """Lädt das trainierte Modell aus einer Datei, falls vorhanden."""
    global forecast_model
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            forecast_model = pickle.load(f)
        logger.info("Model loaded successfully.")
    else:
        logger.info("No saved model found; training a new model.")

def prepare_training_data(training_data, weather_data):
    """Bereitet Trainingsdaten vor, einschließlich abgeleiteter Zeitmerkmale und historischer Werte."""
    X, y = [], []
    for i in range(1, len(training_data)):
        timestamp, energy, power = training_data[i]
        prev_energy = training_data[i-1][1]
        
        date_time = datetime.fromisoformat(timestamp)
        month = date_time.month
        day_of_week = date_time.weekday()
        hour = date_time.hour

        temperature = weather_data.get("temperature", None)
        cloudiness = weather_data.get("cloudiness", None)

        features = [energy, power, prev_energy, month, day_of_week, hour, temperature, cloudiness]
        X.append(features)
        y.append(energy)
    
    return np.array(X), np.array(y)

def train_forecast_model():
    last_trained_timestamp = load_last_trained_timestamp()
    query_range = f"-{TRAINING_QUERY_RANGE}" if last_trained_timestamp is None else f"{last_trained_timestamp.isoformat()}"

    training_data = fetch_data_for_influxdb(query_range)
    if len(training_data) < 10:
        return

    weather_data = fetch_weather_data()
    X, y = prepare_training_data(training_data, weather_data)
    forecast_model.partial_fit(X, y)  # Inkrementelles Training

    save_model()
    save_last_trained_timestamp(datetime.now())

def predict_future_values():
    historical_data = fetch_data_for_influxdb(f"-{VISUALIZATION_QUERY_RANGE}")
    if len(historical_data) < 1:
        return None
    weather_data = fetch_weather_data()
    last_record = np.array([historical_data[-1][1:]] + [weather_data["temperature"], weather_data["cloudiness"]]).reshape(1, -1)
    prediction = forecast_model.predict(last_record)
    return prediction[0] if prediction else None

@app.route('/')
def dashboard():
    latest_data = fetch_data_for_influxdb(f"-{VISUALIZATION_QUERY_RANGE}")[-1]
    forecast = predict_future_values()
    historical_data = fetch_data_for_influxdb(f"-{VISUALIZATION_QUERY_RANGE}")
    timestamps, energies, powers = zip(*[(d[0], d[1], d[2]) for d in historical_data])
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

if __name__ == "__main__":
    load_model()  # Lade das Modell, falls vorhanden
    if config['api'].get('enabled', False):
        from threading import Thread
        api_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=config['api']['port']))
        api_thread.start()
    train_forecast_model()  # Trainiere nur mit neuen Daten
