class MCUStatusBackend:
    TOPIC_MCU_A = "mcuA/status"
    TOPIC_MCU_B = "mcuB/status"

    def __init__(self, mqtt):
        self.mqtt = mqtt

        self.mcuA_online = None
        self.mcuB_online = None

    def start(self):
        self.mqtt.subscribe(self.TOPIC_MCU_A, self._on_message)
        self.mqtt.subscribe(self.TOPIC_MCU_B, self._on_message)

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode().lower()

        if msg.topic == self.TOPIC_MCU_A:
            self.mcuA_online = payload == "online"

        elif msg.topic == self.TOPIC_MCU_B:
            self.mcuB_online = payload == "online"

    def fetch(self):
        return {
            "mcuA": self.mcuA_online,
            "mcuB": self.mcuB_online,
        }
