#!/usr/bin/env python

# pulse.py

import time

import pigpio

pi = pigpio.pi() # Connect to local Pi.

# set gpio modes

g = 13
pi.set_mode(g, pigpio.OUTPUT)


# start 1500 us servo pulses on gpio4

#pi.set_servo_pulsewidth(4, 1500)

# start 75% dutycycle PWM on gpio17
for i in range(20):
   pi.set_PWM_dutycycle(g, i * 12) # 192/255 = 75%
   time.sleep(0.05)


time.sleep(4)
# mirror gpio24 from gpio23
pi.set_PWM_dutycycle(g, 0) # stop PWM

pi.stop() # terminate connection and release resources
