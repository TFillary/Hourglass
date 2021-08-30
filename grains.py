#!/usr/bin/env python3
#############################################################################
# Filename    : grains.py
# Description :	Utilities to analyse an hourgraph graphic, fill with grains
#               and move grains
# Author      : Trevor Fillary
# modification: 29-08-2021
########################################################################
import time
from PIL import Image, ImageDraw, ImageFont
from ST7789 import ST7789
from hourglassgyro import read_gyro_xy

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

# Gravity definitions
Flat = 0
Upside_Down = 1
Rightway_up = 2
GravityLeft = 3
GravityRight = 4

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
#GRAINS_X = 0 # Used to indx the x element of the grains list
#GRAINS_Y = 1 # Used to index the y element of the grains list
#grains = [] # Create list definition to hold each grain x,y - will grow to meet max no of grains - grains[n][GRAINS_X] or grains[n][GRAINS_Y] etc
#sorted_grains = [] # List of grains in a sorted order in each row - scans from centre out for each row

grains_x = [0] * 2000   
grains_y = [0] * 2000
sorted_grains_x = [0] * 2000
sorted_grains_y = [0] * 2000

st7789=0
grain_image = Image.new("RGB", (1, 1), (0, 255, 0)) # green, single image
delete_grain_image = Image.new("RGB", (1, 1), (255, 255, 255)) # white, background colour, single image

def set_grains_display_ref(display_object):
    global st7789
    st7789 = display_object


def analyse_hourglass_graphic(pixels):
    global HOURGLASS_TOP_Y, HOURGLASS_BOTTOM_Y, HOURGLASS_CENTRE_X, HOURGLASS_CENTRE_Y
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

def fill_hourglass(image,pixels):
    # Routine to fill the top half of the hourglass (up to the max number of rows)

    for i in range(HOURGLASS_CENTRE_Y,(HOURGLASS_CENTRE_Y - NO_GRAIN_ROWS),-1):
        fill_row(pixels,i)

    # TODO fix these bodges - just leave a single pixel hole
    pixels[114,113] = (0,0,0) # black
    pixels[115,113] = (0,0,0) # black
    pixels[116,113] = (0,0,0) # black
    pixels[118,113] = (0,0,0) # black
    pixels[119,113] = (0,0,0) # black
    pixels[120,113] = (0,0,0) # black
    st7789.display(image)

def fill_row(pixels,row_y):
    global no_grains, grains_x, grains_y
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

    row_start = no_grains # capture the row index of the grains array for reordering
    # Draw each grain image and add grain x,y to grains list for future processing of movement
    for i in range(left_x, right_x + 1):
        st7789.display(grain_image, i,row_y, i, row_y)
        #TODO - create numpy array to mirror pixels graphic & grains to speedup collision checks
        # Add new state to take account if falling or stationary
        pixels[i,row_y] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
        grains_x[no_grains] = i
        grains_y[no_grains] = row_y
        #grains.append([i,row_y])
        no_grains = no_grains + 1

    row_end = no_grains - 1
    reorder_grains(row_start, row_end)
    
def reorder_grains(row_start, row_end):
    global grains_x, grains_y, sorted_grains_x, sorted_grains_y
    # This section re-orders the grains list so the grains are scanned
    # either side of the centre of the hourglass towards the edges for a 
    # more even pattern draining from the centre of the hourglass
    mid_row = row_start + int((row_end - row_start)/2)
    left = mid_row -1
    right = mid_row
    idx = row_start
    for i in range(row_start, row_end):
        if right <= row_end:
            #sorted_grains.append(grains[right])
            sorted_grains_x[idx] = grains_x[right]
            sorted_grains_y[idx] = grains_y[right]
            right = right + 1
            idx = idx + 1
        if left >= row_start:
            #sorted_grains.append(grains[left])
            sorted_grains_x[idx] = grains_x[left]
            sorted_grains_y[idx] = grains_y[left]
            left = left -1
            idx = idx + 1

    # print(grains)
    # print(sorted_grains)


