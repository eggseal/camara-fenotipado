"""Main module of the system"""

import threading
import time
import logging
import config
import requests

import adafruit_bh1750
import adafruit_dht
import adafruit_ltr390
import adafruit_tsl2561
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import board
import busio
import digitalio
from luma.core.interface.serial import i2c as lumaI2C
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont
import api
from data import data, states, photos_taken
from concurrent.futures import ThreadPoolExecutor

import utils
from modules.ax12 import Ax12
from modules.camera import CameraThread
from modules.survey3 import Survey3

# Pin I/O
i2c = busio.I2C(board.SCL, board.SDA)
DHT_PIN = board.D26
RE_CAMERA = digitalio.DigitalInOut(board.D23)
RGN_CAMERA = digitalio.DigitalInOut(board.D24)
WHITE_LIGHT = digitalio.DigitalInOut(board.D27)
UV_LIGHT = digitalio.DigitalInOut(board.D22)
IR_LIGHT = digitalio.DigitalInOut(board.D17)
START_BTN = digitalio.DigitalInOut(board.D5)
STOP_BTN = digitalio.DigitalInOut(board.D6)
DIR_SWITCH = digitalio.DigitalInOut(board.D12)

# Set directions
for pin in [RE_CAMERA, RGN_CAMERA, WHITE_LIGHT, UV_LIGHT, IR_LIGHT]:
    pin.direction = digitalio.Direction.OUTPUT
for pin in [START_BTN, STOP_BTN, DIR_SWITCH]:
    pin.direction = digitalio.Direction.INPUT
    pin.pull = digitalio.Pull.UP

# Constants
CAM_RGB_INDEX = 2
CAM_RGBT_INDEX = 0
CONNECTION_URL = f"http://127.0.0.1:{config.WIFI_PORT}/active"
CAM_SRC = "/media/sise"
CAM_SRC_RGN = "/media/sise/0000-00011/DCIM/Photo"
CAM_SRC_RE = "/media/sise/0000-0001/DCIM/Photo"
CAM_DEST = config.CAM_DEST
DXL_DEVICENAME = "/dev/ttyAMA0"
DXL_BAUDRATE = 1_000_000
DXL_ID = 1
DXL_SPEED = 50
MOTOR_STEPS = lambda: int(data.get(data.PHOTO_AMOUNT) or 11)
MOTOR_STEP_TIME = lambda: 13 / max(MOTOR_STEPS() - 1, 1) + 0.5
MOTOR_RESET_TIME = lambda: (MOTOR_STEPS() * MOTOR_STEP_TIME())
ANGLES = lambda: [round(i * (300 / (MOTOR_STEPS() - 1))) for i in range(MOTOR_STEPS())]
SENSOR_READ_TIME = 0.5
DISPLAY_UPDATE_TIME = 0.2
WIFI_CHECK_TIME = 5
TOTAL_CAMERAS = 4

# Class configuration
Ax12.DEVICENAME = DXL_DEVICENAME
Ax12.BAUDRATE = DXL_BAUDRATE
Ax12.connect()

# Library initialization
data.init_values(DIR_SWITCH, MOTOR_STEPS())
dxl = Ax12(DXL_ID)
dxl.set_moving_speed(DXL_SPEED)
dxl.set_goal_position(0)
dht = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)
try:
    pot = AnalogIn(ADS.ADS1115(i2c), ADS.P0)
except Exception as e:
    logging.warning("Potentiometer with ADS1115 not recognized. %s", e)
    pot = None
try:
    display = sh1106(lumaI2C(address=0x3C))
except Exception as e:
    logging.warning("Display SH1106 not recognized in I2C bus on address 0x3C. %s", e)
    display = None
display_font = ImageFont.load_default()

try:
    tsl = adafruit_tsl2561.TSL2561(i2c)
except ValueError:
    logging.warning("Sensor TSL2561 not recognized in I2C bus.")
    tsl = None
try:
    bh = adafruit_bh1750.BH1750(i2c)
except ValueError:
    logging.warning("Sensor BH1750 not recognized in I2C bus.")
    bh = None
try:
    ltr = adafruit_ltr390.LTR390(i2c)
except ValueError:
    logging.warning("Sensor LTR390 not recognized in I2C bus.")
    ltr = None
stop_event = threading.Event()
side_cam = CameraThread("RGB", CAM_RGB_INDEX, stop_event, 800, 600)
top_cam = CameraThread("RGBT", CAM_RGBT_INDEX, stop_event, 848, 480)
re_camera = Survey3(RE_CAMERA, "RE", CAM_SRC, CAM_DEST)
rgn_camera = Survey3(RGN_CAMERA, "RGN", CAM_SRC, CAM_DEST)

app = api.create(__name__)

