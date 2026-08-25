"""Helper functions used on the main module"""

import logging
import os
import shutil
import time
import zipfile
from io import BytesIO

import digitalio

import config


def generate_photo_name(prefix: str, timestamp: float, step: int) -> str:
    """Return a string representation of the photo data with camera label, time and step
    Args:
        prefix: The label to identify the camera type
        timestamp: The unix time in which the process of the photo started
        step: The index of the angle in which the photo was taken
    Returns:
        All the data stored in a string filename (PNG) "RGB-20251119_013323-4.png"
    """
    time_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(timestamp))
    return f"{prefix}-{time_str}-{step}.jpg"


def extract_photo_name(name: str):
    """Extract data from the image names created in save_rgb_image function.
    Args:
        name: The file name
    """
    label, timestamp, end = name.split("-")
    step, extension = end.split(".")
    return (label, timestamp, step, extension)


def insert_array_padded(array: list, index: int, item) -> list:
    """Inserts an item in a list in any position, padding with None if out of range.
    Args:
        array: The list to modify
        index: The position to insert the item on
        item: The item to put on the list
    Returns
        The modified list
    """
    if index >= len(array):
        array.extend([None] * (index + 1 - len(array)))
    array[index] = item
    return array


def degree_to_byte(degree: int) -> int:
    """Convert a degree value to a byte value for the servo motor.
    Args:
        degree: The degree value to convert.
    Returns:
        The converted byte value, clamped between 0 and 1023.
    """
    return min(max(degree * 1023 // 300, 0), 1023)


def debounce_button(digital_pin: digitalio.DigitalInOut, old_state: bool) -> bool:
    """Debounce a button press to avoid false triggers.
    Args:
        pin: The pin connected to the button.
        old_state: The previous state of the button.
    Returns:
        The new state of the button if it has changed, otherwise returns the old state.
    """
    if digital_pin.value != old_state:
        time.sleep(0.05)
        return digital_pin.value
    return old_state


def get_next_numeric_subdir(base_dir: str) -> int:
    """Reads the destination directory, parses all the stored sessions and gets the largest +1
    Args:
        base_dir: The base directory where all the numeric directories are
    Returns:
        int: The number of the next directory
    """
    max_num = -1
    for name in os.listdir(base_dir):
        full = os.path.join(base_dir, name)
        if not os.path.isdir(full):
            continue

        if not name.isdigit():
            continue
        number = int(name)
        max_num = max(number, max_num)

    return max_num + 1


def get_session_dirpath(base: str, session: int) -> str:
    """Builds the full path of the session directory based on the number. Creates it if needed
    Args:
        base: The base directory where all the numeric directories are
        session: The number of the session you're looking for
    Returns:
        str: The full path of the session
    """
    dirpath = os.path.join(base, str(session).zfill(8))
    os.makedirs(dirpath, exist_ok=True)
    return dirpath


def zip_dir(dirpath: str) -> BytesIO:
    mem = BytesIO()

    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zip:
        for root, _, files in os.walk(dirpath):
            for file in files:
                filepath = os.path.join(root, file)
                relative = os.path.relpath(filepath, dirpath)
                zip.write(filepath, relative)

    mem.seek(0)
    return mem


def safe_copy(src: str, dest: str, chunk: int = 64 * 1024) -> bool:
    # Retry 3 times
    for _ in range(3):
        try:
            shutil.copy2(src, dest)
            return True
        except (OSError, IOError) as e:
            logging.warning("Failed copying %s: %s", src, str(e))
            os.remove(dest)

        try:
            with open(src, "rb") as file_src, open(dest, "wb") as file_dest:
                while True:
                    buffer = file_src.read(chunk)
                    if not buffer:
                        break
                    file_dest.write(buffer)
            return True
        except (OSError, IOError) as e:
            logging.error("Failed manually copying %s: %s", src, str(e))
            os.remove(dest)

        time.sleep(0.5)
    return False
