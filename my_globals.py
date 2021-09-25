#!/usr/bin/env python3
#############################################################################
# Filename    : my_globals.py
# Description :	Globals for hourglass application
# Author      : Trevor Fillary
# modification: 25-09-2021
########################################################################

# Gravity definitions - For the normal way up gravity is South
FLAT = 0
N = 1
S = 2
E = 3
W = 4
NE =5
NW = 6
SE = 7
SW = 8
# TODO: Delete the following 4 variables when compass points working
#UPSIDE_DOWN = 1
#RIGHTWAY_UP = 2
#GRAVITY_LEFT = 3
#GRAVITY_RIGHT = 4

mode = 0

SCREEN_SIZE = 240 # 240x240 square
hg_tl_x = 0 # HourGlass Top Left
hg_tl_y = 0
hg_br_x = 0 # HourGlass bottom right
hg_br_y = 0

st7789 = None  # Display object
image = None   # Image object

no_grains = 0  # Keeps track of the number of grains created in the hourglass
pass_delay = 0 # Used to delay the passes to match the required delay - needs to be calibrated before use - 0 means don't use!!