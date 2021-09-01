#!/usr/bin/env python3
#############################################################################
# Filename    : hourglassgyro.py
# Description :	Module to read the gyro sensor for the hourglass application
# Author      : Trevor Fillary
# modification: 29-08-2021
########################################################################

import smbus			#import SMBus module of I2C

# Import application modules
import my_globals as g

# Definitions for gyro
#some MPU6050 Registers and their Address
PWR_MGMT_1   = 0x6B
SMPLRT_DIV   = 0x19
CONFIG       = 0x1A
GYRO_CONFIG  = 0x1B
INT_ENABLE   = 0x38
ACCEL_XOUT_H = 0x3B
ACCEL_YOUT_H = 0x3D
ACCEL_ZOUT_H = 0x3F
GYRO_XOUT_H  = 0x43
GYRO_YOUT_H  = 0x45
GYRO_ZOUT_H  = 0x47

# Create / init gyro object
bus = 0
Device_Address = 0

def gyro_init():
    global bus, Device_Address
    # Setup gyro object for module functions
    bus = smbus.SMBus(1) 	# or bus = smbus.SMBus(0) for older version boards
    Device_Address = 0x68   # MPU6050 device address
    MPU_Init()

def MPU_Init():
    #write to sample rate register
    bus.write_byte_data(Device_Address, SMPLRT_DIV, 7)

    #Write to power management register
    bus.write_byte_data(Device_Address, PWR_MGMT_1, 1)

    #Write to Configuration register
    bus.write_byte_data(Device_Address, CONFIG, 0)

    #Write to Gyro configuration register
    bus.write_byte_data(Device_Address, GYRO_CONFIG, 24)

    #Write to interrupt enable register
    bus.write_byte_data(Device_Address, INT_ENABLE, 1)


def read_raw_data(addr):
    # Accelero and Gyro value are 16-bit
    high = bus.read_byte_data(Device_Address, addr)
    low = bus.read_byte_data(Device_Address, addr+1)
    
    #concatenate higher and lower value
    value = ((high << 8) | low)
    
    #to get signed value from mpu6050
    if(value > 32768):
        value = value - 65536
    return value

# Useful general routine NOT used in this application
def read_gyro_data():
    #Read Accelerometer raw value
    acc_x = read_raw_data(ACCEL_XOUT_H)
    acc_y = read_raw_data(ACCEL_YOUT_H)
    acc_z = read_raw_data(ACCEL_ZOUT_H)

    #Read Gyroscope raw value
    gyro_x = read_raw_data(GYRO_XOUT_H)
    gyro_y = read_raw_data(GYRO_YOUT_H)
    gyro_z = read_raw_data(GYRO_ZOUT_H)

    #Full scale range +/- 250 degree/C as per sensitivity scale factor
    Ax = acc_x/16384.0
    Ay = acc_y/16384.0
    Az = acc_z/16384.0

    Gx = gyro_x/131.0
    Gy = gyro_y/131.0
    Gz = gyro_z/131.0

    print ("Gx=%.2f" %Gx, u'\u00b0'+ "/s", "\tGy=%.2f" %Gy, u'\u00b0'+ "/s", "\tGz=%.2f" %Gz, u'\u00b0'+ "/s", "\tAx=%.2f g" %Ax, "\tAy=%.2f g" %Ay, "\tAz=%.2f g" %Az) 	

def read_gyro_xy():
    # Cut down routine to just read the x and y accelerometer values used.  
    # Ax and Ay are used to determine the orientation of the hourglass, either Upright/Upside down/Left down/Right down
    # Return gravity direction and whether there is a tilt in progress
    
    # Read Accelerometer raw value
    acc_x = read_raw_data(ACCEL_XOUT_H)
    acc_y = read_raw_data(ACCEL_YOUT_H)

    Ay = acc_x/16384.0      # x & y swaped due to sensor orientationin the Pi Zero case
    Ax = acc_y/16384.0

    # Ax and Ay are used to determine the orientation of the hourglass, either Upright/Upside down/Left down/Right down

    Tiltleft = False
    Tiltright = False

    # Used to establish gravity direction
    Direction = g.FLAT  # default - ie gravity has no effect on the grains

    if Ay > 0.7:
        Direction = g.UPSIDE_DOWN
        # Set tilt limits
        if Ax >0.15 and Ax <0.75:
            # Upside down bottom right 
            Tiltright = True

        if Ax <-0.15 and Ax >-0.75:
            # Upside down bottom left 
            Tiltleft = True

    elif Ay < -0.7:
        Direction = g.RIGHTWAY_UP
        # Set tilt limits
        if Ax >0.15 and Ax <0.75:
            # Upright bottom left 
            Tiltleft = True

        if Ax <-0.15 and Ax >-0.75:
            # Upright bottom right 
            Tiltright = True

    elif Ax > 0.7:
        Direction = g.GRAVITY_LEFT
        # Set tilt limits
        if Ay >0.15 and Ay <0.75:
            # Left bottom left 
            Tiltleft = True
        
        if Ay <-0.15 and Ay >-0.75:
            # Left bottom right
            Tiltright = True

    elif Ax < -0.7:
        Direction = g.GRAVITY_RIGHT
        # Set tilt limits
        if Ay >0.15 and Ay <0.75:
            # Right bottom left 
            Tiltright = True
        
        if Ay <-0.15 and Ay >-0.75:
            # Right bottom right
            Tiltleft = True

    #print(Ax,Ay)
    #print(Direction, Tiltleft, Tiltright)

    return Direction, Tiltleft, Tiltright