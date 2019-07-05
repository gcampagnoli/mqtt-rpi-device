#!/usr/bin/python3
import paho.mqtt.client as mqtt
import json
import threading
import time
from pathlib import Path
import subprocess
import random

class RPIDevice:
   GPIO_OUTPUT  = 1
   GPIO_INPUT   = 0

   def __init__(self,configurationFile):
      print("Opening %s configuration file..." % configurationFile)
      with open(str(configurationFile)) as json_file:
          self.data = json.load(json_file)
      self.deviceId = self.data["sensor-id"]
      print("Device %s created" % self.deviceId)
      self.mqtt_client = mqtt.Client(self.data["sensor-id"] + str(random.randint(1000, 9999)))
      self.mqtt_client.user_data_set(self.data)
      self.mqtt_client.on_connect = self.on_connect
      self.mqtt_client.on_message = self.on_message
      self.mqtt_client.on_publish = self.on_publish
      self.mqtt_client.on_subscribe = self.on_subscribe
      self.polling_time = self.data["sensor-polling"]
      self.ext_value = 0
      self.last_read = 0
      self.topic = ""
      self.command = ""


   def setCommand(self, topic, command):
      self.topic = self.data["mqtt-topic-base"] + self.data["sensor-id"] + "/" + topic
      self.command = command

   def connect(self):
      self.mqtt_client.connect(self.data["mqtt-server"],self.data["mqtt-port"])
      self.mqtt_client.loop_forever()

   def readData(self):
      ps = subprocess.Popen(self.command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      output = ps.communicate()[0].decode().strip()
      self.ext_value = output

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
     oldExtValue = ""
     while True:
         self.readData()
         if (oldExtValue != self.ext_value ):
             self.mqtt_client.publish(self.topic,str(self.ext_value))
             oldExtValue = self.ext_value
         print(self.ext_value)
         time.sleep(self.data["sensor-polling"])


def worker(configFile,topic,cmd):
    """thread worker function"""
    aaaa = RPIDevice(configFile)
    print(topic, cmd)
    aaaa.setCommand(topic,cmd)
    aaaa.connect()
    print ('Worker: %s' % configFile)
    return

threads = []
configs = [ "sensor01.conf"]
with open(configs[0]) as json_file:
    data = json.load(json_file)


for i in range(len(data["sensor-list"])):
    t = threading.Thread(target=worker, args=(configs[0],data["sensor-list"][i]["topic"],data["sensor-list"][i]["command"]))
    threads.append(t)
    t.start()
