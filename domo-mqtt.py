#!/usr/bin/python3
import paho.mqtt.client as mqtt
import json
import RPi.GPIO as GPIO

def rp3_whois(userdata, out):
    print("Called whois")
    mqtt_client.publish(userdata["mqtt-topic"], GPIO.input(userdata["gpio"][out]))    

def rp3_command(userdata,out,cmd):
    print("Called open " + str(userdata["gpio"][out]))
    GPIO.output(userdata["gpio"][out],cmd) 
#    mqtt_client.publish(userdata["mqtt-topic"],"OK")



def on_message(client, userdata, message):
    print("Received message '" + msg + "' on topic '"  + message.topic + "' with QoS " + str(message.qos))
    tpc = str(message.topic.decode("utf-8"))
    msg = str(message.payload.decode("utf-8"))
    channel = int(tpc[-2:])
    rp3_command(userdata,channel,int(msg))

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unexpected disconnection.")

def on_connect(client, userdata, flags, rc):
    subscriptions  = []
    print("Connected with result code "+str(rc))
    for i in range(len(data["gpio"])):
       subscriptions.append((userdata["mqtt-topic"] + "%02d" % i,i+1))
    print(subscriptions)
    client.subscribe(subscriptions)

def on_subscribe(client, userdata, mid, granted_qos):
    print("ok")

def switch(val):
   print("interruttore " + str(val))

with open('domo.conf') as json_file:  
    data = json.load(json_file)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for i in range(len(data["gpio"])):
    GPIO.setup(data["gpio"][i],GPIO.OUT)
mqtt_client = mqtt.Client(data["device-unique-id"])
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_message = on_message
mqtt_client.on_subscribe = on_subscribe
data["services"]["command"] = rp3_command
data["services"]["whois"] = rp3_whois
mqtt_client.user_data_set(data)
mqtt_client.connect(data["mqtt-server"],data["mqtt-port"])
mqtt_client.loop_forever()







