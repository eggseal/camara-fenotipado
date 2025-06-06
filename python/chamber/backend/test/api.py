import cv2
from flask import Flask, Response, request, jsonify
import threading
import time
import random
from dotenv import load_dotenv
import os
import base64
from collections import defaultdict

load_dotenv()

# Constants
CAM_RGB_INDEX = 0
# CAM_DEST = "/home/rpi4sise1/Desktop/pictures"
CAM_DEST = "./"
CAMERA_FPS = 15
API_PORT = int(os.getenv("API_PORT", "8000"))

# Library initialization
rgb_camera = cv2.VideoCapture(CAM_RGB_INDEX)
app = Flask(__name__)

# Variables
last_update = 0
last_picture = 0
data = {
    "temp": 0,
    "hum": 0,
    "white_lux": 0,
    "ir_lux": 0,
    "uv_lux": 0,
    "running": False,
    "direction": 0,
    "angle": 0,
    "progress": 0,
}
bogos_binted_w = 0
bogos_binted_i = 0
bogos_binted_u = 0

# Camera thread
frame_lock = threading.Lock()
stop_event = threading.Event()
current_frame: bytes = b""

data_lock = threading.Lock()

# Thread functions
def start_api():
    app.run(host="0.0.0.0", port=API_PORT, debug=False, use_reloader=False)

def generate_frames():
    while not stop_event.is_set():
        with frame_lock:
            ret, frame = rgb_camera.read()
        if not ret: continue

        _, buffer = cv2.imencode('.jpg', frame)
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
        )

def read_sensor_data():
    global data_lock, data, bogos_binted_i, bogos_binted_w, bogos_binted_u
    while not stop_event.is_set():
        with data_lock:
            data["temp"] = round(random.uniform(10, 40), 1)
            data["hum"] = round(random.uniform(20, 100), 1)
            data["white_lux"] = round(random.uniform(0, 1000), 1)
            data["ir_lux"] = round(random.uniform(0, 1000), 1)
            data["uv_lux"] = round(random.uniform(0, 14), 1)
            data["direction"] = random.choice([-1, 0, 1])
            data["angle"] = random.randint(0, 300)
            print(data)

            if data["progress"] == 0:
                bogos_binted_i = 0
                bogos_binted_w = 0
                bogos_binted_u = 0

            if data["running"]:
                data["progress"] += random.randint(0, 10)
            if data["progress"] > 100:
                data["progress"] = 100
            elif data["progress"] == 100:
                data["progress"] = 0
        time.sleep(0.5)

def save_rgb_image(frame, timestamp: float, step=0):
    filename = f"RGB-{time.strftime('%Y%m%d-%H%M%S', time.localtime(timestamp))}-step{step}.png"
    cv2.imwrite(f"{CAM_DEST}/{filename}", frame)

@app.route("/dashboard")
def serve_dashboard():
    with data_lock:
        return data

@app.route("/dashboard/photos")
def serve_photos():
    photos_dir = CAM_DEST

    # Define the limits per category
    category_limits = {
        "RGB": bogos_binted_w,
        "RGN": bogos_binted_u,
        "RE": bogos_binted_i
    }

    # Store photos per category
    categorized_files = defaultdict(list)

    try:
        # Filter only image files
        files = [f for f in os.listdir(photos_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

        # Categorize and sort by timestamp
        for f in files:
            parts = f.split("-")
            if len(parts) < 3:
                continue  # Skip bad format

            category = parts[0].upper()
            timestamp = parts[1] + "-" + parts[2]
            if category in category_limits:
                # Use timestamp as sort key
                categorized_files[category].append((timestamp, f))

        # Prepare payload
        photos_payload = []

        for category, items in categorized_files.items():
            # Sort by timestamp (descending) and take the last N
            items = sorted(items, key=lambda x: x[0], reverse=True)[:category_limits[category]]

            for _, file in items:
                full_path = os.path.join(photos_dir, file)
                with open(full_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                photos_payload.append({
                    "filename": file,
                    "content": encoded_string,
                    "content_type": "image/jpeg" if file.lower().endswith(".jpg") else "image/png"
                })

        response = {
            "photo_counts": category_limits,
            "photos": photos_payload
        }

        return jsonify(response)

    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/dashboard/<string:key>", methods=["POST"])
def update_dashboard_var(key):
    try:
        value = float(request.args.get("value", 0))
    except ValueError:
        return {"error": "Invalid value"}, 400

    if key in data:
        with data_lock:
            data[key] = value
            return {key: data[key]}
    return {"error": f"{key} not found"}, 404

@app.route("/video")
def serve_video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def main():
    global last_update, last_picture, bogos_binted_w
    
    process_start = time.time()
    if data["running"] and process_start - last_picture > 2:
        with frame_lock:
            ret, frame = rgb_camera.read()
        if ret:
            save_rgb_image(frame, process_start)
            bogos_binted_w += 1
        last_picture = process_start

if __name__ == "__main__":
    api_thread = threading.Thread(target=start_api, daemon=True)
    sensor_thread = threading.Thread(target=read_sensor_data, daemon=True)
    try:
        api_thread.start()
        sensor_thread.start()
        while True:
            main()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        stop_event.set()
        rgb_camera.release()
        os._exit(0)