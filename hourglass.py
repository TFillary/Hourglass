#!/usr/bin/env python3
#############################################################################
# Filename    : hourglass.py
# Description :	Application to use the Pirate Audio board with 240x240 pixel screen + 4 buttons to
#               run an hourglass using a gyro/accelerometer board to control it.
#               Inspiration from https://hackaday.io/project/165620-digital-hourglass, but developed from scratch
#               Can take any 'typical' hourglass graphic and work out where to fill it (amount of fill can be changed)
# Author      : Trevor Fillary
# modification: 20-08-2021
########################################################################

import smbus			#import SMBus module of I2C
import time
import math
import numpy as np
from pathlib import Path

from gpiozero import Button

from colorsys import hsv_to_rgb
from PIL import Image, ImageDraw, ImageFont
from ST7789 import ST7789

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

# Gravity definitions
Flat = 0
Upside_Down = 1
Rightway_up = 2
GravityLeft = 3
GravityRight =4

# Definitions for the screen
SCREEN_SIZE = 240 # 240x240 square
MAX_SCREEN_INDEX = 239 # 0 to 239
MIN_SCREEN_INDEX = 0

# Definitions for hourglass
HOURGLASS_TOP_Y = 0 # Inside hourglass
HOURGLASS_BOTTOM_Y = 0 # Inside hourglass
HOURGLASS_CENTRE_Y = 0 # Inside hourglass
HOURGLASS_CENTRE_X = 0 # Inside hourlgass
HOURGLASS_UPRIGHT = True # Assume upright initially

NO_GRAIN_ROWS = 30  # Sets number of sand rows to display
no_grains = 0 # Number of grains in array
GRAINS_X = 0 # Used to indx the x element of the grains list
GRAINS_Y = 1 # Used to index the y element of the grains list
grains = [] # Create list definition to hold each grain x,y - will grow to meet max no of grains - grains[n][GRAINS_X] or grains[n][GRAINS_Y] etc
sorted_grains = [] # List of grains in a sorted order in each row - scans from centre out for each row


# Global image variables
pixels = 0
image = 0
#image2 = 0
draw = 0

grain_image = Image.new("RGB", (1, 1), (0, 255, 0)) # green, single image
delete_grain_image = Image.new("RGB", (1, 1), (255, 255, 255)) # white, background colour, single image

# Global state variables
TIMING = 1
MENU = 2 
FINISHED = 3
CONTINUOUS = 4
TEST = 5
NULL = 99
mode = MENU  # default to menu at start


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
    Direction = Flat  # default - ie gravity has no effect on the grains

    if Ay > 0.7:
        Direction = Upside_Down
        # Set tilt limits
        if Ax >0.15 and Ax <0.75:
            # Upside down bottom right 
            Tiltright = True

        if Ax <-0.15 and Ax >-0.75:
            # Upside down bottom left 
            Tiltleft = True

    elif Ay < -0.7:
        Direction = Rightway_up
        # Set tilt limits
        if Ax >0.15 and Ax <0.75:
            # Upright bottom left 
            Tiltleft = True

        if Ax <-0.15 and Ax >-0.75:
            # Upright bottom right 
            Tiltright = True

    elif Ax > 0.7:
        Direction = GravityLeft
        # Set tilt limits
        if Ay >0.15 and Ay <0.75:
            # Left bottom left 
            Tiltleft = True
        
        if Ay <-0.15 and Ay >-0.75:
            # Left bottom right
            Tiltright = True

    elif Ax < -0.7:
        Direction = GravityRight
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

def draw_menu():
    global image, pixels, draw
    image = Image.open("hourglass.bmp") # Load initial picture
    draw = ImageDraw.Draw(image) # Setup so can draw on the screen for menu etc.
    pixels = image.load()  # Load image into memory for pixes access later - check for collisions etc.

        # Now to add some text for the buttons.....
    font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 16) # Create our font, passing in the font file and font size
    font2 = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 24) # Create our font, passing in the font file and font size

    # TODO - Fix tite size/pos
    # Rectangle for title
    #draw.rectangle((40, 18, 200, 50), outline = ("black"))
    #draw.text((50, 20), "Hourglass", font = font2, fill = ("#eba414")) # Title

    txt_colour = (0,0,0)
    draw.text((5, 60), "Timer", font = font, fill = txt_colour) # A button
    
    #TODO - DELETE??
    #draw.text((5, 180), "Generate", font = font, fill = txt_colour) # B button
    draw.text((156, 60), "Continuous", font = font, fill = txt_colour) # X button
    #draw.text((170, 180), "Easy", font = font, fill = txt_colour) # Y button

    #draw.text((190, 120), str(get_difficulty()+1), font = font2, fill = (0,255,0))
    #draw.line((195, 80, 195, 120), width=4, fill=(255, 0, 0))
    #draw.line((195, 150, 195, 180), width=4, fill=(255, 0, 0))

    #image2 = Image.open("marble_pic.png")
    #image2 = image2.resize((80,80)) 
    #image.paste(image2, (60,80)) # onto menu screen

    # draw menu
    st7789.display(image)

