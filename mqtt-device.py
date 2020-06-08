#!/usr/bin/python3
import sys
import paho.mqtt.client as mqtt
import json
import RPi.GPIO as GPIO
import threading
import argparse
from pathlib import Path
import subprocess
import time
import Adafruit_DHT
import os
import time
from filelock import Timeout, FileLock


class RPIDeviceConfiguration:
    data = {}
    def __init__(self, configurationFile):
        print("Opening %s configuration file..." % configurationFile)
        try:
            with open(str(configurationFile)) as json_file:
                self.data = json.load(json_file)
        except ValueError as e:
            print('Your settings file(s) contain invalid JSON syntax! Please fix and restart!, {}'.format(str(e)))
            exit(1)

    def getData(self,value):
        return self.data[value]

    def getAll(self):
        return self.data



class RPIDeviceMqtt:
   MQTT_CONNECTION_SUCCESSFUL=0
   MQTT_CONNECTION_INCORRECT_PROTOCOL=1
   MQTT_CONNECTION_INVALID_CLIENT_IDENTIFIER=2
   MQTT_CONNECTION_SERVER_UNAVAILABLE=3
   MQTT_CONNECTION_BAD_USERNAME_OR_PASSWORD=4
   MQTT_CONNECTION_NOT_AUTHORISED=5
   MQTT_CONNECTION_RESULT_STRINGS=[
      "Connection successfully established" ,
      "Connection refused : incorrect protocol", 
      "Connection refused : invalid client identifier", 
      "Connection refused : server unavailable",
      "Connection refused : bad username or password",
      "Connection refused : not authorised"]
   data = {}
   def __init__(self, DeviceConfiguration):
      self.data = DeviceConfiguration.getAll()
      self.deviceId = self.data["device-unique-id"]
      self.mqtt_client = mqtt.Client(self.data["device-unique-id"])
      self.mqtt_client.user_data_set(self.data)
      self.mqtt_client.on_connect = self.on_connect
      self.mqtt_client.on_message = self.on_message
      self.mqtt_client.on_subscribe = self.on_subscribe
      self.mqtt_client.on_disconnect = self.on_disconnect
#      self.topic = self.data["mqtt-topic-base"] + self.data["device-unique-id"]
      if ("gpio-cmd-map" in self.data):
         self.gpiostatus = {v: k for k, v in self.data["gpio-cmd-map"].items()}
      else:
         self.gpiostatus = None
      if ("status-topic" in self.data):
         self.statustopic = self.data["mqtt-topic-base"] + self.data["device-unique-id"] + "/" + self.data["status-topic"]
      else:
         self.statustopic = None
      if ("command-topic" in self.data):
         self.commandtopic = self.data["mqtt-topic-base"] + self.data["device-unique-id"] + "/" + self.data["command-topic"]
      else:
         self.commandtopic = None


   def connect(self):
      self.mqtt_client.connect(self.data["mqtt-server"],self.data["mqtt-port"])
      self.mqtt_client.loop_forever()

   def on_disconnect(self,client, userdata,rc=0):
      if rc != 0:
        print("Unexpected disconnection.")
      get_methods(client)
      attrs = vars(client)
      print("\n".join("%s: %s" % item for item in attrs.items()))
      print("Disconnected from "+str(client))

   def setTopic(self, newTopic):
      self.topic = newTopic

   def on_connect(self,client, userdata, flags, rc):
      if (rc == RPIDeviceMqtt.MQTT_CONNECTION_SUCCESSFUL):
         if (self.commandtopic != None):
            self.subscribe_result = client.subscribe(self.commandtopic)
            print("Subscribing to %s => %d %d" % (self.commandtopic, self.subscribe_result[0], self.subscribe_result[1]))
         if (self.statustopic != None):
            self.subscribe_result = client.subscribe(self.statustopic)
            print("Subscribing to %s => %d %d" % (self.statustopic, self.subscribe_result[0], self.subscribe_result[1]))
         return
      if (rc > 5):
         print("Connection refused : Invalid result")
         exit(1)
      print(RPIDeviceMqtt.MQTT_CONNECTION_RESULT_STRINGS[rc])
      exit(rc)

   def on_message(self,client, userdata, message):
      pass

   def on_subscribe(self,client,userdata,mid,granted_qos):
     if (mid == self.subscribe_result[1]):
         print("OK")

