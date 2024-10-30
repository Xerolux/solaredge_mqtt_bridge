
from influxdb import InfluxDBClient
import logging

logger = logging.getLogger("InfluxService")

class InfluxService:
    def __init__(self, host, database):
        self.client = InfluxDBClient(host=host, database=database)
        logger.info("Connected to InfluxDB at %s", host)

    def write_data(self, measurement, time, fields):
        json_body = [{"measurement": measurement, "time": time, "fields": fields}]
        self.client.write_points(json_body)
