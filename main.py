
import asyncio
import logging
from weather_service import WeatherService
from forecast_service import ForecastService
from mail_service import MailService
from influx_service import InfluxService
from mqtt_service import MQTTService
from modbus_service import ModbusService
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

async def main():
    # Configuration values (in a real application, load these from config.yaml or environment)
    weather_service = WeatherService(api_key="your_api_key", location="Zorneding,DE")
    forecast_service = ForecastService()
    mail_service = MailService(smtp_server="smtp.example.com", sender_email="sender@example.com", recipient_email="recipient@example.com", password="password")
    influx_service = InfluxService(host="localhost", database="energy_data")
    mqtt_service = MQTTService(broker="mqtt.example.com", port=1883)
    modbus_service = ModbusService(host="192.168.1.100", port=502, unit_id=1)

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