def analyse_hourglass_graphic():
    global pixels, HOURGLASS_TOP_Y, HOURGLASS_BOTTOM_Y, HOURGLASS_CENTRE_X, HOURGLASS_CENTRE_Y
    # Routine to analyse the hourglass graphic that may change in size or position if it is updated
    # Assumes the hourglass is broadly central within the screen, background is white and hourglass
    # outline is black

    # Find top y inside hourglass
    found = False
    # Find top of outside of hourglass (assume middle of the screen for x) - black
    for i in range(1,MAX_SCREEN_INDEX):
        if pixels[(SCREEN_SIZE/2),i] == (0,0,0):
            # Found start of outside
            HOURGLASS_TOP_Y = i
            found = True
            break
    
    if not found:
        print ("Hourgrlass graphic error")
        exit()
    
    found = False

    for i in range(HOURGLASS_TOP_Y, MAX_SCREEN_INDEX):
        if pixels[(SCREEN_SIZE/2),i] != (0,0,0):
            # Found start of inside
            HOURGLASS_TOP_Y = i
            found=True
            break

    if not found:
        print ("Hourgrlass graphic error")
        exit()
    
    # Find bottom y inside hourglass
    found = False
    # Find bottom of outside of hourglass (assume middle of the screen for x) - black
    for i in range(MAX_SCREEN_INDEX,0, -1):
        if pixels[(SCREEN_SIZE/2),i] == (0,0,0):
            # Found start of outside
            HOURGLASS_BOTTOM_Y = i
            found = True
            break
    
    if not found:
        print ("Hourgrlass graphic error")
        exit()
    
    found = False

    for i in range(HOURGLASS_BOTTOM_Y, 0, -1):
        if pixels[(SCREEN_SIZE/2),i] != (0,0,0):
            # Found start of inside
            HOURGLASS_BOTTOM_Y = i
            found=True
            break

    if not found:
        print ("Hourgrlass graphic error")
        exit()

    # Find centre y inside hourglass
    HOURGLASS_CENTRE_Y = int(HOURGLASS_TOP_Y + ((HOURGLASS_BOTTOM_Y - HOURGLASS_TOP_Y)/2))

    # Find centre x inside hourglass
    # Start by finding left most inside hourglass
    for i in range(int(SCREEN_SIZE/2), 0, -1):
        if pixels[i,HOURGLASS_TOP_Y] == (0,0,0):
            # Found start of inside
            left_x = i
            found=True
            break

    if not found:
        print ("Hourgrlass graphic error")
        exit()

    # Next find right most inside hourglass
    for i in range(int(SCREEN_SIZE/2), MAX_SCREEN_INDEX):
        if pixels[i,HOURGLASS_TOP_Y] == (0,0,0):
            # Found start of inside
            right_x = i
            found=True
            break

    if not found:
        print ("Hourgrlass graphic error")
        exit()

    # Find centre x inside hourglass
    HOURGLASS_CENTRE_X = int(left_x + ((right_x - left_x)/2))

def fill_hourglass():
    global sorted_grains
    # Routine to fill the top half of the hourglass (up to the max number of rows)

    for i in range(HOURGLASS_CENTRE_Y,(HOURGLASS_CENTRE_Y - NO_GRAIN_ROWS),-1):
        fill_row(i)

    # TODO fix these bodges - just leave a single pixel hole
    pixels[114,113] = (0,0,0) # black
    pixels[115,113] = (0,0,0) # black
    pixels[116,113] = (0,0,0) # black
    pixels[118,113] = (0,0,0) # black
    pixels[119,113] = (0,0,0) # black
    pixels[120,113] = (0,0,0) # black
    st7789.display(image)

