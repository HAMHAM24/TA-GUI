#include <PZEM004Tv30.h>

// === PIN UART PZEM ===
#define PZEM_RX_PIN 2   // ESP32-C3 RX  <- PZEM TX
#define PZEM_TX_PIN 3   // ESP32-C3 TX  -> PZEM RX

// Gunakan UART1 (WAJIB di ESP32-C3)
HardwareSerial PZEMSerial(1);

// Inisialisasi PZEM (INI CARA BENAR)
PZEM004Tv30 pzem(PZEMSerial, PZEM_RX_PIN, PZEM_TX_PIN);

void setup() {
  Serial.begin(115200);

  // Start UART PZEM
  PZEMSerial.begin(9600, SERIAL_8N1, PZEM_RX_PIN, PZEM_TX_PIN);

  Serial.println("ESP32-C3 + PZEM004T v3.0");
}

void loop() {

  Serial.print("Custom Address: 0x");
  Serial.println(pzem.readAddress(), HEX);

  float voltage   = pzem.voltage();
  float current   = pzem.current();
  float power     = pzem.power();
  float energy    = pzem.energy();
  float frequency = pzem.frequency();
  float pf        = pzem.pf();

  if (isnan(voltage)) {
    Serial.println("PZEM not responding");
  } else {
    Serial.print("Voltage   : "); Serial.print(voltage); Serial.println(" V");
    Serial.print("Current   : "); Serial.print(current); Serial.println(" A");
    Serial.print("Power     : "); Serial.print(power);   Serial.println(" W");
    Serial.print("Energy    : "); Serial.print(energy,3);Serial.println(" kWh");
    Serial.print("Frequency : "); Serial.print(frequency,1); Serial.println(" Hz");
    Serial.print("PF        : "); Serial.println(pf);
  }

  Serial.println("--------------------------------");
  delay(2000);
}
