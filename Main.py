from Quaternion         import Quaternion
from PB_Control         import PB_Control
from Trajectory_Planner import Trajectory_Planner
from Sensor             import Sensor
from Cleanflight_MSP    import Cleanflight_MSP
from EStop              import EStop
from threading          import Thread
from threading          import Event
from Logger             import Logger
import struct
import time
import numpy as np
import csv
from time import sleep
import numpy as np
import math
import time
import copy #For deep copies

#Replace this with a thread that takes realsense cameras and places them into the variables
def receiveRigidBodyFrame():
    i=0
    global positions, orientations, recordingTimes, originalQuart
    while True:
        try:            
            i=i+1
            with open('/home/pi/t265/coordinateData.csv') as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                line_count=0
                for row in csv_reader:
                    
                    #Must map these coordiantes to the same as the way Motiv motion capture would have mappd them
                    #Have camera positioned such that it is facing the front table
                    #Y axis are the same
                    #X axis are the same
                    #Z axis are the same
                    positions[0][0] = float(row[6]) #x
                    positions[0][1] = float(row[7]) #y
                    positions[0][2] = float(row[8]) #z

                    if(originalQuart.x == 0 and originalQuart.y == 0 and originalQuart.z ==0 and originalQuart.w == 0):
                        originalQuart = Quaternion(float(row[2]), float(row[3]), float(row[4]), float(row[5]))
                    currQuart = Quaternion(float(row[2]), float(row[3]), float(row[4]), float(row[5]))
                    #Following operation makes the current quaternion the delta between the current orintation vector and the original
                    transform = originalQuart.inverse().multiplication(currQuart)
                    orientations[0] = [transform.x, transform.y, transform.z, transform.w]
                    
                    trackingFlags[0] = True

                    
                    recordingTimes[0] = recordingTimes[1]
                    recordingTimes[1] = int(row[1]) #This gives time in microseconds
                    
                    '''
                    recordingTimes[0] = recordingTimes[1]
                    recordingTimes[1] = int(round(time.time()*1000))
                    print("Time From array: " + str(recordingTimes[1]-recordingTimes[0]))
                    '''                  


                    
                    ###############################
                    ##Possible source of error: ###
                    ###############################
                    #Period from camera measurements in this thread is 142ms. It is not actually running at 200Hz as was thought with the PI
                    #The reason for this is printing the period actually takes 140ms
                    
                #Used to sync the threads
                event.set()
        except:
            #print("Indexing Error")
            print()