def update_grains(mode, image, pixels, pass_delay):
    global sorted_grains_x, sorted_grains_y, no_grains
    # Cycles through the grains to move them to the next available space either one below, lower left or lower right, 
    # or when tilting to the left or right.
    # The grain movement parameters are adjusted to account for the orientation of the hourglass
    # Function runs until there are no more grains to move or runs continuously
    # Algorithm is: No tilt- try moving grain straight down first then attempt to move down at 45 deg (left or right)
    #               A tilt - try moving grain down at 45 deg first then attempt to move just left/right
    
    update_count = 1 # set to 1 to get started on main loop
    # init stat variables - only valid if run during a standard timing run
    total_move_count = 0
    pass_count = 0

    # TODO: Fix CONTINUOUS mode now that mode is passed as a parameter !! ie cant exit continuous
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

        for i in range(0, no_grains-1):
            # Check all grains in this pass
            # Move grain down one pixel position, if possible, else down left or down right one position
            # Note that this routine copes with any orientation of the hourglass by the settings of
            # x/y step/left/right variables

            # Get x & y of current grain
            grain_x = sorted_grains_x[i]
            grain_y = sorted_grains_y[i]

            if toggle: # Check left first
                # Check if next pixel down is free
                if pixels[grain_x+step_x,grain_y+step_y] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x+step_x,grain_y+step_y] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains_x[i] = grain_x+step_x
                    sorted_grains_y[i] = grain_y+step_y
                    update_count = update_count + 1  # indicate moved a grain
                # Check left lower pixel
                elif pixels[grain_x + step_x + x_left, grain_y + step_y + y_left] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x + step_x + x_left, grain_y + step_y + y_left] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains_x[i] = grain_x + step_x + x_left
                    sorted_grains_y[i] = grain_y + step_y + y_left
                    update_count = update_count + 1  # indicate moved a grain
                # Check right lower pixel
                elif pixels[grain_x + step_x + x_right, grain_y + step_y + y_right] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x + step_x + x_right, grain_y + step_y + y_right] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains_x[i] = grain_x + step_x + x_right
                    sorted_grains_y[i] = grain_y + step_y + y_right
                    update_count = update_count + 1  # indicate moved a grain
            else: # Check right first
                # Check if next pixel down is free
                if pixels[grain_x+step_x,grain_y+step_y] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x+step_x,grain_y+step_y] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains_x[i] = grain_x+step_x
                    sorted_grains_y[i] = grain_y+step_y
                    update_count = update_count + 1  # indicate moved a grain
                # Check right lower pixel
                elif pixels[grain_x + step_x + x_right, grain_y + step_y + y_right] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x + step_x + x_right, grain_y + step_y + y_right] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains_x[i] = grain_x + step_x + x_right
                    sorted_grains_y[i] = grain_y + step_y + y_right
                    update_count = update_count + 1  # indicate moved a grain
                # Check left lower pixel
                elif pixels[grain_x + step_x + x_left, grain_y + step_y + y_left] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x + step_x + x_left, grain_y + step_y + y_left] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains_x[i] = grain_x + step_x + x_left
                    sorted_grains_y[i] = grain_y + step_y + y_left
                    update_count = update_count + 1  # indicate moved a grain
            
            toggle = not toggle # Swap for next time

        pass_count = pass_count + 1
        total_move_count = total_move_count + update_count # Add count for the current pass
        #print(pass_count, total_move_count, update_count)

        # Update screen to display all grains moved this pass
        st7789.display(image)

        # Don't delay in continuous mode or if no cal has been run        
        if pass_delay != 0 and not mode == CONTINUOUS:
            time.sleep((pass_delay-0.012)) # subtracted 12ms fudge factor to cal!!

    no_grains = 0 # force to zero for the next run    
    return total_move_count, pass_count