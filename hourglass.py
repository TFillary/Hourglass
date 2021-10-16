#!/usr/bin/env python3
#############################################################################
# Filename    : hourglass.py
# Description :	Application to use the Pirate Audio board with 240x240 pixel screen + 4 buttons to
#               run an hourglass using a gyro/accelerometer board to control it.
#               Inspiration from https://hackaday.io/project/165620-digital-hourglass, but developed from scratch.
#               Implements a form of Cellular Automata.  Each grain of sand has simple rules applied for it's movement
#               taking account of the direction of gravity (N,S,E,W,NE,NW,SE,SW).
#               Can take any 'typical' hourglass graphic and work out where to fill it (amount of fill can be changed)
#               This implementation has 1238 grains (can be varied as required)
#               Note that the code has been optimised to run as fast as possible so it does not always use the 
#               standard python data types.
#               Modes:  Timer - when initially pressed will run through as quick as possible - orientation is fixed
#                       Continuous - runs continuously with orientation taken into account
#                       Set - sets specified hourglass time - when Timer is pushed again will run at set rate 
#                             - orientation is fixed again
#                       Cal - runs through like the Timer to calibrate the times.  Should be able to more accurately set
#                             the specified times.
# Author      : Trevor Fillary
# modification: 16-10-2021
########################################################################

import time
from gpiozero import Button

from colorsys import hsv_to_rgb
from PIL import Image, ImageDraw, ImageFont
from ST7789 import ST7789

# Import application modules
import my_globals as g
from hourglassgyro import gyro_init, read_gyro_xy
from grains import analyse_hourglass_graphic, fill_hourglass, update_grains

# Image variables
draw = None

# Stat variables
total_move_count = 0
pass_count = 0
g.mode = g.MENU  # default to menu at start


# Used to set the reqired timing period
set_time = 3 # Default to 3 minutes
cal_time = 0

def draw_menu():
    global draw
    g.image = Image.open("hourglassOnly.bmp") # Load initial picture
    hg_width, hg_height = g.image.size

    menuimage = Image.new('RGB', (240,240), color = (255,255,255)) # Create a white screen
    draw = ImageDraw.Draw(menuimage) # Setup so can draw on the screen for menu etc.
    
    # Now to add some text for the buttons.....
    font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 16) # Create our font, passing in the font file and font size
    #font2 = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 24) # Create our font, passing in the font file and font size

    txt_colour = (0,0,0)
    draw.text((5, 60), "Time", font = font, fill = txt_colour) # A button
    draw.text((5, 180), "Set", font = font, fill = txt_colour) # B button    
    draw.text((157, 60), "Continuous", font = font, fill = txt_colour) # X button
    draw.text((170, 180), "Cal", font = font, fill = txt_colour) # Y button

    # draw menu items
    g.st7789.display(menuimage)

    # Calculate position of hourglass graphic (centre of the screen)
    mid_screen = int(g.SCREEN_SIZE/2)
    mid_hourglass_x = int(hg_width/2)
    mid_hourglass_y = int(hg_height/2)
    g.hg_tl_x = mid_screen - mid_hourglass_x
    g.hg_tl_y = mid_screen - mid_hourglass_y
    g.hg_br_x = mid_screen + mid_hourglass_x
    g.hg_br_y = mid_screen + mid_hourglass_y

    g.st7789.display(g.image, g.hg_tl_x,g.hg_tl_y,g.hg_br_x,g.hg_br_y)  # add hourglass image


def draw_set():
    # Draw set image screen
    set_image = Image.new('RGB', (240,240), color = (255,255,255)) # Create a white screen
    draw = ImageDraw.Draw(set_image) # Setup so can draw on the screen for menu etc.
    
    # Now to add some text for the buttons.....
    font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 16) # Create our font, passing in the font file and font size
    #font2 = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 24) # Create our font, passing in the font file and font size

    txt_colour = (0,0,0)
    draw.text((5, 60), "1.5 Minutes", font = font, fill = txt_colour) # A button
    draw.text((5, 180), "6 Minutes", font = font, fill = txt_colour) # B button    
    draw.text((156, 60), "3 Minutes", font = font, fill = txt_colour) # X button
    draw.text((156, 180), "10 Minutes", font = font, fill = txt_colour) # Y button

    # draw Set screen
    g.st7789.display(set_image)

