import os
import subprocess
import threading
import time
import requests

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

AP_SSID = os.environ["AP_SSID"]
AP_PASSWORD = os.environ["AP_PASS"]
WIFI_INTERFACE = os.environ["WIFI_INTER"]
FLASK_PORT = int(os.environ["WIFI_PORT"])

app = Flask(__name__)
flask_started = False


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


class AP:
    started = False
    conn_uuid = None
    lock = threading.Lock()

    @classmethod
    def start(cls):
        print("Starting AP")
        with cls.lock:
            if cls.started:
                return

            result = run([
                "nmcli", "-t", "-f", "UUID", "dev", "wifi", "hotspot", 
                "ifname", WIFI_INTERFACE,
                "ssid", AP_SSID,
                "password", AP_PASSWORD,
            ])

            if result.returncode != 0:
                print(result.stderr)
                return

            cls.conn_uuid = result.stdout.strip()
            cls.started = True

    @classmethod
    def stop(cls):
        with cls.lock:
            if not cls.started or not cls.conn_uuid:
                return

            run(["nmcli", "connection", "down", cls.conn_uuid])
            cls.conn_uuid = None
            cls.started = False


def is_wifi_connected():
    try:
        res = requests.get("https://www.google.com", timeout=5)
        return True
    except Exception as e:
        logging.warning(f"Error checking connection: {e}")
        return False


def wait_for_wifi(timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        if is_wifi_connected():
            return True
        time.sleep(1)
    return False


def get_ap_ip():
    result = run(["nmcli", "-t", "-f", "IP4.ADDRESS", "device", "show", WIFI_INTERFACE])

    for line in result.stdout.splitlines():
        if line.startswith("IP4.ADDRESS"):
            return line.split(":")[1].split("/")[0]

    return None


def run_flask():
    global flask_started
    flask_started = True

    while True:
        ap_ip = get_ap_ip()
        if ap_ip:
            break
        time.sleep(1)

    app.run(
        host="0.0.0.0",
        port=FLASK_PORT,
        debug=False,
        use_reloader=False,
    )


@app.route("/")
def index():
    return render_template(
        "index.html",
        ap_ssid=AP_SSID,
        ap_ip=get_ap_ip(),
    )


@app.route("/active")
def active():
    return jsonify({ "active": AP.started, "ip": get_ap_ip(), "port": FLASK_PORT })


@app.route("/wifi-cred", methods=["POST"])
def wifi_cred():
    ssid = request.form.get("ssid")
    password = request.form.get("pass")

    if not ssid or not password:
        return jsonify({"msg": "Missing SSID or password"}), 400

    result = run([
        "nmcli",
        "dev",
        "wifi",
        "connect",
        ssid,
        "password",
        password,
        "wifi-sec.key-mgmt",
        "wpa-psk"
    ])
    if result.returncode != 0:
        return jsonify({"msg": result.stderr.strip()}), 500

    if not wait_for_wifi():
        return jsonify({"msg": "Failed to connect to Wi-Fi"}), 500

    try:
        return jsonify({"msg": "Wi-Fi changed"})
    finally:
        AP.stop()


def main():
    global flask_started
    disconnected_since = None

    print("Starting loop")
    while True:
        print("Waiting...")
        time.sleep(30)

        if is_wifi_connected():
            print("WiFi is connected")
            disconnected_since = None
            continue

        if disconnected_since is None:
            print("WiFi is disconnected")
            disconnected_since = time.time()
            continue

        if time.time() - disconnected_since > 30:
            print("Starting service")
            AP.start()


if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
