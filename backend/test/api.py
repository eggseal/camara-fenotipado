import base64
import logging
import os
import random
import threading
import time

import cv2
from flask import jsonify

import config
from backend import api, utils
from data import data, photos_taken, states
from modules.camera import CameraThread

# Constants
CAM_RGB_INDEX = 0
CAM_RGBT_INDEX = 2
CAM_DEST = config.CAM_DEST
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240
CAMERA_FPS = 10
API_PORT = config.API_PORT
SENSOR_READ_TIME = 1

app = api.create(__name__)

# Shared data
stop_event = threading.Event()
side_cam = CameraThread("RGB", CAM_RGB_INDEX, stop_event, 800, 600)
top_cam = CameraThread("RGBT", CAM_RGBT_INDEX, stop_event, 848, 480)


@app.route("/dashboard/photos")
def serve_photos():
    """Get all the photos taken on the last execution
    Returns:
        dict: All the photo contents stored by all cameras
    """

    photos_dir = utils.get_session_dirpath(CAM_DEST, states.get(states.SESSION))
    formats = (".jpg", ".jpeg", ".png")
    limits = {
        "RGBT": photos_taken.get(photos_taken.TOP),
        "RGB": photos_taken.get(photos_taken.SIDE),
        "RGN": photos_taken.get(photos_taken.UV),
        "RE": photos_taken.get(photos_taken.IR),
    }
    photos = {
        "RGBT": [],
        "RGB": [],
        "RGN": [],
        "RE": [],
    }
    if not states.get(states.TRANSFERRED):
        return jsonify({"photo_counts": limits, "photos": photos, "completed": False})

    # Get all image files and sort them newest to oldest
    files = [file for file in os.listdir(photos_dir) if file.lower().endswith(formats)]
    files.sort(
        key=lambda file: os.path.getctime(os.path.join(photos_dir, file)), reverse=True
    )

    if len(files) == 0:
        logging.error("Tried serving photos via API but there's none stored.")
        return jsonify({"photo_counts": limits, "photos": photos, "completed": True})

    latest_timestamp = utils.extract_photo_name(files[0])[1]
    logging.debug(
        "Latest timestamp found is [%s]. Found %d files.", latest_timestamp, len(files)
    )
    for file in files:
        label, timestamp, step, ext = utils.extract_photo_name(file)
        if timestamp != latest_timestamp:
            continue

        if label not in photos:
            logging.warning("Found a file with an unrecognized label: %s", file)
            continue

        full_path = os.path.join(photos_dir, file)
        with open(full_path, "rb") as image_file:
            content = base64.b64encode(image_file.read()).decode("utf-8")
        utils.insert_array_padded(
            photos[label],
            int(step),
            {
                "filename": file,
                "content": content,
                "content_type": "image/jpeg" if ext == "jpg" else "image/png",
            },
        )

    return jsonify({"photo_counts": limits, "photos": photos, "completed": True})


def save_rgb_image(prefix, frame, timestamp: float, step=0):
    filename = f"{prefix}-{time.strftime('%Y%m%d-%H%M%S', time.localtime(timestamp))}-{step}.png"
    cv2.imwrite(os.path.join(CAM_DEST, filename), frame)


def read_sensor_data():
    """Read data from the sensors and update the global data dictionary."""
    while not stop_event.is_set():
        data.set(data.TEMP, round(random.uniform(10, 40), 1))
        data.set(data.HUM, round(random.uniform(20, 100), 1))
        data.set(data.WHITE_LUX, round(random.uniform(0, 1000), 1))
        data.set(data.IR_LUX, round(random.uniform(0, 1000), 1))
        data.set(data.UV_LUX, round(random.uniform(0, 14), 1))
        data.set(data.ANGLE, random.randint(0, 300))

        if data.get(data.PROGRESS) == 0 and not data.get(data.RUNNING):
            photos_taken.set(photos_taken.SIDE, 0)
            photos_taken.set(photos_taken.TOP, 0)
            photos_taken.set(photos_taken.IR, 0)
            photos_taken.set(photos_taken.UV, 0)

        if data.get(data.RUNNING):
            data.set(data.PROGRESS, data.get(data.PROGRESS) + 10)

        if data.get(data.PROGRESS) > 100:
            data.set(data.PROGRESS, 0)
            data.set(data.RUNNING, False)
        time.sleep(SENSOR_READ_TIME)


process_start = 0


def main_loop():
    global photos_taken, last_update, last_picture, process_start
    last_picture = 0
    local_start = process_start
    steps = 0

    while not stop_event.is_set():
        if local_start != process_start:
            steps = 0
            local_start = process_start

        if data.get(data.RUNNING) and time.time() - last_picture > 2:
            frame = side_cam.get_frame()
            frame_top = top_cam.get_frame()

            if frame is not None:
                save_rgb_image("RGB", frame, process_start, steps)
            photos_taken.add(photos_taken.SIDE, 1)

            if frame_top is not None:
                save_rgb_image("RGBT", frame_top, process_start, steps)
            photos_taken.add(photos_taken.TOP, 1)

            last_picture = time.time()
            steps += 1

        time.sleep(0.1)


if __name__ == "__main__":
    sensor_thread = threading.Thread(target=read_sensor_data, daemon=True)
    main_thread = threading.Thread(target=main_loop, daemon=True)
    sensor_thread.start()
    main_thread.start()
    try:
        app.run("0.0.0.0", API_PORT)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        stop_event.set()
        side_cam.release()
        top_cam.release()
        os._exit(0)
