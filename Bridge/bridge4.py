import configparser
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
import threading
import time

class Bridge():

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('bridge_config.ini')
        self.setupMQTT()
        self.lock = threading.Lock()
        self.id = 4

    def setupMQTT(self): #mqtt connection setup
        self.clientMQTT = mqtt.Client()
        self.clientMQTT.on_connect = self.on_connect
        print("Connecting to MQTT broker...")
        self.clientMQTT.connect(
            self.config.get("MQTT", "Server", fallback="broker.hivemq.com"),
            self.config.getint("MQTT", "Port", fallback = 1883),
            60)
        self.clientMQTT.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))

    def loopSensori(self): 
        while (True):   
            self.useData()
            time.sleep(15) #timer to simulate data sending from sensors every 15 seconds like arduino does in the real example

    def loopAttuatori(self): #simulation of actuators commands received
        while (True):
            msg = subscribe.simple("LPGCActuators/" + str(self.id) + "/#", hostname="broker.hivemq.com", port=1883)
            actuator = int(msg.topic.split("/",2)[2])
            val = int(str(msg.payload).split("'",2)[1])
            strval = "Actuator %d: %d " % (actuator, val)
            print(strval)
        

    def useData(self):
        #simulation of sensors data
        data = [16, 0, 500] #temperature, motion, photoresistor

        numval = 3

        for i in range (numval):
            val = data[i]
            strval = "Sensor %d: %d " % (i, val)
            print(strval)
            self.clientMQTT.publish('LPGCSensors/' + str(self.id) + '/{:d}'.format(i),'{:d}'.format(val))


   

if __name__ == '__main__':
    br=Bridge()
    
    tA = threading.Thread(target=br.loopAttuatori, name='tA') 
    tS = threading.Thread(target=br.loopSensori, name='tS') 

    tA.start()
    tS.start()
    
    tA.join()
    tS.join()