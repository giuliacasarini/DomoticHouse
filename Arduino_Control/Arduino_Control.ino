#include <dht.h>
#include <Servo.h>
#include <IRremote.h>
#include <IRremoteInt.h>
#include <LiquidCrystal_I2C.h>


dht DHT;          
int dhtPin = 12;
int rgbPinR = 10;
int rgbPinG = 9;
int rgbPinB = 11;  
int motionPin = 8;
int lightPin = 6;
int servoPin = 3;
int photoPin = A0;
int lightState = 0;
int des_temp = 0;
int light_state = 0;
int windows_state = 0;
Servo myservo;
unsigned long timestamp;//timer
int RECV_PIN = 4; // Infrared receiving pin
IRrecv irrecv(RECV_PIN); // Create a class object used to receive class 
decode_results results; // Create a decoding results class object
LiquidCrystal_I2C lcd(0x3F, 16, 2);

void color (unsigned char red, unsigned char green, unsigned char blue) //function to set RGB led color
{
  analogWrite(rgbPinR, red); 
  analogWrite(rgbPinG, green); 
  analogWrite(rgbPinB, blue); 
} 

void setup() {
  pinMode(motionPin, INPUT);
  pinMode(rgbPinR,OUTPUT);
  pinMode(rgbPinG,OUTPUT);
  pinMode(rgbPinB,OUTPUT);
  color(255, 255, 255);
  pinMode(lightPin,OUTPUT);
  myservo.attach(servoPin);
  myservo.write(90);
  timestamp = millis(); //timer for sensor data sending
  Serial.begin(9600); // Initialize the serial port and set the baud rate to 9600
  irrecv.enableIRIn(); // Start the receiver
  lcd.init(); // initialize the lcd
  lcd.backlight(); // Turn on backlight
}

void loop() {
    if(Serial.available() > 0){
      int actuator;
      int data;
      actuator = Serial.read();
      if (actuator == 1)
      { //boiler
        data = Serial.read();
        if (data=='A') color(255, 0, 0);
        if (data=='S') color(255, 255, 255);
      }
      if (actuator == 2)
      { //windows
        data = Serial.read();
        if (data=='A') myservo.write(0);
        if (data=='S') myservo.write(90);
      }
      if (actuator == 3)
      { //lights
        data = Serial.read();
        if (data=='A') digitalWrite(lightPin, HIGH);
        if (data=='S') digitalWrite(lightPin, LOW);
      }
      if (actuator == 4)
      { //air conditioner
        data = Serial.read();
        if (data=='A') color(0, 0, 255);
        if (data=='S') color(255, 255, 255);
      }
    }
    // Read DHT and judge the state according to the return value
    int chk = DHT.read11(dhtPin);
    int motion = digitalRead(motionPin);
    int photoValue = analogRead(photoPin);
    lcd.setCursor(1,0);
    lcd.print("Temperature: ");
    lcd.setCursor(1,1);
    lcd.print(DHT.temperature);// Prints actual temperature to the LCD
    if (irrecv.decode(&results)) // Waiting for decoding
    { 
      switch (results.value) {
        case 0xFF02FD: // Received "+"
          des_temp = 1;  // Increase temperature
          Serial.write(0xFF);
          Serial.write(2);
          Serial.write(3);
          Serial.write(des_temp);
          Serial.write(0xFE); 
          break;
        case 0xFF9867: // Received "-"
          des_temp = 1; // Decrease temperature
          Serial.write(0xFF);
          Serial.write(2);
          Serial.write(4);
          Serial.write(des_temp);
          Serial.write(0xFE); 
        break;
        case 0xFFA25D: // Received "ON/OFF"
          light_state = 1; //turn on/off lights
          Serial.write(0xFF);
          Serial.write(2);
          Serial.write(5);
          Serial.write(light_state);
          Serial.write(0xFE); 
        break;
        case 0xFF6897: // Received "0" 
          windows_state = 1;//open/close windows
          Serial.write(0xFF);
          Serial.write(2);
          Serial.write(6);
          Serial.write(windows_state);
          Serial.write(0xFE); 
        break;
      }
      irrecv.resume(); // Next Value
    }

    if (millis() - timestamp > 15000)
    {
      switch (chk)
      {
        case DHTLIB_OK: 
          //sending packet containing sensors data on serial port
          Serial.write(0xFF);
          Serial.write(3);

          Serial.write(int(DHT.temperature));
          Serial.write(motion);
          Serial.write(photoValue);

          Serial.write(0xFE); 

          timestamp = millis();
          light_state = 0;
          windows_state = 0;
          des_temp = 0;

          break;
        case DHTLIB_ERROR_CHECKSUM: // Checksum error
          //Serial.println("Checksum error");
          break;
        case DHTLIB_ERROR_TIMEOUT:  // Time out error
          //Serial.println("Time out error");
          break;
        default: // Unknown error
          //Serial.println("Unknown error");
          break;
      }
    }
}