'''
def rotateQuart(x, y, z, w):
    roll  = math.atan2(2*y*w + 2*x*z, 1 - 2*y*y - 2*z*z)
    pitch = math.atan2(2*x*w + 2*y*z, 1 - 2*x*x - 2*z*z)
    yaw   = math.asin(2*x*y + 2*z*w)
    #Need to modify the pitch by 30 degrees as the camera mount is angled at 30 degrees
    #30 degrees = 0.5236 rad
    pitch = pitch - 0.5236
    qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
    qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
    qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    return [qx, qy, qz, qw]
'''
def mainThread_run():
    global positions, orientations, trackingFlags, numCopters, payloadPose, recordingTimes #These are the interface variables to the optitrackThread
    global commandsToGo #This is the interface to the comThread
    global ARM, DISARM, ANGLE_MODE, NEUTRAL, ZERO_ROLL, ZERO_PITCH, ZERO_THROTTLE, ZERO_YAW_RATE
    loopCounter = 0
    expTime = 0
    start = 0
    end = 0
    timeSum = 0
    timeCt = 0
    while True:


        EStop_failsafe.updateArmingState() #Read data from Estop


        ##Normal closed-loop run in safe mode##
        #Was in the Following conditional: EStop_failsafe.armingState == ord('1')
        if(trajPlanner.ARM_FLAG == True and trajPlanner.FAILSAFE_FLAG == False and sensor.FAILSAFE_FLAG == False and EStop_failsafe.armingState == ord('1')):
            event.wait()  #Wait untill the camera measurements are updated for all the drones
            event.clear() #Clear the event for the next cycle
            if (sensor.initFlag == False):
                sensor.process(positions, orientations, trackingFlags, 9) #Add in average time difference of 9
                expInitTime = time.perf_counter()
            else: ##THIS IS THE MAIN CLOSED_LOOP
                expTime = time.perf_counter() - expInitTime #This is the experiment timer which starts at zero as soon as the experiment is properly initialized.
                #Orientations received here and sent to sensor to be processed. Orientation
                #In order to match the camera frame to the flight controller frame, for the camera:
                    #Z of camera becomes X of flight controller
                    #X of camera becomes Y of flight controller
                    #Y of camera becomes Z of flight controller
                #Re mapping coordinates
                #Camera coordinate system
                x = sensor.Position[0][0]
                y = sensor.Position[0][1]
                z = sensor.Position[0][2]
                #Transform to Flight Controller coordinate system
                sensor.Position[0][0] = copy.deepcopy(z)
                sensor.Position[0][1] = copy.deepcopy(x)
                sensor.Position[0][2] = copy.deepcopy(y)
                
                ##############################
                ####Remove this###############
                ##############################
                #Calculating recording time of the camera for a frame. - Remove this as it introduced a lot of noise to velocity
                timeDiff = recordingTimes[1] - recordingTimes[0]
                if(recordingTimes[0] == 0 or timeDiff == 0): #If on first iteration and does not have a time difference
                    timeDiff = 9 #115 Hz average recording rate of the camera
                
                sensor.process(positions, orientations, trackingFlags, timeDiff)

                #Finds the frequency of this thread
                #Runs at 22Hz due to the raspberry pi being slow
                end = int(round(time.time()*1000))
                if((end-start)<100):
                    timeSum = timeSum + (end-start)
                    timeCt = timeCt + 1
                    print("Time Average: " + str(timeSum/timeCt))
                start = int(round(time.time()*1000))
                
                
                ###################################################
                ####THIS YAW IS ACTUALLY THE PITCH OF THE CAMERA###
                ###################################################
                #Since the yaw of the drone is around the Y axis of the camera, the roll of the camera is what we need
                #Need to determine how the found yaw compares to the actual yaw
                #print((sensor.yaw[0]*180)/math.pi)
                #print((sensor.yawFiltered[0]*180)/math.pi)
                
                trajPlanner.generate(expTime, sensor.Position, sensor.Velocity)
                controller.control_allocation(expTime, sensor.yawFiltered,
                                              trajPlanner.errors, trajPlanner.phase, trajPlanner.rampUpDuration, trajPlanner.rampDownDuration)
                #Set commandsToGo
                commandsToGoTemp = []
                i=0
                commandsToGoTemp.append(controller.mappedCommands[i] + [ARM, ANGLE_MODE, NEUTRAL, NEUTRAL])
                commandsToGo = commandsToGoTemp

                #print(sensor.Position[0])
                #print(trajPlanner.desiredPose)
                
                #Log data
                '''
                print(trajPlanner.desiredPose)
                print(controller.fXYZ[i])
                print(sensor.Position[i])
                print(sensor.Velocity[i])
                print(sensor.yawFiltered[i])
                print(controller.roll[i])
                print(controller.pitch[i])
                print(controller.throttle[i])
                print(controller.yawRate[i])
                print("========================================================")
                '''
                logger.getData([('posDesiredX0', trajPlanner.desiredPose[0]), ('posDesiredY0', trajPlanner.desiredPose[1]), ('posDesiredZ0', trajPlanner.desiredPose[2])])
                logger.getData([('Fx'+str(i), controller.fXYZ[i][0]), ('Fy'+str(i), controller.fXYZ[i][1]), ('Fz'+str(i), controller.fXYZ[i][2])])
                logger.getData([('posErrX'+str(i), trajPlanner.errors[i][0]), ('posErrY'+str(i), trajPlanner.errors[i][1]), ('posErrZ'+str(i), trajPlanner.errors[i][2])])
                logger.getData([('posx'+str(i), sensor.Position[i][0]), ('posy'+str(i), sensor.Position[i][1]), ('posz'+str(i), sensor.Position[i][2])])
                logger.getData([('velx'+str(i), sensor.Velocity[i][0]), ('vely'+str(i), sensor.Velocity[i][1]), ('velz'+str(i), sensor.Velocity[i][2])])
                logger.getData([('yaw'+ str(i), sensor.yawFiltered[i])])
                logger.getData([('rollCmd'+str(i), controller.roll[i]),('pitchCmd'+str(i), controller.pitch[i]),
                                ('throttleCmd'+str(i), controller.throttle[i]), ('yawRateCmd'+str(i), controller.yawRate[i])])
                logger.getData([('mspRoll'+str(i), controller.mappedCommands[i][0]), ('mspPitch'+str(i), controller.mappedCommands[i][1]),
                             ('mspThrottle'+str(i), controller.mappedCommands[i][2]), ('mspYawRate'+str(i), controller.mappedCommands[i][3])])
                logger.getData([('trackingFlag'+str(i), trackingFlags[i])])
                logger.saveData()
                
        else:
            #Case1: Experiment completed
            #Was in the following conditional: EStop_failsafe.armingState == ord('1')
            if(trajPlanner.ARM_FLAG == False and trajPlanner.FAILSAFE_FLAG == False and sensor.FAILSAFE_FLAG == False and EStop_failsafe.armingState == ord('1')):
                print("Experiment completed successfully.")
            #Case2: Failsafe triggered
            
            else:
                if (EStop_failsafe.armingState != ord('1')):
                    print("Failsafe, root cause: stop button:" + str(EStop_failsafe.armingState))
                elif(sensor.FAILSAFE_FLAG == True):
                    print("Failsafe, root cause: camera system lost track of at least one copter")
                else:
                    print("Failsafe, root cause: large deviation from the virtual points")
            
            #Send disarm commands to all copters
            commandsToGoTemp = []
            i=0
            commandsToGoTemp.append([ZERO_ROLL, ZERO_PITCH, ZERO_THROTTLE, ZERO_YAW_RATE, DISARM, ANGLE_MODE, NEUTRAL, NEUTRAL])
            commandsToGo = commandsToGoTemp
            #Saving data to file and generating plots
            
            logger.saveDataToFile()
            #logger.generatePlots("PayLoad_Position",['posPayloadX', 'posPayloadY', 'posPayloadZ'])
            logger.generatePlots("Desired_Position_Copter0",['posDesiredX0','posDesiredY0','posDesiredZ0'])
            logger.generatePlots("Yaw_Orientations",['yaw'+str(i) for i in range (numCopters)])
            logger.generatePlots("Tracking_Flags",['trackingFlag'+str(i) for i in range (numCopters)])
            i=0
            logger.generatePlots("High-level_Force_Commands"+str(i),['Fx'+str(i),'Fy'+str(i),'Fz'+str(i)])
            logger.generatePlots("Position_Errors_Copter"+str(i),['posErrX'+str(i),'posErrY'+str(i),'posErrZ'+str(i)])
            logger.generatePlots("Position_Copter"+str(i),['posx'+str(i),'posy'+str(i),'posz'+str(i)])
            logger.generatePlots("Velocity_Copter"+str(i),['velx'+str(i),'vely'+str(i),'velz'+str(i)])
            logger.generatePlots("Reference_Commands_Copter"+str(i),['rollCmd'+str(i),'pitchCmd'+str(i),'throttleCmd'+str(i),'yawRateCmd'+str(i)])
            logger.generatePlots("MSP_Commands_Copter"+str(i),['mspRoll'+str(i),'mspPitch'+str(i),'mspThrottle'+str(i),'mspYawRate'+str(i)])
            debugLogger.generatePlots("Debug_MSP_Commands_Copter"+str(i),['dmspRoll'+str(i),'dmspPitch'+str(i),'dmspThrottle'+str(i),'dmspYawRate'+str(i)])
            
            break
        loopCounter += 1
        if (loopCounter%1000 == 0):
            print('Average loop rate is:',loopCounter/(time.perf_counter() - expInitTime),'Hz')

