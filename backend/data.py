import threading

import digitalio

import config, utils


class DataManager:
    def __init__(self, data: dict) -> None:
        self.lock = threading.Lock()
        self.data = data

    def get(self, key: str):
        with self.lock:
            return self.data[key]

    def set(self, key, value, use_value: bool = True):
        with self.lock:
            if self.is_key(key):
                self.data[key] = value if use_value else 0
            return self.is_key(key)

    def add(self, key, value):
        original = self.get(key)
        return self.set(key, original + value)

    def is_key(self, key: str):
        return key in self.data

    def get_data(self):
        with self.lock:
            return dict(self.data)


class Data(DataManager):
    TEMP = "temp"
    HUM = "hum"
    WHITE_LUX = "white_lux"
    IR_LUX = "ir_lux"
    UV_LUX = "uv_lux"
    RUNNING = "running"
    ANGLE = "angle"
    PROGRESS = "progress"
    PHOTO_AMOUNT = "photo_amount"
    initialized = False

    def set(self, key, value, use_value: bool = True):
        if key == Data.RUNNING and value == 1 and not self.get(Data.RUNNING):
            self.run_pre_session()
        if key == Data.PHOTO_AMOUNT and self.get(Data.RUNNING) == 1:
            return True
        return super().set(key, value, use_value)

    def init_values(self, dir_switch: digitalio.DigitalInOut, motor_steps: int):
        self.dir_switch = dir_switch
        self.motor_steps = motor_steps
        self.initialized = True

    def run_pre_session(self):
        print("Presession")
        if not self.initialized:
            return
        states.set(states.SESSION, utils.get_next_numeric_subdir(config.CAM_DEST))
        states.set(
            states.DIRECTION,
            0 #utils.debounce_button(self.dir_switch, states.get(states.DIRECTION)),
        )
        data.set(data.PROGRESS, 0)
        if states.get(states.DIRECTION):
            states.set(states.ANGLE, self.motor_steps - 1)


data = Data(
    {
        Data.TEMP: 0,
        Data.HUM: 0,
        Data.WHITE_LUX: 0,
        Data.IR_LUX: 0,
        Data.UV_LUX: 0,
        Data.RUNNING: False,
        Data.ANGLE: 0,
        Data.PROGRESS: 0,
        Data.PHOTO_AMOUNT: 11,
    }
)


class State(DataManager):
    START = "start"
    STOP = "stop"
    ROTATED = "rotated"
    TRANSFERRED = "transferred"
    ANGLE = "angle"
    SESSION = "session"
    DIRECTION = "direction"


states = State(
    {
        State.START: True,
        State.STOP: True,
        State.ROTATED: True,
        State.TRANSFERRED: True,
        State.ANGLE: 0,
        State.SESSION: 0,
        State.DIRECTION: 0,
    }
)


class Photos(DataManager):
    SIDE = "side"
    TOP = "top"
    IR = "ir"
    UV = "uv"


photos_taken = Photos({Photos.SIDE: 0, Photos.TOP: 0, Photos.IR: 0, Photos.UV: 0})
