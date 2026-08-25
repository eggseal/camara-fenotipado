import time

import adafruit_bh1750
import adafruit_dht
import adafruit_ltr390
import adafruit_tsl2561
import board
import busio
import digitalio
from prompt_toolkit.application import Application, run_in_terminal
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl

from modules.ax12 import Ax12

# Pin I/O
i2c = busio.I2C(board.SCL, board.SDA)
DHT_PIN = board.D7
LED_W = digitalio.DigitalInOut(board.D27)
LED_R = digitalio.DigitalInOut(board.D22)
LED_U = digitalio.DigitalInOut(board.D17)
SWITCH_PIN = digitalio.DigitalInOut(board.D5)
BUTTON_PIN = digitalio.DigitalInOut(board.D6)

# Set pin directions
for pin in [LED_W, LED_R, LED_U]:
    pin.direction = digitalio.Direction.OUTPUT
    pin.value = False

for pin in [SWITCH_PIN, BUTTON_PIN]:
    pin.direction = digitalio.Direction.INPUT
    pin.pull = digitalio.Pull.UP

# Class configuration
Ax12.DEVICENAME = "/dev/ttyAMA0"
Ax12.BAUDRATE = 1_000_000
Ax12.connect()

# Constants
MOTOR_ID = 1
MOTOR_SPEED = 100
SEPARATOR = "="

# Variables
bh1750 = adafruit_bh1750.BH1750(i2c)
ltr390 = adafruit_ltr390.LTR390(i2c)
tsl2561 = adafruit_tsl2561.TSL2561(i2c)
dht = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)
dxl = Ax12(MOTOR_ID)
dxl.set_moving_speed(MOTOR_SPEED)
led_w = False
led_r = False
led_u = False


def read_bh1750():
    lux = bh1750.lux
    if lux is not None:
        print(f"Light Level: {lux:.2f} lux")
    else:
        print("Failed to read from BH1750 sensor!")


def read_ltr390():
    uv = ltr390.uvi
    if uv is not None:
        print(f"Light Level: {uv:.2f} lux")
    else:
        print("Failed to read from LTR390 sensor!")


def read_tsl2561():
    ir = tsl2561.infrared
    if ir is not None:
        print(f"Light Level: {ir:.2f} lux")
    else:
        print("Failed to read from TSL2561 sensor!")


def read_dht():
    try:
        dht.measure()
    except RuntimeError as e:
        print(f"DHT Sensor error: {e}")

    temp = dht.temperature
    hum = dht.humidity
    if hum is not None and temp is not None:
        print(f"Temperature: {temp:.1f} C, Humidity: {hum:.1f} %")
    else:
        print("Failed to read from DHT sensor!")

def toggle_white():
    global led_w
    led_w = not led_w
    LED_W.value = led_w
    print(f"White LEDs are {led_w}")


def toggle_ir():
    global led_r
    led_r = not led_r
    LED_R.value = led_r
    print(f"IR LEDs are {led_r}")


def toggle_uv():
    global led_u
    led_u = not led_u
    LED_U.value = led_u
    print(f"UV LEDs are {led_u}")

def toggle_state(pin, message):
    pin.value = not pin.value
    print(message.format(value=pin.value))


def move_dynamixel():
    angle = int(input("Angle: "))
    pos = min(max(int(angle) * 1023 // 300, 0), 1023)
    dxl.set_goal_position(pos)
    print(f"Moved dynamixel to {angle}")


cursor = 0
commands = [
    {"name": "BH1750 | White Light", "run": read_bh1750},
    {"name": "TSL2561 | IR Light", "run": read_tsl2561},
    {"name": "LTR390 | UV Light", "run": read_ltr390},
    {
        "name": "White LEDs",
        "run": lambda: toggle_white(),
    },
    {"name": "IR LEDs", "run": lambda: toggle_ir()},
    {"name": "UV LEDs", "run": lambda: toggle_uv()},
    {"name": "Button", "run": lambda: print(f"Button is {BUTTON_PIN.value}")},
    {"name": "Switch", "run": lambda: print(f"Switch is {SWITCH_PIN.value}")},
    {"name": "DHT22 | Temperature & Humidity", "run": read_dht},
    {"name": "AX12 | Dynamixel Motor", "run": move_dynamixel},
    {"name": "Exit", "run": lambda: app.exit()},
]


def render():
    lines = []
    width = max(len(cmd["name"]) for cmd in commands) + 4
    lines.append(("", (SEPARATOR * width) + "\n"))
    for i, cmd in enumerate(commands):
        marker = "[O]" if i == cursor else "[ ]"
        lines.append(("", f"{marker} {cmd['name']}\n"))
    return lines


text = FormattedTextControl(render)
window = Window(content=text)
kb = KeyBindings()


@kb.add("up")
def _(_):
    global cursor
    cursor = max(0, cursor - 1)


@kb.add("down")
def _(_):
    global cursor
    cursor = min(len(commands) - 1, cursor + 1)


@kb.add("enter")
def _(_):
    command = commands[cursor]
    run_in_terminal(command["run"])


app = Application(
    layout=Layout(window),
    key_bindings=kb,
    full_screen=False,
)

if __name__ == "__main__":
    try:
        app.run()
    finally:
        dxl.set_torque_enable(0)
        Ax12.disconnect()
