class LampButtonBackend:
    """
    Backend MQTT untuk kontrol lampu
    - Tidak tahu UI
    - Tidak tahu DHT
    - Hanya publish perintah lampu
    """

    BASE_TOPIC = "mcuA/lamp"

    def __init__(self, mqtt_client, logger=None):
        self.mqtt = mqtt_client
        self.logger = logger
        self.states = {}


    def set_lamp(self, lamp_index: int, state: bool):
        topic = f"{self.BASE_TOPIC}{lamp_index}"
        payload = "ON" if state else "OFF"
        print(f"[MQTT] {topic} -> {payload}")
        if self.logger:
            self.logger(f"[MQTT] {topic} -> {payload}")
        self.mqtt.publish(topic, payload)
 
    def start(self):
        # subscribe ke state lampu
        for i in range(1, 6):
            topic = f"ui/mcuA/lamp{i}/state"
            self.mqtt.subscribe(topic, self._on_state)

    def publish(self, lamp_index: int, state: bool):
        payload = "ON" if state else "OFF"

        # 1️⃣ COMMAND ke MCU (INI YANG HILANG)
        cmd_topic = f"mcuA/lamp{lamp_index}"
        self.mqtt.publish(cmd_topic, payload)

        # 2️⃣ STATE ke UI (retain)
        state_topic = f"ui/mcuA/lamp{lamp_index}/state"
        self.mqtt.publish(state_topic, payload, retain=True)

        self.states[lamp_index] = state

        if self.logger:
            self.logger(f"[LAMP] lamp{lamp_index} -> {payload}")


    def _on_state(self, client, userdata, msg):
        lamp_index = int(msg.topic.split("lamp")[1].split("/")[0])
        state = msg.payload.decode() == "ON"
        self.states[lamp_index] = state


