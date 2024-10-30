import logging
import time
import yaml
import requests
import joblib
import pandas as pd
import asyncio
import json
from datetime import datetime, timedelta
from pymodbus.client import AsyncModbusTcpClient
from paho.mqtt import client as mqtt_client
from influxdb import InfluxDBClient
from sklearn.linear_model import SGDRegressor
from sklearn.metrics import mean_squared_error
from pathlib import Path

# Configure logging to file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("solaredge_reader.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SolarEdgeReader")

# Load configuration file
with open("config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# Configurations
MODBUS_HOST = config['modbus']['host']
MODBUS_PORT = config['modbus']['port']
MODBUS_UNIT_ID = config['modbus'].get('unit_id', 1)  # Default unit ID
MQTT_BROKER = config['mqtt']['broker']
MQTT_PORT = config['mqtt']['port']
MQTT_TOPIC = config['mqtt']['topic']
MQTT_USE_SSL = config['mqtt'].get('use_ssl', False)
MQTT_CA_CERT = config['mqtt'].get('ca_cert')
INFLUXDB_HOST = config['influxdb']['host']
INFLUXDB_DATABASE = config['influxdb']['database']
WEATHER_ENABLED = config['weather'].get('enabled', False)
WEATHER_API_KEY = config['weather'].get('api_key')
WEATHER_LOCATION = "Zorneding,DE"
WEATHER_CACHE_PATH = "weather_cache.json"

# General settings
DATA_INTERVAL = config['general'].get('interval', 10)
RECONNECT_ATTEMPTS = config['general'].get('reconnect_attempts', 3)
RECONNECT_DELAY = config['general'].get('reconnect_delay', 5)

# Training settings
TRAINING_ENABLED = config['training'].get('enabled', False)
TRAINING_INTERVAL = config['training'].get('interval', 86400)  # Default: 1 day
LEARNING_RATE = config['training'].get('learning_rate', 0.01)  # Default learning rate
MODEL_PATH = config['training'].get('model_path', 'energy_model.pkl')
DRIFT_THRESHOLD = config['training'].get('drift_threshold', 100)  # Error threshold for retraining

# Initialize model with SGDRegressor for adaptive learning
try:
    model = joblib.load(MODEL_PATH)
    logger.info("Loaded existing prediction model.")
except FileNotFoundError:
    model = SGDRegressor(learning_rate='constant', eta0=LEARNING_RATE)
    logger.info("No model found. Initialized a new model with learning rate %s", LEARNING_RATE)

# Async functions
async def connect_mqtt():
    """Asynchronously connect to MQTT with optional SSL/TLS."""
    client = mqtt_client.Client()
    if MQTT_USE_SSL:
        client.tls_set(ca_certs=MQTT_CA_CERT)
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.loop_start()
    return client

async def connect_influxdb():
    """Asynchronously connect to InfluxDB."""
    client = InfluxDBClient(host=INFLUXDB_HOST, database=INFLUXDB_DATABASE)
    logger.info("Connected to InfluxDB")
    return client

async def fetch_weather_data():
    """Fetch and cache weather data."""
    if Path(WEATHER_CACHE_PATH).is_file():
        with open(WEATHER_CACHE_PATH, 'r') as cache_file:
            cached_data = json.load(cache_file)
            if datetime.now() < datetime.fromisoformat(cached_data['expiry']):
                logger.info("Using cached weather data")
                return cached_data['weather']

    try:
        response = requests.get(f"http://api.openweathermap.org/data/2.5/weather?q={WEATHER_LOCATION}&appid={WEATHER_API_KEY}&units=metric")
        response.raise_for_status()
        weather_data = response.json()
        cache_data = {
            "weather": {
                "temperature": weather_data["main"]["temp"],
                "humidity": weather_data["main"]["humidity"],
                "description": weather_data["weather"][0]["description"]
            },
            "expiry": (datetime.now() + timedelta(hours=1)).isoformat()  # Cache for 1 hour
        }
        with open(WEATHER_CACHE_PATH, 'w') as cache_file:
            json.dump(cache_data, cache_file)
        logger.info("Fetched and cached new weather data")
        return cache_data['weather']
    except Exception as e:
        logger.error(f"Failed to fetch weather data: {e}")
        return {}

async def fetch_data(modbus_client):
    """Fetch data asynchronously from Modbus."""
    data = {}
    try:
        await modbus_client.connect()
        result = await modbus_client.read_input_registers(100, 2, unit=MODBUS_UNIT_ID)  # Energy
        data["energy"] = result.registers
        result = await modbus_client.read_input_registers(200, 2, unit=MODBUS_UNIT_ID)  # Power
        data["power"] = result.registers
        await modbus_client.close()
        logger.info("Fetched Modbus data")
    except Exception as e:
        logger.error(f"Modbus data fetch failed: {e}")
    return data

async def publish_data(mqtt_client_instance, data, weather_data):
    """Publish data and weather to MQTT."""
    timestamp = datetime.now().isoformat()
    for key, values in data.items():
        payload = f"{key}: " + ", ".join(map(str, values)) + f" at {timestamp}"
        mqtt_client_instance.publish(f"{MQTT_TOPIC}/{key}", payload)
    if WEATHER_ENABLED and weather_data:
        mqtt_client_instance.publish(f"{MQTT_TOPIC}/weather", json.dumps(weather_data))
    logger.info("Published data to MQTT")

async def train_model(recent_data, current_error):
    """Train model with recent data if drift detected."""
    if recent_data.empty:
        logger.warning("No recent data for training.")
        return
    recent_data['timestamp'] = pd.to_datetime(recent_data['time']).map(datetime.timestamp)
    X = recent_data[['timestamp']]
    y = recent_data['value']

    model.partial_fit(X, y)

    # Save model if drift threshold exceeded
    if current_error > DRIFT_THRESHOLD:
        joblib.dump(model, MODEL_PATH)
        logger.info("Model drift detected. Model retrained and saved.")

async def detect_drift(recent_data):
    """Calculate prediction error and detect data drift."""
    if recent_data.empty:
        return 0
    recent_data['timestamp'] = pd.to_datetime(recent_data['time']).map(datetime.timestamp)
    X = recent_data[['timestamp']]
    y_true = recent_data['value']
    y_pred = model.predict(X)
    error = mean_squared_error(y_true, y_pred)
    return error

async def main():
    """Main function to orchestrate data fetching, publishing, and adaptive training."""
    mqtt_client_instance = await connect_mqtt()
    influx_client = await connect_influxdb()
    modbus_client = AsyncModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
    last_training = datetime.min

    while True:
        tasks = [
            fetch_data(modbus_client),
            fetch_weather_data() if WEATHER_ENABLED else None
        ]
        results = await asyncio.gather(*filter(None, tasks))
        data, weather_data = results[0], results[1] if WEATHER_ENABLED else {}

        # Store in InfluxDB
        timestamp = datetime.utcnow().isoformat()
        influx_payload = [{"measurement": "data", "time": timestamp, "fields": data}]
        influx_client.write_points(influx_payload)
        
        # Publish to MQTT
        await publish_data(mqtt_client_instance, data, weather_data)

        # Adaptive model training with drift detection
        if TRAINING_ENABLED and (datetime.now() - last_training).total_seconds() >= TRAINING_INTERVAL:
            recent_data = pd.DataFrame(list(influx_client.query("SELECT * FROM data WHERE time > now() - 30d").get_points()))
            error = await detect_drift(recent_data)
            await train_model(recent_data, error)
            last_training = datetime.now()

        await asyncio.sleep(DATA_INTERVAL)  # Adjustable interval for data retrieval

if __name__ == "__main__":
    asyncio.run(main())