def comThread_run():
    global numCopters
    global ARM, DISARM, ANGLE_MODE, NEUTRAL, ZERO_ROLL, ZERO_PITCH, ZERO_THROTTLE, ZERO_YAW_RATE
    HZ = 100 #This thread runs at 100 HZ
    ## Arming procedure:
    # 1) Start sending MSP RX with all sticks in middle position (1550) and throttle stick down (1050) & DISARM #We must send a disarm
    # 2) Start sending MSP RX with all sticks in middle position (1550) and throttle stick down (1050) & ARM
    disArmCommandsToGoMSP = [ZERO_ROLL, ZERO_PITCH, ZERO_THROTTLE, ZERO_YAW_RATE, DISARM, ANGLE_MODE, NEUTRAL, NEUTRAL] # The 1600 is to enable the "Angle Mode" in clean flight.
    armCommandsToGoMSP    = [ZERO_ROLL, ZERO_PITCH, ZERO_THROTTLE, ZERO_YAW_RATE,    ARM, ANGLE_MODE, NEUTRAL, NEUTRAL]
    dataLength = len(disArmCommandsToGoMSP)
    dataBytes = 2*dataLength
    direction = '<'
    h = 'h'
    for i in range(1, 20):  #command for about a second before arming
        eval('cleanflightMSP0.sendMSP(direction, dataBytes, 200, disArmCommandsToGoMSP, direction+ str(dataLength) + h)')
        time.sleep(1/HZ)
    for i in range(1, 20):
        eval('cleanflightMSP0.sendMSP(direction, dataBytes, 200,    armCommandsToGoMSP, direction+ str(dataLength) + h)')
        time.sleep(1/HZ)
    ## Continuously sending the latest available commands to each copter
    i=0
    while True:
        debugLogger.getData([('dmspRoll'+str(i), commandsToGo[i][0]), ('dmspPitch'+str(i), commandsToGo[i][1]), ('dmspThrottle'+str(i), commandsToGo[i][2]), ('dmspYawRate'+str(i), commandsToGo[i][3])])
        debugLogger.saveData()
        eval('cleanflightMSP'+str(i)+'.sendMSP(direction, dataBytes, 200,    commandsToGo[i], direction+ str(dataLength) + h)')
        time.sleep(1/HZ)
   
