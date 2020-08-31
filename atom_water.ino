#include <M5Atom.h>
#include <WiFi.h>
#include <PubSubClient.h>

//HL-52S v1.0 relay module: (ATTENZIONE!) il relè si attiva con un segnale LOW e si disattiva con un segnale HIGH
#define ln1 25  //relay 1 (left) -> yellow wire
#define ln2 21  //relay 2 (right) -> white wire


//wifi ssid
char ssid[] = "";
//wifi password   
char password[] = "";
//mqtt Broker IP address  
char mqtt_server[] = "";
//mqtt client  
WiFiClient atomClient;
PubSubClient client(atomClient);


void setup()
{
    M5.begin(true, false, true);
    
    //WiFi setup
    WiFi.begin(ssid, password);
      
    while (WiFi.status() != WL_CONNECTED) {
      delay(500);
    }

    //mqtt setup
    //1883: mqtt port number 
    client.setServer(mqtt_server, 1883);     
    client.setCallback(callback);

    //relay setup
    //relay1: yellow wire In1 
    pinMode(ln1, OUTPUT);
    digitalWrite(ln1, HIGH);
    
    //relay2: white wire In2 
    pinMode(ln2, OUTPUT);
    digitalWrite(ln2, HIGH);
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
          //aprire elettrovalvola
          digitalWrite(ln2, LOW);
          delay(200);
          digitalWrite(ln2, HIGH);
          delay(200);
          
          //green led: elettrovalvola aperta
          M5.dis.drawpix(0, 0xf00000);
          
      }else if(messageString == "off") {
          //switch off water
          //chiudere elettrovalvola
          digitalWrite(ln1, LOW);
          delay(200);
          digitalWrite(ln1, HIGH);
          delay(200);
          
          //red led: elettrovalvola chiusa
          M5.dis.drawpix(0, 0x00f000);
      }
  }
}


void loop()
{ 
  if (!client.connected()) {
    
      //led giallo
      M5.dis.drawpix(0, 0xFFFF00);
       
      // mqtt connection
      while (!client.connected()) {  
        // Attempt to connect
        if (client.connect("atom_water")) {
          // Subscribe to water topic
          while (!client.subscribe("atom/water")){
                delay(1000);
          }
          
        } else {
          // Wait 5 seconds before retrying
          delay(5000);
        }
      }
  
     //blue led: mqtt connection ok
     M5.dis.drawpix(0, 0x0000FF);
  }
  
  client.loop();
}
