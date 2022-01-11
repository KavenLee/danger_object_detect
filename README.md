

## Auto Recharging Project using Robot Arm

=================================================================



#### Description

- I was in charge of detecting dangerous substances in the electric vehicle automatic charging project using a robot arm. My task is to detect if there are any dangerous substances within the range of motion of the robot arm, transmit the result value to the internal network using Modbus TCP, and display the Json file on the web server combining PHP&NginX using Docker-Compose for the detected.

  

- For object detection, Yolov3 was used, and Modbus TCP used pymodbus, a Python library.

- After that, the completed program was registered as a service of ubuntu and started automatically when rebooting and system startup.

- This project was created and used on Ubuntu on Jetson Xavier Tx2. 



#### Requirements

- Docker == 5.0.0
- Docker-Compose == 1.29.2
- Opencv >= 4.2
- numpy >= 1.17
- pymodbus == 2.5.2


#### Weights file
https://github.com/KavenLee/danger_object_detect/releases/tag/yolomodel
- Move the downloaded file to the path in "python/".




#### Reference

- Yolo : 

https://github.com/AlexeyAB



- pymodbus:

https://pymodbus.readthedocs.io/en/latest/source/example/asynchronous_server.html
