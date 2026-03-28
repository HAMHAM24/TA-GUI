import paho.mqtt.client as mqtt
import json
import time

BROKER = "10.33.11.148"
PORT = 1883
TOPIC = "esp32c/data"

# ================= CALLBACK =================
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("MQTT Connected")
        client.subscribe(TOPIC)
    else:
        print("Connection failed, code:", reason_code)

def on_disconnect(client, userdata, reason_code, properties):
    print("Disconnected from broker. Reconnecting...")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())

        print("===== DATA DITERIMA =====")
        print("Voltage   :", data["voltage"], "V")
        print("Current   :", data["current"], "A")
        print("Power     :", data["power"], "W")
        print("Energy    :", data["energy"], "kWh")
        print("Frequency :", data["frequency"], "Hz")
        print("PF        :", data["pf"])
        print("--------------------------")

    except Exception as e:
        print("Invalid JSON:", e)

# ================= CLIENT =================
client = mqtt.Client(
    client_id="PythonReceiver",
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

# Auto reconnect setting
client.reconnect_delay_set(min_delay=1, max_delay=5)

# ================= CONNECT LOOP =================
while True:
    try:
        print("Connecting to MQTT broker...")
        client.connect(BROKER, PORT, 60)
        client.loop_forever()
    except Exception as e:
        print("Connection error:", e)
        time.sleep(3)