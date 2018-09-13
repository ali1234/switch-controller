#https://python-evdev.readthedocs.io/en/latest/tutorial.html
#https://stackoverflow.com/questions/44934309/how-to-access-the-joysticks-of-a-gamepad-using-python-evdev

#import time
from evdev import InputDevice, categorize, ecodes
import serial

dev = InputDevice('/dev/input/event8')

ser = serial.Serial('/dev/ttyACM0', 250000)

def send(msg):
    ser.write('%s\r\n'.encode('utf-8') % msg);

command = [0]*15
dpad = [0]*4
command[0] = 8 #HAT_CENTER
lx = 128
ly = 128
rx = 128
ry = 128

print(dev)
#print(dev.capabilities(True))

previousCommand = "800000000000000 126 126 126 126"

#start = time.time()
for event in dev.read_loop():
    if event.type == ecodes.EV_KEY:
        if (event.code == ecodes.BTN_DPAD_UP):
            dpad[0] = int(event.value)
        elif (event.code == ecodes.BTN_DPAD_RIGHT):
            dpad[1] = int(event.value)
        elif (event.code == ecodes.BTN_DPAD_DOWN):
            dpad[2] = int(event.value)
        elif (event.code == ecodes.BTN_DPAD_LEFT):
            dpad[3] = int(event.value)
        elif (event.code == ecodes.BTN_THUMBL):
            command[1] = int(event.value)
        elif (event.code == ecodes.BTN_TL):
            command[2] = int(event.value)
        elif (event.code == ecodes.BTN_TL2):
            command[3] = int(event.value)
        elif (event.code == ecodes.BTN_SELECT):
            command[4] = int(event.value)
        #elif (event.code == ecodes.BTN_SELECT): # No Capture Button Control
        #command[5] = int(event.value)
        elif (event.code == ecodes.BTN_EAST):
            command[6] = int(event.value)
        elif (event.code == ecodes.BTN_SOUTH):
            command[7] = int(event.value)
        elif (event.code == ecodes.BTN_NORTH):
            command[8] = int(event.value)
        elif (event.code == ecodes.BTN_WEST):
            command[9] = int(event.value)
        elif (event.code == ecodes.BTN_THUMBL):
            command[10] = int(event.value)
        elif (event.code == ecodes.BTN_TR):
            command[11] = int(event.value)
        elif (event.code == ecodes.BTN_TR2):
            command[12] = int(event.value)
        elif (event.code == ecodes.BTN_START):
            command[13] = int(event.value)
        elif (event.code == ecodes.BTN_MODE):
            command[14] = int(event.value)
        if (dpad == [1,0,0,0]):
            command[0] = 0
        elif (dpad == [1,1,0,0]):
            command[0] = 1
        elif (dpad == [0,1,0,0]):
            command[0] = 2
        elif (dpad == [0,1,1,0]):
            command[0] = 3
        elif (dpad == [0,0,1,0]):
            command[0] = 4
        elif (dpad == [0,0,1,1]):
            command[0] = 5
        elif (dpad == [0,0,0,1]):
            command[0] = 6
        elif (dpad == [1,0,0,1]):
            command[0] = 7
        elif (dpad == [0,0,0,0]):
            command[0] = 8
    elif event.type == ecodes.EV_ABS:
        if (event.code == ecodes.ABS_X):
            lx = int(event.value)
        elif (event.code == ecodes.ABS_Y):
            ly = int(event.value)
        elif (event.code == ecodes.ABS_RX):
            rx = int(event.value)
        elif (event.code == ecodes.ABS_RY):
            ry = int(event.value)
    stringCommand = ''.join(str(x) for x in command) + " " + str(lx) + " " + str(ly) + " " + str(rx) + " " + str(ry)
#now = time.time()

#if((now - start)*1000 > 1):
#   start = now
#print stringCommand
    if (previousCommand != stringCommand): # Only send updates
        send(stringCommand)
        previousCommand =stringCommand