############
##  MAIN  ##
############
if (__name__ == '__main__'):
    numCopters = 1
    positions = []
    recordingTimes = [0,0]
    orientations = []
    trackingFlags = []
    payloadPose = [0, 0, 0, 0, 0, 0, 0]
    ARM = 1600; DISARM = 1000; ANGLE_MODE = 1600; NEUTRAL = 1000;
    ZERO_ROLL = 1500; ZERO_PITCH = 1500; ZERO_YAW_RATE = 1500; ZERO_THROTTLE = 1000;
    zeroCommands = [ZERO_ROLL, ZERO_PITCH, ZERO_THROTTLE, ZERO_YAW_RATE, ARM, ANGLE_MODE, NEUTRAL, NEUTRAL]
    commandsToGo = [] # This is a list of lists. Each list contains the low-level commands for each copter in the order of copter IDs.
    commandsToGo.append(zeroCommands) #Roll, pitch, throttle, yaw rate, aux1, aux2, ...
    positions.append([0, 0, 0])
    orientations.append([0, 0, 0, 0])
    trackingFlags.append(False)
    initTime = 0.0
    expTime = 0.0
    originalQuart = Quaternion(0, 0, 0, 0)
    errorsZList = []
    ######## Creating instances of all required classes (creating objects) #########
    ################################################################################
    event = Event() # Event object to sync the main thread and the optitrack thread

    #To run in the mainThread
    sensor         = Sensor(numCopters)                       #Sensor object. Grabs camera measurements and estimates linear velocities.
    trajPlanner    = Trajectory_Planner()                     #Trajectory planning object. Generates time dependent trajectories or set points.
    controller     = PB_Control()                             #Passivity based controller object. Determines desired thrust, roll, and pitch of each copter.
    EStop_failsafe = EStop('/dev/ttyUSB1', 115200)                   #EStop object. When pressed, EStop disarms FC & puts in failsafe mode.
    logger         = Logger()                                 #Loggs and plots variables
    debugLogger         = Logger()                                 #Loggs and plots variables

    #To run in the comThread
    cleanflightMSP0 = Cleanflight_MSP('/dev/ttyUSB0', 115200)          #MSP object to comunicate with the head copter. Packages messages in the MSP Protocal.

    time.sleep(1)

    ######## Creating and running all the three threads #######
    ##############################################
    
    #Starts streaming RealSense data here
    thread = Thread(target=receiveRigidBodyFrame, args= ())
    thread.start()
    
    comThread = Thread(target = comThread_run)  #Thread to communicate with the copters. (Send commands only)
    comThread.start()                           #Start up thread to constantly send rx data
    print("Comunication with copters established and copters are armed. (Thread #2)")
    time.sleep(1.5)                               #Wait for 1.5 second to let the copters go through the arming procedure.

    mainThread = Thread(target = mainThread_run)#The main thread which runs sensor, trajectory planner, and controller modules.
    mainThread.start()                          #Start up thread to close the feed-back control loop
    print("Main thread initiated to start the experiment. (Thread #3)")
    

