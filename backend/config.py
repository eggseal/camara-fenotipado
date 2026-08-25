import logging
import os

from dotenv import load_dotenv

load_dotenv()

API_PORT = 5000 # int(os.getenv("API_PORT", "5000"))
CAM_DEST = "/results" # os.getenv("CAM_DEST", "/home/sise/Desktop/Fenotipado")
AP_SSID = os.environ["AP_SSID"]
WIFI_PORT = int(os.environ["WIFI_PORT"])

logging.basicConfig(
    format=(
        "\033[90m%(asctime)s\033[0m [\033[36m%(levelname)s\033[0m] [\033[33m%(module)s::%(funcName)s\033[0m] %(message)s"
    ),
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)
