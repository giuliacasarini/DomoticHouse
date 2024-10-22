
import time

class House(): #house class to save current parameters of actuators and sensors for every house

    def __init__(self, id):
        self.id = id
        self.temperature = 0
        self.des_temperature = 20
        self.boiler = False
        self.air_conditioner = False
        self.power_permission = False
        self.timer_shutdown = time.perf_counter()

        self.lights = False
        self.photoresistor = 1000
        self.lights_state = 0
        self.lights_timer = time.perf_counter()

        self.presence = False
        self.presence_timer = time.perf_counter()

        self.windows = False
        self.windows_state = 0
        self.windows_timer = time.perf_counter()

        self.holiday = False
	