def fill_row(row_y):
    global image, pixels, no_grains, grains
    # For selected line, add grains to fill whole line
    # Start by finding left most inside hourglass
    for i in range(HOURGLASS_CENTRE_X, 0, -1):
        if pixels[i,row_y] == (0,0,0): # black
            # Found start of inside
            left_x = i + 1
            found=True
            break

    if not found:
        print ("Hourgrlass graphic error")
        exit()

    # Next find right most inside hourglass
    for i in range(HOURGLASS_CENTRE_X, MAX_SCREEN_INDEX):
        if pixels[i,row_y] == (0,0,0): # black
            # Found start of inside
            right_x = i - 1
            found=True
            break

    if not found:
        print ("Hourgrlass graphic error")
        exit()    

    row_start = len(grains) # capture the row index of the grains array for reordering
    # Draw each grain image and add grain x,y to grains list for future processing of movement
    for i in range(left_x, right_x + 1):
        st7789.display(grain_image, i,row_y, i, row_y)
        no_grains = no_grains + 1
        #TODO - create numpy array to mirror pixels graphic & grains to speedup collision checks
        # Add new state to take account if falling or stationary
        pixels[i,row_y] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
        grains.append([i,row_y])

    row_end = len(grains) - 1
    reorder_grains(row_start, row_end)
    
def reorder_grains(row_start, row_end):
    global grains, sorted_grains
    # This section re-orders the grains list so the grains are scanned
    # either side of the centre of the hourglass towards the edges for a 
    # more even pattern draining from the centre of the hourglass
    mid_row = row_start + int((row_end - row_start)/2)
    left = mid_row -1
    right = mid_row
    for i in range(row_start, row_end):
        if right <= row_end:
            sorted_grains.append(grains[right])
            right = right + 1
        if left >= row_start:
            sorted_grains.append(grains[left])
            left = left -1

    # print(grains)
    # print(sorted_grains)


