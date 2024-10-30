import asyncio
import logging
import yaml
from datetime import datetime
from weather_service import WeatherService
from forecast_service import ForecastService
from mail_service import MailService
from influx_service import InfluxService
from mqtt_service import MQTTService
from modbus_service import ModbusService
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Load configuration
with open("config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

async def main():
    # Initialize services with values from config.yaml
    weather_service = WeatherService(
        api_key=config['weather']['api_key'], 
        location=config['weather']['location'], 
        cache_path=config['weather']['cache_path']
    )
    forecast_service = ForecastService(
        model_path=config['training']['model_path'],
        learning_rate=config['training']['learning_rate'],
        drift_threshold=config['training']['drift_threshold']
    )
    mail_service = MailService(
        smtp_server=config['notifications']['smtp_server'],
        sender_email=config['notifications']['email_sender'],
        recipient_email=config['notifications']['email_recipient'],
        password=config['notifications']['email_password']
    )
    influx_service = InfluxService(
        host=config['influxdb']['host'],
        database=config['influxdb']['database']
    )
    mqtt_service = MQTTService(
        broker=config['mqtt']['broker'],
        port=config['mqtt']['port'],
        use_ssl=config['mqtt'].get('use_ssl', False),
        ca_cert=config['mqtt'].get('ca_cert')
    )
    modbus_service = ModbusService(
        host=config['modbus']['host'],
        port=config['modbus']['port'],
        unit_id=config['modbus'].get('unit_id', 1)
    )

    # Fetch and process data
    weather_data = weather_service.fetch_weather_data()
    modbus_data = await modbus_service.fetch_data(100, 2)

    # Publish to MQTT and write to InfluxDB
    mqtt_service.publish("weather", str(weather_data))
    influx_service.write_data("modbus_data", datetime.utcnow().isoformat(), {"value": modbus_data})

    # Train forecast model
    error = forecast_service.detect_drift(pd.DataFrame(modbus_data, columns=["value"]))
    forecast_service.train_model(pd.DataFrame(modbus_data, columns=["value"]), error)

    # Send report
    mail_service.send_report("Daily report content")

if __name__ == "__main__":
    asyncio.run(main())