class RPIWindowsPersonalComputer(RPIDeviceMqtt):
    def __init__(self,DeviceConfiguration):
        RPIDeviceMqtt.__init__(self, DeviceConfiguration)
        self.lastUpdate = 0
        if ("computer-username" in self.data):
            self.ComputerUsername = self.data["computer-username"]
        else:
            print("computer-username parameter missing in configuration file!")
            exit(0)
        if ("computer-password" in self.data):
            self.ComputerPassword = self.data['computer-password']
        else:
            print("computer-password parameter missing in configuration file!")
            exit(0)
        if ("computer-ip" in self.data):
            self.ComputerIp = self.data['computer-ip']
        else:
            print("computer-ip parameter missing in configuration file!")
            exit(0)
        if ("computer-macaddr" in self.data):
            self.ComputerMAC = self.data['computer-macaddr']
        else:
            print("computer-macaddr parameter missing in configuration file!")
            exit(0)
        if ("computer-shutdown-timeout" in self.data):
            self.ComputerShutdownTimeout = int(self.data['computer-shutdown-timeout'])
        else:
            self.ComputerShutdownTimeout = 10
        if ("computer-shutdown-message" in self.data):
            self.ComputerShutdownMessage = self.data['computer-shutdown-message']
        else:
            self.ComputerShutdownMessage = "MQTT Shutdown"
        t = threading.Thread(target=self.update_loop, args=())
        t.start()
        self.lastUpdateWake = 0
        self.lastUpdateShutdown = 0 

    def update_loop(self):
        while(1):
           self.update_status()
           time.sleep(30)


    def update_status(self):
        response = os.system("ping -c 1 " + self.ComputerIp)
        if response == 0 :
            res = "ON"
        else:
            res = "OFF"
        print("Publish update status on " + self.statustopic + " " + str(res))
        self.mqtt_client.publish(self.statustopic,str(res))
        self.lastUpdate = time.time()
        return res

    def on_message(self,client, userdata, message):
        msg = str(message.payload.decode("utf-8"))
        print("Received message '" + msg + "' on topic '"  + message.topic + "' with QoS " + str(message.qos))
        if (message.topic == self.commandtopic):
            if (msg == "ON"):
                if (self.update_status() == "OFF"):
                   if (time.time() - self.lastUpdateWake > 180 or self.lastUpdateWake == 0):
                      os.system("wakeonlan " + self.ComputerMAC)
                      print("wakeonlan " + self.ComputerMAC)
                      self.lastUpdateWake = time.time()
                else:
                   print("Il target è già acceso")
            if (msg == "OFF"):
                if (self.update_status() == "ON"):
                   if (time.time() - self.lastUpdateShutdown > 30 or self.lastUpdateShutdown == 0):
                      os.system("net rpc shutdown -f -t " + str(self.ComputerShutdownTimeout) + " -C '" + self.ComputerShutdownMessage  + "' -U " + self.ComputerUsername + "%" + self.ComputerPassword + " -I " + self.ComputerIp)
                      print("net rpc shutdown ")
                      self.lastUpdateShutdown = time.time()
                else:
                    print("Il target è già spento")
#            print("Publish update status on " + self.statustopic + " " + str(self.gpiostatus[self.currentValue]))
#            self.mqtt_client.publish(self.statustopic,str())
            self.update_status()


