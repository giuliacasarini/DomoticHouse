import serial
from serial.tools import list_ports as ports_list
import configparser
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
import threading

class Bridge():

    def __init__(self):
        try:
            self.config = configparser.ConfigParser()
            self.config.read('bridge_config.ini')
            self.setupSerial()
            self.setupMQTT()
            self.lock = threading.Lock()
            self.id = 1 #id of the house 
        except Exception as e: 
            print(e)

    def setupSerial(self):
        #trying to open serial port
        self.ser = None
        try:
            if self.config.get("Serial", "UseDescription", fallback=False):
                self.portname = self.config.get("Serial", "Portname", fallback="COM5")
            else:
                print("list of available ports: ")
                ports = ports_list.comports()

                for port in ports:
                    print(port.device)
                    print(port.description)
                    if self.config.get("Serial", "PortDescription", fallback="arduino").lower() \
                            in port.description.lower():
                        self.portname = port.device
                        
            if self.portname is not None:
                print("connecting to " + self.portname)
                self.ser = serial.Serial(self.portname, 9600, timeout=0)
        except Exception as e: 
                print(e)

        #internal input buffer from serial
        self.inbuffer = []

    def setupMQTT(self): #mqtt connection setup
        try:
            self.clientMQTT = mqtt.Client()
            self.clientMQTT.on_connect = self.on_connect
            print("Connecting to MQTT broker...")
            self.clientMQTT.connect(
               self.config.get("MQTT", "Server", fallback="broker.hivemq.com"),
               self.config.getint("MQTT", "Port", fallback = 1883),
               60)
            self.clientMQTT.loop_start()
        except Exception as e: 
            print(e)

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))


    def loopSensori(self):
        #infinite loop for sensors managing
        while (True):
            try:   
                self.lock.acquire()
                if not self.ser is None:
                    if self.ser.in_waiting>0:
                        lastchar=self.ser.read(1)
                        self.lock.release()
                        #saving data into buffer until a packet footer is received, so we know the package is ended
                        if lastchar==b'\xfe': #EOL
                            self.useData()
                            self.inbuffer =[]
                        else:
                            self.inbuffer.append (lastchar)
                    else:
                        self.lock.release()  
                else:
                    self.lock.release()
            except Exception as e: 
                print(e)
    
    def loopAttuatori(self):
         #infinite lopp for actuators managing
        while (True):
            try:
                msg = subscribe.simple("LPGCActuators/" + str(self.id) + "/#", hostname="broker.hivemq.com", port=1883)
                actuator = int(msg.topic.split("/",2)[2])
                val = int(str(msg.payload).split("'",2)[1])
                strval = "Actuator %d: %d " % (actuator, val)
                #print(strval)
                if actuator == 0:
                    self.lock.acquire()
                    self.ser.write(actuator.to_bytes(1,byteorder='little'))
                    self.ser.write (val.to_bytes(1,byteorder='little'))
                    self.lock.release()
                else:
                    if val==1:
                        self.lock.acquire()
                        self.ser.write(actuator.to_bytes(1,byteorder='little'))
                        self.ser.write (b'A')
                        self.lock.release()
                    else:
                        self.lock.acquire()
                        self.ser.write(actuator.to_bytes(1,byteorder='little'))
                        self.ser.write(b'S')
                        self.lock.release()
            except Exception as e: 
                print(e)
            
        

    def useData(self):
        #i have received a packet from the serial port. I can use it
        if len(self.inbuffer)<4: #at least header, size, footer
            return False
        #split parts
        if self.inbuffer[0] != b'\xff':
            return False
        try:
            numval = int.from_bytes(self.inbuffer[1], byteorder='little')
            if (numval < 3):
                i = int.from_bytes(self.inbuffer[2], byteorder='little')
                val = int.from_bytes(self.inbuffer[3], byteorder='little')
                strval = "Sensor %d: %d " % (i, val)
                print(strval)
                self.clientMQTT.publish('LPGCSensors/' + str(self.id) + '/{:d}'.format(i),'{:d}'.format(val))

            else:  
                for i in range (numval):
                    val = int.from_bytes(self.inbuffer[i+2], byteorder='little')
                    strval = "Sensor %d: %d " % (i, val)
                    print(strval)
                    self.clientMQTT.publish('LPGCSensors/' + str(self.id) + '/{:d}'.format(i),'{:d}'.format(val))
        except Exception as e: 
            print(e)

if __name__ == '__main__':
    br=Bridge()
    
    tA = threading.Thread(target=br.loopAttuatori, name='tA') 
    tS = threading.Thread(target=br.loopSensori, name='tS') 

    tA.start()
    tS.start()
    
    tA.join()
    tS.join()