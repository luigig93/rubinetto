#include <M5Atom.h>
#include <WiFi.h>
#include <PubSubClient.h>


//mqtt
//SSID rete WiFi
char ssid[] = "";  
//password rete WiFi
char password[] = "";  
//indirizzo IP broker mqtt
char mqtt_server[] = "";  
WiFiClient espClient;
PubSubClient client(espClient);


//sensore: FS400A G1"
//k-factor: tra 4.5 e 4.8
//relazione frequenza/flusso: 
// .) freq = flow * K_FACTOR
// .) flow = freq / K_FACTOR  (Liter/min)
#define K_FACTOR 4.8

//GPIO input sensore: yellow wire
int flowPin = 25;  
volatile int flow_freq;  

//IRAM_ATTR is for esp32
void IRAM_ATTR Flow()
{
   flow_freq++;
}


void setup() {
  // Initialize the M5Stack object
  M5.begin(true, false, true);

  //wifi setup
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  //mqtt setup
  //1883: port number for mqtt
  client.setServer(mqtt_server, 1883); 
  
  //flow meter setup
  //Sets the pin as an input
  pinMode(flowPin, INPUT);
  //Configures interrupt           
  attachInterrupt(digitalPinToInterrupt(flowPin), Flow, RISING);
}


void loop() {

  //mqtt
  if (!client.connected()) {
      
      //led giallo
      M5.dis.drawpix(0, 0xFFFF00);
  
      // mqtt connection
      while (!client.connected()) {
        // Attempt to connect
        if (!client.connect("atom_flow")) {
          // Wait 5 seconds before retrying
          delay(5000);
        }
     }
     
     //blue led: mqtt connection ok
     M5.dis.drawpix(0, 0x0000FF);
  }
  
  //flow sensor
  // Reset the counter
  flow_freq = 0;  
  //Wait 1 second, sampling period
  delay (1000);   
  //calcolo flusso
  float flow = flow_freq/K_FACTOR; 

  // led feedback
  if(flow_freq > 0){
    //led verde: sta passando acqua
    M5.dis.drawpix(0, 0xf00000);
    
  }else {
    //led rosso: non sta passando acqua
    M5.dis.drawpix(0, 0x00f000);
  }

  //publish: fire and forget 
  char flow_string[5];
  dtostrf(flow, 4, 1, flow_string);
  client.publish("atom/flow", flow_string);
}
