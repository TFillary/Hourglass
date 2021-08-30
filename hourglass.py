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

import time
import math
import numpy as np
from pathlib import Path

from gpiozero import Button

from colorsys import hsv_to_rgb
from PIL import Image, ImageDraw, ImageFont
from ST7789 import ST7789

from hourglassgyro import gyro_init, read_gyro_xy
from grains import set_grains_display_ref, analyse_hourglass_graphic, fill_hourglass, update_grains, no_grains

# Global image variables
pixels = 0
image = 0
#image2 = 0
draw = 0

# Global state variables
TIMING = 1
MENU = 2 
FINISHED = 3
CONTINUOUS = 4
SET_MENU = 5
SET = 6
CAL = 7
WAIT = 8
NULL = 99
mode = MENU  # default to menu at start

# Stat variables
total_move_count = 0
pass_count = 0
pass_delay = 0 # Used to delay the passes to match the required delay - needs to be calibrated before use - 0 means don't use!!

# Used to set the reqired timing period
set_time = 3 # Default to 3 minutes
cal_time = 0

def draw_menu():
    global image, pixels, draw
    image = Image.open("hourglass.bmp") # Load initial picture
    draw = ImageDraw.Draw(image) # Setup so can draw on the screen for menu etc.
    pixels = image.load()  # Load image into memory for pixel access later - check for collisions etc.

        # Now to add some text for the buttons.....
    font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 16) # Create our font, passing in the font file and font size
    font2 = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 24) # Create our font, passing in the font file and font size

    # TODO - Fix tite size/pos
    # Rectangle for title
    #draw.rectangle((40, 18, 200, 50), outline = ("black"))
    #draw.text((50, 20), "Hourglass", font = font2, fill = ("#eba414")) # Title

    txt_colour = (0,0,0)
    draw.text((5, 60), "Time", font = font, fill = txt_colour) # A button
    draw.text((5, 180), "Set", font = font, fill = txt_colour) # B button    
    draw.text((156, 60), "Continuous", font = font, fill = txt_colour) # X button
    draw.text((170, 180), "Cal", font = font, fill = txt_colour) # Y button

    #draw.text((190, 120), str(get_difficulty()+1), font = font2, fill = (0,255,0))
    #draw.line((195, 80, 195, 120), width=4, fill=(255, 0, 0))
    #draw.line((195, 150, 195, 180), width=4, fill=(255, 0, 0))

    #image2 = Image.open("marble_pic.png")
    #image2 = image2.resize((80,80)) 
    #image.paste(image2, (60,80)) # onto menu screen

    # draw menu
    st7789.display(image)

def draw_set():
    # Draw set image screen
    set_image = Image.new('RGB', (240,240), color = (255,255,255)) # Create a white screen
    draw = ImageDraw.Draw(set_image) # Setup so can draw on the screen for menu etc.
    
        # Now to add some text for the buttons.....
    font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 16) # Create our font, passing in the font file and font size
    font2 = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 24) # Create our font, passing in the font file and font size

    txt_colour = (0,0,0)
    draw.text((5, 60), "1.5 Seconds", font = font, fill = txt_colour) # A button
    draw.text((5, 180), "6 Seconds", font = font, fill = txt_colour) # B button    
    draw.text((156, 60), "3 Seconds", font = font, fill = txt_colour) # X button
    draw.text((156, 180), "10 Seconds", font = font, fill = txt_colour) # Y button

    # draw Set screen
    st7789.display(set_image)

def draw_completed():
    # Draw completed image screen
    completed_image = Image.new('RGB', (240,240), color = (255,255,255)) # Create a white screen
    draw = ImageDraw.Draw(completed_image) # Setup so can draw on the screen for menu etc.
    
    # Now to add some text 
    font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 16) # Create our font, passing in the font file and font size
    font2 = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 24) # Create our font, passing in the font file and font size

    # Success image
    #image2 = Image.open("success.png")
    #image2 = image2.resize((100,100)) 
    #image.paste(image2, (70,10)) # onto screen

    draw.text((40, 50), "TIME'S UP", font = font2, fill = ("red"))

    txt = "No. Passes: {}".format(pass_count)
    draw.text((20, 100), txt, font = font, fill = ("black"))

    txt = "No Moves: {}".format(total_move_count)
    draw.text((20, 140), txt, font = font, fill = ("black"))

    txt = "Time Taken: \n{:.2f}, seconds".format(duration)
    draw.text((20, 180), txt, font = font, fill = ("black"))

    # draw completed screen
    st7789.display(completed_image)

