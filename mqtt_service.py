
from paho.mqtt import client as mqtt_client
import logging

logger = logging.getLogger("MQTTService")

class MQTTService:
    def __init__(self, broker, port, use_ssl=False, ca_cert=None):
        self.client = mqtt_client.Client()
        if use_ssl and ca_cert:
            self.client.tls_set(ca_certs=ca_cert)
        self.client.connect(broker, port)
        self.client.loop_start()
        logger.info("Connected to MQTT Broker at %s:%s", broker, port)

    def publish(self, topic, payload):
        self.client.publish(topic, payload)
