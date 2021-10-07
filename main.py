# ////////////////////////////////////////////////////////////////
# //                     IMPORT STATEMENTS                      //
# ////////////////////////////////////////////////////////////////

import math
import sys
import time
from threading import Thread
import os
os.environ['DISPLAY'] = ":0.0"
os.environ['KIVY_WINDOW'] = 'egl_rpi'

from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import *
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.slider import Slider
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.animation import Animation
from functools import partial
from kivy.config import Config
from kivy.core.window import Window
from pidev.Joystick import Joystick # buttons are actually buttons -1
from pidev.kivy import DPEAButton
from pidev.kivy import PauseScreen
from time import sleep
import RPi.GPIO as GPIO
from pidev.stepper import stepper
from pidev.Cyprus_Commands import Cyprus_Commands_RPi as cyprus



#PORTS
# 1 is cyprus
# 2 is magnet
# 3 is tall tower
# 4 is short tower

# ////////////////////////////////////////////////////////////////
# //                      GLOBAL VARIABLES                      //
# //                         CONSTANTS                          //
# ////////////////////////////////////////////////////////////////
START = True
STOP = False
UP = False
DOWN = True
ON = True
OFF = False
YELLOW = .180, 0.188, 0.980, 1
BLUE = 0.917, 0.796, 0.380, 1
CLOCKWISE = 0
COUNTERCLOCKWISE = 1
ARM_SLEEP = 2.5
DEBOUNCE = 0.10

lowerTowerPosition = 60
upperTowerPosition = 76


# ////////////////////////////////////////////////////////////////
# //            DECLARE APP CLASS AND SCREENMANAGER             //
# //                     LOAD KIVY FILE                         //
# ////////////////////////////////////////////////////////////////
class MyApp(App):

    def build(self):
        self.title = "Robotic Arm"
        return sm

Builder.load_file('main.kv')
Window.clearcolor = (.1, .1,.1, 1) # (WHITE)

cyprus.open_spi()
cyprus.initialize()
# ////////////////////////////////////////////////////////////////
# //                    SLUSH/HARDWARE SETUP                    //
# ////////////////////////////////////////////////////////////////

sm = ScreenManager()
arm = stepper(port = 0, speed = 10)

# ////////////////////////////////////////////////////////////////
# //                       MAIN FUNCTIONS                       //
# //             SHOULD INTERACT DIRECTLY WITH HARDWARE         //
# ////////////////////////////////////////////////////////////////



