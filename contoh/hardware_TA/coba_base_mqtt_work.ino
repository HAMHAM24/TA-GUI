import paho.mqtt.client as mqtt

BROKER = "192.168.100.4"
PORT = 1883
TOPIC = "esp32c/data"

def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected, reason code:", reason_code)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    print(f"{msg.topic} -> {msg.payload.decode()}")

client = mqtt.Client(
    client_id="PythonClient",
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.on_connect = on_connect
client.on_message = on_message

print("Connecting to broker...")
client.connect(BROKER, PORT, 60)
client.loop_forever()
