import time
import carrier
import machine
import math
from machine import Pin, SPI, ADC
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY, PEN_P4

# ================== DISABLE RGB LED PINS ==================
# Pico Display uses GPIO6, GPIO7, GPIO8 for RGB LEDs.
# Since GPIO8 is used by CC2500 MISO, we lock them as inputs.
for pin in [6, 7, 8]:
    machine.Pin(pin, machine.Pin.IN)
# ==========================================================

#-------------- Screen Functions --------------

def setup_screen():
    display = PicoGraphics(display=DISPLAY_PICO_DISPLAY, pen_type=PEN_P4, rotate=0)
    display.set_backlight(1)
    display.set_font("bitmap8")
    
    class color:
        WHITE = display.create_pen(255, 255, 255)
        BLACK = display.create_pen(0, 0, 0)
        CYAN = display.create_pen(0, 255, 255)
        MAGENTA = display.create_pen(255, 0, 255)
        YELLOW = display.create_pen(255, 255, 0)
        GREEN = display.create_pen(0, 255, 0)
        GREEN2 = display.create_pen(0, 255, 135)
        RED = display.create_pen(255, 0, 0)
        
    #Intro Animation
    clear(display,color)
    """
    display.set_pen(color.GREEN)
    display.circle(90, 30, 30)
    display.set_pen(color.BLACK)
    display.circle(90, 30, 25)
    display.set_pen(color.GREEN)
    display.circle(90, 30, 20)
    display.set_pen(color.BLACK)
    display.circle(90, 30, 15)
    display.rectangle(85, 35, 50, 75)
    display.rectangle(0, 0, 150, 40)
    display.update()
    time.sleep_ms(200)


    display.update()
    time.sleep_ms(200)
    """
    #CIRCLE EN BAS
    display.set_pen(color.GREEN)
    display.circle(42, 110, 20)
    display.set_pen(color.BLACK)
    display.circle(42, 110, 15)
    display.rectangle(0, 60, 50, 75)
    display.rectangle(42, 103, 50, 34)
    display.set_pen(color.GREEN)
    display.circle(90, 30, 20)
    display.set_pen(color.BLACK)
    display.circle(90, 30, 15)
    display.rectangle(85, 35, 50, 75)
    display.rectangle(0, 0, 150, 40)
    display.update()
    display.update()
    time.sleep_ms(50)

    display.set_pen(color.GREEN)
    display.circle(42, 110, 30)
    display.set_pen(color.BLACK)
    display.circle(42, 110, 25)
    display.set_pen(color.GREEN)
    display.circle(42, 110, 20)
    display.set_pen(color.BLACK)
    display.circle(42, 110, 15)
    display.rectangle(0, 60, 50, 75)
    display.rectangle(42, 103, 50, 34)
    display.set_pen(color.GREEN)
    display.circle(90, 30, 30)
    display.set_pen(color.BLACK)
    display.circle(90, 30, 25)
    display.set_pen(color.GREEN)
    display.circle(90, 30, 20)
    display.set_pen(color.BLACK)
    display.circle(90, 30, 15)
    display.rectangle(85, 35, 50, 75)
    display.rectangle(0, 0, 150, 40)
    display.update()
    time.sleep_ms(50)

    display.set_pen(color.GREEN)
    display.circle(42, 110, 40)
    display.set_pen(color.BLACK)
    display.circle(42, 110, 35)
    display.set_pen(color.GREEN)
    display.circle(42, 110, 30)
    display.set_pen(color.BLACK)
    display.circle(42, 110, 25)
    display.set_pen(color.GREEN)
    display.circle(42, 110, 20)
    display.set_pen(color.BLACK)
    display.circle(42, 110, 15)
    display.rectangle(0, 60, 50, 75)
    display.rectangle(42, 103, 50, 34)
    display.set_pen(color.GREEN)
    display.circle(90, 30, 40)
    display.set_pen(color.BLACK)
    display.circle(90, 30, 35)
    display.set_pen(color.GREEN)
    display.circle(90, 30, 30)
    display.set_pen(color.BLACK)
    display.circle(90, 30, 25)
    display.set_pen(color.GREEN)
    display.circle(90, 30, 20)
    display.set_pen(color.BLACK)
    display.circle(90, 30, 15)
    display.rectangle(85, 35, 50, 75)
    display.rectangle(0, 0, 150, 40)
    display.update()
    time.sleep_ms(50)
    
    #autre trucs
    display.set_pen(color.GREEN)
    display.line(42, 110, 42, 20, 5)
    display.update()
    time.sleep_ms(100)
    display.circle(42, 25, 8)
    display.set_pen(color.BLACK)
    display.circle(42, 25, 5)
    display.update()
    time.sleep_ms(50)
    
    display.set_pen(color.GREEN)
    display.line(15, 110, 225, 110, 5)
    display.set_pen(color.WHITE)
    display.text("HUMANSCATTER", 100, 90, 240, 2)
    display.update()
    time.sleep_ms(200)
    
    #Set Up main UI
    clear(display,color)
    display.set_pen(color.GREEN)
    display.line(142, 0, 142, 25, 3)
    display.line(0, 25, 240, 25, 2)
    display.set_pen(color.GREEN2)
    display.text("HUMANSCATTER", 10, 2, 240, 2)
    display.text("RSSI", 152, 2, 240, 2)
    display.update()

    return(display, color)

def clear(display, color):
    display.set_pen(color.BLACK)
    display.clear()
    display.update()

def clear_text(display, color):
    display.set_pen(color.BLACK)
    display.rectangle(0, 30, 240, 105)
    display.rectangle(195, 2, 45, 20)
    display.update()


def print_msg(display, message, color):
    clear_text(display,color)
    display.set_pen(color.WHITE) #White Pen
    display.text(message.data, 5, 35, 235, 2)
    display.text(str(message.RSSI), 195, 2, 235, 2)
    display.update()

def print_waiting(display, message, color):
    clear_text(display,color)
    display.set_pen(color.CYAN) #White Pen
    display.text("message pending", 10, 50, 240, 3)
    display.update()

def print_carrier_timeout(display, color):
    clear(display,color)
    display.set_pen(color.RED) #Yellow Pen
    display.triangle(80, 70, 160, 70, 120, 0)
    display.set_pen(color.YELLOW) #Yellow Pen
    display.triangle(90, 65, 150, 65, 120, 13)
    display.set_pen(color.RED) #Red Pen
    display.text("CARRIER STOP", 3, 80, 240, 4)
    display.text('!', 118, 21, 240, 6)
    display.set_pen(color.WHITE) #White Pen
    display.text("restart the device", 30, 115, 235, 2)
    display.update()
