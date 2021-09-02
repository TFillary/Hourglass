#!/usr/bin/env python3
#############################################################################
# Filename    : my_globals.py
# Description :	Globals for hourglass application
# Author      : Trevor Fillary
# modification: 01-09-2021
########################################################################

# Gravity definitions
FLAT = 0
UPSIDE_DOWN = 1
RIGHTWAY_UP = 2
GRAVITY_LEFT = 3
GRAVITY_RIGHT = 4

mode = 0

st7789 = None  # Display object
image = None   # Image object

no_grains = 0  # Keeps track of the number of grains created in the hourglass
pass_delay = 0 # Used to delay the passes to match the required delay - needs to be calibrated before use - 0 means don't use!!