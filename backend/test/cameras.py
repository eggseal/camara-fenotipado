import os
import time

import board
import cv2
import digitalio
from cv2 import VideoCapture
from cv2.typing import MatLike
from prompt_toolkit.application import Application, run_in_terminal
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl

import utils
from modules.survey3 import Survey3

# Pin I/O
RE_CAMERA_PIN = digitalio.DigitalInOut(board.D23)
RGN_CAMERA_PIN = digitalio.DigitalInOut(board.D24)

# Set pin directions
RE_CAMERA_PIN.direction = digitalio.Direction.OUTPUT
RGN_CAMERA_PIN.direction = digitalio.Direction.OUTPUT

# Constants
RGB_CAMERA_INDEX = 0
RGBTOP_CAMERA_INDEX = 2
SOURCE = "/media/sise"
SOURCE_RE = "/media/sise/0000-0001/DCIM/Photo"
SOURCE_RGN = "/media/sise/0000-00011/DCIM/Photo"
CAM_DEST = "/home/sise/Desktop/Fenotipado"
SEPARATOR = "="

# Variables
rgb_camera = VideoCapture(RGB_CAMERA_INDEX, cv2.CAP_V4L2)
rgb_cameratop = VideoCapture(RGBTOP_CAMERA_INDEX, cv2.CAP_V4L2)
re_camera = Survey3(RE_CAMERA_PIN, "RE", SOURCE, CAM_DEST)
rgn_camera = Survey3(RGN_CAMERA_PIN, "RGN", SOURCE, CAM_DEST)
process_start = 0
mount = True


# Functions
def save_rgb_image(prefix: str, frame: MatLike, timestamp: float, step=0):
    """Save the RGB image to the specified directory with a timestamp and step number.
    Args:
        prefix: The label of the image to identify the camera
        frame: The image frame to save.
        timestamp: The timestamp to use for the filename.
        step: The step number for the filename. Defaults to 0.
    """
    filename = utils.generate_photo_name(prefix, timestamp, step)
    dirpath = utils.get_session_dirpath(CAM_DEST, 999)
    cv2.imwrite(os.path.join(dirpath, filename), frame)  # pylint: disable=no-member


def trigger_picture():
    print("Triggering RE...")
    re_camera.attempt_read(5)
    print("Triggering RGN...")
    rgn_camera.attempt_read(5)
    time.sleep(3)
    print("Triggering RGB...")
    success, frame = rgb_camera.read()
    print("Triggering RGBT...")
    successtop, frametop = rgb_cameratop.read()
    if success:
        save_rgb_image("RGB", frame, time.time())
    if successtop:
        save_rgb_image("RGBT", frametop, time.time())


def mount_dismount():
    global mount

    mount = not mount
    print("Mounting RE" if mount else "Dismounting RE")
    re_camera.attempt_set_mount(mount, 5)
    time.sleep(1)
    # re_camera.toggle_mount()
    print("Mounting RGN" if mount else "Dismounting RGN")
    rgn_camera.toggle_mount()
    # rgn_camera.attempt_set_mount(mount, 5)
    time.sleep(3)


def transfer_images():
    print("Transferring RE")
    try:
        re_camera.transfer_latest()
    except Exception as e:
        print(f"Error tranferring RE: {e}")

    print("Transferring RGN")
    try:
        rgn_camera.transfer_latest()
    except Exception as e:
        print(f"Error tranferring RE: {e}")


cursor = 0
commands = [
    {"name": "Trigger picture", "run": trigger_picture},
    {"name": "Mount / Dismount", "run": mount_dismount},
    {"name": "Transfer images", "run": transfer_images},
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
        re_camera.set_mount(True)
        rgn_camera.set_mount(True)
