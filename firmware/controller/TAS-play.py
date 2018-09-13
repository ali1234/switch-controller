#https://python-evdev.readthedocs.io/en/latest/tutorial.html
#https://stackoverflow.com/questions/44934309/how-to-access-the-joysticks-of-a-gamepad-using-python-evdev

import time
from evdev import InputDevice, categorize, ecodes
import serial

dev = InputDevice('/dev/input/event8')

ser = serial.Serial('/dev/ttyACM0', 250000)

file = open("commands.txt", "r")

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
recordFlag = False
playFlag = False

startPlay = time.time()
lineRead = file.readline()
lineTime = float(file.readline())

while True:
#    stringCommand = ''.join(str(x) for x in command) + " " + str(lx) + " " + str(ly) + " " + str(rx) + " " + str(ry)


    nowPlay = time.time()
    if (nowPlay-startPlay>lineTime):
        print(lineRead)
        ser.write('%s'.encode('utf-8') % lineRead);
        startPlay = nowPlay
        lineRead = file.readline().rstrip()
        lineTime = float(file.readline())
        stringCommand = lineRead
        print stringCommand
        send(stringCommand)



#if((now - start)*1000 > 1):
#   start = now
#print stringCommand
#    if (previousCommand != stringCommand): # Only send updates
#        send(stringCommand)
#        previousCommand =stringCommand
