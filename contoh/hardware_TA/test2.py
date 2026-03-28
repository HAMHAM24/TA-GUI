import paho.mqtt.client as mqtt

BROKER = "10.33.11.148"
PORT = 1883
TOPIC = "esp32c/simple"

def on_connect(client, userdata, flags, rc):
    print("Connected with code:", rc)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    print("Received:", msg.payload.decode())

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("Connecting to broker...")
client.connect(BROKER, PORT, 60)

client.loop_forever()