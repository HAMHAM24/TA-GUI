#include <WiFi.h>
#include <PubSubClient.h>
#include <PZEM004Tv30.h>
#include <DS1302.h>

// ================= WIFI =================
const char* ssid = "3KSERA";
const char* password = "04115474";

// ================= MQTT =================
const char* mqtt_server = "192.168.100.4";
const int   mqtt_port   = 1883;
const char* mqtt_topic  = "esp32c/data";

// ================= PZEM =================
#define PZEM_RX_PIN 5   // ESP32-C3 RX  <- PZEM TX
#define PZEM_TX_PIN 6   // ESP32-C3 TX  -> PZEM RX
HardwareSerial PZEMSerial(1);
PZEM004Tv30 pzem(PZEMSerial, PZEM_RX_PIN, PZEM_TX_PIN);

// ================= RTC =================
#define RTC_CE   4
#define RTC_IO   3
#define RTC_SCLK 2

DS1302 rtc(RTC_CE, RTC_IO, RTC_SCLK);

// ================= MQTT CLIENT =================
WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastPublish = 0;
unsigned long lastWifiCheck = 0;

// ================= WIFI =================
void start_wifi() {
  WiFi.mode(WIFI_STA);

  WiFi.setSleep(false);                 // Non power save
  WiFi.setAutoReconnect(true);          // Auto reconnect
  WiFi.persistent(false);               // Tidak simpan config flash
  WiFi.setTxPower(WIFI_POWER_8_5dBm);   // Set daya pancar (opsional)

  WiFi.begin(ssid, password);
  Serial.println("WiFi connecting...");
}
// ================= MQTT =================
void reconnectMQTT() {
  if (!client.connected()) {
    Serial.print("MQTT connecting...");
    if (client.connect("ESP32C3_PZEM")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.println(client.state());
    }
  }
}

// ================= SETUP =================
void setup() {
  Serial.begin(115200);

  // RTC init
  rtc.writeProtect(false);
  rtc.halt(false);

  // ===== SET WAKTU SEKALI SAJA =====
  Time t(2026, 2, 6, 10, 30, 0, Time::kFriday);
  rtc.time(t);

  start_wifi();
  client.setServer(mqtt_server, mqtt_port);
}

// ================= LOOP =================
void loop() {

  // ===== WIFI CHECK =====
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - lastWifiCheck > 10000) {
      lastWifiCheck = millis();
      Serial.println("Retry WiFi...");
      WiFi.disconnect();
      WiFi.begin(ssid, password);
    }
    return;
  }

  static bool wifiShown = false;
  if (!wifiShown) {
    Serial.print("WiFi Connected, IP: ");
    Serial.println(WiFi.localIP());
    wifiShown = true;

    PZEMSerial.begin(9600, SERIAL_8N1, PZEM_RX_PIN, PZEM_TX_PIN);
  }

  reconnectMQTT();
  client.loop();

  if (millis() - lastPublish > 3000) {
    lastPublish = millis();

    // ===== BACA RTC =====
    Time now = rtc.time();

    Serial.print("Tanggal: ");
    Serial.print(now.yr); Serial.print("-");
    Serial.print(now.mon); Serial.print("-");
    Serial.print(now.date);

    Serial.print(" | Waktu: ");
    Serial.print(now.hr); Serial.print(":");
    Serial.print(now.min); Serial.print(":");
    Serial.println(now.sec);

    // ===== BACA PZEM =====
    float voltage   = pzem.voltage();
    float current   = pzem.current();
    float power     = pzem.power();
    float energy    = pzem.energy();
    float frequency = pzem.frequency();
    float pf        = pzem.pf();

    if (!isnan(voltage)) {

      Serial.print("Voltage   : "); Serial.print(voltage); Serial.println(" V");
      Serial.print("Current   : "); Serial.print(current); Serial.println(" A");
      Serial.print("Power     : "); Serial.print(power);   Serial.println(" W");
      Serial.print("Energy    : "); Serial.print(energy,3);Serial.println(" kWh");
      Serial.print("Frequency : "); Serial.print(frequency,1); Serial.println(" Hz");
      Serial.print("PF        : "); Serial.println(pf);

      // MQTT hanya kirim PZEM saja
      String payload = "{";
      payload += "\"voltage\":" + String(voltage,2) + ",";
      payload += "\"current\":" + String(current,3) + ",";
      payload += "\"power\":" + String(power,2) + ",";
      payload += "\"energy\":" + String(energy,3) + ",";
      payload += "\"frequency\":" + String(frequency,1) + ",";
      payload += "\"pf\":" + String(pf,2);
      payload += "}";

      client.publish(mqtt_topic, payload.c_str());
    }
    else {
      Serial.println("PZEM not responding");
    }

    Serial.println("--------------------------------");
  }
}