def update_grains():
    global sorted_grains
    # Cycles through the grains to move them to the next available space either one below, lower left or lower right, 
    # or when tilting to the left or right.
    # The grain movement parameters are adjusted to account for the orientation of the hourglass
    # Function runs until there are no more grains to move or runs continuously
    # Algorithm is: No tilt- try moving grain straight down first then attempt to move down at 45 deg (left or right)
    #               A tilt - try moving grain down at 45 deg first then attempt to move just left/right
    
    update_count = 1 # set to 1 to get started on main loop
    total_move_count = 0
    pass_count = 0

    # Main loop to loop until there is no more grain movement (when being used as a timer) or to run continuously
    while (mode == CONTINUOUS) or not(update_count == 0):
        
        update_count = 0 # Reset for current pass of the grains
        toggle = True # Used to toggle checking left/right first
        
        # Get gyro info 
        Direction, Tiltleft, Tiltright = read_gyro_xy() 
        
        if Direction == Rightway_up: 
            if Tiltleft:
                step_x = -1 # step x & y are to select next step down, ie 45 deg for a tilt
                step_y = 1 # +ve down
                x_left = 0 # x/y left and right are used if 'step x/y' cant find a free spot.  Values are added to step x/y!
                x_right = 0
                y_left = -1 # effectively just go left 
                y_right = 0

            elif Tiltright:
                step_x = 1 # step x & y are to select next step down, ie 45 deg for a tilt
                step_y = 1 # +ve down
                x_left = 0 # x/y left and right are used if 'step x/y' cant find a free spot.  Values are added to step x/y!
                x_right = 0 
                y_left = 0 
                y_right = -1 # effectively just go right

            else:
                # No tilt
                step_x = 0 # step x & y are to select next step down, ie straight down
                step_y = 1 # +ve down
                x_left = -1 # x/y left and right are used if 'step x/y' cant find a free spot.  Values are added to step x/y!
                x_right = 1 # Change to 45 deg
                y_left = 0 # not used when upright
                y_right = 0
        
        elif Direction == Upside_Down:
            if Tiltleft:
                step_x = 1 # step x & y are to select next step down, ie 45 deg for a tilt
                step_y = -1 # -ve down
                x_left = 0 # x/y left and right are used if 'step x/y' cant find a free spot.  Values are added to step x/y!
                x_right = 0
                y_left = 1 # effectively just go left 
                y_right = 0

            elif Tiltright:
                step_x = -1 # step x & y are to select next step down, ie 45 deg for a tilt
                step_y = -1 # +ve down
                x_left = 0 # x/y left and right are used if 'step x/y' cant find a free spot.  Values are added to step x/y!
                x_right = 0 
                y_left = 0 
                y_right = 1 # effectively just go right

            else:
                # No tilt
                step_x = 0 # step x & y are to select next step down, ie straight down
                step_y = -1 # -ve down
                x_left = 1
                x_right = -1
                y_left = 0 # not used when upside down
                y_left = 0

        elif Direction == GravityLeft:
            # left side down so swap axis, ie x axis now controls 'gravity' direction and y across the hourglass
            if Tiltleft:
                step_x = -1 
                step_y = -1 
                x_left = 1 
                x_right = 0
                y_left = 0 
                y_right = 0

            elif Tiltright:
                step_x = -1 
                step_y = 1 
                x_left = 0 
                x_right = 1 
                y_left = 0 
                y_right = 0

            else:
                # No tilt
                step_x = -1 
                step_y = 0 
                x_left = 0 
                x_right = 0
                y_left = -1
                y_right = 1

        elif Direction == GravityRight:
            # right side down so swap axis, ie x axis now controls 'gravity' direction and y across the hourglass
            if Tiltleft:
                step_x = 1 
                step_y = 1 
                x_left = -1 
                x_right = 0
                y_left = 0 
                y_right = 0

            elif Tiltright:
                step_x = 1 
                step_y = -1 
                x_left = 0 
                x_right = -1 
                y_left = 0 
                y_right = 0

            else:
                # No tilt
                step_x = 1 
                step_y = 0 
                x_left = 0 
                x_right = 0
                y_left = 1
                y_right = -1

        elif Direction == Flat: # Nothing to do....
            step_x = 0
            step_y = 0
            x_left = 0 
            x_right = 0
            y_left = 0
            y_right = 0            
        

        #print(Direction, step_x,step_y,x_left,x_right,y_left,y_right)

        for i in range(0, len(grains)):
            # Check all grains in this pass
            # Move grain down one pixel position, if possible, else down left or down right one position
            # Note that this routine copes with any orientation of the hourglass by the settings of
            # x/y step/left/right variables

            # Get x & y of current grain
            grain_x = sorted_grains[i][GRAINS_X]
            grain_y = sorted_grains[i][GRAINS_Y]

            if toggle: # Check left first
                # Check if next pixel down is free
                if pixels[grain_x+step_x,grain_y+step_y] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x+step_x,grain_y+step_y] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains[i] = [grain_x+step_x, grain_y+step_y]
                    update_count = update_count + 1  # indicate moved a grain
                # Check left lower pixel
                elif pixels[grain_x + step_x + x_left, grain_y + step_y + y_left] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x + step_x + x_left, grain_y + step_y + y_left] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains[i] = [grain_x + step_x + x_left, grain_y + step_y + y_left]
                    update_count = update_count + 1  # indicate moved a grain
                # Check right lower pixel
                elif pixels[grain_x + step_x + x_right, grain_y + step_y + y_right] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x + step_x + x_right, grain_y + step_y + y_right] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains[i] = [grain_x + step_x + x_right, grain_y + step_y + y_right]
                    update_count = update_count + 1  # indicate moved a grain
            else: # Check right first
                # Check if next pixel down is free
                if pixels[grain_x+step_x,grain_y+step_y] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x+step_x,grain_y+step_y] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains[i] = [grain_x+step_x, grain_y+step_y]
                    update_count = update_count + 1  # indicate moved a grain
                # Check right lower pixel
                elif pixels[grain_x + step_x + x_right, grain_y + step_y + y_right] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x + step_x + x_right, grain_y + step_y + y_right] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains[i] = [grain_x + step_x + x_right, grain_y + step_y + y_right]
                    update_count = update_count + 1  # indicate moved a grain
                # Check left lower pixel
                elif pixels[grain_x + step_x + x_left, grain_y + step_y + y_left] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x + step_x + x_left, grain_y + step_y + y_left] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains[i] = [grain_x + step_x + x_left, grain_y + step_y + y_left]
                    update_count = update_count + 1  # indicate moved a grain
            
            toggle = not toggle # Swap for next time

        pass_count = pass_count + 1
        total_move_count = total_move_count + update_count # Add count for the current pass
        #print(pass_count, total_move_count, update_count)

        # Update screen to display all grains moved this pass
        st7789.display(image)
        #time.sleep(0.13)


