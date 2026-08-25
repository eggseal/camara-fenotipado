import logging
import shutil
import time
from os import listdir, path, remove

import digitalio

from utils import generate_photo_name, get_session_dirpath, safe_copy

logging.basicConfig(
    format=(
        "\033[90m%(asctime)s\033[0m "
        + "[\033[36m%(levelname)s\033[0m] "
        + "[\033[33m%(module)s::%(funcName)s\033[0m] "
        + "%(message)s"
    ),
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)


class Pulse:
    DO_NOTHING = 0.001
    TAKE_PHOTO = 0.002
    TRANSFER = 0.0015


class Survey3:
    def __init__(self, pin: digitalio.DigitalInOut, cam_id: str, base_origin: str, dest: str):
        self.pin = pin
        self.base_origin = base_origin
        self.dest = dest
        self.id = cam_id
        self.pin.direction = digitalio.Direction.OUTPUT
        self.pin.value = False
        self.set_mount(True)

    def set_mount(self, to_mount: bool):
        # When to_mount is True, it ensures the SD becomes not accessible
        origin = self.get_origin()
        origin_exists = path.isdir(origin) if origin is not None else False
        # Mounted means the origin path should not be accessible
        if to_mount and origin_exists:
            logging.warning("Origin for camera %s accessible. Mounting back.", self.id)
            self.toggle_mount()
            return True
        # Dismounted means origin should exist
        if not to_mount and not origin_exists:
            logging.warning("Origin for camera %s not accessible. Dismounting.", self.id)
            self.toggle_mount()
            return True
        return False

    def get_origin(self):
        try:
            drives = listdir(self.base_origin)
        except Exception:
            return None

        for drive in drives:
            drive_path = path.join(self.base_origin, drive)
            if not path.isdir(drive_path):
                continue

            marker = path.join(drive_path, f"{self.id}.txt")
            if not path.isfile(marker):
                continue

            photo_path = path.join(drive_path, "DCIM", "Photo")
            if path.isdir(photo_path):
                return photo_path
        return None

    def pulse(self, pulse: float):
        self.pin.value = True
        time.sleep(pulse)
        self.pin.value = False
        time.sleep(0.1)

    def read(self):
        logging.info(f"Triggering {self.id}")
        self.pulse(Pulse.DO_NOTHING)
        self.pulse(Pulse.TAKE_PHOTO)
        self.pulse(Pulse.DO_NOTHING)
        time.sleep(1)

    def toggle_mount(self):
        logging.info(f"Toggling mount for {self.id}")
        self.pulse(Pulse.DO_NOTHING)
        self.pulse(Pulse.TRANSFER)
        self.pulse(Pulse.DO_NOTHING)
        time.sleep(1)

    def attempt_read(self, attempts: int = 1):
        if attempts <= 0:
            return

        for _ in range(attempts):
            if self.set_mount(True): 
                time.sleep(2) # If the SD was actually dismounted, wait 2 extra seconds for it to mount
            if self.set_mount(True): 
                time.sleep(2)
                continue # If the SD was actually dismounted again, restart the loop without trying to read yet, if this time it was mounted proceed to reading

            self.read()
            time.sleep(2)
            if not self.set_mount(True): 
                return # If after reading the SD is still mounted it assumes it read correctly the image

    def attempt_set_mount(self, mount: bool, attempts: int = 1):
        if attempts <= 0:
            return

        for _ in range(attempts):
            changed = self.set_mount(mount) # If the SD is in the opposite state, order it to change
            if changed: time.sleep(2) # If the SD was actually in the opposite state, wait 2 extra seconds for it to change
            if not self.set_mount(mount): break # If after receiving the change order its in the correct state it assumes it toggled correctly

    def transfer_latest(self):
        origin = self.get_origin()
        if origin is None or not path.exists(origin):
            logging.error("Origin not available for camera %s", self.id)
            return False

        latest = None
        for file in listdir(origin):
            name = path.join(origin, file)
            if not path.isfile(name):
                continue
            if latest is None or path.getctime(name) > path.getctime(latest):
                latest = name
        if latest is None:
            logging.error("No files found in %s.", origin)
            return False

        safe_copy(
            latest, path.join(self.dest, generate_photo_name(self.id, time.time(), 0))
        )
        remove(latest)
        return True

    def transfer_n(self, n: int, session: int, timestamp: float = 0):
        if timestamp == 0:
            timestamp = time.time()

        origin = self.get_origin()
        if origin is None or not path.exists(origin):
            logging.error("Origin not available for camera %s", self.id)
            return False

        files = [
            f
            for f in listdir(origin)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        files = sorted(
            files, key=lambda x: path.getctime(path.join(origin, x)), reverse=True
        )

        if len(files) < n:
            logging.error(
                "Not enough files found in %s. Expected %d, found %d",
                origin,
                n,
                len(files),
            )
            return False

        for i, file in enumerate(files[:n]):
            src = path.join(origin, file)
            dst = path.join(
                get_session_dirpath(self.dest, session),
                generate_photo_name(self.id, timestamp, i),
            )

            safe_copy(src, dst)
            remove(src)

        return True

    def clear_sd(self):
        origin = self.get_origin()
        if origin is None or not path.exists(origin):
            logging.error("Origin not available for camera %s", self.id)
            return False

        for file in listdir(origin):
            name = path.join(origin, file)
            if not path.isfile(name):
                continue

            try:
                remove(name)
            except Exception as e:
                logging.error("Failed to remove %s: %s", name, str(e))
        return True
