#include <M5Atom.h>
#include <WiFi.h>
#include <PubSubClient.h>


//mqtt
char ssid[] = "";  //SSID rete WiFi
char password[] = "";  //password rete WiFi
char mqtt_server[] = "";  //indirizzo IP broker MQTT
WiFiClient espClient;
PubSubClient client(espClient);


//sensore: FS400A G1"
//k-factor: tra 4.5 e 4.8
//relazione frequenza/flusso: 
// .) freq = flow * K_FACTOR
// .) flow = freq / K_FACTOR  (Liter/min)
#define K_FACTOR 4.8
int flowPin = 21;  //GPIO input sensore
volatile int flow_freq; //This integer needs to be set as volatile to ensure it updates correctly during the interrupt process. 

//IRAM_ATTR is for esp32
void IRAM_ATTR Flow()
{
   flow_freq++; //Every time this function is called, increment "count" by 1
}


void setup() {
  // Initialize the M5Stack object
  M5.begin(true, false, true);

  //wifi setup
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    //inserisci led giallo
    M5.dis.drawpix(0, 0xFFFF00);
  }

  //mqtt setup
  client.setServer(mqtt_server, 1883); //1883: port number for MQTT

  //debug
  Serial.println(WiFi.localIP());
  
  //flow meter setup
  pinMode(flowPin, INPUT);           //Sets the pin as an input
  attachInterrupt(digitalPinToInterrupt(flowPin), Flow, RISING);  //Configures interrupt 0 (pin 2 on the Arduino Uno) to run the function "Flow"
}


void loop() {

  //mqtt
  if (!client.connected()) {
      // Loop until we're reconnected
      while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        // Attempt to connect
        if (client.connect("atom_flow")) {
          Serial.println("connected");
          //led blue indica connessione WiFi e MQTT riuscita
          M5.dis.drawpix(0, 0x0000FF);
      
        } else {
          Serial.print("failed, rc=");
          Serial.print(client.state());
          // Wait 5 seconds before retrying
          delay(5000);
        }
     }
  }

  //dovrebbe servire solamente per subscribe
  //client.loop();
  
  //flow sensor
  flow_freq = 0;  // Reset the counter so we start counting from 0 again
  delay (1000);   //Wait 1 second, sampling period, maybe adjust it
  float flow = flow_freq/K_FACTOR; //calcolo flusso

  if(flow_freq > 0){
    //led verde: sta passando acqua
    M5.dis.drawpix(0, 0xf00000);
    
  }else {
    //led rosso: non sta passando acqua
    M5.dis.drawpix(0, 0x00f000);
  }

  //publish
  char flow_string[5];
  dtostrf(flow, 4, 1, flow_string);
  client.publish("atom/flow", flow_string);
  //debug
  Serial.printf("flow: %.1f L/m\r\n", flow);
}
