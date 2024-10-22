import configparser
import paho.mqtt.client as mqtt
import time
import datetime
import requests
import pandas as pd

from house import House

weather_api_key = "e1cc4990d13b2adf429027669e3817ad"

class Server():

	def __init__(self):
		self.config = configparser.ConfigParser()
		self.config.read('server_config.ini')
		self.setupMQTT()

		self.houses_list = [] #list containing the houses we are controlling
		h1 = House(1)
		h2 = House(2)
		h3 = House(3)
		h4 = House(4)
		self.houses_list.append(h1)
		self.houses_list.append(h2)
		self.houses_list.append(h3)
		self.houses_list.append(h4)

		self.current_slot = 0 #id of the current house that has power assigned
		self.slot_timer = time.perf_counter() #timer to change slot assignment after some time  

	def setupMQTT(self):
		try:
			self.clientMQTT = mqtt.Client()
			self.clientMQTT.on_connect = self.on_connect
			self.clientMQTT.on_message = self.on_message
			print("connecting to MQTT broker...")
			self.clientMQTT.connect(
				self.config.get("MQTT","Server", fallback= "broker.hivemq.com"),
				self.config.getint("MQTT","Port", fallback= 1883),
				60)

			self.clientMQTT.loop_start()
		except Exception as e: 
			print(e)


	def on_connect(self, client, userdata, flags, rc):
		try:
			print("Connected with result code " + str(rc))

			# Subscribing in on_connect() means that if we lose the connection and
			# reconnect then subscriptions will be renewed.
			for h in self.houses_list: #subscribing to a different sensors topic for each house
				self.clientMQTT.subscribe("LPGCSensors/"+ str(h.id) + "/#")
		except Exception as e: 
			print(e)

	
	def assign_slots(self):
		toc = time.perf_counter()
		slot_elapsedtime = int(toc - self.slot_timer)
		if(self.houses_list[self.current_slot].presence == True and slot_elapsedtime < 180): #someone is in the house and slot timer > 180 secs
			#if the slot is not already activated for the house
			if (self.houses_list[self.current_slot].power_permission == False):
				print("Energy slot assigned to house " + str(self.houses_list[self.current_slot].id))
				self.houses_list[self.current_slot].power_permission = True
		else: #if previous house can't be powered on, then power_permission false
			self.houses_list[self.current_slot].power_permission = False
			#if the slot is in the houses range, we increase to next slot and timer get restarted	
			if self.current_slot < (len(self.houses_list)-1):
				self.current_slot += 1
				self.slot_timer = time.perf_counter()
			else: #otherwise, current slot get initialized to 0 and the cycle can start again
				self.current_slot = 0


	# The callback for when a PUBLISH message is received from the server.
	def on_message(self, client, userdata, msg):
		try:
			
			#print(msg.topic + " " + str(msg.payload))
			split = msg.topic.split("/",2)
			house_id = int(split[1]) 
			current_house = self.houses_list[house_id-1]
			sensor = int(split[2])
			val = int(str(msg.payload).split("'",2)[1])
			#getting house id, sensor id and sensor value from the message

			toc = time.perf_counter()

		
			if (current_house.holiday == False): #EVERYDAY LIFE MODE

				location = 'Modena'
				# Weather API request to get current forecast of the location above
				url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={weather_api_key}"
				response = requests.get(url)
				data = response.json()
				df = pd.DataFrame(data["weather"])
				valMeteo = df["main"].item()

				now = datetime.datetime.now() #setting hours for day and night periods
				start_night = now.replace(hour = int(22), minute = int(00))
				start_day = now.replace(hour = int(6), minute = int(00))

				if (sensor == 0): #temperature sensor
					current_house.temperature = val

				elif(sensor == 1): #motion sensor
					if (datetime.datetime.now() < start_night or datetime.datetime.now() > start_day): #day
						movement_elapsedtime = int(toc - current_house.presence_timer) #time passed since last movement was detected
						
						if (val == 0 and movement_elapsedtime > 120 and current_house.presence == True): #if sensor value = 0 and no movement detected for 120 secs, no one is in the house
							current_house.presence = False
							print('House ' + str(current_house.id) + ' : no presence detected') 
						elif (val == 1 and current_house.presence == False) : #if sensor value = 1, someone is in the house
							current_house.presence = True
							current_house.presence_timer = time.perf_counter()
							print('House ' + str(current_house.id) + ' : presence detected')
					else: #night -> assuming everyone is at home on night, but maybe sleeping so no movement gets detected
						current_house.presence = True
				
				elif(sensor == 2): #photoresistor 
					current_house.photoresistor = val
				elif(sensor == 3): #remote command to increase temperature
					current_house.des_temperature += val

				elif(sensor == 4): #remote command to decrease temperature
					current_house.des_temperature -= val

				elif(sensor == 5): #remote command for lights
					current_house.lights_state = val

				elif(sensor == 6): #remote command for windows
					current_house.windows_state = val

				#LIGHTS
				lights_elapsedtime = int(toc - current_house.lights_timer) #time passed since last time lights have been turned on/off
				if ((current_house.photoresistor > 300 and current_house.presence == True and current_house.lights == False and lights_elapsedtime > 60) or (current_house.lights_state == 1 and current_house.lights == False)):
					self.lights_on(current_house.id)
				elif(((current_house.photoresistor <= 300 or current_house.presence == False) and current_house.lights == True and lights_elapsedtime > 60) or (current_house.lights_state == 1 and current_house.lights == True)):
					self.lights_off(current_house.id)

				#WINDOWS
				windows_elapsedtime = int(toc - current_house.windows_timer) #time passed since last windows opening
				#check meteo to decide if the windows should open or not, while there's no one at home
				if((valMeteo == "Clear" and current_house.presence == False and windows_elapsedtime > 240 and current_house.windows == False) or (current_house.windows_state == 1 and current_house.windows == False)):
					self.open_windows(current_house.id)
				elif((windows_elapsedtime > 120 and current_house.windows == True) or (current_house.windows_state == 1 and current_house.windows == True)):
					self.close_windows(current_house.id)

				if(datetime.datetime.now().month < 5 or datetime.datetime.now().month > 9):
					#BOILER -> WINTER
					if (datetime.datetime.now() < start_night or datetime.datetime.now() > start_day): #day
						if(current_house.temperature < current_house.des_temperature and current_house.boiler == False and current_house.power_permission == True): #boiler turned on if temperature is under desired one
							print('House ' + str(current_house.id) + ' : boiler on')
							self.publish_commands(current_house.id, 1, 1)
							current_house.boiler = True
						elif((current_house.temperature >= current_house.des_temperature and current_house.boiler == True) or (current_house.power_permission == False and current_house.boiler == True)): #boiler turned off if temperature is above desired one or time slot is finished
							print('House ' + str(current_house.id) + ' : boiler off')
							self.publish_commands(current_house.id, 1, 0)
							current_house.boiler = False
					else: #night -> boiler turned off because everyone is sleeping
							print('House ' + str(current_house.id) + ' : boiler off')
							self.publish_commands(current_house.id, 1, 0)
							current_house.boiler = False
				else:
					#AIR CONDITIONER -> SUMMER
					if(current_house.temperature >= current_house.des_temperature and current_house.air_conditioner == False and current_house.power_permission == True ): ##air conditioner turned on if temperature is above desired one 
						print('House ' + str(current_house.id) + ' : air conditioner on')
						self.publish_commands(current_house.id, 4, 1)
						current_house.air_conditioner = True
					elif((current_house.temperature < current_house.des_temperature and current_house.air_conditioner == True) or (current_house.air_conditioner == True and current_house.power_permission == False)): #air conditioner turned off if temperature is under desired one or time slot is finished
						print('House ' + str(current_house.id) + ' : air conditioner off')
						self.publish_commands(current_house.id, 4, 0)
						current_house.air_conditioner = False

			else: #HOLIDAY MODE
				print('House ' + str(current_house.id) + ' : holiday on') 
				if (sensor == 1): #motion sensor
					if (val == 1):
						current_house.holiday = False

		except Exception as e: 
			print(e)


	def publish_commands(self, house_id, actuator, command):
		try:
			self.clientMQTT.publish('LPGCActuators/' + str(house_id) + '/{:d}'.format(actuator),'{:d}'.format(command))
		except Exception as e: 
			print(e)


	def loop(self):
		# infinite loop to manage sensors messages and take decisions
		while (True):
			self.assign_slots()

	def open_windows(self, house_id):
		try:
			current_house = self.houses_list[house_id-1]
			current_house.windows = True
			current_house.windows_state = 0
			self.publish_commands(current_house.id, 2, 1)
			current_house.windows_timer = time.perf_counter()
			print('House ' + str(current_house.id) + ' : windows opened') 
		except Exception as e: 
			print(e)


	def close_windows(self, house_id):
		try:
			current_house = self.houses_list[house_id-1]
			current_house.windows = False
			current_house.windows_state = 0
			self.publish_commands(current_house.id, 2, 0)
			print('House ' + str(current_house.id) + ' : windows closed')
		except Exception as e: 
			print(e)

	def lights_on(self, house_id):
		try:
			current_house = self.houses_list[house_id-1]
			current_house.lights = True
			current_house.lights_state = 0
			current_house.lights_timer = time.perf_counter()
			self.publish_commands(current_house.id, 3, 1)
			print('House ' + str(current_house.id) + ' : lights on')
		except Exception as e: 
			print(e)


	def lights_off(self, house_id):
		try:
			current_house = self.houses_list[house_id-1]
			current_house.lights = False
			current_house.lights_state = 0
			current_house.lights_timer = time.perf_counter()
			self.publish_commands(current_house.id, 3, 0)
			print('House ' + str(current_house.id) + ' : lights off')
		except Exception as e: 
			print(e)

	
	def get_houses(self):
		try:
			return self.houses_list
		except Exception as e: 
			print(e)
