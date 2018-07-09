
// Libs
#include <MFRC522.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>

// Pins
#define SS_PIN 2
#define RST_PIN 15

// Network
IPAddress ip(192, 168, 0, 61);
IPAddress gateway(192, 168, 0, 50);
IPAddress subnet(255, 255, 255, 0);
const char* wifi_ssid = "FactoryNetwork";
const char* wifi_password = "changeme";
const char* mqtt_server = "192.168.0.32";
const int mqtt_port = 1883;

// Setup
MFRC522 mfrc522(SS_PIN, RST_PIN);
WiFiClient wifi_client;
PubSubClient mqtt_client(wifi_client);

// MQTT
const char* mqtt_id = "ESP8266Client";
const char* mqtt_username = "esp8266";
const char* mqtt_pw = "changeme";
const char* mqtt_topic = "candy";

//char name [10] = "";
//int n = 0;
long last_msg = 0;
//char msg[50];
//int value = 0;

void setup()
{
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();
  setup_wifi();
  mqtt_client.setServer(mqtt_server, mqtt_port);
  mqtt_client.setCallback(mqtt_callback);
}

void setup_wifi() {

  delay(10);
  // Connecting to a WiFi network
  Serial.print("\nConnecting to: ");
  Serial.println(wifi_ssid);

  WiFi.config(ip, gateway, subnet);

  WiFi.begin(wifi_ssid, wifi_password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connection established.");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [topic=");
  Serial.print(topic);
  Serial.print("]: ");
  for (int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

void reconnect() {
  // Loop until we're reconnected
  while (!mqtt_client.connected()) {
    Serial.println("Attempting to connect to MQTT broker...");
    // Attempt to connect
    if (mqtt_client.connect(mqtt_id, mqtt_username, mqtt_pw)) {
      Serial.println("Connection to MQTT broker established.");
    } else {
      Serial.print("Failed to establish connection to MQTT broker, rc=");
      Serial.print(mqtt_client.state());
      Serial.println(" retrying in 5 seconds.");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

void loop()
{ 

  // Establish connection to MQTT broker
  if (!mqtt_client.connected())
    reconnect();

  mqtt_client.loop();

  // Read RFID tags 
  MFRC522::StatusCode status;
  byte block;
  byte len;
  byte read_buffer[18];
  block = 4;
  len = 18;
  
  if (!mfrc522.PICC_IsNewCardPresent())
    return;
    
  if (!mfrc522.PICC_ReadCardSerial())
    return;
    
  long code = 0;
  for (byte i = 0; i < mfrc522.uid.size; i++)
    code=((code+mfrc522.uid.uidByte[i])*10);
  
  Serial.print("Code: ");
  Serial.println(code);
      
  status = mfrc522.MIFARE_Read(block, read_buffer, &len);
  if (status != MFRC522::STATUS_OK) {
    Serial.print(F("Read failed: "));
    Serial.println(mfrc522.GetStatusCodeName(status));
    return;
  }
  
  // Candy tag
  char name[10] = "";
  int n = 0;
  for (uint8_t i = 9; i < 16; i++)
  {
    if (read_buffer[i] != 32 && isalpha(read_buffer[i]))
      {
        if(n<=10) 
        {
          name[n] = read_buffer[i];
          n++;
        }
      }
  }
  
  publish_candy_message(name);
  log_candy(name);
  delay(500);
}

void log_candy(const char* name)
{
  Serial.print("[ip=");
  Serial.print(WiFi.localIP());
  Serial.print(",candy=");
  Serial.print(name);
  Serial.println("]");
}

void publish_candy_message(const char* name) 
{
  long now = millis();
  if (now - last_msg > 2000) {
    last_msg = now;
    Serial.print("Publish message: ");
    Serial.println(name);
    mqtt_client.publish(mqtt_topic, name);
  }
}
  


