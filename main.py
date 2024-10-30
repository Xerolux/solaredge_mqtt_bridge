
import asyncio
import logging
import yaml
import os
from datetime import datetime
from weather_service import WeatherService
from forecast_service import ForecastService
from mail_service import MailService
from influx_service import InfluxService
from mqtt_service import MQTTService
from modbus_service import ModbusService
from logging.handlers import RotatingFileHandler

# Load configuration with reloading capability
def load_config():
    with open("config.yaml", "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

config = load_config()

# Configure logging based on config
log_file = config.get('logging', {}).get('file')
log_level = config.get('logging', {}).get('level', 'INFO').upper()
if log_file:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    handler = RotatingFileHandler(log_file, maxBytes=config['logging'].get('max_size', 5*1024*1024), backupCount=config['logging'].get('backup_count', 3))
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), handlers=[handler], format="%(asctime)s %(levelname)s %(message)s")
else:
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), format="%(asctime)s %(levelname)s %(message)s")

# Initialize services
weather_service = WeatherService(config['weather'], caching=config['weather'].get('caching', False), cache_duration=config['weather'].get('cache_duration', 600))
forecast_service = ForecastService(config['forecast'])
modbus_service = ModbusService(config['modbus'], async_enabled=config.get('async_collection', {}).get('enabled', False))
mqtt_service = MQTTService(config['mqtt'], compression=config['mqtt'].get('compression', False), separate_topics=config['mqtt'].get('separate_topics', False))
mail_service = MailService(config['alerting'])

async def reload_config():
    # Periodically reload config if enabled
    if config['logging'].get('reload_on_change', False):
        while True:
            global config
            config = load_config()
            await asyncio.sleep(60)

async def health_check():
    # Health check with alerting based on thresholds
    while True:
        modbus_ok = await modbus_service.check_connection()
        mqtt_ok = await mqtt_service.check_connection()
        if not modbus_ok or not mqtt_ok:
            if config['health_check'].get('alert_on_failure', False):
                mail_service.send_alert("Service Health Check Failure")
        await asyncio.sleep(config['health_check'].get('interval', 60))

async def main():
    try:
        await asyncio.gather(
            reload_config(),
            weather_service.fetch_weather_data(),
            modbus_service.collect_data(rate_limit=config['data_aggregation'].get('rate_limit', 30)),
            mqtt_service.publish_data(),
            health_check()
        )
    except Exception as e:
        logging.error(f"Error in main loop: {e}")

if __name__ == "__main__":
    asyncio.run(main())
