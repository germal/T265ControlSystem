# T265ControlSystem
This is the main control system used to fly the copter from the position reported by the T265 camera.

Written by Mitchell Cooke (cookem4@mcmaster.ca)

## How to Run
In order to run the project one must first run the camera recording app from the repository T265LiveCamData. This file interfaces with the RealSense SDK and writes the camera data to a single line CSV file. The T265ControlSystem project then reads from this single line CSV file to get the camera's current position and orientation. The reason that position and orientation is recieved in the python project through a CSV file is because the RealSense SDK is only available for C/C++ and the python wrapper does not work on ARM based architecture. In summary, the C program T265LiveCamData reads the position and orientation data from the camera and writes it to a single line CSV file. The python program T265ControlSystem then reads this single line CSV file in order to fly the copter.
 
## Technical Details
The control system of this program is written by Keyvan (current PhD candidate) and Mohammad (graduated). Modifications of filtering have been made to allow the camera to report a smoother position and velocity with less noise while minimizing phase delay below 10ms. The matlab code for analysing and designing filters is in the GitHub repository named ____________. There are also several matlab programs for analysing the position reported by the T265 camera, which are contained in the repository named T255MatlabAnalysis. Each of these scripts explain their purpose in the code and some sample data has been included so that the programs can be tested. These matlab scripts can be helpful for understanding the accuracy and capabilities of the camera.

Currently, the position filter uses an order of 5 in order to minimize the phase lag below 10ms and the velocity filter uses an order of 1 (no filtering). Thresholding is done as it is common for there to be large spikes in velocity. 

Several html files are generated after the program is run that display flight information. 

## Current Troubles
When flown with this program, the drone is very jumpy in the Z direction and can be oscillatory in the XY plane. Force mapping in the Z direction has been experimented with and has been unsuccessful due to the drone not taking off. 

It is believed that the instability of the drone is due to the inaccuracies associated with the T265 camera. Camera position reporting can vary by about a centimetre even when the drone is stationary. With vibrations from the motors also causing drift with time, this can cause oscillations in the control system. It was observed that about 15cm of drift was created from a 30 second flight.

Another problem is delay with the stop button. It is not understood why, but the motors only stop about a second after the stop button is pressed, which is dangerous and can easily damage the drone. Perhps there is some form of delay with the serial ports on the Raspberryh Pi, however, there is no delay with the T265 camera as when it is moved the postion updates on screen instantly.

It was attempted to see if the instability of flight is due to the Raspberry Pi itself by trying to send Motiv motion capture data of position and orientation serially to the Pi. This requires a USB 3.0 M to M connection, which I was not able to use to successfully use to communicate between the computer running Motiv and the Pi.

## Future Suggestions
The first step with future work is to see if there is a way to successfully implement force mapping in the Z direction. Another way to improve stability of the copter may be through sensor fusion, possibly with GPS if the drone is used outdoors.
 
