#include <M5Atom.h>
#include <WiFi.h>
#include <PubSubClient.h>

//MQTT parameters
char ssid[] = "";   //wifi ssid
char password[] = "";  //wifi password
char mqtt_server[] = "";  //MQTT Broker IP address
WiFiClient atomClient;
PubSubClient client(atomClient);


void setup()
{
    M5.begin(true, false, true);
    
    //MQTT
    setup_wifi();
    client.setServer(mqtt_server, 1883);  //1883: MQTT port number    
    client.setCallback(callback);

    //RELAY
    //relay1: yellow wire In1 
    pinMode(25, OUTPUT);
    //relay2: white wire In2 
    pinMode(21, OUTPUT);
}


void setup_wifi() {
  delay(10);
  // We start by connecting to a WiFi network
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    //led giallo
    M5.dis.drawpix(0, 0xFFFF00);
    delay(500);
    M5.dis.clear();
  }

  //blue led
  M5.dis.drawpix(0, 0x0000FF);
}


void callback(char* topic, byte* message, unsigned int length) {
  String messageString;

  //ricostruzione messaggio
  for (int i = 0; i < length; i++) {
    messageString += (char)message[i];
  }

  
  if (String(topic) == "atom/water") {
      if(messageString == "on"){    
          //switch on water
          //dobbiamo aprire
          digitalWrite(25, HIGH);
          delay(200);
          digitalWrite(25, LOW);
          delay(200);
          //green led
          M5.dis.drawpix(0, 0xf00000);
          
      }else if(messageString == "off") {
          //switch off water
          //dobbiamo chiudere
          digitalWrite(21, HIGH);
          delay(200);
          digitalWrite(21, LOW);
          delay(200);
          //red led
          M5.dis.drawpix(0, 0x00f000);
      }
  }
}


void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {  
    //led giallo
    M5.dis.drawpix(0, 0xFFFF00);
    // Attempt to connect
    if (client.connect("atom_xxx")) {
      // Subscribe to water topic
      client.subscribe("atom/water");
      
    } else {
      // Wait 5 seconds before retrying
      delay(5000);
      M5.dis.clear();
    }
  }

  //red led
  M5.dis.drawpix(0, 0x00f000);
}


void loop()
{
  if (!client.connected()) {
    reconnect();
  }
  
  client.loop();
}
