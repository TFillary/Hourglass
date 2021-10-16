#!/usr/bin/env python3
#############################################################################
# Filename    : grains.py
# Description :	Utilities to analyse an hourgraph graphic, fill with grains
#               and move grains according to the gravity direction
# Author      : Trevor Fillary
# modification: 16-10-2021
########################################################################
import time
from PIL import Image, ImageDraw, ImageFont
from ST7789 import ST7789

# Import application modules
import my_globals as g
from hourglassgyro import read_gyro_xy


# Definitions for the screen
pixels = None  # Pixel graphic object
MAX_SCREEN_INDEX = 239 # 0 to 239
MIN_SCREEN_INDEX = 0

# Definitions for hourglass
HOURGLASS_TOP_Y = 0 # Inside hourglass
HOURGLASS_BOTTOM_Y = 0 # Inside hourglass
HOURGLASS_CENTRE_Y = 0 # Inside hourglass
HOURGLASS_CENTRE_X = 0 # Inside hourlgass
HOURGLASS_UPRIGHT = True # Assume upright initially

NO_GRAIN_ROWS = 32  # Sets number of sand rows to display

# Note 'simplified' fixed arrays are used to speed up processing, ie Python List processing is slow....
grains_x = [0] * 2000           # NOTE: Nominally set to 2000, depends on how much sand is filled.  Used fixed size to speed up code
grains_y = [0] * 2000
sorted_grains_x = [0] * 2000
sorted_grains_y = [0] * 2000

grain_image = Image.new("RGB", (1, 1), (0, 255, 0)) # green, single image
delete_grain_image = Image.new("RGB", (1, 1), (255, 255, 255)) # white, background colour, single image


def analyse_hourglass_graphic():
    global pixels, HOURGLASS_TOP_Y, HOURGLASS_BOTTOM_Y, HOURGLASS_CENTRE_X, HOURGLASS_CENTRE_Y
    # Routine to analyse the hourglass graphic that may change in size or position if it is updated
    # Assumes the hourglass is broadly central within the screen, background is white and hourglass
    # outline is black

    pixels = g.image.load()  # Load image into memory for pixel access later - check for collisions etc.
    hg_width, hg_height = g.image.size

    # Find top y inside hourglass
    found = False
    # Find top of outside of hourglass (assume middle of the screen for x) - black
    for i in range(1,hg_height):
        if pixels[(int(hg_width/2)),i] == (0,0,0):
            # Found start of outside
            HOURGLASS_TOP_Y = i
            found = True
            break
    
    if not found:
        print ("Hourgrlass graphic error")
        exit()
    
    found = False

    for i in range(HOURGLASS_TOP_Y, hg_height):
        if pixels[(int(hg_width/2)),i] != (0,0,0):
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
    for i in range(hg_height-1,0, -1):
        if pixels[(int(hg_width/2)),i] == (0,0,0):
            # Found start of outside
            HOURGLASS_BOTTOM_Y = i
            found = True
            break
    
    if not found:
        print ("Hourgrlass graphic error")
        exit()
    
    found = False

    for i in range(HOURGLASS_BOTTOM_Y, 0, -1):
        if pixels[(int(hg_width/2)),i] != (0,0,0):
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
    for i in range(int(hg_width/2), 0, -1):
        if pixels[i,HOURGLASS_TOP_Y] == (0,0,0):
            # Found start of inside
            left_x = i
            found=True
            break

    if not found:
        print ("Hourgrlass graphic error")
        exit()

    # Next find right most inside hourglass
    for i in range(int(hg_width/2), hg_width):
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
    global pixels
    # Routine to fill the top half of the hourglass (up to the max number of rows)

    for i in range(HOURGLASS_CENTRE_Y,(HOURGLASS_CENTRE_Y - NO_GRAIN_ROWS),-1):
        fill_row(i)


