import threading
import paho.mqtt.client as mqtt
    

class DHT22MQTTBackend:
    """
    Backend MQTT untuk sensor DHT22
    - Tidak tahu UI
    - Tidak membuat koneksi MQTT sendiri
    - Hanya subscribe & simpan state
    - Data diambil lewat fetch()
    """

    TOPIC_TEMP_A = "mcuA/dht/temperature"
    TOPIC_HUM_A  = "mcuA/dht/humidity"
    TOPIC_TEMP_B = "mcuB/dht/temperature"
    TOPIC_HUM_B  = "mcuB/dht/humidity"

    def __init__(self, mqtt_client):
        # MQTT core (shared)
        self.mqtt = mqtt_client

        # State sensor
        self.temp_A = None
        self.hum_A  = None
        self.temp_B = None
        self.hum_B  = None

    # ======================================
    def start(self):
        """
        Subscribe topic DHT22 lewat MQTT core
        """
        self.mqtt.subscribe(self.TOPIC_TEMP_A, self._on_message)
        self.mqtt.subscribe(self.TOPIC_HUM_A,  self._on_message)
        self.mqtt.subscribe(self.TOPIC_TEMP_B, self._on_message)
        self.mqtt.subscribe(self.TOPIC_HUM_B,  self._on_message)

    # ======================================
    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode()

        try:
            value = float(payload)
        except ValueError:
            return

        if msg.topic == self.TOPIC_TEMP_A:
            self.temp_A = value

        elif msg.topic == self.TOPIC_HUM_A:
            self.hum_A = value

        elif msg.topic == self.TOPIC_TEMP_B:
            self.temp_B = value

        elif msg.topic == self.TOPIC_HUM_B:
            self.hum_B = value

    # ======================================
    def fetch(self) -> dict:
        """
        Ambil data DHT22 terbaru + rata-rata
        Dipanggil bebas dari main (timer/UI)
        """
        temps = [t for t in (self.temp_A, self.temp_B) if t is not None]
        hums  = [h for h in (self.hum_A, self.hum_B) if h is not None]

        avg_temp = sum(temps) / len(temps) if temps else None
        avg_hum  = sum(hums)  / len(hums)  if hums  else None

        return {
            "temp_A": self.temp_A,
            "hum_A": self.hum_A,
            "temp_B": self.temp_B,
            "hum_B": self.hum_B,
            "avg_temperature": avg_temp,
            "avg_humidity": avg_hum,
        }
