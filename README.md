# mqtt-rpi-device
Install: 

pip3 install paho-mqtt python-etcd

Python based service to expose through MQTT your Raspberry device

Use: 
.mqtt-device.py --conf [CONFIG ... CONFIG]

Example: 
./mqtt-device.py --conf raspberry/raspberry.conf

Send to a broker MQTT the following data

house/room01/raspberry00001/cpu-temperature 46

house/room01/raspberry00001/gpu-temperature 46.2

house/room01/raspberry00001/rpi-harddisk-percentage 24

house/room01/raspberry00001/cpu-usage-avg-1-min 0.14

house/room01/raspberry00001/cpu-usage-avg-5-min 0.11

house/room01/raspberry00001/cpu-usage-avg-15-min 0.05


./mqtt-device.py --conf relay_board/domo01.conf relay_board/domo02.conf


