#!/usr/bin/python3
import paho.mqtt.client as mqtt
import json
import RPi.GPIO as GPIO
import threading
import time
import Adafruit_DHT
from pathlib import Path

class RPIDevice:
   GPIO_OUTPUT  = 1
   GPIO_INPUT   = 0

   def __init__(self,configurationFile):
      print("Opening %s configuration file..." % configurationFile)
      with open(str(configurationFile)) as json_file:
          self.data = json.load(json_file)
      self.deviceId = self.data["sensor-id"]
      print("Device %s created" % self.deviceId)
      self.mqtt_client = mqtt.Client(self.data["sensor-id"])
      self.mqtt_client.user_data_set(self.data)
      self.mqtt_client.on_connect = self.on_connect
      self.mqtt_client.on_message = self.on_message
      self.mqtt_client.on_publish = self.on_publish
      self.mqtt_client.on_subscribe = self.on_subscribe
      self.sensor_model = self.data["sensor-model"]
      self.GPIO = self.data["gpio"]
      self.polling_time = self.data["sensor-polling"]
      self.humidity = 0
      self.temperature = 0
      self.last_read = 0

   def connect(self):
      self.mqtt_client.connect(self.data["mqtt-server"],self.data["mqtt-port"])
      self.mqtt_client.loop_forever()

   def readData(self):
      if ((self.last_read + self.polling_time) < int(time.time())):
          print("read from sensor %d on GPIO %d" % (self.sensor_model, self.GPIO))
          Rhumidity, Rtemperature = Adafruit_DHT.read_retry(self.sensor_model, self.GPIO, retries = 1)
          if (Rhumidity != None and Rtemperature != None):
              self.temperature = int(Rtemperature)
              self.humidity = int(Rhumidity)

   def on_connect(self,client, userdata, flags, rc):
      print("Connected with result code "+str(rc))
      t = threading.Thread(target=self.sender, args=())
      threads.append(t)
      t.start()


   def on_message(self,client, userdata, message):
      msg = str(message.payload.decode("utf-8"))
      print("Received message '" + msg + "' on topic '"  + message.topic + "' with QoS " + str(message.qos))
  
   def on_publish(client,userdata,result):             #create function for callback
      print("data published \n")  


   def on_subscribe(self,client,userdata,mid,granted_qos):
     print("%s" % str(mid))


   def sender(self):
     oldTemperature  = 0
     oldHumidity = 0
     while True:
         
         self.readData()
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


def worker(configFile):
    """thread worker function"""
    aaaa = RPIDevice(configFile)
    aaaa.connect()
    print ('Worker: %s' % configFile)
    return

threads = []
configs = [ "sensor01.conf"]
for i in range(len(configs)):
    t = threading.Thread(target=worker, args=(configs[i],))
    threads.append(t)
    t.start()
