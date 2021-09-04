#!/usr/bin/env python3
#############################################################################
# Filename    : my_globals.pyx
# Description :	Cython version - Globals for hourglass application
# Author      : Trevor Fillary
# modification: 01-09-2021
########################################################################

import cython

# Gravity definitions
FLAT = 0
UPSIDE_DOWN = 1
RIGHTWAY_UP = 2
GRAVITY_LEFT = 3
GRAVITY_RIGHT = 4

cdef int mode = 0

st7789 = None  # Display object
image = None   # Image object

cdef int no_grains = 0  # Keeps track of the number of grains created in the hourglass
pass_delay = 0 # Used to delay the passes to match the required delay - needs to be calibrated before use - 0 means don't use!!