def fill_row(row_y):
    global pixels, grains_x, grains_y
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

    row_start = g.no_grains # capture the row index of the grains array for reordering
    # Draw each grain image and add grain x,y to grains list for future processing of movement
    for i in range(left_x, right_x + 1):
        pixels[i,row_y] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
        grains_x[g.no_grains] = i
        grains_y[g.no_grains] = row_y
        g.no_grains = g.no_grains + 1

    g.st7789.display(g.image, g.hg_tl_x,g.hg_tl_y,g.hg_br_x,g.hg_br_y)  # update hourglass image (inc added grains row) only
    row_end = g.no_grains - 1
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
    for _ in range(row_start, row_end + 1):
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


def update_grains():
    global pixels, sorted_grains_x, sorted_grains_y
    # Cycles through the grains to move them to the next available space either one below, lower left or lower right.
    # These checks are performed at all compass directionS - N/S/E/W/NE/NW/SE/SW
    # The grain movement parameters are adjusted to account for the orientation of the hourglass to minimise 
    # the later on processing. 
    #
    # Function runs until there are no more grains to move or runs continuously
    # Algorithm is: try moving grain straight down first, if fails then attempt to move down at 45 deg (left and right checks).
    #
    # To speed up processing only update the desplay every 'n' number of passes
    
    update_count = 1 # set to 1 to get started on main loop
    # init stat variables - only valid if run during a standard timing run
    total_move_count = 0
    pass_count = 0
    display_update = 0 # Used to limit screen updates to every other pass

    # Main loop to loop until there is no more grain movement (when being used as a timer) or to run continuously
    while (g.mode == g.CONTINUOUS) or not(update_count == 0):
        
        update_count = 0 # Reset for current pass of the grains
        toggle = True # Used to toggle checking left/right first
        
        # Get gyro direction 
        Direction = read_gyro_xy() 
    
        #print(Direction)

    # Down x/y are used for the inital test to see if can move directly below
    # x/y left & right are used to check whether the can move 45 degrees left or right
    # All number pairs are added to the 'grain' position for any testing

        if Direction == g.S or g.mode == g.TIMING or g.mode == g.CAL:  # Force right way up if in timing mode
            down_x = 0 # down x & y are to select next step down, ie straight down
            down_y = 1 # +ve down
            x_left = -1 # x/y left and right are used if 'down x/y' cant find a free spot.  
            y_left = 1 # Change to down 45 deg
            x_right = 1 # Change to down 45 deg
            y_right = 1

        elif Direction == g.SW:
            down_x = -1 # down x & y are to select next step down, ie 45 deg for a tilt
            down_y = 1 # +ve down
            x_left = -2 # x/y left and right are used if 'down x/y' cant find a free spot.  
            y_left = 0 # effectively up left 45 deg 
            x_right = 0
            y_right = 2

        elif Direction == g.SE:
            down_x = 1 # down x & y are to select next step down, ie 45 deg for a tilt
            down_y = 1 # +ve down
            x_left = 0 # x/y left and right are used if 'down x/y' cant find a free spot. 
            y_left = 2 
            x_right = 2 
            y_right = 0 # effectively up right 45 deg

        elif Direction == g.N: # Upside down
            down_x = 0 # step x & y are to select next step down, ie straight down
            down_y = -1 # -ve down
            x_left = 1 # change to down 45 deg
            y_left = -1 # change to down 45 deg
            x_right = -1
            y_right = -1

        elif Direction == g.NE:
            down_x = 1 # step x & y are to select next step down, ie 45 deg for a tilt
            down_y = -1 # -ve down
            x_left = 2 # x/y left and right are used if 'down x/y' cant find a free spot.  
            y_left = 0 # effectively up left 45 deg
            x_right = 0
            y_right = -2

        elif Direction == g.NW:
            down_x = -1 # step x & y are to select next step down, ie 45 deg for a tilt
            down_y = -1 # +ve down
            x_left = 0 # x/y left and right are used if 'down x/y' cant find a free spot.
            y_left = -2  
            x_right = -2 
            y_right = 0 # effectively up right 45 deg

        elif Direction == g.W:
            down_x = -1 
            down_y = 0 
            x_left = -1 
            y_left = -1
            x_right = -1
            y_right = 1

        elif Direction == g.E:
            down_x = 1 
            down_y = 0 
            x_left = 1 
            y_left = 1
            x_right = 1
            y_right = -1

        elif Direction == g.FLAT: # Nothing to do....
            down_x = 0
            down_y = 0
            x_left = 0 
            x_right = 0
            y_left = 0
            y_right = 0            
        
        #print(Direction, step_x,step_y,x_left,x_right,y_left,y_right)

        for i in range(0, g.no_grains-1):
            # Check all grains in this pass
            # Move grain down one pixel position, if possible, else down left or down right one position
            # Note that this routine copes with any orientation of the hourglass by the settings of
            # x/y step/left/right variables

            # Get x & y of current grain
            grain_x = sorted_grains_x[i]
            grain_y = sorted_grains_y[i]

            if toggle: # Check left first
                # Check if next pixel down is free
                if pixels[grain_x+down_x,grain_y+down_y] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x+down_x,grain_y+down_y] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains_x[i] = grain_x+down_x
                    sorted_grains_y[i] = grain_y+down_y
                    update_count = update_count + 1  # indicate moved a grain
                # Check left lower pixel
                elif pixels[grain_x + x_left, grain_y + y_left] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x + x_left, grain_y + y_left] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains_x[i] = grain_x + x_left
                    sorted_grains_y[i] = grain_y + y_left
                    update_count = update_count + 1  # indicate moved a grain
                # Check right lower pixel
                elif pixels[grain_x + x_right, grain_y + y_right] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x + x_right, grain_y + y_right] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains_x[i] = grain_x + x_right
                    sorted_grains_y[i] = grain_y + y_right
                    update_count = update_count + 1  # indicate moved a grain
            else: # Check right 
                # Check if next pixel down is free
                if pixels[grain_x+down_x,grain_y+down_y] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x+down_x,grain_y+down_y] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains_x[i] = grain_x+down_x
                    sorted_grains_y[i] = grain_y+down_y
                    update_count = update_count + 1  # indicate moved a grain
                # Check right lower pixel
                elif pixels[grain_x + x_right, grain_y + y_right] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x + x_right, grain_y + y_right] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains_x[i] = grain_x + x_right
                    sorted_grains_y[i] = grain_y + y_right
                    update_count = update_count + 1  # indicate moved a grain
                # Check left lower pixel
                elif pixels[grain_x + x_left, grain_y + y_left] == (255,255,255): # white, ie empty
                    # Delete original grain
                    pixels[grain_x,grain_y] = (255,255,255) # write a white pixels to the local graphic for future collision checks.
                    # Write new grain
                    pixels[grain_x + x_left, grain_y + y_left] = (0,255,0) # write a green pixels to the local graphic for future collision checks.
                    # Update new grain x,y in grains list
                    sorted_grains_x[i] = grain_x + x_left
                    sorted_grains_y[i] = grain_y + y_left
                    update_count = update_count + 1  # indicate moved a grain
            
            toggle = not toggle # Swap for next time

        pass_count = pass_count + 1
        total_move_count = total_move_count + update_count # Add count for the current pass
        #print(pass_count, total_move_count, update_count)

        if display_update == 10:  # Delay update for 'n' passes to improve performance
            # Update screen to display all grains moved this pass
            g.st7789.display(g.image, g.hg_tl_x,g.hg_tl_y,g.hg_br_x,g.hg_br_y)  # update hourglass image only
            display_update = 0
        display_update = display_update + 1

        # Don't delay in continuous mode or if no cal has been run        
        if g.pass_delay != 0 and not g.mode == g.CONTINUOUS:
            time.sleep((g.pass_delay-0.012)) # subtracted 12ms fudge factor to cal!!

    return total_move_count, pass_count