class RPIGPIODevice(RPIDeviceMqtt):
    def __init__(self,DeviceConfiguration):
        RPIDeviceMqtt.__init__(self, DeviceConfiguration)
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        if ("gpio" in self.data):
            self.GPIO = int(self.data['gpio'])
        else:
            print("gpio parameter missing in configuration file!")
            exit(0)
        GPIO.setup(self.GPIO, GPIO.OUT)
        print("Setup GPIO device on pin " + str(self.GPIO))
        self.currentValue = 0
        if (self.data["backup-status"] == 1 ):
            self.loadGPIOstatus()

    def __del__(self):
        try :
            if ("gpio" in self.data):
                GPIO.cleanup() 
                #GPIO.setup(self.data['gpio'],GPIO.IN)
        except KeyError:
            pass

    def update_status(self):
        print("Publish update status on " + self.statustopic + " " + str(self.gpiostatus[self.currentValue]))
        self.mqtt_client.publish(self.statustopic,str(self.gpiostatus[self.currentValue]))

    def on_message(self,client, userdata, message):
        msg = str(message.payload.decode("utf-8"))
        print("Received message '" + msg + "' on topic '"  + message.topic + "' with QoS " + str(message.qos))
        if (message.topic == self.commandtopic):
            if (msg in self.data["gpio-cmd-map"]):
                command = self.data["gpio-cmd-map"][msg]
                print("Set GPIO pin " + str(self.GPIO) + " to " + str(command))
                GPIO.output(self.GPIO,command)
                self.currentValue = command
                print("Publish update status on " + self.statustopic + " " + str(self.gpiostatus[self.currentValue]))
                self.mqtt_client.publish(self.statustopic,str(self.gpiostatus[self.currentValue]))

    def loadGPIOstatus(self):
        backupFile = Path(self.data["backup-path"] + "/" + self.data["backup-name"])
        if backupFile.is_file():
            f = open(self.data["backup-path"] + "/" + self.data["backup-name"], "r")
            try:
                pinValue = f.read(1)
                self.currentValue = pinValue
                f.close()
                if len(pinValue) == 1:
                    print("Old status was %d", int(pinValue))
                    self._writegpio(int(pinValue))
            except IOError as e:
                print("Errore (%s): %s" % (e.errno, e.strerror))

    def saveGPIOstatus(self,status):
        backuppath = Path(self.data["backup-path"])
        backuppath.mkdir(mode=0o777,parents=True, exist_ok=True)
        try:
            f = open(self.data["backup-path"] + "/" + self.data["backup-name"],"w+")
            f.write(str(status))
            f.close()
        except IOError as e:
            print("Errore (%s): %s" % (e.errno, e.strerror))

    def _writegpio(self,value):
        print(type(self.GPIO))
        print(type(value))
        print("Set GPIO pin " + str(self.GPIO) + " to " + str(value))
        GPIO.output(self.GPIO,int(value))
        self.currentValue = int(value)
        self.update_status()

    def readGPIO(self):
        return GPIO.input(self.GPIO)

class RPIRollerShutter(RPIDeviceMqtt):
   def __init__(self, DeviceConfiguration):
      RPIDeviceMqtt.__init__(self, DeviceConfiguration)
      GPIO.setmode(GPIO.BCM)
      GPIO.setwarnings(False)
      self._position = self.loadGPIOstatus()
      self.GPIO = int(self.data['gpio'])
      self.GPIO_UP_DOWN = int(self.data['gpio_up_down'])
      GPIO.setup(self.GPIO, GPIO.OUT)
      GPIO.setup(self.GPIO_UP_DOWN, GPIO.OUT)
      # (self.data["set-position-topic"] != None ):
      self.positionsettopic = self.data["mqtt-topic-base"] + self.data["device-unique-id"] + "/" + self.data["set-position-topic"]

   def __del__(self):
      GPIO.cleanup()

   def on_message(self,client, userdata, message):
      msg = str(message.payload.decode("utf-8"))
      print("Received message '" + msg + "' on topic '"  + message.topic + "' with QoS " + str(message.qos))
      print((message.topic == self.statustopic) and (self.data["status-payload"] == msg))
      if ((message.topic == self.statustopic)):
         print("Received status message")
         self.mqtt_client.publish(self.statustopic,str(self._position))
      else:
         if (self.data["gpio-cmd-map"][msg] != None):
             self.writeGPIO(int(self.data["gpio-cmd-map"][msg]))
         if (self.data["gpio-stop-cmd"] == msg):
             self.writeStopGPIO()
         if ((message.topic == self.positionsettopic)):
             if (int(msg) >= self.data['position_min'] and int(msg) <= self.data['position_max']):
                self.movetoposition(int(msg))

   def on_connect(self,client, userdata, flags, rc):
      super().on_connect(client, userdata, flags, rc)
#      print("Connected with result code "+str(rc))
#      self.subscribe_result = client.subscribe(self.topic)
#      print("Subscribing to %s => %d %d" % (self.topic, self.subscribe_result[0], self.subscribe_result[1]))
#      self.subscribe_result = client.subscribe(self.statustopic)
#      print("Subscribing to %s => %d %d" % (self.statustopic, self.subscribe_result[0], self.subscribe_result[1]))
      self.subscribe_result = client.subscribe(self.positionsettopic)
      print("Subscribing to %s => %d %d" % (self.positionsettopic, self.subscribe_result[0], self.subscribe_result[1]))


   def loadGPIOstatus(self):
     backupFile = Path(self.data["backup-path"] + "/" + self.data["backup-name"])
     if backupFile.is_file():
        f = open(self.data["backup-path"] + "/" + self.data["backup-name"], "r")
        try:
          position = f.read(10)
          f.close()
          print("Old status was " + position)
          return int(position)
        except IOError as e:
          print("Errore (%s): %s" % (e.errno, e.strerror))
     else:
        return 0

   def movetoposition(self,newpos):
      if (newpos != self._position):
         if (newpos > self._position):
            GPIO.output(self.GPIO_UP_DOWN,value)
            GPIO.output(self.GPIO,0)
            time.sleep((newpos - self._position) * 2)
            GPIO.output(self.GPIO,1)
         else:
            GPIO.output(self.GPIO_UP_DOWN,value)
            GPIO.output(self.GPIO,0)
            time.sleep((self._position - newpos ) * 2)
            GPIO.output(self.GPIO,1)


   def saveGPIOstatus(self,status):
      backuppath = Path(self.data["backup-path"])
      backuppath.mkdir(mode=0o777,parents=True, exist_ok=True)
      try:
         f = open(self.data["backup-path"] + "/" + self.data["backup-name"],"w+")
         f.write(str(status))
         f.close()
      except IOError as e:
          print("Errore (%s): %s" % (e.errno, e.strerror))

   def writeStopGPIO(self):
      GPIO.output(self.GPIO,1)

   def writeGPIO(self,value):
      print(value)
      print(self.GPIO)
      print(str(self._position) + " " + str(self.data['position_min']) + " " + str(self.data['position_max']))
      if (value == 1):
