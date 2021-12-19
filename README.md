# Hourglass
## Raspberry Pi with a Pirate Audio HAT and a gyro sensor implementation of an Hourglass

Inspiration from https://hackaday.io/project/165620-digital-hourglass, but developed from scratch. Implements a form of Cellular Automata where each grain of sand has simple rules applied for it's movement taking account of the direction of gravity.
  - Simple algorithm - move sand grain in gravity direction one pixel, if not possible then try adjacent left/right pixel.  Gravity to be determined as either N/S/E/W/NE/NW/SE/SW
  - Can take any 'typical' hourglass graphic and work out where to fill it (amount of fill can be changed by simple code change)
  - This implementation has 1238 grains (can be varied as required by simple code change)
  - If the hourglass is too far off vertical than the grains stop (ie if it is laid flat then the grains stop just like the real thing)

## Modes:
  - Timer - when initially pressed will run through as quick as possible, but time required can be 'Set' - orientation is fixed
  - Continuous - runs continuously with orientation taken into account
  - Set - sets specified hourglass time - when Timer is pushed again will run at set rate - orientation is fixed again
  - Cal - runs through like the Timer to calibrate the times.  Should be able to more accurately set the specified times.

## Note that the code has been optimised to run as fast as possible so it does not always use the standard python data types, ie minmised use of floating point and used simple arrays instead of lists.
## Also, the original target was the Raspberry Pi Zero W, so the code was structured to be able to use Cython to run smoothly enough.  Now runs natively on the Raspberry Pi Zero 2 W which is fast enought with Python.

![image](https://user-images.githubusercontent.com/30411837/146686590-3b8019ee-bb5f-4212-b62c-7b6685081622.png)
![image](https://user-images.githubusercontent.com/30411837/146686568-4c33ea34-a891-40af-9da4-bd581183cf6d.png)