class MainScreen(Screen):
    cyprus.setup_servo(2)
    version = cyprus.read_firmware_version()
    armPosition = 0
    armControl = ObjectProperty(None)
    lastClick = time.clock()
    magnetControl = ObjectProperty(None)
    auto = ObjectProperty(None)

    joystick = Joystick(0,False)

    ison = False

    s0 = stepper(port=0, micro_steps=32, hold_current=20, run_current=20, accel_current=20, deaccel_current=20,
                 steps_per_unit=200, speed=3)

    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.initialize()

    def debounce(self):
        processInput = False
        currentTime = time.clock()
        if ((currentTime - self.lastClick) > DEBOUNCE):
            processInput = True
        self.lastClick = currentTime
        return processInput

    def toggleArm(self):
        print("Process arm movement here")


    def start_joy_thread(self):
        print("Starting Thread")
        self.ison = True
        Thread(target = self.joy_update).start()
        """
        Get the state of a button. This project uses the "Logitech Attack 3" which contains 11 physical buttons but are
        indexed 0-10
        :param button_num: Button number to get the state of
        :raises: ValueError if the given button number is not in the range of available buttons
        :rtype: int
        :return: 0 or 1 (1=button depressed)
        """

    def joy_update(self):
        while self.ison:
            #self.joy_y_val = self.joystick.get_axis
            #simple rotation
            if self.joystick.get_button_state(3) == 1: #Actually button labeled 4
                self.s0.setMaxSpeed(300)
                self.s0.relative_move(-2)

            if self.joystick.get_button_state(4) == 1: #Actually button labeled 5
                self.s0.setMaxSpeed(300)
                self.s0.relative_move(2)
            #stop
            if -0.2 < self.joystick.get_axis('x') < 0.2: # Stop At 0, contingent on the 0.2 bounds
                self.softstop()

            #auto, probably will break;
            if self.joystick.get_button_state(1) == 1 or self.joystick.get_button_state(2) == 1: #if either button labeled 3 or 2 is pressed
                cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)#set arm to up pos
                if self.magnetControl.text == 'Magnet Off': #magnet set to on
                    self.toggleMagnet()
                self.s0.setMaxSpeed(88)
                self.s0.relative_move(2)
                self.isbusy()
                if (cyprus.read_gpio() & 0b0010) == 0: #port 6 tall
                    self.s0.relative_move(-0.8)
                    self.isbusy()
                    sleep(1)
                    self.armDown()
                    self.armUp()
                    self.s0.relative_move(0.35)
                    self.armDown()
                    self.toggleMagnet()
                    self.armUp()
                    self.home()
                    self.toggleMagnet()



                elif (cyprus.read_gpio() & 0b0001) == 0: #port 7 short
                    self.s0.relative_move(-0.45)
                    self.isbusy()
                    sleep(1)
                    self.armDown()
                    self.armUp()
                    self.s0.relative_move(-0.35)
                    self.armDown()
                    self.toggleMagnet()
                    self.armUp()
                    self.home()
                    self.toggleMagnet()

            if self.joystick.get_button_state(0) == 1: #Trigger ButtonMagnet
                self.toggleMagnet()
                sleep(0.1)

            #leftright swivel
            if self.joystick.get_axis('x') > 0.2 or self.joystick.get_button_state(7):#BUTTON8
                self.softstop()
                print(self.joystick.get_axis('x'))
                for i in range(0,24):
                    self.s0.start_relative_move(0.3)
            if self.joystick.get_axis('x') < -0.2 or self.joystick.get_button_state(8):#button9
                self.softstop()
                print(self.joystick.get_axis('x'))
                for i in range(0,24):
                    self.s0.start_relative_move(-0.3)

            #piston updown

            if self.joystick.get_axis('y') > 0.5 or self.joystick.get_button_state(6): # button 7
                print("MovingUp")
                cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            if self.joystick.get_axis('y') < -0.5 or self.joystick.get_button_state(5): # button 6
                print("MovingDown")
                cyprus.set_pwm_values(1, period_value=100000, compare_value=100000, compare_mode=cyprus.LESS_THAN_OR_EQUAL)


        print('leaving thread...')

    def toggleMagnet(self): #turns magnet on and off
        if self.magnetControl.text == "Magnet Off":
            cyprus.set_servo_position(2, 0)
            self.magnetControl.text = "Magnet On"
            self.magnetControl.color = 0, 0, 1, 1
        elif self.magnetControl.text == "Magnet On":
            cyprus.set_servo_position(2, 0.5)
            self.magnetControl.color = 1, 0, 0, 1
            self.magnetControl.text = "Magnet Off"

    def softstop(self): #s0.softstop shortcut
        self.s0.softStop()

    def armDown(self):
        cyprus.set_pwm_values(1, period_value=100000, compare_value=100000, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
        sleep(0.8)
    def armUp(self):
        cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
        sleep(0.2)

    def tallStand(self):
        if (cyprus.read_gpio() & 0b0001) == 0: #port 7 which is short
            return True

    def shortStand(self):
        if (cyprus.read_gpio() & 0b0010) == 0:#port 6 which is tall
            return True

    def isbusy(self):

        while self.s0.isBusy() and self.ison == True:
                sleep(0.2)

    def togglearm(self):
        if self.armControl.text == 'Arm Up':
            self.armControl.text = 'Arm Down'
            self.armControl.color = 0,0,0,1
            self.armDown()
        elif self.armControl.text == 'Arm Down':
            self.armControl.text = 'Arm Up'
            self.armControl.color = 0,0,1,1
            self.armUp()

    def threadforarm(self):
        Thread(target = self.togglearm).start()


    def home(self):
        self.s0.relative_move(2)

    def homeArm(self):
        arm.home(self.homeDirection)


    def initialize(self):
        print("Home arm and turn off magnet")

    def resetColors(self):
        self.ids.armControl.color = YELLOW
        self.ids.magnetControl.color = YELLOW
        self.ids.auto.color = BLUE

    def quit(self):
        MyApp().stop()

    def threadautomatic(self):
        self.ison = False
        sleep(2)
        Thread(target = self.automatic).start()

    def maxspeed(self):
        self.s0.setMaxSpeed(100)

    def automatic(self): #{ERROR MESSAGE TypeError: 'kivy.weakproxy.WeakProxy' object is not callable } whydoes this happen and everything else works, this is the last thing to finish.
            self.s0.setMaxSpeed(100)
            self.s0.relative_move(2)
            if self.magnetControl.text == 'Magnet Off':
                self.toggleMagnet()
            if (cyprus.read_gpio() & 0b0010) == 0: #port 6 tall
                self.s0.relative_move(-0.8)
                sleep(0.3)
                self.armDown()
                self.armUp()
                self.s0.relative_move(0.35)
                self.armDown()
                self.toggleMagnet()
                self.armUp()
                self.home()



            elif (cyprus.read_gpio() & 0b0001) == 0: #port 7 short
                self.s0.relative_move(-0.45)
                sleep(0.3)
                self.armDown()
                self.armUp()
                self.s0.relative_move(-0.35)
                self.armDown()
                self.toggleMagnet()
                self.armUp()
                self.home()
            sleep(2)
            Thread(target=self.start_joy_thread).start()



sm.add_widget(MainScreen(name = 'main'))


# ////////////////////////////////////////////////////////////////
# //                          RUN APP                           //
# ////////////////////////////////////////////////////////////////

MyApp().run()
cyprus.close_spi()