#and self._position > int(self.data['position_min']) ):
         print('Abbasso serranda')
         GPIO.output(self.GPIO_UP_DOWN,value)
         GPIO.output(self.GPIO,0)
         time.sleep(2)
         GPIO.output(self.GPIO,1)
         self._position -= 1
      if (value == 0):
# and self._position < int(self.data['position_max']) ):
         print('Alzo serranda')
         GPIO.output(self.GPIO_UP_DOWN,value)
         GPIO.output(self.GPIO,0)
         time.sleep(2)
         GPIO.output(self.GPIO,1)
         self._position += 1
         print(self._position)
      self.saveGPIOstatus(self._position)


   def readGPIO(self):
      return GPIO.input(self.GPIO)
 


class RPIDoorSensor(RPIDeviceMqtt):
   def __init__(self, DeviceConfiguration):
      RPIDeviceMqtt.__init__(self, DeviceConfiguration)
      self.GPIO = self.data["gpio"]
      print("Door sensor on gpio " + str(self.GPIO))
      if (self.data["sensor-polling"] == None):
         print("Missing sensor-polling parameter in configuration file")
         exit(1)
      GPIO.setmode(GPIO.BCM)
      GPIO.setup(self.GPIO, GPIO.IN,GPIO.PUD_UP)
      GPIO.setwarnings(False)

   def __del__(self):
      GPIO.cleanup()

   def on_connect(self,client, userdata, flags, rc):
      super().on_connect(client, userdata, flags, rc)
      t = threading.Thread(target=self.reading_thread_loop, args=())
      t.start()

   def reading_thread_loop(self):
     print("Starting polling thread on " + str(self.statustopic)  + " " + str(self.data["sensor-polling"]))
     oldStatus = None
     while True:
          status =  GPIO.input(self.GPIO)
          if (oldStatus != status ):
             if (status == 1):
                 print(self.statustopic + " Open")
                 self.mqtt_client.publish(self.statustopic,str(self.data['open-value']))
             else:
                 print(self.statustopic + " Close")
                 self.mqtt_client.publish(self.statustopic,str(self.data['close-value']))
             oldStatus = status
          time.sleep(self.data["sensor-polling"])


class RPISensorDeviceHumidity(RPIDeviceMqtt):
   def __init__(self, DeviceConfiguration):
      RPIDeviceMqtt.__init__(self, DeviceConfiguration)
      if (self.data["sensor-polling"] == None):
         print("Missing sensor-polling parameter in configuration file")
         exit(1)
      if (self.data["sensor-model"] == None):
         print("Missing sensor-model parameter in configuration file")
         exit(1)
      self.sensor_model = self.data["sensor-model"]
      self.polling_time = self.data["sensor-polling"]
      self.GPIO = self.data["gpio"]
      self.status = 0
      self.temperature = 0
      self.humidity = 0
 
   def on_connect(self,client, userdata, flags, rc):
      print("Connected with result code "+str(rc))
      t = threading.Thread(target=self.reading_thread_loop, args=())
      t.start()

   def reading_thread_loop(self):
     oldTemperature  = 0
     oldHumidity = 0
     while True:
       print("read from sensor %d on GPIO %d" % (self.sensor_model, self.GPIO))
       Rhumidity, Rtemperature = Adafruit_DHT.read_retry(self.sensor_model, self.GPIO, retries = 1)
       if (Rhumidity != None and Rtemperature != None):
          self.temperature = int(Rtemperature)
          self.humidity = int(Rhumidity)
       if (oldTemperature != self.temperature ):
             self.mqtt_client.publish(self.data["mqtt-topic-base"] + self.data["device-temperature-id"],str(self.temperature))
             oldTemperature = self.temperature

       if (oldHumidity != self.humidity ):
             self.mqtt_client.publish(self.data["mqtt-topic-base"] + self.data["device-humidity-id"],str(self.humidity))
             oldHumidity = self.humidity

       print(self.temperature, self.humidity)
       print(self.data["mqtt-topic-base"] + self.data["device-temperature-id"])
       print(self.data["mqtt-topic-base"] + self.data["device-humidity-id"])
       time.sleep(self.data["sensor-polling"]) 




