class ACButtonBackend:
    """
    Backend MQTT untuk kontrol AC
    - Tidak tahu UI
    - Tidak tahu Lamp / DHT
    - Hanya publish command AC
    """

    TOPIC_AC = "mcuB/ac"
    STATE_TOPIC = "ui/mcuB/ac/state"

    def __init__(self, mqtt_client, logger=None):
        self.mqtt = mqtt_client
        self.logger = logger
        self.state = {}
        
    def temp_up(self):
        self.mqtt.publish(self.TOPIC_AC, "TEMP_UP")
        print(f"[MQTT] {self.TOPIC_AC} -> TEMP_UP")
        if self.logger:
            self.logger(f"[MQTT] {self.TOPIC_AC} -> TEMP_UP")

    def temp_down(self):
        self.mqtt.publish(self.TOPIC_AC, "TEMP_DOWN")
        print(f"[MQTT] {self.TOPIC_AC} -> TEMP_DOWN")
        if self.logger:
            self.logger(f"[MQTT] {self.TOPIC_AC} -> TEMP_DOWN")

    def mode_cool(self):
        self.mqtt.publish(self.TOPIC_AC, "MODE_COOL")
        print(f"[MQTT] {self.TOPIC_AC} -> MODE_COOL")
        if self.logger:
            self.logger(f"[MQTT] {self.TOPIC_AC} -> MODE_COOL")

    def mode_fan(self):
        self.mqtt.publish(self.TOPIC_AC, "MODE_FAN")
        print(f"[MQTT] {self.TOPIC_AC} -> MODE_FAN")
        if self.logger:
            self.logger(f"[MQTT] {self.TOPIC_AC} -> MODE_FAN")

    def start(self):
        self.mqtt.subscribe("ui/mcuB/ac/state", self._on_state)

    def power(self, state: bool):
        payload = "ON" if state else "OFF"

        # command ke MCU
        self.mqtt.publish("mcuB/ac", payload)

        # 🔥 STATE UI (retain)
        self.mqtt.publish("ui/mcuB/ac/state", payload, retain=True)

        self.state = state

        if self.logger:
            self.logger(f"[AC STATE] {state}")

    def _on_state(self, client, userdata, msg):
        self.state = msg.payload.decode() == "ON"
