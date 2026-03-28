  #include <WiFi.h>
  #include <PubSubClient.h>
  #include <PZEM004Tv30.h>

  // ================= WIFI =================
  const char* ssid = "3KSERA";
  const char* password = "04115474";

  // ================= MQTT =================
  const char* mqtt_server = "192.168.100.4";
  const int   mqtt_port   = 1883;
  const char* mqtt_topic  = "esp32c/data";

  // ================= PZEM =================
  #define PZEM_RX_PIN 2
  #define PZEM_TX_PIN 3

  HardwareSerial PZEMSerial(1);
  PZEM004Tv30 pzem(PZEMSerial, PZEM_RX_PIN, PZEM_TX_PIN);

  // ================= MQTT CLIENT =================
  WiFiClient espClient;
  PubSubClient client(espClient);

  unsigned long lastPublish = 0;
  unsigned long lastWifiCheck = 0;

  // ================= WIFI START =================
  void start_wifi() {
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);  // bikin lebih cepat & stabil
    WiFi.begin(ssid, password);
    Serial.println("WiFi connecting...");
  }

  // ================= MQTT RECONNECT NON BLOCK =================
  void reconnectMQTT() {
    if (!client.connected()) {
      Serial.print("MQTT connecting...");
      if (client.connect("ESP32C3_PZEM")) {
        Serial.println("connected");
      } else {
        Serial.println("failed");
      }
    }
  }

  // ================= SETUP =================
  void setup() {
    Serial.begin(115200);

    start_wifi();
    client.setServer(mqtt_server, mqtt_port);
  }

  // ================= LOOP =================
  void loop() {

    // ===== WIFI CHECK =====
    if (WiFi.status() != WL_CONNECTED) {
      if (millis() - lastWifiCheck > 10000) {   // retry tiap 10 detik
        lastWifiCheck = millis();
        Serial.println("Retry WiFi...");
        WiFi.disconnect();
        WiFi.begin(ssid, password);
      }
      return;  // jangan lanjut kalau WiFi belum connect
    }

    // Jika baru connect, tampilkan IP sekali
    static bool wifiShown = false;
    if (!wifiShown) {
      Serial.print("WiFi Connected, IP: ");
      Serial.println(WiFi.localIP());
      wifiShown = true;

      // Start PZEM setelah WiFi stabil
      PZEMSerial.begin(9600, SERIAL_8N1, PZEM_RX_PIN, PZEM_TX_PIN);
    }

    // ===== MQTT =====
    reconnectMQTT();
    client.loop();

    // ===== PUBLISH DATA =====
    if (millis() - lastPublish > 3000) {
      lastPublish = millis();

      float voltage   = pzem.voltage();
      float current   = pzem.current();
      float power     = pzem.power();
      float energy    = pzem.energy();
      float frequency = pzem.frequency();
      float pf        = pzem.pf();

      if (!isnan(voltage)) {

        String payload = "{";
        payload += "\"voltage\":" + String(voltage,2) + ",";
        payload += "\"current\":" + String(current,3) + ",";
        payload += "\"power\":" + String(power,2) + ",";
        payload += "\"energy\":" + String(energy,3) + ",";
        payload += "\"frequency\":" + String(frequency,1) + ",";
        payload += "\"pf\":" + String(pf,2);
        payload += "}";

        client.publish(mqtt_topic, payload.c_str());
        Serial.println(payload);
      } else {
        Serial.println("PZEM not responding");
      }
    }
  }