def btn1handler():
    global mode, set_time
    # If TIMING or FINISHED, any button press will go back to the menu
    if mode == TIMING or mode == FINISHED:
        mode = MENU
    elif mode == SET:
        set_time = 1.5 # Minutes
        mode = MENU
    elif mode == WAIT:
        mode = MENU        
    else: # Menu option for button A is to start timer
        mode = TIMING

def btn2handler():
    global mode, set_time
    # If TIMING or FINISHED, any button press will go back to the menu
    if mode == TIMING or mode == FINISHED:
        mode = MENU
    elif mode == SET:
        set_time = 6 # Minutes
        mode = MENU
    elif mode == WAIT:
        mode = MENU           
    else: # Menu option for button B is to set timer duration
        mode = SET_MENU

def btn3handler():
    global mode, set_time
    # If TIMING or FINISHED, any button press will go back to the menu
    if mode == TIMING or mode == FINISHED:
        mode = MENU
    elif mode == SET:
        set_time = 3 # Minutes
        mode = MENU
    elif mode == WAIT:
        mode = MENU   
    else: # Menu option for button X is to run hourglass continuously
        mode = CONTINUOUS

def btn4handler():
    global mode, set_time
    # If TIMING or FINISHED, any button press will go back to the menu
    if mode == TIMING or mode == FINISHED:
        mode = MENU
    elif mode == SET:
        set_time = 10 # Minutes
        mode = MENU
    elif mode == WAIT:
        mode = MENU           
    else: # Menu option for button Y is to run the calibration
        mode = CAL

# Setup gyro object
gyro_init()

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

set_grains_display_ref(st7789)

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
    if mode == TIMING:
        game_start = time.time()
        if pass_delay != 0:  # Only update if has been through a calibration
            pass_delay = (set_time*60/pass_count) - (cal_time/pass_count)
        total_move_count, pass_count = update_grains(mode, image, pixels, pass_delay)
        no_grains = 0 # ready to start again
        mode = FINISHED

    # Run continuously to allow playing with hourglass
    elif mode == CONTINUOUS:
        total_move_count, pass_count = update_grains(mode, image, pixels, pass_delay)
        no_grains = 0 # ready to start again
        mode = MENU

    # Display the timer set options
    elif mode == SET_MENU:
        draw_set()
        mode = SET # Set mode for buttion selection
        
    elif mode == CAL:
        cal_start = time.time()
        total_move_count, pass_count = update_grains(mode, image, pixels, pass_delay)
        cal_time = time.time() - cal_start
        pass_delay = (set_time*60/pass_count) - (cal_time/pass_count)
        #print(cal_time,pass_delay,pass_count, total_move_count)
        mode = MENU # Set mode for buttion selection

    # Draw initial screen and menu
    elif mode == MENU:
        no_grains = 0 # ready to start again
        #grains = [] # Create list definition to hold each grain x,y - will grow to meet max no of grains - grains[n][GRAINS_X] or grains[n][GRAINS_Y] etc
        #sorted_grains = [] # List of grains in a sorted order in each row - scans from centre out for each row
        draw_menu() # Load hourglass graphic and add menu options
        analyse_hourglass_graphic(pixels) # Set up useful constants based on graphic size/position
        fill_hourglass(image,pixels) # Fill top of hourglass
        mode = NULL  # Dont do anything until a button is pressed.

    if mode == FINISHED:
        game_end = time.time()
        duration = game_end - game_start
        draw_completed()
        print(duration)
        mode = WAIT


    #time.sleep(0.05)