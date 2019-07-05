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
      self.topic = self.data["mqtt-topic-base"] + self.data["device-unique-id"]

   def connect(self):
      self.mqtt_client.connect(self.data["mqtt-server"],self.data["mqtt-port"])
      self.mqtt_client.loop_forever()

   def on_disconnect(self,client, userdata,rc=0):
      print("Disconnected result code "+str(rc))

   def setTopic(self, newTopic):
      self.topic = newTopic

   def on_connect(self,client, userdata, flags, rc):
      print("Connected with result code "+str(rc))
      self.subscribe_result = client.subscribe(self.topic)
      print("Subscribing to %s => %d %d" % (self.topic, self.subscribe_result[0], self.subscribe_result[1]))

   def on_message(self,client, userdata, message):
      pass

   def on_subscribe(self,client,userdata,mid,granted_qos):
     if (mid == self.subscribe_result[1]):
         print("OK")



class RPIGPIODevice(RPIDeviceMqtt):
   def __init__(self,DeviceConfiguration):
     RPIDeviceMqtt.__init__(self, DeviceConfiguration)
     self.GPIO = 0
     GPIO.setmode(GPIO.BCM)
     GPIO.setwarnings(False)
     self.setGPIOUsed(self.data['gpio'], GPIO.OUT)
     if (self.data["backup-status"] == 1 ):
        self.loadGPIOstatus()

   def __del__(self):
      try :
         if (self.data['gpio'] != None):
            GPIO.setup(self.data['gpio'],GPIO.IN)
      except KeyError:
         pass

   def on_message(self,client, userdata, message):
     msg = str(message.payload.decode("utf-8"))
     print("Received message '" + msg + "' on topic '"  + message.topic + "' with QoS " + str(message.qos))
     if (self.data["gpio-cmd-map"][msg] != None):
        self.writeGPIO(self.data["gpio-cmd-map"][msg])

   def setGPIOUsed(self,gpioBCM,IO):
      GPIO.setup(gpioBCM,IO)
      print("Controlling on GPIO %d" %  gpioBCM)
      self.GPIO = gpioBCM

   def loadGPIOstatus(self):
     backupFile = Path(self.data["backup-path"] + "/" + self.data["backup-name"])
     if backupFile.is_file():
        f = open(self.data["backup-path"] + "/" + self.data["backup-name"], "r")
        try:
          pinValue = f.read(1)
          f.close()
          if len(pinValue) == 1:
             print("Old status was %d", int(pinValue))
             self.sendCommand(int(pinValue))
        except IOError as e:
          print("Errore (%s): %s" % (e.errno, e.strerror))

   def saveGPIOstatus(self,status):
      try:
         f = open(self.data["backup-path"] + "/" + self.data["backup-name"],"w+")
         f.write(str(status))
         f.close()
      except IOError as e:
          print("Errore (%s): %s" % (e.errno, e.strerror))

   def writeGPIO(self,value):
      print(value)
      GPIO.output(self.gpio,value)

   def readGPIO(self):
      return GPIO.input(self.gpio)

class RPISensorDeviceHumidity(RPIDeviceMqtt):
   def __init__(self, DeviceConfiguration):
      RPIDeviceMqtt.__init__(self, DeviceConfiguration)
      pass

class RPIRaspberryDevice(RPIDeviceMqtt):
   def __init__(self, DeviceConfiguration):
      RPIDeviceMqtt.__init__(self, DeviceConfiguration)
      if (self.data["sensor-polling"] == None):
         print("Missing sensor-polling parameter in configuration file")
         exit(1)
      self.polling_time = self.data["sensor-polling"]
      self.ext_value = 0
      self.last_read = 0
      self.topic = ""
      self.command = "" 

   def connect(self):
      self.mqtt_client.connect(self.data["mqtt-server"],self.data["mqtt-port"])
      self.mqtt_client.loop_forever()

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


deviceFamilyClassMapping = {
  "switch" : RPIGPIODevice,
  "humidity" : RPISensorDeviceHumidity,
  "rp3b+"    : RPIRaspberryDevice}



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


#aaaa = RPIGPIODevice("domo01.conf")
#aaaa.connect()

#exit(0)

parser = argparse.ArgumentParser()
parser.add_argument('--conf', nargs='+')

for param, value in parser.parse_args()._get_kwargs():
    if  param.upper() == "CONF" and value == None:
        print("Parameter missing : conf\nUsage %s --conf [configfile]" % sys.argv[0])
        exit(1)
    else:
        configs = value


threads = []
for i in range(len(configs)):
    t = threading.Thread(target=starter, args=(configs[i],))
    threads.append(t)
    t.start()