# TODO - delete this function?????
def draw_completed(duration):
    global image, draw
    image = Image.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), ("#99ccff")) # Make initial board bluish..
    draw = ImageDraw.Draw(image) # Setup so can draw on the screen for menu etc.

    # Success image
    image2 = Image.open("success.png")
    image2 = image2.resize((100,100)) 
    image.paste(image2, (70,10)) # onto screen

    # Now to add some text as well.....
    font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 24) # Create our font, passing in the font file and font size
    draw.text((20, 115), "Maze Completed", font = font, fill = ("red"))

    txt = "Time Taken: \n{:.2f}, seconds".format(duration)
    draw.text((20, 150), txt, font = font, fill = ("red"))

    # draw menu
    st7789.display(image)


def btn1handler():
    global mode
    # If TIMING or FINISHED, any button press will go back to the menu
    if mode == TIMING or mode == FINISHED:
        mode = MENU
    else: # Menu option for button A is to start timer
        mode = TIMING

def btn2handler():
    global mode
    # If TIMING or FINISHED, any button press will go back to the menu
    if mode == TIMING or mode == FINISHED:
        mode = MENU
    else: # Select test mode to see gyro output - Test button not shown in menu
        mode = TEST

def btn3handler():
    global mode
    # If TIMING or FINISHED, any button press will go back to the menu
    if mode == TIMING or mode == FINISHED:
        mode = MENU
    else: # Menu option for button X is to run hourglass continuously
        mode = CONTINUOUS

def btn4handler():
    global mode
    # If TIMING or FINISHED, any button press will go back to the menu
    if mode == TIMING or mode == FINISHED:
        mode = MENU
    else: # Menu option TBC
        mode = MENU

# Setup gyro object
bus = smbus.SMBus(1) 	# or bus = smbus.SMBus(0) for older version boards
Device_Address = 0x68   # MPU6050 device address
MPU_Init()

# Setup screen object
SPI_SPEED_MHZ = 80

st7789 = ST7789(
    rotation=90,  # Needed to display the right way up on Pirate Audio
    port=0,       # SPI port
    cs=1,         # SPI port Chip-select channel
    dc=9,         # BCM pin used for data/command
    backlight=13,
    spi_speed_hz=SPI_SPEED_MHZ * 1000 * 1000
)
# Button numbering is using BCM numbering
btn1 = Button(5)      # assign each button to a variable
btn2 = Button(6)      # by passing in the pin number
btn3 = Button(16)     # associated with the button
btn4 = Button(24)     # 

# tell the button what to do when pressed
btn1.when_pressed = btn1handler
btn2.when_pressed = btn2handler
btn3.when_pressed = btn3handler
btn4.when_pressed = btn4handler

while True:
# TODO: Add a calibrate mode to determine time taken to complete grains grain and adjust delay of
# grain movement algorithm so that time taken to complete matches set time

    # TODO: Run timing for specified time
    if mode == TIMING:
        game_start = time.time()
        update_grains()
        mode = FINISHED

    # Run continuously to allow playing with hourglass
    elif mode == CONTINUOUS:
        update_grains()
        mode = MENU

    # Non visible test mode to show raw gyro data read
    elif mode == TEST:
        read_gyro_data()
        time.sleep(1)

    # Draw initial screen and menu
    elif mode == MENU:
        grains = [] # Create list definition to hold each grain x,y - will grow to meet max no of grains - grains[n][GRAINS_X] or grains[n][GRAINS_Y] etc
        sorted_grains = [] # List of grains in a sorted order in each row - scans from centre out for each row
        draw_menu() # Load hourglass graphic and add menu options
        analyse_hourglass_graphic() # Set up useful constants based on graphic size/position
        fill_hourglass() # Fill top of hourglass
        mode = NULL  # Dont do anything until a button is pressed.

    # TODO: complete timing finished processing
    if mode == FINISHED:
        game_end = time.time()
        duration = game_end - game_start
        print(duration)
        mode = NULL


    #time.sleep(0.05)