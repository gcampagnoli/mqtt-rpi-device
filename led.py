#!/usr/bin/python3

import RPi.GPIO as GPIO   # Import the GPIO library.
import time               # Import time library

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(5,GPIO.OUT)
GPIO.setup(6,GPIO.OUT)
GPIO.setup(13,GPIO.OUT)
GPIO.setup(26,GPIO.OUT)

pwmW = GPIO.PWM(6, 100) 
pwmR = GPIO.PWM(13, 100) 
pwmG = GPIO.PWM(5, 100) 
pwmB = GPIO.PWM(26, 100) 

pwmB.stop()
pwmW.stop() 
pwmR.stop()
 

try:
  while True:                      # Loop until Ctl C is pressed to stop.
    for dc in range(0, 101, 5):    # Loop 0 to 100 stepping dc by 5 each loop
      pwmG.ChangeDutyCycle(dc)
      time.sleep(0.05)             # wait .05 seconds at current LED brightness
      print(dc)
    for dc in range(95, 0, -5):    # Loop 95 to 5 stepping dc down by 5 each loop
      pwmG.ChangeDutyCycle(dc)
      time.sleep(0.05)             # wait .05 seconds at current LED brightness
      print(dc)
except KeyboardInterrupt:
  print("Ctl C pressed - ending program")
pwmG.stop()  
