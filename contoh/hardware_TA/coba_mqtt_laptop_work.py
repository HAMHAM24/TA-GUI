
#include <WiFi.h>
#include <PubSubClient.h>

// ===== WIFI =====
const char* ssid = "3KSERA";
const char* password = "04115474";

// ===== MQTT =====
const char* mqtt_server = "192.168.100.4"; // IP broker
const int mqtt_port = 1883;
const char* mqtt_topic = "esp32c/data";

WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastMsg = 0;

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32C_Client")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long now = millis();
  if (now - lastMsg > 2000) {
    lastMsg = now;

    int nilai = random(0, 100);
    char msg[50];
    sprintf(msg, "Nilai sensor: %d", nilai);

    Serial.print("Publish: ");
    Serial.println(msg);

    client.publish(mqtt_topic, msg);
  }
}



