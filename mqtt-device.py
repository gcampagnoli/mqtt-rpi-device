#!/usr/bin/python3
import paho.mqtt.client as mqtt
import json
import RPi.GPIO as GPIO
import threading
from pathlib import Path

class RPIDevice:
   GPIO_OUTPUT  = 1
   GPIO_INPUT   = 0

   def __init__(self,configurationFile):
      print("Opening %s configuration file..." % configurationFile)
      with open(str(configurationFile)) as json_file:
          self.data = json.load(json_file)
      self.deviceId = self.data["device-unique-id"]
      self.GPIO = 0 
      GPIO.setmode(GPIO.BCM)
      GPIO.setwarnings(False)
      self.setGPIOUsed(self.data['gpio'], self.GPIO_OUTPUT)
      backupFile = Path(self.data["device-unique-id"])
      if backupFile.is_file():
          f = open(self.data["device-unique-id"], "r")
          try:
             pinValue = f.read(1)
             f.close()
             if len(pinValue) == 1: 
                print("Old status was %d", int(pinValue))
                self.sendCommand(int(pinValue))
          except IOError as e:
             print("Errore (%s): %s" % (e.errno, e.strerror))
      print("Device %s created" % self.deviceId)
      self.mqtt_client = mqtt.Client(self.data["device-unique-id"])
      self.mqtt_client.user_data_set(self.data)
      self.mqtt_client.on_connect = self.on_connect
      self.mqtt_client.on_message = self.on_message
      self.mqtt_client.on_subscribe = self.on_subscribe

   def connect(self):
      self.mqtt_client.connect(self.data["mqtt-server"],self.data["mqtt-port"])
      self.mqtt_client.loop_forever()

   def setGPIOUsed(self,gpioBCM,IO):
      if (IO == self.GPIO_OUTPUT):
         GPIO.setup(gpioBCM,GPIO.OUT)
      else:
         GPIO.setup(gpioBCM,GPIO.IN)
      print("Controlling on GPIO %d" %  gpioBCM)
      self.GPIO = gpioBCM

   def sendCommand(self,cmd):
      print("setting %d => %d" % (self.GPIO, int(cmd)))
      self.GPIOOUT(self.GPIO,cmd)
      f = open(self.data["device-unique-id"],"w+")
      f.write(str(cmd))
      f.close()
  
   def readStatus(self):
      return self.GPIOIN(self.GPIO)

   @staticmethod
   def GPIOOUT(gpio, cmd):
      GPIO.output(gpio,cmd)

   @staticmethod
   def GPIOIN(gpio):
      return GPIO.input(gpio)


   def on_connect(self,client, userdata, flags, rc):
      print("Connected with result code "+str(rc))
      r = client.subscribe(userdata["mqtt-topic-base"] + userdata["device-unique-id"])
      topic = (userdata["mqtt-topic-base"] + userdata["device-unique-id"])
      print("Subscribe to %s results %s" % (topic, str(r)))

   def on_message(self,client, userdata, message):
      msg = str(message.payload.decode("utf-8"))
      print("Received message '" + msg + "' on topic '"  + message.topic + "' with QoS " + str(message.qos))
      if (msg == "1" or msg == "0"):
         self.sendCommand(int(msg))


   def on_subscribe(self,client,userdata,mid,granted_qos):
     print("%s" % str(mid))



def worker(configFile):
    """thread worker function"""
    aaaa = RPIDevice(configFile)
    aaaa.connect()
    print ('Worker: %s' % configFile)
    return

threads = []
configs = [ "domo01.conf","domo02.conf","domo03.conf","domo04.conf"]
for i in range(4):
    t = threading.Thread(target=worker, args=(configs[i],))
    threads.append(t)
    t.start()
