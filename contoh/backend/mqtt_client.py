import threading
import paho.mqtt.client as mqtt

class MqttClient:
    def __init__(self, broker="10.33.11.148", port=1883, logger=None):
        self.client = mqtt.Client()
        self.broker = broker
        self.port = port
        self.logger = logger

        self._subscriptions = []  # <-- TAMBAHAN PENTING

        self.client.on_connect = self._on_connect

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_forever()
        except Exception as e:
            if self.logger:
                self.logger(f"[MQTT ERROR] {e}")
            else:
                print("[MQTT ERROR]", e)

    def _on_connect(self, client, userdata, flags, rc):
        print("[MQTT CORE] Connected")

        # 🔥 DAFTARKAN ULANG SEMUA SUBSCRIBE
        for topic, callback in self._subscriptions:
            client.subscribe(topic)
            client.message_callback_add(topic, callback)

    def subscribe(self, topic, callback):
        # simpan dulu
        self._subscriptions.append((topic, callback))

        # kalau sudah connect, langsung subscribe
        if self.client.is_connected():
            self.client.subscribe(topic)
            self.client.message_callback_add(topic, callback)
            
    def publish(self, topic, payload, retain=False):
        self.client.publish(topic, payload, retain=retain)