# Variables
ap_conn = {"active": False, "ip": "", "port": 0}
times = {"rotation_start": 0.0, "sensor_read": 0.0, "process_start": 0.0}


# Thread functions
def start_api():
    """Start the Flask API server in a separate thread."""
    api.run(app, "0.0.0.0", config.API_PORT)


def read_sensor_data():
    """Read data from the sensors and update the global data dictionary."""
    has_dht = True
    dht_read = 0
    while not stop_event.is_set():
        try:
            dht.measure()
            if dht.temperature is None or dht.humidity is None:
                raise Exception("Succeeded reading. Read None")
            has_dht = True
        except Exception as e:
            if has_dht:
                logging.warning("Sensor DHT11 not recognized. %s", e)
            has_dht = False

        data.set(data.TEMP, dht.temperature, has_dht)
        data.set(data.HUM, dht.humidity, has_dht)
        data.set(data.WHITE_LUX, round(bh.lux, 1) if bh else -1)
        data.set(data.IR_LUX, round(tsl.infrared, 1) if tsl else -1)
        data.set(data.UV_LUX, round(ltr.uvi, 1) if ltr else -1)
        # data.set(data.ANGLE, pot.value)
        time.sleep(SENSOR_READ_TIME)


def connection_check():
    has_connection_server = True
    while not stop_event.is_set():
        try:
            res = requests.get(CONNECTION_URL)
            has_connection_server = True
        except Exception as e:
            if has_connection_server:
                logging.warning(f"Error checking connection: {e}")
                has_connection_server = False
            time.sleep(WIFI_CHECK_TIME)
            continue

        if res.status_code == 200:
            data = res.json()
            ap_conn["active"] = data["active_ap"]
            ap_conn["ip"] = data["ip"]
            ap_conn["port"] = data["port"]
        time.sleep(WIFI_CHECK_TIME)


def update_display():
    """Update the frame in the OLED display"""
    while not stop_event.is_set():
        if display is None:
            time.sleep(DISPLAY_UPDATE_TIME)
            continue

        field_mode = bh is None and tsl is None and ltr is None
        image = Image.new("1", (display.width, display.height))
        draw = ImageDraw.Draw(image)

        content = [
            f"AP: {config.AP_SSID if ap_conn['active'] else 'OFF'}",
            f"http://{ap_conn['ip']}:{ap_conn['port']}/" if ap_conn['active'] else "NO AP URL (OK)",
            f"Sentido: {'ANTIHORARIO' if states.get(states.DIRECTION) else 'HORARIO'}",
            f"Estado: {'ON' if data.get(data.RUNNING) else 'OFF'} | {data.get(data.PROGRESS)}%",
        ]
        line = display.height // len(content)

        for i in range(len(content)):
            draw.text((0, line * i), content[i], font=display_font, fill=255)
        display.display(image)
        time.sleep(DISPLAY_UPDATE_TIME)


# Functions
def update_progress(angle_index: int, prev_camera: int, completed=False):
    """Returns the current progress made based on number of steps and cameras
    Args:
        angle_index: The index of the current angle of the motor
        prev_camera: The number of the camera that took the last photo
    """
    if completed:
        data.set(data.PROGRESS, 100)
        logging.info("Forced progress to 100% after marked completed")
        return

    step = (
        angle_index
        if not states.get(states.DIRECTION)
        else MOTOR_STEPS() - angle_index - 1
    )
    data.set(
        data.PROGRESS,
        round(
            ((step / MOTOR_STEPS()) + (prev_camera / TOTAL_CAMERAS) / MOTOR_STEPS()) * 99
        ),
    )
    logging.info("Changed progress to %d%%", data.get(data.PROGRESS))


def toggle_lights(state_white: bool, state_ir: bool, state_uv: bool):
    """Toggle the state of all the lights
    Args:
        state_white: The new state of the white LEDs
        state_ir: The new state of the infrarred LEDs
        state_uv: The new state of the ultravioled LEDs
    """
    WHITE_LIGHT.value = state_white
    IR_LIGHT.value = state_ir
    UV_LIGHT.value = state_uv
    time.sleep(1)


def move_motor_next():
    """Order the motor to move to the next angle, update roation start time
    If it's moving to the starting position block the main thread and update starting time
    """
    dxl.set_moving_speed(DXL_SPEED)
    logging.info(f"{states.get(states.ANGLE)}")
    angle = ANGLES()[states.get(states.ANGLE)]
    logging.info(
        "Began moving towards %d° (%d in bytes).", angle, utils.degree_to_byte(angle)
    )
    dxl.set_goal_position(utils.degree_to_byte(angle))
    data.set(data.ANGLE, angle)

    times["rotation_start"] = time.time()
    if (states.get(states.ANGLE) == 0 or states.get(states.ANGLE) == MOTOR_STEPS() - 1) and data.get(data.PROGRESS) == 0:
        time.sleep(MOTOR_RESET_TIME())
        times["process_start"] = time.time()