def draw_completed():
    # Draw completed image screen
    completed_image = Image.new('RGB', (240,240), color = (255,255,255)) # Create a white screen
    draw = ImageDraw.Draw(completed_image) # Setup so can draw on the screen for menu etc.
    
    # Now to add some text 
    font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 16) # Create our font, passing in the font file and font size
    font2 = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 24) # Create our font, passing in the font file and font size

    draw.text((40, 50), "TIME'S UP", font = font2, fill = ("red"))

    txt = "No. Passes: {}".format(pass_count)
    draw.text((20, 100), txt, font = font, fill = ("black"))

    txt = "No Moves: {}".format(total_move_count)
    draw.text((20, 140), txt, font = font, fill = ("black"))

    txt = "Time Taken: \n{:.2f}, seconds".format(duration)
    draw.text((20, 180), txt, font = font, fill = ("black"))

    # draw completed screen
    g.st7789.display(completed_image)

def btn1handler():
    global set_time
    # If TIMING or FINISHED, any button press will go back to the menu
    if g.mode == g.TIMING or g.mode == g.FINISHED:
        g.mode = g.MENU
    elif g.mode == g.SET:
        set_time = 1.5 # Minutes
        g.mode = g.MENU
    elif g.mode == g.WAIT:
        g.mode = g.MENU        
    else: # Menu option for button A is to start timer
        g.mode = g.TIMING

def btn2handler():
    global set_time
    # If TIMING or FINISHED, any button press will go back to the menu
    if g.mode == g.TIMING or g.mode == g.FINISHED:
        g.mode = g.MENU
    elif g.mode == g.SET:
        set_time = 6 # Minutes
        g.mode = g.MENU
    elif g.mode == g.WAIT:
        g.mode = g.MENU           
    else: # Menu option for button B is to set timer duration
        g.mode = g.SET_MENU

def btn3handler():
    global set_time
    # If TIMING or FINISHED, any button press will go back to the menu
    if g.mode == g.TIMING or g.mode == g.FINISHED:
        g.mode = g.MENU
    elif g.mode == g.SET:
        set_time = 3 # Minutes
        g.mode = g.MENU
    elif g.mode == g.WAIT:
        g.mode = g.MENU   
    else: # Menu option for button X is to run hourglass continuously
        g.mode = g.CONTINUOUS

def btn4handler():
    global set_time
    # If TIMING or FINISHED, any button press will go back to the menu
    if g.mode == g.TIMING or g.mode == g.FINISHED:
        g.mode = g.MENU
    elif g.mode == g.SET:
        set_time = 10 # Minutes
        g.mode = g.MENU
    elif g.mode == g.WAIT:
        g.mode = g.MENU           
    else: # Menu option for button Y is to run the calibration
        g.mode = g.CAL

# Setup gyro object
gyro_init()

# Setup screen object
SPI_SPEED_MHZ = 80
# Save object in global for other modules to use
g.st7789 = ST7789(
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
    if g.mode == g.TIMING:
        game_start = time.time()
        if g.pass_delay != 0:  # Only update if has been through a calibration
            g.pass_delay = (set_time*60/pass_count) - (cal_time/pass_count)
        total_move_count, pass_count = update_grains()
        g.mode = g.FINISHED

    # Run continuously to allow playing with hourglass
    elif g.mode == g.CONTINUOUS:
        total_move_count, pass_count = update_grains()
        g.mode = g.MENU

    # Display the timer set options
    elif g.mode == g.SET_MENU:
        draw_set()
        g.mode = g.SET # Set mode for buttion selection
        
    elif g.mode == g.CAL:
        cal_start = time.time()
        total_move_count, pass_count = update_grains()
        cal_time = time.time() - cal_start
        g.pass_delay = (set_time*60/pass_count) - (cal_time/pass_count)
        #print(cal_time,pass_delay,pass_count, total_move_count)
        g.mode = g.MENU # Set mode for buttion selection

    # Draw initial screen and menu
    elif g.mode == g.MENU:
        g.no_grains = 0 # ready to start again
        draw_menu() # Load hourglass graphic and add menu options
        analyse_hourglass_graphic() # Set up useful constants based on graphic size/position
        fill_hourglass() # Fill top of hourglass
        g.mode = g.DO_NOTHING  # Dont do anything until a button is pressed.

    if g.mode == g.FINISHED:
        game_end = time.time()
        duration = game_end - game_start
        draw_completed()
        #print(duration)
        g.mode = g.WAIT


    #time.sleep(0.05)