class RPIRaspberryDevice(RPIDeviceMqtt):
   def __init__(self, DeviceConfiguration):
      RPIDeviceMqtt.__init__(self, DeviceConfiguration)
      if (self.data["sensor-polling"] == None):
         print("Missing sensor-polling parameter in configuration file")
         exit(1)
      self.polling_time = self.data["sensor-polling"]

   def on_connect(self,client, userdata, flags, rc):
      print("Connected with result code "+str(rc))
      t = threading.Thread(target=self.reading_thread_loop, args=())
      t.start()


   def reading_thread_loop(self):
      print("reading")
      oldExtValue = ""
      while True:
         for i in range(len(self.data['sensor-list'])):
             ps = subprocess.Popen(self.data['sensor-list'][i]['command'],shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
             output = ps.communicate()[0].decode().strip()
             if (oldExtValue != output ):
                self.mqtt_client.publish(self.data["mqtt-topic-base"] + self.data["device-unique-id"] + "/" + self.data['sensor-list'][i]['topic'],str(output))
                oldExtValue = output
                print(output)
         time.sleep(self.data["sensor-polling"])
 


#Device family implemented
# switch - relay board
# humidity - D11, D22 , Adafruit sensor
# rp3b+ - raspberry infos
# door  - door sensor
# pc - windows running pc

deviceFamilyClassMapping = {
  "switch" : RPIGPIODevice,
  "humidity" : RPISensorDeviceHumidity,
  "rp3b+"    : RPIRaspberryDevice,
  "door"     : RPIDoorSensor,
  "roller"   : RPIRollerShutter,
  "pc"       : RPIWindowsPersonalComputer}



def starter(configFile):
    """thread worker function"""
    configuration = RPIDeviceConfiguration(configFile)
    if (configuration.getData("device-family") != None): 
       if (deviceFamilyClassMapping[configuration.getData("device-family")] != None):
           aaaa = deviceFamilyClassMapping[configuration.getData("device-family")](configuration)
           aaaa.connect()
           print ('Worker: %s' % configFile)
    else:
       print("Missing device-family option in configuration file, valid values are : ")
       print(deviceFamilyClassMapping.keys())
    return



def get_methods(object, spacing=20): 
  methodList = [] 
  for method_name in dir(object): 
    try: 
        if callable(getattr(object, method_name)): 
            methodList.append(str(method_name)) 
    except: 
        methodList.append(str(method_name)) 
  processFunc = (lambda s: ' '.join(s.split())) or (lambda s: s) 
  for method in methodList: 
    try: 
        print(str(method.ljust(spacing)) + ' ' + 
              processFunc(str(getattr(object, method).__doc__)[0:90])) 
    except: 
        print(method.ljust(spacing) + ' ' + ' getattr() failed') 

#aaaa = RPIGPIODevice("domo01.conf")
#aaaa.connect()

#exit(0)

def getKeysByValue(dictOfElements, valueToFind):
    listOfKeys = list()
    listOfItems = dictOfElements.items()
    for item  in listOfItems:
        if item[1] == valueToFind:
            listOfKeys.append(item[0])
    return  listOfKeys


parser = argparse.ArgumentParser()
parser.add_argument('--conf', nargs='+')
parser.add_argument('--listfile', nargs='+')
startup=False

for param, value in parser.parse_args()._get_kwargs():
    if  (param.upper() == "CONF" and value != None):
        configs=value
        startup=True
    if  (param.upper() == "LISTFILE" and value != None):
        startup=True
        try:
           with open(str(value[0])) as json_file:
              configs = json.load(json_file)['files']
        except ValueError as e:
           print('Your settings file(s) contain invalid JSON syntax! Please fix and restart!, {}'.format(str(e)))
           sys.exit(0)


if  (startup==False):
    parser.print_help()
    sys.exit(0)


print(configs)

threads = []
for i in range(len(configs)):
    t = threading.Thread(target=starter, args=(configs[i],))
    threads.append(t)
    t.start()
