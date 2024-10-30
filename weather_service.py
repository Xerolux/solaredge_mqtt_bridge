
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger("WeatherService")

class WeatherService:
    def __init__(self, api_key, location, cache_path="weather_cache.json"):
        self.api_key = api_key
        self.location = location
        self.cache_path = Path(cache_path)

    def fetch_weather_data(self):
        if self.cache_path.is_file():
            with open(self.cache_path, 'r') as cache_file:
                cached_data = json.load(cache_file)
                if datetime.now() < datetime.fromisoformat(cached_data['expiry']):
                    logger.info("Using cached weather data")
                    return cached_data['weather']

        try:
            response = requests.get(f"http://api.openweathermap.org/data/2.5/weather?q={self.location}&appid={self.api_key}&units=metric")
            response.raise_for_status()
            weather_data = response.json()
            cache_data = {
                "weather": {
                    "temperature": weather_data["main"]["temp"],
                    "humidity": weather_data["main"]["humidity"],
                    "description": weather_data["weather"][0]["description"]
                },
                "expiry": (datetime.now() + timedelta(hours=1)).isoformat()
            }
            with open(self.cache_path, 'w') as cache_file:
                json.dump(cache_data, cache_file)
            logger.info("Fetched and cached new weather data")
            return cache_data['weather']
        except Exception as e:
            logger.error(f"Failed to fetch weather data: {e}")
            return {}