def main():
    """Main function to handle the chamber operations."""
    new_start = utils.debounce_button(START_BTN, states.get(states.START))
    new_stop = utils.debounce_button(STOP_BTN, states.get(states.STOP))

    if data.get(data.RUNNING):
        data.set(data.RUNNING, not (new_stop and not states.get(states.STOP)))
    else:
        data.set(data.RUNNING, new_start and not states.get(states.START))

    if data.get(data.RUNNING):
        if states.get(states.ROTATED):
            move_motor_next()
            states.set(
                states.ROTATED, False
            )

        if time.time() - times["rotation_start"] > MOTOR_STEP_TIME():
            logging.info("Step %d / %d started.", states.get(states.ANGLE), MOTOR_STEPS())

            toggle_lights(True, False, False)
            logging.info("Taking RGB Side picture...")
            frame = side_cam.get_frame()
            photos_taken.add(photos_taken.SIDE, 1)
            if frame is not None:
                side_cam.save_image(
                    CAM_DEST, frame, times["process_start"], states.get(states.ANGLE)
                )
            update_progress(states.get(states.ANGLE), 1)

            logging.info("Taking RGB Top picture...")
            frame_top = top_cam.get_frame()
            photos_taken.add(photos_taken.TOP, 1)
            if frame_top is not None:
                top_cam.save_image(
                    CAM_DEST,
                    frame_top,
                    times["process_start"],
                    states.get(states.ANGLE),
                )
            update_progress(states.get(states.ANGLE), 2)

            logging.info("Taking RE and RGN pictures...")
            toggle_lights(False, True, False)
            # Attempt to read each camera 5 times max
            with ThreadPoolExecutor(max_workers=2) as ex:
                ex.submit(re_camera.attempt_read, 5)
                #ex.submit(rgn_camera.attempt_read, 5)
            # Add to the photos counter
            photos_taken.add(photos_taken.IR, 1)
            photos_taken.add(photos_taken.UV, 1)
            update_progress(states.get(states.ANGLE), 4)

            logging.info("Updating end of loop states...")
            states.set(states.TRANSFERRED, False)
            states.set(states.ROTATED, True)
            if states.get(states.DIRECTION):
                states.add(states.ANGLE, -1)
            else:
                states.add(states.ANGLE, 1)
            toggle_lights(False, False, False)

    completed_steps = (
        states.get(states.ANGLE) >= MOTOR_STEPS() or states.get(states.ANGLE) < 0
    )
    if not states.get(states.TRANSFERRED) and (
        completed_steps or not data.get(data.RUNNING)
    ):
        logging.info("Transferring %d images.", states.get(states.ANGLE))

        with ThreadPoolExecutor(max_workers=2) as ex:
            ex.submit(re_camera.attempt_set_mount, False, 5)
            #ex.submit(rgn_camera.attempt_set_mount, False, 5)

        re_camera.transfer_n(states.get(states.ANGLE), states.get(states.SESSION), times["process_start"])
        rgn_camera.transfer_n(states.get(states.ANGLE), states.get(states.SESSION), times["process_start"])
        re_camera.clear_sd()
        rgn_camera.clear_sd()

        with ThreadPoolExecutor(max_workers=2) as ex:
            ex.submit(re_camera.attempt_set_mount, True, 5)
            ex.submit(rgn_camera.attempt_set_mount, True, 5)

        update_progress(states.get(states.ANGLE), 4, True)
        states.set(states.ANGLE, 0)
        states.set(states.TRANSFERRED, True)
        data.set(data.RUNNING, False)

    states.set(states.START, new_start)
    states.set(states.STOP, new_stop)


if __name__ == "__main__":
    states.set(states.SESSION, utils.get_next_numeric_subdir(CAM_DEST))

    api_thread = threading.Thread(target=start_api, daemon=True)
    sensor_thread = threading.Thread(target=read_sensor_data, daemon=True)
    display_thread = threading.Thread(target=update_display, daemon=True)
    connection_thread = threading.Thread(target=connection_check, daemon=True)
    try:
        api_thread.start()
        sensor_thread.start()
        display_thread.start()
        connection_thread.start()
        side_cam.start()
        top_cam.start()
        while True:
            main()
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("Exiting program.")
    finally:
        stop_event.set()
        sensor_thread.join()
        display_thread.join()
        connection_thread.join()
        side_cam.release()
        top_cam.release()
        dxl.set_torque_enable(0)
        Ax12.disconnect()
        for pin in [RE_CAMERA, RGN_CAMERA, WHITE_LIGHT, UV_LIGHT, IR_LIGHT]:
            pin.value = False
